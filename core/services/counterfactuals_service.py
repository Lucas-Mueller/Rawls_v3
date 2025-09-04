"""
Counterfactuals Service for Phase2Manager Refactoring

Provides payoff calculations, counterfactual analysis, detailed results formatting,
and final rankings collection for Phase 2 experiments.

Replaces counterfactual-related methods throughout Phase2Manager with a single,
focused service that handles all payoff logic and results transparency.
"""

import asyncio
import random
from typing import Protocol, Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum

from models import (
    GroupDiscussionResult, PrincipleChoice, JusticePrinciple, IncomeClass,
    PrincipleRanking, RankedPrinciple, CertaintyLevel, ParticipantContext
)
from config import ExperimentConfiguration
from config.phase2_settings import Phase2Settings
from core.distribution_generator import DistributionGenerator
from utils.agent_centric_logger import AgentCentricLogger
from utils.selective_memory_manager import MemoryEventType
from agents import Runner

if TYPE_CHECKING:
    from experiment_agents.participant_agent import ParticipantAgent

import logging

logger = logging.getLogger(__name__)


class LanguageProvider(Protocol):
    """Protocol for language manager dependency."""
    def get(self, key: str, **kwargs) -> str:
        """Get localized text for the given key."""
        ...


class SeedManager(Protocol):
    """Protocol for seed manager dependency."""
    @property
    def random(self):
        """Get the seeded random instance."""
        ...


class Logger(Protocol):
    """Protocol for logger dependency."""
    def info(self, message: str) -> None:
        """Log info message."""
        ...
    
    def warning(self, message: str) -> None:
        """Log warning message."""
        ...
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        ...


class MemoryServiceProvider(Protocol):
    """Protocol for memory service dependency."""
    async def update_final_results_memory(
        self,
        agent: "ParticipantAgent",
        context: ParticipantContext,
        result_content: str,
        final_earnings: float,
        consensus_reached: bool,
        **kwargs
    ) -> str:
        """Update memory with final Phase 2 results."""
        ...


class CounterfactualsService:
    """
    Unified counterfactuals and payoff calculation service for Phase2Manager.
    
    Handles all payoff-related operations including principle application,
    counterfactual earnings calculation, detailed results formatting,
    and final rankings collection.
    
    Key responsibilities:
    - Apply consensus principles or random assignment for payoffs
    - Calculate counterfactual earnings under all 4 principles
    - Build detailed results with transparency and localization
    - Collect final principle rankings from all participants
    - Handle both consensus and non-consensus scenarios
    """
    
    def __init__(
        self,
        language_manager: LanguageProvider,
        settings: Phase2Settings,
        logger: Optional[Logger] = None,
        seed_manager: Optional[SeedManager] = None,
        memory_service: Optional[MemoryServiceProvider] = None
    ):
        """
        Initialize CounterfactualsService with dependencies.
        
        Args:
            language_manager: Provider for localized text
            settings: Phase 2 configuration settings
            logger: Optional logger for service operations
            seed_manager: Optional seed manager for reproducible randomness
            memory_service: Optional memory service for updating participant memory
        """
        self.language_manager = language_manager
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.seed_manager = seed_manager
        self.memory_service = memory_service
    
    async def apply_group_principle_and_calculate_payoffs(
        self,
        discussion_result: GroupDiscussionResult,
        config: ExperimentConfiguration,
        participants: List["ParticipantAgent"]
    ) -> tuple[Dict[str, float], Dict[str, str], Dict[str, Dict[str, float]], Any]:
        """
        Apply chosen principle or random assignment if no consensus.
        
        Updated contract: returns (payoffs, assigned_classes, alternative_earnings_by_agent, distribution_set)
        Handles consensus vs random assignment logic.
        
        Args:
            discussion_result: Result of group discussion with consensus info
            config: Experiment configuration
            participants: List of participant agents
            
        Returns:
            tuple: (payoffs dict, assigned_classes dict, alternative_earnings_by_agent dict, distribution_set)
        """
        try:
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
                for participant in participants:
                    assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution, config.income_class_probabilities, random_gen=self.seed_manager.random if self.seed_manager else None)
                    payoffs[participant.name] = earnings
                    assigned_classes[participant.name] = assigned_class.value
            else:
                # Random assignment - each participant gets random income class from random distribution
                for participant in participants:
                    if self.seed_manager:
                        random_distribution = self.seed_manager.random.choice(distribution_set.distributions)
                    else:
                        random_distribution = random.choice(distribution_set.distributions)
                    assigned_class, earnings = DistributionGenerator.calculate_payoff(random_distribution, config.income_class_probabilities, random_gen=self.seed_manager.random if self.seed_manager else None)
                    payoffs[participant.name] = earnings
                    assigned_classes[participant.name] = assigned_class.value
            
            # Calculate counterfactual earnings for transparency
            alternative_earnings_by_agent = await self.calculate_phase2_counterfactuals(
                distribution_set, assigned_classes, consensus_principle, constraint_amount
            )
            
            self.logger.debug(f"Payoffs calculated for {len(participants)} participants")
            return payoffs, assigned_classes, alternative_earnings_by_agent, distribution_set
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate payoffs: {e}")
            raise
    
    async def calculate_phase2_counterfactuals(
        self,
        distribution_set,
        assigned_classes: Dict[str, str],
        consensus_principle: Optional[PrincipleChoice] = None,
        constraint_amount: Optional[int] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate alternative earnings under all 4 principles for transparency.
        
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
        try:
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
            
            self.logger.debug(f"Counterfactuals calculated for {len(assigned_classes)} participants")
            return alternative_earnings_by_agent
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate counterfactuals: {e}")
            raise
    
    async def build_detailed_results(
        self,
        participant_name: str,
        final_earnings: float,
        assigned_class: str,
        alternative_earnings: Dict[str, float],
        consensus_result: GroupDiscussionResult,
        distribution_set
    ) -> str:
        """
        Build Phase 2 results with comprehensive earnings display.
        
        Build detailed Phase 2 results with comprehensive earnings display
        that includes distributions table and principle outcomes.
        
        Args:
            participant_name: Name of the participant
            final_earnings: Participant's final earnings
            assigned_class: Income class assigned to participant
            alternative_earnings: Alternative earnings under each principle
            consensus_result: Result of group discussion
            distribution_set: The distribution set used for Phase 2
            
        Returns:
            Formatted results string with comprehensive earnings display
        """
        try:
            # Build header and assignment info
            result_parts = []
            
            # Phase 2 header
            phase2_header = self.language_manager.get('results.phase2_header')
            result_parts.append(f"{phase2_header}: ${final_earnings:.2f}")
            
            # Income class assignment
            assigned_class_label = self.language_manager.get(f"common.income_classes.{assigned_class}")
            class_assignment = self.language_manager.get('results.assigned_income_class', class_name=assigned_class_label)
            result_parts.append(class_assignment)
            
            # Consensus information
            if consensus_result.consensus_reached and consensus_result.agreed_principle:
                consensus_msg = self.language_manager.get(
                    "voting_results.consensus_reached", 
                    principle_name=consensus_result.agreed_principle.principle.value
                )
                result_parts.append(consensus_msg + ".")
            else:
                no_consensus_msg = self.language_manager.get("phase2_no_consensus")
                result_parts.append(no_consensus_msg + ".")
            
            # Add comprehensive earnings display
            # Convert string assigned_class to IncomeClass enum
            if assigned_class.startswith('IncomeClass.'):
                # Handle enum string representation like 'IncomeClass.high'
                enum_value = assigned_class.split('.')[1].lower()
            else:
                # Handle direct value like 'high' or 'MEDIUM HIGH' 
                enum_value = assigned_class.lower().replace(' ', '_')
            
            assigned_class_enum = IncomeClass(enum_value)
            
            comprehensive_display = self._build_comprehensive_earnings_display(
                participant_name, assigned_class_enum, distribution_set, consensus_result, self.language_manager
            )
            result_parts.append(f"\n{comprehensive_display}")
            
            return "\n".join(result_parts)
            
        except Exception as e:
            self.logger.warning(f"Failed to build detailed results for {participant_name}: {e}")
            # Fallback to basic format
            return f"Phase 2 results: ${final_earnings:.2f}. Income class: {assigned_class}."
    
    def _get_participant_language_manager(self, participant: "ParticipantAgent"):
        """
        Get language-specific manager for a participant based on their language preference.
        
        Args:
            participant: The participant agent with language configuration
            
        Returns:
            Language manager with participant's language set, or current language manager as fallback
        """
        try:
            # Check if participant has language configuration
            if hasattr(participant, 'config') and hasattr(participant.config, 'language'):
                participant_language = participant.config.language.lower()
                
                # Map language strings to supported languages 
                language_mapping = {
                    'english': 'English',
                    'spanish': 'Spanish',
                    'mandarin': 'Mandarin',
                    'chinese': 'Mandarin'  # alias
                }
                
                target_language = language_mapping.get(participant_language)
                if target_language:
                    # Create a temporary language manager copy for this participant's language
                    from utils.language_manager import SupportedLanguage, create_language_manager
                    
                    language_enum_mapping = {
                        'English': SupportedLanguage.ENGLISH,
                        'Spanish': SupportedLanguage.SPANISH,
                        'Mandarin': SupportedLanguage.MANDARIN
                    }
                    
                    language_enum = language_enum_mapping.get(target_language)
                    if language_enum:
                        # Create participant-specific language manager
                        return create_language_manager(language_enum)
                    
            # Fallback to current language manager
            return self.language_manager
            
        except Exception as e:
            self.logger.debug(f"Failed to get participant language manager for {participant.name}: {e}")
            # Fallback to current language manager
            return self.language_manager
    
    def _build_comprehensive_earnings_display(self, participant_name: str, assigned_class_enum: IncomeClass, distribution_set, consensus_result: GroupDiscussionResult, lang_manager) -> str:
        """
        Build comprehensive earnings display for Phase 2 results using LanguageManager.
        
        Uses DistributionGenerator.calculate_comprehensive_constraint_outcomes() to build
        complete display structure with distributions table and principle outcomes.
        Marks group's consensus choice with localized marker.
        
        Args:
            participant_name: Name of the participant
            assigned_class_enum: Participant's assigned income class (IncomeClass enum)
            distribution_set: The distribution set used for Phase 2
            consensus_result: Result of group discussion with consensus info
            lang_manager: Language manager for localization
            
        Returns:
            Formatted comprehensive earnings display string
        """
        try:
            # Get comprehensive outcomes using LanguageManager
            comprehensive_data = DistributionGenerator.calculate_comprehensive_constraint_outcomes(
                distribution_set.distributions,
                assigned_class_enum,
                lang_manager  # Pass LanguageManager for localization
            )
            
            # Build display parts
            display_parts = []
            
            # Add distributions table (already localized)
            display_parts.append(comprehensive_data['distributions_table'])
            display_parts.append("")  # Empty line
            
            # Add principle outcomes header - use Phase 2-specific template
            outcomes_header = lang_manager.get(
                'comprehensive_earnings.phase2_outcomes_header',
                class_name=comprehensive_data['class_display_name']
            )
            display_parts.append(outcomes_header)
            
            # Determine group choice for marking
            group_choice_principle = None
            group_choice_constraint = None
            
            if consensus_result.consensus_reached and consensus_result.agreed_principle:
                group_choice_principle = consensus_result.agreed_principle.principle.value
                group_choice_constraint = consensus_result.agreed_principle.constraint_amount
            
            # Add all outcomes with proper group choice marking
            for outcome in comprehensive_data['outcomes']:
                # Determine if this outcome matches the group choice
                choice_marker = ""
                if group_choice_principle == outcome['principle_key']:
                    if outcome['constraint_amount'] is None or outcome['constraint_amount'] == group_choice_constraint:
                        choice_marker = lang_manager.get('comprehensive_earnings.markers.group_choice')
                
                # Format outcome line using LanguageManager
                outcome_line = lang_manager.get(
                    'comprehensive_earnings.outcome_line',
                    principle_name=outcome['principle_name'],
                    distribution=lang_manager.get('distributions.distribution_label', number=outcome['distribution_index'] + 1),
                    income=lang_manager.get('constraint_formatting.currency_format', amount=outcome['agent_income']),
                    earnings=lang_manager.get('constraint_formatting.currency_format', amount=outcome['agent_earnings']),
                    marker=choice_marker
                )
                display_parts.append(outcome_line)
            
            return "\n".join(display_parts)
            
        except Exception as e:
            self.logger.warning(f"Failed to build comprehensive earnings display for {participant_name}: {e}")
            return f"Earnings display unavailable due to error: {str(e)}"
    
    def _build_consensus_info(self, discussion_result: GroupDiscussionResult, lang_manager) -> str:
        """
        Build consensus information text based on discussion result.
        
        Args:
            discussion_result: Result of group discussion
            lang_manager: Language manager for localization
            
        Returns:
            Formatted consensus information string
        """
        try:
            if discussion_result.consensus_reached and discussion_result.agreed_principle:
                # Get localized principle name
                principle_key = discussion_result.agreed_principle.principle.value
                principle_name = lang_manager.get(f"common.principle_names.{principle_key}")
                
                # Check if there's a constraint amount
                if discussion_result.agreed_principle.constraint_amount is not None:
                    constraint_amount = discussion_result.agreed_principle.constraint_amount
                    consensus_msg = lang_manager.get(
                        "voting_results.consensus_with_constraint", 
                        principle_name=principle_name,
                        constraint_amount=constraint_amount
                    )
                else:
                    consensus_msg = lang_manager.get(
                        "voting_results.consensus_reached", 
                        principle_name=principle_name
                    )
                return consensus_msg
            else:
                # No consensus reached
                return lang_manager.get("phase2_no_consensus")
                
        except Exception as e:
            self.logger.warning(f"Failed to build consensus info: {e}")
            # Fallback message
            if discussion_result.consensus_reached:
                return "Consensus was reached on a justice principle."
            else:
                return "No consensus was reached. Earnings were randomly assigned."
    
    async def deliver_results_and_update_memory(
        self,
        participants: List["ParticipantAgent"],
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        assigned_classes: Dict[str, IncomeClass], 
        alternative_earnings_by_agent: Dict[str, Dict[str, float]],
        config: ExperimentConfiguration,
        distribution_set
    ) -> List[ParticipantContext]:
        """
        Deliver Phase 2 results using the new phase2_results_delivery_prompt and update participant memory.
        
        This method uses the new phase2_results_delivery_prompt template with proper consensus
        information and updates all participant memory in preparation for ranking collection.
        
        Args:
            participants: List of participant agents
            contexts: List of participant contexts
            discussion_result: Result of group discussion with consensus info
            payoff_results: Final payoff amounts for each participant  
            assigned_classes: Income class assignments (IncomeClass enum values)
            alternative_earnings_by_agent: Counterfactual earnings by participant
            config: Experiment configuration
            distribution_set: The distribution set used for Phase 2
            
        Returns:
            List of updated contexts for use in ranking collection
        """
        try:
            self.logger.info(f"Delivering Phase 2 results using new prompt template for {len(participants)} participants")
            
            updated_contexts = []
            
            for i, participant in enumerate(participants):
                context = contexts[i]
                
                # Get participant's results
                final_earnings = payoff_results[participant.name]
                assigned_class_enum = assigned_classes[participant.name]
                alternative_earnings = alternative_earnings_by_agent[participant.name]
                
                # Get participant-specific language manager
                participant_lang_manager = self._get_participant_language_manager(participant)
                
                try:
                    # Get the new results delivery prompt template
                    prompt_template = participant_lang_manager.get("phase2_results_delivery_prompt")
                    
                    # Get localized income class name
                    income_class_key = assigned_class_enum.value  # e.g., 'high', 'medium_low'
                    income_class_display = participant_lang_manager.get(f"common.income_classes.{income_class_key}")
                    
                    # Build consensus information
                    consensus_info = self._build_consensus_info(discussion_result, participant_lang_manager)
                    
                    # Format the prompt with all required parameters
                    result_content = prompt_template.format(
                        income_class=income_class_display,
                        earnings=final_earnings,
                        alt_floor=alternative_earnings.get('maximizing_floor', 0.0),
                        alt_average=alternative_earnings.get('maximizing_average', 0.0),
                        alt_floor_constraint=alternative_earnings.get('maximizing_average_with_floor', 0.0),
                        alt_range_constraint=alternative_earnings.get('maximizing_average_with_range', 0.0)
                    )
                    
                    # Replace the consensus placeholder with actual consensus information
                    result_content = result_content.replace(
                        "[Consensus/No consensus information will be dynamically inserted]",
                        consensus_info
                    )
                    
                except Exception as prompt_error:
                    self.logger.warning(f"Failed to format new prompt template for {participant.name}: {prompt_error}")
                    # Fallback to the old build_detailed_results method
                    assigned_class_str = assigned_class_enum.value
                    result_content = await self.build_detailed_results(
                        participant.name,
                        final_earnings,
                        assigned_class_str,
                        alternative_earnings,
                        discussion_result,
                        distribution_set
                    )
                
                # Update participant memory with results
                if self.memory_service:
                    try:
                        updated_memory = await self.memory_service.update_final_results_memory(
                            agent=participant,
                            context=context,
                            result_content=result_content,
                            final_earnings=final_earnings,
                            consensus_reached=discussion_result.consensus_reached,
                            config=config
                        )
                        context.memory = updated_memory
                        
                        self.logger.debug(f"Memory updated for {participant.name} with Phase 2 results")
                    
                    except Exception as memory_error:
                        self.logger.warning(f"Failed to update memory for {participant.name}: {memory_error}")
                        # Continue without memory update - don't block the process
                else:
                    # Fallback: update memory directly via participant agent
                    try:
                        updated_memory = await participant.update_memory(result_content, context.bank_balance)
                        context.memory = updated_memory
                        self.logger.debug(f"Memory updated directly for {participant.name}")
                    except Exception as fallback_error:
                        self.logger.warning(f"Fallback memory update failed for {participant.name}: {fallback_error}")
                
                updated_contexts.append(context)
            
            self.logger.info("Phase 2 results delivery and memory update completed successfully")
            return updated_contexts
            
        except Exception as e:
            self.logger.warning(f"Failed to deliver results and update memory: {e}")
            # Return original contexts to avoid breaking the flow
            return contexts
    
    async def collect_final_rankings(
        self,
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        assigned_classes: Dict[str, str],
        alternative_earnings_by_agent: Dict[str, Dict[str, float]],
        config: ExperimentConfiguration,
        participants: List["ParticipantAgent"],
        utility_agent,
        logger: Optional[AgentCentricLogger] = None,
        distribution_set = None
    ) -> Dict[str, PrincipleRanking]:
        """
        DEPRECATED: Collect final rankings with result delivery logic (Phase 1 compatibility).
        
        This method maintains backward compatibility during the transition to the two-call process.
        New callers should use the streamlined collect_final_rankings_streamlined() method instead.
        
        Args:
            contexts: List of participant contexts  
            discussion_result: Result of group discussion
            payoff_results: Final payoff amounts for each participant
            assigned_classes: Income class assignments
            alternative_earnings_by_agent: Counterfactual earnings by participant
            config: Experiment configuration
            participants: List of participant agents
            utility_agent: Utility agent for parsing responses
            logger: Optional logger for detailed logging
            distribution_set: Optional distribution set for comprehensive earnings display
            
        Returns:
            Dict mapping participant names to their final principle rankings
        """
        # For backward compatibility, delegate to the two-call process
        try:
            # First, convert assigned_classes to IncomeClass enums for deliver_results_and_update_memory
            assigned_classes_enum = {}
            for participant_name, class_str in assigned_classes.items():
                if class_str.startswith('IncomeClass.'):
                    # Handle enum string representation like 'IncomeClass.high'
                    enum_value = class_str.split('.')[1].lower()
                else:
                    # Handle direct value like 'high' or 'MEDIUM HIGH' 
                    enum_value = class_str.lower().replace(' ', '_')
                assigned_classes_enum[participant_name] = IncomeClass(enum_value)
            
            # Deliver results and update memory first
            updated_contexts = await self.deliver_results_and_update_memory(
                participants=participants,
                contexts=contexts,
                discussion_result=discussion_result,
                payoff_results=payoff_results,
                assigned_classes=assigned_classes_enum,
                alternative_earnings_by_agent=alternative_earnings_by_agent,
                config=config,
                distribution_set=distribution_set
            )
            
            # Then collect rankings using the streamlined method
            return await self.collect_final_rankings_streamlined(
                contexts=updated_contexts,
                participants=participants,
                utility_agent=utility_agent,
                payoff_results=payoff_results,
                assigned_classes=assigned_classes,
                logger=logger
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to collect final rankings via compatibility method: {e}")
            raise

    async def collect_final_rankings_streamlined(
        self,
        contexts: List[ParticipantContext],
        participants: List["ParticipantAgent"],
        utility_agent,
        payoff_results: Optional[Dict[str, float]] = None,
        assigned_classes: Optional[Dict[str, str]] = None,
        logger: Optional[AgentCentricLogger] = None
    ) -> Dict[str, PrincipleRanking]:
        """
        Collect final principle rankings from participants with pre-updated contexts.
        
        This method focuses solely on ranking collection, assuming that participant
        contexts have already been updated with Phase 2 results via deliver_results_and_update_memory().
        
        Args:
            contexts: List of pre-updated participant contexts from deliver_results_and_update_memory
            participants: List of participant agents
            utility_agent: Utility agent for parsing responses
            payoff_results: Optional payoff results for logging (from Phase 1 compatibility)
            assigned_classes: Optional class assignments for logging (from Phase 1 compatibility) 
            logger: Optional logger for detailed logging
            
        Returns:
            Dict mapping participant names to their final principle rankings
        """
        try:
            self.logger.info(f"Collecting final rankings from {len(participants)} participants")
            
            final_ranking_tasks = []
            
            for i, participant in enumerate(participants):
                context = contexts[i]
                
                # Create async task for getting final ranking - no result delivery needed
                task = asyncio.create_task(
                    self._get_final_ranking_task_streamlined(participant, context, utility_agent)
                )
                final_ranking_tasks.append((task, participant.name))
            
            # Gather just the tasks for asyncio
            tasks = [task_info[0] for task_info in final_ranking_tasks]
            rankings_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and build final rankings dictionary
            final_rankings = {}
            
            for i, (ranking_result, (_, participant_name)) in enumerate(zip(rankings_results, final_ranking_tasks)):
                if isinstance(ranking_result, Exception):
                    self.logger.warning(f"Failed to get final ranking from {participant_name}: {ranking_result}")
                    # Create default ranking
                    default_rankings = [
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                        RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
                    ]
                    final_rankings[participant_name] = PrincipleRanking(
                        rankings=default_rankings,
                        certainty=CertaintyLevel.NO_OPINION
                    )
                else:
                    final_rankings[participant_name] = ranking_result
                
                # Log detailed participant info if logger provided and we have the data
                if logger and hasattr(logger, 'log_participant_summary'):
                    context = contexts[i]
                    final_earnings = payoff_results.get(participant_name) if payoff_results else 0.0
                    assigned_class = assigned_classes.get(participant_name, "unknown") if assigned_classes else "unknown"
                    
                    logger.log_participant_summary(
                        participant_name=participant_name,
                        final_earnings=final_earnings,
                        assigned_class=assigned_class,
                        final_memory_length=len(context.memory) if context.memory else 0,
                        final_bank_balance=context.bank_balance,
                        ranking=final_rankings[participant_name]
                    )
            
            self.logger.info(f"Final rankings collected successfully from {len(final_rankings)} participants")
            return final_rankings
            
        except Exception as e:
            self.logger.warning(f"Failed to collect final rankings: {e}")
            raise
    
    async def _get_final_ranking_task(
        self,
        participant: "ParticipantAgent",
        context: ParticipantContext,
        agent_config,
        result_content: str,
        utility_agent
    ) -> PrincipleRanking:
        """
        Get final ranking from a single participant.
        
        Args:
            participant: The participant agent
            context: Participant context
            agent_config: Agent configuration
            result_content: Formatted results content
            utility_agent: Utility agent for parsing
            
        Returns:
            PrincipleRanking from the participant
        """
        try:
            # Update participant memory with results
            updated_memory = await participant.update_memory(result_content, context.bank_balance)
            context.memory = updated_memory
            
            # Get final ranking using proven Phase 1 pattern
            final_ranking_prompt = self.language_manager.get("prompts.phase2_final_ranking_prompt")
            result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
            text_response = result.final_output
            
            # Parse the ranking using utility agent
            parsed_ranking = await utility_agent.parse_principle_ranking_enhanced(text_response)
            
            return parsed_ranking
            
        except Exception as e:
            self.logger.warning(f"Failed to get final ranking from {participant.name}: {e}")
            # Return default ranking
            default_rankings = [
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ]
            return PrincipleRanking(
                rankings=default_rankings,
                certainty=CertaintyLevel.NO_OPINION
            )
    
    async def _get_final_ranking_task_streamlined(
        self,
        participant: "ParticipantAgent",
        context: ParticipantContext,
        utility_agent
    ) -> PrincipleRanking:
        """
        Get final ranking from a single participant with pre-updated context.
        
        This method assumes the participant's context memory has already been updated
        with Phase 2 results, so it focuses solely on ranking collection.
        
        Args:
            participant: The participant agent
            context: Pre-updated participant context with results in memory
            utility_agent: Utility agent for parsing
            
        Returns:
            PrincipleRanking from the participant
        """
        try:
            # No memory update needed - context is pre-updated from deliver_results_and_update_memory
            
            # Get final ranking using proven Phase 1 pattern
            final_ranking_prompt = self.language_manager.get("prompts.phase2_final_ranking_prompt")
            result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
            text_response = result.final_output
            
            # Parse the ranking using utility agent
            parsed_ranking = await utility_agent.parse_principle_ranking_enhanced(text_response)
            
            return parsed_ranking
            
        except Exception as e:
            self.logger.warning(f"Failed to get final ranking from {participant.name}: {e}")
            # Return default ranking
            default_rankings = [
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ]
            return PrincipleRanking(
                rankings=default_rankings,
                certainty=CertaintyLevel.NO_OPINION
            )
