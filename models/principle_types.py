"""
Justice principle types and related models for the Frohlich Experiment.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class JusticePrinciple(str, Enum):
    """The four justice principles participants can choose from."""
    MAXIMIZING_FLOOR = "maximizing_floor"
    MAXIMIZING_AVERAGE = "maximizing_average"
    MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT = "maximizing_average_floor_constraint"  
    MAXIMIZING_AVERAGE_RANGE_CONSTRAINT = "maximizing_average_range_constraint"


class CertaintyLevel(str, Enum):
    """Certainty levels for participant responses."""
    VERY_UNSURE = "very_unsure"
    UNSURE = "unsure"
    NO_OPINION = "no_opinion"
    SURE = "sure"
    VERY_SURE = "very_sure"


class PrincipleChoice(BaseModel):
    """A participant's choice of justice principle."""
    principle: JusticePrinciple
    constraint_amount: Optional[int] = Field(None, description="Required for constraint principles")
    certainty: CertaintyLevel
    reasoning: Optional[str] = Field(None, description="Participant's reasoning")
    
    # Disable validation by default for parsing
    model_config = {"validate_assignment": False, "arbitrary_types_allowed": True}
    
    def is_valid_constraint(self) -> bool:
        """Check if constraint amount is valid for voting."""
        if self.principle in [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]:
            return self.constraint_amount is not None and self.constraint_amount > 0
        return True  # Non-constraint principles are always valid
    
    def validate_for_voting(self) -> 'PrincipleChoice':
        """Validate and return a copy suitable for voting."""
        if not self.is_valid_constraint():
            raise ValueError(f"Invalid constraint for voting: principle={self.principle.value}, constraint={self.constraint_amount}")
        
        # Return self since validation passed
        return self
    
    @classmethod
    def create_for_parsing(
        cls,
        principle: JusticePrinciple,
        constraint_amount: Optional[int] = None,
        certainty: CertaintyLevel = CertaintyLevel.SURE,
        reasoning: Optional[str] = None
    ) -> 'PrincipleChoice':
        """Create PrincipleChoice for parsing (no validation constraints)."""
        return cls(
            principle=principle,
            constraint_amount=constraint_amount,
            certainty=certainty,
            reasoning=reasoning
        )


class RankedPrinciple(BaseModel):
    """A principle with its ranking position."""
    principle: JusticePrinciple
    rank: int = Field(..., ge=1, le=4, description="Rank from 1 (best) to 4 (worst)")


class PrincipleRanking(BaseModel):
    """Complete ranking of all four principles."""
    rankings: List[RankedPrinciple] = Field(..., min_length=4, max_length=4)
    certainty: CertaintyLevel = Field(..., description="Overall certainty level for the entire ranking")
    
    @field_validator('rankings')
    @classmethod
    def validate_complete_ranking(cls, v):
        """Ensure all principles are ranked exactly once."""
        principles = [r.principle for r in v]
        ranks = [r.rank for r in v]
        
        # Check all principles are present
        expected_principles = set(JusticePrinciple)
        actual_principles = set(principles)
        if expected_principles != actual_principles:
            raise ValueError("All four principles must be ranked")
        
        # Check all ranks 1-4 are used exactly once
        expected_ranks = {1, 2, 3, 4}
        actual_ranks = set(ranks)
        if expected_ranks != actual_ranks:
            raise ValueError("Ranks must be 1, 2, 3, 4 used exactly once")
        
        return v


class VoteProposal(BaseModel):
    """A proposal to conduct a vote."""
    proposed_by: str
    proposal_text: str
    

class VoteResult(BaseModel):
    """Result of a group vote."""
    votes: List[PrincipleChoice]
    consensus_reached: bool
    agreed_principle: Optional[PrincipleChoice] = None
    vote_counts: Dict[str, int] = Field(default_factory=dict)
    individual_votes: List[Dict[str, Any]] = Field(default_factory=list, description="Individual vote details for each participant")
    disagreement_summary: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)