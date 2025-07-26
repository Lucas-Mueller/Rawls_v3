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
    final_ranking: str
    confidence_level: str


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
                    "principle_ranking_result": self.phase_1.initial_ranking.principle_ranking_result,
                    "confidence_level": self.phase_1.initial_ranking.confidence_level,
                    "memory_coming_in_this_round": self.phase_1.initial_ranking.memory_coming_in_this_round
                },
                "detailed_explanation": {
                    "response_to_demonstration": self.phase_1.detailed_explanation.response_to_demonstration,
                    "memory_coming_in_this_round": self.phase_1.detailed_explanation.memory_coming_in_this_round
                },
                "ranking_2": {
                    "principle_ranking_result": self.phase_1.ranking_2.principle_ranking_result,
                    "confidence_level": self.phase_1.ranking_2.confidence_level,
                    "memory_coming_in_this_round": self.phase_1.ranking_2.memory_coming_in_this_round
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
                    "principle_ranking_result": self.phase_1.ranking_3.principle_ranking_result,
                    "confidence_level": self.phase_1.ranking_3.confidence_level,
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
                    "final_ranking": self.phase_2.post_group_discussion.final_ranking,
                    "confidence_level": self.phase_2.post_group_discussion.confidence_level,
                    "memory_coming_in_this_round": self.phase_2.post_group_discussion.memory_coming_in_this_round
                }
            }
        }


class GeneralExperimentInfo(BaseModel):
    """General experiment information for target state."""
    consensus_reached: bool
    consensus_principle: Optional[str] = None
    public_conversation_phase_2: str
    final_vote_results: Dict[str, str]
    config_file_used: str


class TargetStateStructure(BaseModel):
    """Complete target state structure."""
    general_information: GeneralExperimentInfo
    agents: List[Dict[str, Any]]  # Agent logs in target format

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "general_information": {
                "consensus_reached": self.general_information.consensus_reached,
                "consensus_principle": self.general_information.consensus_principle,
                "public_conversation_phase_2": self.general_information.public_conversation_phase_2,
                "final_vote_results": self.general_information.final_vote_results,
                "config_file_used": self.general_information.config_file_used
            },
            "agents": self.agents
        }