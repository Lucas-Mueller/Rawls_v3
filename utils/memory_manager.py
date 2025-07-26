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
        max_retries: int = 5
    ) -> str:
        """
        Prompt agent to update their memory based on round content.
        
        Args:
            agent: The participant agent to prompt
            context: Current participant context
            round_content: Content from the current round (prompt + response + outcome)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Updated memory string
            
        Raises:
            MemoryError: If agent fails to create valid memory after max_retries
        """
        error_handler = get_global_error_handler()
        
        for attempt in range(max_retries):
            try:
                # Create memory update prompt
                prompt = MemoryManager._create_memory_update_prompt(
                    context.memory, round_content
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
    def _create_memory_update_prompt(current_memory: str, round_content: str) -> str:
        """
        Create generic prompt for memory update.
        
        Args:
            current_memory: Agent's current memory
            round_content: Content from the current round
            
        Returns:
            Formatted prompt for memory update
        """
        return f"""Review what just happened and update your memory with whatever you think will be important for future decisions in this experiment. Focus on information that might influence your choices about justice principles or help you in group discussions.

Current Memory:
{current_memory if current_memory.strip() else "(Empty)"}

Recent Activity:
{round_content}"""