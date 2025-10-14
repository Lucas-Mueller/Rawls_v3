"""
Discussion Service for Phase 2 Discussion Management.

Handles discussion prompts, statement validation, and group composition formatting
with multilingual support and language-aware validation.
"""

import asyncio
import re
from typing import List, Optional, Protocol, Tuple, Any, Callable, Awaitable
from utils.logging import run_with_transcript_logging
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState
from utils.statement_validation_errors import StatementValidationFailureType


class LanguageProvider(Protocol):
    """Protocol for language managers that provide localized messages."""
    def get(self, key: str, **kwargs) -> str:
        """Get localized message with substitutions."""
        ...


class Logger(Protocol):
    """Protocol for logging information and warnings."""
    def log_info(self, message: str) -> None:
        """Log an info message."""
        ...
    
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        ...


class ParticipantAgent(Protocol):
    """Protocol for participant agents."""
    agent: Any  # OpenAI Agent
    name: str


class ParticipantContext(Protocol):
    """Protocol for participant context."""
    round_number: int
    interaction_type: Optional[str]
    role_description: str


class AgentConfiguration(Protocol):
    """Protocol for agent configuration."""
    language: str
    reasoning_enabled: bool


class DiscussionService:
    """
    Manages discussion prompts, statement validation, and group composition formatting.
    
    Provides centralized discussion/reasoning prompt generation with multilingual support
    and language-aware statement validation.
    """
    
    def __init__(self, language_manager: LanguageProvider, settings: Optional[Phase2Settings] = None,
                 logger: Optional[Logger] = None, transcript_logger=None):
        """
        Initialize discussion service.
        
        Args:
            language_manager: For localized message retrieval
            settings: Phase 2 settings for validation rules (optional)
            logger: For logging info and warnings (optional)
        """
        self.language_manager = language_manager
        self.settings = settings or Phase2Settings.get_default()
        self.logger = logger
        self.transcript_logger = transcript_logger
        
        # Discussion history management settings - now configurable through Phase2Settings
        # Use the configurable public_history_max_length from settings
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger is available."""
        if self.logger:
            self.logger.log_info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log warning message if logger is available."""
        if self.logger:
            self.logger.log_warning(message)

    async def _invoke_discussion_interaction(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        prompt: str,
        interaction_type: str,
        timeout_seconds: Optional[float] = None
    ):
        """Execute a participant interaction with transcript logging and optional timeout."""
        context.interaction_type = interaction_type
        coroutine = run_with_transcript_logging(
            participant=participant,
            prompt=prompt,
            context=context,
            transcript_logger=self.transcript_logger,
            interaction_type=interaction_type
        )

        if timeout_seconds is not None:
            return await asyncio.wait_for(coroutine, timeout_seconds)
        return await coroutine

    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message with fallback handling."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self._log_warning(f"Missing translation key: {key} - {str(e)}")
            # Return English fallback or key name
            return f"[MISSING: {key}]"

    @staticmethod
    def _strip_markdown_emphasis(text: str) -> str:
        """Remove Markdown bold/italic markers for cleaner prompts."""
        if not text:
            return text

        pattern = re.compile(r"(\*\*|__)(.+?)(\1)", flags=re.DOTALL)
        return pattern.sub(r"\2", text)
    
    def _build_manipulator_reasoning_note(self, context: Optional[ParticipantContext]) -> Optional[str]:
        """
        Build a round-one reminder for manipulators to keep the injected target in focus.
        """
        if context is None:
            return None

        role_description = getattr(context, "role_description", "")
        if not role_description:
            return None

        headers_to_check: List[str] = []
        try:
            headers_to_check.append(self.language_manager.get("manipulator.target_header"))
        except Exception:
            pass
        headers_to_check.append("**MANIPULATOR TARGET**")

        if not any(header and header in role_description for header in headers_to_check if header):
            return None

        principle_slug = self._extract_manipulator_principle_slug(role_description)
        if not principle_slug:
            return None

        principle_display = self._format_principle_display_name(principle_slug)

        try:
            return self.language_manager.get(
                "manipulator.reasoning_target_reminder",
                principle_name=principle_display
            )
        except Exception:
            return f"Reminder: Your manipulator target is {principle_display}. Keep steering consensus toward this exact outcome."

    def _extract_manipulator_principle_slug(self, role_description: str) -> Optional[str]:
        """
        Parse the injected manipulator target principle slug from the role description.
        """
        if not role_description:
            return None

        lines = role_description.splitlines()

        try:
            template = self.language_manager.get("manipulator.target_principle_line", principle="{principle}")
        except Exception:
            template = "Principle: {principle}"

        placeholder = "{principle}"
        if placeholder not in template:
            template = "Principle: {principle}"

        prefix, suffix = template.split(placeholder)
        prefix = prefix.strip()
        suffix = suffix.strip()

        for raw in lines:
            stripped = raw.strip()
            if prefix and not stripped.startswith(prefix):
                continue
            if suffix and not stripped.endswith(suffix):
                continue
            start = len(prefix)
            end = len(stripped) - len(suffix) if suffix else len(stripped)
            candidate = stripped[start:end].strip()
            if candidate:
                return candidate

        for raw in lines:
            stripped = raw.strip()
            if stripped.lower().startswith("principle:"):
                return stripped.split(":", 1)[1].strip()

        return None

    def _format_principle_display_name(self, slug: str) -> str:
        """
        Convert a principle slug to a localized display name for prompts.
        """
        key_map = {
            "maximizing_floor": "common.principle_names.maximizing_floor",
            "maximizing_average": "common.principle_names.maximizing_average",
            "maximizing_average_floor_constraint": "common.principle_names.maximizing_average_floor_constraint",
            "maximizing_average_range_constraint": "common.principle_names.maximizing_average_range_constraint",
        }

        translation_key = key_map.get(slug)
        if translation_key:
            try:
                return self.language_manager.get(translation_key)
            except Exception:
                pass

        return slug.replace("_", " ").strip().title()
    
    def build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                               max_rounds: int, participant_names: List[str],
                               internal_reasoning: str = "") -> str:
        """
        Build localized discussion prompt without embedding transcript (history is in instructions).
        
        Args:
            discussion_state: Current discussion state with history
            round_num: Current round number (1-based)
            max_rounds: Maximum number of rounds
            participant_names: List of participant names for group composition
            internal_reasoning: Optional internal reasoning (not used in input prompt to avoid duplication)
            
        Returns:
            Formatted discussion prompt with group composition (reasoning handled by system context)
        """
        language_manager = self.language_manager

        # Use short, task-focused prompt. Discussion transcript and round info are provided via context header.
        return language_manager.get(
            "prompts.phase2_discussion_short_prompt"
        )
    
    def build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int,
                                      max_rounds: int, context: Optional[ParticipantContext] = None) -> str:
        """
        Build prompt for internal reasoning before public statement.

        Args:
            discussion_state: Current discussion state with history
            round_num: Current round number (1-based)
            max_rounds: Maximum number of rounds

        Returns:
            Formatted internal reasoning prompt

        Note: DEFENSIVE stripping applied even though stripping happens at source,
        to protect against edge cases, old data, or direct assignments to public_history.
        """
        language_manager = self.language_manager

        # Use full prompt with Phase 2 explanation for first round only
        if round_num == 1:
            history_value = discussion_state.public_history if discussion_state.public_history and discussion_state.public_history.strip() else self._get_localized_message("no_previous_discussion_placeholder")
            # DEFENSIVE: Strip markdown even though it should be clean
            history_value = self._strip_markdown_emphasis(history_value)
            prompt = language_manager.get(
                "prompts.phase2_internal_reasoning",
                discussion_history=history_value,
                round_number=round_num,
                max_rounds=max_rounds
            )

            reminder = self._build_manipulator_reasoning_note(context)
            if reminder:
                prompt = f"{prompt}\n\n{reminder}"
            return prompt
        else:
            return language_manager.get(
                "prompts.phase2_internal_reasoning_short",
                round_number=round_num,
                max_rounds=max_rounds
            )
    
    def format_group_composition(self, participant_names: List[str]) -> str:
        """
        Format localized group composition message.
        
        Args:
            participant_names: List of participant names
            
        Returns:
            Formatted group composition message with proper localization
        """
        if not participant_names:
            return ""
        
        if len(participant_names) == 1:
            participant_list = participant_names[0]
        elif len(participant_names) == 2:
            try:
                participant_list = self._get_localized_message(
                    "common.list_formatting.two_items",
                    first=participant_names[0],
                    second=participant_names[1]
                )
            except Exception:
                participant_list = f"{participant_names[0]} and {participant_names[1]}"
        else:
            try:
                participant_list = self._get_localized_message(
                    "common.list_formatting.three_plus_items",
                    items=", ".join(participant_names[:-1]),
                    last=participant_names[-1]
                )
            except Exception:
                try:
                    conjunction = self._get_localized_message("common.list_formatting.conjunction")
                except Exception:
                    conjunction = "and"
                participant_list = ", ".join(participant_names[:-1]) + f" {conjunction} {participant_names[-1]}"

        return self._get_localized_message(
            "system_messages.discussion.group_composition", 
            participants=participant_list
        )
    
    def validate_statement(self, statement: str, participant_name: str, language: str) -> bool:
        """
        Validate that a statement is non-empty and meaningful with language awareness.
        
        Reuses existing validation logic with language-aware minimum length checking.
        
        Args:
            statement: The statement to validate
            participant_name: Name of the participant for logging
            language: Language being used (for appropriate minimum length)
            
        Returns:
            True if statement is valid, False otherwise
        """
        if not statement:
            self._log_warning(f"Empty statement received from {participant_name}")
            return False
            
        if not statement.strip():
            self._log_warning(f"Whitespace-only statement received from {participant_name}")
            return False
        
        # Get language-appropriate minimum length
        min_length = self.settings.get_min_statement_length(language)
        
        # Count actual characters (handle multi-byte characters properly)
        statement_length = len(statement.strip())
        
        # Check for minimum meaningful content 
        if statement_length < min_length:
            self._log_warning(f"Statement too short from {participant_name}: '{statement.strip()[:50]}...' ({statement_length} chars, min: {min_length})")
            return False
            
        self._log_info(f"Valid statement received from {participant_name} ({statement_length} characters, language: {language})")
        return True

    def generate_statement_validation_feedback(
        self,
        original_statement: str,
        failure_type: StatementValidationFailureType,
        attempt_number: int,
        min_required_length: int,
        language: str = "english"
    ) -> str:
        """
        Generate contextual feedback for statement validation failures.

        Follows exact pattern of UtilityAgent.generate_parsing_feedback() but for statements.
        Provides specific guidance based on the failure type to help participants improve.

        Args:
            original_statement: The statement that failed validation
            failure_type: Type of validation failure
            attempt_number: Current attempt number (1-based)
            min_required_length: Minimum required length for statements
            language: Language for localized feedback

        Returns:
            Formatted feedback message for the participant
        """
        # Map failure types to template keys
        failure_type_keys = {
            StatementValidationFailureType.TOO_SHORT: "too_short",
            StatementValidationFailureType.EMPTY_RESPONSE: "empty_response",
            StatementValidationFailureType.MINIMAL_CONTENT: "minimal_content"
        }

        template_key = failure_type_keys.get(failure_type, "too_short")

        # Get language-specific templates from language manager
        try:
            template = {
                "explanation": self._get_localized_message(f"statement_validation_feedback.{template_key}.explanation"),
                "instruction": self._get_localized_message(f"statement_validation_feedback.{template_key}.instruction"),
                "example": self._get_localized_message(f"statement_validation_feedback.{template_key}.example")
            }
        except Exception as e:
            # Fallback to English hard-coded templates
            fallback_templates = {
                "too_short": {
                    "explanation": "Your statement needs to be more detailed for meaningful discussion.",
                    "instruction": f"Please provide at least {min_required_length} characters explaining your reasoning or perspective.",
                    "example": "Example: I believe we should focus on maximizing average income because it provides the best overall outcome for our group while still considering fairness."
                },
                "empty_response": {
                    "explanation": "No statement was provided for this discussion round.",
                    "instruction": "Please share your thoughts, analysis, or preferences regarding the justice principles being discussed.",
                    "example": "Example: Based on our discussion, I think the floor constraint approach is most appropriate because it ensures basic security for everyone."
                },
                "minimal_content": {
                    "explanation": "While your agreement is noted, discussion benefits from detailed reasoning.",
                    "instruction": "Please explain your reasoning and add your analysis to help the group reach consensus.",
                    "example": "Example: I agree with the previous point about floor constraints because they provide essential security while still allowing for economic growth."
                }
            }
            template = fallback_templates.get(template_key, fallback_templates["too_short"])

        # Build feedback message with language-specific phrases (exact A1/A2 pattern)
        try:
            attempt_phrase = self._get_localized_message(
                "statement_validation_feedback.attempt_label",
                attempt_number=attempt_number
            )
        except Exception:
            attempt_phrase = f"Attempt {attempt_number}"

        try:
            validation_issue_phrase = self._get_localized_message(
                "statement_validation_feedback.issue_heading"
            )
        except Exception:
            validation_issue_phrase = "Statement Issue"

        feedback_parts = [
            f"⚠️ {validation_issue_phrase} ({attempt_phrase}):",
            "",
            template["explanation"],
            "",
            template["instruction"],
            "",
            "💡 " + template["example"]
        ]

        # Add statement preview for context
        if original_statement and len(original_statement.strip()) > 0:
            try:
                statement_preview_phrase = self._get_localized_message(
                    "statement_validation_feedback.preview_label"
                )
            except Exception:
                statement_preview_phrase = "Your statement"

            preview = original_statement[:50] + "..." if len(original_statement) > 50 else original_statement
            feedback_parts.extend([
                "",
                f"🔍 {statement_preview_phrase}: \"{preview}\""
            ])

        return "\n".join(feedback_parts)

    def is_cjk_language(self, language: str) -> bool:
        """
        Check if language uses CJK characters.
        
        Args:
            language: Language name to check
            
        Returns:
            True if language uses CJK characters
        """
        return self.settings.is_cjk_language(language)
    
    def get_min_statement_length(self, language: str) -> int:
        """
        Get minimum statement length based on language.
        
        Args:
            language: Language name
            
        Returns:
            Minimum character length for valid statements in this language
        """
        return self.settings.get_min_statement_length(language)
    
    def _create_statement_memory_content(self, prompt: str, statement: str, round_number: int) -> str:
        """Create formatted memory content for statement round."""
        return f"""{self._get_localized_message('memory_field_labels.prompt')} {prompt}
{self._get_localized_message('memory_field_labels.your_statement')} {statement}
{self._get_localized_message('memory_field_labels.outcome')} {self._get_localized_message('memory_outcomes.made_discussion_statement', round_number=round_number)}"""
    
    def _get_agent_language(self, agent_config: AgentConfiguration) -> str:
        """Extract language from agent configuration."""
        return getattr(agent_config, 'language', 'english')  # Default fallback
    
    def should_use_reasoning(self, agent_config: AgentConfiguration) -> bool:
        """Check if reasoning is enabled for this specific agent.

        Args:
            agent_config: Agent configuration containing reasoning preference

        Returns:
            True if agent should use reasoning, defaults to True if not specified
        """
        return getattr(agent_config, 'reasoning_enabled', True)
    
    
    async def get_participant_statement_with_retry(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration,
        participant_names: List[str],
        max_rounds: int,
        max_retries: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        Get participant statement with retry/backoff functionality and two-step reasoning.
        
        Args:
            participant: The participant agent to get statement from
            context: The participant's context for the round
            discussion_state: Current discussion state with history
            agent_config: Agent configuration settings
            participant_names: List of participant names for group composition
            max_rounds: Maximum number of rounds in the experiment
            max_retries: Optional override for max retry attempts
            
        Returns:
            Tuple of (statement, internal_reasoning)
            
        Raises:
            Exception: If all retry attempts are exhausted
        """
        max_attempts = max_retries or self.settings.max_statement_retries
        timeout_seconds = self.settings.statement_timeout_seconds
        
        for attempt in range(max_attempts):
            try:
                # Log retry attempts
                if attempt > 0:
                    self._log_info(f"Statement retry {attempt + 1}/{max_attempts} for {participant.name}")
                    # Exponential backoff
                    backoff_time = self.settings.retry_backoff_factor ** (attempt - 1)
                    await asyncio.sleep(backoff_time)
                
                # Step 1: Get internal reasoning if enabled - SIMPLIFIED
                internal_reasoning = ""
                if self.should_use_reasoning(agent_config):
                    try:
                        reasoning_prompt = self.build_internal_reasoning_prompt(
                            discussion_state, context.round_number, max_rounds, context=context
                        )

                        reasoning_result = await self._invoke_discussion_interaction(
                            participant=participant,
                            context=context,
                            prompt=reasoning_prompt,
                            interaction_type="internal_reasoning",
                            timeout_seconds=self.settings.reasoning_timeout_seconds
                        )
                        internal_reasoning = reasoning_result.final_output or ""
                    except Exception:
                        internal_reasoning = ""  # Simple fallback as planned
                
                # Store reasoning in context for subsequent interactions
                if hasattr(context, 'internal_reasoning'):
                    context.internal_reasoning = internal_reasoning
                
                # Step 2: Build discussion prompt with reasoning
                discussion_prompt = self.build_discussion_prompt(
                    discussion_state=discussion_state,
                    round_num=context.round_number,
                    max_rounds=max_rounds,
                    participant_names=participant_names,
                    internal_reasoning=internal_reasoning
                )
                
                # Set interaction type for statement retrieval
                # Step 3: Execute with timeout to get public statement
                result = await self._invoke_discussion_interaction(
                    participant=participant,
                    context=context,
                    prompt=discussion_prompt,
                    interaction_type="statement",
                    timeout_seconds=timeout_seconds
                )
                
                statement = result.final_output
                
                # Validate statement
                agent_language = self._get_agent_language(agent_config)
                if not self.validate_statement(statement, participant.name, agent_language):
                    if attempt < max_attempts - 1:
                        self._log_warning(f"Invalid statement from {participant.name}, retrying...")
                        continue
                    else:
                        raise ValueError(f"Invalid statement after {max_attempts} attempts")
                
                self._log_info(f"Successfully retrieved statement from {participant.name}")
                return statement, internal_reasoning
                
            except asyncio.TimeoutError:
                self._log_warning(f"Statement timeout for {participant.name} (attempt {attempt + 1})")
                if attempt == max_attempts - 1:
                    raise
                    
            except Exception as e:
                self._log_warning(f"Statement error for {participant.name} (attempt {attempt + 1}): {str(e)}")
                if attempt == max_attempts - 1:
                    raise
        
        # Should not reach here due to raise in final attempt
        raise RuntimeError("Unexpected end of retry loop")

    async def get_participant_statement_with_intelligent_retry(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration,
        participant_names: List[str],
        max_rounds: int,
        max_retries: Optional[int] = None,
        participant_retry_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        utility_agent = None
    ) -> Tuple[str, str]:
        """
        Enhanced statement retrieval with intelligent feedback capability.

        Follows EXACT same pattern as UtilityAgent parse_*_enhanced_with_feedback methods.
        Only difference: validates statements instead of parsing responses.

        Args:
            participant: The participant agent to get statement from
            context: The participant's context for the round
            discussion_state: Current discussion state with history
            agent_config: Agent configuration settings
            participant_names: List of participant names for group composition
            max_rounds: Maximum number of rounds in the experiment
            max_retries: Optional override for max retry attempts
            participant_retry_callback: Optional callback for participant retry communication
            utility_agent: Utility agent for failure classification

        Returns:
            Tuple of (statement, internal_reasoning)

        Raises:
            Exception: If all retry attempts are exhausted
        """
        max_attempts = max_retries or self.settings.max_statement_retries
        timeout_seconds = self.settings.statement_timeout_seconds

        # Track validation attempts and errors for analysis (exact A1/A2 pattern)
        validation_attempts = []
        last_validation_error = None

        for attempt in range(max_attempts):
            try:
                # Log retry attempts (existing logic)
                if attempt > 0:
                    self._log_info(f"Statement retry {attempt + 1}/{max_attempts} for {participant.name}")
                    backoff_time = self.settings.retry_backoff_factor ** (attempt - 1)
                    await asyncio.sleep(backoff_time)

                # Get internal reasoning if enabled (existing logic)
                internal_reasoning = ""
                if self.should_use_reasoning(agent_config):
                    try:
                        reasoning_prompt = self.build_internal_reasoning_prompt(
                            discussion_state, context.round_number, max_rounds, context=context
                        )

                        reasoning_result = await self._invoke_discussion_interaction(
                            participant=participant,
                            context=context,
                            prompt=reasoning_prompt,
                            interaction_type="internal_reasoning",
                            timeout_seconds=self.settings.reasoning_timeout_seconds
                        )
                        internal_reasoning = reasoning_result.final_output or ""
                    except Exception:
                        internal_reasoning = ""  # Simple fallback

                # Store reasoning in context (existing logic)
                if hasattr(context, 'internal_reasoning'):
                    context.internal_reasoning = internal_reasoning

                # Build discussion prompt (existing logic)
                discussion_prompt = self.build_discussion_prompt(
                    discussion_state=discussion_state,
                    round_num=context.round_number,
                    max_rounds=max_rounds,
                    participant_names=participant_names,
                    internal_reasoning=internal_reasoning
                )

                # Execute with timeout (existing logic)
                result = await self._invoke_discussion_interaction(
                    participant=participant,
                    context=context,
                    prompt=discussion_prompt,
                    interaction_type="statement",
                    timeout_seconds=timeout_seconds
                )

                statement = result.final_output

                # Enhanced validation with failure classification (NEW - follows A1/A2 pattern)
                agent_language = self._get_agent_language(agent_config)
                min_length = self.get_min_statement_length(agent_language)

                if not self.validate_statement(statement, participant.name, agent_language):
                    # Classify the validation failure type using utility agent (robust vs pattern matching)
                    if utility_agent:
                        try:
                            failure_type = await utility_agent.classify_statement_validation_failure(
                                statement=statement,
                                min_length=min_length,
                                language=agent_language,
                                context=f"Discussion round {context.round_number}"
                            )
                        except Exception as e:
                            self._log_warning(f"Utility agent classification failed: {e}, using fallback")
                            # Fallback classification
                            if not statement or len(statement.strip()) < 3:
                                failure_type = StatementValidationFailureType.EMPTY_RESPONSE
                            elif len(statement.strip()) < min_length:
                                failure_type = StatementValidationFailureType.TOO_SHORT
                            else:
                                failure_type = StatementValidationFailureType.MINIMAL_CONTENT
                    else:
                        # Fallback classification when no utility agent provided
                        if not statement or len(statement.strip()) < 3:
                            failure_type = StatementValidationFailureType.EMPTY_RESPONSE
                        elif len(statement.strip()) < min_length:
                            failure_type = StatementValidationFailureType.TOO_SHORT
                        else:
                            failure_type = StatementValidationFailureType.MINIMAL_CONTENT

                    validation_attempts.append({
                        "attempt": attempt + 1,
                        "failure_type": failure_type,
                        "statement_length": len(statement) if statement else 0
                    })

                    # If not final attempt and we have retry callback
                    if attempt < max_attempts - 1 and participant_retry_callback:
                        try:
                            # Generate intelligent feedback (synchronous method)
                            feedback = self.generate_statement_validation_feedback(
                                original_statement=statement,
                                failure_type=failure_type,
                                attempt_number=attempt + 1,
                                min_required_length=min_length,
                                language=agent_language
                            )

                            # Use callback to request retry from participant
                            new_response = await participant_retry_callback(feedback)

                            if new_response and new_response.strip():
                                self._log_info(f"Received retry response for statement validation attempt {attempt + 2}: {len(new_response)} chars")
                                # Continue to next attempt (the new_response will be used via the callback mechanism)
                                continue
                            else:
                                self._log_warning(f"Empty retry response received for statement validation attempt {attempt + 2}")

                        except Exception as callback_error:
                            self._log_warning(f"Retry callback failed on statement validation attempt {attempt + 1}: {callback_error}")
                            # Continue with normal retry logic if callback fails

                    if attempt < max_attempts - 1:
                        continue
                    else:
                        # Final attempt failed - create comprehensive error
                        last_validation_error = f"Invalid statement after {max_attempts} attempts. " + \
                            f"Failure types: {[attempt['failure_type'].value for attempt in validation_attempts]}"
                        raise ValueError(last_validation_error)

                self._log_info(f"Successfully retrieved statement from {participant.name}")
                return statement, internal_reasoning

            except asyncio.TimeoutError:
                self._log_warning(f"Statement timeout for {participant.name} (attempt {attempt + 1})")
                if attempt == max_attempts - 1:
                    raise

            except Exception as e:
                self._log_warning(f"Statement error for {participant.name} (attempt {attempt + 1}): {str(e)}")
                if attempt == max_attempts - 1:
                    raise

        # Should not reach here due to raise in final attempt
        raise RuntimeError("Unexpected end of retry loop")

    def manage_discussion_history_length(self, discussion_state: GroupDiscussionState) -> None:
        """
        Keep discussion history under limit by trimming oldest content.
        Preserves recent conversation while preventing excessive memory usage.
        
        Args:
            discussion_state: Discussion state to manage
        """
        if len(discussion_state.public_history) > self.settings.public_history_max_length:
            # Keep the most recent 75% of content to provide buffer
            keep_length = int(self.settings.public_history_max_length * 0.75)

            # Add marker to indicate truncation and keep recent discussion
            recent_history = discussion_state.public_history[-keep_length:]
            # DEFENSIVE: Strip markdown when truncating to ensure clean history
            recent_history = self._strip_markdown_emphasis(recent_history)
            truncated_history = self._get_localized_message("system_messages.discussion.truncation_marker") + "\n" + recent_history
            discussion_state.public_history = truncated_history

            # Log the truncation for debugging
            self._log_info(f"Discussion history truncated: kept {keep_length} of {len(discussion_state.public_history)} characters")
    
    async def extract_favored_principle(self, statement: str, utility_agent) -> str:
        """Extract favored principle from participant statement using multilingual parsing."""
        try:
            # First, check for exact Chinese phrase matches to avoid LLM parsing issues
            chinese_mappings = {
                "在最低收入约束条件下最大化平均收入": "maximizing_average_floor_constraint",
                "在范围约束条件下最大化平均收入": "maximizing_average_range_constraint", 
                "最大化最低收入": "maximizing_floor",
                "最大化平均收入": "maximizing_average"
            }
            
            for chinese_term, principle in chinese_mappings.items():
                if chinese_term in statement:
                    self._log_info(f"Direct Chinese mapping found: {chinese_term} -> {principle}")
                    return principle
            
            # Use the utility agent for robust multilingual parsing
            parsed = await utility_agent.parse_principle_choice_enhanced(statement)
            # Return the canonical principle key (e.g., "maximizing_floor")
            return parsed.principle.value
        except Exception as e:
            # Log the error for debugging
            self._log_warning(f"Failed to extract principle from statement: {str(e)}")
            # Return a specific unspecified key instead of reusing constraint specification
            return self.language_manager.get("prompts.phase2_favored_principle_unspecified")
