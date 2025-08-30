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
        Enhanced multilingual vote detection using utility agent intelligence.
        Detects when participants want to trigger formal voting in discussions.
        Replaces regex patterns with smart LLM-based analysis for better accuracy.
        """
        await self.async_init()

        statement_lower = statement.lower().strip()
        
        # Detect likely language for better processing
        language_hint = self._detect_language_hint(statement)
        logger.debug(f"Detected language '{language_hint}' for vote intention analysis: {statement}")

        # PRIMARY: LLM-based multilingual vote intention detection
        try:
            vote_detection_prompt = f"""
Analyze if this statement expresses IMMEDIATE intention to vote or make a decision.

Statement: "{statement}"
Language hint: {language_hint}

DETECT VOTE_INTENTION for:
1. IMMEDIATE PROPOSALS: "Let's vote", "Votemos", "我们投票吧", "I propose we vote"
2. DECISION READINESS: "Ready to vote", "Time to vote", "Es hora de votar", "投票时间到了"
3. ACTION SIGNALS: "Voting is the next step", "Now we vote", "Ahora votemos", "现在投票"
4. CONSENSUS TRIGGERS: "Should we vote?", "¿Votamos?", "我们应该投票吗?"
5. DECISION LANGUAGE: "Let's decide", "Decidamos", "我们来决定", "Sugiero que tomemos una decisión"
6. PROCEDURE INITIATION: "Let's move to voting", "Procedamos a la votación", "开始投票程序"

DO NOT DETECT when the speaker:
1. ASKS QUESTIONS ABOUT VOTING: "When should we vote?", "¿Cuándo deberíamos votar?", "什么时候投票?"
2. EXPRESSES UNCERTAINTY: "Maybe we should vote", "Tal vez deberíamos votar", "也许我们应该投票"
3. SEEKS MORE DISCUSSION: "We need more discussion", "Necesitamos más discusión", "需要更多讨论"
4. MAKES CONDITIONAL STATEMENTS: "If we vote", "Si votamos", "如果我们投票"
5. REFERS TO PAST/FUTURE: "We voted before", "We will vote later", "Votaremos después"
6. ASKS FOR OPINIONS: "Do you think we should vote?", "¿Crees que deberíamos votar?", "你觉得我们应该投票吗?"

SPANISH LANGUAGE SPECIFICS:
✓ "Sugiero que tomemos una decisión" → VOTE_INTENTION (decision proposal)
✓ "Procedamos a la votación" → VOTE_INTENTION (procedure initiation)  
✓ "Es momento de decidir" → VOTE_INTENTION (timing signal)
✓ "Votemos ahora" → VOTE_INTENTION (immediate proposal)
✓ "¿Podemos votar ahora?" → VOTE_INTENTION (consensus seeking)

✗ "¿Deberíamos votar?" → NO_VOTE_INTENTION (opinion question, not proposal)
✗ "¿Cuándo deberíamos votar?" → NO_VOTE_INTENTION (timing question)
✗ "Necesitamos más discusión" → NO_VOTE_INTENTION (more discussion needed)
✗ "Tal vez deberíamos votar" → NO_VOTE_INTENTION (uncertainty)
✗ "Si votamos después" → NO_VOTE_INTENTION (conditional)

EXAMPLES:
✓ "Let's vote" → VOTE_INTENTION_DETECTED
✓ "Votemos ahora" → VOTE_INTENTION_DETECTED
✓ "Time for the vote" → VOTE_INTENTION_DETECTED  
✓ "Sugiero que tomemos una decisión" → VOTE_INTENTION_DETECTED
✓ "Should we vote?" → VOTE_INTENTION_DETECTED (seeking immediate consensus)

✗ "¿Deberíamos votar?" → NO_VOTE_INTENTION (opinion question in Spanish)
✗ "Maybe we should vote" → NO_VOTE_INTENTION (uncertainty)
✗ "When should we vote?" → NO_VOTE_INTENTION (timing question)
✗ "We need more discussion" → NO_VOTE_INTENTION (more discussion)

Response format - respond with EXACTLY one of these:
VOTE_INTENTION_DETECTED
NO_VOTE_INTENTION

