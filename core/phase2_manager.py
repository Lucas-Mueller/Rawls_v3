"""
Phase 2 manager for group discussion and consensus building.
"""
import asyncio
import time
from typing import List, Optional

from models import (
    ParticipantContext, Phase2Results, GroupDiscussionResult, GroupDiscussionState,
    ExperimentPhase, Phase1Results, ExperimentStage
)
from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
from experiment_agents import update_participant_context, UtilityAgent, ParticipantAgent
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.logging import TranscriptLogger, run_with_transcript_logging
from utils.error_handling import ExperimentErrorHandler


class Phase2Manager:
    """Manages Phase 2 group discussion and consensus building."""
    
    def __init__(
        self,
        participants: List[ParticipantAgent],
        utility_agent: UtilityAgent,
        experiment_config=None,
        language_manager=None,
        error_handler=None,
        seed_manager=None,
        agent_logger=None,
        transcript_logger: Optional[TranscriptLogger] = None
    ):
        self.participants = participants
        self.utility_agent = utility_agent
        self.config = experiment_config
        self.language_manager = language_manager
        self.seed_manager = seed_manager
        self.agent_logger = agent_logger  # Store agent_logger for services
        self.logger = None  # Will be set in run_phase2
        # Use provided error handler or create a new one
        self.error_handler = error_handler if error_handler is not None else ExperimentErrorHandler()
        self.transcript_logger = transcript_logger
        
        # Load Phase 2 settings
        self.settings = experiment_config.phase2_settings if experiment_config and experiment_config.phase2_settings else Phase2Settings.get_default()
        
        # Initialize refactored services
        self._services_initialized = False
        self.speaking_order_service = None
        self.discussion_service = None
        self.voting_service = None
        self.memory_service = None
        self.counterfactuals_service = None
        self.manipulator_service = None

        # Add consensus lock for thread safety
        self._consensus_lock = asyncio.Lock()
        self._voting_in_progress = False
    
    def _initialize_services(self):
        """Initialize refactored services."""
        if self._services_initialized:
            return
        
        # Import services only when needed to avoid circular imports
        from core.services import SpeakingOrderService, DiscussionService, VotingService, MemoryService, CounterfactualsService, ManipulatorService
        
        # Simple logger that delegates to our logging methods
        logger = self
        
        # Initialize services - memory_service first since others depend on it
        self.memory_service = MemoryService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=logger,
            config=self.config,
            transcript_logger=self.transcript_logger
        )
        
        self.speaking_order_service = SpeakingOrderService(
            seed_manager=self.seed_manager,
            settings=self.settings,
            logger=logger
        )
        
        self.discussion_service = DiscussionService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=logger,
            transcript_logger=self.transcript_logger
        )
        
        self.voting_service = VotingService(
            language_manager=self.language_manager,
            utility_agent=self.utility_agent,
            settings=self.settings,
            logger=logger,
            memory_service=self.memory_service,
            agent_logger=self.agent_logger,
            phase2_rounds=self.config.phase2_rounds if self.config else 10,
            transcript_logger=self.transcript_logger
        )
        
        self.counterfactuals_service = CounterfactualsService(
            language_manager=self.language_manager,
            settings=self.settings,
            logger=logger,
            seed_manager=self.seed_manager,
            memory_service=self.memory_service,
            config=self.config,
            transcript_logger=self.transcript_logger
        )

        self.manipulator_service = ManipulatorService(
            language_manager=self.language_manager,
            logger=logger
        )

        self._services_initialized = True
        self._log_info("Phase2 services initialized")
    
    def _log_info(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.info(message)
    
    def _log_warning(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.warning(message)
    
    # Logger interface methods for services
    def log_info(self, message: str):
        """Custom logger interface for services."""
        self._log_info(message)

    def log_warning(self, message: str):
        """Custom logger interface for services."""
        self._log_warning(message)

    def info(self, message: str):
        """Standard logger interface for services."""
        self._log_info(message)

    def warning(self, message: str):
        """Standard logger interface for services."""
        self._log_warning(message)

    def debug(self, message: str):
        """Standard logger interface for services."""
        self._log_info(message)

    def error(self, message: str):
        """Standard logger interface for services."""
        self._log_warning(message)
    
    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message with fallback handling."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self._log_warning(f"Missing translation key: {key} - {str(e)}")
            # Return English fallback or key name
            return f"[MISSING: {key}]"
    
    
    
    def _get_localized_income_class(self, income_class: str) -> str:
        """Get localized income class label."""
        return self._get_localized_message(f"common.income_classes.{income_class}")
    


    
    
    async def run_phase2(
        self, 
        config: ExperimentConfiguration,
        phase1_results: List[Phase1Results],
        logger: AgentCentricLogger = None,
        process_logger=None
    ) -> Phase2Results:
        """Execute complete Phase 2 group discussion."""
        
        # Store logger for use in consensus methods
        self.logger = logger

        # Initialize services
        self._initialize_services()

        # Initialize voting history tracking if logger is provided
        if logger:
            logger.initialize_voting_history()

        # Check for manipulator targeting configuration (Hypothesis 3)
        manipulator_config = getattr(config, 'manipulator', None)
        self._manipulator_target_principle = None
        self._manipulator_target_info = None

        if manipulator_config and manipulator_config.get('target_strategy') == 'least_popular_after_round1':
            # Import and use preference aggregation service for surgical target detection
            from core.services import PreferenceAggregationService

            pref_service = PreferenceAggregationService(self.language_manager)

            try:
                target_result = pref_service.aggregate_preferences(
                    phase1_results=phase1_results,
                    manipulator_name=manipulator_config['name'],
                    tiebreak_order=manipulator_config.get('tiebreak_order', [])
                )

                # Store for result logging
                self._manipulator_target_principle = target_result['least_popular_principle']
                self._manipulator_target_info = {
                    'target_principle': target_result['least_popular_principle'],
                    'detection_method': 'surgical_aggregation',
                    'target_strategy': 'least_popular_after_round1',
                    'principle_scores': target_result['principle_scores'],
                    'tiebreak_applied': target_result['tiebreak_applied'],
                    'tied_principles': target_result.get('tied_principles', []),
                    'aggregation_method': target_result['aggregation_method']
                }

                # Store full target_result for injection service
                self._manipulator_aggregation_result = target_result

                # Log aggregation details
                if process_logger:
                    process_logger.log_technical(
                        f"Manipulator target (surgical aggregation): {self._manipulator_target_principle}"
                    )
                    process_logger.log_technical(
                        f"Preference scores (Borda count): {target_result['principle_scores']}"
                    )
                    if target_result['tiebreak_applied']:
                        process_logger.log_technical(
                            f"Tiebreaker applied: {target_result['tied_principles']}"
                        )

                    # Log formatted summary
                    summary = pref_service.format_aggregation_summary(target_result)
                    process_logger.log_technical(f"Aggregation summary:\n{summary}")

                self._log_info(f"Surgical preference aggregation complete: target = {self._manipulator_target_principle}")

            except Exception as e:
                self._log_warning(f"Failed to aggregate preferences for manipulator targeting: {e}")
                # Continue without target - manipulator will use prompt-based detection

        # CRITICAL: Initialize participants with CONTINUOUS memory from Phase 1
        participant_contexts = self._initialize_phase2_contexts(phase1_results, config)

        # Inject manipulator target instructions if available
        if (manipulator_config and
            self._manipulator_target_principle and
            hasattr(self, '_manipulator_aggregation_result')):
            try:
                self._log_info("Injecting manipulator target instructions...")
                delivery_metadata = self.manipulator_service.inject_target_instructions(
                    contexts=participant_contexts,
                    manipulator_name=manipulator_config['name'],
                    target_principle=self._manipulator_target_principle,
                    aggregation_details=self._manipulator_aggregation_result,
                    process_logger=process_logger
                )

                # Update _manipulator_target_info with delivery metadata
                self._manipulator_target_info.update(delivery_metadata)

                # Log delivery status
                if delivery_metadata['delivered']:
                    self._log_info(
                        f"Successfully delivered target to {manipulator_config['name']} "
                        f"via {delivery_metadata['delivery_channel']} at {delivery_metadata['delivered_at']}"
                    )
                    if process_logger:
                        process_logger.log_technical(
                            f"Manipulator target delivered: {self._manipulator_target_principle} "
                            f"(channel: {delivery_metadata['delivery_channel']})"
                        )
                else:
                    self._log_warning(
                        f"Failed to deliver target to {manipulator_config['name']}: "
                        f"{delivery_metadata.get('error_message', 'Unknown error')}"
                    )
                    if process_logger:
                        process_logger.log_technical(
                            f"Manipulator target delivery failed: {delivery_metadata.get('error_message', 'Unknown error')}"
                        )

            except Exception as e:
                self._log_warning(f"Error during manipulator target injection: {e}")
                # Continue experiment even if injection fails
                if self._manipulator_target_info:
                    self._manipulator_target_info['injection_error'] = str(e)

        # Group discussion
        discussion_result = await self._run_group_discussion(
            config, participant_contexts, logger, process_logger
        )
        
        # Apply chosen principle and calculate payoffs
        payoff_results, assigned_classes, alternative_earnings_by_agent, distribution_set = await self.counterfactuals_service.apply_group_principle_and_calculate_payoffs(
            discussion_result=discussion_result,
            config=config,
            participants=self.participants
        )
        
        # PHASE 1: Deliver results and update participant memory
        self._log_info("Phase 3: Delivering results and updating participant memory")
        try:
            updated_contexts = await self.counterfactuals_service.deliver_results_and_update_memory(
                participants=self.participants,
                contexts=participant_contexts,
                discussion_result=discussion_result,
                payoff_results=payoff_results,
                assigned_classes=assigned_classes,
                alternative_earnings_by_agent=alternative_earnings_by_agent,
                config=config,
                distribution_set=distribution_set
            )
            self._log_info(f"Successfully updated memory for {len(updated_contexts)} participants")
        except Exception as e:
            self._log_warning(f"Error during result delivery and memory update: {str(e)}")
            raise
        
        # PHASE 2: Collect final rankings using updated contexts
        self._log_info("Phase 3: Collecting final rankings from participants with updated memory")
        try:
            final_rankings = await self.counterfactuals_service.collect_final_rankings_streamlined(
                contexts=updated_contexts,  # Use updated contexts from first call
                participants=self.participants,
                utility_agent=self.utility_agent,
                payoff_results=payoff_results,  # Optional for logging compatibility
                assigned_classes=assigned_classes,  # Use as-is, already in correct format
                logger=logger
            )
            self._log_info(f"Successfully collected final rankings from {len(final_rankings)} participants")
        except Exception as e:
            self._log_warning(f"Error during final ranking collection: {str(e)}")
            raise
        
        # PHASE 3: Log post-discussion state for each participant
        if logger:
            self._log_info("Phase 3: Logging post-discussion state for all participants")
            try:
                for i, participant in enumerate(self.participants):
                    participant_name = participant.name
                    
                    # Extract required data for logging
                    class_assigned = assigned_classes.get(participant_name, "unknown")
                    payoff = payoff_results.get(participant_name, 0.0)
                    ranking = final_rankings.get(participant_name)
                    
                    # Get updated context data
                    updated_context = updated_contexts[i]
                    memory_state = updated_context.memory
                    bank_balance = updated_context.bank_balance
                    
                    # Log post-discussion state
                    if ranking:  # Only log if we have a valid ranking
                        logger.log_post_discussion(
                            agent_name=participant_name,
                            class_assigned=class_assigned,
                            payoff=payoff,
                            ranking=ranking,
                            memory_state=memory_state,
                            bank_balance=bank_balance,
                            final_vote=None,  # Not tracking final votes in current implementation
                            vote_timestamp=None  # Not tracking vote timestamps in current implementation
                        )
                        self._log_info(f"Post-discussion state logged for {participant_name}")
                    else:
                        self._log_warning(f"No ranking available for {participant_name}, skipping post-discussion logging")
                
                self._log_info(f"Post-discussion logging completed for {len(self.participants)} participants")
            except Exception as e:
                self._log_warning(f"Error during post-discussion logging: {str(e)}")
                # Continue execution - logging failure should not break experiment
        
        return Phase2Results(
            discussion_result=discussion_result,
            payoff_results=payoff_results,
            alternative_earnings_by_agent=alternative_earnings_by_agent,
            final_rankings=final_rankings
        )
    
    
    def _initialize_phase2_contexts(
        self, 
        phase1_results: List[Phase1Results],
        config: ExperimentConfiguration
    ) -> List[ParticipantContext]:
        """
        CRITICAL: Transfer complete Phase 1 memory to Phase 2 contexts with validation
        This ensures continuous memory across experimental phases
        """
        phase2_contexts = []
        
        # Validate we have matching number of results and configs
        if len(phase1_results) != len(config.agents):
            self._log_warning(f"Mismatch: {len(phase1_results)} Phase 1 results but {len(config.agents)} agent configs")
        
        for i, phase1_result in enumerate(phase1_results):
            agent_config = config.agents[i]
            
            # Initialize services if needed
            self._initialize_services()
            
            # Validate and sanitize memory before transfer using MemoryService
            validated_memory = self.memory_service.validate_and_sanitize_memory(
                phase1_result.final_memory_state,
                agent_config.memory_character_limit,
                phase1_result.participant_name
            )
            
            # Create Phase 2 context with validated memory
            phase2_context = ParticipantContext(
                name=phase1_result.participant_name,
                role_description=agent_config.personality,
                bank_balance=phase1_result.total_earnings,  # Carry forward earnings
                memory=validated_memory,  # VALIDATED MEMORY FROM PHASE 1
                round_number=1,  # Start Phase 2 at round 1
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=agent_config.memory_character_limit,
                stage=ExperimentStage.DISCUSSION
            )
            
            phase2_contexts.append(phase2_context)
            
        return phase2_contexts
    
    async def _process_participant_statement(
        self, participant, context, agent_config, discussion_state, 
        round_num, speaking_order_position, process_logger
    ) -> tuple[str, str, bool]:
        """Process a single participant's statement with error handling."""
        # Update context with current round
        context.round_number = round_num
        context.stage = ExperimentStage.DISCUSSION

        # Log statement request
        if process_logger:
            process_logger.phase2_agent_speaking(participant.name, round_num)

        self._log_info(f"=== REQUESTING STATEMENT FROM {participant.name} ===")
        self._log_info(f"Round {round_num}, Speaking position {speaking_order_position + 1}")

        # Get participant statement with intelligent retry support
        start_time = time.time()
        participant_names = [p.name for p in self.participants]

        # Format Phase 2 discussion context header explicitly (replaces side channel)
        context.formatted_context_header = self.language_manager.format_phase2_discussion_instructions(
            round_number=round_num,
            max_rounds=self.config.phase2_rounds,
            participant_names=participant_names,
            discussion_history=discussion_state.public_history
        )

        # Use intelligent retry if enabled (following EXACT A1/A2 pattern)
        if self.config.enable_intelligent_retries:
            # Create retry callback that handles participant re-prompting (EXACT A1/A2 pattern)
            async def retry_callback(feedback: str) -> str:
                try:
                    self.logger.info(f"Intelligent retry callback triggered for {participant.name} in statement validation")

                    # Build discussion prompt (same as original)
                    discussion_prompt = self.discussion_service.build_discussion_prompt(
                        discussion_state=discussion_state,
                        round_num=context.round_number,
                        max_rounds=self.config.phase2_rounds,
                        participant_names=participant_names,
                        internal_reasoning=getattr(context, 'internal_reasoning', "")
                    )

                    # Build retry prompt with original prompt + feedback + guidance
                    retry_prompt = self._build_statement_retry_prompt(discussion_prompt, feedback, self.config.retry_feedback_detail)

                    # Get participant's retry response
                    retry_result = await run_with_transcript_logging(
                        participant=participant,
                        prompt=retry_prompt,
                        context=context,
                        transcript_logger=self.transcript_logger,
                        interaction_type="statement"
                    )
                    retry_response = retry_result.final_output

                    # Update participant memory with retry experience if enabled
                    if self.config.memory_update_on_retry:
                        await self._update_memory_with_retry_experience(
                            participant, context, feedback, retry_response, self.config
                        )

                    self.logger.info(f"Retry callback successful for {participant.name}, response length: {len(retry_response)}")
                    return retry_response

                except Exception as e:
                    self.logger.error(f"Retry callback failed for {participant.name} in statement validation: {e}")
                    return ""  # Return empty string to signal failure

            # Use enhanced method with feedback capability (same as A1/A2)
            statement, internal_reasoning = await self.discussion_service.get_participant_statement_with_intelligent_retry(
                participant=participant,
                context=context,
                discussion_state=discussion_state,
                agent_config=agent_config,
                participant_names=participant_names,
                max_rounds=self.config.phase2_rounds,
                max_retries=self.config.max_participant_retries + 1,  # +1 for initial attempt
                participant_retry_callback=retry_callback,
                utility_agent=self.utility_agent
            )
        else:
            # Fall back to existing method without intelligent retries
            statement, internal_reasoning = await self.discussion_service.get_participant_statement_with_retry(
                participant=participant,
                context=context,
                discussion_state=discussion_state,
                agent_config=agent_config,
                participant_names=participant_names,
                max_rounds=self.config.phase2_rounds
            )
        response_time = time.time() - start_time
        
        # Check if response is quarantined
        is_quarantined = statement.startswith("__QUARANTINED__")
        if is_quarantined:
            statement = statement.replace("__QUARANTINED__", "")
            self._log_warning(f"QUARANTINED RESPONSE for {participant.name} in round {round_num}")
        
        # Log response completion
        if process_logger:
            process_logger.phase2_agent_response(participant.name, len(statement), response_time)
        
        # Check if fallback response
        is_fallback = statement.startswith(f"[{participant.name} failed to provide") or is_quarantined
        self._log_info(f"=== STATEMENT RECEIVED FROM {participant.name} ===")
        self._log_info(f"Is fallback/quarantined: {is_fallback}")
        
        # Manage discussion history and add statement
        self.discussion_service.manage_discussion_history_length(discussion_state)
        
        if not is_quarantined or not self.settings.quarantine_failed_responses:
            discussion_state.add_statement(participant.name, statement, self.language_manager)
        else:
            neutral_msg = self.language_manager.get("prompts.phase2_agent_unavailable", participant_name=participant.name)
            discussion_state.add_statement(participant.name, neutral_msg, self.language_manager)
        
        return statement, internal_reasoning, is_fallback
    
    async def _log_discussion_round(
        self, logger, participant, round_num, speaking_order_position, 
        internal_reasoning, statement, context
    ):
        """Log discussion round details."""
        favored_principle = await self.discussion_service.extract_favored_principle(statement, self.utility_agent)
        logger.log_discussion_round(
            participant.name,
            round_num,
            speaking_order_position + 1,
            internal_reasoning,
            statement,
            "N/A",  # Using formal voting system
            favored_principle,
            context.memory,
            context.bank_balance
        )
    
    async def _update_participant_memory_and_context(
        self, participant, context, statement, internal_reasoning, round_num, participant_idx, discussion_state
    ):
        """Update participant memory and return updated context."""
        include_reasoning = self.config.phase2_include_internal_reasoning_in_memory if self.config else False
        
        context.memory = await self.memory_service.update_discussion_memory(
            agent=participant,
            context=context,
            statement=statement,
            internal_reasoning=internal_reasoning,
            round_num=round_num,
            include_internal_reasoning=include_reasoning,
            discussion_history=discussion_state.public_history
        )
        # Return updated context
        updated_ctx = update_participant_context(context, new_round=round_num, new_stage=context.stage)
        return updated_ctx
    
    async def _attempt_end_of_round_voting(
        self, round_num, contexts, participant_recent_statements, 
        participant_recent_reasoning, discussion_state, process_logger
    ):
        """Attempt to initiate voting at the end of a round."""
        self._log_info(f"Starting end-of-round vote prompting for round {round_num}")
        vote_responses = {}
        
        for participant_idx, participant in enumerate(self.participants):
            context = contexts[participant_idx]
            
            try:
                recent_statement = participant_recent_statements.get(participant.name, "")
                context.stage = ExperimentStage.VOTING
                recent_reasoning = participant_recent_reasoning.get(participant.name, "")

                # Format Phase 2 context header explicitly for vote initiation
                context.formatted_context_header = self.language_manager.format_phase2_discussion_instructions(
                    round_number=round_num,
                    max_rounds=self.config.phase2_rounds,
                    participant_names=[p.name for p in self.participants],
                    discussion_history=discussion_state.public_history,
                    agent_recent_statement=recent_statement
                )

                wants_vote = await self.voting_service.prompt_for_vote_initiation(
                    participant=participant,
                    context=context,
                    agent_recent_statement=recent_statement,
                    internal_reasoning=recent_reasoning
                )
                vote_responses[participant.name] = wants_vote
                
                # Log individual vote initiation decision
                if self.agent_logger:
                    try:
                        # Convert boolean to "Yes"/"No" string
                        vote_value = "Yes" if wants_vote else "No"
                        success = self.agent_logger.update_initiate_vote(participant.name, round_num, vote_value)
                        if success:
                            self._log_info(f"Successfully logged vote initiation for {participant.name}: {vote_value}")
                        else:
                            self._log_warning(f"Failed to log vote initiation for {participant.name}: {vote_value}")
                    except Exception as e:
                        self._log_warning(f"Error logging vote initiation for {participant.name}: {str(e)}")
                
                # Update memory with vote decision
                # Context header already set above for vote initiation, reuse it
                contexts[participant_idx].memory = await self.memory_service.update_vote_initiation_decision_memory(
                    agent=participant,
                    context=contexts[participant_idx],
                    round_num=round_num,
                    wants_vote=wants_vote
                )
                
                if wants_vote:
                    self._log_info(f"{participant.name} wants to initiate voting")
                    
                    try:
                        if process_logger:
                            process_logger.phase2_voting_initiated(round_num)
                        
                        consensus_reached = await self.voting_service.conduct_voting_process(
                            participants=self.participants,
                            initiating_participant=participant,
                            contexts=contexts,
                            discussion_state=discussion_state,
                            agent_recent_statement=recent_statement,
                            error_handler=self.error_handler,
                            utility_agent=self.utility_agent,
                            internal_reasoning=recent_reasoning
                        )
                        
                        if consensus_reached:
                            self._log_info(f"Consensus reached through {participant.name}'s voting")
                            
                            # DEFENSIVE CONSENSUS HANDLING: Handle both normal and fallback cases
                            if process_logger:
                                # Use defensive access to consensus result
                                try:
                                    agreed_principle = discussion_state._consensus_result.agreed_principle.principle.value if discussion_state._consensus_result.agreed_principle else None
                                    constraint_amount = discussion_state._consensus_result.agreed_principle.constraint_amount if discussion_state._consensus_result.agreed_principle else None
                                except AttributeError:
                                    # Fallback to last vote result if consensus_result is missing
                                    self._log_warning("Missing _consensus_result, using last_vote_result as fallback")
                                    if hasattr(discussion_state, 'last_vote_result') and discussion_state.last_vote_result:
                                        agreed_principle = discussion_state.last_vote_result.agreed_principle.principle.value if discussion_state.last_vote_result.agreed_principle else None
                                        constraint_amount = discussion_state.last_vote_result.agreed_principle.constraint_amount if discussion_state.last_vote_result.agreed_principle else None
                                    else:
                                        agreed_principle = None
                                        constraint_amount = None
                                process_logger.phase2_voting_result(True, agreed_principle, constraint_amount, round_num)
                            
                            # Defensive consensus result return
                            if hasattr(discussion_state, '_consensus_result') and discussion_state._consensus_result:
                                for ctx in contexts:
                                    ctx.stage = ExperimentStage.VOTING
                                return discussion_state._consensus_result
                            elif hasattr(discussion_state, 'last_vote_result') and discussion_state.last_vote_result and discussion_state.last_vote_result.consensus_reached:
                                # Create fallback consensus result
                                from models import GroupDiscussionResult
                                self._log_info("🛡️ Creating fallback consensus result from last_vote_result")
                                fallback_result = GroupDiscussionResult(
                                    consensus_reached=True,
                                    agreed_principle=discussion_state.last_vote_result.agreed_principle,
                                    final_round=round_num,
                                    discussion_history=discussion_state.public_history,
                                    vote_history=discussion_state.vote_history
                                )
                                for ctx in contexts:
                                    ctx.stage = ExperimentStage.VOTING
                                return fallback_result
                            else:
                                self._log_warning("⚠️ Consensus detected but no valid result available for return")
                                return None
                        else:
                            self._log_info(f"No consensus reached through {participant.name}'s voting")
                            if process_logger:
                                process_logger.phase2_voting_result(False, None, None, round_num)
                    
                    except Exception as voting_error:
                        self._log_warning(f"Error during voting process: {str(voting_error)}")
                    
                    # Exit after first vote attempt
                    break
                    
            except Exception as prompt_error:
                self._log_warning(f"Error during vote prompting for {participant.name}: {str(prompt_error)}")
                vote_responses[participant.name] = None
                
                # Log error case for vote initiation
                if self.agent_logger:
                    try:
                        success = self.agent_logger.update_initiate_vote(participant.name, round_num, "Error")
                        if success:
                            self._log_info(f"Successfully logged vote initiation error for {participant.name}")
                        else:
                            self._log_warning(f"Failed to log vote initiation error for {participant.name}")
                    except Exception as e:
                        self._log_warning(f"Error logging vote initiation error for {participant.name}: {str(e)}")
        
        # Log voting history
        if self.logger:
            clean_responses = {
                name: "Yes" if resp is True else "No" if resp is False else "Error"
                for name, resp in vote_responses.items()
            }
            self.logger.log_round_vote_requests(round_num, clean_responses)
        
        # DEFENSIVE FINAL CHECK: Even if no explicit vote attempts, check if consensus exists
        if (hasattr(discussion_state, 'last_vote_result') and 
            discussion_state.last_vote_result and 
            discussion_state.last_vote_result.consensus_reached and 
            not hasattr(discussion_state, '_consensus_result')):
            
            self._log_info("🛡️ DEFENSIVE: Found unreported consensus in last_vote_result")
            from models import GroupDiscussionResult
            defensive_result = GroupDiscussionResult(
                consensus_reached=True,
                agreed_principle=discussion_state.last_vote_result.agreed_principle,
                final_round=round_num,
                discussion_history=discussion_state.public_history,
                vote_history=discussion_state.vote_history
            )
            
            if process_logger:
                try:
                    agreed_principle = discussion_state.last_vote_result.agreed_principle.principle.value if discussion_state.last_vote_result.agreed_principle else None
                    constraint_amount = discussion_state.last_vote_result.agreed_principle.constraint_amount if discussion_state.last_vote_result.agreed_principle else None
                    process_logger.phase2_voting_result(True, agreed_principle, constraint_amount, round_num)
                    self._log_info("🛡️ DEFENSIVE: Reported consensus to process_logger")
                except Exception as e:
                    self._log_warning(f"Failed to report defensive consensus to process_logger: {e}")
            
            return defensive_result
        
        for ctx in contexts:
            if ctx.stage == ExperimentStage.VOTING:
                ctx.stage = ExperimentStage.DISCUSSION
        return None  # No consensus reached
    
    async def _run_group_discussion(
        self,
        config: ExperimentConfiguration,
        contexts: List[ParticipantContext],
        logger: AgentCentricLogger = None,
        process_logger=None
    ) -> GroupDiscussionResult:
        """Run sequential group discussion with voting."""
        # Ensure services are initialized (needed for speaking order service)
        self._initialize_services()

        discussion_state = GroupDiscussionState()
        # Set valid participants for isolation protection
        discussion_state.valid_participants = [agent.name for agent in config.agents]
        last_round_finisher = None
        
        for round_num in range(1, config.phase2_rounds + 1):
            discussion_state.round_number = round_num
            
            # Always use complex voting mode
            
            # Generate speaking order based on configuration
            speaking_order = self.speaking_order_service.generate_speaking_order(
                round_num=round_num,
                num_participants=len(contexts),
                randomize_speaking_order=config.randomize_speaking_order,
                strategy=getattr(config, 'speaking_order_strategy', 'fixed'),
                last_round_finisher=last_round_finisher
            )
            
            if process_logger:
                speaking_names = [self.participants[i].name for i in speaking_order]
                process_logger.phase2_round_start(round_num, config.phase2_rounds, speaking_names)
                round_start_time = time.time()
            # Track who finishes this round (last speaker)
            current_round_finisher = speaking_order[-1]
            
            # Track participants who spoke in this round for logging consistency validation
            round_participants_logged = set()
            
            # Track recent statements and reasoning for vote consistency
            participant_recent_statements = {}
            participant_recent_reasoning = {}
            
            # Process each participant's statement in speaking order
            for speaking_order_position, participant_idx in enumerate(speaking_order):
                participant = self.participants[participant_idx]
                context = contexts[participant_idx]
                agent_config = config.agents[participant_idx]
                
                # Process participant statement
                statement, internal_reasoning, is_fallback = await self._process_participant_statement(
                    participant, context, agent_config, discussion_state, 
                    round_num, speaking_order_position, process_logger
                )
                
                # Store for vote consistency and track logging
                participant_recent_statements[participant.name] = statement
                participant_recent_reasoning[participant.name] = internal_reasoning
                if not is_fallback:
                    round_participants_logged.add(participant.name)
                
                # Log discussion round if logger available
                if logger and not is_fallback:
                    await self._log_discussion_round(
                        logger, participant, round_num, speaking_order_position,
                        internal_reasoning, statement, context
                    )
                
                # Update context round number only (memory update deferred to post-round phase)
                contexts[participant_idx].round_number = round_num
                
                # Skip consensus processing for failed responses
                if is_fallback:
                    continue
                
                # Check for early consensus (if already reached)
                async with self._consensus_lock:
                    if hasattr(discussion_state, '_consensus_reached') and discussion_state._consensus_reached:
                        return discussion_state._consensus_result
            
            # Validate round logging consistency
            if logger:
                expected_participants = {participant.name for participant in self.participants}
                if round_participants_logged != expected_participants:
                    missing_participants = expected_participants - round_participants_logged
                    extra_participants = round_participants_logged - expected_participants
                    
                    self._log_warning(f"Round {round_num} logging inconsistency:")
                    if missing_participants:
                        self._log_warning(f"  Missing logs for: {missing_participants}")
                    if extra_participants:
                        self._log_warning(f"  Extra logs for: {extra_participants}")
                else:
                    self._log_info(f"Round {round_num} logging consistent: {len(round_participants_logged)} participants")
            
            # Update last round finisher for next round
            last_round_finisher = current_round_finisher

            # Post-round symmetric memory update phase
            self._log_info(f"Starting post-round memory updates for round {round_num} with complete context")

            # Format Phase 2 context header for all memory updates
            for participant_idx in range(len(self.participants)):
                contexts[participant_idx].formatted_context_header = self.language_manager.format_phase2_discussion_instructions(
                    round_number=round_num,
                    max_rounds=self.config.phase2_rounds,
                    participant_names=[p.name for p in self.participants],
                    discussion_history=discussion_state.public_history
                )

            for participant_idx, participant in enumerate(self.participants):
                if participant.name in participant_recent_statements:
                    # Update memory with complete round context (context header already set above)
                    contexts[participant_idx] = await self._update_participant_memory_and_context(
                        participant, contexts[participant_idx],
                        participant_recent_statements[participant.name],
                        participant_recent_reasoning[participant.name],
                        round_num, participant_idx, discussion_state
                    )
                    self._log_info(f"Updated memory for {participant.name} with complete round {round_num} context")
                else:
                    # Update context for participants without statements (fallback cases)
                    contexts[participant_idx].round_number = round_num
                    contexts[participant_idx].stage = ExperimentStage.DISCUSSION

            self._log_info(f"Completed symmetric memory updates for round {round_num}")

            # Calculate rounds remaining
            rounds_remaining = config.phase2_rounds - round_num

            # Insert countdown message when there are exactly 2 rounds left
            if rounds_remaining == 2:
                countdown_msg = self.language_manager.get(
                    "system_messages.discussion.rounds_remaining",
                    rounds_remaining=rounds_remaining
                )
                discussion_state.public_history += f"\n{countdown_msg}"
                self._log_info(f"Added round countdown message: {rounds_remaining} rounds remaining")

            # Try to initiate voting at end of round
            consensus_result = await self._attempt_end_of_round_voting(
                round_num, contexts, participant_recent_statements,
                participant_recent_reasoning, discussion_state, process_logger
            )
            if consensus_result:
                return consensus_result
                
            # Log round completion for ProcessFlowLogger
            if process_logger:
                round_duration = time.time() - round_start_time if 'round_start_time' in locals() else 0.0
                process_logger.phase2_round_complete(round_num, round_duration)
            
        
        # No consensus reached
        
        return GroupDiscussionResult(
            consensus_reached=False,
            final_round=config.phase2_rounds,
            discussion_history=discussion_state.public_history,
            vote_history=discussion_state.vote_history
        )

    def _build_statement_retry_prompt(self, original_prompt: str, feedback: str, detail_level: str) -> str:
        """Build retry prompt with statement validation feedback (EXACT A1/A2 pattern)."""
        language_manager = self.language_manager

        # Base retry prompt structure (EXACT A1/A2 pattern)
        retry_intro = language_manager.get('retry_prompts.retry_needed_intro',
                                        fallback="Let me try to provide a better response.")

        # Add detail based on configuration (EXACT A1/A2 pattern)
        if detail_level == "detailed":
            retry_prompt = f"""{retry_intro}

{language_manager.get('retry_prompts.feedback_header', fallback='Feedback on previous response:')} {feedback}

{language_manager.get('retry_prompts.original_request', fallback='Please respond to the original request:')} {original_prompt}"""
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
        """Update participant memory with retry experience (EXACT A1/A2 pattern)."""
        try:
            language_manager = self.language_manager

            # Create memory content for retry experience
            retry_memory_content = f"""{language_manager.get('memory_field_labels.feedback_received', fallback='Feedback received:')} {feedback[:200]}...
{language_manager.get('memory_field_labels.improved_response', fallback='Improved response:')} {retry_response[:300]}...
{language_manager.get('memory_field_labels.outcome', fallback='Outcome:')} {language_manager.get('memory_outcomes.statement_retry_successful', fallback='Successfully provided improved statement after feedback')}"""

            # Use MemoryService for consistent memory updates
            if hasattr(self, 'memory_service') and self.memory_service:
                # Import MemoryEventType if needed
                try:
                    from utils.memory_content import MemoryEventType
                    updated_memory = await self.memory_service.update_memory_selective(
                        agent=participant,
                        context=context,
                        content=retry_memory_content,
                        event_type=MemoryEventType.RETRY_EXPERIENCE,
                        event_metadata={"retry_type": "statement_validation", "successful": True}
                    )
                    context.memory = updated_memory
                except ImportError:
                    # Fallback to simple memory update if MemoryEventType not available
                    context.memory += f"\n\n{retry_memory_content}"

            self.logger.info(f"Updated memory with retry experience for {participant.name}")

        except Exception as e:
            self.logger.warning(f"Failed to update memory with retry experience for {participant.name}: {e}")
            # Non-fatal: continue execution
