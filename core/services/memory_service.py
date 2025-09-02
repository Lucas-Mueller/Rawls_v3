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
        config=None
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
        
        # Content truncation limits
        self.statement_max_chars = 300
        self.reasoning_max_chars = 200
        
        # Memory guidance style from config (falls back to 'narrative')
        self.memory_guidance_style = getattr(config, 'memory_guidance_style', 'narrative') if config else 'narrative'
    
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
                memory_guidance_style=self.memory_guidance_style,
                **kwargs
            )
            
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
            **kwargs: Additional arguments
            
        Returns:
            Updated memory string
        """
        # Build memory content similar to Phase2Manager's round_content construction
        round_content = f"Round {round_num}: Your statement: {statement}"
        
        if include_internal_reasoning and internal_reasoning:
            round_content += f"\nInternal reasoning: {internal_reasoning}"
        
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
        if initiator_name:
            memory_content = self.language_manager.get(
                f"voting_phases.{phase_name}_with_initiator", 
                initiator_name=initiator_name
            )
        else:
            memory_content = self.language_manager.get(f"voting_phases.{phase_name}")
        
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
        formatted_content = f"Final Phase 2 Results: {result_content}"
        
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
        - Statements: ≤300 characters (preserves meaning while preventing memory bloat)
        - Internal reasoning: ≤200 characters (less critical for memory continuity)
        - Other content: No truncation (full context preserved)
        
        Args:
            content: Original content to potentially truncate
            event_type: Event type for context-aware truncation
            
        Returns:
            Truncated content if applicable, original content otherwise
        """
        if not content:
            return content
        
        # Extract statement and reasoning parts for discussion events
        if event_type == MemoryEventType.DISCUSSION_STATEMENT:
            lines = content.split('\n')
            truncated_lines = []
            
            for line in lines:
                if line.startswith('Round ') and 'statement:' in line:
                    # Extract statement part
                    statement_part = line.split('statement:', 1)[1].strip() if 'statement:' in line else line
                    if len(statement_part) > self.statement_max_chars:
                        statement_part = statement_part[:self.statement_max_chars].rstrip() + '...'
                    truncated_lines.append(line.split('statement:', 1)[0] + 'statement: ' + statement_part)
                elif line.startswith('Internal reasoning:'):
                    # Extract reasoning part
                    reasoning_part = line.split(':', 1)[1].strip() if ':' in line else line
                    if len(reasoning_part) > self.reasoning_max_chars:
                        reasoning_part = reasoning_part[:self.reasoning_max_chars].rstrip() + '...'
                    truncated_lines.append('Internal reasoning: ' + reasoning_part)
                else:
                    # Keep other lines as-is (metadata, formatting)
                    truncated_lines.append(line)
            
            return '\n'.join(truncated_lines)
        
        # For non-discussion events, return content as-is (no truncation needed)
        return content
    
    def _create_config_fallback(self):
        """
        Create fallback config object when none provided.
        
        Returns:
            Mock config object with essential attributes
        """
        class ConfigFallback:
            def __init__(self, settings: Phase2Settings):
                self.memory_guidance_style = getattr(settings, 'memory_guidance_style', 'narrative')
                self.selective_memory_updates = getattr(settings, 'selective_memory_updates', True)
        
        return ConfigFallback(self.settings)