"""
Participant agent system for the Frohlich Experiment.
"""
from agents import Agent, RunContextWrapper, ModelSettings

from config import AgentConfiguration
from models import ParticipantContext, ExperimentPhase
from utils.memory_manager import MemoryManager


# Broad experiment explanation that gets included in all agent instructions
BROAD_EXPERIMENT_EXPLANATION = """
You are participating in an experiment studying principles of justice and income distribution.

The experiment has two main phases:

PHASE 1: You will individually learn about and apply four different principles of justice to income distributions. You will be asked to rank these principles by preference and apply them to specific scenarios. Your choices will affect your earnings.

PHASE 2: You will join a group discussion to reach consensus on which principle of justice the group should adopt. The group's chosen principle will then be applied to determine everyone's final earnings.

The Four Justice Principles:
1. **Maximizing the floor income**: Choose the distribution that maximizes the lowest income in society
2. **Maximizing the average income**: Choose the distribution that maximizes the average income  
3. **Maximizing the average income with a floor constraint**: Maximize average income while ensuring everyone gets at least a specified minimum
4. **Maximizing the average income with a range constraint**: Maximize average income while keeping the gap between richest and poorest within a specified limit

Throughout the experiment, maintain your assigned personality while engaging thoughtfully with the principles and other participants.
"""


def create_participant_agent(config: AgentConfiguration) -> Agent[ParticipantContext]:
    """Create a participant agent with the given configuration."""
    return Agent[ParticipantContext](
        name=config.name,
        instructions=lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
        model=config.model,
        model_settings=ModelSettings(temperature=config.temperature)
        # Note: output_type will be set dynamically based on the specific task
    )


def _generate_dynamic_instructions(
    ctx: RunContextWrapper[ParticipantContext], 
    agent: Agent, 
    config: AgentConfiguration
) -> str:
    """Generate context-aware instructions including memory, bank balance, etc."""
    
    context = ctx.context
    
    # Format memory for display
    formatted_memory = MemoryManager.format_memory_prompt(context.memory, context.phase)
    
    # Phase-specific instructions
    phase_instructions = _get_phase_specific_instructions(context.phase, context.round_number)
    
    return f"""
Name: {context.name}
Role Description: {context.role_description}
Bank Balance: ${context.bank_balance:.2f}
Current Phase: {context.phase.value.replace('_', ' ').title()}
Round: {context.round_number}

{formatted_memory}

{BROAD_EXPERIMENT_EXPLANATION}

PERSONALITY: {config.personality}

{phase_instructions}

Remember to stay true to your personality while participating thoughtfully in the experiment.
Provide clear, reasoned responses that explain your thinking.
"""


def _get_phase_specific_instructions(phase: ExperimentPhase, round_number: int) -> str:
    """Get instructions specific to the current phase and round."""
    
    if phase == ExperimentPhase.PHASE_1:
        if round_number == 0:
            return """
CURRENT TASK: Initial Principle Ranking
You will be asked to rank the four justice principles from best (1) to worst (4) based on your preference.
For each principle, also indicate your certainty level (very unsure, unsure, no opinion, sure, very sure).
Explain your reasoning clearly.
"""
        elif round_number == -1:  # Special case for detailed explanation step
            return """
CURRENT TASK: Learning About Principle Applications
You will be shown examples of how each justice principle would be applied to specific income distributions.
This is for learning purposes - pay attention to how each principle works in practice.
"""
        elif 1 <= round_number <= 4:
            return f"""
CURRENT TASK: Principle Application (Round {round_number} of 4)
You will be shown 4 income distributions and must choose ONE of the justice principles to apply.
If you choose a constraint principle (floor or range), you MUST specify the constraint amount in dollars.
Your choice will determine which distribution is selected, and you'll be randomly assigned to an income class within that distribution.
Your earnings will be $1 for every $10,000 of income you receive.
"""
        elif round_number == 5:  # Final ranking
            return """
CURRENT TASK: Final Principle Ranking
After experiencing the four rounds of principle application, rank the principles again from best (1) to worst (4).
Reflect on what you learned from applying these principles and how it may have changed your preferences.
"""
    
    elif phase == ExperimentPhase.PHASE_2:
        return f"""
CURRENT TASK: Group Discussion (Round {round_number})
You are now in the group discussion phase. Work with other participants to reach consensus on which justice principle the group should adopt.

DISCUSSION RULES:
- Take turns speaking in the assigned order
- Listen to others' perspectives and reasoning  
- Share your own views based on your Phase 1 experiences
- You may propose a vote when you think the group is ready
- All participants must agree to vote before voting begins
- Consensus requires everyone to choose the EXACT same principle (including constraint amounts)

The group's chosen principle will determine everyone's final earnings.
If no consensus is reached, final earnings will be randomly determined.
"""
    
    return "No specific instructions for current phase/round."


def create_agent_with_output_type(config: AgentConfiguration, output_type: type) -> Agent[ParticipantContext]:
    """Create a participant agent with a specific output type for structured responses."""
    base_agent = create_participant_agent(config)
    return base_agent.clone(output_type=output_type)


def update_participant_context(
    context: ParticipantContext,
    memory_update: str,
    balance_change: float = 0.0,
    new_round: int = None,
    new_phase: ExperimentPhase = None
) -> ParticipantContext:
    """Update participant context with new information."""
    
    # Update memory
    updated_memory = MemoryManager.update_memory(
        context.memory, 
        memory_update, 
        context.max_memory_length,
        priority_sections=["INITIAL RANKING", "FINAL RANKING", "EARNINGS", "PHASE TRANSITION"]
    )
    
    # Create updated context
    updated_context = ParticipantContext(
        name=context.name,
        role_description=context.role_description,
        bank_balance=context.bank_balance + balance_change,
        memory=updated_memory,
        round_number=new_round if new_round is not None else context.round_number,
        phase=new_phase if new_phase is not None else context.phase,
        max_memory_length=context.max_memory_length
    )
    
    return updated_context