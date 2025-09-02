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
        language_manager=None,
        error_handler=None,
        utility_agent=None
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
        # Use provided error handler or fall back to global one
        if error_handler is None:
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
                
                # Check memory length with 15% tolerance buffer
                char_limit = agent.config.memory_character_limit
                tolerance_limit = int(char_limit * 1.15)  # 15% tolerance
                memory_length = len(updated_memory)
                
                if memory_length <= char_limit:
                    # Memory is within normal limits
                    if attempt > 0:
                        logger.info(f"Memory update succeeded for {agent.name} after {attempt + 1} attempts")
                    return updated_memory
                elif memory_length <= tolerance_limit:
                    # Memory exceeds base limit but within tolerance - allow it
                    logger.info(f"Memory for {agent.name} exceeds base limit ({memory_length} > {char_limit}) but within tolerance ({tolerance_limit})")
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
                truncated_memory = compressed_memory[:target_length - 50] + "\n[Memory compressed and truncated due to length limit]"
                return truncated_memory
                
        except Exception as e:
            logger.error(f"Utility agent compression failed for {agent_name}: {e}")
            # Fallback to basic truncation
            truncated_memory = memory_content[:target_length - 50] + "\n[Memory compressed due to length limit]"
            return truncated_memory
