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


class Phase1Manager:
    """Manages Phase 1 execution for all participants."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent, language_manager, error_handler=None, seed_manager=None):
        self.participants = participants
        self.utility_agent = utility_agent
        self.language_manager = language_manager
        self.error_handler = error_handler
        self.seed_manager = seed_manager
        self.logger = None  # Will be set in run_phase1
    
    async def run_phase1(self, config: ExperimentConfiguration, logger: AgentCentricLogger = None, process_logger=None) -> List[Phase1Results]:
        """Execute complete Phase 1 for all participants in parallel."""
        
        # Set logger instance for use in helper methods
        self.logger = logger
        
        
        tasks = []
        for i, participant in enumerate(self.participants):
            agent_config = config.agents[i]
            context = self._create_initial_participant_context(agent_config)
            task = asyncio.create_task(
                self._run_single_participant_phase1(participant, context, config, agent_config, logger, process_logger)
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
    
    def _log_info(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.info(message)
    
    def _log_warning(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.warning(message)
    
    
    async def _run_single_participant_phase1(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        config: ExperimentConfiguration,
        agent_config: AgentConfiguration,
        logger: AgentCentricLogger = None,
        process_logger=None
    ) -> Phase1Results:
        """Run complete Phase 1 for a single participant."""
        
        # 1.1 Initial Principle Ranking
        context.round_number = 0
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Initial ranking", 0.1)
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
        
        # Update memory with agent using new guidance style
        memory_guidance_style = config.memory_guidance_style if config else "narrative"
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, ranking_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.2 Detailed Explanation (informational only)
        context.round_number = -1  # Special round for learning
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Learning principles", 0.25)
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
        
        # Update memory with agent using new guidance style
        memory_guidance_style = config.memory_guidance_style if config else "narrative"
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, explanation_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.2b Post-explanation ranking
        context.round_number = 0  # Reset to 0 for second ranking
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Post-explanation ranking", 0.4)
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
        
        # Update memory with agent using new guidance style
        memory_guidance_style = config.memory_guidance_style if config else "narrative"
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, post_ranking_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.3 Repeated Application (4 rounds)
        application_results = []
        for round_num in range(1, 5):
            context.round_number = round_num
            
            if process_logger:
                progress = 0.4 + (round_num * 0.1)  # 0.5, 0.6, 0.7, 0.8
                process_logger.phase1_agent_progress(participant.name, f"Application round {round_num}", progress)
            
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
            
            # Update context with earnings FIRST so bank balance is correct during memory update
            context = update_participant_context(
                context,
                balance_change=result.earnings,
                new_round=round_num
            )
            
            # Update memory with agent using new guidance style (now with correct bank balance)
            from config import ExperimentConfiguration
            config_obj: ExperimentConfiguration = config
            memory_guidance_style = config_obj.memory_guidance_style if config_obj else "narrative"
            
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, round_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent
            )
        
        # 1.4 Final Ranking
        context.round_number = 5
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Final ranking", 0.9)
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
        
        # Update memory with agent using new guidance style
        memory_guidance_style = config.memory_guidance_style if config else "narrative"
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, final_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Completed", 1.0)
        
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
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {ranking_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.completed_initial_ranking')}"""
        
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
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {explanation_prompt}
{language_manager.get('memory_field_labels.your_response')} {result.final_output}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.learned_principle_applications')}"""
        
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
        print(f"DEBUG: Principle choice response to parse: {repr(text_response)}")
        parsed_choice = await self.utility_agent.parse_principle_choice_enhanced(text_response)
        
        # Validate constraint specification
        max_retries = 2
        retry_count = 0
        
        while not await self.utility_agent.validate_constraint_specification(parsed_choice) and retry_count < max_retries:
            # Log constraint re-prompting attempt
            self._log_info(f"Constraint validation failed for {participant.name} - attempt {retry_count + 1}/{max_retries + 1}")
            self._log_info(f"Principle: {parsed_choice.principle.value}, Constraint: {parsed_choice.constraint_amount}")
            
            # Re-prompt for valid constraint
            retry_prompt = await self.utility_agent.re_prompt_for_constraint(
                participant.name, parsed_choice
            )
            
            retry_result = await Runner.run(participant.agent, retry_prompt, context=context)
            retry_text = retry_result.final_output
            
            # Update memory with constraint re-prompt experience
            try:
                retry_memory_content = f"Constraint re-prompt: {retry_prompt}\nMy response: {retry_text}"
                updated_memory = await participant.update_memory(retry_memory_content, context.bank_balance)
                context.memory = updated_memory
                self._log_info(f"Updated {participant.name} memory after constraint retry {retry_count + 1}")
            except Exception as e:
                self._log_warning(f"Failed to update memory after constraint retry for {participant.name}: {e}")
            
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
        
        # Apply principle to distributions (UNWEIGHTED selection per spec)
        chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
            distribution_set.distributions,
            parsed_choice,
            None,
            language_manager=self.language_manager
        )
        
        # Calculate payoff and income class assignment
        assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution, probabilities, random_gen=self.seed_manager.random)
        
        # Calculate alternative earnings by principle (not just distribution)
        alternative_earnings_by_principle = DistributionGenerator.calculate_alternative_earnings_by_principle(
            distribution_set.distributions, 
            parsed_choice.constraint_amount if parsed_choice.constraint_amount else None,
            random_gen=self.seed_manager.random
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
        
        # Build comprehensive earnings display using LanguageManager
        comprehensive_data = DistributionGenerator.calculate_comprehensive_constraint_outcomes(
            distribution_set.distributions,
            assigned_class,
            self.language_manager,  # Pass LanguageManager to method
            None  # unweighted display to match selection spec
        )

        # Build complete earnings display using LanguageManager
        earnings_display_parts = []

        # Add distributions table (already formatted with LanguageManager)
        earnings_display_parts.append(comprehensive_data['distributions_table'])
        earnings_display_parts.append("")  # Empty line

        # Add principle outcomes header with localized class name and round number
        principle_outcomes_header = self.language_manager.get(
            'comprehensive_earnings.principle_outcomes_header',
            round_number=round_num,
            class_name=comprehensive_data['class_display_name']
        )
        earnings_display_parts.append(principle_outcomes_header)

        # Add all outcomes with proper choice marking
        for outcome in comprehensive_data['outcomes']:
            # Determine if this outcome matches the agent's choice
            choice_marker = ""
            if outcome['principle_key'] == parsed_choice.principle.value:
                if parsed_choice.constraint_amount is None or outcome['constraint_amount'] == parsed_choice.constraint_amount:
                    choice_marker = self.language_manager.get('comprehensive_earnings.markers.assigned_principle')
            
            # Format outcome line using LanguageManager
            outcome_line = self.language_manager.get(
                'comprehensive_earnings.outcome_line',
                principle_name=outcome['principle_name'],
                distribution=self.language_manager.get('distributions.distribution_label', number=outcome['distribution_index'] + 1),
                income=self.language_manager.get('constraint_formatting.currency_format', amount=outcome['agent_income']),
                earnings=self.language_manager.get('constraint_formatting.currency_format', amount=outcome['agent_earnings']),
                marker=choice_marker
            )
            earnings_display_parts.append(outcome_line)

        # Join all parts
        earnings_display = "\n".join(earnings_display_parts)
        
        # Check if original values mode was used
        original_values_mode = getattr(config, 'original_values_mode', None)
        is_original_values = original_values_mode and original_values_mode.enabled if original_values_mode else False
        original_situation = None
        if is_original_values:
            # Map round numbers to situations A, B, C, D
            situation_map = {1: "A", 2: "B", 3: "C", 4: "D"}
            original_situation = situation_map.get(round_num, "Unknown")
        
        # Create complete round content with full counterfactual information
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {application_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.chosen_principle')} {parsed_choice.principle.value}"""
        
        # Add constraint info if relevant
        if parsed_choice.constraint_amount is not None:
            round_content += f"\n{language_manager.get('memory_field_labels.constraint_amount')} {parsed_choice.constraint_amount}"
        
        # Add assigned class info
        round_content += f"\n{language_manager.get('memory_field_labels.assigned_class')} {language_manager.get(f'common.income_classes.{assigned_class.value}')}"
        
        # Add distribution context
        if is_original_values and original_situation:
            round_content += f"\n{language_manager.get('memory_field_labels.original_values_situation')} {original_situation}"
        else:
            round_content += f"\n{language_manager.get('memory_field_labels.distribution_multiplier')} {distribution_set.multiplier:.2f}"
        
        # Add explicit payoff line
        round_content += f"\n{language_manager.get('memory_field_labels.your_payoff')} {earnings:.2f}"
        
        # Add comprehensive earnings display
        round_content += f"\n\n{earnings_display}"
        
        round_content += f"\n{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.applied_principle_round', round_number=round_num)}"
        
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
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {post_explanation_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.completed_post_explanation_ranking')}"""
        
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
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {final_ranking_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.completed_final_ranking')}"""
        
        return parsed_ranking, round_content
    
    def _build_ranking_prompt(self) -> str:
        """Build prompt for principle ranking."""
        language_manager = self.language_manager
        return language_manager.get("prompts.phase1_initial_ranking_prompt")
    
    def _build_detailed_explanation_prompt(self, config: ExperimentConfiguration = None) -> str:
        """Build prompt for detailed explanation of principles."""
        language_manager = self.language_manager
        
        # If original values mode is enabled, use Sample situation distributions for explanation
        if config and config.original_values_mode and config.original_values_mode.enabled:
            sample_distribution_set = DistributionGenerator.get_sample_distribution()
            distributions_table = DistributionGenerator.format_distributions_table(
                sample_distribution_set.distributions, self.language_manager
            )
            
            # Build explanation with Sample distributions
            base_explanation = language_manager.get("prompts.phase1_detailed_principles_explanation")
            intro_text = language_manager.get("prompts.phase1_distributions_intro")
            return f"{base_explanation}\n\n{intro_text}\n\n{distributions_table}"
        else:
            return language_manager.get("prompts.phase1_detailed_principles_explanation")
    
    def _build_post_explanation_ranking_prompt(self) -> str:
        """Build prompt for post-explanation ranking."""
        language_manager = self.language_manager
        return language_manager.get("prompts.phase1_post_explanation_ranking_prompt")
    
    def _build_application_prompt(self, distribution_set, round_num: int) -> str:
        """Build prompt for principle application."""
        language_manager = self.language_manager
        distributions_table = DistributionGenerator.format_distributions_table(
            distribution_set.distributions, self.language_manager
        )
        
        return language_manager.get("prompts.phase1_application_round",
                                   round_number=round_num,
                                   distributions_table=distributions_table)
    
    def _build_final_ranking_prompt(self) -> str:
        """Build prompt for final ranking after experience."""
        language_manager = self.language_manager
        return language_manager.get("prompts.phase1_final_ranking_prompt")
