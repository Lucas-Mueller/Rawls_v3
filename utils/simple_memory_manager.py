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
        decision_text = language_manager.get(f"memory_insertions.{decision_key}")
        
        memory_addition = language_manager.get(
            "memory_insertions.vote_initiation_decision",
            round_num=round_num,
            decision=decision_text
        )
        
        context.memory += f"\n{memory_addition}"
    
    @staticmethod
    def insert_confirmation_response(
        context: "ParticipantContext",
        agrees_to_vote: bool,
        language_manager
    ) -> None:
        """Insert voting confirmation response into memory."""
        
        response_key = "agreed_to" if agrees_to_vote else "declined_to"
        response_text = language_manager.get(f"memory_insertions.{response_key}")
        
        memory_addition = language_manager.get(
            "memory_insertions.confirmation_response",
            response=response_text
        )
        
        context.memory += f"\n{memory_addition}"
    
    @staticmethod
    def insert_secret_ballot_choice(
        context: "ParticipantContext",
        principle_name: str,
        language_manager
    ) -> None:
        """Insert secret ballot choice into memory."""
        
        memory_addition = language_manager.get(
            "memory_insertions.secret_ballot_choice",
            principle_name=principle_name
        )
        
        context.memory += f"\n{memory_addition}"