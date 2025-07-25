"""
Memory management utilities for agent-managed memory system.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from experiment_agents.participant_agent import ParticipantAgent
    from models.experiment_types import ParticipantContext


class MemoryLengthExceededError(Exception):
    """Raised when agent memory exceeds the character limit."""
    
    def __init__(self, attempted_length: int, limit: int):
        self.attempted_length = attempted_length
        self.limit = limit
        super().__init__(
            f"Memory length {attempted_length} exceeds limit {limit} characters. "
            f"Please reduce your memory by {attempted_length - limit} characters."
        )


class ExperimentAbortError(Exception):
    """Raised when experiment must be aborted due to repeated memory failures."""
    pass


class MemoryManager:
    """Manages agent-generated memory with validation and retry logic."""
    
    @staticmethod
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
            ExperimentAbortError: If agent fails to create valid memory after max_retries
        """
        for attempt in range(max_retries):
            try:
                # Create memory update prompt
                prompt = MemoryManager._create_memory_update_prompt(
                    context.memory, round_content
                )
                
                # Get updated memory from agent
                updated_memory = await agent.update_memory(prompt)
                
                # Validate memory length
                is_valid, length = MemoryManager._validate_memory_length(
                    updated_memory, agent.config.memory_character_limit
                )
                
                if is_valid:
                    return updated_memory
                else:
                    # Memory too long - create error message for next attempt
                    error_msg = (
                        f"Your memory is {length} characters, which exceeds the limit of "
                        f"{agent.config.memory_character_limit} characters. Please shorten "
                        f"your memory by {length - agent.config.memory_character_limit} characters."
                    )
                    round_content = f"ERROR: {error_msg}\n\nPlease update your memory again, making it shorter."
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ExperimentAbortError(
                        f"Agent {agent.name} failed to create valid memory after "
                        f"{max_retries} attempts. Last error: {str(e)}"
                    )
                # For other exceptions, try again with error context
                round_content = f"ERROR: An error occurred while updating memory: {str(e)}\n\nPlease try updating your memory again."
        
        # This should never be reached due to the exception handling above
        raise ExperimentAbortError(
            f"Agent {agent.name} failed to create valid memory after {max_retries} attempts"
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
        return f"""Current Memory:
{current_memory if current_memory.strip() else "(Empty)"}

Recent Activity:
{round_content}

Review what just happened and update your memory with whatever you think will be important for future decisions in this experiment. Focus on information that might influence your choices about justice principles or help you in group discussions."""