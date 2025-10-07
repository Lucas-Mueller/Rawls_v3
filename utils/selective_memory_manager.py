"""
Selective memory management system for optimizing LLM calls through intelligent event classification.

This module provides intelligent routing between simple memory insertions and complex LLM-based
memory updates. It integrates with the enhanced MemoryManager to support context-aware template
selection for preventing activity duplication in discussion-related interactions.

Key Components:
- Event classification system to route simple vs. complex memory updates
- Integration with MemoryManager's context-aware template selection
- Backward compatibility for interaction_type extraction from participant contexts
- Automatic fallback to full LLM updates when simple updates fail

The system optimizes memory update performance by:
- Using direct insertion for simple events (voting responses, confirmations)
- Leveraging full LLM processing for complex events (discussions, results)
- Enabling context-aware template selection to prevent activity duplication
- Maintaining compatibility with both new and legacy participant contexts
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
    PHASE1_RANKING = "phase1_ranking"
    PHASE1_EXPLANATION = "phase1_explanation"
    PHASE1_RETRY = "phase1_retry"
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
        MemoryEventType.PRINCIPLE_APPLICATION,
        MemoryEventType.PHASE1_RANKING,
        MemoryEventType.PHASE1_EXPLANATION,
        MemoryEventType.PHASE1_RETRY
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
        transcript_logger=None,
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
                    agent,
                    context,
                    content,
                    config,
                    language_manager,
                    error_handler,
                    utility_agent,
                    transcript_logger=transcript_logger,
                    **kwargs
                )
        else:
            # Use full LLM update for complex events
            return await SelectiveMemoryManager._full_memory_update(
                agent,
                context,
                content,
                config,
                language_manager,
                error_handler,
                utility_agent,
                transcript_logger=transcript_logger,
                **kwargs
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

            if metadata.get("phase") == "Phase 1":
                task = metadata.get("task")
                if task in {"initial_ranking", "post_explanation_ranking", "final_ranking"}:
                    return MemoryEventType.PHASE1_RANKING
                if task in {"detailed_explanation"}:
                    return MemoryEventType.PHASE1_EXPLANATION
                if task in {"retry_feedback", "constraint_retry"}:
                    return MemoryEventType.PHASE1_RETRY
        
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
            # Remove any existing trailing "--- Memory End ---" marker before appending new content
            # This prevents duplicate markers (MemoryService will add it back after this method returns)
            if context.memory and language_manager:
                try:
                    marker = language_manager.get("memory.memory_end_marker")
                    context.memory = context.memory.rstrip()
                    if context.memory.endswith(marker):
                        context.memory = context.memory[:-len(marker)].rstrip()
                except Exception as e:
                    logger.warning(f"Could not retrieve memory end marker for removal: {e}")

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
        transcript_logger=None,
        **kwargs
    ) -> str:
        """
        Handle complex memory updates using full LLM processing with context-aware template selection.
        
        This method serves as the bridge between SelectiveMemoryManager and the enhanced MemoryManager
        for complex events that require full agent-based memory updates. It extracts interaction_type 
        information from the participant context and passes it to MemoryManager for intelligent template 
        selection that prevents activity duplication in discussion-related interactions.
        
        Args:
            agent: The participant agent to perform memory update
            context: Current participant context (includes interaction_type for template selection)
            content: Content for memory update (round prompt + response + outcome)
            config: Experiment configuration containing memory_guidance_style and other settings
            language_manager: Language manager instance for localized prompts
            error_handler: Error handler instance for exception management
            utility_agent: Utility agent for complex operations like memory compression
            **kwargs: Additional arguments passed to MemoryManager (cleaned to avoid conflicts)
            
        Returns:
            Updated memory string incorporating new content with appropriate template selection
            
        Note:
            This method implements backward compatibility by gracefully extracting interaction_type
            from context when available, while falling back to None for older contexts. The extracted
            interaction_type enables context-aware template selection to prevent activity duplication
            in discussion-related memory updates.
        """
        # Clean kwargs to avoid parameter conflicts
        kwargs_clean = kwargs.copy()
        kwargs_clean.pop('memory_guidance_style', None)  # Remove if present to avoid conflict
        
        # Extract memory guidance style - config takes precedence
        memory_guidance_style = "narrative"
        if config and hasattr(config, 'memory_guidance_style'):
            memory_guidance_style = config.memory_guidance_style

        # Extract include_experiment_explanation flag from config
        include_experiment_explanation = True  # Default to True for backward compatibility
        if config and hasattr(config, 'include_experiment_explanation'):
            include_experiment_explanation = config.include_experiment_explanation

        # Extract interaction_type from context for template selection (with backward compatibility)
        # This enables context-aware memory prompts that prevent activity duplication
        # Falls back to None for older contexts without interaction_type attribute
        interaction_type = getattr(context, 'interaction_type', None)

        # Extract round and phase information for first-round template selection
        round_number = getattr(context, 'round_number', None)
        phase = getattr(context, 'phase', None) or "phase_2"  # Default to phase_2 if not specified

        # Use existing MemoryManager for full LLM updates
        return await MemoryManager.prompt_agent_for_memory_update(
            agent=agent,
            context=context,
            round_content=content,
            memory_guidance_style=memory_guidance_style,
            interaction_type=interaction_type,
            round_number=round_number,
            phase=phase,
            include_experiment_explanation=include_experiment_explanation,
            language_manager=language_manager,
            error_handler=error_handler,
            utility_agent=utility_agent,
            transcript_logger=transcript_logger,
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
    
