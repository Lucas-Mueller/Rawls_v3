"""
Phase 2 manager for group discussion and consensus building.
"""
import asyncio
import random
import re
from typing import List, Dict
from agents import Agent, Runner

from models import (
    ParticipantContext, Phase2Results, GroupDiscussionResult, GroupDiscussionState,
    ExperimentPhase, VoteResult, PrincipleChoice, GroupStatementResponse,
    VotingResponse, Phase1Results, PrincipleRanking, PrincipleRankingResponse,
    JusticePrinciple, CertaintyLevel
)
from config import ExperimentConfiguration, AgentConfiguration
from experiment_agents import update_participant_context, UtilityAgent, ParticipantAgent
from core.distribution_generator import DistributionGenerator
from utils.memory_manager import MemoryManager
from utils.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from utils.language_manager import get_language_manager
from utils.error_handling import AgentCommunicationError, ErrorSeverity, ExperimentErrorHandler


class Phase2Manager:
    """Manages Phase 2 group discussion and consensus building."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent, experiment_config=None):
        self.participants = participants
        self.utility_agent = utility_agent
        self.config = experiment_config
        self.logger = None  # Will be set in run_phase2
        self.error_handler = ExperimentErrorHandler()
        self.validation_stats = {
            "total_statement_requests": 0,
            "successful_statements": 0,
            "failed_validations": 0,
            "retry_attempts": 0,
            "fallback_statements": 0
        }
    
    def _log_info(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.info(message)
    
    def _log_warning(self, message: str):
        """Safe logging helper."""
        if self.logger and hasattr(self.logger, 'debug_logger'):
            self.logger.debug_logger.warning(message)
    
    def _validate_statement(self, statement: str, participant_name: str) -> bool:
        """
        Validate that a statement is non-empty and meaningful.
        
        Args:
            statement: The statement to validate
            participant_name: Name of the participant for logging
            
        Returns:
            True if statement is valid, False otherwise
        """
        if not statement:
            self._log_warning(f"Empty statement received from {participant_name}")
            return False
            
        if not statement.strip():
            self._log_warning(f"Whitespace-only statement received from {participant_name}")
            return False
            
        # Check for minimum meaningful content (at least 10 characters after stripping)
        if len(statement.strip()) < 10:
            self._log_warning(f"Statement too short from {participant_name}: '{statement.strip()}'")
            return False
            
        self._log_info(f"Valid statement received from {participant_name} ({len(statement.strip())} characters)")
        return True
    
    def _log_validation_statistics(self):
        """Log final validation statistics for the experiment."""
        self._log_info("=== STATEMENT VALIDATION STATISTICS ===")
        self._log_info(f"Total statement requests: {self.validation_stats['total_statement_requests']}")
        self._log_info(f"Successful statements: {self.validation_stats['successful_statements']}")
        self._log_info(f"Failed validations: {self.validation_stats['failed_validations']}")
        self._log_info(f"Total retry attempts: {self.validation_stats['retry_attempts']}")
        self._log_info(f"Fallback statements used: {self.validation_stats['fallback_statements']}")
        
        if self.validation_stats['total_statement_requests'] > 0:
            success_rate = (self.validation_stats['successful_statements'] / 
                          self.validation_stats['total_statement_requests']) * 100
            self._log_info(f"Success rate: {success_rate:.1f}%")
        
        if self.validation_stats['successful_statements'] > 0:
            avg_retries = (self.validation_stats['retry_attempts'] / 
                          self.validation_stats['successful_statements'])
            self._log_info(f"Average retries per successful statement: {avg_retries:.2f}")
        
        self._log_info("=== END VALIDATION STATISTICS ===")
        
        return self.validation_stats.copy()
    
    async def _get_participant_statement_with_retry(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration,
        internal_reasoning: str = "",
        max_retries: int = 3
    ) -> tuple[str, str]:
        """
        Get participant statement with retry logic for empty responses.
        
        Args:
            participant: The participant agent
            context: Current participant context
            discussion_state: Current discussion state
            agent_config: Agent configuration
            internal_reasoning: Internal reasoning to include in prompt (if reasoning enabled)
            max_retries: Maximum number of retry attempts
            
        Returns:
            tuple: (statement, round_content)
            
        Raises:
            AgentCommunicationError: If all retry attempts fail
        """
        discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number, internal_reasoning)
        self.validation_stats["total_statement_requests"] += 1
        
        for attempt in range(max_retries):
            try:
                self._log_info(f"Getting statement from {participant.name} (attempt {attempt + 1}/{max_retries})")
                
                # Get statement from agent
                result = await Runner.run(participant.agent, discussion_prompt, context=context)
                statement = result.final_output
                
                # Validate the statement
                if self._validate_statement(statement, participant.name):
                    # Update statistics
                    self.validation_stats["successful_statements"] += 1
                    if attempt > 0:
                        self.validation_stats["retry_attempts"] += attempt
                    
                    # Create round content for memory
                    round_content = f"""Prompt: {discussion_prompt}
