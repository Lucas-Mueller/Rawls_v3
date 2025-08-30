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

# Import multilingual support components  
from utils.cultural_adaptation import get_amount_formatter, SupportedLanguage as CulturalLanguage
from core.principle_name_manager import get_principle_name_manager

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
    
    def __init__(self, participants: List[Any], language_manager: Any, logger: Any, settings: Any = None):
        """
        Initialize the two-stage voting manager.
        
        Args:
            participants: List of ParticipantAgent objects
            language_manager: LanguageManager instance for multilingual support
            logger: AgentCentricLogger instance for vote tracking
            settings: Phase2Settings instance with voting configuration
        """
        self.participants = participants
        self.language_manager = language_manager
        self.logger = logger
        self.settings = settings
        
        # Initialize multilingual support components
        self.amount_formatter = get_amount_formatter()
        self.principle_name_manager = get_principle_name_manager()
        
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
            logger.error("Mismatch between participants and contexts")
            return None
        
        participant_votes = []
        
        for i, context in enumerate(contexts):
            participant = self.participants[i]
            
            logger.info(f"Starting two-stage voting for {participant.name}")
            
            # Stage 1: Principle Selection
            principle_result = await self._conduct_principle_selection_with_retry(participant, context)
            
            if not principle_result or not principle_result.success:
                logger.warning(f"Stage 1 failed for {participant.name}")
                return None  # Voting failed
            
            principle_num = principle_result.value
            
            # Stage 2: Amount specification (if needed)
            amount_result = None
            constraint_amount = None
            
            if principle_num in [3, 4]:  # Constraint principles
                amount_result = await self._conduct_amount_specification_with_retry(
                    participant, context, principle_num
                )
                
                if not amount_result or not amount_result.success:
                    logger.warning(f"Stage 2 failed for {participant.name}")
                    return None  # Voting failed
                
                constraint_amount = amount_result.value
            
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
            
            # Update participant memory with their two-stage voting experience
            await self._update_participant_memory_for_voting(
                participant, context, participant_vote, discussion_state
            )
        
        # Convert to principle choices for consensus checking
        try:
            principle_choices = [self._convert_to_principle_choice(vote) for vote in participant_votes]
            
            # Use existing consensus checking logic (this would be imported from the existing system)
            # For now, we'll return a mock success result
            # TODO: Integrate with actual consensus checking logic in Phase 3
            
            logger.info("Two-stage voting completed successfully for all participants")
            return self._create_vote_result(participant_votes, principle_choices)
            
        except Exception as e:
            logger.error(f"Error processing voting results: {e}")
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
            # Use enhanced language manager method for two-stage prompts
            base_prompt = self.language_manager.get_two_stage_principle_selection_prompt()
        except Exception as e:
            logger.warning(f"Failed to get two-stage principle prompt: {e}")
            # Fallback prompt if translation system not available
            base_prompt = self._get_fallback_principle_prompt()
        
        current_prompt = base_prompt
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Principle selection attempt {attempt}/{self.max_retries} for {participant.name}")
                
                # Get response from agent with timeout
                result = await asyncio.wait_for(
                    self._run_agent(participant.agent, current_prompt, context),
                    timeout=self.timeout_seconds
                )
                
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
                        timeout_msg = "Response timed out. Please try again."
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
            base_prompt = self.language_manager.get_two_stage_amount_specification_prompt(principle_name)
        except Exception as e:
            logger.warning(f"Failed to get two-stage amount prompt: {e}")
            base_prompt = self._get_fallback_amount_prompt(principle_name)
        
        current_prompt = base_prompt
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Amount specification attempt {attempt}/{self.max_retries} for {participant.name}")
                
                # Get response from agent with timeout
                result = await asyncio.wait_for(
                    self._run_agent(participant.agent, current_prompt, context),
                    timeout=self.timeout_seconds
                )
                
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
                        timeout_msg = "Response timed out. Please try again."
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

    def _validate_principle_selection(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Validate principle selection response using regex.
        
        Args:
            response: Raw agent response
            
        Returns:
            Tuple of (validated_value, error_type)
            - validated_value: 1-4 if valid, None if invalid
            - error_type: string describing error type for user feedback
        """
        response = response.strip()
        
        # Check for exact match: single digit 1-4
        if re.match(r'^[1-4]$', response):
            return int(response), None
        
        # Common error patterns with specific error messages
        if re.match(r'^[1-4]\D+', response):  # "1." or "1 - Principle One"
            return None, "respond_with_number_only"
            
        if response.lower() in ["one", "two", "three", "four", "uno", "dos", "tres", "cuatro", "一", "二", "三", "四"]:
            return None, "use_digits_not_words"
            
        if re.match(r'^[5-9]$', response) or re.match(r'^[0-9]{2,}$', response):
            return None, "number_out_of_range"
            
        if response == "0":
            return None, "zero_not_valid"
            
        if len(response) > 20:
            return None, "response_too_long"
            
        if not response:
            return None, "empty_response"
        
        # Default error for unrecognized patterns
        return None, "invalid_format_general"

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
        Create vote result from participant votes with consensus checking.
        """
        # Check for consensus - all principle choices must be identical
        if not principle_choices:
            logger.warning("No principle choices to evaluate for consensus")
            return VoteResult(
                votes=principle_choices,
                consensus_reached=False,
                agreed_principle=None,
                vote_counts={},
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
        
        if consensus_reached:
            # Get the agreed principle (first choice since all are identical)
            agreed_principle = principle_choices[0]
            logger.info(f"Consensus reached: {agreed_principle.principle.value} with constraint {agreed_principle.constraint_amount}")
        else:
            logger.info(f"No consensus reached: {len(vote_groups)} different vote combinations")
        
        return VoteResult(
            votes=principle_choices,
            consensus_reached=consensus_reached,
            agreed_principle=agreed_principle,
            vote_counts=vote_counts,
            timestamp=datetime.now()
        )

    async def _run_agent(self, agent: Any, prompt: str, context: Any) -> Any:
        """
        Run agent with given prompt and context using the actual Runner system.
        """
        return await Runner.run(agent, prompt, context=context)

    # Fallback methods for when language manager is not available
    def _get_fallback_principle_prompt(self) -> str:
        """Fallback principle selection prompt in English."""
        return """A vote has been initiated. Which of the four principles do you want to vote for?

1. Maximizing Floor Income
2. Maximizing Average Income 
3. Maximizing Average with Floor Constraint
4. Maximizing Average with Range Constraint

Respond with ONLY the number (1, 2, 3, or 4):"""

    def _get_fallback_amount_prompt(self, principle_name: str) -> str:
        """Fallback amount specification prompt in English."""
        return f"""You chose {principle_name}. Please state the amount in dollars as a whole positive number.

Respond with the amount (examples: 25000 or $25000):"""

    def _get_fallback_error_message(self, error_type: str, attempt: int) -> str:
        """Fallback error messages in English."""
        messages = {
            "respond_with_number_only": f"Invalid response (attempt {attempt}/{self.max_retries}). You must respond with exactly one number: 1, 2, 3, or 4.",
            "use_digits_not_words": f"Invalid response (attempt {attempt}/{self.max_retries}). Please use digits (1, 2, 3, or 4), not words.",
            "number_out_of_range": f"Invalid response (attempt {attempt}/{self.max_retries}). You must respond with 1, 2, 3, or 4 only.",
            "zero_not_valid": f"Invalid response (attempt {attempt}/{self.max_retries}). Zero is not a valid principle choice. Use 1, 2, 3, or 4.",
            "response_too_long": f"Invalid response (attempt {attempt}/{self.max_retries}). Please respond with just the number.",
            "empty_response": f"Empty response (attempt {attempt}/{self.max_retries}). Please respond with 1, 2, 3, or 4.",
            "invalid_format_general": f"Invalid response (attempt {attempt}/{self.max_retries}). You must respond with exactly one number: 1, 2, 3, or 4.",
            "amount_must_be_positive": f"Invalid amount (attempt {attempt}/{self.max_retries}). You must respond with a positive whole dollar amount.",
            "whole_numbers_only": f"Invalid amount format (attempt {attempt}/{self.max_retries}). You must respond with a whole dollar amount (no decimals).",
            "no_negative_amounts": f"Invalid amount (attempt {attempt}/{self.max_retries}). Negative amounts are not allowed.",
            "no_text_in_amount": f"Invalid amount format (attempt {attempt}/{self.max_retries}). You must respond with a number only.",
            "empty_amount_response": f"Empty response (attempt {attempt}/{self.max_retries}). Please provide a dollar amount.",
            "invalid_amount_format": f"Invalid amount format (attempt {attempt}/{self.max_retries}). You must respond with a positive whole dollar amount.",
            "amount_too_low": f"Amount too low (attempt {attempt}/{self.max_retries}). Please provide a realistic dollar amount (minimum ${getattr(self.settings, 'amount_min_reasonable', 1000) if self.settings else 1000:,}).",
            "amount_too_high": f"Amount too high (attempt {attempt}/{self.max_retries}). Please provide a realistic dollar amount (maximum ${getattr(self.settings, 'amount_max_reasonable', 100000) if self.settings else 100000:,})."
        }
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
    
    async def _update_participant_memory_for_voting(
        self, 
        participant: Any, 
        context: Any, 
        participant_vote: ParticipantVote,
        discussion_state: Any
    ):
        """
        Update participant memory with their two-stage voting experience.
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
                total_attempts=total_attempts
            )
            
            # Update participant memory using the MemoryManager
            memory_guidance_style = getattr(self.settings, 'memory_guidance_style', 'narrative') if self.settings else 'narrative'
            context.memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, memory_content, memory_guidance_style=memory_guidance_style
            )
            
            logger.info(f"Updated memory for {participant.name} after two-stage voting")
            
        except Exception as e:
            logger.warning(f"Failed to update memory for {participant.name} after voting: {e}")
            # Don't fail the entire voting process due to memory update issues