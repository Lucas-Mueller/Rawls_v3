"""
Memory Service for Phase2Manager Refactoring

Provides unified memory management with consistent guidance styles,
content truncation, and event-based routing between simple and complex updates.

Replaces SelectiveMemoryManager calls throughout Phase2Manager with a single,
focused service that handles discussion, voting, and results memory updates.
"""

import logging
from typing import Protocol, Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum

from utils.selective_memory_manager import SelectiveMemoryManager, MemoryEventType
from utils.memory_manager import MemoryManager
from config.phase2_settings import Phase2Settings

if TYPE_CHECKING:
    from experiment_agents.participant_agent import ParticipantAgent
    from models.experiment_types import ParticipantContext

logger = logging.getLogger(__name__)


class LanguageProvider(Protocol):
    """Protocol for language manager dependency."""
    def get(self, key: str, **kwargs) -> str:
        """Get localized text for the given key."""
        ...


class UtilityProvider(Protocol):
    """Protocol for utility agent dependency."""
    async def parse_principle_ranking_enhanced(self, text_response: str) -> Any:
        """Parse principle ranking from text response."""
        ...


class ErrorHandler(Protocol):
    """Protocol for error handler dependency."""
    def handle_error(self, error: Exception, context: str = "") -> None:
        """Handle an error with context."""
        ...


class Logger(Protocol):
    """Protocol for logger dependency."""
    def info(self, message: str) -> None:
        """Log info message."""
        ...
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        ...
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        ...


