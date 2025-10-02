"""
Core experiment data structures for the Frohlich Experiment.
"""
import math
import uuid
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from .principle_types import PrincipleChoice, PrincipleRanking, VoteResult


class ExperimentPhase(str, Enum):
    """The two main phases of the experiment."""
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"


class ExperimentStage(str, Enum):
    """Sub-stage within an experiment phase for contextual instructions."""
    INITIAL_RANKING = "initial_ranking"
    PRINCIPLE_EXPLANATION = "principle_explanation"
    POST_EXPLANATION_RANKING = "post_explanation_ranking"
    APPLICATION = "application"
    DISCUSSION = "discussion"
    VOTING = "voting"
    RESULTS = "results"
    FINAL_RANKING = "final_ranking"


class IncomeClass(str, Enum):
    """The five income classes in distributions."""
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    MEDIUM_LOW = "medium_low"
    LOW = "low"


class IncomeClassProbabilities(BaseModel):
    """Probabilities for income class assignment."""
    high: float = Field(default=0.05, ge=0, le=1)
    medium_high: float = Field(default=0.10, ge=0, le=1)
    medium: float = Field(default=0.50, ge=0, le=1)
    medium_low: float = Field(default=0.25, ge=0, le=1)
    low: float = Field(default=0.10, ge=0, le=1)
    
    @field_validator('high', 'medium_high', 'medium', 'medium_low', 'low')
    @classmethod
    def validate_probability_range(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Probabilities must be between 0 and 1')
        return v
    
    @model_validator(mode='after')
    def validate_probabilities_sum_to_one(self):
        total = self.high + self.medium_high + self.medium + self.medium_low + self.low
        if not math.isclose(total, 1.0, rel_tol=1e-9):
            raise ValueError(f'Probabilities must sum to 1.0, got {total}')
        return self


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
    
    def get_average_income(self, probabilities: Optional['IncomeClassProbabilities'] = None) -> float:
        """Get the average income across all classes with optional weighting."""
        if probabilities is None:
            # Backward compatibility: equal weights
            return (self.high + self.medium_high + self.medium + self.medium_low + self.low) / 5
        
        # Weighted average calculation
        return (
            self.high * probabilities.high +
            self.medium_high * probabilities.medium_high +
            self.medium * probabilities.medium +
            self.medium_low * probabilities.medium_low +
            self.low * probabilities.low
        )
    
    def get_range(self) -> int:
        """Get the range (high - low)."""
        return self.high - self.low


class DistributionSet(BaseModel):
    """A set of 4 income distributions for an experiment round."""
    distributions: List[IncomeDistribution] = Field(..., min_length=4, max_length=4)
    multiplier: float = Field(..., gt=0, description="Applied to base distribution")


class ApplicationResult(BaseModel):
    """Result of applying a principle choice to distributions."""
    round_number: int
    principle_choice: PrincipleChoice
    chosen_distribution: IncomeDistribution
    assigned_income_class: IncomeClass
    earnings: float
    alternative_earnings: Dict[str, float] = Field(default_factory=dict, description="What participant would have earned under other distributions")
    alternative_earnings_same_class: Dict[str, float] = Field(default_factory=dict, description="What participant would have earned under each principle with SAME class assignment")


class Phase1Results(BaseModel):
    """Complete results for a participant's Phase 1."""
    participant_name: str
    initial_ranking: PrincipleRanking
    post_explanation_ranking: PrincipleRanking
    application_results: List[ApplicationResult]
    final_ranking: PrincipleRanking
    total_earnings: float
    final_memory_state: str = Field(..., description="Complete memory from Phase 1 for Phase 2 continuity")


class ParticipantContext(BaseModel):
    """Context object passed to agents containing current state."""
    name: str
    role_description: str
    bank_balance: float
    memory: str = Field(..., description="Agent-managed memory continuous across Phase 1 and Phase 2")
    round_number: int
    phase: ExperimentPhase
    memory_character_limit: int = 50000
    allow_vote_tool: bool = Field(default=True, description="Controls availability of propose_vote tool during voting sub-phases")
    interaction_type: Optional[str] = Field(default=None, description="Type of interaction: 'public_statement', 'internal_reasoning', 'memory_update', 'confirmation', 'ballot'")
    internal_reasoning: str = Field(default="", description="Most recent internal reasoning generated by agent, available for context display")
    stage: ExperimentStage | None = Field(default=None, description="Current sub-stage within the experiment phase")
    formatted_context_header: Optional[str] = Field(
        default=None,
        description="Pre-formatted Phase 2 discussion context header with round info and history. "
                    "Set by Phase2Manager before Runner calls to make data flow explicit. "
                    "Required for Phase 2 discussion stage (ParticipantAgent will raise error if None)."
    )
    first_memory_update: bool = Field(default=True, description="Track if this is the first memory update to show experiment explanation only once")


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
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    valid_participants: Optional[List[str]] = None
    # CONSENSUS CLEANUP: Removed current_round_preferences - preference consensus disabled

    # Complex voting fields
    active_vote_in_progress: bool = False
    last_vote_result: Optional[VoteResult] = None
    vote_triggered: bool = False  # Track if voting has been initiated (prevents reminder messages)

    @staticmethod
    def _strip_markdown_emphasis(text: str) -> str:
        """Remove Markdown bold/italic markers for clean history storage."""
        if not text:
            return text
        import re
        pattern = re.compile(r"(\*\*|__)(.+?)(\1)", flags=re.DOTALL)
        return pattern.sub(r"\2", text)

    def add_statement(self, participant_name: str, statement: str, language_manager=None):
        """Add statement to public history with participant validation and round number formatting."""
        # Validate participant if valid_participants is set
        if self.valid_participants and participant_name not in self.valid_participants:
            raise ValueError(
                f"Invalid participant '{participant_name}' not in configured agents: {self.valid_participants}. "
                f"Experiment ID: {self.experiment_id}"
            )

        # Strip markdown emphasis from statement before storing
        clean_statement = self._strip_markdown_emphasis(statement)

        statement_obj = DiscussionStatement(
            participant_name=participant_name,
            statement=clean_statement,
            round_number=self.round_number
        )
        self.statements.append(statement_obj)

        # Format statement with round number if language manager is available
        if language_manager:
            try:
                formatted_statement = language_manager.get(
                    "discussion_format.round_speaker_format",
                    round_number=self.round_number,
                    speaker_name=participant_name,
                    statement=clean_statement
                )
                self.public_history += f"\n{formatted_statement}"
            except Exception:
                # Fallback to simple format if translation key is missing or other error
                self.public_history += f"\n{participant_name}: {clean_statement}"
        else:
            # Fallback to simple format when no language manager provided
            self.public_history += f"\n{participant_name}: {clean_statement}"
    
    def add_vote_result(self, vote_result: VoteResult, language_manager=None):
        """Add vote result to public history."""
        self.vote_history.append(vote_result)
        
        if language_manager:
            consensus_status = "Yes" if vote_result.consensus_reached else "No"
            vote_summary = language_manager.get("system_messages.voting.result_summary", consensus=consensus_status)
            if vote_result.consensus_reached and vote_result.agreed_principle:
                vote_summary += language_manager.get("system_messages.voting.agreed_principle", principle=vote_result.agreed_principle.principle.value)
            result_tag = language_manager.get("system_messages.voting.result_tag")
        else:
            # Fallback to English
            vote_summary = f"Vote conducted - Consensus: {'Yes' if vote_result.consensus_reached else 'No'}"
            if vote_result.consensus_reached and vote_result.agreed_principle:
                vote_summary += f" (Agreed on: {vote_result.agreed_principle.principle.value})"
            result_tag = "[VOTING RESULT]"
            
        self.public_history += f"\n{result_tag} {vote_summary}"


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
    alternative_earnings_by_agent: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Counterfactual earnings by participant under each principle")
    final_rankings: Dict[str, PrincipleRanking] = Field(default_factory=dict, description="Final principle rankings by each participant")


class ExperimentResults(BaseModel):
    """Complete results for the entire experiment."""
    experiment_id: str
    timestamp: datetime
    total_runtime: float = Field(..., description="Total runtime in seconds")
    phase1_results: List[Phase1Results]
    phase2_results: Phase2Results
    
    # Reproducibility metadata
    seed_used: Optional[int] = Field(None, description="Random seed used for this experiment")
    seed_source: Optional[str] = Field(None, description="Source of seed: 'explicit' or 'generated'")
    
