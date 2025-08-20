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


def build_phase1_delta(
    round_number: int,
    principle_choice: PrincipleChoice,
    assigned_class: IncomeClass,
    earnings: float,
    distribution_multiplier: float,
    rationale: Optional[str] = None,
    top_counterfactuals: Optional[List[str]] = None,
    original_values_mode: bool = False,
    original_values_situation: Optional[str] = None
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
    delta_parts = [
        f"Round {round_number}: Applied {principle_choice.principle.value}",
        f"Class: {assigned_class.value}, Earnings: {earnings}"
    ]
    
    # Add distribution info (concise)
    if original_values_mode and original_values_situation:
        delta_parts.append(f"(Original Values: {original_values_situation})")
    else:
        delta_parts.append(f"(Multiplier: {distribution_multiplier:.2f})")
    
    # Add constraint info if relevant
    if principle_choice.constraint_amount is not None:
        delta_parts.append(f"Constraint: {principle_choice.constraint_amount}")
    
    # Add brief rationale if provided and not too long
    if rationale and len(rationale) <= 200:
        delta_parts.append(f"Reasoning: {rationale}")
    elif rationale and len(rationale) > 200:
        # Truncate long rationale
        delta_parts.append(f"Reasoning: {rationale[:200]}...")
    
    # Add top counterfactual highlights (not full table)
    if top_counterfactuals:
        highlights = ", ".join(top_counterfactuals[:2])  # Max 2 highlights
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
    include_internal_reasoning: bool = False
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
    delta_parts = [f"Round {round_number}"]
    
    # Add speaking order info
    if speaking_order_position is not None:
        delta_parts.append(f"Speaking #{speaking_order_position}")
    
    # Add brief statement (truncated if too long)
    if statement:
        if len(statement) <= 150:
            delta_parts.append(f"Statement: {statement}")
        else:
            # Truncate long statements
            delta_parts.append(f"Statement: {statement[:150]}...")
    
    # Add stance information
    if favored_principle:
        delta_parts.append(f"Favored: {favored_principle}")
    
    # Add vote intention
    if vote_intention is not None:
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