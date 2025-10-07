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
    PrincipleRanking, RankedPrinciple, CertaintyLevel, ParticipantContext, ExperimentStage
)
from config import ExperimentConfiguration
from config.phase2_settings import Phase2Settings
from utils.logging import run_with_transcript_logging
from core.distribution_generator import DistributionGenerator
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.selective_memory_manager import MemoryEventType
from utils.memory_manager import MemoryManager
from utils.parsing_errors import create_parsing_error

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
        memory_service: Optional[MemoryServiceProvider] = None,
        config: Optional[ExperimentConfiguration] = None,
        transcript_logger=None
    ):
        """
        Initialize CounterfactualsService with dependencies.
        
        Args:
            language_manager: Provider for localized text
            settings: Phase 2 configuration settings
            logger: Optional logger for service operations
            seed_manager: Optional seed manager for reproducible randomness
            memory_service: Optional memory service for updating participant memory
            config: Optional experiment configuration for retry support
        """
        self.language_manager = language_manager
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.seed_manager = seed_manager
        self.memory_service = memory_service
        self.config = config
        self.transcript_logger = transcript_logger
        # Cache Phase 2 probabilities for consistent displays
        self._phase2_probabilities = None
        # Track assigned distributions for no-consensus scenarios
        self._assigned_distributions = {}

    async def _invoke_phase2_interaction(
        self,
        participant: "ParticipantAgent",
        context: ParticipantContext,
        prompt: str,
        interaction_type: str
    ):
        """Execute a participant interaction with transcript logging support."""
        context.interaction_type = interaction_type
        return await run_with_transcript_logging(
            participant=participant,
            prompt=prompt,
            context=context,
            transcript_logger=self.transcript_logger,
            interaction_type=interaction_type
        )
    
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
            # Store probabilities for use in comprehensive display
            self._phase2_probabilities = getattr(config, 'income_class_probabilities', None)
            # Generate new distribution set for Phase 2 payoffs
            distribution_set = DistributionGenerator.generate_dynamic_distribution(
                config.distribution_range_phase2,
                random_gen=self.seed_manager.random if self.seed_manager else None
            )

            payoffs = {}
            assigned_classes = {}
            # Track which distribution was assigned to each participant (for no-consensus display)
            assigned_distributions = {}
            consensus_principle = None
            constraint_amount = None

            if discussion_result.consensus_reached and discussion_result.agreed_principle:
                # Apply agreed principle
                consensus_principle = discussion_result.agreed_principle
                constraint_amount = consensus_principle.constraint_amount

                chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
                    distribution_set.distributions,
                    discussion_result.agreed_principle,
                    config.income_class_probabilities,
                    language_manager=self.language_manager
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
                    # Track which distribution index was assigned (1-indexed for display)
                    distribution_index = distribution_set.distributions.index(random_distribution) + 1
                    assigned_distributions[participant.name] = distribution_index
                    assigned_class, earnings = DistributionGenerator.calculate_payoff(random_distribution, config.income_class_probabilities, random_gen=self.seed_manager.random if self.seed_manager else None)
                    payoffs[participant.name] = earnings
                    assigned_classes[participant.name] = assigned_class.value

            # Store assigned distributions for use in comprehensive display
            self._assigned_distributions = assigned_distributions

            # Calculate counterfactual earnings for transparency
            alternative_earnings_by_agent = await self.calculate_phase2_counterfactuals(
                distribution_set, assigned_classes, consensus_principle, constraint_amount,
                probabilities=config.income_class_probabilities
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
        constraint_amount: Optional[int] = None,
        probabilities = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate alternative earnings under all 4 principles for transparency.

        Calculate what each agent would earn under all four principles
        using their assigned income class from Phase 2. Uses appropriate constraint
        values for each principle type to avoid incorrect constraint reuse.
        Uses weighted probabilities to ensure consistent distribution selection.

        Args:
            distribution_set: The distribution set generated for Phase 2
            assigned_classes: Dict mapping participant names to their assigned income classes
            consensus_principle: The principle chosen by consensus (if any)
            constraint_amount: The constraint amount used (if any) - DEPRECATED, use consensus_principle
            probabilities: Income class probabilities for weighted average calculation

        Returns:
            Dict[agent_name, Dict[principle_key, earnings]]
        """
        try:
            from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel

            alternative_earnings_by_agent = {}

            # Determine constraint values to use for each constraint type
            # If consensus reached with a constraint principle, use that value
            # Otherwise use representative values from the distributions
            floor_constraint_value = None
            range_constraint_value = None

            if consensus_principle and consensus_principle.constraint_amount:
                if consensus_principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
                    floor_constraint_value = consensus_principle.constraint_amount
                elif consensus_principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT:
                    range_constraint_value = consensus_principle.constraint_amount

            # If no consensus value, use median values from distributions
            if floor_constraint_value is None:
                floor_values = sorted([d.low for d in distribution_set.distributions])
                floor_constraint_value = floor_values[len(floor_values) // 2]

            if range_constraint_value is None:
                range_values = sorted([d.get_range() for d in distribution_set.distributions])
                range_constraint_value = range_values[len(range_values) // 2]

            for participant_name, class_str in assigned_classes.items():
                # Convert string back to enum - handle different formats
                if class_str.startswith('IncomeClass.'):
                    # Handle enum string representation like 'IncomeClass.high'
                    enum_value = class_str.split('.')[1].lower()
                else:
                    # Handle direct value like 'high' or 'MEDIUM HIGH'
                    enum_value = class_str.lower().replace(' ', '_')

                assigned_class = IncomeClass(enum_value)

                # Calculate earnings for each principle with appropriate constraint values
                alternative_earnings = {}

                # 1. Maximizing floor - no constraint
                floor_choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_FLOOR,
                    certainty=CertaintyLevel.SURE
                )
                dist, _ = DistributionGenerator.apply_principle_to_distributions(
                    distribution_set.distributions, floor_choice, probabilities, None
                )
                income = dist.get_income_by_class(assigned_class)
                alternative_earnings['maximizing_floor'] = round(income / 10000.0, 2)

                # 2. Maximizing average - no constraint
                avg_choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                    certainty=CertaintyLevel.SURE
                )
                dist, _ = DistributionGenerator.apply_principle_to_distributions(
                    distribution_set.distributions, avg_choice, probabilities, None
                )
                income = dist.get_income_by_class(assigned_class)
                alternative_earnings['maximizing_average'] = round(income / 10000.0, 2)

                # 3. Maximizing average with floor constraint - use appropriate floor value
                floor_constraint_choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                    constraint_amount=floor_constraint_value,
                    certainty=CertaintyLevel.SURE
                )
                dist, _ = DistributionGenerator.apply_principle_to_distributions(
                    distribution_set.distributions, floor_constraint_choice, probabilities, None
                )
                income = dist.get_income_by_class(assigned_class)
                alternative_earnings['maximizing_average_floor_constraint'] = round(income / 10000.0, 2)

                # 4. Maximizing average with range constraint - use appropriate range value
                range_constraint_choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                    constraint_amount=range_constraint_value,
                    certainty=CertaintyLevel.SURE
                )
                dist, _ = DistributionGenerator.apply_principle_to_distributions(
                    distribution_set.distributions, range_constraint_choice, probabilities, None
                )
                income = dist.get_income_by_class(assigned_class)
                alternative_earnings['maximizing_average_range_constraint'] = round(income / 10000.0, 2)

                alternative_earnings_by_agent[participant_name] = alternative_earnings

            self.logger.debug(f"Counterfactuals calculated for {len(assigned_classes)} participants with proper constraint handling and weighted probabilities")
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
        distribution_set,
        lang_manager: LanguageProvider
    ) -> str:
        """
        Build Phase 2 results using explicit causal narrative format.

        Routes to either consensus or no-consensus results builder based on
        discussion outcome.

        Args:
            participant_name: Name of the participant
            final_earnings: Participant's final earnings
            assigned_class: Income class assigned to participant
            alternative_earnings: Alternative earnings under each principle
            consensus_result: Result of group discussion
            distribution_set: The distribution set used for Phase 2
            lang_manager: Language manager for participant-specific localization

        Returns:
            Formatted results string with explicit causal narrative
        """
        if consensus_result.consensus_reached and consensus_result.agreed_principle:
            return self._build_consensus_results(
                participant_name,
                final_earnings,
                assigned_class,
                alternative_earnings,
                consensus_result,
                distribution_set,
                lang_manager
            )
        else:
            return self._build_no_consensus_results(
                participant_name,
                final_earnings,
                assigned_class,
                alternative_earnings,
                consensus_result,
                distribution_set,
                lang_manager
            )
    
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
    
    def _build_comprehensive_earnings_display(self, participant_name: str, assigned_class_enum: IncomeClass, distribution_set, consensus_result: GroupDiscussionResult, lang_manager, final_earnings: float = 0.0) -> str:
        """
        Build comprehensive earnings display for Phase 2 results using LanguageManager.

        Uses DistributionGenerator.calculate_comprehensive_constraint_outcomes() to build
        complete display structure with distributions table and principle outcomes.
        Marks group's consensus choice with localized marker.
        For no-consensus scenarios, prepends a clear summary explaining random assignment.

        Args:
            participant_name: Name of the participant
            assigned_class_enum: Participant's assigned income class (IncomeClass enum)
            distribution_set: The distribution set used for Phase 2
            consensus_result: Result of group discussion with consensus info
            lang_manager: Language manager for localization
            final_earnings: Participant's final earnings (used for no-consensus summary)

        Returns:
            Formatted comprehensive earnings display string
        """
        try:
            # Get comprehensive outcomes using LanguageManager
            comprehensive_data = DistributionGenerator.calculate_comprehensive_constraint_outcomes(
                distribution_set.distributions,
                assigned_class_enum,
                lang_manager,
                self._phase2_probabilities
            )

            # Build display parts
            display_parts = []

            # Add probabilities block (localized) if available
            try:
                if self._phase2_probabilities is not None:
                    prob_header = lang_manager.get('results.class_probabilities_header')
                    display_parts.append(prob_header)
                    class_keys = ['high', 'medium_high', 'medium', 'medium_low', 'low']
                    for key in class_keys:
                        cls_name = lang_manager.get(f'common.income_classes.{key}')
                        p = getattr(self._phase2_probabilities, key)
                        display_parts.append(f"- {cls_name}: {p*100:.0f}%")
                    display_parts.append("")
            except Exception:
                pass

            # Add distributions table (already localized)
            display_parts.append(comprehensive_data['distributions_table'])
            display_parts.append("")  # Empty line

            # Add principle outcomes header - use Phase 2-specific template
            outcomes_header = lang_manager.get(
                'comprehensive_earnings.phase2_outcomes_header',
                class_name=comprehensive_data['class_display_name']
            )
            display_parts.append(outcomes_header)
            
            # Determine group choice or random assignment for marking
            group_choice_principle = None
            group_choice_constraint = None
            random_distribution_num = None

            if consensus_result.consensus_reached and consensus_result.agreed_principle:
                group_choice_principle = consensus_result.agreed_principle.principle.value
                group_choice_constraint = consensus_result.agreed_principle.constraint_amount
            else:
                # No consensus - mark random assignment
                random_distribution_num = self._assigned_distributions.get(participant_name, 1)

            # Add all outcomes with proper marking
            for outcome in comprehensive_data['outcomes']:
                # Determine if this outcome should be marked
                choice_marker = ""
                if consensus_result.consensus_reached:
                    # Mark group choice for consensus
                    if group_choice_principle == outcome['principle_key']:
                        if outcome['constraint_amount'] is None or outcome['constraint_amount'] == group_choice_constraint:
                            choice_marker = lang_manager.get('comprehensive_earnings.markers.group_choice')
                else:
                    # Mark random assignment for no-consensus
                    if random_distribution_num == outcome['distribution_index'] + 1:
                        choice_marker = lang_manager.get('comprehensive_earnings.markers.random_assignment')
                        random_distribution_num = None  # Only mark first match
                
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
            try:
                return lang_manager.get("fallback_messages.earnings_display_error")
            except Exception:
                return "Earnings display unavailable due to an internal error."
    
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
                try:
                    return lang_manager.get("fallback_messages.consensus_generic")
                except Exception:
                    return "Consensus was reached on a justice principle."
            else:
                try:
                    return lang_manager.get("fallback_messages.no_consensus_generic")
                except Exception:
                    return "No consensus was reached. Earnings were randomly assigned."

    def _format_difference(self, diff: float, lang_manager: LanguageProvider) -> str:
        """
        Format earnings difference for counterfactual display.

        Args:
            diff: Difference in earnings (counterfactual - actual)
            lang_manager: Language manager for localization

        Returns:
            Formatted difference string
        """
        if abs(diff) < 0.01:  # Account for floating point precision
            return lang_manager.get("results_explicit.difference_same")
        elif diff > 0:
            return lang_manager.get("results_explicit.difference_positive", diff=f"{diff:.2f}")
        else:
            return lang_manager.get("results_explicit.difference_negative", diff=f"{diff:.2f}")

    def _build_counterfactual_outcomes(
        self,
        assigned_class_enum: IncomeClass,
        distribution_set,
        alternative_earnings: Dict[str, float],
        consensus_result: GroupDiscussionResult,
        participant_name: str,
        final_earnings: float,
        lang_manager: LanguageProvider
    ) -> str:
        """
        Build counterfactual outcomes section with grouped constraints.

        Returns formatted string with:
        - Simple principles (1 line each with difference)
        - Constraint principles (parent + multiple indented children with differences)
        - Appropriate marker (chosen principle or random assignment)

        Args:
            assigned_class_enum: Participant's assigned income class
            distribution_set: The distribution set used for Phase 2
            alternative_earnings: Alternative earnings under each principle
            consensus_result: Result of group discussion
            participant_name: Name of the participant
            final_earnings: Participant's final earnings
            lang_manager: Language manager for localization

        Returns:
            Formatted counterfactual outcomes string
        """
        try:
            from core.distribution_generator import DistributionGenerator

            def format_income_value(amount: float | int) -> str:
                try:
                    if isinstance(amount, int) or (isinstance(amount, float) and amount.is_integer()):
                        return lang_manager.get("constraint_formatting.currency_format", amount=int(round(amount)))
                except Exception:
                    pass

                if isinstance(amount, float):
                    return f"${amount:,.2f}"
                return f"${amount:,}"

            # Get comprehensive outcomes (all constraint variations)
            comprehensive_data = DistributionGenerator.calculate_comprehensive_constraint_outcomes(
                distribution_set.distributions,
                assigned_class_enum,
                lang_manager,
                self._phase2_probabilities
            )

            # Determine what should be marked
            chosen_principle = None
            chosen_constraint = None
            random_dist_num = None

            if consensus_result.consensus_reached and consensus_result.agreed_principle:
                chosen_principle = consensus_result.agreed_principle.principle.value
                chosen_constraint = consensus_result.agreed_principle.constraint_amount
            else:
                random_dist_num = self._assigned_distributions.get(participant_name)

            # Group outcomes by principle_key
            grouped = {}
            for outcome in comprehensive_data['outcomes']:
                key = outcome['principle_key']
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(outcome)

            result_lines = []

            # 1. Maximizing Floor (simple principle)
            if 'maximizing_floor' in grouped:
                for outcome in grouped['maximizing_floor']:
                    dist_num = outcome['distribution_index'] + 1
                    earnings = outcome['agent_earnings']
                    income = outcome['agent_income']
                    principle_name = lang_manager.get("common.principle_names.maximizing_floor")

                    marker = ""
                    if consensus_result.consensus_reached and chosen_principle == 'maximizing_floor':
                        marker = lang_manager.get("results_explicit.marker_chosen")
                    elif not consensus_result.consensus_reached and dist_num == random_dist_num:
                        marker = lang_manager.get("results_explicit.marker_random")
                        random_dist_num = None

                    distribution_label = lang_manager.get("distributions.distribution_label", number=dist_num)
                    income_display = format_income_value(income)
                    earnings_display = format_income_value(earnings)
                    result_lines.append(f"- {principle_name} → {distribution_label} → {income_display} → {earnings_display}{marker}")

            # 2. Maximizing Average (simple principle)
            if 'maximizing_average' in grouped:
                for outcome in grouped['maximizing_average']:
                    dist_num = outcome['distribution_index'] + 1
                    earnings = outcome['agent_earnings']
                    income = outcome['agent_income']
                    principle_name = lang_manager.get("common.principle_names.maximizing_average")

                    marker = ""
                    if consensus_result.consensus_reached and chosen_principle == 'maximizing_average':
                        marker = lang_manager.get("results_explicit.marker_chosen")
                    elif not consensus_result.consensus_reached and dist_num == random_dist_num:
                        marker = lang_manager.get("results_explicit.marker_random")
                        random_dist_num = None

                    distribution_label = lang_manager.get("distributions.distribution_label", number=dist_num)
                    income_display = format_income_value(income)
                    earnings_display = format_income_value(earnings)
                    result_lines.append(f"- {principle_name} → {distribution_label} → {income_display} → {earnings_display}{marker}")

            # 3. Floor Constraint (grouped with multiple children)
            if 'maximizing_average_floor_constraint' in grouped:
                result_lines.append("")
                parent_name = lang_manager.get("common.principle_names.maximizing_average_floor_constraint")
                result_lines.append(f"- {parent_name}:")

                for outcome in grouped['maximizing_average_floor_constraint']:
                    dist_num = outcome['distribution_index'] + 1
                    earnings = outcome['agent_earnings']
                    income = outcome['agent_income']
                    constraint_amt = outcome['constraint_amount']

                    floor_label = lang_manager.get("results_explicit.floor_constraint_label", amount=f"{constraint_amt:,}")

                    marker = ""
                    if consensus_result.consensus_reached and chosen_principle == 'maximizing_average_floor_constraint' and chosen_constraint == constraint_amt:
                        marker = lang_manager.get("results_explicit.marker_chosen")
                    elif not consensus_result.consensus_reached and dist_num == random_dist_num:
                        marker = lang_manager.get("results_explicit.marker_random")
                        random_dist_num = None

                    distribution_label = lang_manager.get("distributions.distribution_label", number=dist_num)
                    income_display = format_income_value(income)
                    earnings_display = format_income_value(earnings)
                    result_lines.append(f"  {floor_label} → {distribution_label} → {income_display} → {earnings_display}{marker}")

            # 4. Range Constraint (grouped with multiple children)
            if 'maximizing_average_range_constraint' in grouped:
                result_lines.append("")
                parent_name = lang_manager.get("common.principle_names.maximizing_average_range_constraint")
                result_lines.append(f"- {parent_name}:")

                for outcome in grouped['maximizing_average_range_constraint']:
                    dist_num = outcome['distribution_index'] + 1
                    earnings = outcome['agent_earnings']
                    income = outcome['agent_income']
                    constraint_amt = outcome['constraint_amount']

                    range_label = lang_manager.get("results_explicit.range_constraint_label", amount=f"{constraint_amt:,}")

                    marker = ""
                    if consensus_result.consensus_reached and chosen_principle == 'maximizing_average_range_constraint' and chosen_constraint == constraint_amt:
                        marker = lang_manager.get("results_explicit.marker_chosen")
                    elif not consensus_result.consensus_reached and dist_num == random_dist_num:
                        marker = lang_manager.get("results_explicit.marker_random")
                        random_dist_num = None

                    distribution_label = lang_manager.get("distributions.distribution_label", number=dist_num)
                    income_display = format_income_value(income)
                    earnings_display = format_income_value(earnings)
                    result_lines.append(f"  {range_label} → {distribution_label} → {income_display} → {earnings_display}{marker}")

            return "\n".join(result_lines)

        except Exception as e:
            self.logger.warning(f"Failed to build counterfactual outcomes: {e}")
            try:
                return lang_manager.get("fallback_messages.counterfactual_error")
            except Exception:
                return "Counterfactual analysis unavailable."

    def _build_consensus_results(
        self,
        participant_name: str,
        final_earnings: float,
        assigned_class: str,
        alternative_earnings: Dict[str, float],
        consensus_result: GroupDiscussionResult,
        distribution_set,
        lang_manager: LanguageProvider
    ) -> str:
        """
        Build results for consensus scenario using explicit causal narrative format.

        Args:
            participant_name: Name of the participant
            final_earnings: Participant's final earnings
            assigned_class: Income class assigned to participant
            alternative_earnings: Alternative earnings under each principle
            consensus_result: Result of group discussion
            distribution_set: The distribution set used for Phase 2
            lang_manager: Language manager for localization

        Returns:
            Formatted results string for consensus scenario
        """
        try:
            result_parts = []

            # Convert assigned_class to enum
            if assigned_class.startswith('IncomeClass.'):
                enum_value = assigned_class.split('.')[1].lower()
            else:
                enum_value = assigned_class.lower().replace(' ', '_')
            assigned_class_enum = IncomeClass(enum_value)

            # Get principle name and constraint
            principle_slug = consensus_result.agreed_principle.principle.value
            principle_name = lang_manager.get(f"common.principle_names.{principle_slug}")

            constraint_text = ""
            if consensus_result.agreed_principle.constraint_amount is not None:
                constraint_amount = consensus_result.agreed_principle.constraint_amount
                if principle_slug == 'maximizing_average_floor_constraint':
                    constraint_label = lang_manager.get("results_explicit.floor_constraint_label", amount=f"{constraint_amount:,}")
                else:
                    constraint_label = lang_manager.get("results_explicit.range_constraint_label", amount=f"{constraint_amount:,}")
                constraint_text = f" {constraint_label}"

            # 1. Principle applied
            principle_applied = lang_manager.get(
                "results_explicit.principle_applied_consensus",
                principle_name=principle_name,
                constraint=constraint_text
            )
            result_parts.append(principle_applied)
            result_parts.append("")

            # 2. Class probabilities
            if self._phase2_probabilities is not None:
                prob_header = lang_manager.get("results_explicit.probabilities_header")
                result_parts.append(prob_header)
                class_keys = ['high', 'medium_high', 'medium', 'medium_low', 'low']
                for key in class_keys:
                    cls_name = lang_manager.get(f'common.income_classes.{key}')
                    p = getattr(self._phase2_probabilities, key)
                    result_parts.append(f"- {cls_name}: {p*100:.0f}%")
                result_parts.append("")

            # 3. Assignment statement
            class_label = lang_manager.get(f"common.income_classes.{assigned_class_enum.value}")
            assignment = lang_manager.get("results_explicit.assignment_statement", class_name=class_label)
            result_parts.append(assignment)
            result_parts.append("")

            # 4. Distributions table
            distributions_header = lang_manager.get("results_explicit.distributions_header")
            result_parts.append(distributions_header)
            result_parts.append("")

            # Build distributions table
            from core.distribution_generator import DistributionGenerator
            table_lines = []
            table_lines.append("| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |")
            table_lines.append("|--------------|---------|---------|---------|---------|")

            class_order = [IncomeClass.HIGH, IncomeClass.MEDIUM_HIGH, IncomeClass.MEDIUM,
                          IncomeClass.MEDIUM_LOW, IncomeClass.LOW]
            for cls in class_order:
                cls_label = lang_manager.get(f"common.income_classes.{cls.value}")
                row = [cls_label]
                for dist in distribution_set.distributions:
                    income = dist.get_income_by_class(cls)
                    row.append(f"${income:,}")
                table_lines.append("| " + " | ".join(row) + " |")

            # Add average row
            average_label = lang_manager.get("common.average_label", default="Average")
            avg_row = [average_label]
            for dist in distribution_set.distributions:
                avg_income = dist.get_average_income(self._phase2_probabilities)
                avg_row.append(f"${avg_income:,.0f}")
            table_lines.append("| " + " | ".join(avg_row) + " |")

            result_parts.extend(table_lines)
            result_parts.append("")

            # 5. Causal narrative
            # Determine which distribution was selected
            from models.principle_types import PrincipleChoice, CertaintyLevel
            chosen_dist, _ = DistributionGenerator.apply_principle_to_distributions(
                distribution_set.distributions,
                consensus_result.agreed_principle,
                self._phase2_probabilities,
                None
            )
            dist_num = distribution_set.distributions.index(chosen_dist) + 1
            income = chosen_dist.get_income_by_class(assigned_class_enum)

            causal_narrative = lang_manager.get(
                "results_explicit.causal_narrative_consensus",
                principle_name=principle_name,
                constraint=constraint_text,
                dist_num=dist_num,
                class_name=class_label,
                income=f"{income:,}",
                earnings=f"{final_earnings:.2f}"
            )
            result_parts.append(causal_narrative)
            result_parts.append("")

            # 6. Counterfactual analysis
            counterfactual_header = lang_manager.get("results_explicit.counterfactual_header")
            result_parts.append(counterfactual_header)

            counterfactual_purpose = lang_manager.get(
                "results_explicit.counterfactual_purpose_consensus",
                class_name=class_label
            )
            result_parts.append(counterfactual_purpose)
            result_parts.append("")

            # 7. Outcomes header
            outcomes_header = lang_manager.get(
                "results_explicit.outcomes_header",
                class_name=class_label
            )
            result_parts.append(outcomes_header)
            result_parts.append("")

            # 8. Counterfactual outcomes
            counterfactual_outcomes = self._build_counterfactual_outcomes(
                assigned_class_enum,
                distribution_set,
                alternative_earnings,
                consensus_result,
                participant_name,
                final_earnings,
                lang_manager
            )
            result_parts.append(counterfactual_outcomes)
            result_parts.append("")

            # 9. Veil of ignorance reminder
            veil_header = lang_manager.get("results_explicit.veil_reminder_header")
            result_parts.append(veil_header)

            veil_reminder = lang_manager.get("results_explicit.veil_reminder_consensus")
            result_parts.append(veil_reminder)

            return "\n".join(result_parts)

        except Exception as e:
            self.logger.warning(f"Failed to build consensus results for {participant_name}: {e}")
            # Fallback to basic format
            return f"Phase 2 results: ${final_earnings:.2f}. Income class: {assigned_class}."

    def _build_no_consensus_results(
        self,
        participant_name: str,
        final_earnings: float,
        assigned_class: str,
        alternative_earnings: Dict[str, float],
        consensus_result: GroupDiscussionResult,
        distribution_set,
        lang_manager: LanguageProvider
    ) -> str:
        """
        Build results for no-consensus scenario using explicit causal narrative format.

        Args:
            participant_name: Name of the participant
            final_earnings: Participant's final earnings
            assigned_class: Income class assigned to participant
            alternative_earnings: Alternative earnings under each principle
            consensus_result: Result of group discussion
            distribution_set: The distribution set used for Phase 2
            lang_manager: Language manager for localization

        Returns:
            Formatted results string for no-consensus scenario
        """
        try:
            result_parts = []

            # Convert assigned_class to enum
            if assigned_class.startswith('IncomeClass.'):
                enum_value = assigned_class.split('.')[1].lower()
            else:
                enum_value = assigned_class.lower().replace(' ', '_')
            assigned_class_enum = IncomeClass(enum_value)

            # 1. Principle applied (no consensus)
            principle_applied = lang_manager.get("results_explicit.principle_applied_no_consensus")
            result_parts.append(principle_applied)
            result_parts.append("")

            # 2. Class probabilities
            if self._phase2_probabilities is not None:
                prob_header = lang_manager.get("results_explicit.probabilities_header")
                result_parts.append(prob_header)
                class_keys = ['high', 'medium_high', 'medium', 'medium_low', 'low']
                for key in class_keys:
                    cls_name = lang_manager.get(f'common.income_classes.{key}')
                    p = getattr(self._phase2_probabilities, key)
                    result_parts.append(f"- {cls_name}: {p*100:.0f}%")
                result_parts.append("")

            # 3. Assignment statement
            class_label = lang_manager.get(f"common.income_classes.{assigned_class_enum.value}")
            assignment = lang_manager.get("results_explicit.assignment_statement", class_name=class_label)
            result_parts.append(assignment)
            result_parts.append("")

            # 4. Distributions table
            distributions_header = lang_manager.get("results_explicit.distributions_header")
            result_parts.append(distributions_header)
            result_parts.append("")

            # Build distributions table
            table_lines = []
            table_lines.append("| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |")
            table_lines.append("|--------------|---------|---------|---------|---------|")

            class_order = [IncomeClass.HIGH, IncomeClass.MEDIUM_HIGH, IncomeClass.MEDIUM,
                          IncomeClass.MEDIUM_LOW, IncomeClass.LOW]
            for cls in class_order:
                cls_label = lang_manager.get(f"common.income_classes.{cls.value}")
                row = [cls_label]
                for dist in distribution_set.distributions:
                    income = dist.get_income_by_class(cls)
                    row.append(f"${income:,}")
                table_lines.append("| " + " | ".join(row) + " |")

            # Add average row
            average_label = lang_manager.get("common.average_label", default="Average")
            avg_row = [average_label]
            for dist in distribution_set.distributions:
                avg_income = dist.get_average_income(self._phase2_probabilities)
                avg_row.append(f"${avg_income:,.0f}")
            table_lines.append("| " + " | ".join(avg_row) + " |")

            result_parts.extend(table_lines)
            result_parts.append("")

            # 5. Causal narrative (no consensus)
            dist_num = self._assigned_distributions.get(participant_name, 1)

            # Get the actual distribution and income for this participant
            random_dist = distribution_set.distributions[dist_num - 1]
            income = random_dist.get_income_by_class(assigned_class_enum)

            causal_narrative = lang_manager.get(
                "results_explicit.causal_narrative_no_consensus",
                dist_num=dist_num,
                class_name=class_label,
                income=f"{income:,}",
                earnings=f"{final_earnings:.2f}"
            )
            result_parts.append(causal_narrative)
            result_parts.append("")

            # 6. Counterfactual analysis
            counterfactual_header = lang_manager.get("results_explicit.counterfactual_header")
            result_parts.append(counterfactual_header)

            counterfactual_purpose = lang_manager.get(
                "results_explicit.counterfactual_purpose_no_consensus",
                class_name=class_label
            )
            result_parts.append(counterfactual_purpose)
            result_parts.append("")

            # 7. Outcomes header
            outcomes_header = lang_manager.get(
                "results_explicit.outcomes_header",
                class_name=class_label
            )
            result_parts.append(outcomes_header)
            result_parts.append("")

            # 8. Counterfactual outcomes
            counterfactual_outcomes = self._build_counterfactual_outcomes(
                assigned_class_enum,
                distribution_set,
                alternative_earnings,
                consensus_result,
                participant_name,
                final_earnings,
                lang_manager
            )
            result_parts.append(counterfactual_outcomes)
            result_parts.append("")

            # 9. Veil of ignorance reminder (no consensus version)
            veil_header = lang_manager.get("results_explicit.veil_reminder_header")
            result_parts.append(veil_header)

            veil_reminder = lang_manager.get("results_explicit.veil_reminder_no_consensus")
            result_parts.append(veil_reminder)

            return "\n".join(result_parts)

        except Exception as e:
            self.logger.warning(f"Failed to build no-consensus results for {participant_name}: {e}")
            # Fallback to basic format
            return f"Phase 2 results: ${final_earnings:.2f}. Income class: {assigned_class}."
    
    async def deliver_results_and_update_memory(
        self,
        participants: List["ParticipantAgent"],
        contexts: List[ParticipantContext],
        discussion_result: GroupDiscussionResult,
        payoff_results: Dict[str, float],
        assigned_classes: Dict[str, str], 
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
            assigned_classes: Income class assignments (string values)
            alternative_earnings_by_agent: Counterfactual earnings by participant
            config: Experiment configuration
            distribution_set: The distribution set used for Phase 2
            
        Returns:
            List of updated contexts for use in ranking collection
        """
        try:
            self.logger.info(f"Delivering Phase 2 results using new prompt template for {len(participants)} participants")
            
            # Convert string assigned_classes to IncomeClass enums using the same logic as collect_final_rankings
            assigned_classes_enum = {}
            for participant_name, class_str in assigned_classes.items():
                if class_str.startswith('IncomeClass.'):
                    # Handle enum string representation like 'IncomeClass.high'
                    enum_value = class_str.split('.')[1].lower()
                else:
                    # Handle direct value like 'high' or 'MEDIUM HIGH' 
                    enum_value = class_str.lower().replace(' ', '_')
                assigned_classes_enum[participant_name] = IncomeClass(enum_value)
            
            updated_contexts = []
            
            for i, participant in enumerate(participants):
                context = contexts[i]
                
                # Get participant's results
                final_earnings = payoff_results[participant.name]
                assigned_class_enum = assigned_classes_enum[participant.name]
                alternative_earnings = alternative_earnings_by_agent[participant.name]
                
                # Get participant-specific language manager
                participant_lang_manager = self._get_participant_language_manager(participant)
                
                # Use working build_detailed_results method for comprehensive results display
                assigned_class_str = assigned_class_enum.value
                result_content = await self.build_detailed_results(
                    participant.name,
                    final_earnings,
                    assigned_class_str,
                    alternative_earnings,
                    discussion_result,
                    distribution_set,
                    participant_lang_manager
                )
                # Debug trace: ensure Phase 2 content goes into memory update
                try:
                    preview = (result_content or "")[:120].replace("\n", " ")
                    self.logger.debug(f"Phase 2 results preview for {participant.name}: {preview}")
                except Exception:
                    pass
                
                # Update context bank balance with Phase 2 earnings FIRST
                context.bank_balance += final_earnings
                context.stage = ExperimentStage.RESULTS

                # Update participant memory with results (now with correct bank balance)
                if self.memory_service:
                    try:
                        self.logger.debug(f"Using MemoryService path for {participant.name}")
                        updated_memory = await self.memory_service.update_final_results_memory(
                            agent=participant,
                            context=context,
                            result_content=result_content,
                            final_earnings=final_earnings,
                            consensus_reached=discussion_result.consensus_reached,
                            config=config
                        )
                        context.memory = updated_memory
                        
                        self.logger.debug(f"Memory updated for {participant.name} with Phase 2 results via MemoryService")
                    
                    except Exception as memory_error:
                        self.logger.warning(f"Failed to update memory for {participant.name} via MemoryService: {memory_error}")
                        # Continue without memory update - don't block the process
                else:
                    # Fallback: append results directly to memory without using complex memory update
                    try:
                        self.logger.debug(f"Using fallback path for {participant.name} (no MemoryService available)")
                        # Ensure fallback also uses the final-results wrapper
                        wrapped_content = participant_lang_manager.get(
                            "memory.final_results_format",
                            result_content=result_content
                        )
                        
                        # Debug: log what we're appending
                        preview = wrapped_content[:150].replace('\n', ' ')
                        self.logger.debug(f"Fallback appending to memory for {participant.name}: {preview}")
                        
                        # Simple memory append - avoid calling participant.update_memory() which uses "Recent Activity" template
                        if context.memory and not context.memory.endswith('\n'):
                            context.memory += '\n'
                        context.memory += wrapped_content
                        
                        self.logger.debug(f"Memory updated directly for {participant.name} using simple append")
                    except Exception as fallback_error:
                        self.logger.warning(f"Fallback memory update failed for {participant.name}: {fallback_error}")
                
                updated_contexts.append(context)
            
            self.logger.info("Phase 2 results delivery and memory update completed successfully")
            return updated_contexts
            
        except Exception as e:
            self.logger.warning(f"Failed to deliver results and update memory: {e}")
            # Return original contexts to avoid breaking the flow
            return contexts
    

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

                # Create async task for getting final ranking - use retry method if enabled
                if self.config and self.config.enable_intelligent_retries:
                    task = asyncio.create_task(
                        self._get_final_ranking_task_with_retry(participant, context, utility_agent)
                    )
                else:
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
            updated_memory = await participant.update_memory(
                result_content,
                context.bank_balance,
                phase=context.phase,
                round_number=context.round_number,
                role_description=context.role_description,
                transcript_logger=self.transcript_logger
            )
            context.memory = updated_memory
            
            # Get final ranking using proven Phase 1 pattern
            final_ranking_prompt = self.language_manager.get("prompts.phase2_final_ranking_prompt")
            result = await self._invoke_phase2_interaction(
                participant=participant,
                context=context,
                prompt=final_ranking_prompt,
                interaction_type="final_ranking"
            )
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
            context.stage = ExperimentStage.FINAL_RANKING

            # Get final ranking using proven Phase 1 pattern
            final_ranking_prompt = self.language_manager.get("prompts.phase2_final_ranking_prompt")

            # Clear stale context values to prevent discussion-mode formatting in final ranking prompts
            context.interaction_type = None
            context.round_number = None
            context.internal_reasoning = ""
            
            result = await self._invoke_phase2_interaction(
                participant=participant,
                context=context,
                prompt=final_ranking_prompt,
                interaction_type="final_ranking"
            )
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


    async def _get_final_ranking_task_with_retry(
        self,
        participant: "ParticipantAgent",
        context: ParticipantContext,
        utility_agent
    ) -> PrincipleRanking:
        """
        Get final ranking from a single participant with retry support.

        This method follows the Phase 1 retry pattern, using the config's
        enable_intelligent_retries setting to determine whether to apply
        intelligent retry logic with participant feedback.

        Args:
            participant: The participant agent
            context: Pre-updated participant context with results in memory
            utility_agent: Utility agent for parsing responses

        Returns:
            PrincipleRanking from the participant
        """
        try:
            # No memory update needed - context is pre-updated from deliver_results_and_update_memory

            # Get final ranking prompt
            final_ranking_prompt = self.language_manager.get("prompts.phase2_final_ranking_prompt")

            # Clear stale context values to prevent discussion-mode formatting in final ranking prompts
            context.interaction_type = None
            context.round_number = None
            context.internal_reasoning = ""

            # Always get initial response from participant
            result = await self._invoke_phase2_interaction(
                participant=participant,
                context=context,
                prompt=final_ranking_prompt,
                interaction_type="final_ranking"
            )
            text_response = result.final_output

            # Check if intelligent retries are enabled and config is available
            if self.config and self.config.enable_intelligent_retries:
                # Create retry callback that handles participant re-prompting
                async def retry_callback(feedback: str) -> str:
                    try:
                        self.logger.info(f"Intelligent retry callback triggered for {participant.name} in Phase 2 final ranking")

                        # Build retry prompt with original prompt + feedback + guidance
                        retry_prompt = self._build_retry_prompt(final_ranking_prompt, feedback, self.config.retry_feedback_detail)

                        # Get participant's retry response
                        retry_result = await self._invoke_phase2_interaction(
                            participant=participant,
                            context=context,
                            prompt=retry_prompt,
                            interaction_type="final_ranking"
                        )
                        retry_response = retry_result.final_output

                        # Update participant memory with retry experience if enabled
                        if self.config.memory_update_on_retry:
                            await self._update_memory_with_retry_experience(
                                participant, context, feedback, retry_response
                            )

                        self.logger.info(f"Retry callback successful for {participant.name}, response length: {len(retry_response)}")
                        return retry_response

                    except Exception as e:
                        self.logger.warning(f"Retry callback failed for {participant.name} in Phase 2 final ranking: {e}")
                        # Return empty string to signal failure to utility agent
                        return ""

                # Use enhanced parsing with feedback capability
                parsed_ranking = await utility_agent.parse_principle_ranking_enhanced_with_feedback(
                    text_response,
                    max_retries=self.config.max_participant_retries + 1,  # +1 for initial attempt
                    participant_retry_callback=retry_callback
                )
            else:
                # Fall back to existing enhanced parsing without retries
                try:
                    parsed_ranking = await utility_agent.parse_principle_ranking_enhanced(text_response)
                except Exception as e:
                    # Log parsing failure and re-raise with context
                    self.logger.warning(f"Failed to parse Phase 2 final ranking for {participant.name}: {e}")
                    # Create classified parsing error for better error handling
                    parsing_error = create_parsing_error(
                        response=text_response,
                        parsing_operation="phase2_final_ranking",
                        expected_format="ranking",
                        additional_context={
                            "participant_name": participant.name,
                            "task_name": "phase2_final_ranking",
                            "retry_enabled": False
                        },
                        cause=e
                    )
                    raise parsing_error

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
        participant: "ParticipantAgent",
        context: ParticipantContext,
        feedback: str,
        retry_response: str
    ) -> None:
        """
        Update participant memory with retry experience using MemoryService.

        Uses the semantically appropriate update_memory_selective method with
        SIMPLE_STATUS_UPDATE event type for retry experiences, avoiding
        inappropriate use of update_final_results_memory.

        Args:
            participant: The participant agent whose memory needs updating
            context: Current participant context
            feedback: Feedback provided for the retry
            retry_response: The participant's retry response
        """
        try:
            language_manager = self.language_manager
            retry_memory_content = f"""{language_manager.get('memory_field_labels.retry_feedback') if hasattr(language_manager, 'retry_prompts') else 'Retry feedback:'} {feedback}
{language_manager.get('memory_field_labels.your_response') if hasattr(language_manager, 'retry_prompts') else 'My retry response:'} {retry_response}"""

            # Use MemoryService if available, otherwise fallback to MemoryManager
            if self.memory_service:
                try:
                    # Import MemoryEventType for proper retry experience classification
                    from utils.selective_memory_manager import MemoryEventType

                    # Use MemoryService for memory update with appropriate event type
                    # SIMPLE_STATUS_UPDATE is appropriate for retry experiences
                    updated_memory = await self.memory_service.update_memory_selective(
                        agent=participant,
                        context=context,
                        content=retry_memory_content,
                        event_type=MemoryEventType.SIMPLE_STATUS_UPDATE,
                        event_metadata={
                            'retry_context': True,
                            'participant_name': participant.name,
                            'has_feedback': bool(feedback),
                            'has_retry_response': bool(retry_response)
                        },
                        config=self.config
                    )
                    context.memory = updated_memory
                    self.logger.info(f"Updated {participant.name} memory with retry experience via MemoryService")
                except Exception as e:
                    self.logger.warning(f"Failed to update memory via MemoryService for {participant.name}, falling back to MemoryManager: {e}")
                    # Fallback to MemoryManager
                    await self._fallback_memory_update(participant, context, retry_memory_content)
            else:
                # Fallback to MemoryManager
                await self._fallback_memory_update(participant, context, retry_memory_content)

        except Exception as e:
            self.logger.warning(f"Failed to update memory with retry experience for {participant.name}: {e}")

    async def _fallback_memory_update(
        self,
        participant: "ParticipantAgent",
        context: ParticipantContext,
        retry_memory_content: str
    ) -> None:
        """Fallback memory update using MemoryManager."""
        try:
            # Use existing memory guidance style from config if available
            memory_guidance_style = self.config.memory_guidance_style if self.config else "narrative"

            # Extract round and phase information for proper template selection
            round_number = getattr(context, 'round_number', None)
            phase = getattr(context, 'phase', None) or "phase_2"  # Default to phase_2 since this is CounterfactualsService

            updated_memory = await MemoryManager.prompt_agent_for_memory_update(
                participant, context, retry_memory_content,
                memory_guidance_style=memory_guidance_style,
                language_manager=self.language_manager,
                error_handler=None,  # We don't have error_handler in service
                utility_agent=None,   # We don't have utility_agent in service
                round_number=round_number,
                phase=phase,
                transcript_logger=self.transcript_logger
            )
            context.memory = updated_memory
            self.logger.info(f"Updated {participant.name} memory with retry experience via MemoryManager fallback")
        except Exception as e:
            self.logger.warning(f"MemoryManager fallback also failed for {participant.name}: {e}")
