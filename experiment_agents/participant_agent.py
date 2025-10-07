"""
Participant agent system for the Frohlich Experiment.
"""
from agents import Agent, RunContextWrapper, ModelSettings, Runner

from config import AgentConfiguration
from models import ParticipantContext, ExperimentPhase, ExperimentStage
from utils.model_provider import create_model_config_with_temperature_detection, create_model_settings, create_model_config_sync
from utils.dynamic_model_capabilities import create_agent_with_temperature_retry
# Voting tools removed - now using prompt-based voting
import asyncio
import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.logging import TranscriptLogger

# This will be replaced by dynamic language manager calls


class ParticipantAgent:
    """Wrapper for participant agent with memory management capabilities and dynamic temperature detection."""
    
    def __init__(self, config: AgentConfiguration, experiment_config=None, language_manager=None, temperature_cache=None):
        self.config = config
        self.experiment_config = experiment_config
        self.language_manager = language_manager
        self.temperature_cache = temperature_cache
        self.logger = logging.getLogger(__name__)
        
        # We'll initialize the agent asynchronously in async_init
        self.agent = None
        self.temperature_info = None
        self._initialization_complete = False

    async def async_init(self):
        """Asynchronously initialize the agent with dynamic temperature detection."""
        if self._initialization_complete:
            return
        
        # Prepare base agent kwargs (without model and model_settings)
        base_kwargs = {
            "name": self.config.name,
            "instructions": lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, self.config, self.experiment_config, self.language_manager),
            "tools": [],  # All voting tools removed - now using prompt-based voting
        }
        
        # Use dynamic temperature retry system
        try:
            self.logger.info(f"Creating agent {self.config.name} with dynamic temperature detection")
            
            self.agent, self.temperature_info = await create_agent_with_temperature_retry(
                agent_class=Agent[ParticipantContext],
                model_string=self.config.model,
                temperature=self.config.temperature,
                agent_kwargs=base_kwargs,
                cache=self.temperature_cache
            )
            
            # Log temperature status
            self._log_temperature_status()
            
            self._initialization_complete = True
            self.logger.info(f"✅ Successfully initialized agent {self.config.name}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize agent {self.config.name}: {e}")
            raise e
    
    def _log_temperature_status(self):
        """Log temperature detection status."""
        if not self.temperature_info:
            return
            
        temp_info = self.temperature_info
        detection_method = temp_info.get('detection_method', 'unknown')
        
        if temp_info.get("supports_temperature", False):
            # Temperature supported
            effective_temp = temp_info.get('effective_temperature')
            if effective_temp is not None:
                self.logger.info(
                    f"✅ {self.config.name}: Temperature {effective_temp} active "
                    f"(method: {detection_method})"
                )
            else:
                self.logger.info(
                    f"✅ {self.config.name}: Temperature support confirmed, none requested "
                    f"(method: {detection_method})"
                )
        else:
            # Temperature not supported
            requested = temp_info.get('requested_temperature')
            was_retried = temp_info.get('was_retried', False)
            
            if was_retried:
                self.logger.warning(
                    f"🔄 {self.config.name}: Temperature {requested} not supported, "
                    f"automatically retried without temperature (method: {detection_method})"
                )
            else:
                self.logger.warning(
                    f"❌ {self.config.name}: Temperature {requested} not supported, "
                    f"using default behavior (method: {detection_method})"
                )
    
    @property
    def name(self) -> str:
        if self.agent is None:
            return self.config.name
        return self.agent.name
    
    async def update_memory(self, prompt: str, current_bank_balance: float = 0.0,
                           phase: ExperimentPhase = ExperimentPhase.PHASE_1,
                           round_number: int = 0,
                           role_description: str = None,
                           stage: ExperimentStage = None,
                           transcript_logger: Optional["TranscriptLogger"] = None) -> str:
        """Agent updates their own memory based on prompt using minimal context."""
        # Ensure agent is initialized
        await self.async_init()

        # Use provided role_description or fall back to config personality
        actual_role = role_description if role_description is not None else self.config.personality

        # Create a specialized memory update context that uses minimal formatting
        temp_context = ParticipantContext(
            name=self.config.name,
            role_description="MemoryUpdate",  # Special role for memory context detection
            bank_balance=current_bank_balance,
            memory="",
            round_number=round_number,
            phase=phase,
            memory_character_limit=self.config.memory_character_limit,
            interaction_type="memory_update",  # For consistency with existing interaction types
            stage=stage  # Pass stage for discussion header display
        )

        # Store actual role description for formatting
        temp_context._actual_role_description = actual_role

        if transcript_logger and transcript_logger.config.include_memory_updates:
            from utils.logging import run_with_transcript_logging

            result = await run_with_transcript_logging(
                participant=self,
                prompt=prompt,
                context=temp_context,
                transcript_logger=transcript_logger,
                interaction_type="memory_update"
            )
        else:
            result = await Runner.run(self.agent, prompt, context=temp_context)
        return result.final_output

    def get_instructions_for_context(self, context: ParticipantContext) -> str:
        """Generate the instructions that would be sent for the provided context."""
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call async_init() first.")

        wrapper = RunContextWrapper(context=context)
        return _generate_dynamic_instructions(
            wrapper,
            self.agent,
            self.config,
            self.experiment_config,
            self.language_manager
        )

    def clone(self, **kwargs):
        """Clone the underlying agent with modifications."""
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call async_init() first.")
        return self.agent.clone(**kwargs)


