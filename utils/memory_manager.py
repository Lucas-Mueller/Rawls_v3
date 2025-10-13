"""
Memory management utilities for agent-managed memory system with context-aware template selection.

This module provides sophisticated memory update capabilities that prevent activity duplication
by intelligently selecting prompt templates based on interaction types. The system includes:

- Context-aware template selection to prevent redundant "Recent Activity" sections
- Automatic memory compression when approaching character limits
- Fallback mechanisms for backward compatibility with existing translation files
- Support for both narrative and structured memory guidance styles
- Robust error handling and retry logic for memory updates

Key Features:
- Discussion interaction types (internal_reasoning, statement) use specialized "_no_recent_activity" templates
- Graceful degradation when specialized templates are missing
- Memory compression with configurable tolerance buffers
- Multi-language support through language_manager integration
"""
import logging
from typing import TYPE_CHECKING

from utils.error_handling import (
    MemoryError, ExperimentError, ErrorSeverity, 
    ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors
)

from models import ExperimentPhase
from models.experiment_types import ExperimentStage

if TYPE_CHECKING:
    from experiment_agents.participant_agent import ParticipantAgent
    from models.experiment_types import ParticipantContext

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages agent-generated memory with validation and retry logic."""
    
    @staticmethod
    @handle_experiment_errors(
        category=ExperimentErrorCategory.MEMORY_ERROR,
        severity=ErrorSeverity.RECOVERABLE,
        operation_name="memory_update"
    )
    async def prompt_agent_for_memory_update(
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        round_content: str,
        max_retries: int = 5,
        memory_guidance_style: str = "narrative",
        language_manager=None,
        error_handler=None,
        utility_agent=None,
        interaction_type: str = None,
        round_number: int = None,
        phase: str = None,
        include_experiment_explanation: bool = True,
        transcript_logger=None
    ) -> str:
        """
        Prompt agent to update their memory based on round content with context-aware template selection.
        
        This method implements a sophisticated memory update system that prevents activity duplication
        by selecting appropriate prompt templates based on the interaction type. For discussion-related
        interactions (internal_reasoning, statement), it uses specialized "_no_recent_activity" templates
        that avoid redundant "Recent Activity" sections when the content already contains the activity.
        
        Args:
            agent: The participant agent to prompt for memory update
            context: Current participant context containing existing memory and limits
            round_content: Content from the current round (prompt + response + outcome)
            max_retries: Maximum number of retry attempts for memory update (default: 5)
            memory_guidance_style: Style of memory guidance ("narrative" for story-like updates, 
                                 "structured" for organized format)
            language_manager: Language manager for localized prompts and template selection
            error_handler: Error handler for exception management (defaults to global handler)
            utility_agent: Utility agent for memory compression when size limits are exceeded
            interaction_type: Type of interaction for context-aware template selection. Discussion 
                            types ("internal_reasoning", "statement") trigger specialized templates 
                            to prevent activity duplication. None uses standard templates.
            
        Returns:
            Updated memory string that incorporates new content while respecting character limits
            
        Raises:
            MemoryError: If agent fails to create valid memory after max_retries attempts
            
        Note:
            The method includes automatic memory compression when approaching limits (80% of max),
            tolerance handling (15% over limit allowed), and fallback compression strategies.
            Template selection prevents duplication when round_content already contains the activity
            being described.
        """
        # Use provided error handler or fall back to global one
        if error_handler is None:
            error_handler = get_global_error_handler()

        # Resolve effective phase and round metadata for prompt selection and agent context
        effective_round = round_number if round_number is not None else getattr(context, 'round_number', None)
        phase_candidate = phase if phase is not None else getattr(context, 'phase', None)

        if isinstance(phase_candidate, ExperimentPhase):
            effective_phase_enum = phase_candidate
        elif isinstance(phase_candidate, str):
            try:
                effective_phase_enum = ExperimentPhase(phase_candidate)
            except ValueError:
                effective_phase_enum = ExperimentPhase.PHASE_1
        else:
            effective_phase_enum = ExperimentPhase.PHASE_1

        effective_phase_value = effective_phase_enum.value
        agent_round_number = effective_round if effective_round is not None else getattr(context, 'round_number', 0) or 0
        prompt_round_number = effective_round if effective_round is not None else agent_round_number

        for attempt in range(max_retries):
            try:
                # Check if memory needs compression before update
                memory_to_use = context.memory
                if len(context.memory) > 0.8 * context.memory_character_limit:
                    logger.info(f"Memory approaching limit for {agent.name}, attempting compression...")
                    memory_to_use = await MemoryManager._compress_memory_if_needed(
                        agent,
                        context.memory,
                        context.bank_balance,
                        context.memory_character_limit,
                        language_manager,
                        transcript_logger=transcript_logger
                    )

                # Create memory update prompt
                prompt = MemoryManager._create_memory_update_prompt(
                    memory_to_use,
                    round_content,
                    memory_guidance_style,
                    language_manager,
                    interaction_type,
                    prompt_round_number,
                    effective_phase_value,
                    context,
                    include_experiment_explanation
                )
                
                # Get updated memory from agent with accurate phase/round metadata
                updated_memory = await agent.update_memory(
                    prompt,
                    context.bank_balance,
                    phase=effective_phase_enum,
                    round_number=agent_round_number,
                    stage=context.stage,
                    transcript_logger=transcript_logger
                )

                # Defensively remove any trailing "--- Memory End ---" marker from agent output
                # The marker will be added by MemoryService after this method returns
                if updated_memory and language_manager:
                    try:
                        marker = language_manager.get("memory.memory_end_marker")
                        updated_memory = updated_memory.rstrip()
                        if updated_memory.endswith(marker):
                            updated_memory = updated_memory[:-len(marker)].rstrip()
                    except Exception as e:
                        logger.warning(f"Could not retrieve memory end marker for defensive removal: {e}")

                # Check memory length with 15% tolerance buffer
                char_limit = agent.config.memory_character_limit
                tolerance_limit = int(char_limit * 1.15)  # 15% tolerance
                memory_length = len(updated_memory)
                
                if memory_length <= char_limit:
                    # Memory is within normal limits
                    if attempt > 0:
                        logger.info(f"Memory update succeeded for {agent.name} after {attempt + 1} attempts")
                    # Mark that experiment explanation has been shown
                    if context is not None:
                        context.first_memory_update = False
                    return updated_memory
                elif memory_length <= tolerance_limit:
                    # Memory exceeds base limit but within tolerance - allow it
                    logger.info(f"Memory for {agent.name} exceeds base limit ({memory_length} > {char_limit}) but within tolerance ({tolerance_limit})")
                    # Mark that experiment explanation has been shown
                    if context is not None:
                        context.first_memory_update = False
                    return updated_memory
                else:
                    # Memory exceeds 15% tolerance - compress using utility agent
                    logger.info(f"Memory for {agent.name} exceeds tolerance ({memory_length} > {tolerance_limit}) - compressing using utility agent")
                    
                    # Use provided utility agent or fallback to basic truncation
                    if utility_agent is None:
                        logger.warning(f"No utility agent provided for memory compression of {agent.name} - using basic truncation")
                        # Fallback to basic truncation
                        target_length = int(char_limit * 0.5)
                        compressed_memory = updated_memory[:target_length] + "\n[Memory compressed due to length limit]"
                        return compressed_memory
                    
                    # Use utility agent to compress memory to 50% of limit
                    target_length = int(char_limit * 0.5)
                    compressed_memory = await MemoryManager._compress_memory_with_utility_agent(
                        utility_agent, updated_memory, target_length, language_manager, agent.name
                    )
                    
                    logger.info(f"Memory compressed for {agent.name}: {memory_length} -> {len(compressed_memory)} characters")
                    # Mark that experiment explanation has been shown
                    if context is not None:
                        context.first_memory_update = False
                    return compressed_memory
                    
            except MemoryError:
                raise  # Re-raise memory errors as-is
            except Exception as e:
                # Wrap other exceptions as memory errors
                memory_error = MemoryError(
                    f"Agent {agent.name} memory update failed: {str(e)}",
                    ErrorSeverity.RECOVERABLE if attempt < max_retries - 1 else ErrorSeverity.FATAL,
                    {
                        "agent_name": agent.name,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "original_error": str(e)
                    },
                    cause=e
                )
                memory_error.operation = "agent_memory_update"
                
                if attempt == max_retries - 1:
                    # Final attempt - make it fatal
                    memory_error.severity = ErrorSeverity.FATAL
                    raise memory_error
                else:
                    # Log the error and continue
                    error_handler._log_error(memory_error)
                    round_content = f"ERROR: An error occurred while updating memory: {str(e)}\n\nPlease try updating your memory again."
        
        # This should never be reached due to the exception handling above
        raise MemoryError(
            f"Agent {agent.name} failed to create valid memory after {max_retries} attempts",
            ErrorSeverity.FATAL,
            {
                "agent_name": agent.name,
                "max_retries": max_retries,
                "operation": "memory_update_exhausted"
            }
        )
    
    @staticmethod
    def _validate_memory_length(memory: str, limit: int) -> tuple[bool, int]:
        """
        Validate memory doesn't exceed character limit.
        
        Args:
            memory: Memory string to validate
            limit: Maximum allowed character count
            
        Returns:
            Tuple of (is_valid, actual_length)
        """
        length = len(memory)
        return length <= limit, length
    
    @staticmethod
    def _create_memory_update_prompt(current_memory: str, round_content: str, guidance_style: str = "narrative", language_manager=None, interaction_type: str = None, round_number: int = None, phase: str = None, context: "ParticipantContext" = None, include_experiment_explanation: bool = True) -> str:
        """
        Create context-aware memory update prompt that prevents activity duplication.
        
        This method implements intelligent template selection to prevent redundant "Recent Activity"
        sections in memory updates. When the interaction_type indicates a discussion-related event
        (internal_reasoning, statement), it attempts to use specialized "_no_recent_activity" templates
        that focus on incorporating insights rather than repeating activity descriptions.
        
        Additionally, for the first round of Phase 2, it uses specialized templates that include
        the extended Phase 2 explanation about higher stakes and payoff structure.
        
        Template Selection Logic:
        1. For first round of Phase 2:
           - Uses "_first_round" template variants with extended Phase 2 explanation
        2. For discussion interactions (internal_reasoning, statement):
           - Attempts to use "{base_template}_no_recent_activity" variant
           - Falls back to standard template if specialized version doesn't exist
        3. For other interactions (voting, results, etc.):
           - Uses standard templates with "Recent Activity" sections
        
        Args:
            current_memory: Agent's current memory content to be updated
            round_content: Content from the current round (prompt + response + outcome)
            guidance_style: Style of memory guidance ("narrative" for story-like format, 
                          "structured" for organized bullet points)
            language_manager: Language manager instance for localized template retrieval
            interaction_type: Type of interaction for template selection. Discussion types
                            ("internal_reasoning", "statement") trigger specialized templates.
                            None or other types use standard templates.
            round_number: Current round number (1-based), used to detect first round
            phase: Current phase ("phase1", "phase2"), used with round_number for template selection
            
        Returns:
            Formatted prompt string ready for agent processing
            
        Note:
            The fallback mechanism ensures backward compatibility - if specialized templates
            are missing, the method gracefully degrades to standard templates without errors.
        """
        
        # Discussion interaction types that should avoid "Recent Activity" duplication
        # These types contain the activity description within round_content, making
        # additional "Recent Activity" sections redundant and potentially confusing
        discussion_interaction_types = {"internal_reasoning", "statement"}
        
        # Check if this is the first round of Phase 2 and use specialized templates
        is_first_round_phase2 = (round_number == 1 and phase == "phase_2")
        
        # Choose base prompt template based on memory guidance style preference and round conditions
        if is_first_round_phase2:
            # First round of Phase 2 uses templates with extended Phase 2 explanation
            if guidance_style == "narrative":
                base_prompt_key = "prompts.memory_narrative_update_prompt_first_round"
            else:  # structured
                base_prompt_key = "prompts.memory_memory_update_prompt_first_round"
        else:
            # Regular templates for all other cases
            if guidance_style == "narrative":
                base_prompt_key = "prompts.memory_narrative_update_prompt"
            else:  # structured
                base_prompt_key = "prompts.memory_memory_update_prompt"
        
        # Apply context-aware template selection for discussion interactions
        # This prevents activity duplication by using specialized templates
        if interaction_type in discussion_interaction_types:
            # Attempt to use specialized "_no_recent_activity" template variant
            # These templates focus on insight incorporation rather than activity repetition
            no_recent_activity_key = base_prompt_key + "_no_recent_activity"
            
            # Check if the specialized template exists via test formatting
            # This graceful detection prevents hard errors when templates are missing
            try:
                # Test template existence by attempting minimal formatting
                test_prompt = language_manager.get(no_recent_activity_key, current_memory="test", round_content="test")
                # If successful, use the specialized no recent activity template
                prompt_key = no_recent_activity_key
            except (KeyError, AttributeError):
                # Graceful fallback to standard template if specialized version doesn't exist
                # Ensures backward compatibility with existing translation files
                prompt_key = base_prompt_key
        else:
            # Use standard template for non-discussion interactions (voting, results, etc.)
            # These interactions benefit from explicit "Recent Activity" sections
            prompt_key = base_prompt_key
        
        # Conditionally include experiment explanation based on phase, context, and config
        experiment_explanation = ""
        if include_experiment_explanation and context is not None:
            if phase == "phase_1":
                # Phase 1 logic unchanged
                if context.first_memory_update:
                    # First Phase 1 memory update gets the full initial experiment explanation
                    experiment_explanation = language_manager.get("prompts.initial_experiment_explanation")
                else:
                    # Subsequent Phase 1 memory updates receive the shorter reminder
                    experiment_explanation = language_manager.get("prompts.experiment_explanation")
            elif phase == "phase_2" and not context.first_memory_update:
                # Phase 2: Include explanation for discussion stages, exclude final ranking
                if (context.stage == ExperimentStage.DISCUSSION and
                    interaction_type in {"internal_reasoning", "statement"}):
                    experiment_explanation = language_manager.get("prompts.experiment_explanation")
            elif context.first_memory_update:
                # Preserve existing behavior for first memory update in other phases
                experiment_explanation = language_manager.get("prompts.experiment_explanation")

        return language_manager.get(
            prompt_key,
            current_memory=current_memory if current_memory.strip() else language_manager.get("prompts.memory_empty_memory_placeholder"),
            round_content=round_content,
            experiment_explanation=experiment_explanation
        )
    
    @staticmethod
    async def _compress_memory_if_needed(
        agent: "ParticipantAgent", 
        current_memory: str, 
        bank_balance: float,
        memory_limit: int,
        language_manager=None,
        transcript_logger=None
    ) -> str:
        """
        Compress memory when approaching the character limit.
        
        Args:
            agent: The participant agent
            current_memory: Current memory content
            bank_balance: Current bank balance for context
            memory_limit: Maximum memory character limit
            language_manager: Language manager instance
            
        Returns:
            Compressed memory string
        """
        
        # Create compression prompt
        compression_prompt = language_manager.get(
            "prompts.memory_compression_prompt",
            current_memory=current_memory,
            memory_limit=memory_limit,
            target_length=int(0.6 * memory_limit)  # Target 60% of limit after compression
        )
        
        try:
            compressed_memory = await agent.update_memory(
                compression_prompt,
                bank_balance,
                transcript_logger=transcript_logger
            )
            
            # Validate that compression was successful
            if len(compressed_memory) < len(current_memory):
                logger.info(f"Memory compressed from {len(current_memory)} to {len(compressed_memory)} characters")
                return compressed_memory
            else:
                logger.warning(f"Memory compression did not reduce size, using original memory")
                return current_memory
                
        except Exception as e:
            logger.error(f"Memory compression failed: {e}, using original memory")
            return current_memory

    @staticmethod
    def _apply_truncation_with_suffix(content: str, target_length: int, suffix: str) -> str:
        """Truncate content to target length while preserving a suffix message."""
        if target_length <= 0:
            return ""

        suffix = suffix or ""
        suffix_length = len(suffix)

        if target_length <= suffix_length:
            # Not enough room for content; return the prefix of the suffix
            return suffix[:target_length]

        allowed = target_length - suffix_length
        truncated_content = content[:allowed]
        result = truncated_content + suffix

        # Safety net to ensure we never exceed the target length
        if len(result) > target_length:
            result = result[:target_length]

        return result

    @staticmethod
    async def _compress_memory_with_utility_agent(
        utility_agent,
        memory_content: str,
        target_length: int,
        language_manager,
        agent_name: str = "Agent"
    ) -> str:
        """
        Compress memory using utility agent to target length.
        
        Args:
            utility_agent: The utility agent to use for compression
            memory_content: The memory content to compress
            target_length: Target length for compressed memory
            language_manager: Language manager for localized prompts
            agent_name: Name of agent for logging
            
        Returns:
            Compressed memory string
        """
        
        try:
            # Create compression prompt in the appropriate language using existing localized prompt
            compression_prompt = language_manager.get(
                "prompts.memory_compression_prompt",
                current_memory=memory_content,
                memory_limit=target_length * 2,  # Set a reasonable "limit" for the prompt
                target_length=target_length
            )
            
            # Import the run_without_tracing function for utility agent processing
            from experiment_agents.utility_agent import run_without_tracing
            
            # Use utility agent to compress the memory
            result = await run_without_tracing(utility_agent.parser_agent, compression_prompt)
            compressed_memory = result.final_output.strip()
            
            # Validate compression was effective
            if len(compressed_memory) <= target_length:
                logger.info(f"Utility agent successfully compressed memory from {len(memory_content)} to {len(compressed_memory)} characters")
                return compressed_memory
            else:
                # Compression didn't achieve target - do basic truncation as fallback
                logger.warning(f"Utility agent compression insufficient ({len(compressed_memory)} > {target_length}), using truncation fallback")
                suffix = "\n[Memory compressed and truncated due to length limit]"
                truncated_memory = MemoryManager._apply_truncation_with_suffix(
                    compressed_memory,
                    target_length,
                    suffix
                )
                return truncated_memory
                
        except Exception as e:
            logger.error(f"Utility agent compression failed for {agent_name}: {e}")
            # Fallback to basic truncation
            suffix = "\n[Memory compressed due to length limit]"
            truncated_memory = MemoryManager._apply_truncation_with_suffix(
                memory_content,
                target_length,
                suffix
            )
            return truncated_memory
