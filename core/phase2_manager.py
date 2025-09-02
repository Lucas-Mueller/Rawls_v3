"""
Phase 2 manager for group discussion and consensus building.
"""
import asyncio
import random
import re
import time
from typing import List, Dict, Optional
from agents import Agent, Runner
try:
    from agents.items import ToolCallItem, ToolCallOutputItem
    HAS_SDK_TYPES = True
except ImportError:
    HAS_SDK_TYPES = False

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
from utils.simple_memory_manager import SimpleMemoryManager
from utils.selective_memory_manager import SelectiveMemoryManager, MemoryEventType
from utils.agent_centric_logger import AgentCentricLogger, MemoryStateCapture
from utils.error_handling import AgentCommunicationError, ErrorSeverity, ExperimentErrorHandler
from core.two_stage_voting_manager import TwoStageVotingManager


class Phase2Manager:
    """Manages Phase 2 group discussion and consensus building."""
    
    def __init__(self, participants: List[ParticipantAgent], utility_agent: UtilityAgent, experiment_config=None, language_manager=None, error_handler=None, seed_manager=None):
        self.participants = participants
        self.utility_agent = utility_agent
        self.config = experiment_config
        self.language_manager = language_manager
        self.seed_manager = seed_manager
        self.logger = None  # Will be set in run_phase2
        # Use provided error handler or create a new one
        self.error_handler = error_handler if error_handler is not None else ExperimentErrorHandler()
        
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
    
    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message with fallback handling."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self._log_warning(f"Missing translation key: {key} - {str(e)}")
            # Return English fallback or key name
            return f"[MISSING: {key}]"
    
    def _format_voting_tag_message(self, tag_key: str, message_key: str = None, **kwargs) -> str:
        """Format voting system messages with consistent tagging."""
        tag = self._get_localized_message(f"system_messages.voting.{tag_key}")
        if message_key:
            message = self._get_localized_message(f"system_messages.voting.{message_key}", **kwargs)
            return f"{tag} {message}"
        return tag
    
    def _format_group_composition(self, participants: List[str]) -> str:
        """Format group composition message with proper localization."""
        participant_list = ", ".join(participants[:-1]) + f" and {participants[-1]}" if len(participants) > 1 else participants[0]
        return self._get_localized_message(
            "system_messages.discussion.group_composition", 
            participants=participant_list
        )
    
    def _get_localized_income_class(self, income_class: str) -> str:
        """Get localized income class label."""
        return self._get_localized_message(f"common.income_classes.{income_class}")
    
    
    def _validate_constraint_amount(self, constraint_amount: Optional[int], participant_name: str = None) -> bool:
        """
        Validate that constraint amounts are in a reasonable range.
        
        Args:
            constraint_amount: The constraint amount to validate
            participant_name: Name of participant for logging (optional)
            
        Returns:
            True if valid or None, False if invalid
        """
        if constraint_amount is None:
            return True  # No constraint is valid
        
        # Define reasonable bounds based on typical income distributions
        MIN_REASONABLE_CONSTRAINT = 10    # $1,000
        MAX_REASONABLE_CONSTRAINT = 1000000000  # $100,000
        
        # Check for suspiciously small amounts (likely payoff scale errors)
        LIKELY_PAYOFF_SCALE_MAX = 10  # $10 is likely a payoff amount, not income constraint
        
        if constraint_amount < MIN_REASONABLE_CONSTRAINT:
            participant_info = f" for {participant_name}" if participant_name else ""
            if constraint_amount <= LIKELY_PAYOFF_SCALE_MAX:
                self._log_warning(f"Constraint amount ${constraint_amount}{participant_info} appears to be in payoff scale ($1-$10) rather than income scale ($10,000-$30,000)")
            else:
                self._log_warning(f"Constraint amount ${constraint_amount}{participant_info} is below reasonable minimum of ${MIN_REASONABLE_CONSTRAINT:,}")
            return False
        
        if constraint_amount > MAX_REASONABLE_CONSTRAINT:
            participant_info = f" for {participant_name}" if participant_name else ""
            self._log_warning(f"Constraint amount ${constraint_amount:,}{participant_info} exceeds reasonable maximum of ${MAX_REASONABLE_CONSTRAINT:,}")
            return False
        
        return True
    
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
    ) -> tuple[str, str, dict]:
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
            tuple: (statement, round_content, tool_call_info)
            
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
                    # Set interaction type for public statement (enables propose_vote tool)
                    context.interaction_type = "public_statement"
                    result = await asyncio.wait_for(
                        Runner.run(participant.agent, discussion_prompt, context=context),
                        timeout=self.settings.statement_timeout_seconds
                    )
                    statement = result.final_output
                    
                    # Tool detection removed - no more tool calls to check
                    has_tool_call, tool_call_info = False, {}
                    
                except asyncio.TimeoutError:
                    self._log_warning(f"Timeout waiting for {participant.name} after {self.settings.statement_timeout_seconds}s")
                    statement = ""  # Treat timeout as empty response
                    has_tool_call, tool_call_info = False, {}
                
                # Validate the statement (or allow empty if there's a tool call)
                if self._validate_statement(statement, participant.name) or has_tool_call:
                    # Update statistics
                    self.validation_stats["successful_statements"] += 1
                    if attempt > 0:
                        self.validation_stats["retry_attempts"] += attempt
                    
                    # Create round content for memory
                    language_manager = self.language_manager
                    
                    # Include tool call information in memory if present
                    if has_tool_call:
                        tool_action = f" (Used {tool_call_info.get('tool_name', 'tool')} tool)"
                        outcome_key = 'memory_outcomes.made_discussion_statement_with_tool'
                    else:
                        tool_action = ""
                        outcome_key = 'memory_outcomes.made_discussion_statement'
                    
                    round_content = f"""{language_manager.get('memory_field_labels.prompt')} {discussion_prompt}
{language_manager.get('memory_field_labels.your_statement')} {statement}{tool_action}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get(outcome_key, round_number=context.round_number)}"""
                    
                    if attempt > 0:
                        self._log_info(f"Valid statement received from {participant.name} after {attempt + 1} attempts")
                    
                    if has_tool_call:
                        self._log_info(f"Tool call detected: {tool_call_info}")
                    
                    return statement, round_content, tool_call_info
                else:
                    # Statement validation failed
                    self.validation_stats["failed_validations"] += 1
                    
                    if attempt < max_retries - 1:
                        self._log_warning(f"Invalid statement from {participant.name}, retrying... (attempt {attempt + 1}/{max_retries})")
                        
                        # Modify prompt for retry to be more explicit
                        language_manager = self.language_manager
                        discussion_prompt = f"""
{language_manager.get('error_messages.empty_response_retry')}

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
        logger: AgentCentricLogger = None,
        process_logger=None
    ) -> Phase2Results:
        """Execute complete Phase 2 group discussion."""
        
        # Store logger for use in consensus methods
        self.logger = logger
        
        
        # Initialize voting history tracking if logger is provided
        if logger:
            logger.initialize_voting_history()
        
        # CRITICAL: Initialize participants with CONTINUOUS memory from Phase 1
        participant_contexts = self._initialize_phase2_contexts(phase1_results, config)
        
        # Group discussion
        discussion_result = await self._run_group_discussion(
            config, participant_contexts, logger, process_logger
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
        
        # Log memory size but don't truncate - let memory manager handle overflow
        if len(memory) > character_limit:
            self._log_info(f"Memory exceeds base limit for {participant_name}: {len(memory)} > {character_limit} (will be handled by memory manager)")
        
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
        logger: AgentCentricLogger = None,
        process_logger=None
    ) -> GroupDiscussionResult:
        """Run sequential group discussion with voting."""
        
        discussion_state = GroupDiscussionState()
        # Set valid participants for isolation protection
        discussion_state.valid_participants = [agent.name for agent in config.agents]
        last_round_finisher = None
        
        for round_num in range(1, config.phase2_rounds + 1):
            discussion_state.round_number = round_num
            
            # Always use complex voting mode
            
            # Generate speaking order based on configuration
            speaking_order = self._generate_speaking_order(round_num, contexts, config, last_round_finisher)
            
            if process_logger:
                speaking_names = [self.participants[i].name for i in speaking_order]
                process_logger.phase2_round_start(round_num, config.phase2_rounds, speaking_names)
                round_start_time = time.time()
            # Track who finishes this round (last speaker)
            current_round_finisher = speaking_order[-1]
            
            # Track participants who spoke in this round for logging consistency validation
            round_participants_logged = set()
            
            # Track recent statements for vote consistency
            participant_recent_statements = {}
            
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
                if process_logger:
                    process_logger.phase2_agent_speaking(participant.name, round_num)
                    
                self._log_info(f"=== REQUESTING STATEMENT FROM {participant.name} ===")
                self._log_info(f"Round {round_num}, Speaking position {speaking_order_position + 1}")
                
                start_time = time.time()
                statement, internal_reasoning, tool_call_info = await self._get_participant_statement_enhanced(
                    participant, context, discussion_state, agent_config
                )
                response_time = time.time() - start_time
                
                # Store recent statement for vote consistency (before any quarantine processing)
                participant_recent_statements[participant.name] = statement
                
                # Check if response is quarantined
                is_quarantined = statement.startswith("__QUARANTINED__")
                if is_quarantined:
                    # Remove quarantine marker for display
                    statement = statement.replace("__QUARANTINED__", "")
                    self._log_warning(f"QUARANTINED RESPONSE for {participant.name} in round {round_num}")
                    self.validation_stats["quarantined_responses"] += 1
                
                # Log response completion
                if process_logger:
                    process_logger.phase2_agent_response(participant.name, len(statement), response_time)
                
                # Log statement validation results
                is_fallback = statement.startswith(f"[{participant.name} failed to provide") or is_quarantined
                self._log_info(f"=== STATEMENT RECEIVED FROM {participant.name} ===")
                self._log_info(f"Statement length: {len(statement)} characters")
                self._log_info(f"Is fallback/quarantined: {is_fallback}")
                
                # Log preview for debugging (use settings for length)
                preview_length = self.settings.log_statement_preview_length
                statement_preview = statement[:preview_length] + "..." if len(statement) > preview_length else statement
                self._log_info(f"Statement preview: {statement_preview}")
                
                # Manage discussion history length before adding new content
                self._manage_discussion_history_length(discussion_state)
                
                # Add statement to discussion (quarantined responses get neutral message)
                if not is_quarantined or not self.settings.quarantine_failed_responses:
                    discussion_state.add_statement(participant.name, statement, self.language_manager)
                else:
                    # Add neutral message that doesn't reveal failure
                    language_manager = self.language_manager
                    neutral_msg = language_manager.get("prompts.phase2_agent_unavailable", participant_name=participant.name)
                    discussion_state.add_statement(participant.name, neutral_msg, self.language_manager)
                
                # Log discussion round
                if logger:
                    favored_principle = await self._extract_favored_principle(statement)
                    
                    logger.log_discussion_round(
                        participant.name,
                        round_num,
                        speaking_order_position + 1,  # 1-indexed speaking order
                        internal_reasoning,
                        statement,
                        "N/A",  # Vote intention detection removed - using formal voting system instead
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
                    include_internal_reasoning=include_reasoning,
                    favored_principle=favored_principle
                )
                
                # Update participant memory using selective routing for optimization
                context.memory = await SelectiveMemoryManager.update_memory_selective(
                    agent=participant, 
                    context=context, 
                    content=round_content, 
                    event_type=MemoryEventType.DISCUSSION_STATEMENT,
                    event_metadata={'round_number': round_num, 'participant_name': participant.name},
                    config=self.config,
                    language_manager=self.language_manager, 
                    error_handler=self.error_handler, 
                    utility_agent=self.utility_agent,
                    memory_guidance_style=memory_guidance_style
                )
                contexts[participant_idx] = update_participant_context(
                    context, new_round=round_num
                )
                context = contexts[participant_idx]  # Update local reference to new context
                
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
                    
                    # Formal voting system uses prompt-based initiation only
                    # No automatic voting triggers from agent statements
                
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
            
            # Enhanced end-of-round vote prompting phase
            self._log_info(f"🗳️  Starting end-of-round vote prompting for round {round_num}")
            vote_initiation_successful = False
            vote_responses = {}  # Track all responses for analytics
            
            for participant_idx, participant in enumerate(self.participants):
                context = contexts[participant_idx]
                
                # Enhanced vote initiation prompting with comprehensive logging
                self._log_info(f"🔔 Prompting {participant.name} for vote initiation (participant {participant_idx + 1}/{len(self.participants)})")
                
                try:
                    # Get agent's recent statement for consistency
                    recent_statement = participant_recent_statements.get(participant.name, "")
                    wants_vote = await self._prompt_for_vote_initiation(participant, context, recent_statement)
                    vote_responses[participant.name] = wants_vote
                    
                    # Add simple memory insertion for vote initiation decision
                    SimpleMemoryManager.insert_vote_initiation_decision(
                        contexts[participant_idx], round_num, wants_vote, self.language_manager
                    )
                    
                    if wants_vote:
                        self._log_info(f"✅ {participant.name} wants to initiate voting - starting formal voting process")
                        
                        # Enhanced voting process with better error recovery
                        try:
                            if process_logger:
                                process_logger.phase2_voting_initiated(round_num)
                                
                            consensus_reached = await self._conduct_voting_process(
                                participant, contexts, discussion_state
                            )
                            
                            vote_initiation_successful = True
                            
                            if consensus_reached:
                                # Successful consensus through voting
                                self._log_info(f"🎉 Consensus reached through {participant.name}'s initiated voting - ending discussion")
                                # Log vote initiation analytics
                                self._log_info(f"📊 Vote Initiation Analytics: {participant.name} successfully led group to consensus")
                                
                                if process_logger:
                                    agreed_principle = discussion_state._consensus_result.agreed_principle.principle.value if discussion_state._consensus_result.agreed_principle else None
                                    constraint_amount = discussion_state._consensus_result.agreed_principle.constraint_amount if discussion_state._consensus_result.agreed_principle else None
                                    process_logger.phase2_voting_result(True, agreed_principle, constraint_amount, round_num)
                                    
                                return discussion_state._consensus_result
                            else:
                                # Voting failed to reach consensus
                                self._log_info(f"❌ No consensus reached through {participant.name}'s initiated voting - continuing discussion")
                                # Log analytics for failed voting attempt
                                self._log_info(f"📊 Vote Failure Analytics: {participant.name} initiated voting but consensus not reached")
                                
                                if process_logger:
                                    process_logger.phase2_voting_result(False, None, None, round_num)
                                
                        except Exception as voting_error:
                            self._log_warning(f"🚨 Error during voting process initiated by {participant.name}: {str(voting_error)}")
                            # Continue with next participant even if voting process fails
                            continue
                            
                        # Exit the vote prompting loop after first vote attempt (successful or not)
                        break
                        
                    else:
                        self._log_info(f"⏭️  {participant.name} wants to continue discussion")
                        
                except Exception as prompt_error:
                    self._log_warning(f"🚨 Error during vote prompting for {participant.name}: {str(prompt_error)}")
                    vote_responses[participant.name] = None  # Mark as failed
                    # Continue to next participant
                    continue
            
            # Log comprehensive vote prompting summary
            if not vote_initiation_successful:
                continue_count = sum(1 for response in vote_responses.values() if response is False)
                failed_count = sum(1 for response in vote_responses.values() if response is None)
                
                self._log_info(f"📊 End-of-round vote summary for round {round_num}:")
                self._log_info(f"   • Participants wanting to continue discussion: {continue_count}")
                self._log_info(f"   • Participants with prompt failures: {failed_count}")
                self._log_info(f"   • Result: Continuing to next round")
            else:
                self._log_info(f"📊 End-of-round vote summary for round {round_num}: Voting was initiated")
                
            # Log vote initiation requests to voting history
            if self.logger:
                # Convert None responses to "Error" for logging
                clean_responses = {}
                for agent_name, response in vote_responses.items():
                    if response is True:
                        clean_responses[agent_name] = "Yes"
                    elif response is False:
                        clean_responses[agent_name] = "No"
                    else:
                        clean_responses[agent_name] = "Error"
                self.logger.log_round_vote_requests(round_num, clean_responses)
                
            # Log round completion for ProcessFlowLogger
            if process_logger:
                round_duration = time.time() - round_start_time if 'round_start_time' in locals() else 0.0
                process_logger.phase2_round_complete(round_num, round_duration)
            
        
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
            if self.seed_manager:
                self.seed_manager.random.shuffle(participant_indices)
            else:
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
                if self.seed_manager:
                    self.seed_manager.random.shuffle(remaining)
                else:
                    random.shuffle(remaining)
                
                participant_indices = [first_speaker] + remaining
            else:
                # Fallback to random for first round or small groups
                if self.seed_manager:
                    self.seed_manager.random.shuffle(participant_indices)
                else:
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
        language_manager = self.language_manager
        round_content = f"""{language_manager.get('memory_field_labels.prompt')} {discussion_prompt}
{language_manager.get('memory_field_labels.your_statement')} {statement}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.made_discussion_statement', round_number=context.round_number)}"""
        
        return statement, round_content

    async def _get_participant_statement_enhanced(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        discussion_state: GroupDiscussionState,
        agent_config: AgentConfiguration
    ) -> tuple[str, str, dict]:
        """Get participant's statement with internal reasoning. Returns (statement, internal_reasoning, tool_call_info)."""
        
        # If reasoning is enabled, ask for internal reasoning first
        internal_reasoning = ""
        if agent_config.reasoning_enabled:
            try:
                reasoning_prompt = self._build_internal_reasoning_prompt(discussion_state, context.round_number)
                reasoning_result = await asyncio.wait_for(
                    Runner.run(participant.agent, reasoning_prompt, context=context),
                    timeout=self.settings.statement_timeout_seconds
                )
                internal_reasoning = reasoning_result.final_output
                
                # Tool calls during reasoning are now tracked via global state
                # No need to detect them here - they'll be picked up after statement processing
                    
            except Exception as e:
                # Log reasoning timeout/error but continue with empty reasoning
                # This catches all exceptions including TimeoutError, asyncio.TimeoutError, etc.
                self._log_warning(f"Reasoning timeout/error for {participant.name}: {str(e)}")
                internal_reasoning = ""
        
        # Get public statement with validation and retry logic
        try:
            statement, _, tool_call_info = await self._get_participant_statement_with_retry(
                participant, context, discussion_state, agent_config, internal_reasoning
            )
            
            # Tool calls are now tracked via global state - no need to detect from results
            return statement, internal_reasoning, tool_call_info
            
        except AgentCommunicationError as e:
            # Log the error
            self._log_warning(f"Agent communication error for {participant.name}: {str(e)}")
            self.validation_stats["fallback_statements"] += 1
            
            # Quarantine failed responses if enabled
            if self.settings.quarantine_failed_responses:
                self.validation_stats["quarantined_responses"] += 1
                # Return a neutral statement that doesn't contaminate discussion
                language_manager = self.language_manager
                neutral_statement = language_manager.get("prompts.phase2_agent_unavailable", participant_name=participant.name)
                # Mark as quarantined internally
                return f"__QUARANTINED__{neutral_statement}", internal_reasoning, {}
            else:
                # Legacy behavior: include failure message (not recommended)
                fallback_statement = f"[{participant.name} failed to provide a valid response after multiple attempts]"
                return fallback_statement, internal_reasoning, {}

    async def _prompt_for_vote_initiation(
        self,
        participant: 'ParticipantAgent',
        context: ParticipantContext,
        agent_recent_statement: str = None,
        max_retries: int = 3
    ) -> bool:
        """
        Enhanced vote initiation prompting with recent statement context.
        
        Args:
            participant: The participant agent to prompt
            context: The participant's context
            agent_recent_statement: Agent's recent statement for consistency (optional)
            max_retries: Maximum number of retry attempts for invalid responses
            
        Returns:
            True if agent wants to vote, False otherwise
        """
        language_manager = self.language_manager
        
        # Use enhanced prompt with statement context if available
        if agent_recent_statement and agent_recent_statement.strip():
            vote_prompt = language_manager.get(
                "prompts.vote_initiation_with_statement_prompt",
                agent_recent_statement=agent_recent_statement
            )
        else:
            vote_prompt = language_manager.get("prompts.vote_initiation_prompt")
        
        # Enhanced timeout specifically for vote prompts (shorter than statement timeout)
        vote_prompt_timeout = min(self.settings.statement_timeout_seconds, 60)  # Cap at 60 seconds
        
        for attempt in range(max_retries):
            try:
                # Set interaction type for vote prompting
                context.interaction_type = "vote_prompt"
                
                # Add attempt information to logging for retries
                if attempt > 0:
                    self._log_info(f"Vote prompt retry {attempt + 1}/{max_retries} for {participant.name}")
                    # Add gentle retry instruction for subsequent attempts
                    retry_prompt = f"{vote_prompt}\n\n{self._get_localized_message('voting_prompts.retry_instruction')}"
                else:
                    retry_prompt = vote_prompt
                
                result = await asyncio.wait_for(
                    Runner.run(participant.agent, retry_prompt, context=context),
                    timeout=vote_prompt_timeout
                )
                response = result.final_output.strip()
                
                # Enhanced logging for debugging
                self._log_info(f"Vote prompt response from {participant.name} (attempt {attempt + 1}): '{response[:50]}{'...' if len(response) > 50 else ''}'")
                
                # Use numerical agreement detection (1=Yes, 0=No)
                wants_vote, parse_error = self.utility_agent.detect_numerical_agreement(response)
                
                if parse_error is not None:
                    # Invalid response - try retry if attempts remain
                    self._log_warning(f"Invalid vote prompt response from {participant.name}: {parse_error}")
                    if attempt < max_retries - 1:
                        continue  # Try again with clearer prompt
                    else:
                        # All retries exhausted - default to No (continue discussion)
                        self._log_warning(f"All vote prompt retries exhausted for {participant.name}, defaulting to continue discussion")
                        return False
                
                # Successful response
                result_text = 'Yes' if wants_vote else 'No'
                self._log_info(f"✅ Vote initiation prompt result for {participant.name}: {result_text}")
                
                # Additional logging for analytics
                if wants_vote:
                    self._log_info(f"📊 Vote Analytics: {participant.name} chose to initiate voting (attempt {attempt + 1})")
                else:
                    self._log_info(f"📊 Vote Analytics: {participant.name} chose to continue discussion (attempt {attempt + 1})")
                    
                return wants_vote
                
            except asyncio.TimeoutError:
                self._log_warning(f"Vote prompt timeout for {participant.name} (attempt {attempt + 1}/{max_retries}, {vote_prompt_timeout}s timeout)")
                if attempt < max_retries - 1:
                    continue  # Try again with same timeout
                else:
                    # Final timeout - default to continue discussion
                    self._log_warning(f"Final vote prompt timeout for {participant.name}, defaulting to continue discussion")
                    return False
                    
            except Exception as e:
                self._log_warning(f"Error during vote prompting for {participant.name} (attempt {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    # Wait a bit before retry to handle transient errors
                    await asyncio.sleep(1.0)
                    continue
                else:
                    # Final error - default to continue discussion
                    self._log_warning(f"Final vote prompt error for {participant.name}, defaulting to continue discussion")
                    return False
        
        # Should not reach here, but safety fallback
        self._log_warning(f"Unexpected end of vote prompt method for {participant.name}, defaulting to continue discussion")
        return False

    async def _conduct_voting_process(
        self,
        initiator: 'ParticipantAgent',
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState
    ) -> bool:
        """
        Conduct complete voting process using existing infrastructure.
        
        Args:
            initiator: Agent who initiated the vote
            contexts: All participant contexts
            discussion_state: Current discussion state
            
        Returns:
            True if consensus reached, False otherwise
        """
        # Mark voting as triggered
        discussion_state.vote_triggered = True
        self._voting_in_progress = True
        
        try:
            # Log voting initiation
            if self.logger:
                self.logger.start_vote_round(
                    round_number=discussion_state.round_number,
                    vote_type="prompted_vote",
                    trigger_participant=initiator.name,
                    trigger_statement=f"Responded 'Yes' to vote initiation prompt"
                )
            
            # Add immediate notification to all agents that voting has started
            discussion_state.public_history += f"\n{self._format_voting_tag_message('initiated_tag', 'initiated_message', name=initiator.name)}"
            
            # Update all agent memories with voting start
            await self._update_all_memories_for_voting_phase(
                "initiation", contexts, initiator_name=initiator.name
            )
            
            # Phase 1: Confirmation (all others must agree)
            confirmation_success = await self._conduct_confirmation_phase(
                initiator.name, 
                f"Vote initiation: {initiator.name} wants to vote", 
                contexts, 
                discussion_state
            )
            
            if not confirmation_success:
                self._log_info("Vote confirmation failed - continuing discussion")
                if self.logger:
                    self.logger.complete_vote_round(
                        consensus_reached=False,
                        warnings=["Confirmation phase failed"]
                    )
                return False
            
            # Phase 2: Secret Ballot
            consensus_reached = await self._conduct_secret_ballot_phase(
                contexts, discussion_state
            )
            
            # Set _consensus_result when consensus is reached (required for prompt-based voting)
            if consensus_reached and discussion_state.last_vote_result:
                discussion_state._consensus_result = GroupDiscussionResult(
                    consensus_reached=True,
                    agreed_principle=discussion_state.last_vote_result.agreed_principle,
                    final_round=discussion_state.round_number,
                    discussion_history=discussion_state.public_history,
                    vote_history=discussion_state.vote_history
                )
            
            # Log results
            if self.logger and discussion_state.last_vote_result:
                vote_result = discussion_state.last_vote_result
                self.logger.complete_vote_round(
                    consensus_reached=vote_result.consensus_reached,
                    agreed_principle=vote_result.agreed_principle.principle.value if vote_result.agreed_principle else None,
                    agreed_constraint=vote_result.agreed_principle.constraint_amount if vote_result.agreed_principle else None,
                    vote_counts=vote_result.vote_counts
                )
            
            return consensus_reached
            
        finally:
            self._voting_in_progress = False

    
    def _manage_discussion_history_length(self, discussion_state: GroupDiscussionState) -> None:
        """
        Keep discussion history under limit by trimming oldest content.
        Preserves recent conversation while preventing excessive memory usage.
        """
        max_length = 100000  # 100k chars - much higher than agent memory limits (25k)
        
        if len(discussion_state.public_history) > max_length:
            # Keep the most recent 75% of content to provide buffer
            keep_length = int(max_length * 0.75)
            
            # Add marker to indicate truncation and keep recent discussion
            truncated_history = self._get_localized_message("system_messages.discussion.truncation_marker") + "\n" + discussion_state.public_history[-keep_length:]
            discussion_state.public_history = truncated_history
            
            # Log the truncation for debugging
            self._log_info(f"Discussion history truncated: kept {keep_length} of {len(discussion_state.public_history)} characters")
    
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
            language_manager = self.language_manager
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
                if self.seed_manager:
                    random_distribution = self.seed_manager.random.choice(distribution_set.distributions)
                else:
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
        language_manager = self.language_manager
        
        # Build consensus status message
        if consensus_result.consensus_reached:
            if consensus_result.agreed_principle.constraint_amount:
                consensus_status = self._get_localized_message("voting_results.consensus_with_constraint", 
                                                             principle_name=consensus_result.agreed_principle.principle.value,
                                                             constraint_amount=consensus_result.agreed_principle.constraint_amount)
            else:
                consensus_status = self._get_localized_message("voting_results.consensus_reached", 
                                                             principle_name=consensus_result.agreed_principle.principle.value)
        else:
            consensus_status = self._get_localized_message("phase2_no_consensus")
        
        # Format the class name for display using localization
        formatted_class = self._get_localized_income_class(assigned_class.lower())
        
        # Build the header
        language_manager = self.language_manager
        result_content = f"""{self._get_localized_message('results.phase2_header')}

{self._get_localized_message('results.consensus_status')} {consensus_status}
{language_manager.get('memory_field_labels.your_income_assignment')} {formatted_class}
{language_manager.get('memory_field_labels.your_earnings')} ${final_earnings:.2f}

{self._get_localized_message('results.counterfactual_header')}"""
        
        # Get principle display names
        principle_display_names = {
            "maximizing_floor": language_manager.get("common.principle_names.maximizing_floor"),
            "maximizing_average": language_manager.get("common.principle_names.maximizing_average"),
            "maximizing_average_floor_constraint": language_manager.get("common.principle_names.maximizing_average_floor_constraint"),
            "maximizing_average_range_constraint": language_manager.get("common.principle_names.maximizing_average_range_constraint")
        }
        
        # Add table header
        principle_header = self._get_localized_message('results.table_headers.principle')
        income_header = self._get_localized_message('results.table_headers.income')
        earnings_header = self._get_localized_message('results.table_headers.earnings')
        
        result_content += f"""
┌─────────────────────────────────────────┬──────────┬──────────┐
│ {principle_header:<39} │ {income_header:>8} │ {earnings_header:>8} │
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
            
            result_content += f"\n\n{self._get_localized_message('results.key_insights')}"
            
            if best_diff > 0:
                result_content += f"\n{self._get_localized_message('phase2_counterfactual_insights_best_more', best_principle=best_principle_name, best_diff=best_diff)}"
            elif best_diff == 0:
                result_content += f"\n{self._get_localized_message('phase2_counterfactual_insights_best_same')}"
            else:
                result_content += f"\n{self._get_localized_message('phase2_counterfactual_insights_best_same')}"
                
            if worst_diff > 0:
                result_content += f"\n{self._get_localized_message('phase2_counterfactual_insights_worst_more', worst_principle=worst_principle_name, worst_diff=worst_diff)}"
            elif worst_diff == 0:
                result_content += f"\n{self._get_localized_message('phase2_counterfactual_insights_worst_same')}"
        
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
                result_content = f"{self._get_localized_message('results.phase2_header')}: Phase 2 earnings: ${final_earnings:.2f}. "
                if discussion_result.consensus_reached:
                    result_content += self._get_localized_message("voting_results.consensus_reached", principle_name=discussion_result.agreed_principle.principle.value) + "."
                else:
                    result_content += self._get_localized_message("phase2_no_consensus") + "."
            
            # Update memory with final results using selective routing
            context.memory = await SelectiveMemoryManager.update_memory_selective(
                agent=participant, 
                context=context, 
                content=f"Final Phase 2 Results: {result_content}",
                event_type=MemoryEventType.FINAL_RESULTS,
                event_metadata={'final_earnings': final_earnings, 'consensus_reached': discussion_result.consensus_reached},
                config=self.config,
                language_manager=self.language_manager, 
                error_handler=self.error_handler, 
                utility_agent=self.utility_agent
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
                # Extract individual vote information for this participant
                final_vote, vote_timestamp = self._extract_participant_vote_info(
                    participant_name, discussion_result, logger
                )
                
                logger.log_post_discussion(
                    participant_name,
                    assigned_class,
                    final_earnings,
                    ranking,
                    memory_state,
                    bank_balance,
                    final_vote=final_vote,
                    vote_timestamp=vote_timestamp
                )
            
            final_rankings[participant_name] = ranking
        
        return final_rankings
    
    def _extract_participant_vote_info(
        self, 
        participant_name: str, 
        discussion_result: GroupDiscussionResult, 
        logger: AgentCentricLogger
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Extract individual vote information for a specific participant.
        
        Args:
            participant_name: Name of the participant to extract vote info for
            discussion_result: The discussion result containing vote history
            logger: The agent-centric logger containing voting history
            
        Returns:
            Tuple of (final_vote, vote_timestamp) where both may be None if no vote found
        """
        # Try to extract from agent logger's voting history first (most reliable)
        if (logger and 
            hasattr(logger, 'voting_history') and 
            logger.voting_history and
            logger.voting_history.vote_rounds):
            
            # Get the most recent vote round
            for vote_round in reversed(logger.voting_history.vote_rounds):
                if vote_round.participant_votes:
                    for vote_detail in vote_round.participant_votes:
                        if vote_detail["participant_name"] == participant_name:
                            assessed_choice = vote_detail["assessed_choice"]
                            vote_timestamp = vote_detail.get("vote_timestamp")
                            
                            # Don't return parsing failures as valid votes
                            if assessed_choice and assessed_choice != "PARSING_FAILED":
                                return assessed_choice, vote_timestamp
        
        # Fallback: Try to extract from discussion result vote history (less reliable for individual votes)
        if (discussion_result.vote_history and 
            len(discussion_result.vote_history) > 0):
            
            last_vote = discussion_result.vote_history[-1]
            if last_vote.votes:
                # This is less reliable as it assumes vote order matches participant order
                # But it's a fallback in case voting history isn't properly populated
                for i, participant in enumerate(self.participants):
                    if participant.name == participant_name and i < len(last_vote.votes):
                        vote = last_vote.votes[i]
                        if vote:
                            timestamp = last_vote.timestamp.isoformat() if last_vote.timestamp else None
                            return vote.principle.value, timestamp
        
        # No vote information found
        return None, None
    
    async def _get_final_ranking(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_config: AgentConfiguration
    ) -> PrincipleRanking:
        """Get participant's final principle ranking after Phase 2."""
        
        language_manager = self.language_manager
        final_ranking_prompt = language_manager.get("prompts.phase2_final_ranking_prompt")
        
        # Always use text responses, parse with enhanced utility agent
        result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
        text_response = result.final_output
        
        # Parse using enhanced utility agent with retry logic
        return await self.utility_agent.parse_principle_ranking_enhanced(text_response)
    
    def _build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int) -> str:
        """Build prompt for internal reasoning before public statement."""
        language_manager = self.language_manager
        
        return language_manager.get("prompts.phase2_internal_reasoning",
                                   round_number=round_num,
                                   max_rounds=self.config.phase2_rounds,
                                   discussion_history=discussion_state.public_history or "No previous discussion.")
    
    def _build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, internal_reasoning: str = "") -> str:
        """Build prompt for group discussion round with formal voting support."""
        language_manager = self.language_manager
        
        # Generate dynamic participant information
        num_participants = len(self.participants)
        participant_names = [participant.name for participant in self.participants]
        
        group_participants = self._format_group_composition(participant_names)
        
        # Always use complex mode prompts (formal voting system)
        base_prompt = language_manager.get("prompts.phase2_discussion_prompt",
                                          round_number=round_num,
                                          max_rounds=self.config.phase2_rounds,
                                          discussion_history=discussion_state.public_history or "No previous discussion.",
                                          group_participants=group_participants)
        
        # If internal reasoning is provided, include it in the prompt
        if internal_reasoning and internal_reasoning.strip():
            return f"{base_prompt}\n\n{self._get_localized_message('voting_prompts.internal_reasoning_section')}\n{internal_reasoning}\n================================\n\n{self._get_localized_message('voting_prompts.reasoning_prompt')}"
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
        
        # Formal voting process initiated via prompts only
        self._log_info(f"Complex voting initiated from {participant.name}")
        
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
            
            # Step B: Enhanced Secret Ballot Phase using streamlined method
            consensus_reached = await self._conduct_secret_ballot_phase(contexts, discussion_state)
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
        
        language_manager = self.language_manager
        
        # Create confirmation prompt using new language manager key
        confirmation_prompt = language_manager.get(
            "prompts.utility_voting_confirmation_request",
            initiation_statement=initiation_statement
        )
        
        confirmations = []
        
        # Store original tool settings to restore later
        original_tool_settings = []
        
        try:
            for i, context in enumerate(contexts):
                participant = self.participants[i]
                
                # Auto-confirm initiator since they proposed the vote
                if participant.name == initiator_name:
                    # Auto-confirm for initiator
                    confirmations.append({
                        'participant': participant.name,
                        'response': "1 (auto-confirmed as initiator)",
                        'agrees': True
                    })
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: Confirmed (initiated vote)"
                    self._log_info(f"Auto-confirmed vote initiator: {participant.name}")
                    continue  # Skip to next participant
                
                # Store original setting and disable vote tool during confirmation
                original_tool_settings.append(getattr(context, 'allow_vote_tool', True))
                context.allow_vote_tool = False
                
                # Get confirmation response from participant with timeout
                confirmation_response = None
                max_retries = 3  # Allow retries for re-entrant tool calls
                
                for attempt in range(max_retries):
                    try:
                        # Set interaction type for confirmation (disables propose_vote tool)
                        context.interaction_type = "confirmation"
                        result = await asyncio.wait_for(
                            Runner.run(participant.agent, confirmation_prompt, context=context),
                            timeout=self.settings.confirmation_timeout_seconds
                        )
                        confirmation_response = result.final_output
                        
                        # Tool detection removed - no tool calls to check
                        break  # Got valid response, exit retry loop
                            
                    except asyncio.TimeoutError:
                        self._log_warning(f"Timeout waiting for confirmation from {participant.name} (attempt {attempt + 1})")
                        if attempt == max_retries - 1:
                            confirmation_response = f"[{participant.name} timed out during confirmation]"
                        continue
                
                # CRITICAL: Check if response is a fallback statement (agent failure)
                is_fallback = confirmation_response.startswith(f"[{participant.name} failed to provide")
                if is_fallback:
                    self._log_warning(f"Fallback response detected for {participant.name} - voting confirmation failed")
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: {confirmation_response}"
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.result_tag')} Agent failure detected - confirmation failed"
                    return False
                
                # Use numerical agreement detection (1=yes, 0=no)
                agrees_to_vote, parse_error = self.utility_agent.detect_numerical_agreement(confirmation_response)
                
                # Handle malformed responses
                if parse_error is not None:
                    self._log_warning(f"Malformed confirmation response from {participant.name}: {parse_error}")
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: {confirmation_response}"
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.result_tag')} Invalid response format - confirmation failed. {parse_error}"
                    return False
                
                confirmations.append({
                    'participant': participant.name,
                    'response': confirmation_response,
                    'agrees': agrees_to_vote
                })
                
                # Add to public history (visible to all)
                discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: {confirmation_response}"
                
                # Update participant memory with their confirmation response using simple insertion
                SimpleMemoryManager.insert_confirmation_response(
                    context, agrees_to_vote, self.language_manager
                )
                
                # If anyone disagrees, confirmation phase fails
                if not agrees_to_vote:
                    self._log_info(f"{participant.name} declined voting - confirmation failed")
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.result_tag')} {self._get_localized_message('system_messages.voting.confirmation_failed')}"
                    
                    # Log the failed confirmation attempt with all responses collected so far
                    if self.logger:
                        confirmation_responses = {}
                        for confirmation in confirmations:
                            participant_name = confirmation['participant']
                            agrees = confirmation['agrees']
                            confirmation_responses[participant_name] = "Yes" if agrees else "No"
                        
                        self.logger.log_vote_confirmation_attempt(
                            round_number=discussion_state.round_number,
                            initiator=initiator_name,
                            confirmation_responses=confirmation_responses,
                            confirmation_succeeded=False
                        )
                    
                    return False
            
            self._log_info("All participants agreed to vote - proceeding to secret ballot")
            discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.result_tag')} {self._get_localized_message('system_messages.voting.confirmation_success')}"
        
            # Log confirmation results
            if self.logger:
                self.logger.log_confirmation_phase(confirmations)
                
                # Also log vote confirmation attempt for new voting history tracking
                confirmation_responses = {}
                confirmation_succeeded = True
                for confirmation in confirmations:
                    participant_name = confirmation['participant']
                    agrees = confirmation['agrees']
                    confirmation_responses[participant_name] = "Yes" if agrees else "No"
                    if not agrees:
                        confirmation_succeeded = False
                
                self.logger.log_vote_confirmation_attempt(
                    round_number=discussion_state.round_number,
                    initiator=initiator_name,
                    confirmation_responses=confirmation_responses,
                    confirmation_succeeded=confirmation_succeeded
                )
            
            return True
            
        finally:
            # Always restore original tool settings, even if method exits early
            for i, context in enumerate(contexts):
                if i < len(original_tool_settings):
                    context.allow_vote_tool = original_tool_settings[i]
                    self._log_info(f"Restored vote tool setting for {context.name}: {original_tool_settings[i]}")
    
    async def _conduct_secret_ballot_phase(
        self,
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState
    ) -> bool:
        """
        Conduct secret ballot phase using enhanced TwoStageVotingManager.
        Returns True if consensus is reached.
        """
        
        self._log_info("=== COMPLEX VOTING: SECRET BALLOT PHASE (ENHANCED) ===")
        
        # Initialize enhanced two-stage voting manager
        voting_manager = TwoStageVotingManager(
            participants=self.participants,
            language_manager=self.language_manager,
            logger=self.logger,
            settings=self.settings,
            error_handler=self.error_handler,
            utility_agent=self.utility_agent
        )
        
        # Conduct structured two-stage voting process
        # This replaces 100+ lines of complex LLM parsing with deterministic validation
        vote_result = await voting_manager.conduct_full_voting_process(contexts, discussion_state)
        
        if vote_result is None:
            # Voting process failed - log and return to discussion
            self._log_warning("Two-stage voting process failed - returning to discussion")
            discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.error_tag')} {self._get_localized_message('system_messages.voting.process_failed')}"
            return False
        
        # Store vote result in discussion state (maintains compatibility with existing code)
        discussion_state.last_vote_result = vote_result
        discussion_state.vote_history.append(vote_result)
        
        # Log and update discussion history based on consensus result
        if vote_result.consensus_reached:
            self._log_info(f"Consensus reached via enhanced two-stage voting: {vote_result.agreed_principle.principle.value}")
            
            # Get localized principle name
            principle_key = vote_result.agreed_principle.principle.value
            localized_principle_name = self.language_manager.get(f"principle_names.{principle_key}")
            
            # Add to public history using localized consensus message
            if vote_result.agreed_principle.constraint_amount:
                consensus_msg = self.language_manager.get(
                    "voting_results.consensus_with_constraint",
                    principle_name=localized_principle_name,
                    constraint_amount=vote_result.agreed_principle.constraint_amount
                )
            else:
                consensus_msg = self.language_manager.get(
                    "voting_results.consensus_reached",
                    principle_name=localized_principle_name
                )
            discussion_state.public_history += f"\n[VOTING RESULT] {consensus_msg}"
            
            # Additional logging for transparency
            self._log_info(f"Vote counts: {vote_result.vote_counts}")
        else:
            self._log_info("No consensus reached in enhanced two-stage voting")
            
            # Enhanced direct messaging for clearer vote results
            principles = [v.principle for v in vote_result.votes]
            unique_principles = set(p.value for p in principles)
            
            if len(unique_principles) == 1:
                # Same principle, different constraints - use localized constraint disagreement message
                principle_name = principles[0].value
                constraints = [v.constraint_amount for v in vote_result.votes if v.constraint_amount]
                if constraints:
                    # Use existing localized constraint disagreement message
                    message = self.language_manager.get(
                        "phase2_voting_no_consensus_constraint_disagreement",
                        principle_name=principle_name
                    )
                    # Add detailed constraint info for debugging in logs
                    self._log_info(f"Constraint amounts that differed: {constraints}")
                else:
                    # Same principle, no constraints - use general disagreement message
                    message = self.language_manager.get("phase2_voting_no_consensus_principle_disagreement")
            else:
                # Different principles - use localized principle disagreement message
                message = self.language_manager.get("phase2_voting_no_consensus_principle_disagreement")
                # Add detailed vote breakdown for debugging in logs
                self._log_info(f"Vote distribution: {vote_result.vote_counts}")
            
            discussion_state.public_history += f"\n[VOTING RESULT] {message}"
            
            # Log vote distribution for debugging
            if vote_result.vote_counts:
                self._log_info(f"Vote distribution: {vote_result.vote_counts}")
        
        return vote_result.consensus_reached
    
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
        language_manager = self.language_manager
        
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
    
    
    async def _update_all_memories_for_voting_phase(
        self, 
        phase_name: str,
        contexts: List[ParticipantContext],
        additional_info: str = "",
        initiator_name: str = None
    ):
        """
        Update all participant memories for voting phase transitions with multilingual support.
        
        Args:
            phase_name: Name of the voting phase ("initiation", "confirmation", "secret_ballot", "results")
            contexts: List of participant contexts to update
            additional_info: Additional information to include in memory update
            initiator_name: Name of the participant who initiated voting (for initiation phase)
        """
        for i, context in enumerate(contexts):
            # Get localized voting phase message
            if phase_name == "initiation" and initiator_name:
                memory_content = self.language_manager.get(
                    f"voting_phases.{phase_name}", 
                    initiator_name=initiator_name
                )
            else:
                memory_content = self.language_manager.get(f"voting_phases.{phase_name}")
            
            # Add any additional information
            if additional_info:
                memory_content += f" {additional_info}"
            
            # Update participant memory using selective routing
            context.memory = await SelectiveMemoryManager.update_memory_selective(
                agent=self.participants[i], 
                context=context, 
                content=memory_content,
                event_type=MemoryEventType.PHASE_TRANSITION,
                event_metadata={'phase_name': phase_name, 'initiator_name': initiator_name if 'initiator_name' in locals() else None},
                config=self.config,
                language_manager=self.language_manager,
                error_handler=self.error_handler,
                utility_agent=self.utility_agent,
                memory_guidance_style=self.config.memory_guidance_style if self.config else "narrative"
            )
    
