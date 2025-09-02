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
        seed_manager: Optional[SeedManager] = None
    ):
        """
        Initialize CounterfactualsService with dependencies.
        
        Args:
            language_manager: Provider for localized text
            settings: Phase 2 configuration settings
            logger: Optional logger for service operations
            seed_manager: Optional seed manager for reproducible randomness
        """
        self.language_manager = language_manager
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.seed_manager = seed_manager
    
    async def apply_group_principle_and_calculate_payoffs(
        self,
        discussion_result: GroupDiscussionResult,
        config: ExperimentConfiguration,
        participants: List["ParticipantAgent"]
    ) -> tuple[Dict[str, float], Dict[str, str], Dict[str, Dict[str, float]]]:
        """
        Apply chosen principle or random assignment if no consensus.
        
        Exact contract match: returns (payoffs, assigned_classes, alternative_earnings_by_agent)
        Handles consensus vs random assignment logic.
        
        Args:
            discussion_result: Result of group discussion with consensus info
            config: Experiment configuration
            participants: List of participant agents
            
        Returns:
            tuple: (payoffs dict, assigned_classes dict, alternative_earnings_by_agent dict)
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
                    assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution, config.income_class_probabilities)
                    payoffs[participant.name] = earnings
                    assigned_classes[participant.name] = assigned_class.value
            else:
                # Random assignment - each participant gets random income class from random distribution
                for participant in participants:
                    if self.seed_manager:
                        random_distribution = self.seed_manager.random.choice(distribution_set.distributions)
                    else:
                        random_distribution = random.choice(distribution_set.distributions)
                    assigned_class, earnings = DistributionGenerator.calculate_payoff(random_distribution, config.income_class_probabilities)
                    payoffs[participant.name] = earnings
                    assigned_classes[participant.name] = assigned_class.value
            
            # Calculate counterfactual earnings for transparency
            alternative_earnings_by_agent = await self.calculate_phase2_counterfactuals(
                distribution_set, assigned_classes, consensus_principle, constraint_amount
            )
            
            self.logger.debug(f"Payoffs calculated for {len(participants)} participants")
            return payoffs, assigned_classes, alternative_earnings_by_agent
            
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
        consensus_result: GroupDiscussionResult
    ) -> str:
        """
        Build Phase 2 results with counterfactual table (matching Phase 1 transparency).
        
        Build detailed Phase 2 results matching Phase 1 transparency level.
        Includes class assignment and full counterfactual analysis.
        
        Args:
            participant_name: Name of the participant
            final_earnings: Participant's final earnings
            assigned_class: Income class assigned to participant
            alternative_earnings: Alternative earnings under each principle
            consensus_result: Result of group discussion
            
        Returns:
            Formatted results string with counterfactual analysis
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
            
            # Add counterfactual analysis table
            counterfactuals_header = self.language_manager.get('results.counterfactuals_header')
            result_parts.append(f"\n{counterfactuals_header}:")
            
            # Format alternative earnings for each principle
            principle_names = {
                'maximizing_floor': self.language_manager.get('principles.maximizing_floor'),
                'maximizing_average': self.language_manager.get('principles.maximizing_average'), 
                'maximizing_average_with_floor': self.language_manager.get('principles.maximizing_average_with_floor'),
                'maximizing_average_with_range': self.language_manager.get('principles.maximizing_average_with_range')
            }
            
            for principle_key, earnings in alternative_earnings.items():
                principle_name = principle_names.get(principle_key, principle_key)
                result_parts.append(f"- {principle_name}: ${earnings:.2f}")
            
            return "\n".join(result_parts)
            
        except Exception as e:
            self.logger.warning(f"Failed to build detailed results for {participant_name}: {e}")
            # Fallback to basic format
            return f"Phase 2 results: ${final_earnings:.2f}. Income class: {assigned_class}."
    
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
        logger: Optional[AgentCentricLogger] = None
    ) -> Dict[str, PrincipleRanking]:
        """
        Collect final rankings with enhanced transparency handling.
        
        Collect final principle rankings from all participants after providing
        them with comprehensive results including counterfactual analysis.
        
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
            
        Returns:
            Dict mapping participant names to their final principle rankings
        """
        try:
            final_ranking_tasks = []
            
            for i, participant in enumerate(participants):
                context = contexts[i]
                agent_config = config.agents[i]
                
                # Get participant's results
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
                    result_content = await self.build_detailed_results(
                        participant.name,
                        final_earnings,
                        assigned_class,
                        alternative_earnings,
                        discussion_result
                    )
                else:
                    # Use basic results (original behavior)
                    result_content = f"{self.language_manager.get('results.phase2_header')}: Phase 2 earnings: ${final_earnings:.2f}. "
                    if discussion_result.consensus_reached:
                        result_content += self.language_manager.get("voting_results.consensus_reached", principle_name=discussion_result.agreed_principle.principle.value) + "."
                    else:
                        result_content += self.language_manager.get("phase2_no_consensus") + "."
                
                # Create async task for getting final ranking
                task = asyncio.create_task(
                    self._get_final_ranking_task(participant, context, agent_config, result_content, utility_agent)
                )
                final_ranking_tasks.append((task, participant.name, assigned_class, final_earnings, context.memory, context.bank_balance))
            
            # Gather just the tasks for asyncio
            tasks = [task_info[0] for task_info in final_ranking_tasks]
            rankings_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and build final rankings dictionary
            final_rankings = {}
            
            for i, (ranking_result, (_, participant_name, assigned_class, final_earnings, memory, bank_balance)) in enumerate(zip(rankings_results, final_ranking_tasks)):
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
                
                # Log detailed participant info if logger provided
                if logger:
                    logger.log_participant_summary(
                        participant_name=participant_name,
                        final_earnings=final_earnings,
                        assigned_class=assigned_class,
                        final_memory_length=len(memory) if memory else 0,
                        final_bank_balance=bank_balance,
                        ranking=final_rankings[participant_name]
                    )
            
            self.logger.debug(f"Final rankings collected from {len(final_rankings)} participants")
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
            
            # Get final ranking
            ranking_response = await participant.get_final_ranking(context, agent_config.temperature)
            
            # Parse the ranking using utility agent
            parsed_ranking = await utility_agent.parse_principle_ranking_enhanced(ranking_response.content)
            
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
