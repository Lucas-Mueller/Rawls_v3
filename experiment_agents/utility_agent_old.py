"""
Utility agent for parsing and validating participant responses.
"""
import asyncio
import logging
import re
import os
from typing import Optional, Dict, Any, List
from agents import Agent, Runner, AgentOutputSchema
from agents.tracing.setup import get_trace_provider

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
from utils.language_manager import get_language_manager, SupportedLanguage, get_english_principle_name

logger = logging.getLogger(__name__)


async def run_without_tracing(agent, prompt, context=None):
    """Run agent without tracing to prevent utility agent operations from being traced.

    Uses a disabled trace context to avoid global toggles that can interfere with
    participant tracing in concurrent tasks.
    """
    # Create a disabled (no-op) trace only for this block using provider directly
    # to avoid "Trace already exists" warnings from the high-level helper.
    trace_obj = get_trace_provider().create_trace(name="utility_agent_run", disabled=True)
    with trace_obj:
        return await Runner.run(agent, prompt, context=context)


class UtilityAgent:
    """Specialized agent for parsing and validating participant responses with enhanced text parsing."""
    
    
    def __init__(self, utility_model: str = None, temperature: float = 0.0, experiment_language: str = "english"):
        
        # Use environment variable or default for utility agents
        if utility_model is None:
            utility_model = os.getenv("UTILITY_AGENT_MODEL", "gpt-4.1-mini")
        
        self.utility_model = utility_model
        self.temperature = temperature
        self.temperature_info = None
        self.experiment_language = experiment_language.lower()
        self.language_manager = get_language_manager()
        
        # Agents will be created in async_init
        self.parser_agent = None
        self.validator_agent = None
        self._initialization_complete = False
        
        # Load patterns only for the configured language
        self._language_patterns = self._compile_patterns_for_language(self.experiment_language)
        
        # Multi-language principle mapping tables for lookup-based parsing
        self._principle_mappings = self._create_principle_mappings()
        
    async def async_init(self):
        """Asynchronously initialize utility agents with dynamic temperature detection."""
        if self._initialization_complete:
            return
        
        try:
            # Build utility agents inside a disabled trace context to avoid emitting spans
            trace_obj = get_trace_provider().create_trace(name="utility_agent_init", disabled=True)
            with trace_obj:
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
        operation_name="validate_constraint"
    )
    async def validate_constraint_specification(self, choice: PrincipleChoice) -> bool:
        """Validate constraint principles have required amounts and reasonable scale."""
        try:
            constraint_principles = [
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            ]
            
            if choice.principle in constraint_principles:
                # Check if constraint amount exists and is positive
                if choice.constraint_amount is None or choice.constraint_amount <= 0:
                    logger.warning(
                        f"Constraint principle {choice.principle.value} missing valid constraint amount: {choice.constraint_amount}"
                    )
                    return False
                
                # Check if constraint amount is in reasonable scale (merged from _validate_constraint_scale)
                MIN_INCOME_CONSTRAINT = 1000    # $1,000
                LIKELY_PAYOFF_SCALE_MAX = 10    # $10 suggests payoff scale error
                
                if choice.constraint_amount <= LIKELY_PAYOFF_SCALE_MAX:
                    logger.warning(f"Constraint amount ${choice.constraint_amount} appears to be in payoff scale ($1-$10) rather than income scale ($10,000-$30,000)")
                    return False
                
                if choice.constraint_amount < MIN_INCOME_CONSTRAINT:
                    logger.warning(f"Constraint amount ${choice.constraint_amount} is below reasonable minimum of ${MIN_INCOME_CONSTRAINT:,}")
                    return False
                
                return True
            
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
    
    async def detect_agreement(self, response: str) -> bool:
        """Language-specific agreement detection using configured experiment language.
        
        Uses pre-loaded patterns for the configured experiment language to detect agreement/disagreement.
        """
        await self.async_init()

        text = response.strip()
        
        # CRITICAL: Reject empty or whitespace-only responses immediately
        if not text or len(text) < 2:
            logger.info("Agreement detection: Empty or too short response - treating as disagreement")
            return False
            
        normalized = text.upper()
        
        # Use pre-loaded language-specific patterns
        agreement_tokens = self._language_patterns.get('agreement_tokens', [])
        disagreement_tokens = self._language_patterns.get('disagreement_tokens', [])

        # Check for direct agreement
        has_agree = any(token.upper() in normalized for token in agreement_tokens)
        has_disagree = any(token.upper() in normalized for token in disagreement_tokens)
        
        if has_agree and not has_disagree:
            logger.info(f"Direct agreement detected using {self.experiment_language} patterns")
            return True
        elif has_disagree and not has_agree:
            logger.info(f"Direct disagreement detected using {self.experiment_language} patterns")
            return False

        # If ambiguous, use LLM fallback
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
        
        # Use configured experiment language
        logger.debug(f"Using configured language '{self.experiment_language}' for vote intention analysis: {statement}")

        # PRIMARY: LLM-based multilingual vote intention detection
        try:
            vote_detection_prompt = f"""
Analyze if this statement expresses IMMEDIATE intention to vote or make a decision.

Statement: "{statement}"
Language: {self.experiment_language}

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
    
    
    
    
    def _create_principle_mappings(self) -> Dict[str, JusticePrinciple]:
        """Create comprehensive multi-language principle mapping tables for lookup-based parsing."""
        mappings = {}
        
        # English mappings
        english_mappings = {
            # Core principle names
            "maximizing the floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximizing the average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximizing the average income with a floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximizing the average income with a range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Common variations
            "maximize floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximize average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximizing floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximizing average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "floor income maximization": JusticePrinciple.MAXIMIZING_FLOOR,
            "average income maximization": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximizing the floor": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximizing the average": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximize the floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximize the average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "average income with floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "average income with range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "maximizing average with floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximizing the average with a floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximizing average with range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "maximizing the average with a range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "average maximization with floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "average maximization with range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Short form variations
            "floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "floor constraint principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "range constraint principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "average maximization": JusticePrinciple.MAXIMIZING_AVERAGE,
            "floor maximization": JusticePrinciple.MAXIMIZING_FLOOR,
            "average with floor": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "average with range": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "floor income": JusticePrinciple.MAXIMIZING_FLOOR,
            "average income": JusticePrinciple.MAXIMIZING_AVERAGE,
            "the floor income maximization approach": JusticePrinciple.MAXIMIZING_FLOOR,
            "the principle of maximizing average income": JusticePrinciple.MAXIMIZING_AVERAGE,
        }
        
        # Spanish mappings
        spanish_mappings = {
            # Core principle names
            "maximización del ingreso mínimo": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximización del ingreso promedio": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximización del ingreso promedio bajo restricción de ingreso mínimo": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximización del ingreso promedio bajo restricción de rango": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Common variations
            "maximizar ingreso mínimo": JusticePrinciple.MAXIMIZING_FLOOR,
            "maximizar ingreso promedio": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximización del ingreso medio": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximización de la media de ingresos": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximizando el ingreso promedio": JusticePrinciple.MAXIMIZING_AVERAGE,
            "maximización del ingreso promedio con restricción de mínimo": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximización del ingreso promedio con límite inferior": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximización del ingreso medio con restricción de piso": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "maximización del promedio con restricción": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "restricción de rango": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        }
        
        # Mandarin mappings
        mandarin_mappings = {
            # Core principle names
            "最大化最低收入": JusticePrinciple.MAXIMIZING_FLOOR,
            "最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE,
            "在最低收入约束条件下最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "在范围约束条件下最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Common variations
            "最大化平均收入并设置最低限制": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "带最低约束的平均收入最大化": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "最大化收入平均值": JusticePrinciple.MAXIMIZING_AVERAGE,
            "平均收入最大化": JusticePrinciple.MAXIMIZING_AVERAGE,
            "收入平均值最大化": JusticePrinciple.MAXIMIZING_AVERAGE,
            "最低收入最大化": JusticePrinciple.MAXIMIZING_FLOOR,
            "最大化平均收入并设置范围限制": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "在范围约束下最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        }
        
        # Combine all mappings with language-agnostic lowercase keys
        for lang_mappings in [english_mappings, spanish_mappings, mandarin_mappings]:
            for text, principle in lang_mappings.items():
                # Store with normalized key (lowercase, stripped)
                key = text.lower().strip()
                mappings[key] = principle
                
        return mappings
    
    def _fuzzy_match_principle(self, text: str) -> Optional[JusticePrinciple]:
        """Find principle using fuzzy matching on normalized text."""
        normalized_text = text.lower().strip()
        
        # Direct lookup first
        principle = self._principle_mappings.get(normalized_text)
        if principle:
            return principle
            
        # Fuzzy matching for partial matches
        for mapping_key, principle in self._principle_mappings.items():
            # Check if the key is contained in the text or vice versa
            if mapping_key in normalized_text or normalized_text in mapping_key:
                # Additional check: ensure it's a substantial match (>50% overlap)
                shorter_len = min(len(mapping_key), len(normalized_text))
                longer_len = max(len(mapping_key), len(normalized_text))
                if shorter_len / longer_len > 0.5:
                    return principle
                    
        return None
    
    def _extract_numbered_list(self, response: str) -> List[tuple]:
        """Extract numbered list items from response text."""
        rankings = []
        
        # Use existing regex pattern
        ranking_matches = self._language_patterns['ranking_line'].findall(response)
        
        if len(ranking_matches) >= 4:
            for rank_num, rank_text in ranking_matches[:4]:
                try:
                    rank = int(rank_num)
                    if 1 <= rank <= 4:
                        # Clean up the text: remove markdown, extra whitespace, and explanations
                        clean_text = rank_text.strip()
                        clean_text = re.sub(r'\*+', '', clean_text)  # Remove markdown asterisks
                        clean_text = clean_text.split(':')[0]  # Take only text before colon (remove explanations)
                        clean_text = re.sub(r'\s+', ' ', clean_text)  # Normalize whitespace
                        clean_text = clean_text.strip()
                        if clean_text:
                            rankings.append((rank, clean_text))
                except ValueError:
                    continue
                    
        return rankings
    
    async def parse_principle_choice_enhanced(self, response: str, max_retries: int = 3) -> PrincipleChoice:
        """Simple lookup-based parsing for principle choice - maintains compatibility with enhanced interface."""
        
        try:
            # 1. Find the principle in the response using fuzzy matching
            principle = self._fuzzy_match_principle(response)
            
            if not principle:
                # Try to extract key phrases from the response
                response_lower = response.lower().strip()
                
                # Look for key phrases that might indicate principle
                for phrase in ["my choice is", "i choose", "my preference is", "i prefer", "my selection is"]:
                    if phrase in response_lower:
                        # Extract text after the phrase
                        start_idx = response_lower.find(phrase)
                        text_after = response[start_idx + len(phrase):].strip()
                        principle = self._fuzzy_match_principle(text_after)
                        if principle:
                            break
                
                # If still not found, try splitting response and checking each part
                if not principle:
                    for part in response.split('.'):
                        part = part.strip()
                        if part:
                            principle = self._fuzzy_match_principle(part)
                            if principle:
                                break
            
            if not principle:
                raise ExperimentError(
                    f"Could not identify principle from response",
                    ExperimentErrorCategory.VALIDATION_ERROR,
                    ErrorSeverity.FATAL,
                    {
                        "response_text": response,
                        "operation": "principle_choice_lookup_failure"
                    }
                )
            
            # 2. Extract constraint amount if it's a constraint principle
            constraint_amount = None
            if principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                           JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
                # Look for dollar amounts or numbers in the response
                dollar_matches = re.findall(r'\$(\d{1,6}(?:,\d{3})*|\d{4,6})', response)
                if dollar_matches:
                    try:
                        constraint_amount = int(dollar_matches[0].replace(',', ''))
                    except ValueError:
                        pass
                
                # If no dollar amount, look for bare numbers
                if constraint_amount is None:
                    number_matches = re.findall(r'\b(\d{4,6})\b', response)
                    if number_matches:
                        try:
                            constraint_amount = int(number_matches[0])
                        except ValueError:
                            pass
            
            # 3. Determine certainty level (simple heuristic)
            certainty = CertaintyLevel.SURE  # Default
            response_lower = response.lower()
            if any(word in response_lower for word in ['very unsure', 'extremely uncertain']):
                certainty = CertaintyLevel.VERY_UNSURE
            elif any(word in response_lower for word in ['unsure', 'uncertain', 'not sure']):
                certainty = CertaintyLevel.UNSURE
            elif any(word in response_lower for word in ['no opinion', 'neutral', 'indifferent']):
                certainty = CertaintyLevel.NO_OPINION
            elif any(word in response_lower for word in ['very sure', 'very confident', 'extremely confident']):
                certainty = CertaintyLevel.VERY_SURE
            
            # 4. Create and return the PrincipleChoice
            return PrincipleChoice.create_for_parsing(
                principle=principle,
                constraint_amount=constraint_amount,
                certainty=certainty,
                reasoning=response
            )
            
        except ExperimentError:
            # Re-raise ExperimentErrors as-is
            raise
        except Exception as e:
            # Convert other exceptions to ExperimentError
            raise ExperimentError(
                f"Failed to parse principle choice due to unexpected error: {str(e)}",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.FATAL,
                {
                    "response_text": response,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "operation": "principle_choice_parsing_exception"
                }
            ) from e
    
    
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
        """LLM-first parsing for principle ranking with lookup fallback."""
        
        # Try LLM parsing first (already exists!)
        try:
            llm_result = await self._extract_ranking_llm_fallback(response)
            if llm_result:
                converted_result = self._convert_llm_result_to_principle_ranking(llm_result)
                if converted_result:
                    logger.info("LLM parsing successful")
                    return converted_result
                else:
                    logger.warning("LLM parsing failed validation, falling back to lookup")
        except Exception as e:
            logger.warning(f"LLM parsing failed, falling back to lookup: {e}")
        
        # Fallback to lookup if needed
        return await self._original_lookup_based_parsing(response)

    def _convert_llm_result_to_principle_ranking(self, llm_result: Dict[str, Any]) -> PrincipleRanking:
        """Convert LLM parsing result to PrincipleRanking object."""
        rankings = []
        
        logger.info(f"DEBUG: Converting LLM result: {llm_result}")
        
        for ranking_data in llm_result['rankings']:
            # Map principle name to enum
            principle_name = ranking_data['principle']
            principle = self._map_principle_name_to_enum(principle_name)
            logger.info(f"DEBUG: Mapped principle '{principle_name}' -> {principle}")
            if principle:
                rankings.append(RankedPrinciple(
                    principle=principle,
                    rank=ranking_data['rank']
                ))
        
        logger.info(f"DEBUG: Created {len(rankings)} rankings from {len(llm_result['rankings'])} LLM results")
        
        # Validate we have exactly 4 unique principles
        if len(rankings) != 4:
            logger.warning(f"LLM parsing incomplete: got {len(rankings)} principles, need 4")
            return None
            
        # Check for unique principles
        principles_found = set(r.principle for r in rankings)
        if len(principles_found) != 4:
            logger.warning(f"LLM parsing duplicate principles: {principles_found}")
            return None
        
        # Map certainty
        certainty_str = llm_result.get('certainty', 'sure').lower()
        certainty = self._map_certainty_string_to_enum(certainty_str)
        
        return PrincipleRanking(rankings=rankings, certainty=certainty)

    def _map_principle_name_to_enum(self, principle_name: str) -> Optional[JusticePrinciple]:
        """Map principle name from any language to JusticePrinciple enum."""
        if not principle_name:
            return None
            
        principle_str = principle_name.lower().strip()
        
        # Multi-language mapping for principle names to enum values
        principle_mappings = {
            # English variations
            'maximizing_floor': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing_average': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing_average_floor_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximizing_average_range_constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Full English names
            'maximizing the floor income': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximizing the average income': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximizing the average income with a floor constraint': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximizing the average income with a range constraint': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Spanish variations
            'maximización del ingreso mínimo': JusticePrinciple.MAXIMIZING_FLOOR,
            'maximización del ingreso promedio': JusticePrinciple.MAXIMIZING_AVERAGE,
            'maximización del ingreso promedio con restricción de ingreso mínimo': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            'maximización del ingreso promedio con restricción de rango': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            
            # Mandarin variations  
            '最大化最低收入': JusticePrinciple.MAXIMIZING_FLOOR,
            '最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE,
            '在最低收入约束条件下最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            '在范围约束条件下最大化平均收入': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
        }
        
        # Direct lookup
        principle = principle_mappings.get(principle_str)
        if principle:
            return principle
            
        # Fuzzy matching for partial matches
        for key, enum_val in principle_mappings.items():
            if key in principle_str or principle_str in key:
                # Ensure substantial match (>50% overlap)
                shorter_len = min(len(key), len(principle_str))
                longer_len = max(len(key), len(principle_str))
                if shorter_len / longer_len > 0.5:
                    return enum_val
        
        logger.warning(f"Failed to map principle name '{principle_name}' to enum")
        return None

    def _map_certainty_string_to_enum(self, certainty_str: str) -> CertaintyLevel:
        """Map certainty string from any language to CertaintyLevel enum."""
        if not certainty_str:
            return CertaintyLevel.SURE
            
        certainty_lower = certainty_str.lower().strip()
        
        # Multi-language certainty mapping
        certainty_mappings = {
            # English
            'very_unsure': CertaintyLevel.VERY_UNSURE,
            'very unsure': CertaintyLevel.VERY_UNSURE,
            'unsure': CertaintyLevel.UNSURE,
            'no_opinion': CertaintyLevel.NO_OPINION, 
            'no opinion': CertaintyLevel.NO_OPINION,
            'sure': CertaintyLevel.SURE,
            'very_sure': CertaintyLevel.VERY_SURE,
            'very sure': CertaintyLevel.VERY_SURE,
            
            # Spanish
            'muy_inseguro': CertaintyLevel.VERY_UNSURE,
            'muy inseguro': CertaintyLevel.VERY_UNSURE,
            'inseguro': CertaintyLevel.UNSURE,
            'sin_opinion': CertaintyLevel.NO_OPINION,
            'sin opinion': CertaintyLevel.NO_OPINION,
            'seguro': CertaintyLevel.SURE,
            'muy_seguro': CertaintyLevel.VERY_SURE,
            'muy seguro': CertaintyLevel.VERY_SURE,
            
            # Mandarin
            '非常不确定': CertaintyLevel.VERY_UNSURE,
            '不确定': CertaintyLevel.UNSURE,
            '无意见': CertaintyLevel.NO_OPINION,
            '确定': CertaintyLevel.SURE,
            '非常确定': CertaintyLevel.VERY_SURE,
        }
        
        mapped_certainty = certainty_mappings.get(certainty_lower)
        if mapped_certainty:
            return mapped_certainty
            
        # Default to SURE if no mapping found
        logger.warning(f"Failed to map certainty '{certainty_str}' to enum, defaulting to SURE")
        return CertaintyLevel.SURE

    async def _original_lookup_based_parsing(self, response: str) -> PrincipleRanking:
        """Original lookup-based parsing as fallback."""
        
        try:
            # 1. Extract numbered list from response using existing regex
            numbered_items = self._extract_numbered_list(response)
            
            if len(numbered_items) < 4:
                # Try alternative extraction if numbered list fails
                numbered_items = []
                lines = response.split('\n')
                rank = 1
                for line in lines:
                    line = line.strip()
                    if line and rank <= 4:
                        # Try to extract principle text from line
                        # Remove common prefixes like "1.", "Rank 1:", etc.
                        cleaned = re.sub(r'^\d+[\.\:\)\s]*', '', line).strip()
                        cleaned = re.sub(r'^(rank|preference)\s*\d*[\.\:\)\s]*', '', cleaned, flags=re.IGNORECASE).strip()
                        if cleaned:
                            numbered_items.append((rank, cleaned))
                            rank += 1
            
            # 2. Map each text to principle using lookup table
            mapped_rankings = []
            for rank, text in numbered_items[:4]:  # Only take first 4
                principle = self._fuzzy_match_principle(text)
                if principle:
                    mapped_rankings.append(RankedPrinciple(principle=principle, rank=rank))
            
            # 3. Validate we have exactly 4 unique principles
            if len(mapped_rankings) == 4:
                # Check for unique principles
                principles_found = set(r.principle for r in mapped_rankings)
                if len(principles_found) == 4:
                    # Sort by rank to ensure proper ordering
                    mapped_rankings.sort(key=lambda x: x.rank)
                    
                    # Determine overall certainty (simple heuristic)
                    certainty = CertaintyLevel.SURE  # Default
                    response_lower = response.lower()
                    if any(word in response_lower for word in ['very unsure', 'extremely uncertain']):
                        certainty = CertaintyLevel.VERY_UNSURE
                    elif any(word in response_lower for word in ['unsure', 'uncertain', 'not sure']):
                        certainty = CertaintyLevel.UNSURE
                    elif any(word in response_lower for word in ['no opinion', 'neutral', 'indifferent']):
                        certainty = CertaintyLevel.NO_OPINION
                    elif any(word in response_lower for word in ['very sure', 'very confident', 'extremely confident']):
                        certainty = CertaintyLevel.VERY_SURE
                    
                    return PrincipleRanking(rankings=mapped_rankings, certainty=certainty)
            
            # If we reach here, parsing failed
            raise ExperimentError(
                f"Failed to parse principle ranking: found {len(mapped_rankings)} valid principles, need 4 unique ones",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.FATAL,
                {
                    "response_text": response,
                    "numbered_items_found": len(numbered_items),
                    "valid_mappings_found": len(mapped_rankings),
                    "operation": "principle_ranking_lookup_failure",
                    "extracted_items": [text for _, text in numbered_items[:4]]
                }
            )
            
        except ExperimentError:
            # Re-raise ExperimentErrors as-is
            raise
        except Exception as e:
            # Convert other exceptions to ExperimentError
            raise ExperimentError(
                f"Failed to parse principle ranking due to unexpected error: {str(e)}",
                ExperimentErrorCategory.VALIDATION_ERROR,
                ErrorSeverity.FATAL,
                {
                    "response_text": response,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "operation": "principle_ranking_parsing_exception"
                }
            ) from e
    
    async def _extract_ranking_direct(self, response: str) -> Optional[Dict[str, Any]]:
        """Direct pattern matching for principle ranking using LLM-based parsing."""
        
        rankings = []
        
        # Look for numbered list format
        ranking_matches = self._language_patterns['ranking_line'].findall(response)
        
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
    
    async def _extract_ranking_llm_fallback(self, response: str) -> Optional[Dict[str, Any]]:
        """Fallback LLM-based parsing for principle ranking when pattern matching fails."""
        try:
            # Use the parser agent to extract ranking structure
            language_manager = get_language_manager()
            
            # CRITICAL FIX: Set language manager to correct language before LLM call
            original_language = language_manager.current_language
            experiment_lang_enum = self._get_supported_language_enum()
            if experiment_lang_enum:
                language_manager.set_language(experiment_lang_enum)
            
            try:
                parsing_prompt = language_manager.get("prompts.utility_parse_principle_ranking").format(
                    response=response
                )
            finally:
                # Always restore original language
                language_manager.set_language(original_language)
            
            result = await Runner.run(self.parser_agent, parsing_prompt)
            parsed_text = result.final_output.strip()
            
            # Try to parse as JSON first
            try:
                import json
                ranking_data = json.loads(parsed_text)
                if isinstance(ranking_data, dict) and 'rankings' in ranking_data:
                    # Validate that we have 4 rankings
                    if len(ranking_data['rankings']) == 4:
                        # CRITICAL FIX: Map principle names and certainty to English before returning
                        for ranking in ranking_data['rankings']:
                            original_principle = ranking['principle']
                            mapped_principle = await self._map_principle_name_to_english(original_principle)
                            ranking['principle'] = mapped_principle
                            logger.debug(f"Mapped principle: '{original_principle}' -> '{mapped_principle}'")
                        
                        # Also map certainty level to English
                        if 'certainty' in ranking_data:
                            original_certainty = ranking_data['certainty']
                            mapped_certainty = self._map_certainty_to_english(original_certainty)
                            ranking_data['certainty'] = mapped_certainty
                            logger.debug(f"Mapped certainty: '{original_certainty}' -> '{mapped_certainty}'")
                        
                        return ranking_data
            except json.JSONDecodeError:
                pass
            
            # If JSON parsing fails, try to extract from text format
            return await self._parse_ranking_from_text_fallback(parsed_text)
            
        except Exception as e:
            logger.warning(f"LLM fallback ranking parsing failed: {e}")
            return None
    
    def _get_supported_language_enum(self) -> Optional[SupportedLanguage]:
        """Map experiment_language string to SupportedLanguage enum."""
        language_map = {
            "english": SupportedLanguage.ENGLISH,
            "spanish": SupportedLanguage.SPANISH,
            "mandarin": SupportedLanguage.MANDARIN
        }
        return language_map.get(self.experiment_language.lower()) if self.experiment_language else None
    
    async def _map_principle_name_to_english(self, principle_name: str) -> str:
        """Map principle name from any language to English enum value."""
        # If it's already an English enum value, return as-is
        if principle_name in ['maximizing_floor', 'maximizing_average', 
                            'maximizing_average_floor_constraint', 'maximizing_average_range_constraint']:
            return principle_name
        
        # Try to identify the principle using existing multilingual mapping
        mapped_principle = await self._identify_principle_in_text(principle_name)
        if mapped_principle:
            return mapped_principle
            
        # If identification fails, log and return original (will cause error but is traceable)
        logger.warning(f"Failed to map principle name to English: '{principle_name}'")
        return principle_name
    
    def _map_certainty_to_english(self, certainty: str) -> str:
        """Map certainty level from any language to English enum value."""
        # Direct English mappings
        if certainty in ['very_unsure', 'unsure', 'sure', 'very_sure']:
            return certainty
        
        # Spanish mappings
        spanish_certainty_map = {
            'muy_inseguro': 'very_unsure',
            'inseguro': 'unsure', 
            'seguro': 'sure',
            'muy_seguro': 'very_sure'
        }
        
        # Mandarin mappings
        mandarin_certainty_map = {
            '很不确定': 'very_unsure',
            '不确定': 'unsure',
            'sure': 'sure',  # Sometimes mixed
            '很确定': 'very_sure'
        }
        
        # Try mappings
        mapped = spanish_certainty_map.get(certainty) or mandarin_certainty_map.get(certainty)
        if mapped:
            return mapped
            
        # If no mapping found, log and default to 'sure'
        logger.warning(f"Failed to map certainty level '{certainty}' to English, defaulting to 'sure'")
        return 'sure'
    
    def _with_language_context(self, language_manager, func):
        """Context manager to temporarily set language manager to utility agent's language."""
        class LanguageContext:
            def __init__(self, lang_manager, lang_enum):
                self.lang_manager = lang_manager
                self.lang_enum = lang_enum
                self.original_language = None
                
            def __enter__(self):
                self.original_language = self.lang_manager.current_language
                if self.lang_enum:
                    self.lang_manager.set_language(self.lang_enum)
                return self.lang_manager
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.original_language:
                    self.lang_manager.set_language(self.original_language)
        
        experiment_lang_enum = self._get_supported_language_enum()
        return LanguageContext(language_manager, experiment_lang_enum)
    
    async def _parse_ranking_from_text_fallback(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse ranking from text format as final fallback."""
        rankings = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for patterns like "1. Principle Name" or "Rank 1: Principle"
            # re already imported at module level
            match = re.match(r'(?:rank\s*)?(\d+)\.?\s*:?\s*(.+)', line, re.IGNORECASE)
            if match:
                rank_num = int(match.group(1))
                principle_text = match.group(2).strip()
                
                # Try to identify the principle
                principle = await self._identify_principle_in_text(principle_text)
                if principle and 1 <= rank_num <= 4:
                    rankings.append({
                        'principle': principle,
                        'rank': rank_num
                    })
        
        # Check if we have exactly 4 unique rankings
        if len(rankings) == 4:
            ranks = [r['rank'] for r in rankings]
            if len(set(ranks)) == 4 and all(1 <= r <= 4 for r in ranks):
                return {
                    'rankings': rankings,
                    'certainty': 'sure'  # Default certainty for fallback
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
            choice_data = await self.parse_principle_choice_llm(focus_text, max_retries=3)
            if choice_data:
                return choice_data['principle']
        except Exception:
            pass
        
        # Fallback to full text LLM parsing if focus text doesn't work
        try:
            choice_data = await self.parse_principle_choice_llm(text, max_retries=3)
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
    
    

    
    
    # ========================================
    # NEW LLM-BASED PARSING METHODS
    # ========================================
    
    
    def _preprocess_multilingual_response(self, response: str, language: str) -> str:
        """Preprocess response text based on language for better parsing."""
        import unicodedata
        # re already imported at module level
        
        # Unicode normalization for all languages
        response = unicodedata.normalize('NFKC', response)
        
        if language == "mandarin":
            # Handle Mandarin-specific preprocessing
            # Replace Chinese punctuation with standard punctuation
            response = response.replace('，', ',').replace('。', '.').replace('：', ':')
            # Remove mixed ASCII artifacts that might be leftover from contamination
            response = re.sub(r'Original response:\s*', '', response, flags=re.IGNORECASE)
            # Clean up common Chinese response patterns
            response = re.sub(r'^(回复|答案|响应)[：:\s]*', '', response.strip())
            
        elif language == "spanish":
            # Handle Spanish-specific preprocessing
            # Remove contamination artifacts in Spanish
            response = re.sub(r'Original response:\s*', '', response, flags=re.IGNORECASE)
            # Clean up Spanish response patterns
            response = re.sub(r'^(Respuesta|Mi respuesta|La respuesta)[：:\s]*', '', response.strip())
            # Preserve Spanish accent marks properly
            
        else:  # English
            # Handle English preprocessing
            # Remove contamination artifacts
            response = re.sub(r'Original response:\s*', '', response, flags=re.IGNORECASE)
            # Clean up English response patterns
            response = re.sub(r'^(Response|My response|Answer)[：:\s]*', '', response.strip())
        
        # Common cleanup for all languages
        response = response.strip()
        
        return response
    
    async def _parse_llm_principle_response(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from utility agent LLM with multilingual support."""
        import json
        import unicodedata
        try:
            # MULTILINGUAL ENHANCEMENT: Apply language-specific preprocessing
            response_stripped = self._preprocess_multilingual_response(llm_response, self.experiment_language or "english")
            
            # Remove common LLM artifacts that might interfere with JSON parsing
            artifacts_to_remove = [
                "Here is the JSON:", "JSON response:", "Response:", "Answer:",
                "这是JSON:", "回复:", "答案:", "Respuesta:", "JSON respuesta:"
            ]
            for artifact in artifacts_to_remove:
                response_stripped = response_stripped.replace(artifact, "").strip()
            
            # Enhanced JSON boundary detection with better error handling
            start_idx = response_stripped.find('{')
            end_idx = response_stripped.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                # Try alternative JSON markers in case of formatting issues
                json_patterns = [
                    r'\{[^{}]*"principle"[^{}]*"constraint_amount"[^{}]*"certainty"[^{}]*\}',
                    r'\{.*?"principle".*?\}',
                ]
                # re already imported at module level
                for pattern in json_patterns:
                    match = re.search(pattern, response_stripped, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                        try:
                            parsed_json = json.loads(json_str)
                            if 'principle' in parsed_json:
                                break
                        except json.JSONDecodeError:
                            continue
                else:
                    logger.warning(f"No JSON found in LLM response (multilingual): {response_stripped[:100]}...")
                    return None
            else:
                json_str = response_stripped[start_idx:end_idx + 1]
            
            # Parse the JSON
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
                fallback_amount = await self.parse_constraint_amount(llm_response, self.experiment_language)
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
            # Get the LLM constraint parsing prompt with correct language context
            language_manager = get_language_manager()
            with self._with_language_context(language_manager, None) as lm:
                parsing_prompt = lm.get(
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
                # re already imported at module level
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
                    # Extract constraint amount using multilingual method with configured language
                    constraint_amount = await self.parse_constraint_amount(preference_text, self.experiment_language)
                    if not constraint_amount:
                        constraint_amount = await self.parse_constraint_amount(statement, self.experiment_language)
                    
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
                    constraint_amount = await self.parse_constraint_amount(statement, self.experiment_language)
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
            choice_data = await self.parse_principle_choice_llm(principle_text, max_retries=3)
            if choice_data:
                return JusticePrinciple(choice_data['principle'])
        except Exception:
            pass
        
        return None
    
    async def parse_constraint_amount(self, constraint_text: str, language: str = None) -> Optional[int]:
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
            language: Optional language override (defaults to experiment language)
        
        Returns:
            Parsed amount as integer, or None if no valid amount found
        """
        if not constraint_text or constraint_text.strip() == "":
            return None
        
        # Get language manager for prompt construction
        language_manager = get_language_manager()
        
        parsing_prompt = f"""You are an expert at parsing constraint amounts from multilingual text with specialized Spanish language expertise.

PARSE CONSTRAINT AMOUNT from: "{constraint_text}"
Language: {language or self.experiment_language}

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
            
            # Parse the numeric response (handle both int and float)
            try:
                # Try parsing as float first, then convert to int to handle "2500.0" format
                amount = int(float(response))
                if amount > 0:
                    # Validate constraint scale
                    # Validate constraint amount using merged logic
                    MIN_INCOME_CONSTRAINT = 1000
                    LIKELY_PAYOFF_SCALE_MAX = 10
                    if amount <= LIKELY_PAYOFF_SCALE_MAX or amount < MIN_INCOME_CONSTRAINT:
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
    
    async def parse_constraint_amount_multilingual(self, constraint_text: str, language_hint: str = None) -> Optional[int]:
        """
        Multilingual constraint amount parsing method.
        This is an alias for parse_constraint_amount() for backward compatibility.
        
        Args:
            constraint_text: Text containing constraint amount to parse
            language_hint: Optional language hint (used as language parameter)
        
        Returns:
            Parsed amount as integer, or None if no valid amount found
        """
        return await self.parse_constraint_amount(constraint_text, language_hint)
    
    async def validate_ballot_parsing_consistency(self, raw_response: str, parsed_result: Dict[str, Any], language: str = "english") -> bool:
        """
        Validate ballot parsing matches expected patterns to catch systematic errors.
        
        Args:
            raw_response: Original ballot text from agent
            parsed_result: Dictionary result from parse_principle_choice_llm
            language: Language to use for validation patterns
            
        Returns:
            bool: True if parsing appears consistent, False if potential mismatch detected
        """
        if not parsed_result or 'principle' not in parsed_result:
            logger.warning(f"🚫 VALIDATION: Invalid parsed result: {parsed_result}")
            return False
            
        principle_result = parsed_result['principle']
        response_lower = raw_response.lower().strip()
        
        # English validation patterns
        english_patterns = {
            "maximizing the floor income": "maximizing_floor",
            "maximizing the average income": "maximizing_average", 
            "maximizing floor income": "maximizing_floor",
            "maximizing average income": "maximizing_average",
            "maximizing average with floor constraint": "maximizing_average_floor_constraint",
            "maximizing average with range constraint": "maximizing_average_range_constraint",
            "floor constraint": "maximizing_average_floor_constraint",
            "range constraint": "maximizing_average_range_constraint"
        }
        
        # Spanish validation patterns (enhanced for Phase 2)
        spanish_patterns = {
            # Basic principles - DEL indicates basic principle
            "maximización del ingreso mínimo": "maximizing_floor",
            "maximización del ingreso promedio": "maximizing_average",
            "maximizar los ingresos mínimos": "maximizing_floor", 
            "maximizar los ingresos promedio": "maximizing_average",
            
            # Constraint indicators - CON/con indicates constraint principle  
            # Specific constraint types (more specific patterns first)
            "maximización del promedio con restricción de rango": "maximizing_average_range_constraint",
            "restricción de rango": "maximizing_average_range_constraint",
            "con restricción de rango": "maximizing_average_range_constraint",
            "maximización del promedio con restricción de ingreso mínimo": "maximizing_average_floor_constraint",
            "restricción de ingreso mínimo": "maximizing_average_floor_constraint",
            "con restricción de ingreso mínimo": "maximizing_average_floor_constraint"
        }
        
        # Mandarin validation patterns (enhanced for Phase 2)
        mandarin_patterns = {
            # Basic principles - direct phrases indicate basic principles
            "最大化最低收入": "maximizing_floor",
            "最低收入最大化": "maximizing_floor",
            "平均收入最大化": "maximizing_average", 
            
            # Constraint indicators - 约束条件 indicates constraint principle
            # Specific constraint types (more specific patterns first)
            "在范围约束条件下": "maximizing_average_range_constraint",
            "在最低收入约束条件下": "maximizing_average_floor_constraint", 
            "范围约束条件下最大化平均收入": "maximizing_average_range_constraint",
            "最低收入约束条件下最大化平均收入": "maximizing_average_floor_constraint",
            "范围约束": "maximizing_average_range_constraint",
            "最低收入约束": "maximizing_average_floor_constraint"
        }
        
        # Select appropriate patterns based on language
        validation_patterns = {
            "english": english_patterns,
            "spanish": spanish_patterns, 
            "mandarin": mandarin_patterns
        }.get(language.lower(), english_patterns)
        
        # Check for obvious mismatches - sort by specificity (longer patterns first)
        sorted_patterns = sorted(validation_patterns.items(), key=lambda x: len(x[0]), reverse=True)
        
        for pattern, expected_principle in sorted_patterns:
            if pattern in response_lower:
                if principle_result != expected_principle:
                    logger.error(f"🚫 BALLOT PARSING MISMATCH [{language.upper()}]: "
                               f"'{raw_response}' contains '{pattern}' but parsed as '{principle_result}', "
                               f"expected '{expected_principle}'")
                    return False
                # Match found and correct, no need to check less specific patterns
                break
                    
        # Check for critical disambiguation errors
        critical_mismatches = [
            # Basic principles incorrectly parsed as constraint principles
            ("maximizing the floor income", "maximizing_average_floor_constraint"),
            ("maximizing the average income", "maximizing_average_floor_constraint"),
            ("maximizing the floor income", "maximizing_average_range_constraint"),
            ("maximizing the average income", "maximizing_average_range_constraint"),
        ]
        
        for phrase, wrong_parsing in critical_mismatches:
            if phrase in response_lower and principle_result == wrong_parsing:
                logger.error(f"🚫 CRITICAL PARSING ERROR: '{raw_response}' contains '{phrase}' "
                           f"but was parsed as '{wrong_parsing}' - this is the systematic error we fixed!")
                return False
        
        return True
    
    
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
        
        # Use existing multilingual parsing with configured language
        try:
            amount = await self.parse_constraint_amount(constraint_text, self.experiment_language)
            if amount and amount > 0:
                # Validate constraint amount scale  
                # Validate constraint amount using merged logic
                MIN_INCOME_CONSTRAINT = 1000
                LIKELY_PAYOFF_SCALE_MAX = 10
                if amount <= LIKELY_PAYOFF_SCALE_MAX or amount < MIN_INCOME_CONSTRAINT:
                    logger.warning(f"Flexible extraction found amount ${amount} but it failed scale validation")
                    return None
                
                logger.info(f"Flexible constraint extraction successful: {amount} from '{constraint_text}'")
                return amount
            return None
        except Exception as e:
            logger.warning(f"Flexible constraint extraction failed: {e}")
            return None
    
    
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
