"""
Phase 2 manager for group discussion and consensus building.
"""
import asyncio
import random
import re
import time
from typing import List, Dict, Optional
from agents import Agent, Runner

from models import (
    ParticipantContext, Phase2Results, GroupDiscussionResult, GroupDiscussionState,
    ExperimentPhase, VoteResult, PrincipleChoice, GroupStatementResponse,
    VotingResponse, Phase1Results, PrincipleRanking, PrincipleRankingResponse,
    JusticePrinciple, CertaintyLevel
)
from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
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
        
        # Load Phase 2 settings
        self.settings = experiment_config.phase2_settings if experiment_config and experiment_config.phase2_settings else Phase2Settings.get_default()
        
        # Add consensus lock for thread safety
        self._consensus_lock = asyncio.Lock()
        self._voting_in_progress = False
        
        self.validation_stats = {
            "total_statement_requests": 0,
            "successful_statements": 0,
            "failed_validations": 0,
            "retry_attempts": 0,
            "fallback_statements": 0,
            "quarantined_responses": 0
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
        Validate that a statement is non-empty and meaningful with language awareness.
        
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
        
        # Get language-appropriate minimum length
        language = self.config.language if self.config else "English"
        min_length = self.settings.get_min_statement_length(language)
        
        # Count actual characters (handle multi-byte characters properly)
        statement_length = len(statement.strip())
        
        # Check for minimum meaningful content 
        if statement_length < min_length:
            self._log_warning(f"Statement too short from {participant_name}: '{statement.strip()[:50]}...' ({statement_length} chars, min: {min_length})")
            return False
            
        self._log_info(f"Valid statement received from {participant_name} ({statement_length} characters, language: {language})")
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
        max_retries: int = None
    ) -> tuple[str, str]:
        """
        Get participant statement with retry logic, timeout, and exponential backoff.
        
        Args:
            participant: The participant agent
            context: Current participant context
            discussion_state: Current discussion state
            agent_config: Agent configuration
            internal_reasoning: Internal reasoning to include in prompt (if reasoning enabled)
            max_retries: Maximum number of retry attempts (uses settings if not specified)
            
        Returns:
            tuple: (statement, round_content)
            
        Raises:
            AgentCommunicationError: If all retry attempts fail
        """
        if max_retries is None:
            max_retries = self.settings.max_statement_retries
            
        discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number, internal_reasoning)
        self.validation_stats["total_statement_requests"] += 1
        
        backoff_delay = 1.0  # Initial backoff delay in seconds
        
        for attempt in range(max_retries):
            try:
                self._log_info(f"Getting statement from {participant.name} (attempt {attempt + 1}/{max_retries})")
                
                # Add exponential backoff for retries
                if attempt > 0:
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= self.settings.retry_backoff_factor
                    self._log_info(f"Waited {backoff_delay:.1f}s before retry")
                
                # Get statement from agent with timeout
                try:
                    result = await asyncio.wait_for(
                        Runner.run(participant.agent, discussion_prompt, context=context),
                        timeout=self.settings.statement_timeout_seconds
                    )
                    statement = result.final_output
                except asyncio.TimeoutError:
                    self._log_warning(f"Timeout waiting for {participant.name} after {self.settings.statement_timeout_seconds}s")
                    statement = ""  # Treat timeout as empty response
                
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
        payoff_results, assigned_classes, alternative_earnings_by_agent = await self._apply_group_principle_and_calculate_payoffs(
            discussion_result, config
        )
        
        # Final individual rankings
        final_rankings = await self._collect_final_rankings(
            participant_contexts, discussion_result, payoff_results, assigned_classes, alternative_earnings_by_agent, config, logger
        )
        
        return Phase2Results(
            discussion_result=discussion_result,
            payoff_results=payoff_results, 
            final_rankings=final_rankings
        )
    
    def _validate_and_sanitize_memory(self, memory: str, character_limit: int, participant_name: str) -> str:
        """
        Validate and sanitize memory for safe Phase 2 initialization.
        
        Args:
            memory: Raw memory string from Phase 1
            character_limit: Maximum allowed characters
            participant_name: Name of participant for logging
            
        Returns:
            Sanitized memory string
        """
        # Check if memory is None or corrupted
        if memory is None:
            self._log_warning(f"Null memory detected for {participant_name}, initializing empty")
            return ""
        
        # Ensure string type
        if not isinstance(memory, str):
            self._log_warning(f"Non-string memory detected for {participant_name}, converting")
            try:
                memory = str(memory)
            except Exception as e:
                self._log_warning(f"Failed to convert memory for {participant_name}: {e}")
                return ""
        
        # Check character limit
        if len(memory) > character_limit:
            self._log_warning(f"Memory exceeds limit for {participant_name}: {len(memory)} > {character_limit}")
            if self.settings.memory_validation_strict:
                # Truncate to fit within limit
                memory = memory[:character_limit - 100]  # Leave some buffer
                memory += "\n[Memory truncated for Phase 2 initialization]"
        
        # Remove any null bytes or control characters that could cause issues
        memory = memory.replace('\x00', '')
        memory = ''.join(char for char in memory if ord(char) >= 32 or char in '\n\r\t')
        
        return memory
    
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
            
            # Validate and sanitize memory before transfer
            validated_memory = self._validate_and_sanitize_memory(
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
            
            # Initialize preference tracking for simple mode (reset each round)
            if config.voting_detection_mode == "simple":
                self._current_round_preferences = {}
            
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
                
                # Check if response is quarantined
                is_quarantined = statement.startswith("__QUARANTINED__")
                if is_quarantined:
                    # Remove quarantine marker for display
                    statement = statement.replace("__QUARANTINED__", "")
                    self._log_warning(f"QUARANTINED RESPONSE for {participant.name} in round {round_num}")
                    self.validation_stats["quarantined_responses"] += 1
                
                # Log statement validation results
                is_fallback = statement.startswith(f"[{participant.name} failed to provide") or is_quarantined
                self._log_info(f"=== STATEMENT RECEIVED FROM {participant.name} ===")
                self._log_info(f"Statement length: {len(statement)} characters")
                self._log_info(f"Is fallback/quarantined: {is_fallback}")
                
                # Log preview for debugging (use settings for length)
                preview_length = self.settings.log_statement_preview_length
                statement_preview = statement[:preview_length] + "..." if len(statement) > preview_length else statement
                self._log_info(f"Statement preview: {statement_preview}")
                
                # Add statement to discussion (quarantined responses get neutral message)
                if not is_quarantined or not self.settings.quarantine_failed_responses:
                    discussion_state.add_statement(participant.name, statement)
                else:
                    # Add neutral message that doesn't reveal failure
                    language_manager = get_language_manager()
                    neutral_msg = language_manager.get("prompts.phase2_agent_unavailable", participant_name=participant.name)
                    discussion_state.add_statement(participant.name, neutral_msg)
                
                # Log discussion round
                if logger:
                    vote_intention = MemoryStateCapture.extract_vote_intention(statement)
                    favored_principle = await self._extract_favored_principle(statement)
                    
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
                
                # CONSENSUS DETECTION WITH PROPER LOCKING
                async with self._consensus_lock:
                    # Check if consensus already reached (could happen in concurrent scenarios)
                    if hasattr(discussion_state, '_consensus_reached') and discussion_state._consensus_reached:
                        self._log_info("Consensus already reached, skipping further detection")
                        return discussion_state._consensus_result
                    
                    # Check voting detection mode
                    if config.voting_detection_mode == "complex":
                        # Try complex voting detection only if not already voting
                        if not self._voting_in_progress:
                            consensus_via_voting = await self._handle_complex_voting_mode(
                                participant, statement, discussion_state, contexts
                            )
                            
                            if consensus_via_voting and discussion_state.last_vote_result:
                                # Mark consensus as reached to prevent race conditions
                                discussion_state._consensus_reached = True
                                discussion_state._consensus_result = GroupDiscussionResult(
                                    consensus_reached=True,
                                    agreed_principle=discussion_state.last_vote_result.agreed_principle,
                                    final_round=round_num,
                                    discussion_history=discussion_state.public_history,
                                    vote_history=discussion_state.vote_history
                                )
                                return discussion_state._consensus_result
                    
                    elif config.voting_detection_mode == "simple":
                        # Simple mode: Try preference detection for consensus
                        preference = await self.utility_agent.detect_preference_statement(statement)
                        
                        if preference:
                            # Store preference in local round tracking (not in discussion_state)
                            if not hasattr(self, '_current_round_preferences'):
                                self._current_round_preferences = {}
                            self._current_round_preferences[participant.name] = preference
                            
                            self._log_info(f"[PREFERENCE] {participant.name}: {preference.principle.value}")
                            
                            # Check if all participants have stated preferences
                            if len(self._current_round_preferences) == len(self.participants):
                                preferences_list = list(self._current_round_preferences.values())
                                consensus_reached, agreed_preference, warnings = self.utility_agent.check_preference_consensus_simple_mode(preferences_list)
                                
                                if warnings:
                                    for warning in warnings:
                                        self._log_warning(f"Preference consensus warning: {warning}")
                                
                                if consensus_reached:
                                    self._log_info(f"Simple mode consensus reached via preferences: {agreed_preference.principle.value}")
                                    
                                    # Mark that voting/consensus has been triggered (prevents reminder messages)
                                    discussion_state.vote_triggered = True
                                    
                                    # Add consensus message to discussion history
                                    consensus_msg = f"[CONSENSUS] Preference-based consensus reached: {agreed_preference.principle.value}"
                                    if agreed_preference.constraint_amount:
                                        consensus_msg += f" with constraint of ${agreed_preference.constraint_amount:,}"
                                    
                                    if discussion_state.public_history:
                                        discussion_state.public_history += f"\n\n{consensus_msg}"
                                    else:
                                        discussion_state.public_history = consensus_msg
                                    
                                    # Mark consensus as reached to prevent race conditions
                                    discussion_state._consensus_reached = True
                                    discussion_state._consensus_result = GroupDiscussionResult(
                                        consensus_reached=True,
                                        agreed_principle=agreed_preference,
                                        final_round=round_num,
                                        discussion_history=discussion_state.public_history,
                                        vote_history=discussion_state.vote_history
                                    )
                                    return discussion_state._consensus_result
                                
                                # Clear preferences for next round if no consensus
                                self._current_round_preferences = {}
                
                # Continue with discussion if no consensus mechanism applies
            
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
            
            # Add voting reminder after round 3 if no vote has been triggered
            if round_num == 3 and not hasattr(discussion_state, 'vote_triggered'):
                voting_reminder = self._get_voting_reminder_message()
                discussion_state.public_history += f"\n\n[系统提醒] {voting_reminder}"
                self._log_info("Added voting reminder after round 3 - no voting attempts detected")
        
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
        num_participants = len(participant_indices)
        
        # Validate minimum participants
        if num_participants < self.settings.min_agents_for_experiment:
            self._log_warning(f"Only {num_participants} agents, below minimum of {self.settings.min_agents_for_experiment}")
            # Continue anyway but log warning
        
        if not config.randomize_speaking_order or config.speaking_order_strategy == "fixed":
            # Fixed order: same sequence every round, but apply rotation for small groups
            if last_round_finisher is not None and num_participants > 1:
                # Rotate the list to avoid same finisher-starter pattern
                rotation_amount = (round_num - 1) % num_participants
                participant_indices = participant_indices[rotation_amount:] + participant_indices[:rotation_amount]
            return participant_indices
        
        if config.speaking_order_strategy == "random":
            # Random behavior with finisher restriction
            random.shuffle(participant_indices)
            
            # Apply finisher restriction for all group sizes
            if last_round_finisher is not None and num_participants > 1:
                # Find position of last finisher in new order
                if participant_indices[0] == last_round_finisher:
                    if num_participants == 2:
                        # For 2 agents, just swap them
                        participant_indices[0], participant_indices[1] = participant_indices[1], participant_indices[0]
                    else:
                        # For larger groups, find a non-adjacent position
                        # Move the last finisher to middle of the list
                        mid_position = num_participants // 2
                        participant_indices[0], participant_indices[mid_position] = participant_indices[mid_position], participant_indices[0]
        
        elif config.speaking_order_strategy == "conversational":
            # Enhanced conversational order based on discussion flow
            if last_round_finisher is not None and num_participants > 2:
                # Start with someone who hasn't spoken recently
                # Create weighted selection excluding last finisher
                weights = [1.0] * num_participants
                weights[last_round_finisher] = 0.0  # Exclude last finisher from starting
                
                # Weighted random selection for first speaker
                import numpy as np
                probabilities = np.array(weights) / sum(weights)
                first_speaker = np.random.choice(participant_indices, p=probabilities)
                
                # Remove first speaker and shuffle rest
                remaining = [i for i in participant_indices if i != first_speaker]
                random.shuffle(remaining)
                
                participant_indices = [first_speaker] + remaining
            else:
                # Fallback to random for first round or small groups
                random.shuffle(participant_indices)
        
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
            # Log the error
            self._log_warning(f"Agent communication error for {participant.name}: {str(e)}")
            self.validation_stats["fallback_statements"] += 1
            
            # Quarantine failed responses if enabled
            if self.settings.quarantine_failed_responses:
                self.validation_stats["quarantined_responses"] += 1
                # Return a neutral statement that doesn't contaminate discussion
                language_manager = get_language_manager()
                neutral_statement = language_manager.get("prompts.phase2_agent_unavailable", participant_name=participant.name)
                # Mark as quarantined internally
                return f"__QUARANTINED__{neutral_statement}", internal_reasoning
            else:
                # Legacy behavior: include failure message (not recommended)
                fallback_statement = f"[{participant.name} failed to provide a valid response after multiple attempts]"
                return fallback_statement, internal_reasoning
    
    def _get_voting_reminder_message(self) -> str:
        """Get voting reminder message in appropriate language."""
        language_manager = get_language_manager()
        
        # Check current language to provide appropriate reminder
        current_language = getattr(language_manager, 'current_language', 'mandarin')
        
        if current_language == 'mandarin':
            return "提醒：如果你们已经讨论充分，记住只能通过正式投票达成有约束力的协议。说出'我们投票吧'或'我认为我们应该投票'来开始投票程序。"
        elif current_language == 'spanish':
            return "Recordatorio: Si han discutido lo suficiente, recuerden que solo pueden llegar a un acuerdo vinculante a través de votación formal. Digan 'Votemos' o 'Creo que deberíamos votar' para iniciar el proceso de votación."
        else:  # English
            return "Reminder: If you have discussed sufficiently, remember that you can only reach binding agreement through formal voting. Say 'Let's vote' or 'I think we should vote' to begin the voting process."
    
    async def _extract_favored_principle(self, statement: str) -> str:
        """Extract favored principle from participant statement using multilingual parsing."""
        try:
            # First, check for exact Chinese phrase matches to avoid LLM parsing issues
            chinese_mappings = {
                "在最低收入约束条件下最大化平均收入": "maximizing_average_floor_constraint",
                "在范围约束条件下最大化平均收入": "maximizing_average_range_constraint", 
                "最大化最低收入": "maximizing_floor",
                "最大化平均收入": "maximizing_average"
            }
            
            for chinese_term, principle in chinese_mappings.items():
                if chinese_term in statement:
                    self._log_info(f"Direct Chinese mapping found: {chinese_term} -> {principle}")
                    return principle
            
            # Use the utility agent for robust multilingual parsing
            parsed = await self.utility_agent.parse_principle_choice_enhanced(statement)
            # Return the canonical principle key (e.g., "maximizing_floor")
            return parsed.principle.value
        except Exception as e:
            # Log the error for debugging
            self._log_warning(f"Failed to extract principle from statement: {str(e)}")
            # Return a specific unspecified key instead of reusing constraint specification
            language_manager = get_language_manager()
            return language_manager.get("prompts.phase2_favored_principle_unspecified")
    
    
    
    
    
    
    
    
    
    async def _apply_group_principle_and_calculate_payoffs(
        self,
        discussion_result: GroupDiscussionResult,
        config: ExperimentConfiguration
    ) -> tuple[Dict[str, float], Dict[str, str], Dict[str, Dict[str, float]]]:
        """Apply chosen principle or random assignment if no consensus.
        
        Returns:
            tuple: (payoffs dict, assigned_classes dict, alternative_earnings_by_agent dict)
        """
        
        # Generate new distribution set for Phase 2 payoffs
        distribution_set = DistributionGenerator.generate_dynamic_distribution(
            config.distribution_range_phase2
        )
        
        payoffs = {}
        assigned_classes = {}
        consensus_principle = None
        constraint_amount = None
        
        if discussion_result.consensus_reached and discussion_result.agreed_principle:
            # Apply agreed principle
            consensus_principle = discussion_result.agreed_principle
            constraint_amount = consensus_principle.constraint_amount
            
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
        
        # Calculate counterfactual earnings for transparency
        alternative_earnings_by_agent = await self._calculate_phase2_counterfactuals(
            distribution_set, assigned_classes, consensus_principle, constraint_amount
        )
        
        return payoffs, assigned_classes, alternative_earnings_by_agent
    
    async def _calculate_phase2_counterfactuals(
        self,
        distribution_set,
        assigned_classes: Dict[str, str],
        consensus_principle: Optional[PrincipleChoice] = None,
        constraint_amount: Optional[int] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate what each agent would earn under all four principles
        using their assigned income class from Phase 2.
        
        Args:
            distribution_set: The distribution set generated for Phase 2
            assigned_classes: Dict mapping participant names to their assigned income classes
            consensus_principle: The principle chosen by consensus (if any)
            constraint_amount: The constraint amount used (if any)
            
        Returns:
            Dict[agent_name, Dict[principle_key, earnings]]
        """
        from models import JusticePrinciple, PrincipleChoice, IncomeClass
        
        alternative_earnings_by_agent = {}
        
        for participant_name, class_str in assigned_classes.items():
            # Convert string back to enum - handle different formats
            if class_str.startswith('IncomeClass.'):
                # Handle enum string representation like 'IncomeClass.high'
                enum_value = class_str.split('.')[1].lower()
            else:
                # Handle direct value like 'high' or 'MEDIUM HIGH' 
                enum_value = class_str.lower().replace(' ', '_')
            
            assigned_class = IncomeClass(enum_value)
            
            # Use the same method as Phase 1 for calculating counterfactuals
            alternative_earnings = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
                distribution_set.distributions,
                assigned_class,
                constraint_amount
            )
            
            alternative_earnings_by_agent[participant_name] = alternative_earnings
            
        return alternative_earnings_by_agent
    
    async def _build_phase2_detailed_results(
        self,
        participant_name: str,
        final_earnings: float,
        assigned_class: str,
        alternative_earnings: Dict[str, float],
        consensus_result: GroupDiscussionResult
    ) -> str:
        """
        Build detailed Phase 2 results matching Phase 1 transparency level.
        Includes class assignment and full counterfactual analysis.
        """
        from utils.language_manager import get_language_manager
        language_manager = get_language_manager()
        
        # Build consensus status message
        if consensus_result.consensus_reached:
            consensus_status = f"Group reached consensus on {consensus_result.agreed_principle.principle.value}"
            if consensus_result.agreed_principle.constraint_amount:
                consensus_status += f" (${consensus_result.agreed_principle.constraint_amount:,})"
        else:
            consensus_status = "Group did not reach consensus. Earnings were randomly assigned"
        
        # Format the class name for display
        class_display_map = {
            "very_high": "VERY HIGH",
            "high": "HIGH",
            "medium": "MEDIUM",
            "low": "LOW",
            "very_low": "VERY LOW"
        }
        formatted_class = class_display_map.get(assigned_class.lower(), assigned_class)
        
        # Build the header
        result_content = f"""PHASE 2 FINAL RESULTS

Consensus Status: {consensus_status}
Your Income Class Assignment: {formatted_class}
Your Earnings: ${final_earnings:.2f}

COUNTERFACTUAL ANALYSIS - What you would have earned under each principle:"""
        
        # Get principle display names
        principle_display_names = {
            "maximizing_floor": language_manager.get("common.principle_names.maximizing_floor"),
            "maximizing_average": language_manager.get("common.principle_names.maximizing_average"),
            "maximizing_average_floor_constraint": language_manager.get("common.principle_names.maximizing_average_floor_constraint"),
            "maximizing_average_range_constraint": language_manager.get("common.principle_names.maximizing_average_range_constraint")
        }
        
        # Add table header
        result_content += """
┌─────────────────────────────────────────┬──────────┬──────────┐
│ Justice Principle                       │ Income   │ Earnings │
├─────────────────────────────────────────┼──────────┼──────────┤"""
        
        # Add each principle's earnings
        for principle_key, alt_earnings in alternative_earnings.items():
            principle_name = principle_display_names.get(principle_key, principle_key)
            # Calculate income from earnings (reverse the payoff calculation)
            alt_income = int(alt_earnings * 10000)  # Convert earnings back to income
            
            result_content += f"\n│ {principle_name:<39} │ ${alt_income:,}".ljust(9) + f" │ ${alt_earnings:.2f}".ljust(8) + " │"
        
        # Close the table
        result_content += "\n└─────────────────────────────────────────┴──────────┴──────────┘"
        
        # Add key insights
        if alternative_earnings:
            current_earnings = final_earnings
            best_earnings = max(alternative_earnings.values())
            worst_earnings = min(alternative_earnings.values())
            
            # Find which principles gave best/worst outcomes
            best_principle = next(k for k, v in alternative_earnings.items() if v == best_earnings)
            worst_principle = next(k for k, v in alternative_earnings.items() if v == worst_earnings)
            
            best_principle_name = principle_display_names.get(best_principle, best_principle)
            worst_principle_name = principle_display_names.get(worst_principle, worst_principle)
            
            best_diff = best_earnings - current_earnings
            worst_diff = current_earnings - worst_earnings
            
            result_content += f"\n\nKey Insights:"
            
            if best_diff > 0:
                result_content += f"\n- Best alternative: Would have earned ${best_diff:.2f} more under {best_principle_name}"
            elif best_diff == 0:
                result_content += f"\n- Best alternative: Current earnings match the best possible outcome"
            else:
                result_content += f"\n- Best alternative: All other principles would have yielded less"
                
            if worst_diff > 0:
                result_content += f"\n- Worst alternative: Would have earned ${worst_diff:.2f} less under {worst_principle_name}"
            elif worst_diff == 0:
                result_content += f"\n- Worst alternative: Current earnings match the worst possible outcome"
        
        return result_content
    
    async def _collect_final_rankings(
        self,
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        assigned_classes: Dict[str, str],
        alternative_earnings_by_agent: Dict[str, Dict[str, float]],
        config: ExperimentConfiguration,
        logger: AgentCentricLogger = None
    ) -> Dict[str, PrincipleRanking]:
        """Collect final principle rankings from all participants."""
        
        final_ranking_tasks = []
        
        for i, participant in enumerate(self.participants):
            context = contexts[i]
            agent_config = config.agents[i]
            
            # Update context with final results using agent-managed memory - Enhanced transparency
            final_earnings = payoff_results[participant.name]
            assigned_class = assigned_classes[participant.name]
            alternative_earnings = alternative_earnings_by_agent[participant.name]
            
            # Check transparency configuration
            transparency_config = getattr(config, 'phase2_enhanced_transparency', None)
            use_enhanced_transparency = (
                transparency_config is None or  # Default to enhanced if not configured
                (transparency_config and transparency_config.enabled)
            )
            
            if use_enhanced_transparency:
                # Build detailed results matching Phase 1 transparency level
                result_content = await self._build_phase2_detailed_results(
                    participant.name,
                    final_earnings,
                    assigned_class,
                    alternative_earnings,
                    discussion_result
                )
            else:
                # Use basic results (original behavior)
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
        
        # Generate dynamic participant information
        num_participants = len(self.participants)
        participant_names = [participant.name for participant in self.participants]
        
        if num_participants == 1:
            group_participants = f"The current group consists of 1 participant: {participant_names[0]}"
        elif num_participants == 2:
            group_participants = f"The current group consists of 2 participants: {participant_names[0]} and {participant_names[1]}"
        else:
            # For 3 or more participants: "Name1, Name2, and Name3"
            names_except_last = ", ".join(participant_names[:-1])
            group_participants = f"The current group consists of {num_participants} participants: {names_except_last}, and {participant_names[-1]}"
        
        # Use different prompts based on voting detection mode
        if self.config.voting_detection_mode == "complex":
            # For complex mode: allow voting proposals
            base_prompt = language_manager.get("prompts.phase2_discussion_prompt_complex",
                                              round_number=round_num,
                                              max_rounds=self.config.phase2_rounds,
                                              discussion_history=discussion_state.public_history or "No previous discussion.",
                                              group_participants=group_participants)
        else:
            # For simple mode: use preference-based consensus (FIXED to use correct prompt)
            base_prompt = language_manager.get("prompts.phase2_discussion_prompt_simple",
                                              round_number=round_num,
                                              max_rounds=self.config.phase2_rounds,
                                              discussion_history=discussion_state.public_history or "No previous discussion.",
                                              group_participants=group_participants)
        
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
        
        # Ensure we're not already in a voting process (prevent double voting)
        if self._voting_in_progress:
            self._log_info("Voting already in progress, skipping new vote detection")
            return False
        
        # Check if voting intention is detected using existing method
        vote_detection_result = await self.utility_agent.detect_vote_intention_enhanced(statement)
        
        if vote_detection_result is None:
            return False  # No voting intention detected
        
        self._log_info(f"Complex voting intention detected from {participant.name}")
        
        # Mark that voting has been triggered (prevents reminder messages)
        discussion_state.vote_triggered = True
        
        # Set voting flag to prevent concurrent votes
        self._voting_in_progress = True
        
        try:
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
            
            # Step A: Confirmation Phase with timeout
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
                return False
            
            # Step B: Secret Ballot Phase
            consensus_reached = await self._conduct_secret_ballot_phase(
                contexts, discussion_state
            )
        finally:
            # Always reset voting flags
            self._voting_in_progress = False
            discussion_state.active_vote_in_progress = False
        
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
            
            # Get confirmation response from participant with timeout
            try:
                result = await asyncio.wait_for(
                    Runner.run(participant.agent, confirmation_prompt, context=context),
                    timeout=self.settings.confirmation_timeout_seconds
                )
                confirmation_response = result.final_output
            except asyncio.TimeoutError:
                self._log_warning(f"Timeout waiting for confirmation from {participant.name}")
                confirmation_response = f"[{participant.name} timed out during confirmation]"
            
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
            
            # Update participant memory with their confirmation response
            confirmation_content = f"""Voting Confirmation Round {discussion_state.round_number}:
You were asked if you agree to proceed with voting on justice principles.
Your response: {confirmation_response}
Outcome: {'Agreed to proceed with voting' if agrees_to_vote else 'Declined to vote'}"""
            
            # Extract configuration for memory guidance
            memory_guidance_style = self.config.memory_guidance_style if self.config else "narrative"
            
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, confirmation_content, memory_guidance_style=memory_guidance_style
            )
            
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
            
            # Get secret ballot from participant with timeout
            try:
                result = await asyncio.wait_for(
                    Runner.run(participant.agent, ballot_prompt, context=context),
                    timeout=self.settings.ballot_timeout_seconds
                )
                ballot_response = result.final_output
            except asyncio.TimeoutError:
                self._log_warning(f"Timeout waiting for ballot from {participant.name}")
                ballot_response = f"[{participant.name} timed out during ballot]"
            
            # Parse ballot using existing utility agent methods
            try:
                principle_choice = await self.utility_agent.parse_principle_choice_enhanced(ballot_response)
                
                # Validation: Check if ballot mentions principle c/d explicitly
                ballot_lower = ballot_response.lower()
                if 'principle c' in ballot_lower or 'floor constraint' in ballot_lower:
                    expected = JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
                    if principle_choice.principle != expected:
                        self._log_warning(f"PARSING ERROR: Ballot says 'principle c/floor constraint' but parsed as {principle_choice.principle.value}")
                        self._log_warning(f"Correcting principle for {participant.name} from {principle_choice.principle.value} to {expected.value}")
                        principle_choice.principle = expected
                elif 'principle d' in ballot_lower or 'range constraint' in ballot_lower:
                    expected = JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
                    if principle_choice.principle != expected:
                        self._log_warning(f"PARSING ERROR: Ballot says 'principle d/range constraint' but parsed as {principle_choice.principle.value}")
                        self._log_warning(f"Correcting principle for {participant.name} from {principle_choice.principle.value} to {expected.value}")
                        principle_choice.principle = expected
                
                ballots.append(principle_choice)
                self._log_info(f"Secret ballot received from {participant.name}: {principle_choice.principle.value} (constraint: ${principle_choice.constraint_amount if principle_choice.constraint_amount else 'None'})")
                
                # Update participant memory with their ballot choice
                ballot_content = f"""Secret Ballot Vote Round {discussion_state.round_number}:
You cast a secret ballot for a justice principle.
Your vote: {principle_choice.principle.value}
{f'With constraint: ${principle_choice.constraint_amount:,}' if principle_choice.constraint_amount else 'No specific constraint amount'}
Outcome: Vote recorded (secret ballot - results pending)"""
                
                # Extract configuration for memory guidance
                memory_guidance_style = self.config.memory_guidance_style if self.config else "narrative"
                
                context.memory = await MemoryManager.prompt_agent_for_memory_update(
                    participant, context, ballot_content, memory_guidance_style=memory_guidance_style
                )
                
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
            # Analyze disagreement type and provide specific feedback
            disagreement_message = self._analyze_ballot_disagreement(ballots)
            discussion_state.public_history += f"\n[VOTING RESULT] {disagreement_message}"
        
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
    
    def _analyze_ballot_disagreement(self, ballots: List[PrincipleChoice]) -> str:
        """
        Analyze the nature of disagreement in failed ballot consensus.
        
        Returns a localized message describing the specific type of disagreement:
        - Principle disagreement: agents voted for different principles
        - Constraint disagreement: agents agreed on principle but differed on constraint amounts
        - Mixed disagreement: combination of principle and constraint disagreements
        
        Args:
            ballots: List of ballot choices from all participants
            
        Returns:
            Localized announcement message describing the disagreement type
        """
        from utils.language_manager import get_language_manager
        language_manager = get_language_manager()
        
        if not ballots:
            # Fallback to generic message if no ballots
            return language_manager.get("prompts.phase2_voting_no_consensus_mixed_disagreement")
        
        # Group ballots by principle only (ignoring constraint amounts)
        principle_groups = {}
        for ballot in ballots:
            principle = ballot.principle.value
            if principle not in principle_groups:
                principle_groups[principle] = []
            principle_groups[principle].append(ballot)
        
        # Analyze disagreement patterns
        if len(principle_groups) == 1:
            # All agents agreed on the same principle but disagreed on constraints
            principle_name = list(principle_groups.keys())[0]
            
            # Get display name for the agreed principle
            principle_display_names = {
                "maximizing_floor": language_manager.get("common.principle_names.maximizing_floor"),
                "maximizing_average": language_manager.get("common.principle_names.maximizing_average"),
                "maximizing_average_floor_constraint": language_manager.get("common.principle_names.maximizing_average_floor_constraint"),
                "maximizing_average_range_constraint": language_manager.get("common.principle_names.maximizing_average_range_constraint")
            }
            
            principle_display_name = principle_display_names.get(principle_name, principle_name)
            
            return language_manager.get(
                "prompts.phase2_voting_no_consensus_constraint_disagreement",
                principle_name=principle_display_name
            )
            
        elif len(principle_groups) == len(ballots):
            # Every agent voted for a different principle - complete principle disagreement
            return language_manager.get("prompts.phase2_voting_no_consensus_principle_disagreement")
            
        else:
            # Mixed situation: some agents agreed on principles, others disagreed
            # This could happen when there are multiple small groups with principle agreement
            # but disagreement between groups
            return language_manager.get("prompts.phase2_voting_no_consensus_mixed_disagreement")
    
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