Response:"""

            result = await run_without_tracing(self.parser_agent, vote_detection_prompt)
            response = result.final_output.strip()
            
            # Parse response - trust the LLM's multilingual analysis
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
            # Fallback to simple patterns only for obvious cases
            return self._detect_vote_intention_simple_fallback(statement_lower)

    def _detect_vote_intention_simple_fallback(self, statement_lower: str) -> Optional[str]:
        """
        Simple fallback for vote intention detection when LLM fails.
        Only handles the most obvious multilingual cases.
        """
        # Simple obvious patterns across languages
        obvious_patterns = [
            r"\blet'?s vote\b",           # English
            r"\btime to vote\b",          # English  
            r"\bready to vote\b",         # English
            r"\bvotemos\b",               # Spanish "let's vote"
            r"\ba votar\b",               # Spanish "to vote"
            r"\b我们投票\b",                # Chinese "we vote"
            r"\b投票吧\b",                 # Chinese "let's vote"
        ]
        
        for pattern in obvious_patterns:
            if re.search(pattern, statement_lower):
                logger.info(f"Vote detected via obvious fallback pattern: {pattern}")
                return statement_lower
        
        # No obvious vote intention detected
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
                parsed_data = await self._parse_llm_principle_response(response_text)
                if parsed_data:
                    return parsed_data
                    
            except Exception as e:
                logger.warning(f"LLM principle parsing failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                    
        return None
    
    async def _parse_llm_principle_response(self, llm_response: str) -> Optional[Dict[str, Any]]:
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
            
            # Fallback: If constraint amount is missing but principle requires it, try multilingual parsing
            if (constraint_amount is None and 
                principle_name in ['maximizing_average_floor_constraint', 'maximizing_average_range_constraint']):
                language_hint = self._detect_language_hint(llm_response)
                fallback_amount = await self.parse_constraint_amount_multilingual(llm_response, language_hint)
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
                parsed_data = await self._parse_llm_principle_response(f"PRINCIPLE_DETECTED: {preference_content}")
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
                    # Extract constraint amount using multilingual method with language hints
                    language_hint = self._detect_language_hint(statement)
                    constraint_amount = await self.parse_constraint_amount_multilingual(preference_text, language_hint)
                    if not constraint_amount:
                        constraint_amount = await self.parse_constraint_amount_multilingual(statement, language_hint)
                    
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
                    language_hint = self._detect_language_hint(statement)
                    constraint_amount = await self.parse_constraint_amount_multilingual(statement, language_hint)
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
    
    async def parse_constraint_amount_multilingual(self, constraint_text: str, language_hint: str = None) -> Optional[int]:
        """
        Use utility agent to parse constraint amounts across languages and formats.
        
        This replaces hardcoded regex patterns with intelligent LLM-based parsing
        that can handle:
        - Multiple languages (English/Spanish/Chinese)
        - Various number formats (European: 15.000,50 vs Latin American: 15,000.50)
        - Word numbers (fifteen thousand, quince mil, 一万五千)
        - Currency symbols and codes
        
        Args:
            constraint_text: Text containing constraint amount to parse
            language_hint: Optional language hint ("english", "spanish", "mandarin")
        
        Returns:
            Parsed amount as integer, or None if no valid amount found
        """
        if not constraint_text or constraint_text.strip() == "":
            return None
        
        # Get language manager for prompt construction
        language_manager = get_language_manager()
        
        parsing_prompt = f"""You are an expert at parsing constraint amounts from multilingual text with specialized Spanish language expertise.

PARSE CONSTRAINT AMOUNT from: "{constraint_text}"
Language hint: {language_hint or "unknown"}

**SPANISH LANGUAGE EXPERTISE (CRITICAL)**:
1. **Spanish Constraint Terminology**:
   - "restricción" = constraint/restriction (most common)
   - "límite" = limit 
   - "tope" = cap/ceiling
   - "cota" = bound
   - "barrera" = barrier
   - "frontera" = boundary
   - "umbral" = threshold
   - "máximo" = maximum
   - "limitación" = limitation
   - "condición" = condition

2. **Spanish Number Format Rules**:
   - **European Spanish**: €15.000 = 15000 (period as thousands separator, NO comma decimal for whole numbers)
   - **Latin American Spanish**: $15,000 = 15000 (comma as thousands separator)
   - **Mixed format**: €2.250.500 = 2,250,500 (multiple periods for large numbers)
   - **Decimal handling**: €125.750,25 = 125750 (ignore decimal part for constraint amounts)

