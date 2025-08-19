"""
Utility agent for parsing and validating participant responses.
"""
import asyncio
import logging
import re
import os
from typing import Optional, Dict, Any, List
from agents import Agent, Runner, AgentOutputSchema

from models import (
    PrincipleChoice, PrincipleRanking, VoteProposal, JusticePrinciple,
    ParsedResponse, ValidationResult, CertaintyLevel, RankedPrinciple
)
from utils.error_handling import (
    ValidationError, AgentCommunicationError, ExperimentError,
    ErrorSeverity, ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors
)
from utils.model_provider import create_model_config_with_temperature_detection, create_model_settings, create_model_config_sync
from utils.dynamic_model_capabilities import create_agent_with_temperature_retry
from utils.language_manager import get_language_manager, get_english_principle_name

logger = logging.getLogger(__name__)


class UtilityAgent:
    """Specialized agent for parsing and validating participant responses with enhanced text parsing."""
    
    def __init__(self, utility_model: str = None, temperature: float = 0.0):
        # Use environment variable or default for utility agents
        if utility_model is None:
            utility_model = os.getenv("UTILITY_AGENT_MODEL", "gpt-4.1-mini")
        
        self.utility_model = utility_model
        self.temperature = temperature
        self.temperature_info = None
        self.language_manager = get_language_manager()
        
        # Agents will be created in async_init
        self.parser_agent = None
        self.validator_agent = None
        self._initialization_complete = False
        
        # Enhanced parsing patterns
        self._principle_patterns = self._compile_principle_patterns()
        self._certainty_patterns = self._compile_certainty_patterns()
        self._ranking_patterns = self._compile_ranking_patterns()
        
    async def async_init(self):
        """Asynchronously initialize utility agents with dynamic temperature detection."""
        if self._initialization_complete:
            return
        
        try:
            logger.info(f"Creating utility agents with model: {self.utility_model}")
            
            # Create parser agent with dynamic temperature detection
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
            
            # Create validator agent (reuse temperature info since it's the same model)
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
            
            # Log temperature status
            self._log_temperature_status()
            
            self._initialization_complete = True
            logger.info(f"✅ Utility agents initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize utility agents: {e}")
            raise e
            
    def _log_temperature_status(self):
        """Log temperature detection status for utility agent."""
        if not self.temperature_info:
            return
            
        temp_info = self.temperature_info
        detection_method = temp_info.get('detection_method', 'unknown')
        
        if not temp_info.get("supports_temperature", False):
            was_retried = temp_info.get('was_retried', False)
            if was_retried:
                logger.info(f"🔄 Utility agent: Temperature not supported, automatically retried without temperature (method: {detection_method})")
            else:
                logger.info(f"Utility agent: Using default behavior, temperature not supported (method: {detection_method})")
        else:
            logger.info(f"✅ Utility agent: Temperature support confirmed (method: {detection_method})")
    
    # Old instruction methods replaced by language manager calls
    
    @handle_experiment_errors(
        category=ExperimentErrorCategory.VALIDATION_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="parse_principle_choice"
    )
    async def parse_principle_choice(self, response: str) -> PrincipleChoice:
        """Parse principle choice from participant response."""
        # Ensure utility agent is initialized
        await self.async_init()
        
        error_handler = get_global_error_handler()
        
        parse_prompt = self.language_manager.get_principle_choice_parsing_prompt(response)
        
        try:
            result = await Runner.run(self.parser_agent, parse_prompt)
            parsed_result = result.final_output
            
            if not parsed_result.success:
                raise ValidationError(
                    f"Failed to parse principle choice: {parsed_result.error_message}",
                    ErrorSeverity.RECOVERABLE,
                    {
                        "response_text": response,
                        "parse_error": parsed_result.error_message,
                        "operation": "principle_choice_parsing"
                    }
                )
            
            data = parsed_result.parsed_data
            return PrincipleChoice(
                principle=JusticePrinciple(data['principle']),
                constraint_amount=data.get('constraint_amount'),
                certainty=CertaintyLevel(data['certainty']),
                reasoning=data.get('reasoning')
            )
            
        except (ValueError, KeyError) as e:
            raise ValidationError(
                f"Invalid principle choice format: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "parsing_error": str(e),
                    "operation": "principle_choice_validation"
                },
                cause=e
            )
        except Exception as e:
            raise AgentCommunicationError(
                f"Agent communication failed during principle choice parsing: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "communication_error": str(e),
                    "operation": "principle_choice_agent_communication"
                },
                cause=e
            )
    
    @handle_experiment_errors(
        category=ExperimentErrorCategory.VALIDATION_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="parse_principle_ranking"
    )
    async def parse_principle_ranking(self, response: str) -> PrincipleRanking:
        """Parse principle ranking from participant response."""
        # Ensure utility agent is initialized
        await self.async_init()
        
        parse_prompt = self.language_manager.get_principle_ranking_parsing_prompt(response)
        
        try:
            result = await Runner.run(self.parser_agent, parse_prompt)
            parsed_result = result.final_output
            
            if not parsed_result.success:
                raise ValidationError(
                    f"Failed to parse principle ranking: {parsed_result.error_message}",
                    ErrorSeverity.RECOVERABLE,
                    {
                        "response_text": response,
                        "parse_error": parsed_result.error_message,
                        "operation": "principle_ranking_parsing"
                    }
                )
            
            data = parsed_result.parsed_data
            rankings = []
            for ranking_data in data['rankings']:
                rankings.append(RankedPrinciple(
                    principle=JusticePrinciple(ranking_data['principle']),
                    rank=ranking_data['rank']
                ))
            
            # Extract overall certainty level for the entire ranking
            overall_certainty = CertaintyLevel(data.get('certainty', 'sure'))
            
            ranking = PrincipleRanking(rankings=rankings, certainty=overall_certainty)
            
            # Validate ranking completeness
            if not self._validate_ranking_completeness(ranking):
                raise ValidationError(
                    "Incomplete ranking - missing principles or invalid ranks",
                    ErrorSeverity.RECOVERABLE,
                    {
                        "response_text": response,
                        "parsed_rankings": [{"principle": r.principle.value, "rank": r.rank} for r in rankings],
                        "operation": "ranking_completeness_validation"
                    }
                )
            
            return ranking
            
        except (ValueError, KeyError) as e:
            raise ValidationError(
                f"Invalid principle ranking format: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "parsing_error": str(e),
                    "operation": "principle_ranking_validation"
                },
                cause=e
            )
        except Exception as e:
            raise AgentCommunicationError(
                f"Agent communication failed during principle ranking parsing: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "response_text": response,
                    "communication_error": str(e),
                    "operation": "principle_ranking_agent_communication"
                },
                cause=e
            )
    
    def _validate_ranking_completeness(self, ranking: PrincipleRanking) -> bool:
        """Validate that ranking includes all 4 principles with ranks 1-4."""
        if len(ranking.rankings) != 4:
            return False
        
        principles = {r.principle for r in ranking.rankings}
        expected_principles = set(JusticePrinciple)
        if principles != expected_principles:
            return False
        
        ranks = {r.rank for r in ranking.rankings}
        expected_ranks = {1, 2, 3, 4}
        if ranks != expected_ranks:
            return False
        
        return True
    
    @handle_experiment_errors(
        category=ExperimentErrorCategory.VALIDATION_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="validate_constraint"
    )
    async def validate_constraint_specification(self, choice: PrincipleChoice) -> bool:
        """Validate constraint principles have required amounts."""
        try:
            constraint_principles = [
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            ]
            
            if choice.principle in constraint_principles:
                is_valid = choice.constraint_amount is not None and choice.constraint_amount > 0
                if not is_valid:
                    logger.warning(
                        f"Constraint principle {choice.principle.value} missing valid constraint amount: {choice.constraint_amount}"
                    )
                return is_valid
            
            return True
            
        except Exception as e:
            raise ValidationError(
                f"Constraint validation failed: {str(e)}",
                ErrorSeverity.RECOVERABLE,
                {
                    "principle": choice.principle.value if choice.principle else "unknown",
                    "constraint_amount": choice.constraint_amount,
                    "validation_error": str(e)
                },
                cause=e
            )
    
    async def extract_vote_from_statement(self, statement: str) -> Optional[VoteProposal]:
        """Detect if participant is proposing a vote."""
        # Ensure utility agent is initialized
        await self.async_init()
        
        detection_prompt = self.language_manager.get_vote_detection_prompt(statement)
        
        result = await Runner.run(self.parser_agent, detection_prompt)
        response_text = result.final_output.strip()
        
        if response_text.startswith("VOTE_PROPOSAL:"):
            proposal_text = response_text[len("VOTE_PROPOSAL:"):].strip()
            return VoteProposal(
                proposed_by="participant",  # Will be set by caller
                proposal_text=proposal_text
            )
        
        return None
    
    async def re_prompt_for_constraint(self, participant_name: str, choice: PrincipleChoice) -> str:
        """Generate re-prompt message for missing constraint."""
        constraint_type = "floor" if choice.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT else "range"
        
        # Use translated principle name for agent-facing re-prompt
        principle_name = self.language_manager.get_justice_principle_name(choice.principle.value)
        
        # Use English principle name for system logging
        english_principle_name = get_english_principle_name(choice.principle.value)
        logger.info(f"Re-prompting {participant_name} for missing constraint on {english_principle_name}")
        
        return self.language_manager.get_constraint_re_prompt(
            participant_name=participant_name,
            principle_name=principle_name,
            constraint_type=constraint_type
        )
    
    def _compile_principle_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for principle detection with comprehensive coverage."""
        return {
            # Order matters - more specific patterns first to avoid false matches
            'maximizing_average_floor_constraint': re.compile(
                r'(?:maximizing?.*?(?:average.*?(?:income\s+)?with.*?floor|average.*?floor).*?constraint|'
                r'average.*?(?:income\s+)?with.*?floor.*?constraint|'
                r'average.*?floor.*?constraint|'
                r'floor.*?constraint.*?average|'
                r'average.*?with.*?floor|'  # Added shorter version
                r'floor.*?constraint(?!.*range)|'  # Floor constraint but not range
                r'option\s*[(\[]?c[)\]]?)', 
                re.IGNORECASE
            ),
            'maximizing_average_range_constraint': re.compile(
                r'(?:maximizing?.*?(?:average.*?(?:income\s+)?with.*?range|average.*?range).*?constraint|'
                r'average.*?(?:income\s+)?with.*?range.*?constraint|'
                r'average.*?range.*?constraint|'
                r'range.*?constraint.*?average|'
                r'average.*?with.*?range|'  # Added shorter version
                r'range.*?constraint(?!.*floor)|'  # Range constraint but not floor
                r'option\s*[(\[]?d[)\]]?)', 
                re.IGNORECASE
            ),
            'maximizing_floor': re.compile(
                r'(?:maximizing?.*?(?:the\s+)?floor(?!\s+constraint)(?:\s+income)?|'
                r'floor(?!\s+constraint).*?(?:income|maximization)|'
                r'(?:the\s+)?floor(?!\s+constraint)(?!.*(?:with|constraint|range))|'
                r'option\s*[(\[]?a[)\]]?)(?!.*constraint)', 
                re.IGNORECASE
            ),
            'maximizing_average': re.compile(
                r'(?:maximizing?.*?(?:the\s+)?average(?!\s+(?:with|floor|range)|.*?constraint)(?:\s+income)?|'
                r'average(?!\s+(?:with|floor|range)|.*?constraint).*?(?:income|maximization)|'
                r'(?:the\s+)?average(?!\s+(?:with|floor|range))(?!.*(?:constraint|floor|range|with))|'
                r'option\s*[(\[]?b[)\]]?)(?!.*(?:constraint|floor|range|with))', 
                re.IGNORECASE
            )
        }
    
    def _compile_certainty_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for certainty level detection - order matters!"""
        return {
            # More specific patterns first to avoid false matches
            'very_sure': re.compile(r'very\s+sure|extremely\s+confident|highly\s+certain|completely\s+sure', re.IGNORECASE),
            'very_unsure': re.compile(r'very\s+unsure|extremely\s+uncertain|highly\s+uncertain', re.IGNORECASE),
            'sure': re.compile(r'(?<!very\s)(?<!extremely\s)(?<!highly\s)sure|confident|certain', re.IGNORECASE),
            'unsure': re.compile(r'(?<!very\s)(?<!extremely\s)(?<!highly\s)unsure|uncertain|not\s+confident', re.IGNORECASE),
            'no_opinion': re.compile(r'no\s+opinion|neutral|indifferent|no\s+preference', re.IGNORECASE)
        }
    
    def _compile_ranking_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for ranking detection."""
        return {
            'ranking_line': re.compile(r'(\d+)\.?\s*\*?\*?\s*(.*?)(?=\n\s*\d+\.|$)', re.MULTILINE | re.DOTALL),
            'rank_number': re.compile(r'(?:rank|position|place)?\s*(\d+)', re.IGNORECASE),
            'constraint_amount': re.compile(r'\$?(\d{1,3}(?:,\d{3})*|\d+)(?:\s*(?:dollars?|k|thousand))?', re.IGNORECASE)
        }
    
    async def parse_principle_choice_enhanced(self, response: str, max_retries: int = 3) -> PrincipleChoice:
        """Enhanced parsing for principle choice with retry logic."""
        
        for attempt in range(max_retries):
            try:
                # First try direct pattern matching
                choice_data = self._extract_principle_choice_direct(response)
                if choice_data:
                    return self._create_principle_choice(choice_data)
                
                # Fallback to agent-based parsing
                return await self.parse_principle_choice(response)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt - use more permissive parsing
                    return await self._parse_with_fallback(response, 'principle_choice')
                
                # Add clarifying context for retry
                response = f"Original response: {response}\n\nPlease clearly state your principle choice."
    
    def _extract_principle_choice_direct(self, response: str) -> Optional[Dict[str, Any]]:
        """Direct pattern matching for principle choice."""
        
        # Find principle
        principle = None
        for principle_key, pattern in self._principle_patterns.items():
            if pattern.search(response):
                principle = principle_key
                break
        
        if not principle:
            return None
        
        # Find constraint amount if needed
        constraint_amount = None
        if 'constraint' in principle:
            # Enhanced constraint amount parsing with multiple patterns
            constraint_amount = self._extract_constraint_amount_robust(response, principle)
        
        # Find certainty
        certainty = 'sure'  # default
        for certainty_key, pattern in self._certainty_patterns.items():
            if pattern.search(response):
                certainty = certainty_key
                break
        
        return {
            'principle': principle,
            'constraint_amount': constraint_amount,
            'certainty': certainty,
            'reasoning': response  # Full response as reasoning
        }
    
    def _create_principle_choice(self, data: Dict[str, Any]) -> PrincipleChoice:
        """Create PrincipleChoice object from extracted data."""
        principle = JusticePrinciple(data['principle'])
        constraint_amount = data.get('constraint_amount')
        
        # If constraint principle but no amount specified, try to parse from reasoning
        if (principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                         JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT] and
            constraint_amount is None):
            
            reasoning = data.get('reasoning', '')
            constraint_amount = self._extract_constraint_amount_robust(reasoning, principle.value)
        
        # Validate constraint amount before creating PrincipleChoice
        if (constraint_amount is not None and constraint_amount <= 0):
            constraint_amount = None  # Set to None to trigger retry logic
        
        return PrincipleChoice(
            principle=principle,
            constraint_amount=constraint_amount,
            certainty=CertaintyLevel(data['certainty']),
            reasoning=data.get('reasoning', '')
        )
    
    async def parse_principle_ranking_enhanced(self, response: str, max_retries: int = 3) -> PrincipleRanking:
        """Enhanced parsing for principle ranking with retry logic."""
        
        for attempt in range(max_retries):
            try:
                # First try direct pattern matching
                ranking_data = self._extract_ranking_direct(response)
                if ranking_data and len(ranking_data['rankings']) == 4:
                    return self._create_principle_ranking(ranking_data)
                
                # Fallback to agent-based parsing
                return await self.parse_principle_ranking(response)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt - use more permissive parsing
                    return await self._parse_with_fallback(response, 'principle_ranking')
                
                # Add clarifying context for retry
                response = f"Original response: {response}\n\nPlease provide a complete ranking of all 4 principles from 1-4."
    
    def _extract_ranking_direct(self, response: str) -> Optional[Dict[str, Any]]:
        """Direct pattern matching for principle ranking."""
        
        rankings = []
        
        # Look for numbered list format
        ranking_matches = self._ranking_patterns['ranking_line'].findall(response)
        
        if len(ranking_matches) >= 4:
            for rank_num, rank_text in ranking_matches[:4]:
                principle = self._identify_principle_in_text(rank_text.strip())
                if principle:
                    rankings.append({
                        'principle': principle,
                        'rank': int(rank_num)
                    })
        
        # Find overall certainty
        certainty = 'sure'  # default
        for certainty_key, pattern in self._certainty_patterns.items():
            if pattern.search(response):
                certainty = certainty_key
                break
        
        if len(rankings) == 4:
            return {
                'rankings': rankings,
                'certainty': certainty
            }
        
        return None
    
    def _identify_principle_in_text(self, text: str) -> Optional[str]:
        """Identify which principle is mentioned in text - focus on beginning of text."""
        # Focus on the first part of the text to avoid confusion from later mentions
        # Take first sentence or first 200 characters, whichever is shorter
        first_sentence = text.split(':')[0] if ':' in text else text.split('.')[0]
        focus_text = first_sentence[:200].strip()
        
        # The patterns are ordered from most specific to least specific
        # This ensures we match the correct principle even when text could match multiple patterns
        for principle_key, pattern in self._principle_patterns.items():
            if pattern.search(focus_text):
                return principle_key
        
        # Fallback to full text if focus text doesn't match
        for principle_key, pattern in self._principle_patterns.items():
            if pattern.search(text):
                return principle_key
                
        return None
    
    def _create_principle_ranking(self, data: Dict[str, Any]) -> PrincipleRanking:
        """Create PrincipleRanking object from extracted data."""
        rankings = []
        for ranking_data in data['rankings']:
            rankings.append(RankedPrinciple(
                principle=JusticePrinciple(ranking_data['principle']),
                rank=ranking_data['rank']
            ))
        
        return PrincipleRanking(
            rankings=rankings, 
            certainty=CertaintyLevel(data.get('certainty', 'sure'))
        )
    
    def _extract_constraint_amount_robust(self, response: str, principle: str) -> Optional[int]:
        """Enhanced constraint amount extraction with multiple patterns and fuzzy matching."""
        
        # Pattern 1: Direct amount matching with various formats (including negative detection)
        amount_patterns = [
            r'(-?\d{1,2})\s*k(?:\s|$)',  # Handle simple "20k" or "-20k" format first
            r'\$?(-?\d{1,3}(?:,\d{3})*)\s*(?:dollars?)?',  # $20,000, -20,000, or $-20,000
            r'(-?\d{1,3}(?:,\d{3})*)\s*(?:k|thousand)',    # 20k, -20k or 20 thousand
            r'floor\s*(?:of|at|set\s*at|=)?\s*\$?(-?\d{1,3}(?:,\d{3})*)', # floor of $20,000 or $-20,000
            r'constraint\s*(?:of|at|set\s*at|=)?\s*\$?(-?\d{1,3}(?:,\d{3})*)', # constraint of $20,000
            r'with\s*(?:a\s*)?floor\s*(?:of|at)?\s*\$?(-?\d{1,3}(?:,\d{3})*)', # with a floor of $20,000
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    
                    # Check if this is a "k" pattern (first pattern in our list)
                    if pattern == r'(\d{1,2})\s*k(?:\s|$)':
                        amount *= 1000
                    elif re.search(r'\b' + re.escape(match) + r'\s*(?:k|thousand)', response, re.IGNORECASE):
                        amount *= 1000
                    
                    # Convert to int and validate
                    amount_int = int(amount)
                    # Return None for invalid values to trigger retry logic
                    if amount_int <= 0:
                        continue
                    return amount_int
                except (ValueError, TypeError):
                    continue
        
        # Pattern 2: Contextual amount extraction (look for numbers near constraint keywords)
        constraint_context_patterns = [
            r'(?:floor|constraint|minimum|limit)[\s\w]*?\$?(-?\d{1,3}(?:,\d{3})*)',
            r'\$?(-?\d{1,3}(?:,\d{3})*)[\s\w]*?(?:floor|constraint|minimum|limit)',
            r'(?:principle|option)\s*[(\[]?[cd][)\]]?.*?\$?(-?\d{1,3}(?:,\d{3})*)',  # principle c/d with amount
            r'\$?(-?\d{1,3}(?:,\d{3})*).*?(?:principle|option)\s*[(\[]?[cd][)\]]?',  # amount with principle c/d
        ]
        
        for pattern in constraint_context_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                try:
                    amount = int(match.replace(',', ''))
                    # Reasonable range check (between $1,000 and $100,000) and positive
                    if 1000 <= amount <= 100000:
                        return amount
                except (ValueError, TypeError):
                    continue
        
        # Pattern 3: Fallback to abstract constraint parsing
        return self._parse_abstract_constraint(response, principle)
    
    def _parse_abstract_constraint(self, response: str, principle: str) -> Optional[int]:
        """Parse abstract constraint descriptions like 'practical maximum'."""
        response_lower = response.lower()
        
        # First check for negative numbers - if found, return None to trigger retry
        import re
        negative_patterns = [
            r'-\s*\$?\d+',  # -$1000 or -1000
            r'\$\s*-\s*\d+',  # $-1000
            r'negative\s+\d+',  # negative 1000
        ]
        for pattern in negative_patterns:
            if re.search(pattern, response_lower):
                return None  # Trigger retry for negative values
        
        # Look for abstract constraint terms
        if any(term in response_lower for term in [
            'practical maximum', 'practical max', 'highest possible',
            'maximum possible', 'as high as possible', 'optimal level',
            'best level', 'sweet spot'
        ]):
            # For practical maximum constraints, use a reasonable default
            if 'floor' in principle:
                return 10000  # $10,000 default floor constraint
            elif 'range' in principle:
                return 20000  # $20,000 default range constraint
        
        # Look for relative constraint terms  
        if any(term in response_lower for term in [
            'reasonable', 'moderate', 'middle', 'balanced'
        ]):
            if 'floor' in principle:
                return 8000   # $8,000 moderate floor
            elif 'range' in principle:
                return 15000  # $15,000 moderate range
        
        # Look for high/low terms
        if any(term in response_lower for term in ['high', 'strong', 'substantial']):
            if 'floor' in principle:
                return 12000  # $12,000 high floor
            elif 'range' in principle:
                return 25000  # $25,000 high range
        
        if any(term in response_lower for term in ['low', 'minimal', 'basic']):
            if 'floor' in principle:
                return 5000   # $5,000 low floor
            elif 'range' in principle:
                return 10000  # $10,000 low range
        
        # Default fallback for constraint principles
        if 'floor' in principle:
            return 10000  # Default $10,000 floor
        elif 'range' in principle:
            return 20000  # Default $20,000 range
        
        return None

    async def _parse_with_fallback(self, response: str, parse_type: str) -> Any:
        """Fallback parsing with more permissive approach."""
        
        if parse_type == 'principle_choice':
            # Create a basic choice if we can identify any principle
            for principle_key, pattern in self._principle_patterns.items():
                if pattern.search(response):
                    # Get constraint amount for constraint principles
                    constraint_amount = None
                    if 'constraint' in principle_key:
                        constraint_amount = self._extract_constraint_amount_robust(response, principle_key)
                        # Validate constraint amount - if invalid, set to None to trigger retry
                        if constraint_amount is not None and constraint_amount <= 0:
                            constraint_amount = None
                    
                    # For constraint principles with None constraint, use a temporary bypass
                    if ('constraint' in principle_key and constraint_amount is None):
                        # Create with temporary valid constraint that will pass Pydantic validation
                        temp_constraint = 1  # Temporary positive value to pass Pydantic validation
                        choice = PrincipleChoice(
                            principle=JusticePrinciple(principle_key),
                            constraint_amount=temp_constraint,
                            certainty=CertaintyLevel.SURE,
                            reasoning=response
                        )
                        # Override with None after creation to trigger retry logic
                        choice.constraint_amount = None
                        return choice
                    else:
                        return PrincipleChoice(
                            principle=JusticePrinciple(principle_key),
                            constraint_amount=constraint_amount,
                            certainty=CertaintyLevel.SURE,
                            reasoning=response
                        )
            
            # Ultimate fallback - default choice
            return PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.UNSURE,
                reasoning=response
            )
        
        elif parse_type == 'principle_ranking':
            # Create default ranking if parsing fails
            principles = list(JusticePrinciple)
            rankings = []
            for i, principle in enumerate(principles[:4]):
                rankings.append(RankedPrinciple(
                    principle=principle,
                    rank=i + 1
                ))
            
            return PrincipleRanking(
                rankings=rankings,
                certainty=CertaintyLevel.UNSURE
            )
        
        raise ValueError(f"Unknown parse type: {parse_type}")
    
    async def validate_and_retry_parse(self, response: str, parse_type: str, max_retries: int = 3) -> Any:
        """Validate parsed response and retry if needed."""
        
        for attempt in range(max_retries):
            try:
                if parse_type == 'principle_choice':
                    parsed = await self.parse_principle_choice_enhanced(response)
                    if await self.validate_constraint_specification(parsed):
                        return parsed
                elif parse_type == 'principle_ranking':
                    parsed = await self.parse_principle_ranking_enhanced(response)
                    if len(parsed.rankings) == 4:
                        return parsed
                
                # If validation failed, improve the response text for retry
                if attempt < max_retries - 1:
                    response = await self._improve_response_format(response, parse_type)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
        
        raise ValueError(f"Failed to parse and validate {parse_type} after {max_retries} attempts")
    
    async def _improve_response_format(self, response: str, parse_type: str) -> str:
        """Use parser agent to improve response format."""
        # Ensure utility agent is initialized
        await self.async_init()
        
        format_prompt = self._get_format_improvement_prompt(response, parse_type)
        result = await Runner.run(self.parser_agent, format_prompt)
        
        return result.final_output
    
    def _get_format_improvement_prompt(self, response: str, parse_type: str) -> str:
        """Get prompt for improving response format."""
        return self.language_manager.get_format_improvement_prompt(response, parse_type)