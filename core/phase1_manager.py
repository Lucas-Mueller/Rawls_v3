"""
Phase 1 manager for individual participant familiarization.
"""
import asyncio
import logging
import random
from typing import Dict, List, Callable, Awaitable, Any, Optional
from agents import Agent, Runner

from models import (
    ParticipantContext, Phase1Results, ApplicationResult, ExperimentPhase, ExperimentStage,
    PrincipleRanking, PrincipleRankingResponse, PrincipleChoiceResponse,
    IncomeClass, JusticePrinciple, PrincipleChoice, CertaintyLevel
)
from config import ExperimentConfiguration, AgentConfiguration
from experiment_agents import update_participant_context, UtilityAgent, ParticipantAgent
from core.distribution_generator import DistributionGenerator
from utils.logging.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from utils.seed_manager import SeedManager
from utils.parsing_errors import ParsingError, detect_parsing_failure_type, create_parsing_error
from utils.selective_memory_manager import MemoryEventType

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
        self._participant_rngs: Dict[str, random.Random] = {}
        self.memory_service = None
        self._memory_service_initialized = False
    
    async def run_phase1(self, config: ExperimentConfiguration, logger: AgentCentricLogger = None, process_logger=None) -> List[Phase1Results]:
        """Execute complete Phase 1 for all participants in parallel."""

        # Set logger instance for use in helper methods
        self.logger = logger

        # Ensure each participant has a deterministic RNG derived from the experiment seed
        self._build_participant_rngs(config)

        # Initialize consolidated memory service so Phase 1 uses the same pipeline as Phase 2
        self._ensure_memory_service(config)

        # Log language information for test validation
        if process_logger and self.language_manager:
            language_name = self.language_manager.current_language.value
            process_logger.log_technical(f"Phase 1 executing with language: {language_name}")

        tasks = []
        for i, participant in enumerate(self.participants):
            agent_config = config.agents[i]
            context = self._create_initial_participant_context(agent_config)
            participant_rng = self._participant_rngs.get(agent_config.name)
            if participant_rng is None:
                raise ValueError(f"Missing RNG for participant {agent_config.name}. Ensure _build_participant_rngs is called before scheduling tasks.")
            task = asyncio.create_task(
                self._run_single_participant_phase1(
                    participant,
                    context,
                    config,
                    agent_config,
                    participant_rng,
                    logger,
                    process_logger
                )
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
            memory_character_limit=agent_config.memory_character_limit,
            stage=None
        )
    
    def _log_info(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.info(message)

    def _log_warning(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.warning(message)

    # MemoryService-compatible logger interface
    def info(self, message: str) -> None:
        self._log_info(message)

    def warning(self, message: str) -> None:
        self._log_warning(message)

    def debug(self, message: str) -> None:
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.debug(message)

    def _build_phase1_metadata(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        task: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create consistent metadata for Phase 1 memory updates."""
        stage_value = context.stage.value if context.stage is not None else None
        metadata: Dict[str, Any] = {
            'phase': 'Phase 1',
            'participant_name': participant.name,
            'round_number': context.round_number,
            'stage': stage_value,
            'task': task
        }

        if extra:
            metadata.update({k: v for k, v in extra.items() if v is not None})

        return metadata

    def _ensure_memory_service(self, config: ExperimentConfiguration) -> None:
        """Initialize MemoryService once Phase 1 configuration is available."""
        if self._memory_service_initialized and self.memory_service is not None:
            return

        from core.services import MemoryService
        from config.phase2_settings import Phase2Settings

        settings = getattr(config, 'phase2_settings', None)
        if settings is None:
            settings = Phase2Settings.get_default()

        self.memory_service = MemoryService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=settings,
            logger=self,
            config=config
        )

        self._memory_service_initialized = True

    def _build_participant_rngs(self, config: ExperimentConfiguration) -> None:
        """Create a deterministic RNG for each participant derived from the experiment seed."""
        if self._participant_rngs:
            return

        base_seed = self.seed_manager.current_seed
        if base_seed is None:
            base_seed = config.get_effective_seed()

        rngs: Dict[str, random.Random] = {}
        for index, agent_cfg in enumerate(config.agents):
            derived_seed = (base_seed + index + 1) % (2**31)
            rngs[agent_cfg.name] = random.Random(derived_seed)

        self._participant_rngs = rngs

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

            self._ensure_memory_service(config)
            metadata = self._build_phase1_metadata(
                participant,
                context,
                task="retry_feedback",
                extra={
                    'retry_type': 'intelligent_retry',
                    'has_feedback': bool(feedback)
                }
            )

            context.memory = await self.memory_service.update_memory_selective(
                agent=participant,
                context=context,
                content=retry_memory_content,
                event_type=MemoryEventType.PHASE1_RETRY,
                event_metadata=metadata,
                config=config,
                error_handler=self.error_handler
            )
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
        participant_rng: random.Random,
        logger: AgentCentricLogger = None,
        process_logger=None
    ) -> Phase1Results:
        """Run complete Phase 1 for a single participant."""

        self._ensure_memory_service(config)
        
        # 1.1 Initial Principle Ranking
        context.round_number = 0
        context.stage = ExperimentStage.INITIAL_RANKING
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
        
        ranking_metadata = self._build_phase1_metadata(
            participant,
            context,
            task="initial_ranking"
        )
        context.memory = await self.memory_service.update_memory_selective(
            agent=participant,
            context=context,
            content=ranking_content,
            event_type=MemoryEventType.PHASE1_RANKING,
            event_metadata=ranking_metadata,
            config=config,
            error_handler=self.error_handler
        )
        context = update_participant_context(context, new_round=context.round_number, new_stage=context.stage)
        
        # 1.2 Detailed Explanation (informational only)
        context.round_number = -1  # Special round for learning
        context.stage = ExperimentStage.PRINCIPLE_EXPLANATION
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
        
        explanation_metadata = self._build_phase1_metadata(
            participant,
            context,
            task="detailed_explanation"
        )
        context.memory = await self.memory_service.update_memory_selective(
            agent=participant,
            context=context,
            content=explanation_content,
            event_type=MemoryEventType.PHASE1_EXPLANATION,
            event_metadata=explanation_metadata,
            config=config,
            error_handler=self.error_handler
        )
        context = update_participant_context(context, new_round=context.round_number, new_stage=context.stage)
        
        # 1.2b Post-explanation ranking
        context.round_number = 0  # Reset to 0 for second ranking
        context.stage = ExperimentStage.POST_EXPLANATION_RANKING
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
        
        post_ranking_metadata = self._build_phase1_metadata(
            participant,
            context,
            task="post_explanation_ranking"
        )
        context.memory = await self.memory_service.update_memory_selective(
            agent=participant,
            context=context,
            content=post_ranking_content,
            event_type=MemoryEventType.PHASE1_RANKING,
            event_metadata=post_ranking_metadata,
            config=config,
            error_handler=self.error_handler
        )
        context = update_participant_context(context, new_round=context.round_number, new_stage=context.stage)
        
        # 1.3 Repeated Application (4 rounds)
        application_results = []
        for round_num in range(1, 5):
            context.round_number = round_num
            context.stage = ExperimentStage.APPLICATION
            
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
                    config.distribution_range_phase1,
                    random_gen=participant_rng
                )
            
            result, round_content = await self._step_1_3_principle_application(
                participant,
                context,
                distribution_set,
                round_num,
                agent_config,
                config,
                participant_rng
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
                new_round=round_num,
                new_stage=context.stage
            )
            
            application_metadata = self._build_phase1_metadata(
                participant,
                context,
                task="principle_application",
                extra={
                    'application_round': round_num,
                    'principle': result.principle_choice.principle.value,
                    'constraint': result.principle_choice.constraint_amount,
                    'assigned_class': result.assigned_income_class.value,
                    'earnings': result.earnings
                }
            )

            context.memory = await self.memory_service.update_memory_selective(
                agent=participant,
                context=context,
                content=round_content,
                event_type=MemoryEventType.PRINCIPLE_APPLICATION,
                event_metadata=application_metadata,
                config=config,
                error_handler=self.error_handler
            )
        
        # 1.4 Final Ranking
        context.round_number = 5
        context.stage = ExperimentStage.FINAL_RANKING
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
        
        final_ranking_metadata = self._build_phase1_metadata(
            participant,
            context,
            task="final_ranking"
        )
        context.memory = await self.memory_service.update_memory_selective(
            agent=participant,
            context=context,
            content=final_content,
            event_type=MemoryEventType.PHASE1_RANKING,
            event_metadata=final_ranking_metadata,
            config=config,
            error_handler=self.error_handler
        )
        context = update_participant_context(context, new_round=context.round_number, new_stage=context.stage)
        
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
        config: ExperimentConfiguration,
        participant_rng: random.Random
    ) -> tuple[ApplicationResult, str]:
        """Step 1.3: Single round of principle application."""

        self._ensure_memory_service(config)
        
        application_prompt = self._build_application_prompt(distribution_set, round_num, config)
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, application_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic

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
                metadata = self._build_phase1_metadata(
                    participant,
                    context,
                    task="constraint_retry",
                    extra={'retry_index': retry_count + 1}
                )
                context.memory = await self.memory_service.update_memory_selective(
                    agent=participant,
                    context=context,
                    content=retry_memory_content,
                    event_type=MemoryEventType.PHASE1_RETRY,
                    event_metadata=metadata,
                    config=config,
                    error_handler=self.error_handler
                )
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
        assigned_class, earnings = DistributionGenerator.calculate_payoff(
            chosen_distribution,
            probabilities,
            random_gen=participant_rng
        )
        
        # Calculate alternative earnings by principle (not just distribution)
        alternative_earnings_by_principle = DistributionGenerator.calculate_alternative_earnings_by_principle(
            distribution_set.distributions,
            parsed_choice.constraint_amount if parsed_choice.constraint_amount else None,
            random_gen=participant_rng
        )
        
        # CRITICAL: Calculate what participant would have earned under each principle with SAME class assignment
        alternative_earnings_same_class = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
            distribution_set.distributions,
            assigned_class,
            parsed_choice.constraint_amount if parsed_choice.constraint_amount else None
        )
        
        # Keep old alternative earnings for compatibility with data model
        alternative_earnings = DistributionGenerator.calculate_alternative_earnings(
            distribution_set.distributions,
            random_gen=participant_rng
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

        # Build simplified earnings display with basic info followed by outcomes
        earnings_display_parts = []

        # Check if original values mode was used for situation/multiplier line
        original_values_mode = getattr(config, 'original_values_mode', None)
        is_original_values = original_values_mode and original_values_mode.enabled if original_values_mode else False
        original_situation = None
        if is_original_values:
            # Map round numbers to situations A, B, C, D
            situation_map = {1: "A", 2: "B", 3: "C", 4: "D"}
            original_situation = situation_map.get(round_num, "Unknown")

        # Get localized principle name
        agent_outcome = None
        for outcome in comprehensive_data['outcomes']:
            if (outcome['principle_key'] == parsed_choice.principle.value and
                outcome.get('constraint_amount') == parsed_choice.constraint_amount):
                agent_outcome = outcome
                break

        principle_name_localized = agent_outcome['principle_name'] if agent_outcome else parsed_choice.principle.value

        # Add constraint display if applicable
        if parsed_choice.constraint_amount is not None:
            principle_name_localized += f" (${parsed_choice.constraint_amount:,})"

        # Build payoff notification header
        payoff_header = self.language_manager.get('memory_field_labels.payoff_notification_header')
        earnings_display_parts.append(payoff_header)

        # Add chosen principle
        earnings_display_parts.append(f"{self.language_manager.get('memory_field_labels.chosen_principle')} {principle_name_localized}")

        # Add assigned class
        class_name_localized = comprehensive_data['class_display_name']
        earnings_display_parts.append(f"{self.language_manager.get('memory_field_labels.assigned_class')} {class_name_localized}")

        # Add situation or multiplier
        distribution_display = None
        if agent_outcome and 'distribution_index' in agent_outcome:
            distribution_number = agent_outcome['distribution_index'] + 1
            distribution_display = self.language_manager.get(
                'memory_field_labels.distribution_assignment',
                number=distribution_number
            )

        if is_original_values:
            if distribution_display:
                earnings_display_parts.append(distribution_display)
            elif original_situation:
                earnings_display_parts.append(
                    f"{self.language_manager.get('memory_field_labels.original_values_situation')} {original_situation}"
                )
            else:
                earnings_display_parts.append(
                    f"{self.language_manager.get('memory_field_labels.distribution_multiplier')} {distribution_set.multiplier:.2f}"
                )
        else:
            earnings_display_parts.append(
                f"{self.language_manager.get('memory_field_labels.distribution_multiplier')} {distribution_set.multiplier:.2f}"
            )

        # Add payoff
        earnings_display_parts.append(f"{self.language_manager.get('memory_field_labels.your_payoff')} {earnings:.2f}")

        # Add empty line before outcomes
        earnings_display_parts.append("")

        # Add simplified principle outcomes header
        principle_outcomes_header = self.language_manager.get(
            'comprehensive_earnings.principle_outcomes_simple_header',
            class_name=class_name_localized
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

        # Create simplified round content with prompt, response, and payoff notification
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {application_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}

{earnings_display}

{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.applied_principle_round', round_number=round_num)}"""
        
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