async def create_participant_agent(config: AgentConfiguration, language_manager=None, temperature_cache=None) -> ParticipantAgent:
    """Create a participant agent with the given configuration."""
    agent = ParticipantAgent(config, language_manager=language_manager, temperature_cache=temperature_cache)
    await agent.async_init()
    return agent


async def create_participant_agents_with_dynamic_temperature(
    configs: List[AgentConfiguration],
    experiment_config=None,
    language_manager=None,
    temperature_cache=None
) -> List[ParticipantAgent]:
    """
    Create multiple participant agents with dynamic temperature detection and retry.
    """
    if not configs:
        return []
    
    logger = logging.getLogger(__name__)
    logger.info(f"Creating {len(configs)} participant agents with dynamic temperature detection...")
    
    # Create agents with dynamic temperature detection
    agents = []
    for config in configs:
        try:
            logger.info(f"Creating agent: {config.name} (model: {config.model}, temp: {config.temperature})")
            agent = ParticipantAgent(config, experiment_config, language_manager, temperature_cache)
            await agent.async_init()
            agents.append(agent)
        except Exception as e:
            logger.error(f"Failed to create agent {config.name}: {e}")
            raise e
    
    logger.info(f"✅ Successfully created {len(agents)} participant agents")
    return agents


def _detect_memory_context_type(context: ParticipantContext, role_description: str) -> str:
    """
    Detect the appropriate context type for memory operations.
    
    NOTE: Currently only used for logging/debugging since display_mode is always "full".
    Kept for potential future features like context-aware memory processing.
    
    Args:
        context: Participant context with phase and round information
        role_description: Current role description
        
    Returns:
        Context type: "voting", "discussion", "application", or "general"
    """
    # Check for voting-related contexts
    if any(keyword in role_description.lower() for keyword in ["vote", "ballot", "consensus"]):
        return "voting"
    
    # Phase 1 application contexts
    if context.phase == ExperimentPhase.PHASE_1 and context.round_number >= 1:
        return "application"
    
    # Phase 2 discussion contexts
    if context.phase == ExperimentPhase.PHASE_2:
        # If we're in Phase 2, it's primarily discussion unless voting
        if "vote" not in role_description.lower():
            return "discussion"
        else:
            return "voting"
    
    # Default to general context
    return "general"


