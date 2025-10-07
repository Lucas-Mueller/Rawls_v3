"""
Simplified utility agent for parsing and validating participant responses.
"""
import asyncio
import json
import logging
import re
import os
from typing import Optional, List, Callable, Awaitable
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
from utils.parsing_errors import ParsingError, ParsingFailureType, detect_parsing_failure_type, create_parsing_error
from utils.statement_validation_errors import StatementValidationFailureType

logger = logging.getLogger(__name__)


async def run_without_tracing(agent, prompt, context=None):
    """Run agent without tracing to prevent utility agent operations from being traced."""
    trace_obj = get_trace_provider().create_trace(name="utility_agent_run", disabled=True)
    with trace_obj:
        return await Runner.run(agent, prompt, context=context)


class UtilityAgent:
    """Simplified utility agent for parsing and validating participant responses."""
    
    def __init__(self, utility_model: str = None, temperature: float = 0.0, experiment_language: str = "english", language_manager=None, temperature_cache=None):
        # Use environment variable or default for utility agents
        if utility_model is None:
            utility_model = os.getenv("UTILITY_AGENT_MODEL", "gpt-4.1-mini")
        
        self.utility_model = utility_model
        self.temperature = temperature
        self.experiment_language = experiment_language.lower()
        self.language_manager = language_manager
        self.temperature_cache = temperature_cache
        
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
    
    def _fallback_extract_ranking(self, response: str) -> Optional[dict]:
        """Fallback method to extract ranking from participant response using regex patterns."""
        import re
        
        # First check for VOTE_PROPOSAL text array format
        vote_proposal_match = re.search(r'VOTE_PROPOSAL:\s*\[([^\]]+)\]', response)
        if vote_proposal_match:
            array_content = vote_proposal_match.group(1)
            # Split by comma and clean up each item
            items = [item.strip() for item in array_content.split(',')]
            
            if len(items) == 4:
                # Direct mappings for Chinese principle names
                principle_mappings = {
                    '在最低收入约束条件下最大化平均收入': 'maximizing_average_floor_constraint',
                    '平均收入最大化': 'maximizing_average',
                    '在范围约束条件下最大化平均收入': 'maximizing_average_range_constraint', 
                    '最大化最低收入': 'maximizing_floor'
                }
                
                rankings = []
                for rank, item in enumerate(items, 1):
                    if item in principle_mappings:
                        rankings.append({
                            "principle": principle_mappings[item],
                            "rank": rank
                        })
                
                if len(rankings) == 4:
                    return {
                        "rankings": rankings,
                        "certainty": "sure"
                    }
        
        # Fall back to numbered list extraction
        lines = response.split('\n')
        rankings = []
        
        # Principle mappings for regex matching
        principle_patterns = {
            'mandarin': {
                r'最低收入最大化|最大化最低收入': 'maximizing_floor',
                r'平均收入最大化|最大化平均收入': 'maximizing_average', 
                r'在最低收入约束条件下最大化平均收入|最低收入约束': 'maximizing_average_floor_constraint',
                r'在范围约束条件下最大化平均收入|范围约束': 'maximizing_average_range_constraint'
            },
            'spanish': {
                r'Maximizar los ingresos mínimos': 'maximizing_floor',
                r'Maximizar los ingresos promedio': 'maximizing_average',
                r'Maximizar los ingresos promedio con restricción de ingreso mínimo': 'maximizing_average_floor_constraint', 
                r'Maximizar los ingresos promedio con restricción de rango': 'maximizing_average_range_constraint'
            }
        }
        
        patterns = principle_patterns.get(self.experiment_language.lower(), {})
        
        for line in lines:
            # Look for lines starting with numbers
            rank_match = re.match(r'^\s*(\d+)\.?\s*(.+)', line.strip())
            if rank_match:
                rank = int(rank_match.group(1))
                content = rank_match.group(2)
                
                # Try to match principle patterns
                for pattern, principle in patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        rankings.append({"principle": principle, "rank": rank})
                        break
        
        # Return data if we found 4 rankings
        if len(rankings) == 4:
            return {
                "rankings": rankings,
                "certainty": "sure"  # Default certainty for fallback parsing
            }
        
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

    def _normalize_principle_name(self, principle_text: str) -> str:
        """Normalize natural language principle descriptions to canonical enum values."""
        
        # Convert to lowercase for matching
        text_lower = principle_text.lower().strip()
        
        # English mappings
        english_mappings = {
            # Exact enum names (already correct)
            'maximizing_floor': 'maximizing_floor',
            'maximizing_average': 'maximizing_average', 
            'maximizing_average_floor_constraint': 'maximizing_average_floor_constraint',
            'maximizing_average_range_constraint': 'maximizing_average_range_constraint',
            
            # Natural language variations
            'maximizing the floor income': 'maximizing_floor',
            'maximizing the average income': 'maximizing_average',
            'maximizing the average income with a floor constraint': 'maximizing_average_floor_constraint',
            'maximizing the average income with a range constraint': 'maximizing_average_range_constraint',
            
            # Additional variations
            'maximizing floor income': 'maximizing_floor',
            'maximizing average income': 'maximizing_average',
            'maximizing average with floor constraint': 'maximizing_average_floor_constraint',
            'maximizing average with range constraint': 'maximizing_average_range_constraint',
            
            # Shortened versions
            'floor income': 'maximizing_floor',
            'average income': 'maximizing_average',
            'floor constraint': 'maximizing_average_floor_constraint', 
            'range constraint': 'maximizing_average_range_constraint'
        }
        
        # Spanish mappings
        spanish_mappings = {
            'maximizar los ingresos mínimos': 'maximizing_floor',
            'maximizar los ingresos promedio': 'maximizing_average',
            'maximizar los ingresos promedio con restricción de ingreso mínimo': 'maximizing_average_floor_constraint',
            'maximizar los ingresos promedio con restricción de rango': 'maximizing_average_range_constraint'
        }
        
        # Mandarin mappings  
        mandarin_mappings = {
            '最低收入最大化': 'maximizing_floor',
            '平均收入最大化': 'maximizing_average', 
            '在最低收入约束条件下最大化平均收入': 'maximizing_average_floor_constraint',
            '在范围约束条件下最大化平均收入': 'maximizing_average_range_constraint'
        }
        
        # Try each mapping set
        for mapping_set in [english_mappings, spanish_mappings, mandarin_mappings]:
            if text_lower in mapping_set:
                return mapping_set[text_lower]
        
        # If no exact match, try partial matching for robustness
        if 'floor' in text_lower and 'constraint' in text_lower:
            return 'maximizing_average_floor_constraint'
        elif 'range' in text_lower and 'constraint' in text_lower:
            return 'maximizing_average_range_constraint' 
        elif 'floor' in text_lower or 'minimum' in text_lower or '最低' in principle_text:
            return 'maximizing_floor'
        elif 'average' in text_lower or 'promedio' in text_lower or '平均' in principle_text:
            return 'maximizing_average'
            
        # Return original if no match found (will likely fail enum validation)
        return principle_text

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
                    agent_kwargs=parser_kwargs,
                    cache=self.temperature_cache
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
                    agent_kwargs=validator_kwargs,
                    cache=self.temperature_cache
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
                
                # Normalize principle name before validation
                normalized_principle = self._normalize_principle_name(data['principle'])
                logger.debug(f"LLM returned principle: '{data['principle']}' -> normalized to: '{normalized_principle}'")
                
                # Validate principle name
                valid_principles = [
                    'maximizing_floor', 'maximizing_average', 
                    'maximizing_average_floor_constraint', 'maximizing_average_range_constraint'
                ]
                if normalized_principle not in valid_principles:
                    raise ValueError(f"Invalid principle after normalization: {normalized_principle}")
                
                # Validate certainty level
                valid_certainty = ['very_unsure', 'unsure', 'sure', 'very_sure']
                if data['certainty'] not in valid_certainty:
                    raise ValueError(f"Invalid certainty: {data['certainty']}")
                
                return PrincipleChoice.create_for_parsing(
                    principle=JusticePrinciple(normalized_principle),
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

    async def parse_principle_choice_enhanced_with_feedback(
        self,
        response: str,
        max_retries: int = 3,
        participant_retry_callback: Optional[Callable[[str], Awaitable[str]]] = None
    ) -> PrincipleChoice:
        """
        Enhanced principle choice parsing with participant feedback capability.

        This method extends the existing parse_principle_choice_enhanced method
        to include intelligent feedback generation when parsing fails. It follows
        the exact same pattern as parse_principle_ranking_enhanced_with_feedback().

        Args:
            response: Participant's response to parse
            max_retries: Maximum number of retry attempts
            participant_retry_callback: Optional callback for participant retry communication

        Returns:
            PrincipleChoice instance if parsing succeeds

        Raises:
            ParsingError: If all retry attempts fail, with classified failure type
        """
        await self.async_init()

        # Track parsing attempts and errors for analysis
        parsing_attempts = []
        last_parsing_error = None

        for attempt in range(max_retries):
            try:
                # Try the existing enhanced parsing method
                return await self.parse_principle_choice_enhanced(response, max_retries=1)

            except ExperimentError as e:
                # Convert to parsing error with classification
                failure_type = detect_parsing_failure_type(response, "choice")
                if failure_type is None:
                    # Default classification for principle choice
                    if not response or len(response.strip()) < 10:
                        failure_type = ParsingFailureType.EMPTY_RESPONSE
                    else:
                        failure_type = ParsingFailureType.NO_NUMBERED_LIST

                parsing_error = create_parsing_error(
                    response=response,
                    parsing_operation="principle choice",
                    expected_format="choice",
                    additional_context={
                        "attempt_number": attempt + 1,
                        "max_retries": max_retries,
                        "experiment_language": self.experiment_language,
                        "utility_model": self.utility_model
                    },
                    cause=e
                )

                parsing_attempts.append({
                    "attempt": attempt + 1,
                    "failure_type": failure_type,
                    "error_message": str(e),
                    "response_length": len(response)
                })

                last_parsing_error = parsing_error

                # If this is not the final attempt and we have a retry callback
                if attempt < max_retries - 1 and participant_retry_callback:
                    try:
                        # Generate intelligent feedback (synchronous method)
                        feedback = self.generate_parsing_feedback(
                            original_response=response,
                            failure_type=failure_type,
                            attempt_number=attempt + 1,
                            expected_format="choice"
                        )

                        # Use callback to request retry from participant
                        new_response = await participant_retry_callback(feedback)

                        if new_response and new_response.strip():
                            response = new_response  # Use new response for next attempt
                            logger.info(f"Received retry response for choice parsing attempt {attempt + 2}: {len(new_response)} chars")
                        else:
                            logger.warning(f"Empty retry response received for choice parsing attempt {attempt + 2}")

                    except Exception as callback_error:
                        logger.error(f"Retry callback failed on choice parsing attempt {attempt + 1}: {callback_error}")
                        # Continue with original response if callback fails

                # Add exponential backoff between attempts
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))

        # All attempts failed - create comprehensive error with parsing history
        if last_parsing_error:
            # Limit response length in context to prevent memory issues
            context_response = response[:500] + "..." if len(response) > 500 else response

            last_parsing_error.parsing_context.update({
                "parsing_attempts": parsing_attempts,
                "total_attempts": len(parsing_attempts),
                "final_response": context_response
            })

            # Increment retry count to match total attempts
            for _ in range(len(parsing_attempts) - 1):
                last_parsing_error.increment_retry()

            logger.error(f"Failed to parse principle choice after {max_retries} attempts with feedback. "
                        f"Failure types: {[attempt['failure_type'].value for attempt in parsing_attempts]}")
            raise last_parsing_error

        # Fallback error if no parsing error was created
        final_error = create_parsing_error(
            response=response,
            parsing_operation="principle choice with feedback",
            expected_format="choice",
            additional_context={
                "max_retries": max_retries,
                "experiment_language": self.experiment_language,
                "parsing_attempts": parsing_attempts
            }
        )

        logger.error(f"Principle choice parsing failed completely after {max_retries} attempts")
        raise final_error

    async def parse_principle_ranking_enhanced(self, response: str, max_retries: int = 3) -> PrincipleRanking:
        """Parse principle ranking from participant response."""
        await self.async_init()
        
        # Add language-specific mapping context
        mapping_context = ""
        if self.experiment_language == "mandarin":
            mapping_context = """
        
        PRINCIPLE MAPPINGS (Mandarin → English):
        - "最低收入最大化" → "maximizing_floor"
        - "平均收入最大化" → "maximizing_average"
        - "在最低收入约束条件下最大化平均收入" → "maximizing_average_floor_constraint"
        - "在范围约束条件下最大化平均收入" → "maximizing_average_range_constraint"
        
        Use these exact mappings when converting from Mandarin to English principle names.
        """
        elif self.experiment_language == "spanish":
            mapping_context = """
        
        PRINCIPLE MAPPINGS (Spanish → English):
        - "Maximizar los ingresos mínimos" → "maximizing_floor"
        - "Maximizar los ingresos promedio" → "maximizing_average"  
        - "Maximizar los ingresos promedio con restricción de ingreso mínimo" → "maximizing_average_floor_constraint"
        - "Maximizar los ingresos promedio con restricción de rango" → "maximizing_average_range_constraint"
        
        Use these exact mappings when converting from Spanish to English principle names.
        """
        
        prompt = f"""
        Parse this {self.experiment_language} response for justice principle ranking. The response may contain mixed languages or English explanations - focus on the ranking structure.
        
        Response: "{response}"
        {mapping_context}
        
        INSTRUCTIONS:
        - Look for numbered lists (1., 2., 3., 4.) indicating ranking order
        - Ignore English text in parentheses like "(Maximizing average income)"
        - Focus on {self.experiment_language} principle names, not English explanations
        - Extract a complete ranking of all 4 principles from best (rank 1) to worst (rank 4)
        
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
        
        Always use English principle names in JSON output. Each rank 1-4 must appear exactly once.
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
                
                # Fallback extraction if JSON parsing fails
                if not data:
                    data = self._fallback_extract_ranking(response)
                
                # Debug logging for Mandarin parsing issue
                if self.experiment_language == "mandarin":
                    logger.error(f"MANDARIN PARSE ATTEMPT {attempt + 1}:")
                    logger.error(f"Original participant response: {response[:500]}...")  # First 500 chars
                    logger.error(f"LLM parsing response: {response_text}")
                    logger.error(f"Extracted JSON data: {data}")
                    if data:
                        logger.error(f"Rankings array length: {len(data.get('rankings', []))}")
                
                if not data or len(data['rankings']) != 4:
                    raise ValueError(f"Invalid ranking structure: got {len(data['rankings']) if data else 0} rankings, expected 4")
                
                ranked_principles = []
                for item in data['rankings']:
                    # Normalize principle name before validation
                    normalized_principle = self._normalize_principle_name(item['principle'])
                    logger.debug(f"LLM returned principle: '{item['principle']}' -> normalized to: '{normalized_principle}'")
                    
                    ranked_principles.append(RankedPrinciple(
                        principle=JusticePrinciple(normalized_principle),
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
        """Detect preference statements for consensus building."""
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
    

    def detect_numerical_agreement(self, response: str) -> tuple[bool, Optional[str]]:
        """
        Detect numerical agreement in responses (1=yes, 0=no).
        
        Args:
            response: The participant's response to parse
            
        Returns:
            Tuple of (success, error_message) where:
            - success=True for "1", success=False for "0" 
            - error_message=None for valid responses, error description for invalid responses
        """
        # Clean the response
        response_clean = response.strip()
        
        # Try forgiving digit extraction - find all valid digits (0 or 1) in response
        import re
        digit_matches = re.findall(r'[01]', response_clean)
        
        if len(digit_matches) == 1:
            # Found exactly one valid digit
            if digit_matches[0] == "1":
                return True, None  # Agreement
            elif digit_matches[0] == "0":
                return False, None  # Disagreement
        elif len(digit_matches) > 1:
            # Multiple digits found
            return False, f"Multiple numbers found: {digit_matches}. Please respond with exactly one number (1 or 0)."
        
        # No valid numerical response found
        return False, f"No valid number found. Please respond with exactly: 1 (to vote now) or 0 (to continue discussion)."


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
        
        language_manager = self.language_manager
        return language_manager.get(
            "prompts.utility_constraint_re_prompt",
            participant_name=participant_name,
            principle_name=principle_name,
            constraint_type=constraint_type
        )

    def generate_parsing_feedback(
        self,
        original_response: str,
        failure_type: ParsingFailureType,
        attempt_number: int,
        expected_format: str = "ranking"
    ) -> str:
        """
        Generate contextual feedback for parsing failures.

        This method creates intelligent, multilingual feedback based on the specific
        type of parsing failure encountered. The feedback is tailored to help
        participants understand what went wrong and how to provide a proper response.

        Args:
            original_response: The raw response that failed to parse
            failure_type: The classified type of parsing failure
            attempt_number: Which retry attempt this is (1-based)
            expected_format: The expected response format ('ranking', 'choice', etc.)

        Returns:
            Multilingual feedback string to help the participant retry

        Example:
            >>> feedback = utility_agent.generate_parsing_feedback(
            ...     original_response="I choose option A",
            ...     failure_type=ParsingFailureType.CHOICE_FORMAT_CONFUSION,
            ...     attempt_number=1
            ... )
        """

        # Map failure types to template keys
        failure_type_keys = {
            ParsingFailureType.CHOICE_FORMAT_CONFUSION: "choice_format_confusion",
            ParsingFailureType.INCOMPLETE_RANKING: "incomplete_ranking",
            ParsingFailureType.NO_NUMBERED_LIST: "no_numbered_list",
            ParsingFailureType.EMPTY_RESPONSE: "empty_response"
        }

        # Get the template key, fallback to empty_response if not found
        template_key = failure_type_keys.get(failure_type, "empty_response")

        # Get language-specific templates from language manager
        try:
            template = {
                "explanation": self.language_manager.get(f"parsing_feedback.{template_key}.explanation") or "Your response could not be parsed correctly.",
                "instruction": self.language_manager.get(f"parsing_feedback.{template_key}.instruction") or "Please provide a complete response ranking the justice principles.",
                "example": self.language_manager.get(f"parsing_feedback.{template_key}.example") or "Example: 1. Your top choice, 2. Second choice, 3. Third choice, 4. Last choice"
            }
        except Exception as e:
            logger.warning(f"Failed to get parsing feedback template for {template_key}: {e}")
            # Fallback to English hard-coded template
            fallback_template = {
                "explanation": "Your response could not be parsed correctly.",
                "instruction": "Please provide a complete response ranking the justice principles.",
                "example": "Example: 1. Your top choice, 2. Second choice, 3. Third choice, 4. Last choice"
            }
            template = fallback_template

        # Build feedback message with language-specific phrases
        try:
            attempt_phrase = self.language_manager.get(
                "parsing_feedback.attempt_label",
                attempt_number=attempt_number
            )
        except Exception:
            attempt_phrase = f"Attempt {attempt_number}"

        try:
            parsing_issue_phrase = self.language_manager.get(
                "parsing_feedback.issue_heading"
            )
        except Exception:
            parsing_issue_phrase = "Parsing Issue"

        feedback_parts = [
            f"⚠️ {parsing_issue_phrase} ({attempt_phrase}):",
            "",
            template["explanation"],
            "",
            template["instruction"],
            "",
            "📝 " + template["example"]
        ]

        # Add response preview for context (truncated if too long)
        if original_response and len(original_response.strip()) > 0:
            try:
                response_preview_phrase = self.language_manager.get(
                    "parsing_feedback.preview_label"
                )
            except Exception:
                response_preview_phrase = "Your response"

            preview = original_response[:100] + "..." if len(original_response) > 100 else original_response
            feedback_parts.extend([
                "",
                f"🔍 {response_preview_phrase}: \"{preview}\""
            ])

        return "\n".join(feedback_parts)

    async def parse_principle_ranking_enhanced_with_feedback(
        self,
        response: str,
        max_retries: int = 3,
        participant_retry_callback: Optional[Callable[[str], Awaitable[str]]] = None
    ) -> PrincipleRanking:
        """
        Enhanced parsing with participant feedback capability.

        This method extends the existing parse_principle_ranking_enhanced method
        to include intelligent feedback generation when parsing fails. It uses
        the new error classification system to provide contextual guidance to
        participants for retry attempts.

        Args:
            response: Participant's response to parse
            max_retries: Maximum number of retry attempts
            participant_retry_callback: Optional callback for participant retry communication

        Returns:
            PrincipleRanking instance if parsing succeeds

        Raises:
            ParsingError: If all retry attempts fail, with classified failure type
        """
        await self.async_init()

        # Track parsing attempts and errors for analysis
        parsing_attempts = []
        last_parsing_error = None

        for attempt in range(max_retries):
            try:
                # Try the existing enhanced parsing method
                return await self.parse_principle_ranking_enhanced(response, max_retries=1)

            except ExperimentError as e:
                # Convert to parsing error with classification
                failure_type = detect_parsing_failure_type(response, "ranking")
                if failure_type is None:
                    # Default classification based on error message
                    if "incomplete" in str(e).lower():
                        failure_type = ParsingFailureType.INCOMPLETE_RANKING
                    elif "choice" in str(e).lower():
                        failure_type = ParsingFailureType.CHOICE_FORMAT_CONFUSION
                    else:
                        failure_type = ParsingFailureType.NO_NUMBERED_LIST

                parsing_error = create_parsing_error(
                    response=response,
                    parsing_operation="principle ranking",
                    expected_format="ranking",
                    additional_context={
                        "attempt_number": attempt + 1,
                        "max_retries": max_retries,
                        "experiment_language": self.experiment_language,
                        "utility_model": self.utility_model
                    },
                    cause=e
                )

                parsing_attempts.append({
                    "attempt": attempt + 1,
                    "failure_type": failure_type,
                    "error_message": str(e),
                    "response_length": len(response)
                })

                last_parsing_error = parsing_error

                # If this is not the final attempt and we have a retry callback
                if attempt < max_retries - 1 and participant_retry_callback:
                    try:
                        # Generate intelligent feedback (synchronous method)
                        feedback = self.generate_parsing_feedback(
                            original_response=response,
                            failure_type=failure_type,
                            attempt_number=attempt + 1,
                            expected_format="ranking"
                        )

                        # Use callback to request retry from participant
                        new_response = await participant_retry_callback(feedback)

                        if new_response and new_response.strip():
                            response = new_response  # Use new response for next attempt
                            logger.info(f"Received retry response for attempt {attempt + 2}: {len(new_response)} chars")
                        else:
                            logger.warning(f"Empty retry response received for attempt {attempt + 2}")

                    except Exception as callback_error:
                        logger.error(f"Retry callback failed on attempt {attempt + 1}: {callback_error}")
                        # Continue with original response if callback fails

                # Add exponential backoff between attempts
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))

        # All attempts failed - create comprehensive error with parsing history
        if last_parsing_error:
            # Limit response length in context to prevent memory issues
            context_response = response[:500] + "..." if len(response) > 500 else response

            last_parsing_error.parsing_context.update({
                "parsing_attempts": parsing_attempts,
                "total_attempts": len(parsing_attempts),
                "final_response": context_response
            })

            # Increment retry count to match total attempts
            for _ in range(len(parsing_attempts) - 1):
                last_parsing_error.increment_retry()

            logger.error(f"Failed to parse principle ranking after {max_retries} attempts with feedback. "
                        f"Failure types: {[attempt['failure_type'].value for attempt in parsing_attempts]}")
            raise last_parsing_error

        # Fallback error if no parsing error was created
        final_error = create_parsing_error(
            response=response,
            parsing_operation="principle ranking with feedback",
            expected_format="ranking",
            additional_context={
                "max_retries": max_retries,
                "experiment_language": self.experiment_language,
                "parsing_attempts": parsing_attempts
            }
        )

        logger.error(f"Principle ranking parsing failed completely after {max_retries} attempts")
        raise final_error

    async def classify_statement_validation_failure(
        self,
        statement: str,
        min_length: int,
        language: str,
        context: str = ""
    ) -> StatementValidationFailureType:
        """
        Use utility agent to classify why a statement validation failed.

        More robust than pattern matching - handles edge cases and provides
        accurate classification for appropriate feedback generation.

        Called only on validation failures (not every statement) for efficiency.
        Follows exact A1/A2 pattern of "fast validation → classify failure → feedback".

        Args:
            statement: The statement that failed validation
            min_length: Minimum required length for statements
            language: Language of the experiment (english, spanish, mandarin)
            context: Optional context about the discussion round

        Returns:
            StatementValidationFailureType: Classification of the failure type
        """
        await self.async_init()

        # Calculate actual length for prompt
        actual_length = len(statement.strip()) if statement else 0

        # Build classification prompt
        try:
            classification_prompt = self.language_manager.get(
                "prompts.statement_validation_classification",
                statement=statement,
                min_length=min_length,
                actual_length=actual_length,
                language=language,
                context=context
            )
        except Exception:
            # Fallback prompt if translation key is missing
            classification_prompt = f"""Analyze this discussion statement that failed validation:

Statement: '{statement}'
Minimum required length: {min_length} characters
Actual length: {actual_length} characters
Language: {language}
Context: {context}

Classify why this statement failed validation. Respond with exactly one of these classifications:
- EMPTY_RESPONSE: if the statement is empty or contains only whitespace
- TOO_SHORT: if the statement is below minimum length but has some content
- MINIMAL_CONTENT: if the statement meets length requirements but lacks substantive discussion content

Classification:"""

        try:
            result = await run_without_tracing(self.parser_agent, classification_prompt)
            classification_response = result.final_output.strip().upper()

            # Parse the classification response
            if "EMPTY_RESPONSE" in classification_response:
                return StatementValidationFailureType.EMPTY_RESPONSE
            elif "MINIMAL_CONTENT" in classification_response:
                return StatementValidationFailureType.MINIMAL_CONTENT
            elif "TOO_SHORT" in classification_response:
                return StatementValidationFailureType.TOO_SHORT
            else:
                # Default fallback based on observable characteristics
                if actual_length < min_length:
                    return StatementValidationFailureType.TOO_SHORT
                else:
                    return StatementValidationFailureType.MINIMAL_CONTENT

        except Exception as e:
            logger.warning(f"Failed to classify statement validation failure: {e}")
            # Graceful fallback to simple length-based classification
            if not statement or len(statement.strip()) < 3:
                return StatementValidationFailureType.EMPTY_RESPONSE
            elif actual_length < min_length:
                return StatementValidationFailureType.TOO_SHORT
            else:
                return StatementValidationFailureType.MINIMAL_CONTENT

    async def validate_consensus_against_discussion(self, discussion_content: str, consensus_principle: str) -> tuple[bool, List[str]]:
        """
        Validate that the recorded consensus aligns with the discussion content.
        Returns (is_valid, warnings_list)
        """
        warnings = []
        
        # Use LLM to analyze discussion content for principle preferences
        validation_prompt = self.language_manager.get(
            "prompts.utility_consensus_validation",
            discussion_content=discussion_content,
            consensus_principle=consensus_principle
        )
        
        try:
            await self.async_init()
            result = await run_without_tracing(self.parser_agent, validation_prompt)
            response = result.final_output.strip()
            
            if "CONSENSUS_MISMATCH" in response:
                warnings.append("Consensus validation failed: Final consensus doesn't match discussion content")
                return False, warnings
            elif "CONSENSUS_VALID" in response:
                return True, warnings
            else:
                warnings.append("Consensus validation inconclusive: Unable to determine alignment")
                return True, warnings  # Default to valid if inconclusive
                
        except Exception as e:
            logger.warning(f"Consensus validation failed due to error: {e}")
            warnings.append(f"Consensus validation error: {str(e)}")
            return True, warnings  # Default to valid if error occurs