3. **Spanish Currency Recognition**:
   - **Euros**: €, EUR, euros, euro (Spain primarily)
   - **Pesos**: $, MXN, ARS, COP, pesos, peso (Latin America)
   - **US Dollars**: $, USD, dólares, dólar (used in some regions)

4. **Spanish Number Words (COMPREHENSIVE)**:
   - "cinco mil" = 5000 (five thousand)
   - "diez mil" = 10000 (ten thousand)
   - "quince mil" = 15000 (fifteen thousand)
   - "veinte mil" = 20000 (twenty thousand)
   - "veinticinco mil" = 25000 (twenty-five thousand)
   - "treinta mil" = 30000 (thirty thousand)
   - "cincuenta mil" = 50000 (fifty thousand)
   - **Mixed numeric + word**: "15 mil" = 15000, "2.5 mil" = 2500, "30 mil" = 30000

5. **Spanish Preposition Patterns**:
   - "con restricción de" = with constraint of
   - "bajo restricción de" = under constraint of  
   - "dentro del límite de" = within limit of
   - "sujeto a restricción de" = subject to constraint of
   - "mediante restricción de" = through constraint of
   - "según restricción de" = according to constraint of
   - "por restricción de" = by constraint of

6. **Spanish Null Patterns**:
   - "sin restricciones" = without constraints → NONE
   - "ilimitado" = unlimited → NONE
   - "sin límite" = no limit → NONE
   - "libre" = free/unrestricted → NONE

**COMPREHENSIVE SPANISH EXAMPLES**:
✓ "restricción de €15.000" → 15000 (European format)
✓ "límite de $15,000" → 15000 (Latin American format)
✓ "tope de quince mil euros" → 15000 (number words)
✓ "con restricción de €15000" → 15000 (basic format)
✓ "barrera de 2.5 mil euros" → 2500 (mixed numeric + word)
✓ "constraint MXN 45.000" → 45000 (Mexican peso, European format)
✓ "límite de 30 mil pesos" → 30000 (thirty thousand pesos)
✓ "restricción €18.500,50" → 18500 (ignore decimal)
✓ "bajo restricción de €25.000" → 25000 (preposition variation)
✓ "tope de cinco mil euros" → 5000 (five thousand)
✓ "límite $ 22,500" → 22500 (space after symbol)
✓ "restricción de 125.750 euros" → 125750 (large European format)
✗ "sin restricciones" → NONE
✗ "ilimitado" → NONE
✗ "sin límite" → NONE

**OTHER LANGUAGES**:
- English: $15,000, 15k, fifteen thousand → 15000
- Chinese: ¥15,000, 15千, 一万五千 → 15000
- General: Space separators (15 000), various currency codes

**PARSING RULES**:
1. Extract numeric amount ignoring currency symbols
2. Handle both European (15.000) and Latin American (15,000) formats
3. Convert number words to digits
4. Ignore decimal parts for constraint amounts
5. Return only positive integer amounts
6. Return NONE if no valid amount or null patterns found

Response format: Return ONLY the numeric amount as integer, or "NONE" if no amount found.
Do not include explanations, currency symbols, or formatting.

