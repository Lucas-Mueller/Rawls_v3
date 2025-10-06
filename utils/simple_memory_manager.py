"""
Simple memory insertion utilities for factual updates without agent calls.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.experiment_types import ParticipantContext

class SimpleMemoryManager:
    """Handles simple factual memory insertions without expensive agent calls."""
    
    @staticmethod
    def insert_vote_initiation_decision(
        context: "ParticipantContext",
        round_num: int,
        wants_vote: bool,
        language_manager
    ) -> None:
        """Insert vote initiation decision into memory."""
        
        decision_key = "initiate_voting" if wants_vote else "continue_discussion"
        decision_text = language_manager.get(f"prompts.memory_insertions.{decision_key}")
        
        memory_addition = language_manager.get(
            "prompts.memory_insertions.vote_initiation_decision",
            round_num=round_num,
            decision=decision_text
        )
        
        # Ensure memory is properly formatted
        if not context.memory:
            context.memory = ""
        if context.memory and not context.memory.endswith('\n'):
            context.memory += '\n'
        context.memory += memory_addition
    
    @staticmethod
    def insert_confirmation_response(
        context: "ParticipantContext",
        agrees_to_vote: bool,
        language_manager
    ) -> None:
        """Insert voting confirmation response into memory."""
        
        response_key = "agreed_to" if agrees_to_vote else "declined_to"
        response_text = language_manager.get(f"prompts.memory_insertions.{response_key}")
        
        memory_addition = language_manager.get(
            "prompts.memory_insertions.confirmation_response",
            response=response_text
        )
        
        # Ensure memory is properly formatted
        if not context.memory:
            context.memory = ""
        if context.memory and not context.memory.endswith('\n'):
            context.memory += '\n'
        context.memory += memory_addition
    
    @staticmethod
    def insert_secret_ballot_choice(
        context: "ParticipantContext",
        principle_name: str,
        language_manager
    ) -> None:
        """Insert secret ballot choice into memory."""
        
        memory_addition = language_manager.get(
            "prompts.memory_insertions.secret_ballot_choice",
            principle_name=principle_name
        )
        
        # Ensure memory is properly formatted
        if not context.memory:
            context.memory = ""
        if context.memory and not context.memory.endswith('\n'):
            context.memory += '\n'
        context.memory += memory_addition
    
    @staticmethod
    def insert_amount_specification(
        context: "ParticipantContext",
        amount: str,
        language_manager
    ) -> None:
        """Insert constraint amount specification into memory."""
        
        memory_addition = language_manager.get(
            "prompts.memory_insertions.amount_specification",
            amount=amount
        )
        
        # Ensure memory is properly formatted
        if not context.memory:
            context.memory = ""
        if context.memory and not context.memory.endswith('\n'):
            context.memory += '\n'
        context.memory += memory_addition
    
    @staticmethod
    def insert_simple_status_update(
        context: "ParticipantContext",
        status_message: str,
        language_manager
    ) -> None:
        """Insert simple status update into memory."""
        
        # For simple status updates, we can just append the message directly
        # or use a template if one exists
        try:
            memory_addition = language_manager.get(
                "prompts.memory_insertions.status_update",
                status_message=status_message
            )
        except:
            # Fallback to direct message insertion
            memory_addition = status_message.strip()
        
        # Ensure memory is properly formatted
        if not context.memory:
            context.memory = ""
        if context.memory and not context.memory.endswith('\n'):
            context.memory += '\n'
        context.memory += memory_addition
    
    @staticmethod
    def ensure_memory_initialized(context: "ParticipantContext") -> None:
        """
        Ensure participant memory is initialized and ready for insertions.
        
        Args:
            context: Participant's context to check/initialize
        """
        if context.memory is None:
            context.memory = ""
    
    @staticmethod
    def validate_memory_coherence(context: "ParticipantContext") -> bool:
        """
        Validate that memory maintains coherence after simple insertions.
        
        Args:
            context: Participant's context to validate
            
        Returns:
            True if memory appears coherent, False otherwise
        """
        if not context.memory:
            return True
            
        # Basic coherence checks
        memory_lines = context.memory.strip().split('\n')
        
        # Check for excessive repetition (potential insertion errors)
        if len(memory_lines) > 100:  # Reasonable upper bound
            return False
            
        # Check for malformed entries
        for line in memory_lines[-10:]:  # Check recent entries
            if line.strip() and len(line) < 5:  # Too short to be meaningful
                return False
                
        return True