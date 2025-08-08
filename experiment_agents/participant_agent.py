"""
Participant agent system for the Frohlich Experiment.
"""
from agents import Agent, RunContextWrapper, ModelSettings, Runner

from config import AgentConfiguration
from models import ParticipantContext, ExperimentPhase
from utils.model_provider import create_model_config
from utils.language_manager import get_language_manager


# This will be replaced by dynamic language manager calls


class ParticipantAgent:
    """Wrapper for participant agent with memory management capabilities."""
    
    def __init__(self, config: AgentConfiguration):
        self.config = config
        
        # Use new model provider logic
        model_config = create_model_config(config.model, config.temperature)
        
        # Handle ModelSettings creation - both OpenAI and LiteLLM use ModelSettings for temperature
        model_settings = ModelSettings(temperature=config.temperature)
        self.agent = Agent[ParticipantContext](
            name=config.name,
            instructions=lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
            model=model_config,
            model_settings=model_settings
        )
    
    @property
    def name(self) -> str:
        return self.agent.name
    
    async def update_memory(self, prompt: str, current_bank_balance: float = 0.0) -> str:
        """Agent updates their own memory based on prompt."""
        # Create a temporary context just for memory update
        temp_context = ParticipantContext(
            name=self.config.name,
            role_description="Memory update",
            bank_balance=current_bank_balance,
            memory="",
            round_number=0,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=self.config.memory_character_limit
        )
        
        result = await Runner.run(self.agent, prompt, context=temp_context)
        return result.final_output
    
    def clone(self, **kwargs):
        """Clone the underlying agent with modifications."""
        return self.agent.clone(**kwargs)


def create_participant_agent(config: AgentConfiguration) -> ParticipantAgent:
    """Create a participant agent with the given configuration."""
    return ParticipantAgent(config)


def _generate_dynamic_instructions(
    ctx: RunContextWrapper[ParticipantContext], 
    agent: Agent, 
    config: AgentConfiguration
) -> str:
    """Generate context-aware instructions including memory, bank balance, etc."""
    
    language_manager = get_language_manager()
    context = ctx.context
    
    # Format memory for display using language manager
    memory_content = context.memory if context.memory.strip() else None
    formatted_memory = language_manager.format_memory_section(memory_content or "")
    
    # Get phase-specific instructions using language manager
    phase_instructions = _get_phase_specific_instructions_translated(
        context.phase, context.round_number, language_manager
    )
    
    # Format everything using language manager
    return language_manager.format_context_info(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance,
        phase=context.phase.value.replace('_', ' ').title(),
        round_number=context.round_number,
        formatted_memory=formatted_memory,
        personality=config.personality,
        phase_instructions=phase_instructions
    )


def _get_phase_specific_instructions_translated(phase: ExperimentPhase, round_number: int, language_manager) -> str:
    """Get instructions specific to the current phase and round using language manager."""
    
    if phase == ExperimentPhase.PHASE_1:
        return language_manager.get_phase1_instructions(round_number)
    elif phase == ExperimentPhase.PHASE_2:
        return language_manager.get_phase2_instructions(round_number)
    else:
        return language_manager.get_prompt("fallback", "default_phase_instructions")


# Old hardcoded function replaced by _get_phase_specific_instructions_translated()




def update_participant_context(
    context: ParticipantContext,
    balance_change: float = 0.0,
    new_round: int = None,
    new_phase: ExperimentPhase = None
) -> ParticipantContext:
    """Update participant context with new information (memory handled separately)."""
    
    # Create updated context
    updated_context = ParticipantContext(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance + balance_change,
        memory=context.memory,  # Memory updated separately by agent
        round_number=new_round if new_round is not None else context.round_number,
        phase=new_phase if new_phase is not None else context.phase,
        memory_character_limit=context.memory_character_limit
    )
    
    return updated_context