class MemoryService:
    """
    Unified memory management service for Phase2Manager.
    
    Handles all memory updates with consistent guidance styles, content truncation,
    and intelligent routing between simple direct insertion and complex LLM updates.
    
    Key responsibilities:
    - Discussion statement memory updates with truncation
    - Voting phase memory updates (initiation, confirmation, ballot)
    - Final results memory updates with counterfactual information
    - Content truncation rules (statements ≤300 chars, reasoning ≤200 chars)
    - Consistent memory guidance style application
    - Event classification and routing optimization
    """
    
    def __init__(
        self,
        language_manager: LanguageProvider,
        utility_agent: UtilityProvider,
        settings: Phase2Settings,
        logger: Optional[Logger] = None,
        config=None,
        transcript_logger=None
    ):
        """
        Initialize MemoryService with dependencies.
        
        Args:
            language_manager: Provider for localized text
            utility_agent: Provider for complex parsing operations
            settings: Phase 2 configuration settings
            logger: Optional logger for service operations
            config: Optional experiment configuration for memory_guidance_style
        """
        self.language_manager = language_manager
        self.utility_agent = utility_agent
        self.settings = settings
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.transcript_logger = transcript_logger
        
        # Content truncation limits
        self.statement_max_chars = 300
        self.reasoning_max_chars = 200
        
        # Memory guidance style from config (single source of truth → ExperimentConfiguration)
        # Default to 'structured' when no config is provided
        self.memory_guidance_style = getattr(config, 'memory_guidance_style', 'structured') if config else 'structured'

    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Safely get localized text, falling back to a visible placeholder on error."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self.logger.warning(f"Missing or invalid translation key: {key} ({e})")
            return f"[MISSING: {key}]"
    
    async def update_memory_selective(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        content: str,
        event_type: Optional[MemoryEventType] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
        config=None,
        error_handler: Optional[ErrorHandler] = None,
        **kwargs
    ) -> str:
        """
        Single entry point for all memory updates.
        
        Replaces SelectiveMemoryManager.update_memory_selective with unified interface
        that handles pre-truncation and consistent guidance style application.
        
        Args:
            agent: The participant agent
            context: Current participant context
            content: Content for memory update (will be truncated if needed)
            event_type: Classified event type for routing
            event_metadata: Additional event-specific data
            config: Experiment configuration (fallback for settings)
            error_handler: Error handler for complex operations
            **kwargs: Additional arguments passed to underlying managers
            
        Returns:
            Updated memory string
        """
        try:
            # Apply content truncation before processing
            truncated_content = self.apply_content_truncation(content, event_type)
            
            # Use SelectiveMemoryManager for the actual update with our truncated content
            updated_memory = await SelectiveMemoryManager.update_memory_selective(
                agent=agent,
                context=context,
                content=truncated_content,
                event_type=event_type,
                event_metadata=event_metadata,
                config=config or self._create_config_fallback(),
                language_manager=self.language_manager,
                error_handler=error_handler,
                utility_agent=self.utility_agent,
                transcript_logger=self.transcript_logger,
                memory_guidance_style=self.memory_guidance_style,
                **kwargs
            )
            
            # Post-append validation for simple events: if memory grew near limit, compress
            try:
                if event_type in getattr(SelectiveMemoryManager, 'SIMPLE_MEMORY_EVENTS', set()):
                    # Determine character limit from context or agent config
                    limit = getattr(context, 'memory_character_limit', None)
                    if not limit and hasattr(agent, 'config'):
                        limit = getattr(agent.config, 'memory_character_limit', None)

                    if limit and isinstance(updated_memory, str):
                        threshold = int(0.9 * int(limit))
                        if len(updated_memory) > threshold:
                            self.logger.debug(
                                f"Memory near limit after simple update for {agent.name}: "
                                f"{len(updated_memory)} > {threshold} (limit {limit}). Compressing..."
                            )
                            compressed = await MemoryManager._compress_memory_if_needed(
                                agent=agent,
                                current_memory=updated_memory,
                                bank_balance=context.bank_balance,
                                memory_limit=int(limit),
                                language_manager=self.language_manager
                            )
                            # Persist compressed memory back to context and return it
                            context.memory = compressed
                            updated_memory = compressed
            except Exception as compress_err:
                # Non-fatal: log and proceed with uncompressed memory
                self.logger.warning(
                    f"Post-append compression skipped due to error for {agent.name}: {compress_err}"
                )

            # Append memory end marker
            marker = self._get_localized_message("memory.memory_end_marker")
            updated_memory = f"{updated_memory}\n\n{marker}"

            self.logger.debug(f"Memory update successful for {agent.name}: {event_type}")
            return updated_memory
            
        except Exception as e:
            self.logger.warning(f"Memory update failed for {agent.name}: {e}")
            # Re-raise to maintain existing error handling behavior
            raise
    
    async def update_discussion_memory(
        self,
        agent: "ParticipantAgent", 
        context: "ParticipantContext",
        statement: str,
        internal_reasoning: str = "",
        round_num: int = 1,
        include_internal_reasoning: bool = True,
        discussion_history: str = "",
        **kwargs
    ) -> str:
        """
        Update memory for discussion statements with consistent formatting.
        
        Args:
            agent: The participant agent
            context: Current participant context
            statement: Public statement made by agent
            internal_reasoning: Internal reasoning (if available)
            round_num: Current round number
            include_internal_reasoning: Whether to include reasoning in memory
            discussion_history: Current discussion history to include in memory
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build memory content with discussion history and recent reasoning
        if discussion_history:
            # Add localized header to discussion history
            history_header = self._get_localized_message("memory_discussion_history_header")
            round_content = f"{history_header}\n{discussion_history}\n\n"

            # Add recent reasoning if available
            if include_internal_reasoning and internal_reasoning:
                reasoning_text = self._get_localized_message(
                    "internal_reasoning_format",
                    reasoning=internal_reasoning
                )
                round_content += f"Your Recent Reasoning:\n{reasoning_text}"
        else:
            # Fallback to old format when no discussion history available
            round_content = self._get_localized_message(
                "round_statement_format",
                round_num=round_num,
                statement=statement
            )
            
            if include_internal_reasoning and internal_reasoning:
                reasoning_text = self._get_localized_message(
                    "internal_reasoning_format",
                    reasoning=internal_reasoning
                )
                round_content += f"\n{reasoning_text}"
        
        event_metadata = {
            'round_number': round_num,
            'participant_name': agent.name,
            'has_internal_reasoning': bool(internal_reasoning)
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=round_content,
            event_type=MemoryEventType.DISCUSSION_STATEMENT,
            event_metadata=event_metadata,
            **kwargs
        )
    
    async def update_voting_phase_memory(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext", 
        phase_name: str,
        additional_info: str = "",
        initiator_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Update memory for voting phase transitions.
        
        Args:
            agent: The participant agent
            context: Current participant context
            phase_name: Name of the voting phase (e.g., 'initiation', 'confirmation')
            additional_info: Additional information to include
            initiator_name: Name of the voting initiator (if applicable)
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build memory content using localized messages
        # Note: translations do not define *_with_initiator variants.
        if initiator_name and phase_name == "initiation":
            memory_content = self._get_localized_message(
                "voting_phases.initiation",
                initiator_name=initiator_name
            )
        else:
            memory_content = self._get_localized_message(f"voting_phases.{phase_name}")
        
        # Add additional information if provided
        if additional_info:
            memory_content += f" {additional_info}"
        
        event_metadata = {
            'phase_name': phase_name,
            'initiator_name': initiator_name
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=memory_content,
            event_type=MemoryEventType.PHASE_TRANSITION,
            event_metadata=event_metadata,
            **kwargs
        )
    
    async def update_all_memories_for_voting_phase(
        self,
        participants: List["ParticipantAgent"],
        contexts: List["ParticipantContext"],
        phase_name: str,
        additional_info: str = "",
        initiator_name: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Update all participant memories for voting phase transitions.
        
        Args:
            participants: List of participant agents
            contexts: List of participant contexts
            phase_name: Name of the voting phase
            additional_info: Additional information to include
            initiator_name: Name of the voting initiator (if applicable)
            **kwargs: Additional arguments
        """
        for i, (participant, context) in enumerate(zip(participants, contexts)):
            try:
                contexts[i].memory = await self.update_voting_phase_memory(
                    agent=participant,
                    context=context,
                    phase_name=phase_name,
                    additional_info=additional_info,
                    initiator_name=initiator_name,
                    **kwargs
                )
            except Exception as e:
                self.logger.warning(f"Failed to update voting phase memory for {participant.name}: {e}")
                # Continue with other participants even if one fails
    
    async def update_final_results_memory(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        result_content: str,
        final_earnings: float,
        consensus_reached: bool,
        **kwargs
    ) -> str:
        """
        Update memory with final Phase 2 results.
        
        Args:
            agent: The participant agent
            context: Current participant context
            result_content: Formatted results content
            final_earnings: Agent's final earnings
            consensus_reached: Whether consensus was reached
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Guardrails: quick sanity check to catch accidental Phase 1 content
        try:
            if result_content and "CURRENT TASK: Principle Application" in result_content:
                self.logger.warning(f"update_final_results_memory received Phase 1 application content for {agent.name}; this should not happen")
                # Log preview to help debug
                preview = result_content[:200].replace('\n', ' ')
                self.logger.warning(f"Problematic content preview: {preview}")
        except Exception:
            pass

        formatted_content = self.language_manager.get(
            "memory.final_results_format",
            result_content=result_content
        )
        
        event_metadata = {
            'final_earnings': final_earnings,
            'consensus_reached': consensus_reached
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=formatted_content,
            event_type=MemoryEventType.FINAL_RESULTS,
            event_metadata=event_metadata,
            **kwargs
        )
    
    def apply_content_truncation(self, content: str, event_type: Optional[MemoryEventType] = None) -> str:
        """
        Apply content truncation rules based on event type and content analysis.
        
        Truncation policy:
        - All content: No truncation (full context preserved)
        
        Args:
            content: Original content to potentially truncate
            event_type: Event type for context-aware truncation
            
        Returns:
            Original content without truncation
        """
        # Return content as-is without any truncation
        return content
    
    async def update_vote_initiation_decision_memory(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext", 
        round_num: int,
        wants_vote: bool,
        **kwargs
    ) -> str:
        """
        Update memory with vote initiation decision.
        
        Args:
            agent: The participant agent
            context: Current participant context
            round_num: Round number when decision was made
            wants_vote: Whether agent wants to initiate voting
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build decision content using language manager - matching SimpleMemoryManager format
        decision_key = "initiate_voting" if wants_vote else "continue_discussion"
        decision_text = self.language_manager.get(f"prompts.memory_insertions.{decision_key}")
        
        memory_content = self.language_manager.get(
            "prompts.memory_insertions.vote_initiation_decision",
            round_num=round_num,
            decision=decision_text
        )
        
        event_metadata = {
            'round_number': round_num,
            'wants_vote': wants_vote,
            'participant_name': agent.name
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=memory_content,
            event_type=MemoryEventType.VOTE_INITIATION_RESPONSE,
            event_metadata=event_metadata,
            **kwargs
        )

    async def update_vote_confirmation_memory(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        agrees_to_vote: bool,
        **kwargs
    ) -> str:
        """
        Update memory with vote confirmation decision.
        
        Args:
            agent: The participant agent
            context: Current participant context
            agrees_to_vote: Whether agent agrees to participate in voting
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build confirmation content using language manager - matching SimpleMemoryManager format
        response_key = "agreed_to" if agrees_to_vote else "declined_to"
        response_text = self.language_manager.get(f"prompts.memory_insertions.{response_key}")
        
        memory_content = self.language_manager.get(
            "prompts.memory_insertions.confirmation_response",
            response=response_text
        )
        
        event_metadata = {
            'agrees_to_vote': agrees_to_vote,
            'participant_name': agent.name
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=memory_content,
            event_type=MemoryEventType.VOTING_CONFIRMATION,
            event_metadata=event_metadata,
            **kwargs
        )
    
    async def update_ballot_selection_memory(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        principle_name: str,
        **kwargs
    ) -> str:
        """
        Update memory with ballot selection choice.
        
        Args:
            agent: The participant agent
            context: Current participant context
            principle_name: Name of the selected principle
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build ballot selection content using language manager - matching SimpleMemoryManager format
        memory_content = self.language_manager.get(
            "prompts.memory_insertions.secret_ballot_choice",
            principle_name=principle_name
        )
        
        event_metadata = {
            'principle_name': principle_name,
            'participant_name': agent.name
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=memory_content,
            event_type=MemoryEventType.BALLOT_SELECTION,
            event_metadata=event_metadata,
            **kwargs
        )
    
    async def update_amount_specification_memory(
        self,
        agent: "ParticipantAgent",
        context: "ParticipantContext",
        amount: str,
        **kwargs
    ) -> str:
        """
        Update memory with constraint amount specification.
        
        Args:
            agent: The participant agent
            context: Current participant context
            amount: Specified constraint amount (formatted string)
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build amount specification content using language manager - matching SimpleMemoryManager format
        memory_content = self.language_manager.get(
            "prompts.memory_insertions.amount_specification",
            amount=amount
        )
        
        event_metadata = {
            'amount': amount,
            'participant_name': agent.name
        }
        
        return await self.update_memory_selective(
            agent=agent,
            context=context,
            content=memory_content,
            event_type=MemoryEventType.AMOUNT_SPECIFICATION,
            event_metadata=event_metadata,
            **kwargs
        )
    
    def validate_and_sanitize_memory(self, memory: str, character_limit: int, participant_name: str) -> str:
        """
        Validate and sanitize memory for safe Phase 2 initialization.
        
        Args:
            memory: Raw memory string from Phase 1
            character_limit: Maximum allowed characters
            participant_name: Name of participant for logging
            
        Returns:
            Sanitized memory string
        """
        # Check if memory is None or corrupted
        if memory is None:
            self.logger.warning(f"Null memory detected for {participant_name}, initializing empty")
            return ""
        
        # Ensure string type
        if not isinstance(memory, str):
            self.logger.warning(f"Non-string memory detected for {participant_name}, converting")
            try:
                memory = str(memory)
            except Exception as e:
                self.logger.warning(f"Failed to convert memory for {participant_name}: {e}")
                return ""
        
        # Log memory size but don't truncate - let memory manager handle overflow
        if len(memory) > character_limit:
            self.logger.info(f"Memory exceeds base limit for {participant_name}: {len(memory)} > {character_limit} (will be handled by memory manager)")
        
        # Remove any null bytes or control characters that could cause issues
        memory = memory.replace('\x00', '')
        memory = ''.join(char for char in memory if ord(char) >= 32 or char in '\n\r\t')
        
        return memory
    
    def _create_config_fallback(self):
        """
        Create fallback config object when none provided.
        
        Returns:
            Mock config object with essential attributes
        """
        class ConfigFallback:
            def __init__(self, settings: Phase2Settings):
                self.memory_guidance_style = getattr(settings, 'memory_guidance_style', 'structured')
                self.selective_memory_updates = getattr(settings, 'selective_memory_updates', True)
        
        return ConfigFallback(self.settings)
