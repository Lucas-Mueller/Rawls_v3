"""
Utility agent for parsing and validating participant responses.
"""
import asyncio
import logging
import re
import os
from typing import Optional, Dict, Any, List
from agents import Agent, Runner, AgentOutputSchema, set_tracing_disabled

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


async def run_without_tracing(agent, prompt, context=None):
    """Run agent without tracing to prevent utility agent operations from being traced."""
    # Temporarily disable tracing
    set_tracing_disabled(True)
    try:
        result = await Runner.run(agent, prompt, context=context)
        return result
    finally:
        # Re-enable tracing
        set_tracing_disabled(False)


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
        
        # Save current tracing state
        tracing_was_disabled = False
        try:
            # Temporarily disable tracing for utility agent creation
            set_tracing_disabled(True)
            tracing_was_disabled = True
            
            logger.info(f"Creating utility agents with model: {self.utility_model} (tracing disabled)")
            
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
        finally:
            # Re-enable tracing for participant agents
            if tracing_was_disabled:
                set_tracing_disabled(False)
            
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
            result = await run_without_tracing(self.parser_agent, parse_prompt)
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
            result = await run_without_tracing(self.parser_agent, parse_prompt)
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
        
        result = await run_without_tracing(self.parser_agent, detection_prompt)
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
            # Chinese disagreement patterns
            r"不，我不同意",
            r"不同意",
            r"不，不",
            r"我不同意",
        ]

        # Domain phrases that must NOT flip agreement
        domain_exceptions = [
            r"\bNO\s+CONSTRAINTS?\b",
            r"\bNO\s+RANGE\b",
            r"\bNO\s+FLOOR\b",
        ]

        has_agree = any(tok in normalized for tok in agreement_tokens)

        # Check for refusal patterns (English "NO" and Chinese "不")
        mentions_refusal = (" NO" in f" {normalized}" or normalized.startswith("NO") or 
                          "不" in text)  # Check original text for Chinese characters
        only_domain_no = False
        if mentions_refusal:
            # Check if it's only domain exceptions and not explicit refusal
            only_domain_no = any(re.search(p, normalized) for p in domain_exceptions) and not any(
                re.search(rx, text) for rx in refusal_regexes  # Check against original text for Chinese
            )

        # Immediate decision: clear agreement without explicit refusal
        if has_agree and (not mentions_refusal or only_domain_no):
            logger.info("Direct agreement detected (decisive tokens, no explicit refusal)")
            return True

        # Check explicit refusal - use appropriate text for each pattern
        for rx in refusal_regexes:
            # Chinese patterns should be checked against original text
            if any(chinese_char in rx for chinese_char in ['不', '我', '同意']):
                if re.search(rx, text):
                    logger.info(f"Direct refusal detected via Chinese pattern: {rx}")
                    return False
            # English patterns against normalized text
            else:
                if re.search(rx, normalized):
                    logger.info(f"Direct refusal detected via English pattern: {rx}")
                    return False

        # If ambiguous (e.g., both agree tokens and some non-exception NO), defer to LLM fallback
        language_manager = get_language_manager()
        detection_prompt = language_manager.get(
            "prompts.utility_agreement_detection_enhanced",
            response=response
        )

        result = await run_without_tracing(self.parser_agent, detection_prompt)
        llm_response = result.final_output.strip().upper()
        agrees = any(indicator in llm_response for indicator in ["AGREES", "AGREE", "YES"])
        logger.info(f"LLM agreement analysis: {llm_response} -> {agrees}")
        return agrees
    
    
    async def detect_vote_intention_enhanced(self, statement: str) -> Optional[str]:
        """
        Enhanced vote detection using LLM-first approach with exclusion patterns.
        Detects when participants want to trigger formal voting in discussions.
        """
        await self.async_init()

        statement_lower = statement.lower().strip()
        
        # FIRST: Apply exclusion patterns that prevent false positives
        exclusion_patterns = [
            r"\bshould we vote\s+(later|tomorrow|next)\b",  # Future timing
            r"\bdo you think we should vote\b",             # Opinion questions
            r"\bwhen should we vote\b",                     # Timing questions  
            r"\bhow should we vote\b",                      # Method questions
            r"\bwhat if we vote\b",                         # Hypothetical
            r"\bnot ready to vote\b",                       # Explicit rejection
            r"\bneed more discussion\b",                    # Discussion priority
            r"\bwe need to discuss more\b",                 # Discussion priority
            r"\bbefore we vote\b",                          # Conditional timing
            r"\bafter we vote\b",                           # Future reference
            r"\bif we vote\b",                              # Conditional
            r"\bunless we vote\b",                          # Conditional
            r"\bwe voted\b",                                # Past reference
            r"\bwill vote\b",                               # Future reference
            r"\bmight vote\b",                              # Uncertain future
            r"\bmaybe we should vote\b",                    # Uncertainty
            r"\bwe could vote\b",                           # Possibility
            r"\bvoting would be good\b",                    # Conditional
        ]
        
        # Return early if exclusion patterns match
        for pattern in exclusion_patterns:
            if re.search(pattern, statement_lower):
                logger.info(f"Vote intention excluded by pattern: {pattern}")
                return None

        # PRIMARY: LLM-based vote intention detection
        try:
            # Improved prompt for vote intention detection with broader scope
            vote_detection_prompt = f"""
Analyze this statement to determine if the speaker is expressing intention or readiness to proceed with voting or decision-making.

Statement: "{statement}"

DETECT VOTE_INTENTION when the speaker:
1. PROPOSES voting/decision action: "Let's vote", "I propose we vote", "We should vote now"
2. SIGNALS READINESS for voting: "Ready to vote", "Time to vote", "Time for the vote"
3. INDICATES SEQUENCE/TIMING: "Voting is the next step", "Now we vote", "Let's move to voting"
4. SEEKS AGREEMENT to vote: "Should we vote?", "Can we vote now?"
5. DECLARES DECISION PHASE: "Time to decide", "Let's make our decision", "Ready to decide"

DO NOT DETECT when the speaker:
- Asks WHEN/HOW to vote without proposing action: "When should we vote?", "How should we vote?"
- Expresses UNCERTAINTY: "Maybe we should vote", "We might vote", "We could vote"
- Refers to PAST/FUTURE without immediate intent: "We voted before", "We will vote later"
- Seeks MORE DISCUSSION: "We need more discussion", "Let's think about voting"
- Makes CONDITIONAL statements: "If we vote", "Unless we vote"

EXAMPLES:
✓ "Let's vote" → VOTE_INTENTION_DETECTED
✓ "Time for the vote" → VOTE_INTENTION_DETECTED  
✓ "Voting is the next step" → VOTE_INTENTION_DETECTED
✓ "Should we vote?" → VOTE_INTENTION_DETECTED
✓ "Ready to decide" → VOTE_INTENTION_DETECTED
✗ "Maybe we should vote" → NO_VOTE_INTENTION
✗ "When should we vote?" → NO_VOTE_INTENTION
✗ "We need more discussion" → NO_VOTE_INTENTION
✗ "Random unrelated statement" → NO_VOTE_INTENTION

Response format - respond with EXACTLY one of these:
VOTE_INTENTION_DETECTED
NO_VOTE_INTENTION

Response:"""

            result = await run_without_tracing(self.parser_agent, vote_detection_prompt)
            response = result.final_output.strip()
            
            # Parse response - trust the LLM's analysis
            if response == "VOTE_INTENTION_DETECTED" or (response.startswith("VOTE_DETECTED") and not response.startswith("NO_VOTE_DETECTED")):
                logger.info(f"Vote intention detected via LLM analysis: {statement}")
                return statement
            elif response == "NO_VOTE_INTENTION" or response.startswith("NO_VOTE_DETECTED"):
                logger.info(f"No vote intention detected via LLM: {statement}")
                return None
            else:
                # Log unexpected response and treat as no detection
                logger.warning(f"Unexpected LLM vote detection response: '{response}' - treating as NO_VOTE_INTENTION")
                return None
                
        except Exception as e:
            logger.warning(f"LLM vote detection failed: {e}")
        
        # MINIMAL FALLBACK: Only most obvious cases when LLM fails
        # This should rarely be used if LLM is working properly
        obvious_vote_patterns = [
            r"\blet'?s vote\b",
            r"\btime to vote\b",
            r"\bready to vote\b",
        ]
        
        statement_lower = statement.lower().strip()
        for pattern in obvious_vote_patterns:
            if re.search(pattern, statement_lower):
                logger.info(f"Vote detected via obvious pattern: {pattern}")
                return statement
        
        # No vote intention detected
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
        """Compile regex patterns for ranking detection only."""
        return {
            'ranking_line': re.compile(r'(\d+)\.?\s*\*?\*?\s*(.*?)(?=\n\s*\d+\.|$)', re.MULTILINE | re.DOTALL),
            'rank_number': re.compile(r'(?:rank|position|place)?\s*(\d+)', re.IGNORECASE)
        }
    
    async def parse_principle_choice_enhanced(self, response: str, max_retries: int = 3) -> PrincipleChoice:
        """Streamlined principle choice parsing using JSON-based LLM approach."""
        
        for attempt in range(max_retries):
            try:
                # Primary method: Use JSON-based LLM parsing
                choice_data = await self.parse_principle_choice_llm(response)
                if choice_data:
                    return PrincipleChoice.create_for_parsing(
                        principle=JusticePrinciple(choice_data['principle']),
                        constraint_amount=choice_data.get('constraint_amount'),
                        certainty=CertaintyLevel(choice_data['certainty']),
                        reasoning=choice_data.get('reasoning', response)
                    )
                
                # If LLM parsing fails completely, try one fallback
                if attempt == max_retries - 1:
                    logger.warning(f"JSON parsing failed after {max_retries} attempts, using fallback")
                    return await self.parse_principle_choice(response)
                
            except Exception as e:
                logger.warning(f"Principle choice parsing attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    # Final fallback
                    return await self._parse_with_fallback(response, 'principle_choice')
        
        # This should not be reached due to the fallback in the loop
        raise ValueError(f"Failed to parse principle choice after {max_retries} attempts")
    
    
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
        result = await run_without_tracing(self.parser_agent, format_prompt)
        
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
                
                result = await run_without_tracing(self.parser_agent, parsing_prompt)
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
        """Parse JSON response from utility agent LLM."""
        import json
        try:
            # Clean the response - look for JSON content
            response_stripped = llm_response.strip()
            
            # Try to extract JSON from the response
            start_idx = response_stripped.find('{')
            end_idx = response_stripped.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning(f"No JSON found in LLM response: {response_stripped[:100]}...")
                return None
            
            json_str = response_stripped[start_idx:end_idx + 1]
            parsed_json = json.loads(json_str)
            
            # Validate required fields
            if not all(key in parsed_json for key in ['principle', 'constraint_amount', 'certainty']):
                logger.warning(f"Missing required fields in JSON response: {parsed_json}")
                return None
            
            # CRITICAL: IMMEDIATE rejection of letter-based principles (NO LETTERS SUPPORTED)
            principle_input = parsed_json['principle'].lower().strip()
            
            # REJECT ANY SINGLE LETTER REFERENCES IMMEDIATELY
            if re.match(r'^[a-d]$', principle_input) or re.match(r'^principle\s+[a-d]$', principle_input):
                logger.warning(f"IMMEDIATELY REJECTING letter-based principle: {principle_input}")
                return None
            
            # Direct validation for canonical names (no mapping needed)
            valid_canonical_principles = {
                'maximizing_floor',
                'maximizing_average',
                'maximizing_average_floor_constraint', 
                'maximizing_average_range_constraint'
            }
            
            if principle_input in valid_canonical_principles:
                principle_name = principle_input
            else:
                # Map variations and legacy names to canonical names - NO LETTERS SUPPORTED
                principle_variations = {
                    # English variations - FULL NAMES ONLY
                    'maximizing_floor_income': 'maximizing_floor',
                    'maximizing_average_income': 'maximizing_average',
                    'floor_constraint': 'maximizing_average_floor_constraint',
                    'range_constraint': 'maximizing_average_range_constraint',
                    'maximizing the floor income': 'maximizing_floor',
                    'maximizing the average income': 'maximizing_average',
                    'maximizing floor income': 'maximizing_floor',
                    'maximizing average income': 'maximizing_average',
                    
                    # Chinese principle names
                    '最大化最低收入': 'maximizing_floor',
                    '最大化平均收入': 'maximizing_average', 
                    '在最低收入约束条件下最大化平均收入': 'maximizing_average_floor_constraint',
                    '在范围约束条件下最大化平均收入': 'maximizing_average_range_constraint',
                    '最低收入最大化': 'maximizing_floor',
                    '平均收入最大化': 'maximizing_average',
                    '最低收入约束条件': 'maximizing_average_floor_constraint',
                    '范围约束条件': 'maximizing_average_range_constraint',
                    
                    # Spanish principle names
                    'maximizar los ingresos mínimos': 'maximizing_floor',
                    'maximizar los ingresos promedio': 'maximizing_average',
                    'maximizar los ingresos promedio con restricción de ingreso mínimo': 'maximizing_average_floor_constraint',
                    'maximizar los ingresos promedio con restricción de rango': 'maximizing_average_range_constraint',
                    'maximización del ingreso mínimo': 'maximizing_floor',
                    'maximización del ingreso promedio': 'maximizing_average',
                    'maximización del ingreso promedio bajo restricción de ingreso mínimo': 'maximizing_average_floor_constraint',
                    'maximización del ingreso promedio bajo restricción de rango': 'maximizing_average_range_constraint'
                }
                
                principle_name = principle_variations.get(principle_input)
                if principle_name is None:
                    # DOUBLE CHECK: Ensure no letter-based input was missed
                    if re.search(r'\b[a-d]\b', principle_input):
                        logger.warning(f"REJECTING letter-contaminated principle: {principle_input}")
                        return None
                    logger.warning(f"Invalid principle value: {principle_input}")
                    return None
            
            # Check for common parsing errors - if response mentions constraint but principle is basic average
            response_lower = llm_response.lower()
            if principle_name == 'maximizing_average' and ('floor constraint' in response_lower):
                logger.warning("Detected 'floor constraint' with basic average principle - correcting to floor constraint")
                principle_name = 'maximizing_average_floor_constraint'
            elif principle_name == 'maximizing_average' and ('range constraint' in response_lower):
                logger.warning("Detected 'range constraint' with basic average principle - correcting to range constraint") 
                principle_name = 'maximizing_average_range_constraint'
            
            # Validate certainty value
            valid_certainty = ['very_unsure', 'unsure', 'sure', 'very_sure']
            if parsed_json['certainty'] not in valid_certainty:
                logger.warning(f"Invalid certainty value: {parsed_json['certainty']}")
                return None
            
            # Validate constraint amount - accept any positive amount
            constraint_amount = parsed_json['constraint_amount']
            if constraint_amount is not None:
                if isinstance(constraint_amount, (int, float)) and constraint_amount > 0:
                    constraint_amount = int(constraint_amount)
                    logger.info(f"Parsed constraint amount: ${constraint_amount}")
                else:
                    logger.warning(f"Invalid constraint amount: {constraint_amount} - must be positive number")
                    constraint_amount = None
            
            # Fallback: If constraint amount is missing but principle requires it, try regex extraction
            if (constraint_amount is None and 
                principle_name in ['maximizing_average_floor_constraint', 'maximizing_average_range_constraint']):
                fallback_amount = self._extract_constraint_amount_flexible(llm_response)
                if fallback_amount:
                    constraint_amount = fallback_amount
                    logger.info(f"Fallback extraction recovered constraint amount: ${constraint_amount}")
                else:
                    logger.warning(f"Failed to extract constraint amount for {principle_name} principle")
            
            return {
                'principle': principle_name,
                'constraint_amount': constraint_amount,
                'certainty': parsed_json['certainty'],
                'confidence': 0.9,  # High confidence for JSON format
                'reasoning': llm_response
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}. Response: {llm_response[:200]}...")
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
            
            result = await run_without_tracing(self.parser_agent, detection_prompt)
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
            
            result = await run_without_tracing(self.parser_agent, detection_prompt)
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
            
            result = await run_without_tracing(self.parser_agent, parsing_prompt)
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
                        # Accept any positive amount
                        if amount > 0:
                            logger.info(f"Extracted constraint amount from LLM: ${amount}")
                            return amount
                        else:
                            logger.warning(f"Constraint amount must be positive: ${amount}")
                    except ValueError:
                        pass
            
            return None
            
        except Exception as e:
            logger.warning(f"LLM constraint amount parsing failed: {e}")
            return None
    
    async def detect_preference_statement(self, statement: str) -> Optional[PrincipleChoice]:
        """
        Detect preference statements in participant responses for SIMPLE MODE only.
        Uses LLM-first approach for better natural language understanding.
        
        Args:
            statement: The participant's statement to analyze
            
        Returns:
            PrincipleChoice if preference is detected, None otherwise
        """
        await self.async_init()
        
        # IMMEDIATE rejection of letter-based preferences - COMPREHENSIVE MULTILINGUAL PATTERNS
        statement_lower = statement.lower().strip()
        letter_rejection_patterns = [
            # English patterns
            r'\b(?:prefer|choice|support|choose)\s+(?:principle\s+)?[a-d]\b',
            r'\b(?:my|i)\s+(?:prefer|choice|support|choose)\s+[a-d]\b',
            r'\bpreference:\s*[a-d]\b',
            r'\bchoice:\s*[a-d]\b',
            r'\b[a-d]\s+with\s+\$?\d+',
            r'\b[a-d]\s+with\s+(?:range|floor)\s+constraint',
            
            # CRITICAL MISSING PATTERNS identified in contamination report
            r'\b(?:preference|choice)\s+is\s+(?:principle\s+)?[a-d]\b',  # "My choice is principle b"
            r'\bvote\s+(?:for|is)\s+(?:principle\s+)?[a-d]\b',           # "My vote is principle c"  
            r'\belection\s+de\s+voto\s+es\s+principio\s+[a-d]\b',       # Spanish ballot format
            r'\bi\s+(?:might\s+)?vote\s+for\s+(?:principle\s+)?[a-d]\b', # "I might vote for principle a"
            
            # Spanish patterns  
            r'\b(?:principio|opción|elección)\s*[a-d]\b',
            r'\b(?:mi|yo)\s+(?:prefiero|elijo|apoyo)\s+(?:principio\s+)?[a-d]\b',
            r'\bpreferencia:\s*[a-d]\b',
            r'\belección:\s*[a-d]\b',
            r'\bmi\s+elección\s+de\s+voto\s+es\s+principio\s+[a-d]\b',   # "Mi elección de voto es principio c"
            
            # Mandarin/Chinese patterns
            r'原则\s*[a-dA-D甲乙丙丁]\b',
            r'[甲乙丙丁]\s*(?:原则|选择|方案)\b', 
            r'我\s*(?:选择|偏好|支持)\s*[a-dA-D甲乙丙丁]\b',
            r'选择\s*[a-dA-D甲乙丙丁]\b',
            r'偏好\s*[a-dA-D甲乙丙丁]\b',
            r'原则[a-dA-D甲乙丙丁]\b',  # Mixed format: 原则a, 原则A, 原则甲
        ]
        
        for pattern in letter_rejection_patterns:
            if re.search(pattern, statement_lower):
                logger.info(f"Immediately rejecting letter-based preference: {statement}")
                return None
        
        # PRIMARY: LLM-based detection for natural language understanding
        try:
            language_manager = get_language_manager()
            
            # Enhanced prompt for preference detection with constraint extraction
            enhanced_prompt = f"""
Analyze this statement for DEFINITIVE preference expressions about justice principles:

Statement: "{statement}"

**CRITICAL REQUIREMENT: If the statement contains single letters (a, b, c, d) after preference words, IMMEDIATELY return NO_PREFERENCE_DETECTED. Single letters are NEVER valid principle names.**

Only detect CLEAR, DEFINITIVE preferences with these patterns:
✓ "I prefer [principle]" (definitive choice)
✓ "My preference is [principle]" (definitive statement)  
✓ "I choose [principle]" (definitive choice)
✓ "My choice is [principle]" (definitive statement)
✓ "I support [principle]" (definitive support)
✓ "Preference: [principle]" (definitive format)
✓ "Choice: [principle]" (definitive format)

Do NOT detect preferences in:
✗ Letter-based references: "I prefer a", "My choice is b", "principle c", "principle d" (NEVER detect single letters)
✗ Questions: "Should we choose [principle]?" or "Which principle do you prefer?"
✗ Conditionals: "If we choose [principle]..." or "[principle] might be good"
✗ Possibilities: "We could consider [principle]" or "Maybe [principle] is good"
✗ Past references: "I used to prefer [principle]" or "Previously I thought [principle]"
✗ General discussion: "We should discuss [principle]" or "What do others think about [principle]?"
✗ Future references: "We might prefer [principle] later"

**MULTILINGUAL PRINCIPLE DETECTION:**

**English:**
- "maximizing floor" or "maximizing floor income" = maximizing_floor
- "maximizing average" or "maximizing average income" = maximizing_average
- "floor constraint" or "minimum income" = maximizing_average_floor_constraint
- "range constraint" or "income gap" = maximizing_average_range_constraint

**Chinese (中文):**
- "最大化最低收入" (maximizing floor income) = maximizing_floor
- "最大化平均收入" (maximizing average income) = maximizing_average
- "在最低收入约束条件下最大化平均收入" (maximizing average under floor constraint) = maximizing_average_floor_constraint
- "在范围约束条件下最大化平均收入" (maximizing average under range constraint) = maximizing_average_range_constraint
- "最低收入约束条件" (floor constraint) = maximizing_average_floor_constraint
- "范围约束条件" (range constraint) = maximizing_average_range_constraint

**Spanish:**
- "maximización del ingreso mínimo" = maximizing_floor
- "maximización del ingreso promedio" = maximizing_average
- "maximización del ingreso promedio bajo restricción de ingreso mínimo" = maximizing_average_floor_constraint
- "maximización del ingreso promedio bajo restricción de rango" = maximizing_average_range_constraint

CRITICAL: Only detect CURRENT, DEFINITIVE preference statements, not questions or discussions about preferences.

Examples:
✓ "My choice is maximizing average" → PREFERENCE_DETECTED: maximizing_average
✓ "Choice: maximizing average income" → PREFERENCE_DETECTED: maximizing_average
✓ "I prefer floor constraint with $18,500" → PREFERENCE_DETECTED: maximizing_average_floor_constraint $18,500
✓ "我的偏好是最大化最低收入" → PREFERENCE_DETECTED: maximizing_floor
✓ "我选择在最低收入约束条件下最大化平均收入" → PREFERENCE_DETECTED: maximizing_average_floor_constraint
✗ "I prefer a" → NO_PREFERENCE_DETECTED (single letter rejected)
✗ "My choice is b" → NO_PREFERENCE_DETECTED (single letter rejected)
✗ "What do others think about maximizing floor income?" → NO_PREFERENCE_DETECTED
✗ "maximizing the average income might be good" → NO_PREFERENCE_DETECTED

If DEFINITIVE preference detected, respond with:
PREFERENCE_DETECTED: [full_principle_name] [amount if any]

If no definitive preference, respond with:
NO_PREFERENCE_DETECTED

Response:"""

            result = await run_without_tracing(self.parser_agent, enhanced_prompt)
            response = result.final_output.strip()
            
            if "PREFERENCE_DETECTED:" in response:
                # Parse the LLM response
                preference_text = response.split("PREFERENCE_DETECTED:")[1].strip()
                
                # Extract just the principle name part (before any dollar amounts)
                principle_name_only = re.split(r'\s+with\s+\$|\s+\$', preference_text)[0].strip()
                
                # Extract principle using unified method
                principle = self._map_identifier_to_principle(principle_name_only)
                if not principle:
                    principle = await self._extract_principle_from_text(principle_name_only)
                
                if principle:
                    # Extract constraint amount using unified method
                    constraint_amount = self._extract_constraint_amount_flexible(preference_text)
                    if not constraint_amount:
                        constraint_amount = self._extract_constraint_amount_flexible(statement)
                    
                    return PrincipleChoice(
                        principle=principle,
                        constraint_amount=constraint_amount,
                        certainty=CertaintyLevel.NO_OPINION,
                        reasoning="Preference detected via LLM analysis"
                    )
        
        except Exception as e:
            logger.warning(f"LLM preference detection failed: {e}")
        
        # FIRST: Check for exclusion patterns that should NOT be preferences
        non_preference_patterns = [
            r'\bwhat\s+(?:do|does)\b.*\b(?:maximizing|floor|average|constraint)\b',  # Questions
            r'\bshould\s+we\s+(?:choose|consider)\b.*\b(?:maximizing|floor|average|constraint)\b',  # Should we...
            r'\bwhat\s+if\b.*\b(?:maximizing|floor|average|constraint)\b',  # What if...
            r'\bif\s+we\s+(?:choose|go|went)\b.*\b(?:maximizing|floor|average|constraint)\b',  # If we...
            r'\b(?:used\s+to|might|could|previously)\b.*\b(?:maximizing|floor|average|constraint)\b',  # Past/conditional
            r'\bmight\s+be\s+good\b',  # "might be good"
            r'\bwe\s+(?:could|should|might)\s+consider\b',  # "we could consider"
        ]
        
        for pattern in non_preference_patterns:
            if re.search(pattern, statement_lower):
                logger.info(f"Rejecting non-preference statement: {statement}")
                return None

        # FALLBACK: Full-name patterns only - NO LETTER SUPPORT (statement_lower already defined above)
        full_name_patterns = [
            # Basic preference expressions with maximizing
            (r'\b(?:my\s+(?:preference|choice)\s+is|i\s+prefer|preference\s*:|choice\s*:)\s+(?:maximizing|maximize)\s+(?:the\s+)?floor(?:\s+income)?\b', 'maximizing_floor'),
            (r'\b(?:my\s+(?:preference|choice)\s+is|i\s+prefer|preference\s*:|choice\s*:)\s+(?:maximizing|maximize)\s+(?:the\s+)?average(?:\s+income)?\b', 'maximizing_average'),
            
            # Constraint-based preferences
            (r'\b(?:my\s+(?:preference|choice)\s+is|i\s+prefer|preference\s*:|choice\s*:|i\s+support)\s+floor\s+constraint\b', 'maximizing_average_floor_constraint'),
            (r'\b(?:my\s+(?:preference|choice)\s+is|i\s+prefer|preference\s*:|choice\s*:|i\s+support)\s+range\s+constraint\b', 'maximizing_average_range_constraint'),
            (r'\b(?:my\s+(?:preference|choice)\s+is|i\s+prefer|preference\s*:|choice\s*:|i\s+support)\s+minimum\s+income\b', 'maximizing_average_floor_constraint'),
            (r'\b(?:my\s+(?:preference|choice)\s+is|i\s+prefer|preference\s*:|choice\s*:|i\s+support)\s+income\s+gap\b', 'maximizing_average_range_constraint'),
            
            # Additional "I support" patterns for constraint detection
            (r'\bi\s+support\s+(?:maximizing\s+average\s+(?:income\s+)?(?:with|under)\s+)?floor\s+constraint(?:\s+with)?\b', 'maximizing_average_floor_constraint'),
            (r'\bi\s+support\s+(?:maximizing\s+average\s+(?:income\s+)?(?:with|under)\s+)?range\s+constraint(?:\s+with)?\b', 'maximizing_average_range_constraint'),
            
            # MISSING PATTERNS FROM PHASE 3: Enhanced pattern coverage for missing expressions
            # "Choice: maximizing average income" format
            (r'\bchoice\s*:\s*(?:maximizing|maximize)\s+(?:the\s+)?floor(?:\s+income)?\b', 'maximizing_floor'),
            (r'\bchoice\s*:\s*(?:maximizing|maximize)\s+(?:the\s+)?average(?:\s+income)?\b', 'maximizing_average'),
            (r'\bchoice\s*:\s*floor\s+constraint\b', 'maximizing_average_floor_constraint'),
            (r'\bchoice\s*:\s*range\s+constraint\b', 'maximizing_average_range_constraint'),
            
            # Enhanced "I support" patterns with dollar amounts
            (r'\bi\s+support\s+floor\s+constraint\s+with\s+\$\d+', 'maximizing_average_floor_constraint'),
            (r'\bi\s+support\s+range\s+constraint\s+with\s+\$\d+', 'maximizing_average_range_constraint'),
        ]
        
        for pattern, principle_name in full_name_patterns:
            match = re.search(pattern, statement_lower)
            if match:
                principle = self._map_identifier_to_principle(principle_name)
                if principle:
                    constraint_amount = self._extract_constraint_amount_flexible(statement)
                    return PrincipleChoice(
                        principle=principle,
                        constraint_amount=constraint_amount,
                        certainty=CertaintyLevel.NO_OPINION,
                        reasoning="Preference detected via simple pattern matching"
                    )
        
        # PHASE 5 FIX: Secondary LLM fallback when pattern matching fails
        logger.info("Pattern matching failed, attempting secondary LLM fallback for preference detection")
        return await self._detect_preference_via_llm(statement)
    
    def _map_identifier_to_principle(self, identifier: str) -> Optional[JusticePrinciple]:
        """Map principle identifier to JusticePrinciple. REJECTS ALL LETTER-BASED REFERENCES."""
        identifier = identifier.lower().strip()
        
        # IMMEDIATE REJECTION of letter-based identifiers across all languages
        if re.match(r'^[a-d]$', identifier):
            logger.warning(f"REJECTING letter-based identifier: {identifier}")
            return None
            
        # Remove common prefixes but check for letters after prefix removal
        clean_identifier = re.sub(r'^(principle|principio|原则)\s*', '', identifier)
        if re.match(r'^[a-d]$', clean_identifier):
            logger.warning(f"REJECTING letter-based identifier after prefix removal: {identifier} -> {clean_identifier}")
            return None
        
        # MULTILINGUAL letter rejection - reject common letter patterns in all languages
        letter_rejection_patterns = [
            r'^[a-d]$',  # Single letters
            r'^principle\s+[a-d]$',  # English "principle a"
            r'^principio\s+[a-d]$',  # Spanish "principio b" 
            r'^原则[a-dA-D甲乙丙丁]$',  # Chinese "原则a", "原则甲"
        ]
        
        for pattern in letter_rejection_patterns:
            if re.search(pattern, identifier):
                logger.warning(f"REJECTING letter-based identifier via pattern {pattern}: {identifier}")
                return None
        
        mapping = {
            # English full names ONLY - NO LETTERS SUPPORTED
            'maximizing_floor': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing_floor_income': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing the floor income': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing floor income': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing_average': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing_average_income': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing the average income': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing average income': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing_average_floor_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximizing_average_range_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            'floor_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'range_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Chinese principle names
            '最大化最低收入': JusticePrinciple.MAXIMIZING_FLOOR,
            '最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE,
            '在最低收入约束条件下最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            '在范围约束条件下最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            '最低收入最大化': JusticePrinciple.MAXIMIZING_FLOOR,
            '平均收入最大化': JusticePrinciple.MAXIMIZING_AVERAGE,
            '最低收入约束条件': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            '范围约束条件': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Spanish principle names (comprehensive)
            'maximizar los ingresos mínimos': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizar los ingresos promedio': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizar los ingresos promedio con restricción de ingreso mínimo': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximizar los ingresos promedio con restricción de rango': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            'maximización del ingreso mínimo': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximización del ingreso promedio': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximización del ingreso promedio bajo restricción de ingreso mínimo': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximización del ingreso promedio bajo restricción de rango': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        }
        
        result = mapping.get(clean_identifier)
        if result:
            return result
        
        # Final safety check - reject anything containing letters
        if re.search(r'\b[a-d]\b', identifier):
            logger.warning(f"REJECTING identifier containing letters: {identifier}")
            return None
            
        return None
    
    async def _extract_principle_from_text(self, principle_text: str) -> Optional[JusticePrinciple]:
        """
        Extract JusticePrinciple from text using LLM-based parsing instead of regex.
        This replaces the old regex-based pattern matching approach.
        """
        principle_text = principle_text.lower().strip()
        
        # Try full-name mapping only - NO LETTERS SUPPORTED
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
        # Skip negative numbers entirely
        if '-' in statement:
            return None
            
        # Multiple patterns for flexible amount parsing including space separators and international currencies
        amount_patterns = [
            r'[\$¥€]\s*(\d{1,6}(?:[.,\s]\d{3})*)',  # $14,000 or ¥14,000 or €14,000 or $14000 or ¥15 000
            r'(\d{1,6}(?:[.,\s]\d{3})*)\s*(?:dollars?|\$|元|euros?|€)',  # 14,000 dollars or 14000$ or 15000元 or 15 000€
            r'(\d{1,2})\s*k(?:\s|$|\.)',  # 14k
            r'(\d{1,3})\s*(?:thousand|千|mil)',  # 16 thousand, 18千, 20 mil (Spanish) - fixed to 1-3 digits
            r'(\d{3,6})(?!\s*[%])',  # Plain numbers 3-6 digits (avoid percentages)
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, statement, re.IGNORECASE)
            for match in matches:
                try:
                    # Handle thousand separators: commas, dots (European), spaces
                    if (',' in match or 
                        ('.' in match and len(match.split('.')[-1]) == 3) or
                        ' ' in match):
                        # Has thousand separators: 15,000 or 15.000 or 15 000
                        amount_str = match.replace(',', '').replace('.', '').replace(' ', '')
                    else:
                        # Plain number: 15000 - no processing needed
                        amount_str = match.replace(',', '').replace('.', '').replace(' ', '')
                    
                    amount = float(amount_str)
                    
                    # Check if this is a "k" pattern or thousand marker
                    statement_lower = statement.lower()
                    if 'k' in statement_lower and amount < 1000:
                        amount *= 1000
                    elif ('thousand' in statement_lower or '千' in statement or 'mil' in statement_lower) and amount < 1000:
                        amount *= 1000
                        logger.info(f"Multiplied {match} by 1000 due to thousand/千/mil marker, result: {amount}")
                    
                    amount_int = int(amount)
                    
                    # Accept any positive amount
                    if amount_int > 0:
                        logger.info(f"Extracted flexible constraint amount: ${amount_int}")
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
            result = await run_without_tracing(self.parser_agent, detection_prompt)
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
            
            # CRITICAL FIX: Prevent consensus if constraint amounts are missing for constraint principles
            if (agreed_choice.constraint_amount is None and 
                agreed_choice.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                          JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
                warnings.append(f"Cannot reach consensus: Missing constraint amount for {agreed_choice.principle.value}")
                return False, None, warnings
            
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
            
            # CRITICAL FIX: Prevent consensus if constraint amounts are missing for constraint principles
            if (agreed_choice.constraint_amount is None and 
                agreed_choice.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                          JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
                warnings.append(f"Cannot reach consensus: Missing constraint amount for {agreed_choice.principle.value}")
                return False, None, warnings
            
            return True, agreed_choice, warnings
        
        return False, None, warnings
