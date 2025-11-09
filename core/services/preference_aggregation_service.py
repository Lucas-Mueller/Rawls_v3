"""
Preference Aggregation Service for Hypothesis 3

This service implements surgical (code-based, not LLM-based) aggregation of Phase 1 preference
rankings to determine the least popular principle among non-manipulator agents.

Used for manipulator targeting in hypothesis testing scenarios where we need deterministic,
objective preference aggregation without LLM inference.
"""
from typing import List, Dict, Any, Optional
from collections import Counter

from models import Phase1Results, PrincipleRanking


class PreferenceAggregationService:
    """
    Aggregates Phase 1 preference rankings to determine least popular principle.

    This service provides deterministic, surgical aggregation using Borda count scoring:
    - 1st place = 3 points
    - 2nd place = 2 points
    - 3rd place = 1 point
    - 4th place = 0 points

    Lower total score = less popular principle across the group.

    Attributes:
        language_manager: Language manager for localization (optional)

    Example:
        >>> service = PreferenceAggregationService(language_manager)
        >>> result = service.aggregate_preferences(
        ...     phase1_results=phase1_results,
        ...     manipulator_name="Agent_4",
        ...     tiebreak_order=['maximizing_floor', 'maximizing_average', ...]
        ... )
        >>> print(result['least_popular_principle'])
        'maximizing_average_range_constraint'
    """

    def __init__(self, language_manager=None):
        """
        Initialize the preference aggregation service.

        Args:
            language_manager: Optional language manager for localized principle names
        """
        self.language_manager = language_manager

    def aggregate_preferences(
        self,
        phase1_results: List[Phase1Results],
        manipulator_name: str,
        tiebreak_order: List[str]
    ) -> Dict[str, Any]:
        """
        Aggregate final rankings from non-manipulator agents.

        This method:
        1. Filters out manipulator agent from Phase 1 results
        2. Extracts final rankings from remaining agents
        3. Calculates Borda count scores for each principle
        4. Identifies least popular principle (lowest score)
        5. Applies tiebreaker if multiple principles tied for least popular

        Args:
            phase1_results: List of Phase 1 results for all agents
            manipulator_name: Name of manipulator agent to exclude (e.g., "Agent_4")
            tiebreak_order: Deterministic preference order for breaking ties
                           (first principle in list wins the tie)

        Returns:
            Dictionary containing:
                - principle_scores: Dict[str, float] - Borda scores (higher = more popular)
                - least_popular_principle: str - The principle with lowest score
                - aggregation_method: str - Always 'borda_count'
                - non_manipulator_rankings: List[Dict] - Rankings used for aggregation
                - tiebreak_applied: bool - Whether tiebreaker was needed
                - tied_principles: List[str] - Principles that tied (if any)

        Raises:
            ValueError: If no non-manipulator agents found or rankings invalid
        """
        # Filter out manipulator
        non_manipulator_results = [
            r for r in phase1_results
            if r.participant_name != manipulator_name
        ]

        if not non_manipulator_results:
            raise ValueError(
                f"No non-manipulator agents found (all {len(phase1_results)} agents filtered out)"
            )

        # Extract final rankings
        rankings = [r.final_ranking for r in non_manipulator_results]

        if not rankings:
            raise ValueError("No final rankings available for aggregation")

        # Calculate Borda scores
        principle_scores = self._calculate_borda_scores(rankings)

        if not principle_scores:
            raise ValueError("Failed to calculate preference scores")

        # Find minimum score (least popular)
        min_score = min(principle_scores.values())
        least_popular_candidates = [
            principle for principle, score in principle_scores.items()
            if score == min_score
        ]

        # Apply tiebreaker if needed
        tiebreak_applied = len(least_popular_candidates) > 1

        if tiebreak_applied:
            least_popular = self._apply_tiebreaker(
                least_popular_candidates,
                tiebreak_order
            )
        else:
            least_popular = least_popular_candidates[0]

        # Build rankings list for transparency
        non_manipulator_rankings = []
        for result in non_manipulator_results:
            ranking_list = [
                r.principle.value for r in result.final_ranking.rankings
            ]
            non_manipulator_rankings.append({
                'agent_name': result.participant_name,
                'ranking': ranking_list
            })

        return {
            'principle_scores': principle_scores,
            'least_popular_principle': least_popular,
            'aggregation_method': 'borda_count',
            'non_manipulator_rankings': non_manipulator_rankings,
            'tiebreak_applied': tiebreak_applied,
            'tied_principles': least_popular_candidates if tiebreak_applied else []
        }

    def _calculate_borda_scores(
        self,
        rankings: List[PrincipleRanking]
    ) -> Dict[str, float]:
        """
        Calculate Borda count scores from preference rankings.

        Borda count scoring:
        - 1st place: 3 points
        - 2nd place: 2 points
        - 3rd place: 1 point
        - 4th place: 0 points

        Args:
            rankings: List of PrincipleRanking objects from Phase 1 results

        Returns:
            Dictionary mapping principle names to total Borda scores
            Higher score = more popular across agents

        Example:
            Agent 1: [A, B, C, D] -> A=3, B=2, C=1, D=0
            Agent 2: [B, A, C, D] -> B=3, A=2, C=1, D=0
            Total:   A=5, B=5, C=2, D=0 (D is least popular)
        """
        # Points for each position (0-indexed)
        position_points = {
            0: 3,  # 1st place
            1: 2,  # 2nd place
            2: 1,  # 3rd place
            3: 0   # 4th place
        }

        scores: Dict[str, float] = {}

        for ranking in rankings:
            # Each ranking should have 4 principles
            for position, ranked_principle in enumerate(ranking.rankings):
                principle_name = ranked_principle.principle.value
                points = position_points.get(position, 0)

                if principle_name not in scores:
                    scores[principle_name] = 0.0

                scores[principle_name] += points

        return scores

    def _apply_tiebreaker(
        self,
        tied_principles: List[str],
        tiebreak_order: List[str]
    ) -> str:
        """
        Apply deterministic tiebreaker using config's tiebreak_order.

        The tiebreak_order represents the manipulator's preference order from the config.
        We select the FIRST principle in tiebreak_order that appears in the tied set,
        making the manipulator's predetermined preference the tiebreaker.

        Args:
            tied_principles: List of principle names with identical (lowest) scores
            tiebreak_order: Preference-ordered list of all principles from config

        Returns:
            Single principle name selected as least popular after tiebreak

        Raises:
            ValueError: If no tied principle found in tiebreak_order

        Example:
            tied_principles = ['maximizing_floor', 'maximizing_average']
            tiebreak_order = ['maximizing_floor', 'maximizing_average', ...]
            Returns: 'maximizing_floor' (first in tiebreak_order)
        """
        if not tied_principles:
            raise ValueError("Cannot apply tiebreaker to empty list")

        if not tiebreak_order:
            # Fallback: alphabetical if no tiebreak order provided
            return sorted(tied_principles)[0]

        # Find first principle in tiebreak_order that appears in tied set
        for principle in tiebreak_order:
            if principle in tied_principles:
                return principle

        # Fallback if none match (should not happen with valid data)
        raise ValueError(
            f"No tied principle found in tiebreak order. "
            f"Tied: {tied_principles}, Order: {tiebreak_order}"
        )

    def format_aggregation_summary(
        self,
        aggregation_result: Dict[str, Any]
    ) -> str:
        """
        Format aggregation results as human-readable summary.

        Useful for logging and transparency in experiment reports.

        Args:
            aggregation_result: Result dictionary from aggregate_preferences()

        Returns:
            Formatted string summary of aggregation

        Example output:
            Preference Aggregation (Borda Count):
            - maximizing_floor: 8.0 points
            - maximizing_average: 6.0 points
            - maximizing_average_floor_constraint: 4.0 points
            - maximizing_average_range_constraint: 2.0 points (LEAST POPULAR)

            Tiebreaker applied: No
        """
        lines = ["Preference Aggregation (Borda Count):"]

        scores = aggregation_result['principle_scores']
        least_popular = aggregation_result['least_popular_principle']

        # Sort by score descending
        sorted_principles = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        for principle, score in sorted_principles:
            marker = " (LEAST POPULAR)" if principle == least_popular else ""
            lines.append(f"- {principle}: {score:.1f} points{marker}")

        lines.append("")
        tiebreak_applied = aggregation_result['tiebreak_applied']
        lines.append(f"Tiebreaker applied: {'Yes' if tiebreak_applied else 'No'}")

        if tiebreak_applied:
            tied = aggregation_result['tied_principles']
            lines.append(f"Tied principles: {', '.join(tied)}")

        return "\n".join(lines)
