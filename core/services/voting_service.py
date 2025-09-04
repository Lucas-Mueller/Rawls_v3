"""
Voting Service for Phase 2 Voting Management.

Handles vote initiation, confirmation phases, ballot coordination, and consensus 
validation with multilingual support and comprehensive error handling.
"""

import asyncio
from typing import List, Optional, Protocol, Dict, Any
from agents import Runner
from models import (
    ParticipantContext, GroupDiscussionState, VoteResult,
    PrincipleChoice
)
from experiment_agents import ParticipantAgent
from config.phase2_settings import Phase2Settings
from core.two_stage_voting_manager import TwoStageVotingManager


class LanguageProvider(Protocol):
    """Protocol for language managers that provide localized messages."""
    def get(self, key: str, **kwargs) -> str:
        """Get localized message with substitutions."""
        ...


class UtilityProvider(Protocol):
    """Protocol for utility agents that provide parsing functionality."""
    def detect_numerical_agreement(self, response: str) -> tuple[bool, Optional[str]]:
        """Detect numerical agreement (1=Yes, 0=No) from response."""
        ...


class Logger(Protocol):
    """Protocol for logging information and warnings."""
    def log_info(self, message: str) -> None:
        """Log an info message."""
        ...
    
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        ...


class VotingService:
    """
    Manages voting processes including initiation, confirmation, and ballot coordination.
    
    Consolidates all voting logic from Phase2Manager with protocol-based dependencies
    for clean separation of concerns and testability.
    """
    
    def __init__(self, language_manager: LanguageProvider, utility_agent: UtilityProvider, 
                 settings: Optional[Phase2Settings] = None, logger: Optional[Logger] = None,
                 memory_service: Optional[object] = None, agent_logger: Optional[object] = None):
        """
        Initialize voting service.
        
        Args:
            language_manager: For localized message retrieval
            utility_agent: For numerical agreement detection
            settings: Phase 2 settings for timeouts and validation (optional)
            logger: For logging info and warnings (optional)
            memory_service: For recording simple voting events (optional)
            agent_logger: For agent-centric logging (optional)
        """
        self.language_manager = language_manager
        self.utility_agent = utility_agent
        self.settings = settings or Phase2Settings.get_default()
        self.logger = logger
        # Optional memory service for recording simple voting events
        self.memory_service = memory_service
        # Optional agent-centric logger for detailed voting analytics
        self.agent_logger = agent_logger
    
    def _log_info(self, message: str) -> None:
        """Log info message if logger is available."""
        if self.logger:
            self.logger.log_info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log warning message if logger is available."""
        if self.logger:
            self.logger.log_warning(message)
    
    def _get_localized_message(self, key: str, **kwargs) -> str:
        """Get localized message with fallback handling."""
        try:
            return self.language_manager.get(key, **kwargs)
        except Exception as e:
            self._log_warning(f"Missing translation key: {key} - {str(e)}")
            return f"[MISSING: {key}]"
    
    async def prompt_for_vote_initiation(
        self,
        participant: ParticipantAgent,
        context: ParticipantContext,
        agent_recent_statement: Optional[str] = None,
        internal_reasoning: Optional[str] = None,
        max_retries: int = 3
    ) -> bool:
        """
        Prompt participant for vote initiation decision with retry logic.
        
        Args:
            participant: The participant agent to prompt
            context: The participant's context
            agent_recent_statement: Agent's recent statement for consistency (optional)
            internal_reasoning: Agent's internal reasoning to include in prompt (optional)
            max_retries: Maximum number of retry attempts for invalid responses
            
        Returns:
            True if agent wants to vote, False otherwise
        """
        language_manager = self.language_manager
        
        # Select appropriate prompt based on available context
        has_statement = agent_recent_statement and agent_recent_statement.strip()
        has_reasoning = internal_reasoning and internal_reasoning.strip()
        
        if has_statement and has_reasoning:
            # Both statement and reasoning available - use combined prompt
            vote_prompt = language_manager.get(
                "prompts.vote_initiation_with_statement_and_reasoning_prompt",
                agent_recent_statement=agent_recent_statement,
                internal_reasoning=internal_reasoning
            )
        elif has_reasoning:
            # Only reasoning available - use reasoning-only prompt
            vote_prompt = language_manager.get(
                "prompts.vote_initiation_with_reasoning_prompt",
                internal_reasoning=internal_reasoning
            )
        elif has_statement:
            # Only statement available - use existing statement prompt
            vote_prompt = language_manager.get(
                "prompts.vote_initiation_with_statement_prompt",
                agent_recent_statement=agent_recent_statement
            )
        else:
            # No additional context - use basic prompt
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
                
                # Log vote initiation request if agent logger is available
                if self.agent_logger and hasattr(context, 'current_round_number'):
                    # Create a single-agent vote request dict
                    vote_requests = {participant.name: "Yes" if wants_vote else "No"}
                    self.agent_logger.log_round_vote_requests(
                        round_number=context.current_round_number,
                        vote_requests=vote_requests
                    )
                    
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
        
        # Should never reach here, but safety fallback
        return False
    
    async def conduct_confirmation_phase(
        self,
        participants: List[ParticipantAgent],
        initiator_name: str,
        initiation_statement: str,
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState
    ) -> bool:
        """
        Conduct public confirmation phase using existing agreement detection.
        
        Args:
            participants: List of participant agents
            initiator_name: Name of the participant who initiated voting
            initiation_statement: The statement that initiated voting
            contexts: List of participant contexts
            discussion_state: Current discussion state
            
        Returns:
            True if all participants agree to vote
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
                participant = participants[i]
                
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
                try:
                    confirmation_timeout = self.settings.confirmation_timeout_seconds
                    context.interaction_type = "vote_confirmation"
                    
                    result = await asyncio.wait_for(
                        Runner.run(participant.agent, confirmation_prompt, context=context),
                        timeout=confirmation_timeout
                    )
                    response = result.final_output.strip()
                    
                    self._log_info(f"Confirmation response from {participant.name}: '{response[:100]}{'...' if len(response) > 100 else ''}'")
                    
                    # Use numerical agreement detection (1=Yes, 0=No)
                    agrees_to_vote, parse_error = self.utility_agent.detect_numerical_agreement(response)
                    
                    if parse_error is not None:
                        # Invalid response - treat as disagreement
                        self._log_warning(f"Invalid confirmation response from {participant.name}: {parse_error}")
                        agrees_to_vote = False
                    
                    confirmations.append({
                        'participant': participant.name,
                        'response': response,
                        'agrees': agrees_to_vote
                    })
                    
                    # Add confirmation to public history
                    response_text = "Confirmed" if agrees_to_vote else "Declined"
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: {response_text}"
                    
                    self._log_info(f"✅ Confirmation result for {participant.name}: {'Agrees' if agrees_to_vote else 'Declines'}")
                    
                except asyncio.TimeoutError:
                    self._log_warning(f"Confirmation timeout for {participant.name} after {confirmation_timeout}s")
                    confirmations.append({
                        'participant': participant.name,
                        'response': "(timeout - declined)",
                        'agrees': False
                    })
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: Declined (timeout)"
                    
                except Exception as e:
                    self._log_warning(f"Error during confirmation from {participant.name}: {str(e)}")
                    confirmations.append({
                        'participant': participant.name,
                        'response': f"(error: {str(e)[:50]})",
                        'agrees': False
                    })
                    discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.confirmation_tag')} {participant.name}: Declined (error)"
            
            # Check if all participants agreed to vote
            all_agreed = all(conf['agrees'] for conf in confirmations)
            
            if all_agreed:
                self._log_info("✅ All participants confirmed - proceeding to secret ballot")
                discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.all_confirmed')}"
            else:
                # List who declined
                declined = [conf['participant'] for conf in confirmations if not conf['agrees']]
                self._log_info(f"❌ Voting declined by: {', '.join(declined)} - returning to discussion")
                discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.voting_declined', declined_participants=', '.join(declined))}"
            
            # Log confirmation attempt if agent logger is available
            if self.agent_logger:
                confirmation_responses = {conf['participant']: "Yes" if conf['agrees'] else "No" 
                                        for conf in confirmations}
                self.agent_logger.log_vote_confirmation_attempt(
                    round_number=discussion_state.round_number,
                    initiator=initiator_name,
                    confirmation_responses=confirmation_responses,
                    confirmation_succeeded=all_agreed
                )
            
            return all_agreed
            
        finally:
            # Restore original tool settings
            for i, context in enumerate(contexts):
                if i < len(original_tool_settings):
                    context.allow_vote_tool = original_tool_settings[i]
                    self._log_info(f"Restored vote tool setting for {context.name}: {original_tool_settings[i]}")
    
    async def conduct_secret_ballot(
        self,
        participants: List[ParticipantAgent],
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState,
        error_handler,
        utility_agent
    ) -> Optional[VoteResult]:
        """
        Conduct secret ballot phase using enhanced TwoStageVotingManager.
        
        Args:
            participants: List of participant agents
            contexts: List of participant contexts
            discussion_state: Current discussion state
            error_handler: Error handler for voting process
            utility_agent: Utility agent for voting process
            
        Returns:
            VoteResult if consensus is reached, None otherwise
        """
        
        self._log_info("=== COMPLEX VOTING: SECRET BALLOT PHASE (ENHANCED) ===")
        
        # Initialize enhanced two-stage voting manager
        voting_manager = TwoStageVotingManager(
            participants=participants,
            language_manager=self.language_manager,
            logger=self.logger,
            settings=self.settings,
            error_handler=error_handler,
            utility_agent=utility_agent,
            memory_service=self.memory_service
        )
        
        # Conduct structured two-stage voting process
        # This replaces 100+ lines of complex LLM parsing with deterministic validation
        vote_result = await voting_manager.conduct_full_voting_process(contexts, discussion_state)
        
        if vote_result is None:
            # Voting process failed - log and return to discussion
            self._log_warning("Two-stage voting process failed - returning to discussion")
            discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.error_tag')} {self._get_localized_message('system_messages.voting.process_failed')}"
            return None
        
        # Store vote result in discussion state (maintains compatibility with existing code)
        discussion_state.last_vote_result = vote_result
        discussion_state.vote_history.append(vote_result)

        # Log vote round details if agent logger is available
        if self.agent_logger and vote_result:
            # We need the initiator name from the calling context - for now use trigger_participant if available
            trigger_participant = getattr(vote_result, 'trigger_participant', None)
            
            self.agent_logger.start_vote_round(
                round_number=discussion_state.round_number,
                vote_type="formal_vote",
                trigger_participant=trigger_participant
            )
            
            # Log individual votes if vote_result has participant details
            if hasattr(vote_result, 'individual_votes'):
                for vote_info in vote_result.individual_votes:
                    if hasattr(self.agent_logger, 'log_participant_vote'):
                        self.agent_logger.log_participant_vote(
                            participant_name=vote_info.get('name', 'Unknown'),
                            raw_response=vote_info.get('raw_response', ''),
                            assessed_choice=vote_info.get('assessed_choice', ''),
                            constraint_amount=vote_info.get('constraint_amount'),
                            parsing_success=vote_info.get('parsing_success', False)
                        )
            
            # Complete the vote round logging
            if hasattr(self.agent_logger, 'complete_vote_round'):
                self.agent_logger.complete_vote_round(
                    consensus_reached=vote_result.consensus_reached,
                    agreed_principle=vote_result.agreed_principle.principle.value if vote_result.agreed_principle else None,
                    agreed_constraint=vote_result.agreed_principle.constraint_amount if vote_result.agreed_principle else None
                )

        # Log and update discussion history based on consensus result
        if vote_result.consensus_reached:
            self._log_info(f"Consensus reached via enhanced two-stage voting: {vote_result.agreed_principle.principle.value}")
            
            # Get localized principle name
            principle_key = vote_result.agreed_principle.principle.value
            localized_principle_name = self.language_manager.get(f"common.principle_names.{principle_key}")
            
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
            
            discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.consensus_tag')} {consensus_msg}"
            
            # Set Phase2Manager-compatible consensus fields for early exit
            try:
                from models import GroupDiscussionResult
                # Mark consensus on the discussion state for Phase2Manager lock checks
                setattr(discussion_state, '_consensus_reached', True)
                # Build a GroupDiscussionResult to allow early return from discussion loop
                consensus_result = GroupDiscussionResult(
                    consensus_reached=True,
                    agreed_principle=vote_result.agreed_principle,
                    final_round=discussion_state.round_number,
                    discussion_history=discussion_state.public_history,
                    vote_history=discussion_state.vote_history
                )
                setattr(discussion_state, '_consensus_result', consensus_result)
            except Exception as e:
                # Do not fail voting flow due to logging/compat concerns
                self._log_warning(f"Failed to set consensus result on discussion state: {e}")
        
        else:
            self._log_info(f"No consensus reached - disagreement details: {vote_result.disagreement_summary}")
            
            # Add no consensus message to public history
            no_consensus_msg = self.language_manager.get("voting_results.no_consensus")
            discussion_state.public_history += f"\n{self._get_localized_message('system_messages.voting.no_consensus_tag')} {no_consensus_msg}"
        
        return vote_result
    
    async def conduct_voting_process(
        self,
        participants: List[ParticipantAgent],
        initiating_participant: ParticipantAgent,
        contexts: List[ParticipantContext],
        discussion_state: GroupDiscussionState,
        agent_recent_statement: Optional[str],
        error_handler,
        utility_agent,
        internal_reasoning: Optional[str] = None
    ) -> bool:
        """
        Conduct full voting process: initiation -> confirmation -> ballot.
        
        Args:
            participants: List of all participant agents
            initiating_participant: The participant who might initiate voting
            contexts: List of participant contexts
            discussion_state: Current discussion state
            agent_recent_statement: Recent statement from initiating participant
            error_handler: Error handler for voting process
            utility_agent: Utility agent for voting process
            internal_reasoning: Internal reasoning from initiating participant (optional)
            
        Returns:
            True if consensus is reached, False otherwise
        """
        # Find the initiating participant's context
        initiating_context = None
        for context in contexts:
            if context.name == initiating_participant.name:
                initiating_context = context
                break
        
        if not initiating_context:
            self._log_warning(f"Could not find context for initiating participant: {initiating_participant.name}")
            return False
        
        # Step 1: Conduct confirmation phase
        all_confirmed = await self.conduct_confirmation_phase(
            participants=participants,
            initiator_name=initiating_participant.name,
            initiation_statement=agent_recent_statement or "Voting initiated",
            contexts=contexts,
            discussion_state=discussion_state
        )
        
        if not all_confirmed:
            return False
        
        # Step 2: Conduct secret ballot
        vote_result = await self.conduct_secret_ballot(
            participants=participants,
            contexts=contexts,
            discussion_state=discussion_state,
            error_handler=error_handler,
            utility_agent=utility_agent
        )
        
        # Return whether consensus was reached
        return vote_result is not None and vote_result.consensus_reached
