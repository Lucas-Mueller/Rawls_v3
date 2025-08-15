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
from experiment_agents import update_participant_context, UtilityAgent, ParticipantAgent
from core.distribution_generator import DistributionGenerator
from utils.memory_manager import MemoryManager
from utils.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from utils.language_manager import get_language_manager


class Phase1Manager:
    """Manages Phase 1 execution for all participants."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent):
        self.participants = participants
        self.utility_agent = utility_agent
    
    async def run_phase1(self, config: ExperimentConfiguration, logger: AgentCentricLogger = None) -> List[Phase1Results]:
        """Execute complete Phase 1 for all participants in parallel."""
        
        tasks = []
        for i, participant in enumerate(self.participants):
            agent_config = config.agents[i]
            context = self._create_initial_participant_context(agent_config)
            task = asyncio.create_task(
                self._run_single_participant_phase1(participant, context, config, agent_config, logger)
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    def _create_initial_participant_context(self, agent_config: AgentConfiguration) -> ParticipantContext:
        """Create initial context for a participant."""
        return ParticipantContext(
            name=agent_config.name,
            role_description=agent_config.personality,
            bank_balance=0.0,
            memory="",  # Start with empty memory - agent will manage their own memory
            round_number=0,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=agent_config.memory_character_limit
        )
    
    async def _run_single_participant_phase1(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        config: ExperimentConfiguration,
        agent_config: AgentConfiguration,
        logger: AgentCentricLogger = None
    ) -> Phase1Results:
        """Run complete Phase 1 for a single participant."""
        
        # 1.1 Initial Principle Ranking
        context.round_number = 0
        initial_ranking, ranking_content = await self._step_1_1_initial_ranking(participant, context, agent_config)
        
        # Log initial ranking with current memory state
        if logger:
            memory_before, balance_before = MemoryStateCapture.capture_pre_round_state(context.memory, context.bank_balance)
            logger.log_initial_ranking(
                participant.name,
                initial_ranking,
                memory_before,
                balance_before
            )
        
        # Update memory with agent
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, ranking_content
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.2 Detailed Explanation (informational only)
        context.round_number = -1  # Special round for learning
        explanation_content = await self._step_1_2_detailed_explanation(participant, context, agent_config, config)
        
        # Log detailed explanation
        if logger:
            memory_before, balance_before = MemoryStateCapture.capture_pre_round_state(context.memory, context.bank_balance)
            logger.log_detailed_explanation(
                participant.name,
                explanation_content,
                memory_before,
                balance_before
            )
        
        # Update memory with agent
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, explanation_content
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.2b Post-explanation ranking
        context.round_number = 0  # Reset to 0 for second ranking
        post_explanation_ranking, post_ranking_content = await self._step_1_2b_post_explanation_ranking(
            participant, context, agent_config
        )
        
        # Log post-explanation ranking
        if logger:
            memory_before, balance_before = MemoryStateCapture.capture_pre_round_state(context.memory, context.bank_balance)
            logger.log_post_explanation_ranking(
                participant.name,
                post_explanation_ranking,
                memory_before,
                balance_before
            )
        
        # Update memory with agent
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, post_ranking_content
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.3 Repeated Application (4 rounds)
        application_results = []
        for round_num in range(1, 5):
            context.round_number = round_num
            
            # Capture state before round
            balance_before = context.bank_balance
            memory_before = context.memory
            
            # Generate or retrieve distribution for this round
            if config.original_values_mode and config.original_values_mode.enabled:
                # Use predefined distributions from original values mode
                # Round 1 -> Situation A, Round 2 -> Situation B, etc.
                distribution_set = DistributionGenerator.get_original_values_distribution(round_num)
            else:
                # Generate dynamic distribution (existing behavior)
                distribution_set = DistributionGenerator.generate_dynamic_distribution(
                    config.distribution_range_phase1
                )
            
            result, round_content = await self._step_1_3_principle_application(
                participant, context, distribution_set, round_num, agent_config, config
            )
            application_results.append(result)
            
            # Log demonstration round
            if logger:
                alternative_payoffs = MemoryStateCapture.format_alternative_payoffs(result.alternative_earnings)
                logger.log_demonstration_round(
                    participant.name,
                    round_num,
                    result.principle_choice.principle.value,
                    result.assigned_income_class.value,
                    result.earnings,
                    alternative_payoffs,
                    memory_before,
                    balance_before,
                    balance_before + result.earnings
                )
            
            # Update memory with agent
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, round_content
            )
            
            # Update context with earnings
            context = update_participant_context(
                context,
                balance_change=result.earnings,
                new_round=round_num
            )
        
        # 1.4 Final Ranking
        context.round_number = 5
        final_ranking, final_content = await self._step_1_4_final_ranking(participant, context, agent_config)
        
        # Log final ranking
        if logger:
            memory_before, balance_before = MemoryStateCapture.capture_pre_round_state(context.memory, context.bank_balance)
            logger.log_final_ranking(
                participant.name,
                final_ranking,
                memory_before,
                balance_before
            )
        
        # Update memory with agent
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, final_content
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        return Phase1Results(
            participant_name=participant.name,
            initial_ranking=initial_ranking,
            post_explanation_ranking=post_explanation_ranking,
            application_results=application_results,
            final_ranking=final_ranking,
            total_earnings=context.bank_balance,
            final_memory_state=context.memory  # CRITICAL: Preserve memory for Phase 2
        )
    
    async def _step_1_1_initial_ranking(
        self, 
        participant: ParticipantAgent, 
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> tuple[PrincipleRanking, str]:
        """Step 1.1: Initial principle ranking with certainty."""
        
        ranking_prompt = self._build_ranking_prompt()
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, ranking_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)
        
        # Create round content for memory
        round_content = f"""Prompt: {ranking_prompt}
