"""
Core experiment data structures for the Frohlich Experiment.
"""
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from .principle_types import PrincipleChoice, PrincipleRanking, VoteResult


class ExperimentPhase(str, Enum):
    """The two main phases of the experiment."""
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"


class IncomeClass(str, Enum):
    """The five income classes in distributions."""
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    MEDIUM_LOW = "medium_low"
    LOW = "low"


class IncomeDistribution(BaseModel):
    """A single income distribution with five income levels."""
    high: int = Field(..., gt=0)
    medium_high: int = Field(..., gt=0)
    medium: int = Field(..., gt=0)
    medium_low: int = Field(..., gt=0)
    low: int = Field(..., gt=0)
    
    def get_income_by_class(self, income_class: IncomeClass) -> int:
        """Get income for a specific class."""
        return getattr(self, income_class.value)
    
    def get_floor_income(self) -> int:
        """Get the lowest income (floor)."""
        return self.low
    
    def get_average_income(self) -> float:
        """Get the average income across all classes."""
        return (self.high + self.medium_high + self.medium + self.medium_low + self.low) / 5
    
    def get_range(self) -> int:
        """Get the range (high - low)."""
        return self.high - self.low


class DistributionSet(BaseModel):
    """A set of 4 income distributions for an experiment round."""
    distributions: List[IncomeDistribution] = Field(..., min_items=4, max_items=4)
    multiplier: float = Field(..., gt=0, description="Applied to base distribution")


class ApplicationResult(BaseModel):
    """Result of applying a principle choice to distributions."""
    round_number: int
    principle_choice: PrincipleChoice
    chosen_distribution: IncomeDistribution
    assigned_income_class: IncomeClass
    earnings: float
    alternative_earnings: Dict[str, float] = Field(default_factory=dict, description="What participant would have earned under other distributions")


class Phase1Results(BaseModel):
    """Complete results for a participant's Phase 1."""
    participant_name: str
    initial_ranking: PrincipleRanking
    application_results: List[ApplicationResult]
    final_ranking: PrincipleRanking
    total_earnings: float
    final_memory_state: str = Field(..., description="Complete memory from Phase 1 for Phase 2 continuity")


class ParticipantContext(BaseModel):
    """Context object passed to agents containing current state."""
    name: str
    role_description: str
    bank_balance: float
    memory: str = Field(..., description="Continuous across Phase 1 and Phase 2")
    round_number: int
    phase: ExperimentPhase
    max_memory_length: int = 5000


class DiscussionStatement(BaseModel):
    """A statement made during group discussion."""
    participant_name: str
    statement: str
    round_number: int
    timestamp: datetime = Field(default_factory=datetime.now)
    contains_vote_proposal: bool = False


class GroupDiscussionState(BaseModel):
    """State of the group discussion."""
    round_number: int = 0
    statements: List[DiscussionStatement] = Field(default_factory=list)
    vote_history: List[VoteResult] = Field(default_factory=list)
    public_history: str = ""
    
    def add_statement(self, participant_name: str, statement: str):
        """Add statement to public history."""
        statement_obj = DiscussionStatement(
            participant_name=participant_name,
            statement=statement,
            round_number=self.round_number
        )
        self.statements.append(statement_obj)
        self.public_history += f"\n{participant_name}: {statement}"
    
    def add_vote_result(self, vote_result: VoteResult):
        """Add vote result to public history."""
        self.vote_history.append(vote_result)
        vote_summary = f"Vote conducted - Consensus: {'Yes' if vote_result.consensus_reached else 'No'}"
        if vote_result.consensus_reached and vote_result.agreed_principle:
            vote_summary += f" (Agreed on: {vote_result.agreed_principle.principle.value})"
        self.public_history += f"\n[VOTE RESULT] {vote_summary}"


class GroupDiscussionResult(BaseModel):
    """Final result of group discussion phase."""
    consensus_reached: bool
    agreed_principle: Optional[PrincipleChoice] = None
    final_round: int
    discussion_history: str
    vote_history: List[VoteResult]


class Phase2Results(BaseModel):
    """Complete results for Phase 2."""
    discussion_result: GroupDiscussionResult
    payoff_results: Dict[str, float] = Field(default_factory=dict, description="Final payoffs for each participant")
    final_rankings: Dict[str, PrincipleRanking] = Field(default_factory=dict, description="Final principle rankings by each participant")


class ExperimentResults(BaseModel):
    """Complete results for the entire experiment."""
    experiment_id: str
    timestamp: datetime
    total_runtime: float = Field(..., description="Total runtime in seconds")
    phase1_results: List[Phase1Results]
    phase2_results: Phase2Results
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }