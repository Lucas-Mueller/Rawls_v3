"""
Phase 1 manager for individual participant familiarization.
"""
import asyncio
import logging
from typing import List, Callable, Awaitable
from agents import Agent, Runner

from models import (
    ParticipantContext, Phase1Results, ApplicationResult, ExperimentPhase,
    PrincipleRanking, PrincipleRankingResponse, PrincipleChoiceResponse,
    IncomeClass, JusticePrinciple, PrincipleChoice, CertaintyLevel
)
from config import ExperimentConfiguration, AgentConfiguration
from experiment_agents import update_participant_context, UtilityAgent, ParticipantAgent
from core.distribution_generator import DistributionGenerator
from utils.memory_manager import MemoryManager
from utils.logging.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from utils.seed_manager import SeedManager
from utils.parsing_errors import ParsingError, detect_parsing_failure_type, create_parsing_error

logger = logging.getLogger(__name__)


class Phase1Manager:
    """Manages Phase 1 execution for all participants."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent, language_manager, error_handler=None, seed_manager=None):
        self.participants = participants
        self.utility_agent = utility_agent
        self.language_manager = language_manager
        self.error_handler = error_handler
        self.seed_manager = seed_manager or SeedManager()
        self.logger = None  # Will be set in run_phase1
    
    async def run_phase1(self, config: ExperimentConfiguration, logger: AgentCentricLogger = None, process_logger=None) -> List[Phase1Results]:
        """Execute complete Phase 1 for all participants in parallel."""

        # Set logger instance for use in helper methods
        self.logger = logger

        # Log language information for test validation
        if process_logger and self.language_manager:
            language_name = self.language_manager.current_language.value
            process_logger.log_technical(f"Phase 1 executing with language: {language_name}")

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

    async def _execute_ranking_with_retry(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        prompt: str,
        config: ExperimentConfiguration,
        task_name: str
    ) -> tuple[PrincipleRanking, str]:
        """
        Execute ranking with intelligent retry logic.

        This method handles the core retry logic for ranking tasks, using the
        UtilityAgent's enhanced parsing with feedback and optionally updating
        participant memory with retry experiences.

        Args:
            participant: The participant agent
            context: Current participant context
            prompt: The ranking prompt
            config: Experiment configuration
            task_name: Name of the ranking task for logging

        Returns:
            Tuple of (parsed_ranking, round_content_for_memory)
        """
        # Always get initial response from participant
        result = await Runner.run(participant.agent, prompt, context=context)
        text_response = result.final_output

        # Check if intelligent retries are enabled
        if config.enable_intelligent_retries:
            # Create retry callback that handles participant re-prompting
            async def retry_callback(feedback: str) -> str:
                try:
                    logger.info(f"Intelligent retry callback triggered for {participant.name} in {task_name}")

                    # Build retry prompt with original prompt + feedback + guidance
                    retry_prompt = self._build_retry_prompt(prompt, feedback, config.retry_feedback_detail)

                    # Get participant's retry response
                    retry_result = await Runner.run(participant.agent, retry_prompt, context=context)
                    retry_response = retry_result.final_output

                    # Update participant memory with retry experience if enabled
                    if config.memory_update_on_retry:
                        await self._update_memory_with_retry_experience(
                            participant, context, feedback, retry_response, config
                        )

                    logger.info(f"Retry callback successful for {participant.name}, response length: {len(retry_response)}")
                    return retry_response

                except Exception as e:
                    logger.error(f"Retry callback failed for {participant.name} in {task_name}: {e}")
                    # Return empty string to signal failure to utility agent
                    return ""

            # Use enhanced parsing with feedback capability
            parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced_with_feedback(
                text_response,
                max_retries=config.max_participant_retries + 1,  # +1 for initial attempt
                participant_retry_callback=retry_callback
            )
        else:
            # Fall back to existing enhanced parsing without retries
            try:
                parsed_ranking = await self.utility_agent.parse_principle_ranking_enhanced(text_response)
            except Exception as e:
                # Log parsing failure and re-raise with context
                self._log_warning(f"Failed to parse ranking for {participant.name} in {task_name}: {e}")
                # Create classified parsing error for better error handling
                parsing_error = create_parsing_error(
                    response=text_response,
                    parsing_operation=task_name,
                    expected_format="ranking",
                    additional_context={
                        "participant_name": participant.name,
                        "task_name": task_name,
                        "retry_enabled": config.enable_intelligent_retries
                    },
                    cause=e
                )
                raise parsing_error

        # Create round content for memory
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.outcome')} {self._get_completion_message_for_task(task_name)}"""

        return parsed_ranking, round_content

    def _build_retry_prompt(self, original_prompt: str, feedback: str, detail_level: str) -> str:
        """Build retry prompt with feedback and guidance."""
        language_manager = self.language_manager

        # Base retry prompt structure
        retry_intro = language_manager.get('retry_prompts.retry_needed_intro') if hasattr(language_manager, 'retry_prompts') else "Let me try to provide a better response."

        # Add detail based on configuration
        if detail_level == "detailed":
            retry_prompt = f"""{retry_intro}

{language_manager.get('retry_prompts.feedback_header') if hasattr(language_manager, 'retry_prompts') else 'Feedback on previous response:'} {feedback}

{language_manager.get('retry_prompts.original_request') if hasattr(language_manager, 'retry_prompts') else 'Please respond to the original request:'} {original_prompt}"""
        else:
            # Concise version
            retry_prompt = f"""{retry_intro}

{feedback}

{original_prompt}"""

        return retry_prompt

    async def _update_memory_with_retry_experience(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        feedback: str,
        retry_response: str,
        config: ExperimentConfiguration
    ) -> None:
        """Update participant memory with retry experience."""
        try:
            language_manager = self.language_manager
            retry_memory_content = f"""{language_manager.get('memory_field_labels.retry_feedback') if hasattr(language_manager, 'retry_prompts') else 'Retry feedback:'} {feedback}
{language_manager.get('memory_field_labels.your_response') if hasattr(language_manager, 'retry_prompts') else 'My retry response:'} {retry_response}"""

            # Use existing memory guidance style from config
            memory_guidance_style = config.memory_guidance_style if config else "narrative"
            updated_memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, retry_memory_content,
                memory_guidance_style=memory_guidance_style,
                language_manager=self.language_manager,
                error_handler=self.error_handler,
                utility_agent=self.utility_agent,
                round_number=context.round_number,
                phase="phase_1"
            )
            context.memory = updated_memory
            self._log_info(f"Updated {participant.name} memory with retry experience")
        except Exception as e:
            self._log_warning(f"Failed to update memory with retry experience for {participant.name}: {e}")

    def _get_completion_message_for_task(self, task_name: str) -> str:
        """Get appropriate completion message for a ranking task."""
        language_manager = self.language_manager

        # Map task names to appropriate completion messages
        task_messages = {
            "initial_ranking": language_manager.get('memory_outcomes.completed_initial_ranking') if hasattr(language_manager, 'memory_outcomes') else "Completed initial ranking",
            "post_explanation_ranking": language_manager.get('memory_outcomes.completed_post_explanation_ranking') if hasattr(language_manager, 'memory_outcomes') else "Completed post-explanation ranking",
            "final_ranking": language_manager.get('memory_outcomes.completed_final_ranking') if hasattr(language_manager, 'memory_outcomes') else "Completed final ranking"
        }

        return task_messages.get(task_name, f"Completed {task_name}")

    
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
        initial_ranking, ranking_content = await self._step_1_1_initial_ranking(participant, context, agent_config, config)
        
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
            participant, context, ranking_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent,
            round_number=context.round_number,
            phase="phase_1"
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
            participant, context, explanation_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent,
            round_number=context.round_number,
            phase="phase_1"
        )
        context = update_participant_context(context, new_round=context.round_number)
        
        # 1.2b Post-explanation ranking
        context.round_number = 0  # Reset to 0 for second ranking
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Post-explanation ranking", 0.4)
        post_explanation_ranking, post_ranking_content = await self._step_1_2b_post_explanation_ranking(
            participant, context, agent_config, config
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
            participant, context, post_ranking_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent,
            round_number=context.round_number,
            phase="phase_1"
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
                participant, context, round_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent,
                round_number=context.round_number,
                phase="phase_1"
            )
        
        # 1.4 Final Ranking
        context.round_number = 5
        if process_logger:
            process_logger.phase1_agent_progress(participant.name, "Final ranking", 0.9)
        final_ranking, final_content = await self._step_1_4_final_ranking(participant, context, agent_config, config)
        
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
            participant, context, final_content, memory_guidance_style=memory_guidance_style, language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent,
            round_number=context.round_number,
            phase="phase_1"
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
        agent_config: AgentConfiguration,
        config: ExperimentConfiguration
    ) -> tuple[PrincipleRanking, str]:
        """Step 1.1: Initial principle ranking with certainty."""

        ranking_prompt = self._build_ranking_prompt()

        # Use intelligent retry helper - handles both retry and non-retry paths
        return await self._execute_ranking_with_retry(
            participant, context, ranking_prompt, config, "initial_ranking"
        )
    
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
        
        application_prompt = self._build_application_prompt(distribution_set, round_num, config)
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, application_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        print(f"DEBUG: Principle choice response to parse: {repr(text_response)}")

        if config.enable_intelligent_retries:
            # Create retry callback that handles participant re-prompting (exact A1 pattern)
            async def retry_callback(feedback: str) -> str:
                try:
                    logger.info(f"Intelligent retry callback triggered for {participant.name} in principle choice")

                    # Build retry prompt with original prompt + feedback + guidance
                    retry_prompt = self._build_retry_prompt(application_prompt, feedback, config.retry_feedback_detail)

                    # Get participant's retry response
                    retry_result = await Runner.run(participant.agent, retry_prompt, context=context)
                    retry_response = retry_result.final_output

                    # Update participant memory with retry experience if enabled
                    if config.memory_update_on_retry:
                        await self._update_memory_with_retry_experience(
                            participant, context, feedback, retry_response, config
                        )

                    logger.info(f"Retry callback successful for {participant.name}, response length: {len(retry_response)}")
                    return retry_response

                except Exception as e:
                    logger.error(f"Retry callback failed for {participant.name} in principle choice: {e}")
                    # Return empty string to signal failure to utility agent
                    return ""

            # Use enhanced parsing with feedback capability (same as A1)
            parsed_choice = await self.utility_agent.parse_principle_choice_enhanced_with_feedback(
                text_response,
                max_retries=config.max_participant_retries + 1,  # +1 for initial attempt
                participant_retry_callback=retry_callback
            )
        else:
            # Fall back to existing parsing without retries
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
                updated_memory = await participant.update_memory(
                    retry_memory_content, 
                    context.bank_balance,
                    phase=context.phase,
                    round_number=context.round_number,
                    role_description=context.role_description
                )
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
        
        # Apply principle to distributions (weighted averages allowed by config)
        chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
            distribution_set.distributions, 
            parsed_choice, 
            probabilities,
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
            probabilities
        )

        # Build complete earnings display using LanguageManager (avoid duplicating the table)
        earnings_display_parts = []

        # SURGICAL ADDITION: Build summary section BEFORE comprehensive display
        summary_parts = []

        # Find agent's choice in outcomes
        agent_outcome = None
        for outcome in comprehensive_data['outcomes']:
            if (outcome['principle_key'] == parsed_choice.principle.value and
                outcome.get('constraint_amount') == parsed_choice.constraint_amount):
                agent_outcome = outcome
                break

        if agent_outcome:
            # Choice summary header
            summary_parts.append(self.language_manager.get('comprehensive_earnings.choice_summary_header'))

            # Choice summary line
            constraint_display = f" (${parsed_choice.constraint_amount:,})" if parsed_choice.constraint_amount else ""
            choice_summary = self.language_manager.get(
                'comprehensive_earnings.choice_summary_line',
                principle_name=agent_outcome['principle_name'],
                constraint_display=constraint_display
            )
            summary_parts.append(choice_summary)

            # Outcome line
            choice_outcome = self.language_manager.get(
                'comprehensive_earnings.choice_outcome_line',
                distribution=self.language_manager.get('distributions.distribution_label',
                                                     number=agent_outcome['distribution_index'] + 1),
                class_name=comprehensive_data['class_display_name'],
                income=self.language_manager.get('constraint_formatting.currency_format',
                                               amount=agent_outcome['agent_income']),
                earnings=self.language_manager.get('constraint_formatting.currency_format',
                                                 amount=agent_outcome['agent_earnings'])
            )
            summary_parts.append(choice_outcome)

            # Add empty line separator
            summary_parts.append("")

        # Prepend summary to earnings_display_parts (BEFORE existing comprehensive display)
        earnings_display_parts.extend(summary_parts)

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
        
        # Add comprehensive earnings display with conditional header
        if earnings_display:
            payoff_header = language_manager.get('memory_field_labels.payoff_notification_header')
            round_content += f"\n\n{payoff_header}\n{earnings_display}"
        
        round_content += f"\n{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.applied_principle_round', round_number=round_num)}"
        
        return application_result, round_content
    
    async def _step_1_2b_post_explanation_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration,
        config: ExperimentConfiguration
    ) -> tuple[PrincipleRanking, str]:
        """Step 1.2b: Post-explanation principle ranking."""

        post_explanation_prompt = self._build_post_explanation_ranking_prompt()

        # Use intelligent retry helper - handles both retry and non-retry paths
        return await self._execute_ranking_with_retry(
            participant, context, post_explanation_prompt, config, "post_explanation_ranking"
        )
    
    async def _step_1_4_final_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration,
        config: ExperimentConfiguration
    ) -> tuple[PrincipleRanking, str]:
        """Step 1.4: Final principle ranking after experience."""

        final_ranking_prompt = self._build_final_ranking_prompt()

        # Use intelligent retry helper - handles both retry and non-retry paths
        return await self._execute_ranking_with_retry(
            participant, context, final_ranking_prompt, config, "final_ranking"
        )
    
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
            
            # Build dynamic, weighted example mapping for English using config probabilities
            # Fallback to original static explanation for non-English to avoid i18n drift
            language = getattr(config, 'language', 'English').lower()
            if language == 'english':
                try:
                    probs = getattr(config, 'income_class_probabilities', None)
                    dists = sample_distribution_set.distributions

                    # Principle display names
                    name_floor = language_manager.get('common.principle_names.maximizing_floor')
                    name_avg = language_manager.get('common.principle_names.maximizing_average')
                    name_floor_c = language_manager.get('common.principle_names.maximizing_average_floor_constraint')
                    name_range_c = language_manager.get('common.principle_names.maximizing_average_range_constraint')

                    # Helper to choose distribution index (1-based)
                    def choose(principle: JusticePrinciple, constraint: int | None = None) -> tuple[int, int, float]:
                        pc = PrincipleChoice(principle=principle, constraint_amount=constraint, certainty=CertaintyLevel.SURE)
                        best, _ = DistributionGenerator.apply_principle_to_distributions(dists, pc, probs, language_manager=None)
                        idx = dists.index(best) + 1
                        return idx, best.low, best.get_average_income(probs)

                    # Compute choices
                    idx_floor, floor_low, _ = choose(JusticePrinciple.MAXIMIZING_FLOOR)
                    idx_avg, _, avg_val = choose(JusticePrinciple.MAXIMIZING_AVERAGE)
                    idx_fc_13k, _, avg_fc_13k = choose(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 13000)
                    idx_fc_14k, _, avg_fc_14k = choose(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 14000)
                    # Use typical illustrative range constraints based on sample ranges
                    idx_rc_20k, _, avg_rc_20k = choose(JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 20000)
                    idx_rc_15k, _, avg_rc_15k = choose(JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 15000)

                    # Format probabilities block (localized)
                    if probs:
                        high_n = language_manager.get('common.income_classes.high')
                        mh_n = language_manager.get('common.income_classes.medium_high')
                        m_n = language_manager.get('common.income_classes.medium')
                        ml_n = language_manager.get('common.income_classes.medium_low')
                        low_n = language_manager.get('common.income_classes.low')
                        if language == 'english':
                            prob_header = "The probabilities for each class are as follows"
                            prob_disclaimer = "Note: These probabilities are for this example only and may be different in subsequent rounds. They can vary significantly."
                        elif language == 'spanish':
                            prob_header = "Las probabilidades para cada clase son las siguientes"
                            prob_disclaimer = "Nota: Estas probabilidades son solo para este ejemplo y pueden ser diferentes en rondas posteriores. Pueden variar significativamente."
                        else:
                            prob_header = "各收入类别的概率如下"
                            prob_disclaimer = "注意：这些概率仅适用于此示例，在后续轮次中可能会有所不同。它们可能会显著变化。"
                        prob_lines = [
                            prob_header,
                            f"{high_n}: {probs.high*100:.0f}%",
                            f"{mh_n}: {probs.medium_high*100:.0f}%",
                            f"{m_n}: {probs.medium*100:.0f}%",
                            f"{ml_n}: {probs.medium_low*100:.0f}%",
                            f"{low_n}: {probs.low*100:.0f}%",
                            "",
                            prob_disclaimer,
                            ""
                        ]
                    else:
                        prob_lines = []

                    # Build mapping lines (use localized distribution label)
                    def dist_label(i: int) -> str:
                        return language_manager.get('distributions.distribution_label', number=i)

                    if language == 'english':
                        mapping_lines = [
                            "How each principle would choose:",
                            f"- **{name_floor}**: Would choose {dist_label(idx_floor)} (highest low income)",
                            f"- **{name_avg}**: Would choose {dist_label(idx_avg)} (highest weighted average)",
                            f"- **{name_floor_c} ≤ $13,000**: Would choose {dist_label(idx_fc_13k)} (highest weighted average among eligible)",
                            f"- **{name_floor_c} ≤ $14,000**: Would choose {dist_label(idx_fc_14k)} (highest weighted average among eligible)",
                            f"- **{name_range_c} ≤ $20,000**: Would choose {dist_label(idx_rc_20k)} (highest weighted average among eligible)",
                            f"- **{name_range_c} ≤ $15,000**: Would choose {dist_label(idx_rc_15k)} (highest weighted average among eligible)"
                        ]
                        header = "Here is how each justice principle would be applied to example income distributions:"
                    elif language == 'spanish':
                        mapping_lines = [
                            "Cómo elegiría cada principio:",
                            f"- **{name_floor}**: Elegiría {dist_label(idx_floor)} (ingreso bajo más alto)",
                            f"- **{name_avg}**: Elegiría {dist_label(idx_avg)} (promedio ponderado más alto)",
                            f"- **{name_floor_c} ≤ $13,000**: Elegiría {dist_label(idx_fc_13k)} (promedio ponderado más alto entre las elegibles)",
                            f"- **{name_floor_c} ≤ $14,000**: Elegiría {dist_label(idx_fc_14k)} (promedio ponderado más alto entre las elegibles)",
                            f"- **{name_range_c} ≤ $20,000**: Elegiría {dist_label(idx_rc_20k)} (promedio ponderado más alto entre las elegibles)",
                            f"- **{name_range_c} ≤ $15,000**: Elegiría {dist_label(idx_rc_15k)} (promedio ponderado más alto entre las elegibles)"
                        ]
                        header = "Así es como se aplicaría cada principio de justicia a distribuciones de ingresos de ejemplo:"
                    else:
                        mapping_lines = [
                            "每个原则如何选择：",
                            f"- **{name_floor}**：将选择{dist_label(idx_floor)}（最高低收入）",
                            f"- **{name_avg}**：将选择{dist_label(idx_avg)}（最高加权平均值）",
                            f"- **{name_floor_c} ≤ $13,000**：将选择{dist_label(idx_fc_13k)}（在符合条件的分配中加权平均值最高）",
                            f"- **{name_floor_c} ≤ $14,000**：将选择{dist_label(idx_fc_14k)}（在符合条件的分配中加权平均值最高）",
                            f"- **{name_range_c} ≤ $20,000**：将选择{dist_label(idx_rc_20k)}（在符合条件的分配中加权平均值最高）",
                            f"- **{name_range_c} ≤ $15,000**：将选择{dist_label(idx_rc_15k)}（在符合条件的分配中加权平均值最高)"
                        ]
                        header = "以下是每个公正原则如何应用于收入分配的例子："
                    body = "\n".join([header, "", distributions_table, "", *prob_lines, *mapping_lines])
                    return body
                except Exception:
                    # Fallback to original static explanation on any error
                    pass

            # Build explanation with static template (non-English or fallback)
            base_explanation = language_manager.get("prompts.phase1_detailed_principles_explanation")
            intro_text = language_manager.get("prompts.phase1_distributions_intro")
            return f"{base_explanation}\n\n{intro_text}\n\n{distributions_table}"
        else:
            return language_manager.get("prompts.phase1_detailed_principles_explanation")
    
    def _build_post_explanation_ranking_prompt(self) -> str:
        """Build prompt for post-explanation ranking."""
        language_manager = self.language_manager
        return language_manager.get("prompts.phase1_post_explanation_ranking_prompt")
    
    def _build_application_prompt(self, distribution_set, round_num: int, config: ExperimentConfiguration) -> str:
        """Build prompt for principle application with averages row (weighted if available)."""
        language_manager = self.language_manager
        # Determine probabilities for this round for average calculation row
        if config.original_values_mode and config.original_values_mode.enabled:
            probs = DistributionGenerator.get_original_values_probabilities(round_num)
        else:
            probs = config.income_class_probabilities
        distributions_table = DistributionGenerator.format_distributions_table(
            distribution_set.distributions, self.language_manager, probs
        )
        
        return language_manager.get(
            "prompts.phase1_application_round",
            round_number=round_num,
            distributions_table=distributions_table
        )
    
    def _build_final_ranking_prompt(self) -> str:
        """Build prompt for final ranking after experience."""
        language_manager = self.language_manager
        return language_manager.get("prompts.phase1_final_ranking_prompt")
