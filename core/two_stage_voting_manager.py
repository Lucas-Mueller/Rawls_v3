"""
Two-Stage Voting Manager

This module implements a structured two-stage voting system that replaces
the complex LLM-based vote detection with deterministic numerical input validation.

Stage 1: Principle Selection (1-4)
Stage 2: Amount Specification (for principles 3 & 4)
"""

import re
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import model classes for proper integration
from models.principle_types import VoteResult, PrincipleChoice, JusticePrinciple, CertaintyLevel
from agents import Runner
from utils.logging import run_with_transcript_logging

# Import multilingual support components  
from utils.cultural_adaptation import get_amount_formatter, SupportedLanguage as CulturalLanguage
from core.principle_name_manager import get_principle_name_manager

# Import keyword matching system for fallback validation
from core.principle_keywords import (
    principle_keyword_matcher, 
    SupportedLanguage, 
    match_principle_from_text,
    detect_language_from_response
)

# Import memory content builders
from utils.memory_content import (
    build_two_stage_voting_principle_selection_delta,
    build_two_stage_voting_amount_specification_delta, 
    build_two_stage_voting_complete_delta
)
from utils.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class PrincipleType(Enum):
    """Enumeration of the four justice principles."""
    MAXIMIZING_FLOOR = 1
    MAXIMIZING_AVERAGE = 2
    MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT = 3
    MAXIMIZING_AVERAGE_RANGE_CONSTRAINT = 4


@dataclass
class VotingStageResult:
    """Result of a single voting stage for one participant."""
    participant_name: str
    stage: str  # "principle_selection" or "amount_specification"
    success: bool
    value: Optional[int]
    raw_response: str
    attempts_used: int
    error_type: Optional[str] = None


@dataclass
class ParticipantVote:
    """Complete vote from a single participant."""
    participant_name: str
    principle_num: int
    constraint_amount: Optional[int] = None
    principle_selection_result: Optional[VotingStageResult] = None
    amount_specification_result: Optional[VotingStageResult] = None


