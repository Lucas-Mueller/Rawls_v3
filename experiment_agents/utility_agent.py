"""
Simplified utility agent for parsing and validating participant responses.
"""
import asyncio
import json
import logging
import re
import os
from typing import Optional, List
from agents import Agent, Runner
from agents.tracing.setup import get_trace_provider

from models import (
    PrincipleChoice, PrincipleRanking, JusticePrinciple,
    CertaintyLevel, RankedPrinciple
)
from utils.error_handling import (
    ExperimentError, ErrorSeverity, ExperimentErrorCategory
)
from utils.dynamic_model_capabilities import create_agent_with_temperature_retry
from utils.language_manager import get_language_manager

logger = logging.getLogger(__name__)


async def run_without_tracing(agent, prompt, context=None):
    """Run agent without tracing to prevent utility agent operations from being traced."""
    trace_obj = get_trace_provider().create_trace(name="utility_agent_run", disabled=True)
    with trace_obj:
        return await Runner.run(agent, prompt, context=context)


class UtilityAgent:
    """Simplified utility agent for parsing and validating participant responses."""
    
    def __init__(self, utility_model: str = None, temperature: float = 0.0, experiment_language: str = "english"):
        # Use environment variable or default for utility agents
        if utility_model is None:
            utility_model = os.getenv("UTILITY_AGENT_MODEL", "gpt-4.1-mini")
        
        self.utility_model = utility_model
        self.temperature = temperature
        self.experiment_language = experiment_language.lower()
        self.language_manager = get_language_manager()
        
        # Agents will be created in async_init
        self.parser_agent = None
        self.validator_agent = None
        self._initialization_complete = False

    def _extract_and_validate_json(self, text: str, expected_schema: dict) -> Optional[dict]:
        """Extract and validate JSON from text response with schema checking."""
        # Try to find JSON in the response
        json_candidates = []
        
        # Look for complete JSON objects
        brace_count = 0
        start_idx = None
        
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx is not None:
                    json_candidates.append(text[start_idx:i+1])
        
        # Try to parse each JSON candidate
        for candidate in json_candidates:
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    # Validate schema
                    if self._validate_json_schema(data, expected_schema):
                        return data
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _validate_json_schema(self, data: dict, expected_schema: dict) -> bool:
        """Validate JSON data against expected schema."""
        for key, expected_type in expected_schema.items():
            if key not in data:
                return False
            
            value = data[key]
            if isinstance(expected_type, tuple):
                # Multiple allowed types (e.g., int or None)
                if not any(isinstance(value, t) for t in expected_type):
                    return False
            else:
                # Single expected type
                if not isinstance(value, expected_type):
                    return False
        
        return True

    async def async_init(self):
        """Asynchronously initialize utility agents."""
        if self._initialization_complete:
            return
        
        try:
            trace_obj = get_trace_provider().create_trace(name="utility_agent_init", disabled=True)
            with trace_obj:
                logger.info(f"Creating utility agents with model: {self.utility_model} (tracing disabled)")

                # Create parser agent
                parser_kwargs = {
                    "name": "Response Parser",
                    "instructions": self.language_manager.get_parser_instructions(),
                }

                self.parser_agent, self.temperature_info = await create_agent_with_temperature_retry(
                    agent_class=Agent,
                    model_string=self.utility_model,
                    temperature=self.temperature,
                    agent_kwargs=parser_kwargs
                )

                # Create validator agent
                validator_kwargs = {
                    "name": "Response Validator", 
                    "instructions": self.language_manager.get_validator_instructions(),
                }

                self.validator_agent, _ = await create_agent_with_temperature_retry(
                    agent_class=Agent,
                    model_string=self.utility_model,
                    temperature=self.temperature,
                    agent_kwargs=validator_kwargs
                )

            self._initialization_complete = True
            logger.info(f"✅ Utility agents initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize utility agents: {e}")
            raise e

    async def parse_principle_choice_enhanced(self, response: str, max_retries: int = 3) -> PrincipleChoice:
        """Parse principle choice from participant response with enhanced reliability."""
        await self.async_init()
        
        # Enhanced multilingual prompt with examples
        language_examples = {
            'english': 'Example: "I choose maximizing the floor with a constraint of $50,000"',
            'spanish': 'Ejemplo: "Elijo maximizar el piso con una restricción de $50,000"', 
            'mandarin': '例子："我选择最大化底线，约束为50,000美元"'
        }
        
        example = language_examples.get(self.experiment_language, language_examples['english'])
        
        prompt = f"""
        Parse this {self.experiment_language} response for justice principle choice.
        
        Response: "{response}"
        
        JUSTICE PRINCIPLES (always use these exact English names in output):
        1. "maximizing_floor" - Maximizing the minimum/floor income
        2. "maximizing_average" - Maximizing the average income
        3. "maximizing_average_floor_constraint" - Maximizing average with minimum floor constraint
        4. "maximizing_average_range_constraint" - Maximizing average with income range constraint
        
        CONSTRAINT EXTRACTION:
        - For floor constraint: Extract dollar amount (e.g., "$50,000" → 50000)
        - For range constraint: Extract dollar amount (e.g., "$30,000" → 30000)
        - If no constraint mentioned for constraint principles, set to null
        
        CERTAINTY LEVELS:
        - Look for confidence indicators in the response
        - Map to: "very_unsure", "unsure", "sure", "very_sure"
        
        {example}
        
        Return ONLY valid JSON:
        {{
            "principle": "one_of_the_four_exact_names_above",
            "constraint_amount": null_or_integer_without_commas,
            "certainty": "very_unsure|unsure|sure|very_sure"
        }}
        
        CRITICAL: Always use exact English principle names regardless of input language.
        """
        
        last_error = None
        for attempt in range(max_retries):
            try:
                result = await run_without_tracing(self.parser_agent, prompt)
                response_text = result.final_output.strip()
                
                # Robust JSON extraction
                data = self._extract_and_validate_json(response_text, {
                    'principle': str,
                    'constraint_amount': (int, type(None)),
                    'certainty': str
                })
                
                if not data:
                    raise ValueError("No valid JSON found in response")
                
                # Validate principle name
                valid_principles = [
                    'maximizing_floor', 'maximizing_average', 
                    'maximizing_average_floor_constraint', 'maximizing_average_range_constraint'
                ]
                if data['principle'] not in valid_principles:
                    raise ValueError(f"Invalid principle: {data['principle']}")
                
                # Validate certainty level
                valid_certainty = ['very_unsure', 'unsure', 'sure', 'very_sure']
                if data['certainty'] not in valid_certainty:
                    raise ValueError(f"Invalid certainty: {data['certainty']}")
                
                return PrincipleChoice.create_for_parsing(
                    principle=JusticePrinciple(data['principle']),
                    constraint_amount=data.get('constraint_amount'),
                    certainty=CertaintyLevel(data['certainty']),
                    reasoning=response
                )
                
            except Exception as e:
                last_error = e
                logger.warning(f"Parse attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
        
        # All retries failed
        logger.error(f"Failed to parse principle choice after {max_retries} attempts: {last_error}")
        raise ExperimentError(
            f"Could not parse principle choice from response after {max_retries} attempts: {last_error}",
            ExperimentErrorCategory.VALIDATION_ERROR,
            ErrorSeverity.FATAL
        )

    async def parse_principle_ranking_enhanced(self, response: str, max_retries: int = 3) -> PrincipleRanking:
        """Parse principle ranking from participant response."""
        await self.async_init()
        
        prompt = f"""
        Parse this {self.experiment_language} response for justice principle ranking:
        
        Response: "{response}"
        
        Extract a complete ranking of all 4 principles from best (rank 1) to worst (rank 4).
        
        Return JSON:
        {{
            "rankings": [
                {{"principle": "maximizing_floor", "rank": 1}},
                {{"principle": "maximizing_average", "rank": 2}},
                {{"principle": "maximizing_average_floor_constraint", "rank": 3}},
                {{"principle": "maximizing_average_range_constraint", "rank": 4}}
            ],
            "certainty": "very_unsure|unsure|sure|very_sure"
        }}
        
        Always use English principle names. Each rank 1-4 must appear exactly once.
        """
        
        for attempt in range(max_retries):
            try:
                result = await run_without_tracing(self.parser_agent, prompt)
                response_text = result.final_output.strip()
                
                # Use robust JSON extraction
                data = self._extract_and_validate_json(response_text, {
                    'rankings': list,
                    'certainty': str
                })
                
                if not data or len(data['rankings']) != 4:
                    raise ValueError("Invalid ranking structure")
                
                ranked_principles = []
                for item in data['rankings']:
                    ranked_principles.append(RankedPrinciple(
                        principle=JusticePrinciple(item['principle']),
                        rank=item['rank']
                    ))
                
                return PrincipleRanking(
                    rankings=ranked_principles,
                    certainty=CertaintyLevel(data['certainty'])
                )
                
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"Failed to parse principle ranking: {e}")
                    
        raise ExperimentError(
            "Could not parse principle ranking from response",
            ExperimentErrorCategory.VALIDATION_ERROR,
            ErrorSeverity.FATAL
        )

    async def detect_preference_statement(self, statement: str) -> Optional[PrincipleChoice]:
        """Detect preference statements for simple mode consensus."""
        await self.async_init()
        
        # Reject letter-based preferences immediately
        if re.search(r'\b(?:prefer|choice|preference)\s+[a-d]\b', statement.lower()):
            return None
        
        prompt = f"""
        Analyze this {self.experiment_language} statement for definitive preference expressions:
        
        Statement: "{statement}"
        
        Look for phrases like:
        - "My preference is [principle]"
        - "I prefer [principle]"
        - "My choice is [principle]"
        
        If a clear preference is detected, return JSON:
        {{
            "preference_detected": true,
            "principle": "maximizing_floor|maximizing_average|maximizing_average_floor_constraint|maximizing_average_range_constraint",
            "constraint_amount": null_or_integer,
            "certainty": "sure"
        }}
        
        If no clear preference, return: {{"preference_detected": false}}
        
        Always use English principle names.
        """
        
        try:
            result = await run_without_tracing(self.parser_agent, prompt)
            response_text = result.final_output.strip()
            
            # Use robust JSON extraction
            data = self._extract_and_validate_json(response_text, {
                'preference_detected': bool
            })
            
            if data and data.get('preference_detected'):
                return PrincipleChoice.create_for_parsing(
                    principle=JusticePrinciple(data['principle']),
                    constraint_amount=data.get('constraint_amount'),
                    certainty=CertaintyLevel(data.get('certainty', 'sure')),
                    reasoning=statement
                )
                    
        except Exception as e:
            logger.warning(f"Preference detection failed: {e}")
            
        return None

    async def detect_vote_intention_enhanced(self, response: str) -> Optional[str]:
        """Compatibility method for legacy vote intention detection."""
        # Simple vote intention detection for backward compatibility
        response_lower = response.lower().strip()
        
        vote_intentions = [
            'vote', 'voting', 'ballot', 'poll',
            'let\'s vote', 'should we vote', 'ready to vote',
            'call for a vote', 'time to vote', 'proceed with voting'
        ]
        
        for intention in vote_intentions:
            if intention in response_lower:
                return response  # Return original response if vote intention detected
        
        return None  # No vote intention detected

    async def detect_agreement(self, response: str) -> bool:
        """Detect yes/no agreement in responses."""
        response_lower = response.lower().strip()
        
        # Multi-language agreement patterns
        agreement_words = {
            'english': ['yes', 'agree', 'correct', 'right', 'exactly', 'absolutely'],
            'spanish': ['sí', 'si', 'de acuerdo', 'acepto', 'correcto', 'exacto'],
            'mandarin': ['是的', '对', '同意', '正确', '好的']
        }
        
        
        # Check agreement first
        for word in agreement_words.get(self.experiment_language, agreement_words['english']):
            if word in response_lower:
                return True
                
        return False

    def check_preference_consensus_simple_mode(self, preferences: List[PrincipleChoice]) -> tuple[bool, Optional[PrincipleChoice], List[str]]:
        """Check if preference statements reached consensus in simple mode."""
        if not preferences or len(preferences) == 0:
            return False, None, ["No preferences to check"]
        
        # Check if all preferences are for the same principle
        first_principle = preferences[0].principle
        constraint_amounts = []
        
        for pref in preferences:
            if pref.principle != first_principle:
                return False, None, ["Participants have different principle preferences"]
            
            if pref.constraint_amount is not None:
                constraint_amounts.append(pref.constraint_amount)
        
        # For constraint principles, check if constraint amounts match
        if first_principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                              JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
            if constraint_amounts and len(set(constraint_amounts)) > 1:
                return False, None, ["Different constraint amounts specified"]
        
        # Consensus reached
        consensus_preference = preferences[0]  # All have same principle
        return True, consensus_preference, []

    def check_ballot_consensus(self, ballots: List[PrincipleChoice]) -> tuple[bool, Optional[PrincipleChoice], List[str]]:
        """Check if ballots reached consensus in complex mode."""
        if not ballots or len(ballots) == 0:
            return False, None, ["No ballots to check"]
        
        # All ballots must be for the same principle
        first_principle = ballots[0].principle
        constraint_amounts = []
        
        for ballot in ballots:
            if ballot.principle != first_principle:
                return False, None, ["Ballots contain different principles"]
            
            if ballot.constraint_amount is not None:
                constraint_amounts.append(ballot.constraint_amount)
        
        # For constraint principles, check constraint amounts
        if first_principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                              JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
            if constraint_amounts and len(set(constraint_amounts)) > 1:
                return False, None, ["Different constraint amounts in ballots"]
        
        # Consensus reached
        return True, ballots[0], []

    async def validate_constraint_specification(self, choice: PrincipleChoice) -> bool:
        """Validate that constraint principles have constraint amounts specified."""
        if choice.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
            return choice.constraint_amount is not None and choice.constraint_amount > 0
        return True

    async def re_prompt_for_constraint(self, participant_name: str, choice: PrincipleChoice) -> str:
        """Generate re-prompt message for missing constraint."""
        constraint_type = "floor" if choice.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT else "range"
        principle_name = choice.principle.value
        
        language_manager = get_language_manager()
        return language_manager.get(
            "prompts.utility_constraint_re_prompt",
            participant_name=participant_name,
            principle_name=principle_name,
            constraint_type=constraint_type
        )