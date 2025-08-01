"""
Phase 1 manager for individual participant familiarization.
"""
import asyncio
from typing import List
from agents import Agent, Runner

from models import (
    ParticipantContext, Phase1Results, ApplicationResult, ExperimentPhase,
    PrincipleRanking, PrincipleRankingResponse, PrincipleChoiceResponse,
    IncomeClass
)
from config import ExperimentConfiguration, AgentConfiguration
from experiment_agents import create_agent_with_output_type, update_participant_context, UtilityAgent
from core.distribution_generator import DistributionGenerator
from utils.memory_manager import MemoryManager


class Phase1Manager:
    """Manages Phase 1 execution for all participants."""
    
    def __init__(self, participants: List[Agent], utility_agent: UtilityAgent):
        self.participants = participants
        self.utility_agent = utility_agent
    
    async def run_phase1(self, config: ExperimentConfiguration) -> List[Phase1Results]:
        """Execute complete Phase 1 for all participants in parallel."""
        
        tasks = []
        for i, participant in enumerate(self.participants):
            agent_config = config.agents[i]
            context = self._create_initial_participant_context(agent_config)
            task = asyncio.create_task(
                self._run_single_participant_phase1(participant, context, config, agent_config)
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    def _create_initial_participant_context(self, agent_config: AgentConfiguration) -> ParticipantContext:
        """Create initial context for a participant."""
        return ParticipantContext(
            name=agent_config.name,
            role_description=agent_config.personality,
            bank_balance=0.0,
            memory="Experiment starting. I am participating in a study of justice principles and income distribution.",
            round_number=0,
            phase=ExperimentPhase.PHASE_1,
            max_memory_length=agent_config.memory_length
        )
    
    async def _run_single_participant_phase1(
        self,
        participant: Agent,
        context: ParticipantContext,
        config: ExperimentConfiguration,
        agent_config: AgentConfiguration
    ) -> Phase1Results:
        """Run complete Phase 1 for a single participant."""
        
        # 1.1 Initial Principle Ranking
        context.round_number = 0
        initial_ranking = await self._step_1_1_initial_ranking(participant, context, agent_config)
        context = update_participant_context(
            context,
            f"INITIAL RANKING: Completed initial ranking of justice principles. My top choice was {initial_ranking.rankings[0].principle.value}.",
            new_round=context.round_number
        )
        
        # 1.2 Detailed Explanation (informational only)
        context.round_number = -1  # Special round for learning
        await self._step_1_2_detailed_explanation(participant, context, agent_config)
        context = update_participant_context(
            context,
            "DETAILED EXPLANATION: Learned how each justice principle is applied to income distributions through examples.",
            new_round=context.round_number
        )
        
        # 1.3 Repeated Application (4 rounds)
        application_results = []
        for round_num in range(1, 5):
            context.round_number = round_num
            
            # Generate dynamic distribution for this round
            distribution_set = DistributionGenerator.generate_dynamic_distribution(
                config.distribution_range_phase1
            )
            
            result = await self._step_1_3_principle_application(
                participant, context, distribution_set, round_num, agent_config
            )
            application_results.append(result)
            
            # Update context with earnings and feedback
            context = update_participant_context(
                context,
                f"ROUND {round_num}: Chose {result.principle_choice.principle.value}, assigned to {result.assigned_income_class.value} class, earned ${result.earnings:.2f}. Total earnings now ${context.bank_balance + result.earnings:.2f}.",
                balance_change=result.earnings,
                new_round=round_num
            )
        
        # 1.4 Final Ranking
        context.round_number = 5
        final_ranking = await self._step_1_4_final_ranking(participant, context, agent_config)
        context = update_participant_context(
            context,
            f"FINAL RANKING: Completed final ranking. My top choice is now {final_ranking.rankings[0].principle.value}.",
            new_round=context.round_number
        )
        
        return Phase1Results(
            participant_name=participant.name,
            initial_ranking=initial_ranking,
            application_results=application_results,
            final_ranking=final_ranking,
            total_earnings=context.bank_balance,
            final_memory_state=context.memory  # CRITICAL: Preserve memory for Phase 2
        )
    
    async def _step_1_1_initial_ranking(
        self, 
        participant: Agent, 
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> PrincipleRanking:
        """Step 1.1: Initial principle ranking with certainty."""
        
        ranking_prompt = self._build_ranking_prompt()
        
        # Create agent with structured output type
        ranking_agent = create_agent_with_output_type(agent_config, PrincipleRankingResponse)
        
        result = await Runner.run(ranking_agent, ranking_prompt, context=context)
        
        # Parse and validate response using utility agent
        try:
            parsed_ranking = await self.utility_agent.parse_principle_ranking(
                result.final_output.ranking_explanation + " " + str(result.final_output.principle_rankings.dict())
            )
            return parsed_ranking
        except Exception as e:
            # Fallback to the structured response if parsing fails
            return result.final_output.principle_rankings
    
    async def _step_1_2_detailed_explanation(
        self,
        participant: Agent,
        context: ParticipantContext, 
        agent_config: AgentConfiguration
    ):
        """Step 1.2: Detailed explanation of principles applied to distributions."""
        
        explanation_prompt = self._build_detailed_explanation_prompt()
        
        # This is informational only - no structured response needed
        await Runner.run(participant, explanation_prompt, context=context)
        
        # No return value needed - this is just for learning
    
    async def _step_1_3_principle_application(
        self,
        participant: Agent,
        context: ParticipantContext,
        distribution_set,
        round_num: int,
        agent_config: AgentConfiguration
    ) -> ApplicationResult:
        """Step 1.3: Single round of principle application."""
        
        application_prompt = self._build_application_prompt(distribution_set, round_num)
        
        # Create agent with structured output type
        choice_agent = create_agent_with_output_type(agent_config, PrincipleChoiceResponse)
        
        result = await Runner.run(choice_agent, application_prompt, context=context)
        
        # Parse and validate choice
        try:
            parsed_choice = await self.utility_agent.parse_principle_choice(
                result.final_output.choice_explanation + " " + str(result.final_output.principle_choice.dict())
            )
        except Exception as e:
            # Fallback to structured response
            parsed_choice = result.final_output.principle_choice
        
        # Validate constraint specification
        max_retries = 2
        retry_count = 0
        
        while not await self.utility_agent.validate_constraint_specification(parsed_choice) and retry_count < max_retries:
            # Re-prompt for valid constraint
            retry_prompt = await self.utility_agent.re_prompt_for_constraint(
                participant.name, parsed_choice
            )
            
            retry_result = await Runner.run(choice_agent, retry_prompt, context=context)
            try:
                parsed_choice = await self.utility_agent.parse_principle_choice(
                    retry_result.final_output.choice_explanation + " " + str(retry_result.final_output.principle_choice.dict())
                )
            except Exception:
                parsed_choice = retry_result.final_output.principle_choice
            
            retry_count += 1
        
        # Apply principle to distributions
        chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
            distribution_set.distributions, parsed_choice
        )
        
        # Calculate payoff and income class assignment
        assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution)
        
        # Calculate alternative earnings
        alternative_earnings = DistributionGenerator.calculate_alternative_earnings(
            distribution_set.distributions
        )
        
        return ApplicationResult(
            round_number=round_num,
            principle_choice=parsed_choice,
            chosen_distribution=chosen_distribution,
            assigned_income_class=assigned_class,
            earnings=earnings,
            alternative_earnings=alternative_earnings
        )
    
    async def _step_1_4_final_ranking(
        self,
        participant: Agent,
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> PrincipleRanking:
        """Step 1.4: Final principle ranking after experience."""
        
        final_ranking_prompt = self._build_final_ranking_prompt()
        
        # Create agent with structured output type
        ranking_agent = create_agent_with_output_type(agent_config, PrincipleRankingResponse)
        
        result = await Runner.run(ranking_agent, final_ranking_prompt, context=context)
        
        # Parse and validate response
        try:
            parsed_ranking = await self.utility_agent.parse_principle_ranking(
                result.final_output.ranking_explanation + " " + str(result.final_output.principle_rankings.dict())
            )
            return parsed_ranking
        except Exception as e:
            # Fallback to structured response
            return result.final_output.principle_rankings
    
    def _build_ranking_prompt(self) -> str:
        """Build prompt for principle ranking."""
        return """
Please rank the four justice principles from best (1) to worst (4) based on your preference:

1. **Maximizing the floor income**: Choose the distribution that maximizes the lowest income
2. **Maximizing the average income**: Choose the distribution that maximizes the average income  
3. **Maximizing the average income with a floor constraint**: Maximize average while ensuring minimum income
4. **Maximizing the average income with a range constraint**: Maximize average while limiting income gap

For each principle, indicate your certainty level: very_unsure, unsure, no_opinion, sure, or very_sure.

Provide your ranking with clear reasoning for your preferences.
"""
    
    def _build_detailed_explanation_prompt(self) -> str:
        """Build prompt for detailed explanation of principles."""
        return """
Here is how each justice principle would be applied to example income distributions:

Example Distributions:
| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |
|--------------|---------|---------|---------|----------|
| High         | $32,000 | $28,000 | $31,000 | $21,000 |
| Medium high  | $27,000 | $22,000 | $24,000 | $20,000 |
| Medium       | $24,000 | $20,000 | $21,000 | $19,000 |
| Medium low   | $13,000 | $17,000 | $16,000 | $16,000 |
| Low          | $12,000 | $13,000 | $14,000 | $15,000 |

How each principle would choose:
- **Maximizing the floor**: Would choose Distribution 4 (highest low income: $15,000)
- **Maximizing average**: Would choose Distribution 1 (highest average: $21,600)
- **Maximizing average with floor constraint ≤ $13,000**: Would choose Distribution 1
- **Maximizing average with floor constraint ≤ $14,000**: Would choose Distribution 3  
- **Maximizing average with range constraint ≥ $20,000**: Would choose Distribution 1
- **Maximizing average with range constraint ≥ $15,000**: Would choose Distribution 2

Study these examples to understand how each principle works in practice.
"""
    
    def _build_application_prompt(self, distribution_set, round_num: int) -> str:
        """Build prompt for principle application."""
        distributions_table = DistributionGenerator.format_distributions_table(
            distribution_set.distributions
        )
        
        return f"""
ROUND {round_num}: Choose a Justice Principle

{distributions_table}

Choose ONE of the four justice principles to apply to these distributions:
(a) maximizing the floor
(b) maximizing the average  
(c) maximizing the average with a floor constraint
(d) maximizing the average with a range constraint

**IMPORTANT**: If you choose (c) or (d), you MUST specify the constraint amount in dollars.

Examples of valid choices:
- "I choose (a) maximizing the floor"
- "I choose (c) maximizing the average with a floor constraint of $15,000"
- "I choose (d) maximizing the average with a range constraint of $18,000"

Your chosen principle will determine which distribution is selected. You'll then be randomly assigned to an income class and earn $1 for every $10,000 of income.

What is your choice and reasoning?
"""
    
    def _build_final_ranking_prompt(self) -> str:
        """Build prompt for final ranking after experience."""
        return """
After experiencing four rounds of applying justice principles, please rank them again from best (1) to worst (4).

Reflect on:
- What you learned from applying these principles
- How your earnings were affected by your choices
- Whether your preferences have changed
- What you observed about the outcomes of different principles

Provide your updated ranking with certainty levels and explain how your experience influenced your preferences.
"""