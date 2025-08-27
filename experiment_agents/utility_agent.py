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
        
        # Enhanced parsing patterns (keeping only ranking patterns)
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
    
    async def detect_agreement_multilingual(self, response: str) -> bool:
        """Multilingual agreement detection with context-aware negation handling.

        Rules:
        - Decisive agreement tokens (YES/I AGREE/LET'S VOTE/etc.) return True unless there is an explicit refusal.
        - Words like "NO" are NOT treated as refusal if part of domain phrases (e.g., "NO CONSTRAINTS").
        - If both agreement and ambiguous negation cues appear, defer to LLM fallback.
        - Empty or whitespace-only responses are always treated as disagreement.
        """
        await self.async_init()

        text = response.strip()
        
        # CRITICAL: Reject empty or whitespace-only responses immediately
        if not text or len(text) < 2:
            logger.info("Agreement detection: Empty or too short response - treating as disagreement")
            return False
            
        normalized = text.upper()

        # Agreement tokens (broad but decisive)
        agreement_tokens = [
            "YES", "I AGREE", "AGREED", "LET'S VOTE", "LETS VOTE", "READY TO VOTE",
            "LET'S PROCEED", "LETS PROCEED", "LET'S DO IT", "LETS DO IT",
            "SOUNDS GOOD", "THAT WORKS", "FINE WITH ME"
        ]

        # Explicit refusal patterns (word-boundary, short-window negations)
        refusal_regexes = [
            r"\bNO\b\s*(,|\.|$)",
            r"\bNO\b\s+(THANKS|NOT|NEED|TIME|VOTE|LATER|WAIT)",
            r"\bNOT\s+READY\b",
            r"\bNOT\s+YET\b",
            r"\bNEED\s+MORE\b",
            r"\bHOLD\s+ON\b",
            r"\bI\s+DISAGREE\b",
        ]

        # Domain phrases that must NOT flip agreement
        domain_exceptions = [
            r"\bNO\s+CONSTRAINTS?\b",
            r"\bNO\s+RANGE\b",
            r"\bNO\s+FLOOR\b",
        ]

        has_agree = any(tok in normalized for tok in agreement_tokens)

        # If text mentions "NO" but only in domain exceptions, do not treat as refusal
        mentions_no = " NO" in f" {normalized}" or normalized.startswith("NO")
        only_domain_no = False
        if mentions_no:
            only_domain_no = any(re.search(p, normalized) for p in domain_exceptions) and not any(
                re.search(rx, normalized) for rx in refusal_regexes
            )

        # Immediate decision: clear agreement without explicit refusal
        if has_agree and (not mentions_no or only_domain_no):
            logger.info("Direct agreement detected (decisive tokens, no explicit refusal)")
            return True

        # Check explicit refusal
        if any(re.search(rx, normalized) for rx in refusal_regexes):
            logger.info("Direct refusal detected via explicit patterns")
            return False

        # If ambiguous (e.g., both agree tokens and some non-exception NO), defer to LLM fallback
        language_manager = get_language_manager()
        detection_prompt = language_manager.get(
            "prompts.utility_agreement_detection_enhanced",
            response=response
        )

        result = await Runner.run(self.parser_agent, detection_prompt)
        llm_response = result.final_output.strip().upper()
        agrees = any(indicator in llm_response for indicator in ["AGREES", "AGREE", "YES"])
        logger.info(f"LLM agreement analysis: {llm_response} -> {agrees}")
        return agrees
    
    
    async def detect_vote_intention_enhanced(self, statement: str) -> Optional[str]:
        """Enhanced vote detection with robust pattern matching and semantic fallback."""
        await self.async_init()

        # First: Direct pattern matching for explicit vote phrases only
        vote_indicators = [
            r"\bi propose we vote\b",
            r"\blet'?s vote\b",
            r"\bcall for a vote\b",
            r"\btime to vote\b",
            r"\bready to vote\b",
            r"\bwe should vote\b",
            r"\bproceed with.*vote\b",
            r"\bconduct.*vote\b",
            r"\bformal.*vote\b",
            r"\bvote:?\s*i\b",  # "VOTE: I formally propose..."
            r"\bvoting request\b"
        ]

        # Exclude patterns that are NOT vote proposals
        exclusion_patterns = [
            r"\bshould we vote\?",                 # Questions
            r"\bwhat.*think",                      # What do you think?
            r"\bi'?m not sure",                    # Uncertainty
            r"\bneed more(\s+discussion)?\b",      # Need more discussion
            r"\bmore discussion\b",
            r"\blet me think\b",                   # Thinking statements
            r"\bi think we need\b",                # Need more discussion
            r"\bbefore (we )?moving to a vote\b",  # Hedged meta mentions
            r"\bbefore (we )?vote\b",
            r"\bnot\s+ready(\s+to\s+vote)?\b",
            r"\bnot\s+yet\b",
            r"\bwait\b|\bhold on\b",
            r"\blater\b",
            r"\bprefer to discuss\b|\bneed to discuss\b",
        ]
        
        statement_lower = statement.lower()
        
        # Check for exclusion patterns first
        for pattern in exclusion_patterns:
            if re.search(pattern, statement_lower):
                logger.info(f"Vote NOT detected due to exclusion pattern: {pattern}")
                return None
        
        # Check for explicit vote indicators
        for pattern in vote_indicators:
            if re.search(pattern, statement_lower):
                logger.info(f"Vote detected via direct pattern: {pattern}")
                return statement  # Direct pattern match found
        
        # Fallback: LLM-based semantic analysis (stricter acceptance)
        language_manager = get_language_manager()
        detection_prompt = language_manager.get(
            "prompts.utility_vote_detection_enhanced",
            statement=statement
        )

        result = await Runner.run(self.parser_agent, detection_prompt)
        response = result.final_output.strip().upper()

        # Accept only explicit detection tokens; avoid overly broad matches like "YES" or "VOTING"
        voting_indicators = [
            "VOTING_INTENT_DETECTED",
            "VOTE_DETECTED",
            "VOTE DETECTED",
            "EXPLICIT_VOTE_INTENT",
        ]
        if any(indicator in response for indicator in voting_indicators):
            logger.info(f"Vote detected via LLM analysis: {response}")
            return statement

        logger.info(f"No vote detected. LLM response: {response}")
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
    
    
    
    def _compile_ranking_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for ranking detection."""
        return {
            'ranking_line': re.compile(r'(\d+)\.?\s*\*?\*?\s*(.*?)(?=\n\s*\d+\.|$)', re.MULTILINE | re.DOTALL),
            'rank_number': re.compile(r'(?:rank|position|place)?\s*(\d+)', re.IGNORECASE),
            'constraint_amount': re.compile(r'\$?(\d{1,3}(?:,\d{3})*|\d+)(?:\s*(?:dollars?|k|thousand))?', re.IGNORECASE)
        }
    
    async def parse_principle_choice_enhanced(self, response: str, max_retries: int = 3) -> PrincipleChoice:
        """Enhanced parsing for principle choice using LLM-based parsing (replaces regex)."""
        
        for attempt in range(max_retries):
            try:
                # Use new LLM-based parsing instead of regex
                choice_data = await self.parse_principle_choice_llm(response)
                if choice_data:
                    # Convert LLM response to PrincipleChoice
                    return PrincipleChoice.create_for_parsing(
                        principle=JusticePrinciple(choice_data['principle']),
                        constraint_amount=choice_data.get('constraint_amount'),
                        certainty=CertaintyLevel(choice_data['certainty']),
                        reasoning=choice_data.get('reasoning', response)
                    )
                
                # Fallback to original agent-based parsing if LLM parsing fails
                return await self.parse_principle_choice(response)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt - use more permissive parsing
                    return await self._parse_with_fallback(response, 'principle_choice')
                
                # Add clarifying context for retry
                response = f"Original response: {response}\n\nPlease clearly state your principle choice."
    
    
    def _create_principle_choice(self, data: Dict[str, Any]) -> PrincipleChoice:
        """Create PrincipleChoice object from extracted data using parsing mode."""
        principle = JusticePrinciple(data['principle'])
        constraint_amount = data.get('constraint_amount')
        
        # If constraint principle but no amount specified, try to parse from reasoning
        if (principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                         JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT] and
            constraint_amount is None):
            
            reasoning = data.get('reasoning', '')
            constraint_amount = self._extract_constraint_amount_robust(reasoning, principle.value)
        
        # Validate constraint amount range
        if constraint_amount is not None and constraint_amount <= 0:
            constraint_amount = None  # Set to None for retry logic
        
        # Create in parsing mode to avoid validation during creation
        return PrincipleChoice.create_for_parsing(
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
                ranking_data = await self._extract_ranking_direct(response)
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
    
    async def _extract_ranking_direct(self, response: str) -> Optional[Dict[str, Any]]:
        """Direct pattern matching for principle ranking using LLM-based parsing."""
        
        rankings = []
        
        # Look for numbered list format
        ranking_matches = self._ranking_patterns['ranking_line'].findall(response)
        
        if len(ranking_matches) >= 4:
            for rank_num, rank_text in ranking_matches[:4]:
                principle = await self._identify_principle_in_text(rank_text.strip())
                if principle:
                    rankings.append({
                        'principle': principle,
                        'rank': int(rank_num)
                    })
        
        # Find overall certainty - use simple heuristic
        certainty = 'sure'  # default
        response_lower = response.lower()
        if any(word in response_lower for word in ['very unsure', 'extremely uncertain']):
            certainty = 'very_unsure'
        elif any(word in response_lower for word in ['unsure', 'uncertain', 'not sure']):
            certainty = 'unsure'  
        elif any(word in response_lower for word in ['no opinion', 'neutral', 'indifferent']):
            certainty = 'no_opinion'
        elif any(word in response_lower for word in ['very sure', 'very confident', 'extremely confident']):
            certainty = 'very_sure'
        
        if len(rankings) == 4:
            return {
                'rankings': rankings,
                'certainty': certainty
            }
        
        return None
    
    async def _identify_principle_in_text(self, text: str) -> Optional[str]:
        """Identify which principle is mentioned in text using LLM-based parsing."""
        # Focus on the first part of the text to avoid confusion from later mentions
        # Take first sentence or first 200 characters, whichever is shorter
        first_sentence = text.split(':')[0] if ':' in text else text.split('.')[0]
        focus_text = first_sentence[:200].strip()
        
        # Try LLM-based parsing on focused text first
        try:
            choice_data = await self.parse_principle_choice_llm(focus_text, max_retries=1)
            if choice_data:
                return choice_data['principle']
        except Exception:
            pass
        
        # Fallback to full text LLM parsing if focus text doesn't work
        try:
            choice_data = await self.parse_principle_choice_llm(text, max_retries=1)
            if choice_data:
                return choice_data['principle']
        except Exception:
            pass
                
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
    
    

    async def _parse_with_fallback(self, response: str, parse_type: str) -> Any:
        """Fallback parsing with more permissive approach using LLM instead of regex."""
        
        if parse_type == 'principle_choice':
            # Try LLM-based parsing as fallback
            try:
                choice_data = await self.parse_principle_choice_llm(response, max_retries=1)
                if choice_data:
                    return PrincipleChoice.create_for_parsing(
                        principle=JusticePrinciple(choice_data['principle']),
                        constraint_amount=choice_data.get('constraint_amount'),
                        certainty=CertaintyLevel(choice_data['certainty']),
                        reasoning=response
                    )
            except Exception:
                pass
            
            # Ultimate fallback - default choice using parsing mode
            return PrincipleChoice.create_for_parsing(
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
    
    # ========================================
    # NEW LLM-BASED PARSING METHODS
    # ========================================
    
    async def parse_principle_choice_llm(self, response: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Parse principle choice using LLM instead of regex patterns.
        This replaces the messy regex-based _extract_principle_choice_direct method.
        
        Args:
            response: The participant's response to analyze
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict with principle, constraint_amount, certainty, confidence, or None if parsing fails
        """
        await self.async_init()
        
        for attempt in range(max_retries):
            try:
                # Get the LLM parsing prompt
                parsing_prompt = self.language_manager.get(
                    "prompts.utility_llm_parse_principle_choice",
                    response=response,
                    attempt=attempt + 1
                )
                
                result = await Runner.run(self.parser_agent, parsing_prompt)
                response_text = result.final_output.strip()
                
                # Parse structured LLM response
                parsed_data = self._parse_llm_principle_response(response_text)
                if parsed_data:
                    return parsed_data
                    
            except Exception as e:
                logger.warning(f"LLM principle parsing failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                    
        return None
    
    def _parse_llm_principle_response(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Parse structured LLM response for principle choice."""
        import re
        try:
            # Look for structured response format
            if "PRINCIPLE_DETECTED:" in llm_response:
                content = llm_response.split("PRINCIPLE_DETECTED:")[1].strip()
                
                # Extract principle
                principle = None
                principle_map = {
                    # Order matters! Check longer, more specific patterns first
                    "maximizing_average_floor_constraint": "maximizing_average_floor_constraint",
                    "maximizing_average_range_constraint": "maximizing_average_range_constraint",
                    "maximizing_floor": "maximizing_floor",
                    "maximizing_average": "maximizing_average",
                    "principle c": "maximizing_average_floor_constraint", 
                    "principle d": "maximizing_average_range_constraint",
                    "principle a": "maximizing_floor",
                    "principle b": "maximizing_average",
                    "option c": "maximizing_average_floor_constraint",
                    "option d": "maximizing_average_range_constraint",
                    "option a": "maximizing_floor",
                    "option b": "maximizing_average",
                    "c": "maximizing_average_floor_constraint",
                    "d": "maximizing_average_range_constraint",
                    "a": "maximizing_floor",
                    "b": "maximizing_average"
                }
                
                content_lower = content.lower()
                for key, value in principle_map.items():
                    if key in content_lower:
                        principle = value
                        break
                
                if not principle:
                    return None
                
                # Extract constraint amount if applicable
                constraint_amount = None
                if 'constraint' in principle:
                    # Look for dollar amounts
                    amount_matches = re.findall(r'[\$]?(\d{1,6}(?:,\d{3})*|\d{4,6})', content)
                    if amount_matches:
                        try:
                            constraint_amount = int(amount_matches[0].replace(',', ''))
                            if constraint_amount <= 0:
                                constraint_amount = None
                        except ValueError:
                            pass
                
                # Extract confidence (0.0-1.0)
                confidence = 0.8  # Default confidence
                confidence_matches = re.findall(r'confidence[:\s]*([0-9]\.[0-9]+)', content_lower)
                if confidence_matches:
                    try:
                        confidence = float(confidence_matches[0])
                        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
                    except ValueError:
                        pass
                
                # Extract certainty level
                certainty = 'sure'  # Default
                if any(word in content_lower for word in ['very_unsure', 'very unsure']):
                    certainty = 'very_unsure'
                elif any(word in content_lower for word in ['unsure', 'uncertain']):
                    certainty = 'unsure'
                elif any(word in content_lower for word in ['no_opinion', 'no opinion']):
                    certainty = 'no_opinion'
                elif any(word in content_lower for word in ['very_sure', 'very sure']):
                    certainty = 'very_sure'
                
                return {
                    'principle': principle,
                    'constraint_amount': constraint_amount,
                    'certainty': certainty,
                    'confidence': confidence,
                    'reasoning': llm_response
                }
                
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse LLM principle response: {e}")
            return None
    
    async def parse_preference_statement_llm(self, statement: str) -> Optional[PrincipleChoice]:
        """
        Parse preference statements for SIMPLE MODE using LLM instead of regex.
        This replaces regex-based preference detection.
        
        Args:
            statement: The participant's statement to analyze
            
        Returns:
            PrincipleChoice if preference is detected, None otherwise
        """
        await self.async_init()
        
        try:
            # Get the LLM preference detection prompt
            detection_prompt = self.language_manager.get(
                "prompts.utility_llm_parse_preference_statement",
                statement=statement
            )
            
            result = await Runner.run(self.parser_agent, detection_prompt)
            response_text = result.final_output.strip()
            
            # Parse LLM response
            if "PREFERENCE_DETECTED:" in response_text:
                preference_content = response_text.split("PREFERENCE_DETECTED:")[1].strip()
                
                # Use the principle choice parser to extract details
                parsed_data = self._parse_llm_principle_response(f"PRINCIPLE_DETECTED: {preference_content}")
                if parsed_data:
                    return PrincipleChoice.create_for_parsing(
                        principle=JusticePrinciple(parsed_data['principle']),
                        constraint_amount=parsed_data.get('constraint_amount'),
                        certainty=CertaintyLevel(parsed_data['certainty']),
                        reasoning=f"Preference detected via LLM: {preference_content}"
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM preference detection failed: {e}")
            return None
    
    async def parse_vote_intention_llm(self, statement: str) -> Optional[str]:
        """
        Parse vote intention for COMPLEX MODE using LLM instead of regex.
        This replaces regex-based voting detection.
        
        Args:
            statement: The participant's statement to analyze
            
        Returns:
            Vote intention description if detected, None otherwise
        """
        await self.async_init()
        
        try:
            # Get the LLM vote detection prompt
            detection_prompt = self.language_manager.get(
                "prompts.utility_llm_parse_vote_intention", 
                statement=statement
            )
            
            result = await Runner.run(self.parser_agent, detection_prompt)
            response_text = result.final_output.strip()
            
            # Parse LLM response
            if "VOTE_INTENTION_DETECTED:" in response_text:
                vote_content = response_text.split("VOTE_INTENTION_DETECTED:")[1].strip()
                return vote_content
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM vote intention detection failed: {e}")
            return None
    
    async def parse_constraint_amount_llm(self, response: str, principle: str) -> Optional[int]:
        """
        Parse constraint amounts using LLM instead of complex regex patterns.
        This replaces _extract_constraint_amount_robust method.
        
        Args:
            response: The participant's response containing constraint amount
            principle: The principle type (for context)
            
        Returns:
            Constraint amount in dollars, or None if not found/invalid
        """
        await self.async_init()
        
        try:
            # Get the LLM constraint parsing prompt
            parsing_prompt = self.language_manager.get(
                "prompts.utility_llm_parse_constraint_amount",
                response=response,
                principle=principle
            )
            
            result = await Runner.run(self.parser_agent, parsing_prompt)
            response_text = result.final_output.strip()
            
            # Parse LLM response
            if "CONSTRAINT_AMOUNT:" in response_text:
                amount_text = response_text.split("CONSTRAINT_AMOUNT:")[1].strip()
                
                # Extract numeric value
                import re
                amount_matches = re.findall(r'(\d{1,6}(?:,\d{3})*|\d{4,6})', amount_text)
                if amount_matches:
                    try:
                        amount = int(amount_matches[0].replace(',', ''))
                        # Validate reasonable range (between $1,000 and $100,000)
                        if 1000 <= amount <= 100000:
                            return amount
                    except ValueError:
                        pass
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM constraint amount parsing failed: {e}")
            return None
    
    async def detect_preference_statement(self, statement: str) -> Optional[PrincipleChoice]:
        """
        Detect preference statements in participant responses for SIMPLE MODE only.
        This method is re-enabled specifically for simple mode consensus detection.
        
        Args:
            statement: The participant's statement to analyze
            
        Returns:
            PrincipleChoice if preference is detected, None otherwise
        """
        await self.async_init()
        
        # Enhanced preference detection patterns
        preference_patterns = [
            r'\bmy\s+preference\s+is\s+([a-d]|principle\s+[a-d]|maximizing[^.]*?)(?:\s+with\s+(?:a\s+)?(?:floor|range)\s+constraint\s+of\s+\$?([0-9,]+))?',
            r'\bi\s+prefer\s+([a-d]|principle\s+[a-d]|maximizing[^.]*?)(?:\s+with\s+(?:a\s+)?(?:floor|range)\s+constraint\s+of\s+\$?([0-9,]+))?',
            r'\bi\s+choose\s+([a-d]|principle\s+[a-d]|maximizing[^.]*?)(?:\s+with\s+(?:a\s+)?(?:floor|range)\s+constraint\s+of\s+\$?([0-9,]+))?',
            r'\bi\s+support\s+([a-d]|principle\s+[a-d]|maximizing[^.]*?)(?:\s+with\s+(?:a\s+)?(?:floor|range)\s+constraint\s+of\s+\$?([0-9,]+))?',
            r'\bpreference:\s*([a-d]|principle\s+[a-d]|maximizing[^.]*?)(?:\s+with\s+(?:a\s+)?(?:floor|range)\s+constraint\s+of\s+\$?([0-9,]+))?',
            r'\bchoice:\s*([a-d]|principle\s+[a-d]|maximizing[^.]*?)(?:\s+with\s+(?:a\s+)?(?:floor|range)\s+constraint\s+of\s+\$?([0-9,]+))?'
        ]
        
        statement_lower = statement.lower().strip()
        
        # Try pattern matching first
        for pattern in preference_patterns:
            matches = re.findall(pattern, statement_lower)
            if matches:
                match = matches[0]
                principle_text = match[0] if isinstance(match, tuple) else match
                constraint_amount = None
                
                if isinstance(match, tuple) and len(match) > 1 and match[1]:
                    try:
                        constraint_amount = int(match[1].replace(',', ''))
                    except (ValueError, AttributeError):
                        pass
                
                # Map principle text to JusticePrinciple
                principle = await self._extract_principle_from_text(principle_text)
                if principle:
                    return PrincipleChoice(
                        principle=principle,
                        constraint_amount=constraint_amount,
                        certainty=CertaintyLevel.NO_OPINION,  # Default certainty
                        reasoning="Preference detected via pattern matching"
                    )
        
        # Fallback to LLM-based detection if patterns fail
        try:
            language_manager = get_language_manager()
            detection_prompt = language_manager.get(
                "prompts.utility_preference_detection",
                statement=statement
            )
            
            result = await Runner.run(self.parser_agent, detection_prompt)
            response = result.final_output.strip().upper()
            
            if "PREFERENCE_DETECTED:" in response:
                # Parse the LLM response to extract principle choice
                preference_text = response.split("PREFERENCE_DETECTED:")[1].strip()
                principle = await self._extract_principle_from_text(preference_text)
                
                if principle:
                    # Extract constraint amount if present
                    constraint_match = re.search(r'\$?([0-9,]+)', preference_text)
                    constraint_amount = None
                    if constraint_match:
                        try:
                            constraint_amount = int(constraint_match.group(1).replace(',', ''))
                        except ValueError:
                            pass
                    
                    return PrincipleChoice(
                        principle=principle,
                        constraint_amount=constraint_amount,
                        certainty=CertaintyLevel.NO_OPINION,
                        reasoning="Preference detected via LLM analysis"
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM preference detection failed: {e}")
            return None
    
    def _map_identifier_to_principle(self, identifier: str) -> Optional[JusticePrinciple]:
        """Map principle identifier (a, b, c, d, principle a, etc.) to JusticePrinciple."""
        identifier = identifier.lower().strip()
        
        # Remove common prefixes
        identifier = re.sub(r'^(principle|principio|原则)\s*', '', identifier)
        
        mapping = {
            # Letter-based identifiers
            'a': JusticePrinciple.MAXIMIZING_FLOOR,
            'b': JusticePrinciple.MAXIMIZING_AVERAGE,
            'c': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'd': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # English full names
            'maximizing_floor': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing_average': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing_average_floor_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximizing_average_range_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Chinese principle names
            '最大化最低收入': JusticePrinciple.MAXIMIZING_FLOOR,
            '最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE,
            '在最低收入约束条件下最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            '在范围约束条件下最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Spanish principle names (for completeness)
            'maximización del ingreso mínimo': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximización del ingreso promedio': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximización del ingreso promedio bajo restricción de ingreso mínimo': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximización del ingreso promedio bajo restricción de rango': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        }
        
        return mapping.get(identifier)
    
    async def _extract_principle_from_text(self, principle_text: str) -> Optional[JusticePrinciple]:
        """
        Extract JusticePrinciple from text using LLM-based parsing instead of regex.
        This replaces the old regex-based pattern matching approach.
        """
        principle_text = principle_text.lower().strip()
        
        # First try the letter-based mapping (still useful for simple cases)
        mapped_principle = self._map_identifier_to_principle(principle_text)
        if mapped_principle:
            return mapped_principle
        
        # Use LLM parsing for more complex text analysis
        try:
            choice_data = await self.parse_principle_choice_llm(principle_text, max_retries=1)
            if choice_data:
                return JusticePrinciple(choice_data['principle'])
        except Exception:
            pass
        
        return None
    
    def _extract_constraint_amount_flexible(self, statement: str) -> Optional[int]:
        """
        Flexible constraint amount extraction supporting various formats:
        14,000 | 14.000 | 14000 | $14000 | $ 14000 | 14k | etc.
        """
        # Multiple patterns for flexible amount parsing
        amount_patterns = [
            r'\$\s*(\d{1,3}(?:[.,]\d{3})*(?:\.\d{2})?)',  # $14,000 or $14.000 or $ 14000
            r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:dollars?|\$)',  # 14,000 dollars or 14000$
            r'(\d{1,2})\s*k(?:\s|$|\.)',  # 14k
            r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:thousand)',  # 14 thousand
            r'(\d{1,3}(?:[.,]\d{3})*)(?!\s*[%])',  # Plain numbers (avoid percentages)
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, statement, re.IGNORECASE)
            for match in matches:
                try:
                    # Normalize the amount string
                    amount_str = match.replace(',', '').replace('.', '')
                    
                    # Special handling for different decimal separators
                    if '.' in match and len(match.split('.')[-1]) <= 3:
                        # If there's a dot with 3 or fewer digits after, treat as thousands separator
                        amount_str = match.replace('.', '')
                    
                    amount = float(amount_str)
                    
                    # Check if this is a "k" pattern
                    if 'k' in statement.lower() and amount < 1000:
                        amount *= 1000
                    elif 'thousand' in statement.lower() and amount < 1000:
                        amount *= 1000
                    
                    amount_int = int(amount)
                    
                    # Validate reasonable range
                    if 1000 <= amount_int <= 100000:
                        return amount_int
                        
                except (ValueError, TypeError):
                    continue
        
        return None
    
    async def _detect_preference_via_llm(self, statement: str) -> Optional[PrincipleChoice]:
        """Use LLM to detect preference when pattern matching fails."""
        language_manager = get_language_manager()
        
        # Get preference detection prompt from language manager
        detection_prompt = language_manager.get(
            "prompts.utility_preference_detection",
            statement=statement
        )
        
        try:
            result = await Runner.run(self.parser_agent, detection_prompt)
            response = result.final_output.strip()
            
            # Parse LLM response
            if "PREFERENCE_DETECTED:" in response:
                preference_text = response.split("PREFERENCE_DETECTED:")[1].strip()
                return await self.parse_principle_choice_enhanced(preference_text)
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM preference detection failed: {e}")
            return None
    
    def check_preference_consensus(self, preferences: List[PrincipleChoice]) -> tuple[bool, Optional[PrincipleChoice], List[str]]:
        """
        DEPRECATED: This method is deprecated. Use check_preference_consensus_simple_mode() instead.
        This method now always returns no consensus to enforce mode separation.
        
        Legacy method kept for backward compatibility.
        """
        # CONSENSUS CLEANUP: Always return no consensus - use mode-specific methods
        return False, None, ["Use check_preference_consensus_simple_mode() for simple mode or check_ballot_consensus() for complex mode"]
    
    def check_preference_consensus_simple_mode(self, preferences: List[PrincipleChoice]) -> tuple[bool, Optional[PrincipleChoice], List[str]]:
        """
        Check if preference statements reached consensus in SIMPLE MODE ONLY.
        This method is specifically isolated for simple mode operation.
        
        Args:
            preferences: List of participant preference choices
            
        Returns:
            Tuple of (consensus_reached, agreed_choice, warnings)
        """
        if not preferences:
            return False, None, ["No preferences received"]
        
        # Group preferences by principle and constraint amount (same logic as ballot consensus)
        preference_groups = {}
        warnings = []
        
        for preference in preferences:
            # Create key for grouping (principle + constraint amount)
            key = (preference.principle.value, preference.constraint_amount)
            
            if key not in preference_groups:
                preference_groups[key] = []
            preference_groups[key].append(preference)
            
            # Check for missing constraint amounts
            if (preference.constraint_amount is None and 
                preference.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                       JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
                warnings.append(f"Preference missing constraint amount for {preference.principle.value}")
        
        # Check for consensus (all preferences in same group)
        if len(preference_groups) == 1:
            agreed_choice = list(preference_groups.values())[0][0]  # First preference in the single group
            return True, agreed_choice, warnings
        
        return False, None, warnings
    
    async def validate_consensus_against_discussion(self, discussion_content: str, consensus_principle: str) -> tuple[bool, List[str]]:
        """
        Validate that the recorded consensus aligns with the discussion content.
        Returns (is_valid, warnings_list)
        """
        warnings = []
        
        # Use LLM to analyze discussion content for principle preferences
        language_manager = get_language_manager()
        
        validation_prompt = language_manager.get(
            "prompts.utility_consensus_validation",
            discussion_content=discussion_content,
            consensus_principle=consensus_principle
        )
        
        try:
            result = await Runner.run(self.parser_agent, validation_prompt)
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
    
    def check_ballot_consensus(self, ballots: List[PrincipleChoice]) -> tuple[bool, Optional[PrincipleChoice], List[str]]:
        """
        Check if secret ballots reached consensus. 
        Reuses logic from existing check_preference_consensus but for secret ballots.
        """
        if not ballots:
            return False, None, ["No ballots received"]
        
        # Group ballots by principle and constraint amount  
        ballot_groups = {}
        warnings = []
        
        for ballot in ballots:
            # Create key for grouping (principle + constraint amount)
            key = (ballot.principle.value, ballot.constraint_amount)
            
            if key not in ballot_groups:
                ballot_groups[key] = []
            ballot_groups[key].append(ballot)
            
            # Check for missing constraint amounts
            if (ballot.constraint_amount is None and 
                ballot.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                   JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
                warnings.append(f"Ballot missing constraint amount for {ballot.principle.value}")
        
        # Check for consensus (all ballots in same group)
        if len(ballot_groups) == 1:
            agreed_choice = list(ballot_groups.values())[0][0]  # First ballot in the single group
            return True, agreed_choice, warnings
        
        return False, None, warnings