class TwoStageVotingManager:
    """
    Manages structured two-stage voting process with deterministic validation.
    
    Replaces complex LLM-based vote detection with simple regex validation:
    - Stage 1: Principle selection (1-4) 
    - Stage 2: Amount specification for constraint principles (positive integers)
    """
    
    def __init__(self, participants: List[Any], language_manager: Any, logger: Any, settings: Any = None, error_handler: Any = None, utility_agent: Any = None, memory_service: Any = None, phase2_rounds: int = 10, transcript_logger=None):
        """
        Initialize the two-stage voting manager.

        Args:
            participants: List of ParticipantAgent objects
            language_manager: LanguageManager instance for multilingual support
            logger: AgentCentricLogger instance for vote tracking
            settings: Phase2Settings instance with voting configuration
            error_handler: ExperimentErrorHandler instance for error handling
            utility_agent: UtilityAgent instance for memory compression
            phase2_rounds: Maximum number of Phase 2 rounds (from ExperimentConfiguration)
        """
        self.participants = participants
        self.language_manager = language_manager
        self.logger = logger
        self.settings = settings
        self.error_handler = error_handler
        self.utility_agent = utility_agent
        # Optional MemoryService for writing simple voting-related memory events
        self.memory_service = memory_service
        # Store phase2_rounds from ExperimentConfiguration
        self.phase2_rounds = phase2_rounds
        self.transcript_logger = transcript_logger
        
        # Initialize multilingual support components
        self.amount_formatter = get_amount_formatter()
        self.principle_name_manager = get_principle_name_manager()
        # Wire the language manager so display name lookups work without warnings
        try:
            if self.principle_name_manager and language_manager is not None:
                self.principle_name_manager.language_manager = language_manager
                # Clear cache to avoid stale names if language changed
                self.principle_name_manager.clear_cache()
        except Exception as e:
            logger.warning(f"Failed to attach language manager to PrincipleNameManager: {e}")
        
        # Store settings reference and set defaults
        self.settings = settings
        self.max_retries = getattr(settings, 'two_stage_max_retries', 3) if settings else 3
        self.timeout_seconds = getattr(settings, 'two_stage_timeout_seconds', 30.0) if settings else 30.0

    async def conduct_full_voting_process(
        self, 
        contexts: List[Any], 
        discussion_state: Any
    ) -> Optional[Any]:
        """
        Execute complete two-stage voting for all participants.
        
        Args:
            contexts: List of ParticipantContext objects
            discussion_state: GroupDiscussionState object
            
        Returns:
            VoteResult object if successful, None if voting failed
        """
        if not contexts or len(contexts) != len(self.participants):
            logger.error(f"Mismatch between participants and contexts - participants: {len(self.participants)}, contexts: {len(contexts) if contexts else 0}")
            return None
        
        participant_votes = []
        
        for i, context in enumerate(contexts):
            participant = self.participants[i]
            
            logger.info(f"Starting two-stage voting for {participant.name}")
            
            # Stage 1: Principle Selection
            principle_result = await self._conduct_principle_selection_with_retry(participant, context)
            
            if not principle_result or not principle_result.success:
                logger.error(f"Stage 1 (principle selection) failed for {participant.name}")
                if principle_result:
                    logger.error(f"  - Error type: {principle_result.error_type}")
                    logger.error(f"  - Attempts used: {principle_result.attempts_used}")
                    logger.error(f"  - Raw response: {principle_result.raw_response[:200]}...")
                else:
                    logger.error("  - principle_result was None")
                
                # Create partial participant vote with available data
                partial_vote = ParticipantVote(
                    participant_name=participant.name,
                    principle_num=None,  # Failed to get principle
                    constraint_amount=None,
                    principle_selection_result=principle_result,
                    amount_specification_result=None
                )
                participant_votes.append(partial_vote)
                
                # Continue to capture partial data from other participants before failing
                # but mark that voting has failed
                logger.info("Continuing to collect partial data from remaining participants")
                continue
            
            principle_num = principle_result.value

            # Record ballot selection via MemoryService if available
            try:
                if self.memory_service is not None:
                    display_name = self._get_principle_display_name(principle_num)
                    # Persist the ballot choice using MemoryService (simple event path)
                    await self.memory_service.update_ballot_selection_memory(
                        agent=participant,
                        context=context,
                        principle_name=display_name
                    )
            except Exception as e:
                logger.warning(f"Failed to write ballot selection memory for {participant.name}: {e}")
            
            # Stage 2: Amount specification (if needed)
            amount_result = None
            constraint_amount = None
            
            if principle_num in [3, 4]:  # Constraint principles
                amount_result = await self._conduct_amount_specification_with_retry(
                    participant, context, principle_num
                )
                
                if not amount_result or not amount_result.success:
                    logger.error(f"Stage 2 (amount specification) failed for {participant.name}")
                    if amount_result:
                        logger.error(f"  - Error type: {amount_result.error_type}")
                        logger.error(f"  - Attempts used: {amount_result.attempts_used}")
                        logger.error(f"  - Raw response: {amount_result.raw_response[:200]}...")
                    else:
                        logger.error("  - amount_result was None")
                    
                    # Create partial participant vote with available data
                    partial_vote = ParticipantVote(
                        participant_name=participant.name,
                        principle_num=principle_num,  # Stage 1 succeeded
                        constraint_amount=None,  # Stage 2 failed
                        principle_selection_result=principle_result,
                        amount_specification_result=amount_result
                    )
                    participant_votes.append(partial_vote)
                    
                    # Continue to capture partial data from other participants before failing
                    logger.info("Continuing to collect partial data from remaining participants")
                    continue
                
                constraint_amount = amount_result.value

                # Record amount specification via MemoryService if available
                try:
                    if self.memory_service is not None and constraint_amount is not None:
                        formatted_amount = f"${constraint_amount:,}"
                        await self.memory_service.update_amount_specification_memory(
                            agent=participant,
                            context=context,
                            amount=formatted_amount
                        )
                except Exception as e:
                    logger.warning(f"Failed to write amount specification memory for {participant.name}: {e}")
            
            # Create participant vote
            participant_vote = ParticipantVote(
                participant_name=participant.name,
                principle_num=principle_num,
                constraint_amount=constraint_amount,
                principle_selection_result=principle_result,
                amount_specification_result=amount_result
            )
            
            participant_votes.append(participant_vote)
            logger.info(f"Completed two-stage voting for {participant.name}: principle {principle_num}, amount {constraint_amount}")
        
        # Check if any participant votes are incomplete (indicating failures)
        incomplete_votes = []
        complete_votes = []
        
        for vote in participant_votes:
            if (vote.principle_num is None or 
                not vote.principle_selection_result or 
                not vote.principle_selection_result.success or
                (vote.principle_num in [3, 4] and (not vote.amount_specification_result or not vote.amount_specification_result.success))):
                incomplete_votes.append(vote)
            else:
                complete_votes.append(vote)
        
        # If any voting failed, return failure result with partial data
        if incomplete_votes:
            logger.error(f"Voting failed for {len(incomplete_votes)} participants out of {len(participant_votes)}")
            for vote in incomplete_votes:
                logger.error(f"  - Failed: {vote.participant_name}")
            
            # Return failure vote result with all available data (both complete and partial)
            failure_result = self._create_failure_vote_result(participant_votes)
            logger.debug(f"Created failure vote result with {len(failure_result.individual_votes)} individual vote records")
            return failure_result
        
        # Convert to principle choices for consensus checking
        try:
            logger.debug(f"Converting {len(participant_votes)} participant votes to principle choices")
            principle_choices = [self._convert_to_principle_choice(vote) for vote in participant_votes]
            logger.debug(f"Successfully converted to {len(principle_choices)} principle choices")
            
            # Use existing consensus checking logic (this would be imported from the existing system)
            # For now, we'll return a mock success result
            # TODO: Integrate with actual consensus checking logic in Phase 3
            
            logger.info("Two-stage voting completed successfully for all participants")
            vote_result = self._create_vote_result(participant_votes, principle_choices)
            logger.debug(f"Created vote result - consensus: {vote_result.consensus_reached}")
            
            # Memory will be updated later by CounterfactualsService.deliver_results_and_update_memory()
            # This provides comprehensive results with consensus information
            logger.debug("Skipping immediate memory update - will be handled by comprehensive results delivery")
            
            return vote_result
            
        except Exception as e:
            logger.error(f"Error processing voting results: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    async def _conduct_principle_selection_with_retry(
        self, 
        participant: Any, 
        context: Any
    ) -> Optional[VotingStageResult]:
        """
        Conduct Stage 1 (principle selection) with retry logic.
        
        Args:
            participant: ParticipantAgent object
            context: ParticipantContext object
            
        Returns:
            VotingStageResult with principle selection (1-4) or None if failed
        """
        stage = "principle_selection"
        
        try:
            # Get round information from context
            round_number = context.round_number
            max_rounds = self.phase2_rounds

            # Use enhanced language manager method for two-stage prompts
            logger.debug(f"Attempting to get two-stage principle selection prompt for participant {participant.name}")
            base_prompt = self.language_manager.get_two_stage_principle_selection_prompt(
                round_number=round_number,
                max_rounds=max_rounds
            )
            logger.debug(f"Successfully retrieved two-stage principle selection prompt")
        except Exception as e:
            logger.error(f"Failed to get two-stage principle prompt for {participant.name}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Language manager type: {type(self.language_manager).__name__}")
            # Fallback prompt if translation system not available
            base_prompt = self._get_fallback_principle_prompt()
            logger.warning(f"Using fallback principle prompt for {participant.name}")
        
        current_prompt = base_prompt
        
        # Store original tool setting to restore later
        original_tool_setting = getattr(context, 'allow_vote_tool', True)
        
        try:
            # Disable voting tool during ballot phase
            context.allow_vote_tool = False
            
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug(f"Principle selection attempt {attempt}/{self.max_retries} for {participant.name}")
                    
                    # Get response from agent with timeout
                    logger.debug(f"Calling agent {participant.name} with prompt length {len(current_prompt)}")
                    result = await self._run_agent(
                        participant=participant,
                        prompt=current_prompt,
                        context=context,
                        interaction_type="ballot",
                        timeout_seconds=self.timeout_seconds
                    )
                    logger.debug(f"Received result from agent {participant.name}: type={type(result)}")
                    
                    # Tool detection removed - no more tool calls to check
                    
                    response = result.final_output.strip() if hasattr(result, 'final_output') else str(result).strip()
                
                    # Validate response
                    validated_value, error_type = self._validate_principle_selection(response)
                    
                    if validated_value is not None:
                        # Success
                        voting_result = VotingStageResult(
                            participant_name=participant.name,
                            stage=stage,
                            success=True,
                            value=validated_value,
                            raw_response=response,
                            attempts_used=attempt
                        )
                        
                        self._log_voting_success(participant.name, stage, response, validated_value, attempt)
                        return voting_result
                    else:
                        # Validation failed - prepare retry prompt
                        if attempt < self.max_retries:
                            try:
                                # Use enhanced language manager method for two-stage error messages
                                error_msg = self.language_manager.get_two_stage_error_message(
                                    error_type, attempt, self.max_retries
                                )
                            except Exception as e:
                                logger.warning(f"Failed to get two-stage error message: {e}")
                                error_msg = self._get_fallback_error_message(error_type, attempt)
                            
                            current_prompt = f"{error_msg}\n\n{base_prompt}"
                            self._log_voting_retry(participant.name, stage, response, error_type, attempt)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout in principle selection for {participant.name}, attempt {attempt}")
                    if attempt < self.max_retries:
                        try:
                            # Use enhanced language manager method for timeout messages
                            timeout_msg = self.language_manager.get_two_stage_timeout_message()
                        except Exception as e:
                            logger.warning(f"Failed to get timeout message: {e}")
                            timeout_msg = self.language_manager.get(
                                "voting.timeout_fallback",
                                default="Response timed out. Please try again."
                            )
                        current_prompt = f"{timeout_msg}\n\n{base_prompt}"
                    
                except Exception as e:
                    logger.error(f"Error in principle selection for {participant.name}, attempt {attempt}: {e}")
            
            # All retries exhausted
            self._log_voting_failure(participant.name, stage, self.max_retries)
            return VotingStageResult(
                participant_name=participant.name,
                stage=stage,
                success=False,
                value=None,
                raw_response="",
                attempts_used=self.max_retries,
                error_type="retries_exhausted"
            )
            
        finally:
            # Always restore original tool setting
            context.allow_vote_tool = original_tool_setting
            logger.debug(f"Restored vote tool setting for {participant.name}: {original_tool_setting}")

    async def _conduct_amount_specification_with_retry(
        self, 
        participant: Any, 
        context: Any, 
        principle_num: int
    ) -> Optional[VotingStageResult]:
        """
        Conduct Stage 2 (amount specification) with retry logic.
        
        Args:
            participant: ParticipantAgent object
            context: ParticipantContext object
            principle_num: Selected principle number (3 or 4)
            
        Returns:
            VotingStageResult with constraint amount or None if failed
        """
        stage = "amount_specification"
        principle_name = self._get_principle_display_name(principle_num)
        
        try:
            # Use enhanced language manager method for two-stage amount specification
            logger.debug(f"Attempting to get two-stage amount specification prompt for participant {participant.name}, principle {principle_name}")
            base_prompt = self.language_manager.get_two_stage_amount_specification_prompt(principle_name)
            logger.debug(f"Successfully retrieved two-stage amount specification prompt")
        except Exception as e:
            logger.error(f"Failed to get two-stage amount prompt for {participant.name}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Principle name: {principle_name}")
            base_prompt = self._get_fallback_amount_prompt(principle_name)
            logger.warning(f"Using fallback amount prompt for {participant.name}")
        
        current_prompt = base_prompt
        
        # Store original tool setting to restore later
        original_tool_setting = getattr(context, 'allow_vote_tool', True)
        
        try:
            # Disable voting tool during ballot phase
            context.allow_vote_tool = False
            
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug(f"Amount specification attempt {attempt}/{self.max_retries} for {participant.name}")
                    
                    # Get response from agent with timeout
                    logger.debug(f"Calling agent {participant.name} for amount with prompt length {len(current_prompt)}")
                    # Set interaction type for ballot (disables propose_vote tool)
                    context.interaction_type = "ballot"
                    result = await self._run_agent(
                        participant=participant,
                        prompt=current_prompt,
                        context=context,
                        interaction_type="ballot",
                        timeout_seconds=self.timeout_seconds
                    )
                    logger.debug(f"Received amount result from agent {participant.name}: type={type(result)}")
                    
                    # Tool detection removed - no more tool calls to check
                    
                    response = result.final_output.strip() if hasattr(result, 'final_output') else str(result).strip()
                    
                    # Validate response
                    validated_value, error_type = self._validate_amount_specification(response)
                    
                    if validated_value is not None:
                        # Success
                        voting_result = VotingStageResult(
                            participant_name=participant.name,
                            stage=stage,
                            success=True,
                            value=validated_value,
                            raw_response=response,
                            attempts_used=attempt
                        )
                        
                        self._log_voting_success(participant.name, stage, response, validated_value, attempt)
                        return voting_result
                    else:
                        # Validation failed - prepare retry prompt
                        if attempt < self.max_retries:
                            try:
                                # Use enhanced language manager method for two-stage error messages
                                error_msg = self.language_manager.get_two_stage_error_message(
                                    error_type, attempt, self.max_retries
                                )
                            except Exception as e:
                                logger.warning(f"Failed to get two-stage error message: {e}")
                                error_msg = self._get_fallback_error_message(error_type, attempt)
                            
                            current_prompt = f"{error_msg}\n\n{base_prompt}"
                            self._log_voting_retry(participant.name, stage, response, error_type, attempt)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout in amount specification for {participant.name}, attempt {attempt}")
                    if attempt < self.max_retries:
                        try:
                            # Use enhanced language manager method for timeout messages
                            timeout_msg = self.language_manager.get_two_stage_timeout_message()
                        except Exception as e:
                            logger.warning(f"Failed to get timeout message: {e}")
                            timeout_msg = self.language_manager.get(
                                "voting.timeout_fallback",
                                default="Response timed out. Please try again."
                            )
                        current_prompt = f"{timeout_msg}\n\n{base_prompt}"
                    
                except Exception as e:
                    logger.error(f"Error in amount specification for {participant.name}, attempt {attempt}: {e}")
            
            # All retries exhausted
            self._log_voting_failure(participant.name, stage, self.max_retries)
            return VotingStageResult(
                participant_name=participant.name,
                stage=stage,
                success=False,
                value=None,
                raw_response="",
                attempts_used=self.max_retries,
                error_type="retries_exhausted"
            )
            
        finally:
            # Always restore original tool setting
            context.allow_vote_tool = original_tool_setting
            logger.debug(f"Restored vote tool setting for {participant.name}: {original_tool_setting}")

    def _validate_principle_selection(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Enhanced principle selection validation with keyword fallback support.
        
        Priority order:
        1. Numerical format validation (1-4)
        2. Keyword matching fallback across languages
        3. Error classification for user feedback
        
        Args:
            response: Raw agent response
            
        Returns:
            Tuple of (validated_value, error_type)
            - validated_value: 1-4 if valid, None if invalid
            - error_type: string describing error type for user feedback
        """
        if not response:
            return None, "empty_response"
            
        response_stripped = response.strip()
        
        # Stage 1: Try numerical format validation (preferred method)
        numerical_result, numerical_error = self._validate_numerical_principle_selection(response_stripped)
        if numerical_result is not None:
            logger.debug(f"Principle selection validated numerically: '{response_stripped}' -> {numerical_result}")
            return numerical_result, None
        
        # Stage 2: Try keyword matching fallback
        keyword_result, confidence = self._validate_keyword_principle_selection(response_stripped)
        if keyword_result is not None:
            logger.info(f"Principle selection validated via keywords: '{response_stripped[:50]}...' -> {keyword_result} (confidence: {confidence:.2f})")
            return keyword_result, None
        
        # Stage 3: Classify error for helpful user feedback
        error_type = self._classify_principle_selection_error(response_stripped, numerical_error)
        logger.debug(f"Principle selection validation failed: '{response_stripped}' -> {error_type}")
        return None, error_type
    
    def _validate_numerical_principle_selection(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Validate numerical principle selection (1-4).
        
        Args:
            response: Cleaned response string
            
        Returns:
            Tuple of (validated_value, error_type) for numerical validation only
        """
        # First, try forgiving digit extraction - find all valid digits (1-4) in response
        valid_digits = re.findall(r'[1-4]', response)
        
        if len(valid_digits) == 1:
            # Exactly one valid digit found - use it
            return int(valid_digits[0]), None
        elif len(valid_digits) > 1:
            # Multiple valid digits found - ambiguous
            return None, "multiple_valid_numbers"
        
        # No valid digits found, check for common error patterns
        if re.match(r'^[5-9]$', response) or re.match(r'^[0-9]{2,}$', response):
            return None, "number_out_of_range"
            
        if response == "0":
            return None, "zero_not_valid"
        
        # Not a numerical format - will try keyword fallback
        return None, "not_numerical"
    
    def _validate_keyword_principle_selection(self, response: str) -> Tuple[Optional[int], float]:
        """
        Validate principle selection using keyword matching fallback.
        
        Args:
            response: Response text to analyze for keywords
            
        Returns:
            Tuple of (principle_number, confidence_score)
        """
        try:
            # Detect language from response content
            detected_language = detect_language_from_response(response)
            
            # Use keyword matcher to find principle
            principle_num, confidence = match_principle_from_text(response, detected_language)
            
            # Apply confidence threshold for acceptance
            min_confidence_threshold = 0.3  # Configurable threshold - lowered for better coverage
            if principle_num is not None and confidence >= min_confidence_threshold:
                logger.debug(f"Keyword matching successful: language={detected_language.value}, "
                           f"principle={principle_num}, confidence={confidence:.2f}")
                return principle_num, confidence
            else:
                logger.debug(f"Keyword matching below threshold: principle={principle_num}, "
                           f"confidence={confidence:.2f}, threshold={min_confidence_threshold}")
                return None, confidence
                
        except Exception as e:
            logger.warning(f"Error in keyword matching fallback: {e}")
            return None, 0.0
    
    def _classify_principle_selection_error(self, response: str, numerical_error: Optional[str]) -> str:
        """
        Classify principle selection error for helpful user feedback.
        
        Args:
            response: Original response text
            numerical_error: Error from numerical validation, if any
            
        Returns:
            Error type string for user feedback
        """
        response_lower = response.lower()
        
        # Handle common error patterns
        if numerical_error in ["respond_with_number_only", "number_out_of_range", "zero_not_valid"]:
            return numerical_error
            
        if response_lower in ["one", "two", "three", "four", "uno", "dos", "tres", "cuatro", "一", "二", "三", "四"]:
            return "use_digits_not_words"
            
        if len(response) > 100:
            return "response_too_long"
            
        if any(word in response_lower for word in ['a', 'b', 'c', 'd']):
            return "no_letter_choices"
            
        # Check if response contains principle-related content but failed matching
        principle_related_terms = ['principle', 'income', 'average', 'floor', 'constraint', 
                                  'principio', 'ingreso', 'promedio', 'restricción',
                                  '原则', '收入', '平均', '约束']
        if any(term in response_lower for term in principle_related_terms):
            return "principle_content_unclear"
        
        # Default fallback error
        return "invalid_format_general"

    def _validate_amount_specification(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Validate amount specification response using cultural adaptation.
        
        Args:
            response: Raw agent response
            
        Returns:
            Tuple of (validated_value, error_type)
            - validated_value: positive integer if valid, None if invalid
            - error_type: string describing error type for user feedback
        """
        try:
            # Use cultural adaptation for amount validation
            validated_value, error_type = self.amount_formatter.validate_amount_input(response)
            
            if validated_value is not None:
                # Apply additional range validation if configured
                amount_range_validation = getattr(self.settings, 'amount_range_validation', True) if self.settings else True
                if amount_range_validation:
                    amount_min_reasonable = getattr(self.settings, 'amount_min_reasonable', 1000) if self.settings else 1000
                    amount_max_reasonable = getattr(self.settings, 'amount_max_reasonable', 100000) if self.settings else 100000
                    if validated_value < amount_min_reasonable:
                        return None, "amount_too_low"
                    elif validated_value > amount_max_reasonable:
                        return None, "amount_too_high"
                
                return validated_value, None
            else:
                return None, error_type
                
        except Exception as e:
            logger.warning(f"Failed to use cultural adaptation for amount validation: {e}")
            # Fallback to basic validation
            return self._fallback_amount_validation(response)
    
    def _fallback_amount_validation(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """Fallback amount validation if cultural adaptation fails."""
        response = response.strip()
        
        # Allow $ symbol - strip it for validation
        clean_response = response
        if response.startswith('$'):
            clean_response = response[1:].strip()
        
        # Remove commas for validation
        clean_response = clean_response.replace(',', '')
        
        # Check for valid positive integer
        if re.match(r'^[1-9][0-9]*$', clean_response):
            try:
                amount = int(clean_response)
                
                # Range validation (if enabled)
                amount_range_validation = getattr(self.settings, 'amount_range_validation', True) if self.settings else True
                if amount_range_validation:
                    amount_min_reasonable = getattr(self.settings, 'amount_min_reasonable', 1000) if self.settings else 1000
                    amount_max_reasonable = getattr(self.settings, 'amount_max_reasonable', 100000) if self.settings else 100000
                    if amount < amount_min_reasonable:
                        return None, "amount_too_low"
                    elif amount > amount_max_reasonable:
                        return None, "amount_too_high"
                
                return amount, None
                
            except ValueError:
                return None, "invalid_number_format"
        
        # Common error patterns
        if clean_response.startswith('0') or clean_response == '0':
            return None, "amount_must_be_positive"
            
        if '.' in clean_response:
            return None, "whole_numbers_only"
            
        if clean_response.startswith('-'):
            return None, "no_negative_amounts"
            
        if any(char.isalpha() for char in clean_response):
            return None, "no_text_in_amount"
            
        if not clean_response:
            return None, "empty_amount_response"
        
        # Default error
        return None, "invalid_amount_format"

    def _get_principle_display_name(self, principle_num: int) -> str:
        """Get display name for principle number using PrincipleNameManager."""
        try:
            # Use PrincipleNameManager for multilingual principle names
            return self.principle_name_manager.get_principle_display_name(principle_num)
        except Exception as e:
            logger.warning(f"Failed to get principle display name: {e}")
            # Fallback to hardcoded names
            names = {
                1: "Maximizing Floor Income",
                2: "Maximizing Average Income", 
                3: "Maximizing Average with Floor Constraint",
                4: "Maximizing Average with Range Constraint"
            }
            return names.get(principle_num, f"Principle {principle_num}")

    def _convert_to_principle_choice(self, vote: ParticipantVote) -> PrincipleChoice:
        """
        Convert ParticipantVote to PrincipleChoice format for consensus checking.
        """
        # Map principle numbers to JusticePrinciple enum values
        principle_map = {
            1: JusticePrinciple.MAXIMIZING_FLOOR,
            2: JusticePrinciple.MAXIMIZING_AVERAGE,
            3: JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            4: JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        }
        
        principle = principle_map.get(vote.principle_num)
        if principle is None:
            raise ValueError(f"Invalid principle number: {vote.principle_num}")
        
        return PrincipleChoice(
            principle=principle,
            constraint_amount=vote.constraint_amount,
            certainty=CertaintyLevel.SURE,  # Default certainty for structured voting
            reasoning=f"Selected via two-stage structured voting: principle {vote.principle_num}"
        )

    def _create_vote_result(self, participant_votes: List[ParticipantVote], principle_choices: List[PrincipleChoice]) -> VoteResult:
        """
        Create vote result from participant votes with consensus checking and individual vote details.
        """
        # Check for consensus - all principle choices must be identical
        if not principle_choices:
            logger.warning("No principle choices to evaluate for consensus")
            return VoteResult(
                votes=principle_choices,
                consensus_reached=False,
                agreed_principle=None,
                vote_counts={},
                individual_votes=[],
                disagreement_summary="voting_failed",
                timestamp=datetime.now()
            )
        
        # Group votes by (principle, constraint_amount) for consensus checking
        vote_groups = {}
        vote_counts = {}
        
        for choice in principle_choices:
            # Create a key that includes both principle and constraint amount
            key = (choice.principle.value, choice.constraint_amount)
            
            if key not in vote_groups:
                vote_groups[key] = []
                vote_counts[f"{choice.principle.value}_{choice.constraint_amount or 'none'}"] = 0
            
            vote_groups[key].append(choice)
            vote_counts[f"{choice.principle.value}_{choice.constraint_amount or 'none'}"] += 1
        
        # Consensus reached if all votes are in a single group
        consensus_reached = len(vote_groups) == 1
        agreed_principle = None
        disagreement_summary = None

        if consensus_reached:
            # Get the agreed principle (first choice since all are identical)
            agreed_principle = principle_choices[0]
            logger.info(f"Consensus reached: {agreed_principle.principle.value} with constraint {agreed_principle.constraint_amount}")
        else:
            logger.info(f"No consensus reached: {len(vote_groups)} different vote combinations")

            # Generate disagreement summary with language keys for localization
            principles_voted = set()
            constraint_amounts = {}

            for (principle, constraint), choices in vote_groups.items():
                principles_voted.add(principle)
                if principle not in constraint_amounts:
                    constraint_amounts[principle] = set()
                if constraint is not None:
                    constraint_amounts[principle].add(constraint)

            if len(principles_voted) > 1:
                # Different principles chosen - use language key
                disagreement_summary = "principle_disagreement"
            else:
                # Same principle but different constraints
                principle = list(principles_voted)[0]
                amounts = constraint_amounts[principle]
                if len(amounts) > 1:
                    # Store both the type and details for proper localization
                    disagreement_summary = f"constraint_disagreement:{principle}:{','.join(str(a) for a in sorted(amounts))}"
                else:
                    disagreement_summary = "mixed_disagreement"
        
        # Build individual vote details from ParticipantVote objects
        individual_votes = []
        for vote in participant_votes:
            # Convert principle number to readable name
            principle_name = self._get_principle_display_name(vote.principle_num)
            
            # Combine raw responses from both stages
            raw_response = ""
            if vote.principle_selection_result:
                raw_response = vote.principle_selection_result.raw_response
                if vote.amount_specification_result:
                    raw_response += f" | {vote.amount_specification_result.raw_response}"
            
            # Determine parsing success (both stages must succeed)
            parsing_success = (
                vote.principle_selection_result is not None and 
                vote.principle_selection_result.success and
                (vote.amount_specification_result is None or vote.amount_specification_result.success)
            )
            
            # Create individual vote detail
            individual_vote = {
                "participant_name": vote.participant_name,
                "assessed_choice": principle_name,
                "constraint_amount": vote.constraint_amount,
                "raw_response": raw_response,
                "parsing_success": parsing_success,
                "vote_timestamp": datetime.now().isoformat()
            }
            
            individual_votes.append(individual_vote)
        
        return VoteResult(
            votes=principle_choices,
            consensus_reached=consensus_reached,
            agreed_principle=agreed_principle,
            vote_counts=vote_counts,
            individual_votes=individual_votes,
            disagreement_summary=disagreement_summary,
            timestamp=datetime.now()
        )

    def _create_failure_vote_result(self, participant_votes: List[ParticipantVote]) -> VoteResult:
        """
        Create vote result for failed votes, capturing partial data that was collected.
        
        Args:
            participant_votes: List of ParticipantVote objects (some may be incomplete)
            
        Returns:
            VoteResult with consensus_reached=False and individual_votes containing partial data
        """
        # Build individual vote details from partial ParticipantVote objects
        individual_votes = []
        for vote in participant_votes:
            # Convert principle number to readable name if available
            principle_name = "Unknown"
            if vote.principle_num is not None:
                try:
                    principle_name = self._get_principle_display_name(vote.principle_num)
                except Exception as e:
                    logger.warning(f"Failed to get principle display name for {vote.principle_num}: {e}")
                    principle_name = f"Principle {vote.principle_num}"
            
            # Combine raw responses from available stages
            raw_response = ""
            if vote.principle_selection_result:
                raw_response = vote.principle_selection_result.raw_response
                if vote.amount_specification_result:
                    raw_response += f" | {vote.amount_specification_result.raw_response}"
            elif vote.amount_specification_result:
                # Edge case: only amount specification available
                raw_response = vote.amount_specification_result.raw_response
            
            # Determine parsing success for available stages
            parsing_success = False
            if vote.principle_selection_result:
                parsing_success = (
                    vote.principle_selection_result.success and
                    (vote.amount_specification_result is None or vote.amount_specification_result.success)
                )
            
            # Create individual vote detail with partial data
            individual_vote = {
                "participant_name": vote.participant_name,
                "assessed_choice": principle_name,
                "constraint_amount": vote.constraint_amount,
                "raw_response": raw_response,
                "parsing_success": parsing_success,
                "vote_timestamp": datetime.now().isoformat()
            }
            
            individual_votes.append(individual_vote)
        
        return VoteResult(
            votes=[],  # No valid principle choices since voting failed
            consensus_reached=False,
            agreed_principle=None,
            vote_counts={},
            individual_votes=individual_votes,
            disagreement_summary="voting_failed",
            timestamp=datetime.now()
        )

    async def _run_agent(
        self,
        participant: Any,
        prompt: str,
        context: Any,
        interaction_type: str,
        timeout_seconds: Optional[float]
    ) -> Any:
        """Run participant interaction with transcript support and optional timeout."""

        context.interaction_type = interaction_type

        if hasattr(participant, "agent"):
            coroutine = run_with_transcript_logging(
                participant=participant,
                prompt=prompt,
                context=context,
                transcript_logger=getattr(self, "transcript_logger", None),
                interaction_type=interaction_type
            )
        else:
            coroutine = Runner.run(participant, prompt, context=context)

        if timeout_seconds is not None:
            return await asyncio.wait_for(coroutine, timeout_seconds)
        return await coroutine

    # Fallback methods for when language manager is not available
    def _get_fallback_principle_prompt(self) -> str:
        """Fallback principle selection prompt using language manager."""
        try:
            return self.language_manager.get(
                "voting.fallback_principle_prompt",
                default="""A vote has been initiated. Which of the four principles do you want to vote for?

1. Maximizing Floor Income
2. Maximizing Average Income 
3. Maximizing Average with Floor Constraint
4. Maximizing Average with Range Constraint

Respond with ONLY the number (1, 2, 3, or 4):"""
            )
        except Exception:
            return """A vote has been initiated. Which of the four principles do you want to vote for?

1. Maximizing Floor Income
2. Maximizing Average Income 
3. Maximizing Average with Floor Constraint
4. Maximizing Average with Range Constraint

Respond with ONLY the number (1, 2, 3, or 4):"""

    def _get_fallback_amount_prompt(self, principle_name: str) -> str:
        """Fallback amount specification prompt using language manager."""
        try:
            return self.language_manager.get(
                "voting.fallback_amount_prompt",
                principle_name=principle_name,
                default=f"""You chose {principle_name}. Please state the amount in dollars as a whole positive number.

Respond with the amount (examples: 25000 or $25000):"""
            )
        except Exception:
            return f"""You chose {principle_name}. Please state the amount in dollars as a whole positive number.

Respond with the amount (examples: 25000 or $25000):"""

    def _get_fallback_error_message(self, error_type: str, attempt: int) -> str:
        """Fallback error messages in English."""
        messages = {
            # Numerical validation errors
            "respond_with_number_only": f"Invalid response (attempt {attempt}/{self.max_retries}). You must respond with exactly one number: 1, 2, 3, or 4.",
            "use_digits_not_words": f"Invalid response (attempt {attempt}/{self.max_retries}). Please use digits (1, 2, 3, or 4), not words.",
            "number_out_of_range": f"Invalid response (attempt {attempt}/{self.max_retries}). You must respond with 1, 2, 3, or 4 only.",
            "zero_not_valid": f"Invalid response (attempt {attempt}/{self.max_retries}). Zero is not a valid principle choice. Use 1, 2, 3, or 4.",
            "multiple_valid_numbers": f"Multiple numbers detected (attempt {attempt}/{self.max_retries}). Please respond with only ONE number: 1, 2, 3, or 4.",
            "response_too_long": f"Invalid response (attempt {attempt}/{self.max_retries}). Please respond with just the number.",
            "empty_response": f"Empty response (attempt {attempt}/{self.max_retries}). Please respond with 1, 2, 3, or 4.",
            
            # Keyword validation errors (new)
            "no_letter_choices": f"Invalid response (attempt {attempt}/{self.max_retries}). Don't use letters (a, b, c, d). Use numbers: 1, 2, 3, or 4.",
            "principle_content_unclear": f"Unclear principle choice (attempt {attempt}/{self.max_retries}). Please respond with the number of your preferred principle: 1, 2, 3, or 4.",
            "invalid_format_general": f"Invalid response (attempt {attempt}/{self.max_retries}). You must respond with exactly one number: 1, 2, 3, or 4.",
            
            # Amount validation errors
            "amount_must_be_positive": f"Invalid amount (attempt {attempt}/{self.max_retries}). You must respond with a positive whole dollar amount.",
            "whole_numbers_only": f"Invalid amount format (attempt {attempt}/{self.max_retries}). You must respond with a whole dollar amount (no decimals).",
            "no_negative_amounts": f"Invalid amount (attempt {attempt}/{self.max_retries}). Negative amounts are not allowed.",
            "no_text_in_amount": f"Invalid amount format (attempt {attempt}/{self.max_retries}). You must respond with a number only.",
            "empty_amount_response": f"Empty response (attempt {attempt}/{self.max_retries}). Please provide a dollar amount.",
            "invalid_amount_format": f"Invalid amount format (attempt {attempt}/{self.max_retries}). You must respond with a positive whole dollar amount.",
            "amount_too_low": f"Amount too low (attempt {attempt}/{self.max_retries}). Please provide a realistic dollar amount (minimum ${getattr(self.settings, 'amount_min_reasonable', 1000) if self.settings else 1000:,}).",
            "amount_too_high": f"Amount too high (attempt {attempt}/{self.max_retries}). Please provide a realistic dollar amount (maximum ${getattr(self.settings, 'amount_max_reasonable', 100000) if self.settings else 100000:,}).",
            
            # New text extraction errors
            "no_amount_found": f"No monetary amount found (attempt {attempt}/{self.max_retries}). Please clearly state a dollar amount (e.g., $10,000 or 25000).",
            "multiple_different_amounts_found": f"Multiple different amounts detected (attempt {attempt}/{self.max_retries}). Please specify exactly one dollar amount clearly."
        }
        # Try to get localized error message first
        try:
            return self.language_manager.get(
                f"voting.error_messages.{error_type}",
                attempt=attempt,
                max_retries=self.max_retries,
                default=messages.get(error_type, f"Invalid response (attempt {attempt}/{self.max_retries}). Please try again.")
            )
        except Exception:
            return messages.get(error_type, f"Invalid response (attempt {attempt}/{self.max_retries}). Please try again.")

    # Logging methods
    def _log_voting_success(self, participant_name: str, stage: str, response: str, value: int, attempt: int):
        """Log successful voting stage completion."""
        if self.logger:
            try:
                # Try to use existing logger method if available
                if hasattr(self.logger, 'log_two_stage_voting_success'):
                    self.logger.log_two_stage_voting_success(participant_name, stage, response, value, attempt)
                else:
                    logger.info(f"Two-stage voting success - {participant_name} {stage}: '{response}' -> {value} (attempt {attempt})")
            except Exception as e:
                logger.warning(f"Failed to log voting success: {e}")
        else:
            logger.info(f"Two-stage voting success - {participant_name} {stage}: '{response}' -> {value} (attempt {attempt})")

    def _log_voting_retry(self, participant_name: str, stage: str, response: str, error_type: str, attempt: int):
        """Log voting retry attempt."""
        if self.logger:
            try:
                if hasattr(self.logger, 'log_two_stage_voting_retry'):
                    self.logger.log_two_stage_voting_retry(participant_name, stage, response, error_type, attempt)
                else:
                    logger.warning(f"Two-stage voting retry - {participant_name} {stage}: '{response}' -> {error_type} (attempt {attempt})")
            except Exception as e:
                logger.warning(f"Failed to log voting retry: {e}")
        else:
            logger.warning(f"Two-stage voting retry - {participant_name} {stage}: '{response}' -> {error_type} (attempt {attempt})")

    def _log_voting_failure(self, participant_name: str, stage: str, max_attempts: int):
        """Log voting stage failure after all retries exhausted."""
        if self.logger:
            try:
                if hasattr(self.logger, 'log_two_stage_voting_failure'):
                    self.logger.log_two_stage_voting_failure(participant_name, stage, max_attempts)
                else:
                    logger.error(f"Two-stage voting failure - {participant_name} {stage}: all {max_attempts} attempts exhausted")
            except Exception as e:
                logger.warning(f"Failed to log voting failure: {e}")
        else:
            logger.error(f"Two-stage voting failure - {participant_name} {stage}: all {max_attempts} attempts exhausted")
    
    # REMOVED: _update_participant_memory_for_voting_with_consensus()
    # This method contained Call 1 (redundant short format memory update)
    # Memory updates are now handled by CounterfactualsService.deliver_results_and_update_memory()
    # which provides comprehensive results with consensus information (Call 2)

    async def _update_participant_memory_for_voting(
        self, 
        participant: Any, 
        context: Any, 
        participant_vote: ParticipantVote,
        discussion_state: Any
    ):
        """
        Update participant memory with their two-stage voting experience.
        
        DEPRECATED: This method always passes consensus_reached=False.
        Use _update_participant_memory_for_voting_with_consensus() instead for correct consensus info.
        """
        try:
            # Build complete voting memory content
            principle_display_name = self._get_principle_display_name(participant_vote.principle_num)
            
            # Calculate total stages and attempts
            total_stages = 1 if participant_vote.constraint_amount is None else 2
            total_attempts = (
                (participant_vote.principle_selection_result.attempts_used if participant_vote.principle_selection_result else 1) +
                (participant_vote.amount_specification_result.attempts_used if participant_vote.amount_specification_result else 0)
            )
            
            # Build memory content using our new memory content builders
            memory_content = build_two_stage_voting_complete_delta(
                participant_name=participant_vote.participant_name,
                principle_num=participant_vote.principle_num,
                principle_display_name=principle_display_name,
                constraint_amount=participant_vote.constraint_amount,
                consensus_reached=False,  # Not determined yet at this point
                agreed_principle=None,    # Not determined yet at this point
                total_stages=total_stages,
                total_attempts=total_attempts,
                language_manager=self.language_manager
            )
            
            # Update participant memory using the MemoryManager
            # Use MemoryService/ExperimentConfiguration as the single source of truth for memory mode
            memory_guidance_style = getattr(self.memory_service, 'memory_guidance_style', 'narrative') if hasattr(self, 'memory_service') and self.memory_service else 'narrative'
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant,
                context,
                memory_content,
                memory_guidance_style=memory_guidance_style,
                language_manager=self.language_manager,
                error_handler=self.error_handler,
                utility_agent=self.utility_agent,
                round_number=getattr(context, 'round_number', None),
                phase=getattr(context, 'phase', None),
                transcript_logger=self.transcript_logger
            )
            
            logger.info(f"Updated memory for {participant.name} after two-stage voting")
            
        except Exception as e:
            logger.warning(f"Failed to update memory for {participant.name} after voting: {e}")
            # Don't fail the entire voting process due to memory update issues
