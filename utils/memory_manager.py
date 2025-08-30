"""
Memory management utilities for agent-managed memory system.
"""
import logging
from typing import TYPE_CHECKING

from utils.error_handling import (
    MemoryError, ExperimentError, ErrorSeverity, 
    ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors
)

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
        language_manager=None
    ) -> str:
        """
        Prompt agent to update their memory based on round content.
        
        Args:
            agent: The participant agent to prompt
            context: Current participant context
            round_content: Content from the current round (prompt + response + outcome)
            max_retries: Maximum number of retry attempts
            memory_guidance_style: Style of memory guidance ("narrative" or "structured")
            
        Returns:
            Updated memory string
            
        Raises:
            MemoryError: If agent fails to create valid memory after max_retries
        """
        error_handler = get_global_error_handler()
        
        for attempt in range(max_retries):
            try:
                # Check if memory needs compression before update
                memory_to_use = context.memory
                if len(context.memory) > 0.8 * context.memory_character_limit:
                    logger.info(f"Memory approaching limit for {agent.name}, attempting compression...")
                    memory_to_use = await MemoryManager._compress_memory_if_needed(
                        agent, context.memory, context.bank_balance, context.memory_character_limit, language_manager
                    )
                
                # Create memory update prompt
                prompt = MemoryManager._create_memory_update_prompt(
                    memory_to_use, round_content, memory_guidance_style, language_manager
                )
                
                # Get updated memory from agent
                updated_memory = await agent.update_memory(prompt, context.bank_balance)
                
                # Validate memory length
                is_valid, length = MemoryManager._validate_memory_length(
                    updated_memory, agent.config.memory_character_limit
                )
                
                if is_valid:
                    if attempt > 0:
                        logger.info(f"Memory update succeeded for {agent.name} after {attempt + 1} attempts")
                    return updated_memory
                else:
                    # Memory too long - create specific error for retry
                    memory_error = MemoryError(
                        f"Memory length {length} exceeds limit {agent.config.memory_character_limit}",
                        ErrorSeverity.RECOVERABLE,
                        {
                            "agent_name": agent.name,
                            "attempted_length": length,
                            "limit": agent.config.memory_character_limit,
                            "attempt": attempt + 1,
                            "max_retries": max_retries
                        }
                    )
                    memory_error.operation = "memory_length_validation"
                    
                    # Log the error
                    error_handler._log_error(memory_error)
                    
                    # Create error message for next attempt
                    error_msg = (
                        f"Your memory is {length} characters, which exceeds the limit of "
                        f"{agent.config.memory_character_limit} characters. Please shorten "
                        f"your memory by {length - agent.config.memory_character_limit} characters."
                    )
                    round_content = f"ERROR: {error_msg}\n\nPlease update your memory again, making it shorter."
                    
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
    def _create_memory_update_prompt(current_memory: str, round_content: str, guidance_style: str = "narrative", language_manager=None) -> str:
        """
        Create prompt for memory update based on guidance style.
        
        Args:
            current_memory: Agent's current memory
            round_content: Content from the current round
            guidance_style: Style of guidance ("narrative" or "structured")
            language_manager: Language manager instance
            
        Returns:
            Formatted prompt for memory update
        """
        
        # Choose prompt based on guidance style
        if guidance_style == "narrative":
            prompt_key = "prompts.memory_narrative_update_prompt"
        else:  # structured
            prompt_key = "prompts.memory_memory_update_prompt"  # Keep old structured style as fallback
        
        return language_manager.get(
            prompt_key,
            current_memory=current_memory if current_memory.strip() else language_manager.get("prompts.memory_empty_memory_placeholder"),
            round_content=round_content
        )
    
    @staticmethod
    async def _compress_memory_if_needed(
        agent: "ParticipantAgent", 
        current_memory: str, 
        bank_balance: float,
        memory_limit: int,
        language_manager=None
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
            compressed_memory = await agent.update_memory(compression_prompt, bank_balance)
            
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