def _generate_dynamic_instructions(
    ctx: RunContextWrapper[ParticipantContext], 
    agent: Agent, 
    config: AgentConfiguration,
    experiment_config=None,
    language_manager=None
) -> str:
    """Generate context-aware instructions including memory, bank balance, etc."""
    
    # Guard against missing context during model capability probes
    if ctx is None or getattr(ctx, 'context', None) is None:
        if language_manager:
            try:
                return language_manager.get("prompts.fallback_default_agent_instruction")
            except Exception:
                pass
        return "You are a participant agent in the Frohlich Experiment. Respond concisely."
    
    context = ctx.context
    
    # Check if this is a memory update context and use minimal formatting
    if context.role_description == "MemoryUpdate":
        # Use the actual role description stored in the context, or fall back to config
        actual_role = getattr(context, '_actual_role_description', config.personality)
        return language_manager.format_memory_context(
            name=context.name,
            bank_balance=context.bank_balance,
            personality=config.personality,
            role_description=actual_role,
            phase=context.phase,
            round_number=context.round_number,
            stage=context.stage,
            experiment_config=experiment_config
        )
    
    # Standard context formatting for regular operations
    # Detect memory context type for appropriate summarization
    memory_context_type = _detect_memory_context_type(context, context.role_description)
    
    # Always use full memory display to ensure agents have complete context
    display_mode = "full"
    
    # Format memory for display using language manager with context awareness
    memory_content = context.memory if context.memory and context.memory.strip() else None
    formatted_memory = language_manager.format_memory_section(
        memory_content or "", 
        display_mode=display_mode,
        context_type=memory_context_type
    )
    
    # Get phase-specific instructions using language manager
    stage = getattr(context, 'stage', None)
    stage_key = stage.value if isinstance(stage, ExperimentStage) else stage

    # Initialize variables for Phase 2 context header
    phase2_max_rounds = None
    phase2_participant_names = None
    stage_header = ""
    stage_kwargs = {}

    if language_manager and stage_key == ExperimentStage.FINAL_RANKING.value:
        try:
            phase_key = context.phase.value.replace('_', '') if context.phase else None
            if phase_key:
                stage_kwargs['phase_label'] = language_manager.get_phase_name(phase_key)
        except Exception:
            stage_kwargs.pop('phase_label', None)

    # Start with baseline instructions derived from phase/round context
    phase_instructions = _get_phase_specific_instructions_translated(
        context.phase, context.round_number, language_manager, experiment_config
    )

    if context.phase == ExperimentPhase.PHASE_2:
        max_rounds = experiment_config.phase2_rounds if experiment_config else 5
        phase2_max_rounds = max_rounds  # Store for context header

        # Extract participant names for context header
        participant_names = []
        try:
            if experiment_config and getattr(experiment_config, 'agents', None):
                participant_names = [getattr(a, 'name', '') for a in experiment_config.agents if getattr(a, 'name', '')]
        except Exception:
            participant_names = []
        phase2_participant_names = participant_names  # Store for context header

        if stage_key:
            stage_header = language_manager.get_context_stage_instruction(
                stage_key,
                round_number=context.round_number,
                max_rounds=max_rounds,
                **stage_kwargs
            )

        if stage_key == ExperimentStage.DISCUSSION.value:
            # Phase 2 discussion REQUIRES pre-formatted context header (explicit data flow)
            if not hasattr(context, 'formatted_context_header'):
                raise ValueError(
                    f"Phase 2 discussion context for {context.name} missing 'formatted_context_header' field. "
                    f"Upgrade ParticipantContext model to include this field."
                )
            if context.formatted_context_header is None:
                raise ValueError(
                    f"Phase 2 discussion context for {context.name} has formatted_context_header=None. "
                    f"Phase2Manager must set this field before calling Runner. "
                    f"Current round: {context.round_number}"
                )
            # Use pre-formatted header (explicit data flow, no side channel)
            phase_instructions = context.formatted_context_header
        elif stage_key:
            # Other Phase 2 sub-stages use generic fallback instructions to avoid duplicating status lines
            phase_instructions = language_manager.get("prompts.fallback_default_phase_instructions")
        else:
            # Phase 2 without explicit stage - should use formatted_context_header if available
            if hasattr(context, 'formatted_context_header') and context.formatted_context_header is not None:
                phase_instructions = context.formatted_context_header
            else:
                # Fallback: This shouldn't happen in normal Phase 2 flow
                raise ValueError(
                    f"Phase 2 context for {context.name} has no stage key and no formatted_context_header. "
                    f"Phase2Manager must set context.stage or context.formatted_context_header."
                )
    else:
        if stage_key:
            stage_header = language_manager.get_context_stage_instruction(
                stage_key,
                round_number=context.round_number,
                **stage_kwargs
            )

        if stage_key == ExperimentStage.APPLICATION.value and context.round_number is not None:
            phase_instructions = language_manager.get_phase1_instructions(context.round_number)
        else:
            phase_instructions = language_manager.get_phase1_instructions(context.round_number)

    # Format everything using language manager with config-aware explanation inclusion
    stage_header_formatted = f"{stage_header}\n" if stage_header else ""

    return language_manager.format_context_info(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance,
        phase=context.phase.value.replace('_', ' ').title(),
        round_number=context.round_number,
        formatted_memory=formatted_memory,
        personality=config.personality,
        phase_instructions=phase_instructions,
        experiment_config=experiment_config,
        internal_reasoning=getattr(context, 'internal_reasoning', ''),
        stage=stage,
        max_rounds=phase2_max_rounds,
        participant_names=phase2_participant_names,
        stage_header=stage_header_formatted,
        interaction_type=getattr(context, 'interaction_type', None)
    )


def _get_phase_specific_instructions_translated(phase: ExperimentPhase, round_number: int, language_manager, experiment_config=None) -> str:
    """Get instructions specific to the current phase and round using language manager."""
    
    if phase == ExperimentPhase.PHASE_1:
        return language_manager.get_phase1_instructions(round_number)
    elif phase == ExperimentPhase.PHASE_2:
        max_rounds = experiment_config.phase2_rounds if experiment_config else 5
        return language_manager.get_phase2_instructions(round_number, max_rounds)
    else:
        return language_manager.get_prompt("fallback", "default_phase_instructions")


# Old hardcoded function replaced by _get_phase_specific_instructions_translated()




def update_participant_context(
    context: ParticipantContext,
    balance_change: float = 0.0,
    new_round: int = None,
    new_phase: ExperimentPhase = None,
    new_stage: ExperimentStage | None = None
) -> ParticipantContext:
    """Update participant context with new information (memory handled separately)."""

    # Preserve first_memory_update flag unless phase explicitly changes
    first_memory_update = getattr(context, 'first_memory_update', True)
    if new_phase is not None and new_phase != context.phase:
        first_memory_update = True

    # Create updated context
    updated_context = ParticipantContext(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance + balance_change,
        memory=context.memory,  # Memory updated separately by agent
        round_number=new_round if new_round is not None else context.round_number,
        phase=new_phase if new_phase is not None else context.phase,
        memory_character_limit=context.memory_character_limit,
        interaction_type=context.interaction_type,  # Preserve interaction_type for tool availability
        internal_reasoning=context.internal_reasoning,
        stage=new_stage if new_stage is not None else context.stage,
        formatted_context_header=getattr(context, 'formatted_context_header', None),  # Preserve formatted header
        allow_vote_tool=getattr(context, 'allow_vote_tool', True),  # Preserve vote tool setting
        first_memory_update=first_memory_update
    )

    return updated_context
