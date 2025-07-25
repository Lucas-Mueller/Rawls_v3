"""
Participant agent system for the Frohlich Experiment.
"""
from agents import Agent, RunContextWrapper, ModelSettings, Runner

from config import AgentConfiguration
from models import ParticipantContext, ExperimentPhase


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


class ParticipantAgent:
    """Wrapper for participant agent with memory management capabilities."""
    
    def __init__(self, config: AgentConfiguration):
        self.config = config
        self.agent = Agent[ParticipantContext](
            name=config.name,
            instructions=lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, config),
            model=config.model,
            model_settings=ModelSettings(temperature=config.temperature)
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
    
    context = ctx.context
    
    # Format memory for display
    formatted_memory = f"=== YOUR MEMORY ===\n{context.memory if context.memory.strip() else '(Empty)'}\n{'='*20}"
    
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

RESPONSE FORMAT:
Please structure your response as follows:
1. [Your best choice]
2. [Your second choice]
3. [Your third choice]
4. [Your worst choice]

Overall certainty: [very unsure/unsure/no opinion/sure/very sure]

Then provide your detailed reasoning for this ranking.

Example:
1. Maximizing average with floor constraint
2. Maximizing the floor income
3. Maximizing average income
4. Maximizing average with range constraint

Overall certainty: sure

[Your reasoning here...]
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

RESPONSE FORMAT:
Please structure your response as follows:
1. State your choice clearly: "I choose [principle a/b/c/d]"
2. If choosing c or d, specify: "with a constraint of $[amount]"
3. State your certainty: "I am [very unsure/unsure/sure/very sure] about this choice"
4. Explain your reasoning in detail

Example: "I choose principle c (maximizing average with floor constraint) with a constraint of $15,000. I am sure about this choice because it balances efficiency with protecting the worst-off."
"""
        elif round_number == 5:  # Final ranking
            return """
CURRENT TASK: Final Principle Ranking
After experiencing the four rounds of principle application, rank the principles again from best (1) to worst (4).
Reflect on what you learned from applying these principles and how it may have changed your preferences.

RESPONSE FORMAT:
Please structure your response as follows:
1. [Your best choice]
2. [Your second choice] 
3. [Your third choice]
4. [Your worst choice]

Overall certainty: [very unsure/unsure/no opinion/sure/very sure]

Then explain how your experience in the four application rounds influenced your ranking.

Example:
1. Maximizing the floor income
2. Maximizing average with floor constraint
3. Maximizing average income
4. Maximizing average with range constraint

Overall certainty: very sure

After applying these principles, I learned that...
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

RESPONSE FORMAT:
Structure your discussion statement clearly:
1. Share your perspective based on Phase 1 experience
2. Respond to others' points if applicable
3. If ready to vote, clearly state: "I propose we vote on [specific principle with constraint if applicable]"
4. End with your current preferred principle

Example: "Based on my Phase 1 experience, I found that the floor constraint principle worked well because... I agree with [participant] that efficiency matters, but I think we should prioritize protecting the worst-off. I propose we vote on maximizing average with a floor constraint of $18,000."

The group's chosen principle will determine everyone's final earnings.
If no consensus is reached, final earnings will be randomly determined.
"""
    
    return "No specific instructions for current phase/round."




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