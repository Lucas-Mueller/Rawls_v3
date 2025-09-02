"""
Discussion Service for Phase 2 Discussion Management.

Handles discussion prompts, statement validation, and group composition formatting
with multilingual support and language-aware validation.
"""

import asyncio
from typing import List, Optional, Protocol, Tuple, Any
from agents import Runner
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState


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


class AgentConfiguration(Protocol):
    """Protocol for agent configuration."""
    language: str


class DiscussionService:
    """
    Manages discussion prompts, statement validation, and group composition formatting.
    
    Provides centralized discussion/reasoning prompt generation with multilingual support
    and language-aware statement validation.
    """
    
    def __init__(self, language_manager: LanguageProvider, settings: Optional[Phase2Settings] = None,
                 logger: Optional[Logger] = None):
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
    
    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message with fallback handling."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self._log_warning(f"Missing translation key: {key} - {str(e)}")
            # Return English fallback or key name
            return f"[MISSING: {key}]"
    
    def build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                               max_rounds: int, participant_names: List[str],
                               internal_reasoning: str = "") -> str:
        """
        Build localized discussion prompt with history and group composition.
        
        Args:
            discussion_state: Current discussion state with history
            round_num: Current round number (1-based)
            max_rounds: Maximum number of rounds
            participant_names: List of participant names for group composition
            internal_reasoning: Optional internal reasoning to include
            
        Returns:
            Formatted discussion prompt with group composition and reasoning
        """
        language_manager = self.language_manager
        
        # Generate group composition
        group_participants = self.format_group_composition(participant_names)
        
        # Always use complex mode prompts (formal voting system)
        base_prompt = language_manager.get("prompts.phase2_discussion_prompt",
                                          round_number=round_num,
                                          max_rounds=max_rounds,
                                          discussion_history=discussion_state.public_history or "No previous discussion.",
                                          group_participants=group_participants)
        
        # If internal reasoning is provided, include it in the prompt
        if internal_reasoning and internal_reasoning.strip():
            return f"{base_prompt}\n\n{self._get_localized_message('voting_prompts.internal_reasoning_section')}\n{internal_reasoning}\n================================\n\n{self._get_localized_message('voting_prompts.reasoning_prompt')}"
        else:
            return base_prompt
    
    def build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                                      max_rounds: int) -> str:
        """
        Build prompt for internal reasoning before public statement.
        
        Args:
            discussion_state: Current discussion state with history
            round_num: Current round number (1-based)
            max_rounds: Maximum number of rounds
            
        Returns:
            Formatted internal reasoning prompt
        """
        language_manager = self.language_manager
        
        return language_manager.get("prompts.phase2_internal_reasoning",
                                   round_number=round_num,
                                   max_rounds=max_rounds,
                                   discussion_history=discussion_state.public_history or "No previous discussion.")
    
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
        else:
            # Format as "A, B, and C" or "A and B"
            participant_list = ", ".join(participant_names[:-1]) + f" and {participant_names[-1]}"
        
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
        Get participant statement with retry/backoff functionality.
        
        Args:
            participant: The participant agent to get statement from
            context: The participant's context for the round
            discussion_state: Current discussion state with history
            agent_config: Agent configuration settings
            participant_names: List of participant names for group composition
            max_rounds: Maximum number of rounds in the experiment
            max_retries: Optional override for max retry attempts
            
        Returns:
            Tuple of (statement, round_content_for_memory)
            
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
                
                # Build discussion prompt
                discussion_prompt = self.build_discussion_prompt(
                    discussion_state=discussion_state,
                    round_num=context.round_number,
                    max_rounds=max_rounds,
                    participant_names=participant_names
                )
                
                # Set interaction type for statement retrieval
                context.interaction_type = "statement"
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    Runner.run(participant.agent, discussion_prompt, context=context),
                    timeout=timeout_seconds
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
                
                # Create memory content
                round_content = self._create_statement_memory_content(
                    discussion_prompt, statement, context.round_number
                )
                
                self._log_info(f"Successfully retrieved statement from {participant.name}")
                return statement, round_content
                
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
            truncated_history = self._get_localized_message("system_messages.discussion.truncation_marker") + "\n" + discussion_state.public_history[-keep_length:]
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