Your Statement: {statement}
Outcome: Made statement in Round {context.round_number} of group discussion."""
                    
                    if attempt > 0:
                        self._log_info(f"Valid statement received from {participant.name} after {attempt + 1} attempts")
                    
                    return statement, round_content
                else:
                    # Statement validation failed
                    self.validation_stats["failed_validations"] += 1
                    
                    if attempt < max_retries - 1:
                        self._log_warning(f"Invalid statement from {participant.name}, retrying... (attempt {attempt + 1}/{max_retries})")
                        
                        # Modify prompt for retry to be more explicit
                        discussion_prompt = f"""
IMPORTANT: Your previous response was empty or too short. Please provide a meaningful response.

{self._build_discussion_prompt(discussion_state, context.round_number)}

Please ensure your response contains a clear statement about your position on the justice principles.
                        """.strip()
                    else:
                        # All retries exhausted
                        error_msg = f"Agent {participant.name} failed to provide valid statement after {max_retries} attempts"
                        self._log_warning(error_msg)
                        raise AgentCommunicationError(
                            error_msg,
                            ErrorSeverity.DEGRADED,
                            context={
                                "participant": participant.name,
                                "round": context.round_number,
                                "attempts": max_retries,
                                "last_response": statement
                            }
                        )
                        
            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt failed with exception
                    error_msg = f"Exception getting statement from {participant.name}: {str(e)}"
                    self._log_warning(error_msg)
                    raise AgentCommunicationError(
                        error_msg,
                        ErrorSeverity.DEGRADED,
                        context={
                            "participant": participant.name,
                            "round": context.round_number,
                            "attempts": max_retries,
                            "exception": str(e)
                        },
                        cause=e
                    )
                else:
                    self._log_warning(f"Exception on attempt {attempt + 1} for {participant.name}: {str(e)}, retrying...")
    
    async def run_phase2(
        self, 
        config: ExperimentConfiguration,
        phase1_results: List[Phase1Results],
        logger: AgentCentricLogger = None
    ) -> Phase2Results:
        """Execute complete Phase 2 group discussion."""
        
        # Store logger for use in consensus methods
        self.logger = logger
        
        # Initialize voting history tracking if logger is provided
        if logger:
            logger.initialize_voting_history(config.voting_detection_mode)
        
        # CRITICAL: Initialize participants with CONTINUOUS memory from Phase 1
        participant_contexts = self._initialize_phase2_contexts(phase1_results, config)
        
        # Group discussion
        discussion_result = await self._run_group_discussion(
            config, participant_contexts, logger
        )
        
        # Apply chosen principle and calculate payoffs
        payoff_results, assigned_classes = await self._apply_group_principle_and_calculate_payoffs(
            discussion_result, config
        )
        
        # Final individual rankings
        final_rankings = await self._collect_final_rankings(
            participant_contexts, discussion_result, payoff_results, assigned_classes, config, logger
        )
        
        return Phase2Results(
            discussion_result=discussion_result,
            payoff_results=payoff_results, 
            final_rankings=final_rankings
        )
    
    def _initialize_phase2_contexts(
        self, 
        phase1_results: List[Phase1Results],
        config: ExperimentConfiguration
    ) -> List[ParticipantContext]:
        """
        CRITICAL: Transfer complete Phase 1 memory to Phase 2 contexts
        This ensures continuous memory across experimental phases
        """
        phase2_contexts = []
        
        for i, phase1_result in enumerate(phase1_results):
            agent_config = config.agents[i]
            
            # Create Phase 2 context with continuous memory - no automatic transition
            phase2_context = ParticipantContext(
                name=phase1_result.participant_name,
                role_description=agent_config.personality,
                bank_balance=phase1_result.total_earnings,  # Carry forward earnings
                memory=phase1_result.final_memory_state,  # CONTINUOUS MEMORY FROM PHASE 1
                round_number=0,  # Reset for Phase 2
                phase=ExperimentPhase.PHASE_2,
                memory_character_limit=agent_config.memory_character_limit
            )
            
            phase2_contexts.append(phase2_context)
            
        return phase2_contexts
    
    async def _run_group_discussion(
        self,
        config: ExperimentConfiguration,
        contexts: List[ParticipantContext],
        logger: AgentCentricLogger = None
    ) -> GroupDiscussionResult:
        """Run sequential group discussion with voting."""
        
        discussion_state = GroupDiscussionState()
        # Set valid participants for isolation protection
        discussion_state.valid_participants = [agent.name for agent in config.agents]
        last_round_finisher = None
        
        for round_num in range(1, config.phase2_rounds + 1):
            discussion_state.round_number = round_num
            
            # Generate speaking order based on configuration
            speaking_order = self._generate_speaking_order(round_num, contexts, config, last_round_finisher)
            # Track who finishes this round (last speaker)
            current_round_finisher = speaking_order[-1]
            
            # Track participants who spoke in this round for logging consistency validation
            round_participants_logged = set()
            
            for speaking_order_position, participant_idx in enumerate(speaking_order):
                participant = self.participants[participant_idx]
                context = contexts[participant_idx]
                agent_config = config.agents[participant_idx]
                
                # Update context with current round
                context.round_number = round_num
                
                # Capture pre-statement state
                memory_before = context.memory
                balance_before = context.bank_balance
                
                # Get participant statement (with internal reasoning if enabled)
                self._log_info(f"=== REQUESTING STATEMENT FROM {participant.name} ===")
                self._log_info(f"Round {round_num}, Speaking position {speaking_order_position + 1}")
                
                statement, internal_reasoning = await self._get_participant_statement_enhanced(
                    participant, context, discussion_state, agent_config
                )
                
                # Log statement validation results
                is_fallback = statement.startswith(f"[{participant.name} failed to provide")
                self._log_info(f"=== STATEMENT RECEIVED FROM {participant.name} ===")
                self._log_info(f"Statement length: {len(statement)} characters")
                self._log_info(f"Is fallback statement: {is_fallback}")
                if is_fallback:
                    self._log_warning(f"FALLBACK STATEMENT USED for {participant.name} in round {round_num}")
                
                # Log first 100 characters of statement for debugging
                statement_preview = statement[:100] + "..." if len(statement) > 100 else statement
                self._log_info(f"Statement preview: {statement_preview}")
                
                # Add statement and mark vote proposals when detected later
                discussion_state.add_statement(participant.name, statement)
                
                # Log discussion round
                if logger:
                    vote_intention = MemoryStateCapture.extract_vote_intention(statement)
                    favored_principle = self._extract_favored_principle(statement)
                    
                    logger.log_discussion_round(
                        participant.name,
                        round_num,
                        speaking_order_position + 1,  # 1-indexed speaking order
                        internal_reasoning,
                        statement,
                        vote_intention,
                        favored_principle,
                        memory_before,
                        balance_before
                    )
                    
                    # Track that this participant was logged for this round
                    round_participants_logged.add(participant.name)
                
                # Create delta-focused round content
                from utils.memory_content import build_phase2_delta
                from config import ExperimentConfiguration
                
                # Extract configuration for memory guidance
                include_reasoning = self.config.phase2_include_internal_reasoning_in_memory if self.config else False
                memory_guidance_style = self.config.memory_guidance_style if self.config else "narrative"
                
                round_content = build_phase2_delta(
                    round_number=round_num,
                    participant_name=participant.name,
                    statement=statement,
                    speaking_order_position=speaking_order_position + 1,
                    internal_reasoning=internal_reasoning,
                    include_internal_reasoning=include_reasoning
                )
                
                # Update participant memory with agent using new guidance style
                context.memory = await MemoryManager.prompt_agent_for_memory_update(
                    participant, context, round_content, memory_guidance_style=memory_guidance_style
                )
                contexts[participant_idx] = update_participant_context(
                    context, new_round=round_num
                )
                
                # CRITICAL: Skip consensus mechanisms if agent failed to respond properly
                if is_fallback:
                    self._log_warning(f"Skipping consensus processing for {participant.name} due to agent failure")
                    # Continue to next participant without processing vote/preference detection
                    continue
                
                # Check voting detection mode
                if config.voting_detection_mode == "complex":
                    # Try complex voting detection
                    consensus_via_voting = await self._handle_complex_voting_mode(
                        participant, statement, discussion_state, contexts
                    )
                    
                    if consensus_via_voting and discussion_state.last_vote_result:
                        # Return consensus result from voting
                        return GroupDiscussionResult(
                            consensus_reached=True,
                            agreed_principle=discussion_state.last_vote_result.agreed_principle,
                            final_round=round_num,
                            discussion_history=discussion_state.public_history,
                            vote_history=discussion_state.vote_history
                        )
                
                # Continue with existing simple mode logic (preference detection)
                # Check for preference statement using new simple system
                preference = await self.utility_agent.detect_preference_statement(statement)
                
                # ADD PREFERENCE DETECTION DEBUG LOGGING
                import logging
                debug_logger = logging.getLogger(__name__)
                
                debug_logger.info(f"=== PREFERENCE DETECTION DEBUG ===")
                debug_logger.info(f"Agent: {participant.name}")
                debug_logger.info(f"Statement: {statement}")
                debug_logger.info(f"Preference detected: {preference is not None}")
                if preference:
                    debug_logger.info(f"Preference: {preference.principle.value} with constraint: {preference.constraint_amount}")
                else:
                    debug_logger.info(f"No preference detected")
                
                # Collect preferences from all participants in this round
                if preference:
                    # Store preference for this participant
                    if not hasattr(discussion_state, 'current_round_preferences'):
                        discussion_state.current_round_preferences = {}
                    
                    discussion_state.current_round_preferences[participant.name] = preference
                    
                    # Check for missing constraint amount and issue warning
                    if (preference.constraint_amount is None and 
                        preference.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
                        warning_msg = f"⚠️  {participant.name} did not specify constraint amount for {preference.principle.value}"
                        discussion_state.public_history += f"\n[WARNING] {warning_msg}"
                        self._log_warning(warning_msg)
                    
                    # Add preference to public history
                    preference_display = f"{preference.principle.value}"
                    if preference.constraint_amount:
                        preference_display += f" (${preference.constraint_amount:,})"
                    discussion_state.public_history += f"\n[PREFERENCE] {participant.name}: {preference_display}"
                
                # Check for consensus after each participant speaks
                if hasattr(discussion_state, 'current_round_preferences'):
                    num_participants_with_preferences = len(discussion_state.current_round_preferences)
                    total_participants = len(self.participants)
                    
                    debug_logger.info(f"Preferences collected: {num_participants_with_preferences}/{total_participants}")
                    
                    # If all participants have stated preferences, check for consensus
                    if num_participants_with_preferences == total_participants:
                        # Start vote round tracking for preference consensus
                        if logger:
                            logger.start_vote_round(
                                round_number=round_num,
                                vote_type="preference_consensus"
                            )
                            
                            # Log each participant's preference as a "vote"
                            for participant_name, preference in discussion_state.current_round_preferences.items():
                                logger.log_vote_response(
                                    participant_name=participant_name,
                                    raw_response=f"Preference: {preference.principle.value}",
                                    assessed_choice=preference.principle.value,
                                    constraint_amount=preference.constraint_amount,
                                    parsing_success=True
                                )
                        
                        preferences_list = list(discussion_state.current_round_preferences.values())
                        consensus_reached, agreed_preference, warnings = self.utility_agent.check_preference_consensus(preferences_list)
                        
                        # Log warnings
                        for warning in warnings:
                            self._log_warning(warning)
                            discussion_state.public_history += f"\n[WARNING] {warning}"
                        
                        debug_logger.info(f"Consensus check result: {consensus_reached}")
                        if agreed_preference:
                            debug_logger.info(f"Agreed preference: {agreed_preference.principle.value} with constraint: {agreed_preference.constraint_amount}")
                        
                        # Complete vote round
                        if logger:
                            vote_counts = {}
                            for pref in preferences_list:
                                key = pref.principle.value
                                if pref.constraint_amount:
                                    key += f" (${pref.constraint_amount:,})"
                                vote_counts[key] = vote_counts.get(key, 0) + 1
                            
                            logger.complete_vote_round(
                                consensus_reached=consensus_reached,
                                agreed_principle=agreed_preference.principle.value if agreed_preference else None,
                                agreed_constraint=agreed_preference.constraint_amount if agreed_preference else None,
                                vote_counts=vote_counts,
                                warnings=warnings
                            )
                        
                        if consensus_reached and agreed_preference:
                            # Log validation statistics before returning
                            self._log_validation_statistics()
                            
                            # Clear the round preferences for next potential round
                            discussion_state.current_round_preferences.clear()
                            
                            return GroupDiscussionResult(
                                consensus_reached=True,
                                agreed_principle=agreed_preference,
                                final_round=round_num,
                                discussion_history=discussion_state.public_history,
                                vote_history=[]  # No explicit votes in new system
                            )
                        else:
                            # Reset preferences for next round if no consensus
                            discussion_state.current_round_preferences.clear()
                            consensus_msg = f"No consensus reached in round {round_num}. Discussion continues..."
                            discussion_state.public_history += f"\n[CONSENSUS CHECK] {consensus_msg}"
                            debug_logger.info(consensus_msg)
            
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
        
        # No consensus reached
        # Log validation statistics before returning
        self._log_validation_statistics()
        
        return GroupDiscussionResult(
            consensus_reached=False,
            final_round=config.phase2_rounds,
            discussion_history=discussion_state.public_history,
            vote_history=discussion_state.vote_history
        )
    
    def _generate_speaking_order(
        self, 
        round_num: int, 
        contexts: List[ParticipantContext],
        config: ExperimentConfiguration,
        last_round_finisher: int = None
    ) -> List[int]:
        """Generate speaking order based on configuration strategy.
        
        Implements restriction from master plan: if one round ends with Agent X, 
        the next round cannot start with Agent X.
        """
        participant_indices = list(range(len(contexts)))
        
        if not config.randomize_speaking_order or config.speaking_order_strategy == "fixed":
            # Fixed order: same sequence every round
            return participant_indices
        
        if config.speaking_order_strategy == "random":
            # Random behavior with finisher restriction
            random.shuffle(participant_indices)
            
            # If this isn't the first round, ensure different starter (can't be previous round's finisher)
            if last_round_finisher is not None and participant_indices[0] == last_round_finisher:
                # Swap first and second elements
                if len(participant_indices) > 1:
                    participant_indices[0], participant_indices[1] = participant_indices[1], participant_indices[0]
        
        elif config.speaking_order_strategy == "conversational":
            # For future implementation - currently defaults to random
            # Could implement conversation-driven order based on discussion state
            random.shuffle(participant_indices)
            
            # Still avoid previous round's finisher starting next round
            if last_round_finisher is not None and participant_indices[0] == last_round_finisher:
                if len(participant_indices) > 1:
                    participant_indices[0], participant_indices[1] = participant_indices[1], participant_indices[0]
        
        return participant_indices

    
    async def _get_participant_statement(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration
    ) -> tuple[str, str]:
        """Get participant's statement for the current round."""
        
        discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number)
        
        # Always use text responses, no structured output needed for statements
        result = await Runner.run(participant.agent, discussion_prompt, context=context)
        statement = result.final_output
        
        # Create round content for memory
        round_content = f"""Prompt: {discussion_prompt}
Your Statement: {statement}
Outcome: Made statement in Round {context.round_number} of group discussion."""
        
        return statement, round_content

    async def _get_participant_statement_enhanced(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration
    ) -> tuple[str, str]:
        """Get participant's statement with internal reasoning. Returns (statement, internal_reasoning)."""
        
        # If reasoning is enabled, ask for internal reasoning first
        internal_reasoning = ""
        if agent_config.reasoning_enabled:
            reasoning_prompt = self._build_internal_reasoning_prompt(discussion_state, context.round_number)
            reasoning_result = await Runner.run(participant.agent, reasoning_prompt, context=context)
            internal_reasoning = reasoning_result.final_output
        
        # Get public statement with validation and retry logic
        try:
            statement, _ = await self._get_participant_statement_with_retry(
                participant, context, discussion_state, agent_config, internal_reasoning
            )
            
            return statement, internal_reasoning
            
        except AgentCommunicationError as e:
            # Log the error and use fallback statement
            self._log_warning(f"Agent communication error for {participant.name}: {str(e)}")
            self.validation_stats["fallback_statements"] += 1
            
            # Provide a fallback statement indicating the issue
            fallback_statement = f"[{participant.name} failed to provide a valid response after multiple attempts]"
            
            return fallback_statement, internal_reasoning
    
    def _extract_favored_principle(self, statement: str) -> str:
        """Extract favored principle from participant statement."""
        statement_lower = statement.lower()
        
        if any(phrase in statement_lower for phrase in ["principle a", "maximizing floor", "floor income"]):
            return "Principle A"
        elif any(phrase in statement_lower for phrase in ["principle b", "maximizing average", "average income"]):
            return "Principle B"
        elif any(phrase in statement_lower for phrase in ["principle c", "floor constraint", "average with floor"]):
            return "Principle C"
        elif any(phrase in statement_lower for phrase in ["principle d", "range constraint", "average with range"]):
            return "Principle D"
        else:
            language_manager = get_language_manager()
            return language_manager.get("prompts.phase2_default_constraint_specification")
    
    
    
    
    
    
    
    
    
    async def _apply_group_principle_and_calculate_payoffs(
        self,
        discussion_result: GroupDiscussionResult,
        config: ExperimentConfiguration
    ) -> tuple[Dict[str, float], Dict[str, str]]:
        """Apply chosen principle or random assignment if no consensus.
        
        Returns:
            tuple: (payoffs dict, assigned_classes dict)
        """
        
        # Generate new distribution set for Phase 2 payoffs
        distribution_set = DistributionGenerator.generate_dynamic_distribution(
            config.distribution_range_phase2
        )
        
        payoffs = {}
        assigned_classes = {}
        
        if discussion_result.consensus_reached and discussion_result.agreed_principle:
            # Apply agreed principle
            chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
                distribution_set.distributions, discussion_result.agreed_principle, config.income_class_probabilities
            )
            
            # Assign each participant to income class and calculate payoff
            for participant in self.participants:
                assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution, config.income_class_probabilities)
                payoffs[participant.name] = earnings
                assigned_classes[participant.name] = str(assigned_class)
        else:
            # Random assignment - each participant gets random income class from random distribution
            for participant in self.participants:
                random_distribution = random.choice(distribution_set.distributions)
                assigned_class, earnings = DistributionGenerator.calculate_payoff(random_distribution, config.income_class_probabilities)
                payoffs[participant.name] = earnings
                assigned_classes[participant.name] = str(assigned_class)
        
        return payoffs, assigned_classes
    
    async def _collect_final_rankings(
        self,
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        assigned_classes: Dict[str, str],
        config: ExperimentConfiguration,
        logger: AgentCentricLogger = None
    ) -> Dict[str, PrincipleRanking]:
        """Collect final principle rankings from all participants."""
        
        final_ranking_tasks = []
        
        for i, participant in enumerate(self.participants):
            context = contexts[i]
            agent_config = config.agents[i]
            
            # Update context with final results using agent-managed memory
            final_earnings = payoff_results[participant.name]
            result_content = f"FINAL RESULTS: Phase 2 earnings: ${final_earnings:.2f}. "
            
            if discussion_result.consensus_reached:
                result_content += f"Group reached consensus on {discussion_result.agreed_principle.principle.value}."
            else:
                result_content += "Group did not reach consensus. Earnings were randomly assigned."
            
            # Update memory with agent
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, f"Final Phase 2 Results: {result_content}"
            )
            
            updated_context = update_participant_context(
                context, balance_change=final_earnings
            )
            
            task = asyncio.create_task(
                self._get_final_ranking(participant, updated_context, agent_config)
            )
            assigned_class = assigned_classes[participant.name]
            final_ranking_tasks.append((task, participant.name, assigned_class, final_earnings, context.memory, updated_context.bank_balance))
        
        # Gather just the tasks for asyncio
        tasks = [task_info[0] for task_info in final_ranking_tasks]
        rankings = await asyncio.gather(*tasks)
        
        # Log post-discussion state with final rankings and return dictionary
        final_rankings = {}
        for i, ranking in enumerate(rankings):
            task_info = final_ranking_tasks[i]
            participant_name = task_info[1]
            assigned_class = task_info[2]
            final_earnings = task_info[3]
            memory_state = task_info[4]
            bank_balance = task_info[5]
            
            # Log post-discussion state with actual ranking
            if logger:
                logger.log_post_discussion(
                    participant_name,
                    assigned_class,
                    final_earnings,
                    ranking,
                    memory_state,
                    bank_balance
                )
            
            final_rankings[participant_name] = ranking
        
        return final_rankings
    
    async def _get_final_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> PrincipleRanking:
        """Get participant's final principle ranking after Phase 2."""
        
        language_manager = get_language_manager()
        final_ranking_prompt = language_manager.get("prompts.phase2_final_ranking_prompt")
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        return await self.utility_agent.parse_principle_ranking_enhanced(text_response)
    
    def _build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int) -> str:
        """Build prompt for internal reasoning before public statement."""
        language_manager = get_language_manager()
        
        return language_manager.get("prompts.phase2_internal_reasoning",
                                   round_number=round_num,
                                   max_rounds=self.config.phase2_rounds,
                                   discussion_history=discussion_state.public_history or "No previous discussion.")
    
    def _build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, internal_reasoning: str = "") -> str:
        """Build prompt for group discussion round based on voting detection mode."""
        language_manager = get_language_manager()
        
        # Use different prompts based on voting detection mode
        if self.config.voting_detection_mode == "complex":
            # For complex mode: allow voting proposals
            base_prompt = language_manager.get("prompts.phase2_discussion_prompt_complex",
                                              round_number=round_num,
                                              max_rounds=self.config.phase2_rounds,
                                              discussion_history=discussion_state.public_history or "No previous discussion.")
        else:
            # For simple mode: use preference-based consensus (FIXED to use correct prompt)
            base_prompt = language_manager.get("prompts.phase2_discussion_prompt_simple",
                                              round_number=round_num,
                                              max_rounds=self.config.phase2_rounds,
                                              discussion_history=discussion_state.public_history or "No previous discussion.")
        
        # If internal reasoning is provided, include it in the prompt
        if internal_reasoning and internal_reasoning.strip():
            return f"{base_prompt}\n\n=== YOUR INTERNAL REASONING ===\n{internal_reasoning}\n================================\n\nBased on your internal reasoning above, what is your statement to the group for this round?"
        else:
            return base_prompt
    
    async def _handle_complex_voting_mode(
        self,
        participant: 'ParticipantAgent',
        statement: str,
        discussion_state: GroupDiscussionState,
        contexts: List[ParticipantContext]
    ) -> bool:
        """
        Handle complex voting detection and process if needed.
        Returns True if consensus was reached through voting, False otherwise.
        """
        
        # Check if voting intention is detected using existing method
        vote_detection_result = await self.utility_agent.detect_vote_intention_enhanced(statement)
        
        if vote_detection_result is None:
            return False  # No voting intention detected
        
        self._log_info(f"Complex voting intention detected from {participant.name}")
        
        # Start vote round tracking
        if self.logger:
            self.logger.start_vote_round(
                round_number=discussion_state.round_number,
                vote_type="formal_vote",
                trigger_participant=participant.name,
                trigger_statement=statement
            )
        
        # Set active vote flag
        discussion_state.active_vote_in_progress = True
        
        # Step A: Confirmation Phase
        confirmation_success = await self._conduct_confirmation_phase(
            participant.name, statement, contexts, discussion_state
        )
        
        if not confirmation_success:
            self._log_info("Voting confirmation failed - returning to discussion")
            # Complete failed vote round
            if self.logger:
                self.logger.complete_vote_round(
                    consensus_reached=False,
                    warnings=["Confirmation phase failed"]
                )
            discussion_state.active_vote_in_progress = False
            return False
        
        # Step B: Secret Ballot Phase
        consensus_reached = await self._conduct_secret_ballot_phase(
            contexts, discussion_state
        )
        
        # Complete vote round with results
        if self.logger and discussion_state.last_vote_result:
            vote_result = discussion_state.last_vote_result
            self.logger.complete_vote_round(
                consensus_reached=vote_result.consensus_reached,
                agreed_principle=vote_result.agreed_principle.principle.value if vote_result.agreed_principle else None,
                agreed_constraint=vote_result.agreed_principle.constraint_amount if vote_result.agreed_principle else None,
                vote_counts=vote_result.vote_counts
            )
        
        # Complete voting process
        discussion_state.active_vote_in_progress = False
        
        return consensus_reached
    
    async def _conduct_confirmation_phase(
        self,
        initiator_name: str,
        initiation_statement: str,
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState
    ) -> bool:
        """
        Conduct public confirmation phase using existing agreement detection.
        Returns True if all participants agree to vote.
        """
        
        self._log_info("=== COMPLEX VOTING: CONFIRMATION PHASE ===")
        
        language_manager = get_language_manager()
        
        # Create confirmation prompt using new language manager key
        confirmation_prompt = language_manager.get(
            "prompts.utility_voting_confirmation_request",
            initiation_statement=initiation_statement
        )
        
        confirmations = []
        
        for i, context in enumerate(contexts):
            participant = self.participants[i]
            
            # Get confirmation response from participant
            result = await Runner.run(participant.agent, confirmation_prompt, context=context)
            confirmation_response = result.final_output
            
            # CRITICAL: Check if response is a fallback statement (agent failure)
            is_fallback = confirmation_response.startswith(f"[{participant.name} failed to provide")
            if is_fallback:
                self._log_warning(f"Fallback response detected for {participant.name} - voting confirmation failed")
                discussion_state.public_history += f"\n[VOTING CONFIRMATION] {participant.name}: {confirmation_response}"
                discussion_state.public_history += f"\n[VOTING RESULT] Agent failure detected - confirmation failed"
                return False
            
            # Use existing multilingual agreement detection
            agrees_to_vote = await self.utility_agent.detect_agreement_multilingual(confirmation_response)
            
            confirmations.append({
                'participant': participant.name,
                'response': confirmation_response,
                'agrees': agrees_to_vote
            })
            
            # Add to public history (visible to all)
            discussion_state.public_history += f"\n[VOTING CONFIRMATION] {participant.name}: {confirmation_response}"
            
            # If anyone disagrees, confirmation phase fails
            if not agrees_to_vote:
                self._log_info(f"{participant.name} declined voting - confirmation failed")
                discussion_state.public_history += f"\n[VOTING RESULT] Confirmation failed - returning to discussion"
                return False
        
        self._log_info("All participants agreed to vote - proceeding to secret ballot")
        discussion_state.public_history += f"\n[VOTING RESULT] All participants agreed - proceeding to secret ballot"
        
        # Log confirmation results
        if self.logger:
            self.logger.log_confirmation_phase(confirmations)
        
        return True
    
    async def _conduct_secret_ballot_phase(
        self,
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState
    ) -> bool:
        """
        Conduct secret ballot phase using existing parsing methods.
        Returns True if consensus is reached.
        """
        
        self._log_info("=== COMPLEX VOTING: SECRET BALLOT PHASE ===")
        
        language_manager = get_language_manager()
        ballot_prompt = language_manager.get("prompts.utility_secret_ballot_request")
        
        ballots = []
        
        for i, context in enumerate(contexts):
            participant = self.participants[i]
            
            # Get secret ballot from participant
            result = await Runner.run(participant.agent, ballot_prompt, context=context)
            ballot_response = result.final_output
            
            # Parse ballot using existing utility agent methods
            try:
                principle_choice = await self.utility_agent.parse_principle_choice_enhanced(ballot_response)
                ballots.append(principle_choice)
                self._log_info(f"Secret ballot received from {participant.name}")
                
                # Log the vote response
                if self.logger:
                    self.logger.log_vote_response(
                        participant_name=participant.name,
                        raw_response=ballot_response,
                        assessed_choice=principle_choice.principle.value,
                        constraint_amount=principle_choice.constraint_amount,
                        parsing_success=True
                    )
                
            except Exception as e:
                self._log_warning(f"Failed to parse ballot from {participant.name}: {e}")
                
                # Log failed parsing
                if self.logger:
                    self.logger.log_vote_response(
                        participant_name=participant.name,
                        raw_response=ballot_response,
                        assessed_choice="PARSING_FAILED",
                        parsing_success=False
                    )
                
                # Could implement re-prompt logic here if needed
                discussion_state.public_history += f"\n[VOTING ERROR] Failed to parse ballot - returning to discussion"
                return False
        
        # Check for consensus using new method
        consensus_reached, agreed_principle, warnings = self.utility_agent.check_ballot_consensus(ballots)
        
        # Handle constraint correction if needed
        if warnings and not consensus_reached:
            consensus_reached = await self._handle_constraint_corrections(
                ballots, contexts, warnings, discussion_state
            )
            if consensus_reached:
                # Re-check consensus after corrections
                consensus_reached, agreed_principle, _ = self.utility_agent.check_ballot_consensus(ballots)
        
        # Create VoteResult using existing model and store in existing vote_history
        vote_result = VoteResult(
            votes=ballots,
            consensus_reached=consensus_reached,
            agreed_principle=agreed_principle,
            vote_counts=self._calculate_vote_counts(ballots)
        )
        
        discussion_state.last_vote_result = vote_result
        discussion_state.vote_history.append(vote_result)  # Use existing vote_history
        
        if consensus_reached:
            self._log_info(f"Consensus reached via secret ballot: {agreed_principle.principle.value}")
            # Add to public history (aggregate result only, no individual ballots)
            consensus_msg = f"Secret ballot consensus: {agreed_principle.principle.value}"
            if agreed_principle.constraint_amount:
                consensus_msg += f" (${agreed_principle.constraint_amount:,})"
            discussion_state.public_history += f"\n[VOTING RESULT] {consensus_msg}"
        else:
            self._log_info("No consensus reached in secret ballot")
            discussion_state.public_history += f"\n[VOTING RESULT] No consensus in secret ballot - discussion continues"
        
        return consensus_reached
    
    def _calculate_vote_counts(self, ballots: List[PrincipleChoice]) -> Dict[str, int]:
        """Calculate vote counts for VoteResult."""
        counts = {}
        for ballot in ballots:
            key = ballot.principle.value
            if ballot.constraint_amount:
                key += f" (${ballot.constraint_amount:,})"
            counts[key] = counts.get(key, 0) + 1
        return counts
    
    async def _handle_constraint_corrections(
        self,
        ballots: List[PrincipleChoice],
        contexts: List[ParticipantContext],
        warnings: List[str],
        discussion_state: GroupDiscussionState
    ) -> bool:
        """
        Handle constraint corrections using existing memory management.
        Returns True if corrections were successful.
        """
        
        self._log_info("=== COMPLEX VOTING: CONSTRAINT CORRECTIONS ===")
        
        # This would implement the constraint correction loop
        # For now, return False to indicate corrections not implemented
        # Could be added in a future iteration
        
        discussion_state.public_history += f"\n[VOTING WARNING] Some ballots missing constraint amounts"
        return False