Your Response: {text_response}
Your Rankings: {parsed_ranking.dict() if hasattr(parsed_ranking, 'dict') else str(parsed_ranking)}
Outcome: Completed initial ranking of justice principles."""
        
        return parsed_ranking, round_content
    
    async def _step_1_2_detailed_explanation(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext, 
        agent_config: AgentConfiguration,
        config: ExperimentConfiguration
    ) -> str:
        """Step 1.2: Detailed explanation of principles applied to distributions."""
        
        explanation_prompt = self._build_detailed_explanation_prompt(config)
        
        # This is informational only - no structured response needed
        result = await Runner.run(participant.agent, explanation_prompt, context=context)
        
        # Create round content for memory
        round_content = f"""Prompt: {explanation_prompt}
Your Response: {result.final_output}
Outcome: Learned how each justice principle is applied to income distributions through examples."""
        
        return round_content
    
    async def _step_1_3_principle_application(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        distribution_set,
        round_num: int,
        agent_config: AgentConfiguration,
        config: ExperimentConfiguration
    ) -> tuple[ApplicationResult, str]:
        """Step 1.3: Single round of principle application."""
        
        application_prompt = self._build_application_prompt(distribution_set, round_num)
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, application_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        parsed_choice = await self.utility_agent.parse_principle_choice_enhanced(text_response)
        
        # Validate constraint specification
        max_retries = 2
        retry_count = 0
        
        while not await self.utility_agent.validate_constraint_specification(parsed_choice) and retry_count < max_retries:
            # Re-prompt for valid constraint
            retry_prompt = await self.utility_agent.re_prompt_for_constraint(
                participant.name, parsed_choice
            )
            
            retry_result = await Runner.run(participant.agent, retry_prompt, context=context)
            retry_text = retry_result.final_output
            
            # Parse retry response using enhanced parsing
            parsed_choice = await self.utility_agent.parse_principle_choice_enhanced(retry_text)
            
            retry_count += 1
        
        # Determine probabilities to use
        if config.original_values_mode and config.original_values_mode.enabled:
            # Use round-specific probabilities (Round 1->A, Round 2->B, etc.)
            probabilities = DistributionGenerator.get_original_values_probabilities(round_num)
        else:
            # Use global configuration probabilities
            probabilities = config.income_class_probabilities
        
        # Apply principle to distributions
        chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
            distribution_set.distributions, parsed_choice, probabilities
        )
        
        # Calculate payoff and income class assignment
        assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution, probabilities)
        
        # Calculate alternative earnings by principle (not just distribution)
        alternative_earnings_by_principle = DistributionGenerator.calculate_alternative_earnings_by_principle(
            distribution_set.distributions, 
            parsed_choice.constraint_amount if parsed_choice.constraint_amount else None
        )
        
        # CRITICAL: Calculate what participant would have earned under each principle with SAME class assignment
        alternative_earnings_same_class = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
            distribution_set.distributions,
            assigned_class,
            parsed_choice.constraint_amount if parsed_choice.constraint_amount else None
        )
        
        # Keep old alternative earnings for compatibility with data model
        alternative_earnings = DistributionGenerator.calculate_alternative_earnings(
            distribution_set.distributions
        )
        
        application_result = ApplicationResult(
            round_number=round_num,
            principle_choice=parsed_choice,
            chosen_distribution=chosen_distribution,
            assigned_income_class=assigned_class,
            earnings=earnings,
            alternative_earnings=alternative_earnings,
            alternative_earnings_same_class=alternative_earnings_same_class
        )
        
        # Format counterfactual analysis matching chit_example.png specification
        class_name_mapping = {
            "high": "HIGH",
            "medium_high": "MEDIUM HIGH", 
            "medium": "MEDIUM",
            "medium_low": "MEDIUM LOW",
            "low": "LOW"
        }
        
        # Get the income for the assigned class in the chosen distribution
        assigned_income = chosen_distribution.get_income_by_class(assigned_class)
        
        # Build the counterfactual table using language manager
        language_manager = get_language_manager()
        
        counterfactual_table = language_manager.get(
            "prompts.phase1_counterfactual_table_header",
            assigned_class=class_name_mapping[assigned_class.value]
        )
        
        # Get principle display names dictionary directly
        translations = language_manager.get_current_translations()
        principle_display_names = {
            "maximizing_floor": language_manager.get("common.principle_names.maximizing_floor"),
            "maximizing_average": language_manager.get("common.principle_names.maximizing_average"),
            "maximizing_average_floor_constraint": language_manager.get("common.principle_names.maximizing_average_floor_constraint"),
            "maximizing_average_range_constraint": language_manager.get("common.principle_names.maximizing_average_range_constraint")
        }
        
        for principle_key, alt_earnings in alternative_earnings_same_class.items():
            principle_label = principle_display_names.get(principle_key, principle_key)
            # Calculate income from earnings (reverse the payoff calculation)
            alt_income = int(alt_earnings * 10000)
            counterfactual_table += f"\n{principle_label:<40}  ${alt_income:,}    ${alt_earnings:.2f}"
        
        # Create round content for memory with properly formatted principle name
        chosen_principle_display = DistributionGenerator.format_principle_name_with_constraint(parsed_choice)
        
        round_content = language_manager.get(
            "prompts.phase1_round_memory_template",
            application_prompt=application_prompt,
            text_response=text_response,
            chosen_principle_display=chosen_principle_display,
            round_num=round_num,
            counterfactual_table=counterfactual_table,
            earnings=earnings,
            total_earnings=context.bank_balance + earnings
        )
        
        return application_result, round_content
    
    async def _step_1_2b_post_explanation_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> tuple[PrincipleRanking, str]:
        """Step 1.2b: Post-explanation principle ranking."""
        
        post_explanation_prompt = self._build_post_explanation_ranking_prompt()
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, post_explanation_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)
        
        # Create round content for memory
        round_content = f"""Prompt: {post_explanation_prompt}
Your Response: {text_response}
Your Post-Explanation Rankings: {parsed_ranking.dict() if hasattr(parsed_ranking, 'dict') else str(parsed_ranking)}
Outcome: Completed ranking after learning how principles apply to distributions."""
        
        return parsed_ranking, round_content
    
    async def _step_1_4_final_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> tuple[PrincipleRanking, str]:
        """Step 1.4: Final principle ranking after experience."""
        
        final_ranking_prompt = self._build_final_ranking_prompt()
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)
        
        # Create round content for memory
        round_content = f"""Prompt: {final_ranking_prompt}
Your Response: {text_response}
Your Final Rankings: {parsed_ranking.dict() if hasattr(parsed_ranking, 'dict') else str(parsed_ranking)}
Outcome: Completed final ranking of justice principles after experiencing all four rounds."""
        
        return parsed_ranking, round_content
    
    def _build_ranking_prompt(self) -> str:
        """Build prompt for principle ranking."""
        language_manager = get_language_manager()
        return language_manager.get("prompts.phase1_initial_ranking_prompt_template")
    
    def _build_detailed_explanation_prompt(self, config: ExperimentConfiguration = None) -> str:
        """Build prompt for detailed explanation of principles."""
        language_manager = get_language_manager()
        
        # If original values mode is enabled, use Sample situation distributions for explanation
        if config and config.original_values_mode and config.original_values_mode.enabled:
            sample_distribution_set = DistributionGenerator.get_sample_distribution()
            distributions_table = DistributionGenerator.format_distributions_table(
                sample_distribution_set.distributions
            )
            
            # Build explanation with Sample distributions
            base_explanation = language_manager.get("prompts.phase1_detailed_principles_explanation")
            return f"{base_explanation}\n\nHere are some example distributions to help you understand:\n\n{distributions_table}"
        else:
            return language_manager.get("prompts.phase1_detailed_principles_explanation")
    
    def _build_post_explanation_ranking_prompt(self) -> str:
        """Build prompt for post-explanation ranking."""
        language_manager = get_language_manager()
        return language_manager.get("prompts.phase1_post_explanation_ranking_prompt")
    
    def _build_application_prompt(self, distribution_set, round_num: int) -> str:
        """Build prompt for principle application."""
        distributions_table = DistributionGenerator.format_distributions_table(
            distribution_set.distributions
        )
        
        return f"""
ROUND {round_num}

{distributions_table}

You are to make a choice from among the four principles of justice which are mentioned above:
(a) maximizing the floor,
(b) maximizing the average,
(c) maximizing the average with a floor constraint, and
(d) maximizing the average with a range constraint.

If you choose (c) or (d), you will have to tell us what that floor or range constraint is before you can be said to have made a well-defined choice.

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

Provide your updated ranking with an overall certainty level for the entire ranking and explain how your experience influenced your preferences.
"""