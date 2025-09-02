"""
Selective memory management system for optimizing LLM calls through intelligent event classification.
"""
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any
from enum import Enum

from utils.memory_manager import MemoryManager

if TYPE_CHECKING:
    from experiment_agents.participant_agent import ParticipantAgent
    from models.experiment_types import ParticipantContext

logger = logging.getLogger(__name__)


class MemoryEventType(Enum):
    """Classification of memory update events."""
    # Simple events - use direct insertion (no LLM calls)
    VOTE_INITIATION_RESPONSE = "vote_initiation_response"
    VOTING_CONFIRMATION = "voting_confirmation"  
    BALLOT_SELECTION = "ballot_selection"
    AMOUNT_SPECIFICATION = "amount_specification"
    SIMPLE_STATUS_UPDATE = "simple_status_update"
    
    # Complex events - use full LLM updates
    DISCUSSION_STATEMENT = "discussion_statement"
    PHASE_TRANSITION = "phase_transition"
    FINAL_RESULTS = "final_results"
    PRINCIPLE_APPLICATION = "principle_application"
    UNKNOWN = "unknown"


class SelectiveMemoryManager:
    """
    Manages selective memory updates by routing simple events to direct insertion
    and complex events to full LLM updates.
    """
    
    # Event classification sets
    SIMPLE_MEMORY_EVENTS = {
        MemoryEventType.VOTE_INITIATION_RESPONSE,
        MemoryEventType.VOTING_CONFIRMATION, 
        MemoryEventType.BALLOT_SELECTION,
        MemoryEventType.AMOUNT_SPECIFICATION,
        MemoryEventType.SIMPLE_STATUS_UPDATE
    }
    
    COMPLEX_MEMORY_EVENTS = {
        MemoryEventType.DISCUSSION_STATEMENT,
        MemoryEventType.PHASE_TRANSITION,
        MemoryEventType.FINAL_RESULTS,
        MemoryEventType.PRINCIPLE_APPLICATION
    }
    
    @staticmethod
    async def update_memory_selective(
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        content: str,
        event_type: Optional[MemoryEventType] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        config=None,
        language_manager=None,
        error_handler=None,
        utility_agent=None,
        **kwargs
    ) -> str:
        """
        Selectively update agent memory based on event classification.
        
        Args:
            agent: The participant agent
            context: Current participant context
            content: Content for memory update
            event_type: Classified event type (if known)
            event_metadata: Additional event-specific data
            config: Experiment configuration
            language_manager: Language manager instance
            error_handler: Error handler instance
            utility_agent: Utility agent for complex operations
            **kwargs: Additional arguments passed to memory managers
            
        Returns:
            Updated memory string
        """
        # Check if selective updates are enabled
        if config and hasattr(config, 'selective_memory_updates') and not config.selective_memory_updates:
            # Fall back to full LLM update
            return await SelectiveMemoryManager._full_memory_update(
                agent, context, content, config, language_manager, error_handler, utility_agent, **kwargs
            )
        
        # Classify event type if not provided
        if event_type is None:
            event_type = SelectiveMemoryManager._classify_event(content, context, event_metadata)
        
        # Route to appropriate memory update method
        if event_type in SelectiveMemoryManager.SIMPLE_MEMORY_EVENTS:
            try:
                return await SelectiveMemoryManager._simple_memory_update(
                    context, event_type, content, event_metadata, language_manager
                )
            except Exception as e:
                logger.warning(f"Simple memory update failed for {agent.name}: {e}, falling back to full update")
                # Fallback to full LLM update
                return await SelectiveMemoryManager._full_memory_update(
                    agent, context, content, config, language_manager, error_handler, utility_agent, **kwargs
                )
        else:
            # Use full LLM update for complex events
            return await SelectiveMemoryManager._full_memory_update(
                agent, context, content, config, language_manager, error_handler, utility_agent, **kwargs
            )
    
    @staticmethod
    def _classify_event(content: str, context: "ParticipantContext", metadata: Optional[Dict[str, Any]] = None) -> MemoryEventType:
        """
        Classify the type of memory event based on content and context.
        
        Args:
            content: Memory update content
            context: Participant context
            metadata: Additional event metadata
            
        Returns:
            Classified event type
        """
        content_lower = content.lower()
        
        # Check metadata first for explicit classification
        if metadata:
            if "event_type" in metadata:
                return metadata["event_type"]
            
            # Voting-related metadata
            if metadata.get("is_vote_initiation"):
                return MemoryEventType.VOTE_INITIATION_RESPONSE
            if metadata.get("is_voting_confirmation"):
                return MemoryEventType.VOTING_CONFIRMATION
            if metadata.get("is_ballot_selection"):
                return MemoryEventType.BALLOT_SELECTION
            if metadata.get("is_amount_specification"):
                return MemoryEventType.AMOUNT_SPECIFICATION
        
        # Pattern-based classification
        
        # Vote initiation patterns
        if any(pattern in content_lower for pattern in [
            "chose to initiate voting", "chose to continue discussion",
            "wants to initiate voting", "wants to continue discussion"
        ]):
            return MemoryEventType.VOTE_INITIATION_RESPONSE
        
        # Voting confirmation patterns  
        if any(pattern in content_lower for pattern in [
            "agreed to participate", "declined to participate",
            "voting confirmation", "confirmation response"
        ]):
            return MemoryEventType.VOTING_CONFIRMATION
        
        # Ballot selection patterns
        if any(pattern in content_lower for pattern in [
            "secret ballot", "voted for", "selected principle",
            "ballot choice", "principle selection"
        ]):
            return MemoryEventType.BALLOT_SELECTION
        
        # Amount specification patterns
        if any(pattern in content_lower for pattern in [
            "constraint amount", "floor amount", "range amount",
            "specified amount", "constraint of $", "amount specification"
        ]):
            return MemoryEventType.AMOUNT_SPECIFICATION
        
        # Final results patterns
        if any(pattern in content_lower for pattern in [
            "final phase 2 results", "experiment results", "final earnings",
            "consensus reached", "experiment concluded"
        ]):
            return MemoryEventType.FINAL_RESULTS
        
        # Discussion statement patterns (most common complex event)
        if any(pattern in content_lower for pattern in [
            "round_number", "statement", "discussion", "internal reasoning",
            "your response", "speaking order"
        ]):
            return MemoryEventType.DISCUSSION_STATEMENT
        
        # Phase transition patterns
        if any(pattern in content_lower for pattern in [
            "phase transition", "moving to", "entering phase",
            "phase complete", "starting phase"
        ]):
            return MemoryEventType.PHASE_TRANSITION
        
        # Default to unknown (will use full LLM update)
        return MemoryEventType.UNKNOWN
    
    @staticmethod
    async def _simple_memory_update(
        context: "ParticipantContext",
        event_type: MemoryEventType,
        content: str,
        metadata: Optional[Dict[str, Any]],
        language_manager
    ) -> str:
        """
        Handle simple memory updates using direct insertion.
        
        Args:
            context: Participant context
            event_type: Classified event type
            content: Update content
            metadata: Event metadata
            language_manager: Language manager instance
            
        Returns:
            Updated memory string
        """
        original_memory = context.memory
        
        try:
            if event_type == MemoryEventType.VOTE_INITIATION_RESPONSE:
                # Content already formatted by MemoryService - just append to memory
                if context.memory and not context.memory.endswith('\n'):
                    context.memory += '\n'
                context.memory += content.strip()
            
            elif event_type == MemoryEventType.VOTING_CONFIRMATION:
                # Content already formatted by MemoryService - just append to memory
                if context.memory and not context.memory.endswith('\n'):
                    context.memory += '\n'
                context.memory += content.strip()
            
            elif event_type == MemoryEventType.BALLOT_SELECTION:
                # Content already formatted by MemoryService - just append to memory
                if context.memory and not context.memory.endswith('\n'):
                    context.memory += '\n'
                context.memory += content.strip()
            
            elif event_type == MemoryEventType.AMOUNT_SPECIFICATION:
                # Content already formatted by MemoryService - just append to memory
                if context.memory and not context.memory.endswith('\n'):
                    context.memory += '\n'
                context.memory += content.strip()
            
            elif event_type == MemoryEventType.SIMPLE_STATUS_UPDATE:
                # Simple status update - just append to memory
                if context.memory and not context.memory.endswith('\n'):
                    context.memory += '\n'
                context.memory += content.strip()
            
            else:
                raise ValueError(f"Unsupported simple event type: {event_type}")
            
            logger.debug(f"Simple memory update successful: {event_type}")
            return context.memory
            
        except Exception as e:
            # Restore original memory and re-raise
            context.memory = original_memory
            raise e
    
    @staticmethod
    async def _full_memory_update(
        agent: "ParticipantAgent",
        context: "ParticipantContext", 
        content: str,
        config=None,
        language_manager=None,
        error_handler=None,
        utility_agent=None,
        **kwargs
    ) -> str:
        """
        Handle complex memory updates using full LLM processing.
        
        Args:
            agent: The participant agent
            context: Current participant context
            content: Content for memory update
            config: Experiment configuration
            language_manager: Language manager instance
            error_handler: Error handler instance
            utility_agent: Utility agent for complex operations
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Clean kwargs to avoid parameter conflicts
        kwargs_clean = kwargs.copy()
        kwargs_clean.pop('memory_guidance_style', None)  # Remove if present to avoid conflict
        
        # Extract memory guidance style - config takes precedence
        memory_guidance_style = "narrative"
        if config and hasattr(config, 'memory_guidance_style'):
            memory_guidance_style = config.memory_guidance_style
        
        # Use existing MemoryManager for full LLM updates
        return await MemoryManager.prompt_agent_for_memory_update(
            agent=agent,
            context=context,
            round_content=content,
            memory_guidance_style=memory_guidance_style,
            language_manager=language_manager,
            error_handler=error_handler,
            utility_agent=utility_agent,
            **kwargs_clean  # Pass cleaned kwargs without conflicts
        )
    
    # Helper methods for extracting information from content/metadata
    
    @staticmethod
    def _extract_vote_decision(content: str, metadata: Optional[Dict[str, Any]]) -> bool:
        """Extract vote initiation decision from content or metadata."""
        if metadata and 'wants_vote' in metadata:
            return metadata['wants_vote']
        
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in ['initiate voting', 'start voting', 'wants to vote']):
            return True
        if any(phrase in content_lower for phrase in ['continue discussion', 'keep discussing', 'not ready to vote']):
            return False
        
        # Default to continue discussion if unclear
        return False
    
    @staticmethod
    def _extract_confirmation_decision(content: str, metadata: Optional[Dict[str, Any]]) -> bool:
        """Extract voting confirmation decision from content or metadata."""
        if metadata and 'agrees_to_vote' in metadata:
            return metadata['agrees_to_vote']
        
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in ['agreed to', 'agrees to', 'yes to voting']):
            return True
        if any(phrase in content_lower for phrase in ['declined to', 'disagrees with', 'no to voting']):
            return False
        
        # Default to agreed if unclear
        return True
    
