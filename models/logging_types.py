"""
Agent-centric logging data structures for the Frohlich Experiment.
These models capture the complete agent journey through both phases.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from .principle_types import PrincipleChoice, PrincipleRanking, JusticePrinciple, CertaintyLevel


class PrincipleRankingResult(BaseModel):
    """Clean structure for principle ranking results."""
    rankings: List[Dict[str, Any]] = Field(..., description="List of principle rankings")
    certainty: str = Field(..., description="Certainty level for the ranking")
    
    @classmethod
    def from_principle_ranking(cls, ranking: PrincipleRanking) -> 'PrincipleRankingResult':
        """Convert PrincipleRanking to clean logging format."""
        rankings_list = []
        for ranked_principle in ranking.rankings:
            rankings_list.append({
                "principle": ranked_principle.principle.value,
                "rank": ranked_principle.rank
            })
        
        return cls(
            rankings=rankings_list,
            certainty=ranking.certainty.value
        )


class BaseRoundLog(BaseModel):
    """Base class for all round-level logging with memory state tracking."""
    memory_coming_in_this_round: str
    bank_balance: float


class InitialRankingLog(BaseRoundLog):
    """Captures initial principle ranking in Phase 1."""
    ranking_result: PrincipleRankingResult


class DetailedExplanationLog(BaseRoundLog):
    """Captures detailed explanation step in Phase 1."""
    response_to_demonstration: str


class PostExplanationRankingLog(BaseRoundLog):
    """Captures ranking after detailed explanation in Phase 1."""
    ranking_result: PrincipleRankingResult


class DemonstrationRoundLog(BaseRoundLog):
    """Captures each demonstration round in Phase 1."""
    number_demonstration_round: int
    choice_principal: str
    class_put_in: str
    payoff_received: float
    payoff_if_other_principles: str
    bank_balance_after_round: float


class FinalRankingLog(BaseRoundLog):
    """Captures final ranking after all demonstrations in Phase 1."""
    ranking_result: PrincipleRankingResult


class DiscussionRoundLog(BaseRoundLog):
    """Captures each discussion round in Phase 2."""
    number_discussion_round: int
    speaking_order: int
    internal_reasoning: str
    public_message: str
    initiate_vote: str
    favored_principle: str


class PostDiscussionLog(BaseRoundLog):
    """Captures post-group discussion state in Phase 2."""
    class_put_in: str
    payoff_received: float
    final_ranking: PrincipleRankingResult
    final_vote: Optional[str] = Field(None, description="Final vote cast by this agent")
    vote_timestamp: Optional[str] = Field(None, description="Timestamp when vote was cast")


class VoteRoundDetails(BaseModel):
    """Details of a single voting round."""
    round_number: int = Field(..., description="Phase 2 round when vote was triggered")
    vote_type: str = Field(..., description="Type of vote: 'formal_vote' only (preference consensus removed)")
    trigger_participant: Optional[str] = Field(None, description="Agent who triggered the vote")
    trigger_statement: Optional[str] = Field(None, description="Statement that triggered the vote")
    
    # Vote participation details
    participant_votes: List[Dict[str, Any]] = Field(default_factory=list, description="Individual vote details")
    # Each participant_vote contains:
    # - participant_name: str
    # - raw_response: str (exact agent output)
    # - assessed_choice: str (system's interpretation)
    # - constraint_amount: Optional[float]
    # - vote_timestamp: str
    # - parsing_success: bool
    
    # Vote outcome
    consensus_reached: bool = Field(False, description="Whether consensus was achieved")
    agreed_principle: Optional[str] = Field(None, description="Principle if consensus reached")
    agreed_constraint: Optional[float] = Field(None, description="Constraint amount if applicable")
    vote_counts: Dict[str, int] = Field(default_factory=dict, description="Vote distribution")
    
    # Process details
    confirmation_phase_occurred: bool = Field(False, description="Whether confirmation phase occurred")
    confirmation_results: Optional[List[Dict[str, Any]]] = Field(None, description="Confirmation responses if complex mode")
    warnings: List[str] = Field(default_factory=list, description="System warnings during vote processing")
    
    # Two-stage voting details
    two_stage_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Two-stage voting success details by participant")
    two_stage_retries: List[Dict[str, Any]] = Field(default_factory=list, description="Two-stage voting retry attempts")  
    two_stage_failures: List[Dict[str, Any]] = Field(default_factory=list, description="Two-stage voting failure details")


class VotingHistoryLog(BaseModel):
    """Complete voting history for the experiment."""
    voting_system: str = Field(default="formal_voting", description="Voting system used (formal voting with prompts)")
    total_vote_attempts: int = Field(0, description="Total number of vote attempts")
    successful_votes: int = Field(0, description="Number of votes that reached consensus")
    
    vote_rounds: List[VoteRoundDetails] = Field(default_factory=list, description="Details of each vote round")
    
    # NEW: Round-level vote initiation tracking
    vote_initiation_requests: Dict[int, Dict[str, str]] = Field(default_factory=dict, description="Vote initiation requests per round: round_number -> {agent_name: Yes/No}")
    
    # NEW: Vote confirmation attempts tracking
    vote_confirmation_attempts: List[Dict[str, Any]] = Field(default_factory=list, description="Vote confirmation attempts with initiator and responses")
    # Each confirmation attempt contains:
    # - round_number: int
    # - initiator: str
    # - confirmation_responses: Dict[str, str] (agent_name -> Yes/No)
    # - confirmation_succeeded: bool
    
    # Summary statistics
    vote_statistics: Dict[str, Any] = Field(default_factory=dict, description="Voting statistics")
    # Contains:
    # - preference_detections_per_round: Dict[int, int] (REMOVED - preference consensus disabled)
    # - failed_parsing_attempts: int
    # - fallback_statements_during_votes: int
    # - average_consensus_round: Optional[float]


class AgentPhase1Logging(BaseModel):
    """Complete Phase 1 logging for a single agent."""
    initial_ranking: InitialRankingLog
    detailed_explanation: DetailedExplanationLog
    ranking_2: PostExplanationRankingLog
    demonstrations: List[DemonstrationRoundLog]
    ranking_3: FinalRankingLog


class AgentPhase2Logging(BaseModel):
    """Complete Phase 2 logging for a single agent."""
    rounds: List[DiscussionRoundLog]
    post_group_discussion: PostDiscussionLog


class AgentExperimentLog(BaseModel):
    """Complete experiment logging for a single agent."""
    name: str
    model: str
    temperature: float
    personality: str
    reasoning_enabled: bool
    phase_1: AgentPhase1Logging
    phase_2: AgentPhase2Logging

    def to_target_format(self) -> Dict[str, Any]:
        """Convert to target_state.json format."""
        return {
            "name": self.name,
            "model": self.model,
            "temperature": self.temperature,
            "personality": self.personality,
            "reasoning_enabled": self.reasoning_enabled,
            "phase_1": {
                "initial_ranking": {
                    "ranking_result": self.phase_1.initial_ranking.ranking_result.model_dump(),
                    "memory_coming_in_this_round": self.phase_1.initial_ranking.memory_coming_in_this_round,
                    "bank_balance": self.phase_1.initial_ranking.bank_balance
                },
                "detailed_explanation": {
                    "response_to_demonstration": self.phase_1.detailed_explanation.response_to_demonstration,
                    "memory_coming_in_this_round": self.phase_1.detailed_explanation.memory_coming_in_this_round
                },
                "ranking_2": {
                    "ranking_result": self.phase_1.ranking_2.ranking_result.model_dump(),
                    "memory_coming_in_this_round": self.phase_1.ranking_2.memory_coming_in_this_round,
                    "bank_balance": self.phase_1.ranking_2.bank_balance
                },
                "demonstrations": [
                    {
                        "number_demonstration_round": demo.number_demonstration_round,
                        "choice_principal": demo.choice_principal,
                        "class_put_in": demo.class_put_in,
                        "payoff_received": demo.payoff_received,
                        "payoff_if_other_principles": demo.payoff_if_other_principles,
                        "memory_coming_in_this_round": demo.memory_coming_in_this_round,
                        "bank_balance_after_round": demo.bank_balance_after_round
                    }
                    for demo in self.phase_1.demonstrations
                ],
                "ranking_3": {
                    "ranking_result": self.phase_1.ranking_3.ranking_result.model_dump(),
                    "memory_coming_in_this_round": self.phase_1.ranking_3.memory_coming_in_this_round,
                    "bank_balance": self.phase_1.ranking_3.bank_balance
                }
            },
            "phase_2": {
                "rounds": [
                    {
                        "number_discussion_round": round_log.number_discussion_round,
                        "speaking_order": round_log.speaking_order,
                        "bank_balance": round_log.bank_balance,
                        "memory_coming_in_this_round": round_log.memory_coming_in_this_round,
                        "internal_reasoning": round_log.internal_reasoning,
                        "public_message": round_log.public_message,
                        "initiate_vote": round_log.initiate_vote,
                        "favored_principle": round_log.favored_principle
                    }
                    for round_log in self.phase_2.rounds
                ],
                "post_group_discussion": {
                    "class_put_in": self.phase_2.post_group_discussion.class_put_in,
                    "payoff_received": self.phase_2.post_group_discussion.payoff_received,
                    "final_ranking": self.phase_2.post_group_discussion.final_ranking.model_dump(),
                    "final_vote": self.phase_2.post_group_discussion.final_vote,
                    "vote_timestamp": self.phase_2.post_group_discussion.vote_timestamp,
                    "memory_coming_in_this_round": self.phase_2.post_group_discussion.memory_coming_in_this_round,
                    "bank_balance": self.phase_2.post_group_discussion.bank_balance
                }
            }
        }


class GeneralExperimentInfo(BaseModel):
    """General experiment information for target state."""
    consensus_reached: bool
    consensus_principle: Optional[str] = None
    max_rounds_phase_2: int
    rounds_conducted_phase_2: int
    public_conversation_phase_2: str
    config_file_used: str
    seed_randomness: Optional[int] = None
    income_class_probabilities: Optional[Dict[str, float]] = None
    original_values_mode_enabled: Optional[bool] = None
    manipulator_target_info: Optional[Dict[str, Any]] = None
    # Backward compatibility fields
    seed_used: Optional[int] = None
    seed_source: Optional[str] = None
    
    def __init__(self, **data):
        """Initialize with backward compatibility support."""
        # Handle seed_randomness backward compatibility
        if 'seed_used' in data and 'seed_randomness' not in data:
            data['seed_randomness'] = data['seed_used']
        elif 'seed_randomness' in data and 'seed_used' not in data:
            data['seed_used'] = data['seed_randomness']
        
        super().__init__(**data)


class TargetStateStructure(BaseModel):
    """Complete target state structure with voting history."""
    general_information: GeneralExperimentInfo
    agents: List[Dict[str, Any]]  # Agent logs in target format
    voting_history: Optional[VotingHistoryLog] = None  # NEW: Third category

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "general_information": {
                "consensus_reached": self.general_information.consensus_reached,
                "consensus_principle": self.general_information.consensus_principle,
                "max_rounds_phase_2": self.general_information.max_rounds_phase_2,
                "rounds_conducted_phase_2": self.general_information.rounds_conducted_phase_2,
                "public_conversation_phase_2": self.general_information.public_conversation_phase_2,
                "config_file_used": self.general_information.config_file_used,
                "seed_randomness": self.general_information.seed_randomness,
                "income_class_probabilities": self.general_information.income_class_probabilities,
                "original_values_mode_enabled": self.general_information.original_values_mode_enabled,
                "manipulator_target_info": self.general_information.manipulator_target_info
            },
            "agents": self.agents
        }
        
        # Add voting history if present
        if self.voting_history:
            result["voting_history"] = {
                "voting_system": self.voting_history.voting_system,
                "voting_detection_mode": "complex",  # Temporary compatibility shim
                "total_vote_attempts": self.voting_history.total_vote_attempts,
                "successful_votes": self.voting_history.successful_votes,
                "vote_rounds": [
                    {
                        "round_number": vote_round.round_number,
                        "vote_type": vote_round.vote_type,
                        "trigger_participant": vote_round.trigger_participant,
                        "trigger_statement": vote_round.trigger_statement,
                        "participant_votes": vote_round.participant_votes,
                        "consensus_reached": vote_round.consensus_reached,
                        "agreed_principle": vote_round.agreed_principle,
                        "agreed_constraint": vote_round.agreed_constraint,
                        "vote_counts": vote_round.vote_counts,
                        "confirmation_phase_occurred": vote_round.confirmation_phase_occurred,
                        "confirmation_results": vote_round.confirmation_results,
                        "warnings": vote_round.warnings
                    }
                    for vote_round in self.voting_history.vote_rounds
                ],
                "vote_initiation_requests": self.voting_history.vote_initiation_requests,
                "vote_confirmation_attempts": self.voting_history.vote_confirmation_attempts,
                "vote_statistics": self.voting_history.vote_statistics
            }
        
        return result