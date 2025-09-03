"""
Memory content builders for creating compact round deltas.
Replaces verbose, repetitive memory content with concise summaries.
"""
from typing import Dict, Optional, List
from models.experiment_types import (
    IncomeDistribution, IncomeClass, 
    ApplicationResult, DiscussionStatement
)
from models.principle_types import PrincipleChoice
from utils.language_manager import LanguageManager


def build_phase1_delta(
    round_number: int,
    principle_choice: PrincipleChoice,
    assigned_class: IncomeClass,
    earnings: float,
    distribution_multiplier: float,
    rationale: Optional[str] = None,
    top_counterfactuals: Optional[List[str]] = None,
    original_values_mode: bool = False,
    original_values_situation: Optional[str] = None,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build compact Phase 1 round delta content.
    
    Args:
        round_number: Round number (1-4)
        principle_choice: Chosen justice principle
        assigned_class: Assigned income class
        earnings: Actual earnings from chosen principle
        distribution_multiplier: Applied multiplier for this round
        rationale: Brief rationale (optional, truncated if too long)
        top_counterfactuals: 1-2 most significant counterfactual highlights
        original_values_mode: Whether original values mode was used
        original_values_situation: Original values situation if applicable
        
    Returns:
        Compact round summary for memory
    """
    # Build base delta
    if language_manager:
        # Localized principle display name
        principle_key = principle_choice.principle.value
        try:
            principle_name = language_manager.get(f"common.principle_names.{principle_key}")
        except Exception:
            principle_name = principle_key
        round_prefix = language_manager.get("memory.round_prefix") if hasattr(language_manager, 'get') else "Round "
        delta_parts = [
            language_manager.get("memory.labels.round_applied", round_num=round_number, principle=principle_name),
            language_manager.get("memory.labels.class_earnings", assigned_class=assigned_class.value, earnings=earnings)
        ]
    else:
        delta_parts = [
            f"Round {round_number}: Applied {principle_choice.principle.value}",
            f"Class: {assigned_class.value}, Earnings: {earnings}"
        ]
    
    # Add distribution info (concise)
    if original_values_mode and original_values_situation:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.original_values", situation=original_values_situation))
        else:
            delta_parts.append(f"(Original Values: {original_values_situation})")
    else:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.multiplier", multiplier=distribution_multiplier))
        else:
            delta_parts.append(f"(Multiplier: {distribution_multiplier:.2f})")
    
    # Add constraint info if relevant
    if principle_choice.constraint_amount is not None:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.constraint", constraint=principle_choice.constraint_amount))
        else:
            delta_parts.append(f"Constraint: {principle_choice.constraint_amount}")
    
    # Add brief rationale if provided and not too long
    if rationale and len(rationale) <= 200:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.reasoning", reasoning=rationale))
        else:
            delta_parts.append(f"Reasoning: {rationale}")
    elif rationale and len(rationale) > 200:
        # Truncate long rationale
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.reasoning", reasoning=f"{rationale[:200]}..."))
        else:
            delta_parts.append(f"Reasoning: {rationale[:200]}...")
    
    # Add top counterfactual highlights (not full table)
    if top_counterfactuals:
        highlights = ", ".join(top_counterfactuals[:2])  # Max 2 highlights
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.key_alternatives", highlights=highlights))
        else:
            delta_parts.append(f"Key alternatives: {highlights}")
    
    return " | ".join(delta_parts)


def build_phase2_delta(
    round_number: int,
    participant_name: str,
    statement: Optional[str] = None,
    speaking_order_position: Optional[int] = None,
    vote_intention: Optional[bool] = None,
    favored_principle: Optional[str] = None,
    consensus_reached: Optional[bool] = None,
    agreed_principle: Optional[str] = None,
    is_vote_round: bool = False,
    internal_reasoning: Optional[str] = None,
    include_internal_reasoning: bool = False,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build compact Phase 2 round delta content.
    
    Args:
        round_number: Discussion round number
        participant_name: Name of participant
        statement: Brief statement made (optional, truncated if too long)
        speaking_order_position: Position in speaking order
        vote_intention: Whether participant intends to vote yes/no
        favored_principle: Participant's favored principle
        consensus_reached: Whether consensus was reached in this round
        agreed_principle: Principle agreed upon if consensus reached
        is_vote_round: Whether this was a voting round
        internal_reasoning: Internal reasoning (optional)
        include_internal_reasoning: Whether to include internal reasoning
        
    Returns:
        Compact round summary for memory
    """
    if language_manager:
        delta_parts = [f"{language_manager.get('memory.round_prefix')}{round_number}"]
    else:
        delta_parts = [f"Round {round_number}"]
    
    # Add speaking order info
    if speaking_order_position is not None:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.speaking", position=speaking_order_position))
        else:
            delta_parts.append(f"Speaking #{speaking_order_position}")
    
    # Add brief statement (truncated if too long)
    if statement:
        short = statement if len(statement) <= 150 else f"{statement[:150]}..."
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.statement", statement=short))
        else:
            delta_parts.append(f"Statement: {short}")
    
    # Add stance information
    if favored_principle:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.favored", principle=favored_principle))
        else:
            delta_parts.append(f"Favored: {favored_principle}")
    
    # Add vote intention
    if vote_intention is not None:
        if language_manager:
            vote_status = language_manager.get("common.yes_no.yes") if vote_intention else language_manager.get("common.yes_no.no")
            delta_parts.append(language_manager.get("memory.labels.vote_intention", vote_status=vote_status))
        else:
            vote_status = "Yes" if vote_intention else "No"
            delta_parts.append(f"Vote intention: {vote_status}")
    
    # Add vote results if this was a vote round
    if is_vote_round:
        if consensus_reached:
            consensus_info = f"Consensus: YES"
            if agreed_principle:
                consensus_info += f" (Agreed: {agreed_principle})"
            delta_parts.append(consensus_info)
        else:
            delta_parts.append("Consensus: NO")
    
    # Add internal reasoning if enabled and provided
    if include_internal_reasoning and internal_reasoning:
        if len(internal_reasoning) <= 100:
            delta_parts.append(f"Reasoning: {internal_reasoning}")
        else:
            delta_parts.append(f"Reasoning: {internal_reasoning[:100]}...")
    
    return " | ".join(delta_parts)


def build_distribution_summary(
    distributions: List[IncomeDistribution], 
    multiplier: float,
    original_values_mode: bool = False,
    original_values_situation: Optional[str] = None
) -> str:
    """
    Build concise distribution summary instead of full table.
    
    Args:
        distributions: List of 4 income distributions
        multiplier: Applied multiplier
        original_values_mode: Whether original values mode was used
        original_values_situation: Original values situation if applicable
        
    Returns:
        Brief distribution summary
    """
    if original_values_mode and original_values_situation:
        return f"Distributions: Original Values Mode - {original_values_situation}"
    
    # Calculate range of values across all distributions for summary
    all_values = []
    for dist in distributions:
        all_values.extend([dist.high, dist.medium_high, dist.medium, dist.medium_low, dist.low])
    
    min_val = min(all_values)
    max_val = max(all_values)
    
    return f"Distributions: 4 options (range: {min_val}-{max_val}, multiplier: {multiplier:.2f})"


def extract_counterfactual_highlights(
    alternative_earnings: Dict[str, float],
    actual_earnings: float,
    max_highlights: int = 2
) -> List[str]:
    """
    Extract the most significant counterfactual outcomes.
    
    Args:
        alternative_earnings: Dictionary of alternative earnings by principle
        actual_earnings: Actual earnings received
        max_highlights: Maximum number of highlights to return
        
    Returns:
        List of brief counterfactual highlights
    """
    highlights = []
    
    # Find the best and worst alternatives
    sorted_alternatives = sorted(
        alternative_earnings.items(), 
        key=lambda x: x[1], 
        reverse=True
    )
    
    # Add highest alternative if significantly different
    if sorted_alternatives:
        best_alt, best_earnings = sorted_alternatives[0]
        if best_earnings > actual_earnings * 1.1:  # At least 10% better
            diff = best_earnings - actual_earnings
            highlights.append(f"{best_alt}: +{diff:.0f}")
    
    # Add lowest alternative if significantly different
    if len(sorted_alternatives) > 1:
        worst_alt, worst_earnings = sorted_alternatives[-1]
        if worst_earnings < actual_earnings * 0.9:  # At least 10% worse
            diff = actual_earnings - worst_earnings
            highlights.append(f"{worst_alt}: -{diff:.0f}")
    
    return highlights[:max_highlights]


def build_phase2_detailed_delta(
    participant_name: str,
    final_earnings: float,
    assigned_class: str,
    alternative_earnings: Dict[str, float],
    consensus_reached: bool,
    agreed_principle: Optional[str] = None,
    constraint_amount: Optional[int] = None,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build detailed Phase 2 results delta for memory content.
    Matches Phase 1 level of detail with class assignment and counterfactual analysis.
    
    Args:
        participant_name: Name of the participant
        final_earnings: Final earnings from Phase 2
        assigned_class: Assigned income class
        alternative_earnings: Earnings under each principle
        consensus_reached: Whether group consensus was reached
        agreed_principle: Principle agreed upon (if consensus reached)
        constraint_amount: Constraint amount if applicable
        
    Returns:
        Detailed Phase 2 results summary for memory
    """
    delta_parts = []
    
    # Base result
    if consensus_reached:
        if language_manager:
            if constraint_amount:
                delta_parts.append(language_manager.get(
                    "voting_results.consensus_with_constraint",
                    principle_name=agreed_principle,
                    constraint_amount=constraint_amount
                ))
            else:
                delta_parts.append(language_manager.get(
                    "voting_results.consensus_reached",
                    principle_name=agreed_principle
                ))
        else:
            consensus_info = f"Group consensus: {agreed_principle}"
            if constraint_amount:
                consensus_info += f" (${constraint_amount:,})"
            delta_parts.append(consensus_info)
    else:
        if language_manager:
            delta_parts.append(language_manager.get("memory.labels.no_consensus_random"))
        else:
            delta_parts.append("No consensus - random assignment")
    
    # Personal outcome
    if language_manager:
        delta_parts.append(language_manager.get(
            "memory.labels.class_earnings",
            assigned_class=assigned_class,
            earnings=final_earnings
        ))
    else:
        delta_parts.append(f"Class: {assigned_class}, Earnings: ${final_earnings:.2f}")
    
    # Counterfactual highlights
    if alternative_earnings:
        highlights = extract_counterfactual_highlights(
            alternative_earnings, final_earnings, max_highlights=2
        )
        if highlights:
            if language_manager:
                delta_parts.append(language_manager.get(
                    "memory.labels.alternatives",
                    highlights=", ".join(highlights)
                ))
            else:
                delta_parts.append(f"Alternatives: {', '.join(highlights)}")
    
    return " | ".join(delta_parts)


def extract_phase2_counterfactual_insights(
    alternative_earnings: Dict[str, float],
    actual_earnings: float,
    principle_display_names: Dict[str, str],
    language_manager: Optional[LanguageManager] = None
) -> Dict[str, str]:
    """
    Extract detailed counterfactual insights for Phase 2 results.
    
    Args:
        alternative_earnings: Dictionary of alternative earnings by principle key
        actual_earnings: Actual earnings received
        principle_display_names: Mapping of principle keys to display names
        
    Returns:
        Dictionary with 'best' and 'worst' insight messages
    """
    insights = {}
    
    if not alternative_earnings:
        return insights
    
    best_earnings = max(alternative_earnings.values())
    worst_earnings = min(alternative_earnings.values())
    
    # Find which principles gave best/worst outcomes
    best_principle = next(k for k, v in alternative_earnings.items() if v == best_earnings)
    worst_principle = next(k for k, v in alternative_earnings.items() if v == worst_earnings)
    
    best_principle_name = principle_display_names.get(best_principle, best_principle)
    worst_principle_name = principle_display_names.get(worst_principle, worst_principle)
    
    best_diff = best_earnings - actual_earnings
    worst_diff = actual_earnings - worst_earnings
    
    # Best alternative insight
    if language_manager:
        if best_diff > 0:
            insights['best'] = language_manager.get(
                'phase2_counterfactual_insights_best_more',
                best_diff=best_diff, best_principle=best_principle_name
            )
        else:
            insights['best'] = language_manager.get('phase2_counterfactual_insights_best_same')
    else:
        if best_diff > 0:
            insights['best'] = f"Best alternative: Would have earned ${best_diff:.2f} more under {best_principle_name}"
        elif best_diff == 0:
            insights['best'] = "Best alternative: Current earnings match the best possible outcome"
        else:
            insights['best'] = "Best alternative: All other principles would have yielded less"
    
    # Worst alternative insight
    if language_manager:
        if worst_diff > 0:
            insights['worst'] = language_manager.get(
                'phase2_counterfactual_insights_worst_more',
                worst_diff=worst_diff, worst_principle=worst_principle_name
            )
        else:
            insights['worst'] = language_manager.get('phase2_counterfactual_insights_worst_same')
    else:
        if worst_diff > 0:
            insights['worst'] = f"Worst alternative: Would have earned ${worst_diff:.2f} less under {worst_principle_name}"
        elif worst_diff == 0:
            insights['worst'] = "Worst alternative: Current earnings match the worst possible outcome"
    
    return insights


def build_two_stage_voting_principle_selection_delta(
    participant_name: str,
    principle_num: int,
    principle_display_name: str,
    attempts_used: int,
    success: bool,
    raw_response: Optional[str] = None,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build memory content for two-stage voting principle selection (Stage 1).
    
    Args:
        participant_name: Name of the participant
        principle_num: Selected principle number (1-4) if successful
        principle_display_name: Display name of selected principle
        attempts_used: Number of attempts used
        success: Whether the stage was successful
        raw_response: The raw response (optional, truncated if too long)
        
    Returns:
        Compact memory delta for principle selection
    """
    # Header
    if language_manager:
        delta_parts = [language_manager.get("memory.two_stage.stage1_header")]
    else:
        delta_parts = ["Two-Stage Voting - Stage 1: Principle Selection"]
    
    if success:
        if language_manager:
            delta_parts.append(language_manager.get(
                "memory.two_stage.selected",
                principle_num=principle_num,
                principle_display_name=principle_display_name
            ))
            if attempts_used > 1:
                delta_parts.append(language_manager.get("memory.two_stage.attempts", attempts=attempts_used))
        else:
            delta_parts.append(f"Selected: {principle_num} ({principle_display_name})")
            if attempts_used > 1:
                delta_parts.append(f"Attempts: {attempts_used}")
    else:
        if language_manager:
            delta_parts.append(language_manager.get("memory.two_stage.failed_select"))
            delta_parts.append(language_manager.get("memory.two_stage.attempts", attempts=attempts_used))
        else:
            delta_parts.append("FAILED - Unable to select principle")
            delta_parts.append(f"Attempts: {attempts_used}")
    
    # Add raw response if it's short and meaningful
    if raw_response and len(raw_response.strip()) <= 50:
        if language_manager:
            delta_parts.append(language_manager.get("memory.two_stage.response_short", response=raw_response.strip()))
        else:
            delta_parts.append(f"Response: '{raw_response.strip()}'")
    elif raw_response and len(raw_response.strip()) > 50:
        delta_parts.append(f"Response: '{raw_response.strip()[:50]}...'")
    
    return " | ".join(delta_parts)


def build_two_stage_voting_amount_specification_delta(
    participant_name: str,
    principle_display_name: str,
    constraint_amount: Optional[int],
    attempts_used: int,
    success: bool,
    raw_response: Optional[str] = None,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build memory content for two-stage voting amount specification (Stage 2).
    
    Args:
        participant_name: Name of the participant
        principle_display_name: Display name of the constraint principle
        constraint_amount: Specified constraint amount if successful
        attempts_used: Number of attempts used
        success: Whether the stage was successful
        raw_response: The raw response (optional, truncated if too long)
        
    Returns:
        Compact memory delta for amount specification
    """
    if language_manager:
        delta_parts = [language_manager.get(
            "memory.two_stage.stage2_header",
            principle_display_name=principle_display_name
        )]
    else:
        delta_parts = [f"Two-Stage Voting - Stage 2: Amount Specification for {principle_display_name}"]
    
    if success and constraint_amount is not None:
        if language_manager:
            delta_parts.append(language_manager.get(
                "memory.two_stage.specified",
                constraint_amount=constraint_amount
            ))
            if attempts_used > 1:
                delta_parts.append(language_manager.get("memory.two_stage.attempts", attempts=attempts_used))
        else:
            delta_parts.append(f"Specified: ${constraint_amount:,}")
            if attempts_used > 1:
                delta_parts.append(f"Attempts: {attempts_used}")
    else:
        if language_manager:
            delta_parts.append(language_manager.get("memory.two_stage.failed_amount"))
            delta_parts.append(language_manager.get("memory.two_stage.attempts", attempts=attempts_used))
        else:
            delta_parts.append("FAILED - Unable to specify constraint amount")
            delta_parts.append(f"Attempts: {attempts_used}")
    
    # Add raw response if it's short and meaningful
    if raw_response and len(raw_response.strip()) <= 50:
        if language_manager:
            delta_parts.append(language_manager.get("memory.two_stage.response_short", response=raw_response.strip()))
        else:
            delta_parts.append(f"Response: '{raw_response.strip()}'")
    elif raw_response and len(raw_response.strip()) > 50:
        delta_parts.append(f"Response: '{raw_response.strip()[:50]}...'")
    
    return " | ".join(delta_parts)


def build_two_stage_voting_complete_delta(
    participant_name: str,
    principle_num: int,
    principle_display_name: str,
    constraint_amount: Optional[int] = None,
    consensus_reached: bool = False,
    agreed_principle: Optional[str] = None,
    total_stages: int = 1,
    total_attempts: int = 1,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build memory content for complete two-stage voting process.
    
    Args:
        participant_name: Name of the participant
        principle_num: Selected principle number (1-4)
        principle_display_name: Display name of selected principle
        constraint_amount: Constraint amount if applicable
        consensus_reached: Whether group consensus was achieved
        agreed_principle: Group's agreed principle if consensus reached
        total_stages: Total number of voting stages completed (1 or 2)
        total_attempts: Total attempts across all stages
        
    Returns:
        Compact memory delta for complete voting process
    """
    if language_manager:
        delta_parts = [language_manager.get("memory.two_stage.complete_header")]
    else:
        delta_parts = ["Two-Stage Voting Complete"]
    
    # Personal vote
    if language_manager:
        if constraint_amount is not None:
            delta_parts.append(language_manager.get(
                "memory.two_stage.vote_info_with_constraint",
                principle_num=principle_num,
                principle_display_name=principle_display_name,
                constraint_amount=constraint_amount
            ))
        else:
            delta_parts.append(language_manager.get(
                "memory.two_stage.vote_info",
                principle_num=principle_num,
                principle_display_name=principle_display_name
            ))
    else:
        vote_info = f"Your vote: {principle_num} ({principle_display_name})"
        if constraint_amount is not None:
            vote_info += f" with ${constraint_amount:,} constraint"
        delta_parts.append(vote_info)
    
    # Process efficiency
    if language_manager:
        if total_stages == 2:
            delta_parts.append(language_manager.get("memory.two_stage.process_two_stage"))
        else:
            delta_parts.append(language_manager.get("memory.two_stage.process_single_stage"))
    else:
        if total_stages == 2:
            delta_parts.append("Two-stage process (principle + amount)")
        else:
            delta_parts.append("Single-stage process (principle only)")
    
    if total_attempts > total_stages:
        if language_manager:
            delta_parts.append(language_manager.get("memory.two_stage.total_attempts", total_attempts=total_attempts))
        else:
            delta_parts.append(f"Total attempts: {total_attempts}")
    
    # Group outcome
    if consensus_reached:
        if language_manager:
            if agreed_principle:
                delta_parts.append(language_manager.get("memory.two_stage.consensus_yes_with_agreed", agreed_principle=agreed_principle))
            else:
                delta_parts.append(language_manager.get("memory.two_stage.consensus_yes"))
        else:
            consensus_info = "Group consensus: YES"
            if agreed_principle:
                consensus_info += f" (Agreed: {agreed_principle})"
            delta_parts.append(consensus_info)
    else:
        if language_manager:
            delta_parts.append(language_manager.get("memory.two_stage.consensus_no"))
        else:
            delta_parts.append("Group consensus: NO")
    
    return " | ".join(delta_parts)
