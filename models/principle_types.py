"""
Justice principle types and related models for the Frohlich Experiment.
"""
from enum import Enum
from typing import Optional, List, Dict
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
    
    @model_validator(mode='after')
    def validate_constraint_amount(self):
        """Validate that constraint principles have constraint amounts."""
        if self.principle in [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]:
            if self.constraint_amount is None:
                raise ValueError(f"Constraint amount required for principle {self.principle}")
            if self.constraint_amount <= 0:
                raise ValueError("Constraint amount must be positive")
        return self
    
    def is_valid_constraint(self) -> bool:
        """Check if constraint amount is valid. Returns True if valid."""
        if self.principle in [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]:
            if self.constraint_amount is None or self.constraint_amount <= 0:
                return False
        return True


class RankedPrinciple(BaseModel):
    """A principle with its ranking position."""
    principle: JusticePrinciple
    rank: int = Field(..., ge=1, le=4, description="Rank from 1 (best) to 4 (worst)")


class PrincipleRanking(BaseModel):
    """Complete ranking of all four principles."""
    rankings: List[RankedPrinciple] = Field(..., min_items=4, max_items=4)
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