Response:"""

        try:
            result = await run_without_tracing(self.parser_agent, parsing_prompt)
            response = result.final_output.strip()
            
            if response.upper() == "NONE":
                logger.info(f"No constraint amount found in: '{constraint_text}'")
                return None
            
            # Parse the numeric response
            try:
                amount = int(response)
                if amount > 0:
                    # Validate constraint scale
                    if not self._validate_constraint_scale(amount):
                        logger.warning(f"LLM parsed amount ${amount} but it failed scale validation")
                        return None
                        
                    logger.info(f"LLM parsed constraint amount: {amount} from '{constraint_text}'")
                    return amount
                else:
                    logger.warning(f"LLM returned non-positive amount: {amount}")
                    return None
            except ValueError:
                logger.warning(f"LLM returned non-numeric response: '{response}'")
                return None
        
        except Exception as e:
            logger.warning(f"LLM constraint parsing failed for '{constraint_text}': {e}")
            # Fallback to simple regex only for obvious cases
            return self._extract_constraint_amount_simple_fallback(constraint_text)

    def _extract_constraint_amount_simple_fallback(self, statement: str) -> Optional[int]:
        """
        Simplified fallback for constraint parsing when LLM fails.
        Only handles the most obvious cases.
        """
        # Simple patterns for obvious cases only
        simple_patterns = [
            r'[\$¥€]\s*(\d{3,6})(?!\d)',  # $15000, €15000, ¥15000
            r'(\d{3,6})\s*(?:dollars?|euros?|yuan)',  # 15000 dollars
            r'(\d{1,3})\s*k(?:\s|$|\.)',  # 15k
        ]
        
        for pattern in simple_patterns:
            matches = re.findall(pattern, statement, re.IGNORECASE)
            for match in matches:
                try:
                    amount = int(match)
                    if 'k' in statement.lower() and amount < 1000:
                        amount *= 1000
                    if amount > 0:
                        logger.info(f"Fallback parsed constraint amount: {amount}")
                        return amount
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _detect_language_hint(self, statement: str) -> str:
        """
        Enhanced language detection with comprehensive Spanish intelligence.
        
        Returns:
            Language hint: "spanish", "english", "mandarin", or "unknown"
        """
        statement_lower = statement.lower()
        
        # COMPREHENSIVE SPANISH DETECTION (Enhanced following utility agent philosophy)
        spanish_indicators = {
            # Core constraint terminology (high confidence)
            'high_confidence': ['restricción', 'límite', 'limitación', 'condición', 'tope', 'cota', 'barrera', 'frontera', 'umbral', 'máximo'],
            
            # Currency and number words (medium-high confidence)
            'currency_numbers': ['euros', 'euro', 'pesos', 'peso', 'dólares', 'dólar', 'mil', 'cinco', 'diez', 'quince', 'veinte', 'veinticinco', 'treinta', 'cincuenta'],
            
            # Prepositions and common words (medium confidence) 
            'prepositions': ['con', 'de', 'bajo', 'dentro', 'del', 'sujeto', 'mediante', 'según', 'por', 'sin', 'es', 'la', 'el', 'una'],
            
            # Spanish-specific patterns (medium confidence)
            'patterns': ['condiciones', 'limitaciones', 'ilimitado', 'libre', 'mxn', 'ars', 'cop'],
            
            # Justice principle terms in Spanish (high confidence)
            'principles': ['maximización', 'maximizar', 'ingresos', 'ingreso', 'promedio', 'mínimos', 'mínimo', 'promedio', 'rango']
        }
        
        # Count indicators by confidence level
        high_confidence_count = sum(1 for word in spanish_indicators['high_confidence'] if word in statement_lower)
        currency_count = sum(1 for word in spanish_indicators['currency_numbers'] if word in statement_lower)
        preposition_count = sum(1 for word in spanish_indicators['prepositions'] if word in statement_lower)
        pattern_count = sum(1 for word in spanish_indicators['patterns'] if word in statement_lower)
        principle_count = sum(1 for word in spanish_indicators['principles'] if word in statement_lower)
        
        total_spanish_indicators = high_confidence_count + currency_count + preposition_count + pattern_count + principle_count
        
        # Spanish detection logic with confidence thresholds
        if high_confidence_count >= 1:  # Any high-confidence Spanish constraint term
            return "spanish"
        elif currency_count >= 1 and preposition_count >= 1:  # Spanish currency + Spanish grammar
            return "spanish"  
        elif principle_count >= 2:  # Multiple Spanish justice principle terms
            return "spanish"
        elif total_spanish_indicators >= 3:  # Multiple Spanish indicators together
            return "spanish"
        elif total_spanish_indicators >= 2 and len(statement_lower.split()) <= 8:  # Short phrases with Spanish indicators
            return "spanish"
        
        # Chinese indicators (characters)
        chinese_chars = ['元', '千', '万', '限制', '约束', '条件', '投票', '决定', '最大化', '最低', '平均', '收入', '范围']
        chinese_count = sum(1 for char in chinese_chars if char in statement)
        if chinese_count >= 1:
            return "mandarin"
        
        # English indicators (comprehensive)
        english_indicators = {
            'constraint_terms': ['constraint', 'limit', 'maximum', 'minimum', 'restriction', 'bound', 'cap', 'threshold'],
            'currency_numbers': ['dollars', 'dollar', 'thousand', 'million', 'euros'],
            'principles': ['maximizing', 'maximize', 'income', 'average', 'floor', 'range'],
            'common': ['with', 'of', 'no', 'the', 'and', 'is', 'are', 'vote', 'decision']
        }
        
        english_constraint_count = sum(1 for word in english_indicators['constraint_terms'] if word in statement_lower)
        english_currency_count = sum(1 for word in english_indicators['currency_numbers'] if word in statement_lower)
        english_principle_count = sum(1 for word in english_indicators['principles'] if word in statement_lower)
        english_common_count = sum(1 for word in english_indicators['common'] if word in statement_lower)
        
        total_english_indicators = english_constraint_count + english_currency_count + english_principle_count + english_common_count
        
        # English detection logic
        if english_constraint_count >= 1:  # Any English constraint term
            return "english"
        elif english_principle_count >= 2:  # Multiple English principle terms
            return "english"
        elif total_english_indicators >= 3:  # Multiple English indicators
            return "english"
        
        # Final decision: Spanish vs English for ambiguous cases
        if total_spanish_indicators > total_english_indicators:
            return "spanish"
        elif total_english_indicators > total_spanish_indicators:
            return "english"
        
        return "unknown"
    
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
    
    async def detect_problematic_content_multilingual(self, statement: str) -> Optional[Dict[str, Any]]:
        """
        Detect problematic content using utility agent intelligence.
        Replaces regex-based quarantine detection with smart LLM analysis.
        
        Following our utility agent philosophy: enhance intelligence, not hardcoded patterns.
        
        Args:
            statement: Statement to analyze for problematic content
            
        Returns:
            Dict with problem details if detected, None otherwise
        """
        await self.async_init()
        
        detection_prompt = f"""Analyze this statement for problematic content that should be quarantined:

Statement: "{statement}"

DETECT these critical problems:

1. **Letter-based principle references** (HIGHEST PRIORITY):
   - English: "principle a", "principle b", "choose a", "prefer b", "option a", "option b"
   - Spanish: "principio a", "principio b", "elijo a", "prefiero b", "opción a", "opción b"
   - Chinese: "原则a", "原则b", "选择a", "选择b"
   - Mixed: Any preference/choice word followed by single letters a-d

2. **Premature voting intentions with letters**:
   - "Let's vote for a", "Votemos por b", "我投票给a"
   - "Vote for option a", "Votar por la opción b"
   - Combining letter reference with voting language

3. **Invalid preference expressions**:
   - Any preference statement using single letters instead of full principle names
   - Mixed language letter references

**EXAMPLES OF PROBLEMS TO DETECT**:
✓ "I choose principle a" → PROBLEM: letter_reference
✓ "Mi elección es el principio a" → PROBLEM: letter_reference
✓ "Let's vote for option b" → PROBLEM: letter_reference + voting
✓ "Votemos por la opción b" → PROBLEM: letter_reference + voting
✓ "我选择原则a" → PROBLEM: letter_reference
✓ "Vote for a right now" → PROBLEM: letter_reference + voting

**EXAMPLES OF VALID CONTENT** (should NOT be detected):
✗ "I prefer maximizing floor income" → NO_PROBLEM
✗ "Mi elección es maximización del ingreso promedio" → NO_PROBLEM
✗ "Let's vote for maximizing average income" → NO_PROBLEM
✗ "我选择最大化最低收入" → NO_PROBLEM

**CRITICAL DETECTION RULES**:
- Any single letter (a, b, c, d) after words like: choose, prefer, vote, select, pick, option, principle, principio, opción, elijo, prefiero, voto, 选择, 偏好, 投票, 原则
- Must distinguish between letter references vs. words that contain letters
- Focus on problematic preference/voting expressions with letters

If problem detected, respond with:
PROBLEM_DETECTED: [type] - [detailed_reason]

If no problem, respond with:
NO_PROBLEM_DETECTED

Response:"""

        try:
            result = await run_without_tracing(self.parser_agent, detection_prompt)
            response = result.final_output.strip()
            
            if "PROBLEM_DETECTED:" in response:
                parts = response.split("PROBLEM_DETECTED:")[1].strip().split(" - ", 1)
                problem_type = parts[0].strip()
                reason = parts[1].strip() if len(parts) > 1 else "Problematic content detected"
                
                logger.info(f"🚫 Quarantine detection: {statement[:50]}... → {problem_type}")
                
                return {
                    "type": problem_type,
                    "reason": reason,
                    "message": statement,
                    "detection_method": "utility_agent_llm"
                }
            elif "NO_PROBLEM_DETECTED" in response:
                logger.debug(f"✅ Content approved: {statement[:50]}...")
                return None
            else:
                # Log unexpected response but treat as no detection
                logger.warning(f"Unexpected quarantine detection response: '{response[:100]}...' - treating as NO_PROBLEM")
                return None
                
        except Exception as e:
            logger.warning(f"LLM quarantine detection failed: {e} - falling back to basic check")
            # Fallback to simple letter detection only for obvious cases
            return self._detect_problematic_content_simple_fallback(statement)

    def _detect_problematic_content_simple_fallback(self, statement: str) -> Optional[Dict[str, Any]]:
        """
        Simple fallback for problematic content detection when LLM fails.
        Only handles the most obvious letter-based references.
        """
        statement_lower = statement.lower()
        
        # Only check for the most obvious letter patterns across languages
        obvious_letter_patterns = [
            r'\b(?:principle|principio|原则)\s+[a-d]\b',       # "principle a", "principio b", "原则a"
            r'\b(?:option|opción)\s+[a-d]\b',                # "option a", "opción b" 
            r'\b(?:choose|elijo|选择)\s+[a-d]\b',              # "choose a", "elijo b", "选择a"
            r'\b(?:prefer|prefiero|偏好)\s+[a-d]\b',          # "prefer a", "prefiero b", "偏好a"
        ]
        
        for pattern in obvious_letter_patterns:
            if re.search(pattern, statement, re.IGNORECASE):
                logger.info(f"🚫 Fallback quarantine detection: {statement[:50]}... → letter_reference")
                return {
                    "type": "letter_reference",
                    "reason": "Contains obvious letter-based principle reference",
                    "message": statement,
                    "detection_method": "regex_fallback"
                }
        
        return None
    
    async def _extract_constraint_amount_flexible(self, constraint_text: str) -> Optional[int]:
        """
        Flexible constraint amount extraction using utility agent intelligence.
        This method wraps the existing multilingual parsing infrastructure.
        
        Args:
            constraint_text: Text containing constraint amount to parse
            
        Returns:
            Constraint amount as integer, or None if not found/invalid
        """
        await self.async_init()
        
        if not constraint_text or constraint_text.strip() == "":
            return None
        
        # Detect language hint for better parsing
        language_hint = self._detect_language_hint(constraint_text)
        
        # Use existing multilingual parsing with enhanced error handling
        try:
            amount = await self.parse_constraint_amount_multilingual(constraint_text, language_hint)
            if amount and amount > 0:
                # Validate constraint amount scale  
                if not self._validate_constraint_scale(amount):
                    logger.warning(f"Flexible extraction found amount ${amount} but it failed scale validation")
                    return None
                
                logger.info(f"Flexible constraint extraction successful: {amount} from '{constraint_text}'")
                return amount
            return None
        except Exception as e:
            logger.warning(f"Flexible constraint extraction failed: {e}")
            return None
    
    def _validate_constraint_scale(self, amount: int) -> bool:
        """
        Validate that constraint amount is in reasonable income scale, not payoff scale.
        
        Args:
            amount: Constraint amount to validate
            
        Returns:
            True if valid, False if likely payoff scale error
        """
        if amount is None:
            return True
        
        # Define reasonable bounds
        MIN_INCOME_CONSTRAINT = 1000    # $1,000
        LIKELY_PAYOFF_SCALE_MAX = 10    # $10 suggests payoff scale error
        
        if amount <= LIKELY_PAYOFF_SCALE_MAX:
            logger.warning(f"Constraint amount ${amount} appears to be in payoff scale ($1-$10) rather than income scale ($10,000-$30,000)")
            return False
        
        if amount < MIN_INCOME_CONSTRAINT:
            logger.warning(f"Constraint amount ${amount} is below reasonable minimum of ${MIN_INCOME_CONSTRAINT:,}")
            return False
        
        return True
    
    async def parse_participant_preference(self, statement: str, participant_name: str = None) -> Optional[PrincipleChoice]:
        """
        Parse participant preference statements with constraint amounts.
        Uses LLM-based analysis for multilingual support.
        
        Args:
            statement: The participant's statement to analyze
            participant_name: Optional participant name for logging
            
        Returns:
            PrincipleChoice if preference is detected, None otherwise
        """
        await self.async_init()
        
        # Use existing preference detection logic
        preference = await self.detect_preference_statement(statement)
        
        if preference:
            # If constraint amount is missing but principle requires it, try enhanced extraction
            if (preference.constraint_amount is None and 
                preference.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                       JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
                
                # Use flexible constraint extraction
                extracted_amount = await self._extract_constraint_amount_flexible(statement)
                if extracted_amount:
                    logger.info(f"Enhanced constraint extraction for {participant_name or 'participant'}: {extracted_amount}")
                    # Create new preference with extracted amount
                    return PrincipleChoice(
                        principle=preference.principle,
                        constraint_amount=extracted_amount,
                        certainty=preference.certainty,
                        reasoning=preference.reasoning
                    )
            
            return preference
        
        return None

    async def validate_ballot_parsing_consistency(self, raw_response: str, parsed_result: PrincipleChoice, language: str = "english") -> bool:
        """
        Validate ballot parsing matches expected patterns across languages.
        
        Implements the runtime validation system from Critical_Ballot_Parsing_Fix_Plan.md
        to detect parsing mismatches in real-time and prevent systematic errors.
        
        Args:
            raw_response: The original participant response
            parsed_result: The parsed PrincipleChoice result
            language: The language of the response ("english", "spanish", "mandarin")
            
        Returns:
            bool: True if parsing is consistent with expected patterns, False if mismatch detected
        """
        
        # English validation patterns
        english_patterns = {
            "maximizing the floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximizing the average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximizing average with floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximizing average with range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "my ballot choice is maximizing the floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "my ballot choice is maximizing the average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "considers only the welfare of the worst-off": JusticePrinciple.MAXIMIZING_FLOOR,
        }
        
        # Spanish validation patterns
        spanish_patterns = {
            "maximización del ingreso mínimo": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximización del ingreso promedio": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximización del promedio con restricción": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "restricción de rango": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "mi elección de voto es maximización del ingreso mínimo": JusticePrinciple.MAXIMIZING_FLOOR,
            "mi elección de voto es maximización del ingreso promedio": JusticePrinciple.MAXIMIZING_AVERAGE,
            "considera solo el bienestar de los más desfavorecidos": JusticePrinciple.MAXIMIZING_FLOOR,
        }
        
        # Mandarin validation patterns  
        mandarin_patterns = {
            "最大化最低收入": JusticePrinciple.MAXIMIZING_FLOOR,
            "最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE,
            "在最低收入约束条件下": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "在范围约束条件下": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "我的投票选择是最大化最低收入": JusticePrinciple.MAXIMIZING_FLOOR,
            "我的投票选择是最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE,
            "只考虑最弱势者福利的原则": JusticePrinciple.MAXIMIZING_FLOOR,
        }
        
        # Select appropriate patterns based on language
        validation_patterns = {
            "english": english_patterns,
            "spanish": spanish_patterns, 
            "mandarin": mandarin_patterns
        }.get(language, english_patterns)
        
        # Check for obvious mismatches
        response_lower = raw_response.lower()
        for pattern, expected_principle in validation_patterns.items():
            if pattern in response_lower:
                if parsed_result.principle != expected_principle:
                    logger.error(f"🚫 BALLOT PARSING MISMATCH [{language.upper()}]: '{raw_response}' parsed as {parsed_result.principle.value}, expected {expected_principle.value}")
                    return False
                    
        # Additional critical checks for the specific cases mentioned in the plan
        critical_english_checks = [
            ("my ballot choice is maximizing the floor income", JusticePrinciple.MAXIMIZING_FLOOR),
            ("maximizing the floor income", JusticePrinciple.MAXIMIZING_FLOOR),
        ]
        
        critical_spanish_checks = [
            ("mi elección de voto es maximización del ingreso mínimo", JusticePrinciple.MAXIMIZING_FLOOR),
        ]
        
        critical_mandarin_checks = [
            ("我的投票选择是最大化最低收入", JusticePrinciple.MAXIMIZING_FLOOR),
        ]
        
        critical_checks = {
            "english": critical_english_checks,
            "spanish": critical_spanish_checks,
            "mandarin": critical_mandarin_checks
        }.get(language, critical_english_checks)
        
        for critical_text, expected_principle in critical_checks:
            if critical_text in response_lower:
                if parsed_result.principle != expected_principle:
                    logger.error(f"🚨 CRITICAL BALLOT PARSING ERROR [{language.upper()}]: The systematic error has occurred! '{raw_response}' parsed as {parsed_result.principle.value}, should be {expected_principle.value}")
                    return False
        
        return True
