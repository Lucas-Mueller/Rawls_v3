"""
Agent-centric logging system for the Frohlich Experiment.
Replaces the experiment-centric logging with detailed agent journey tracking.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from models.logging_types import (
    AgentExperimentLog, AgentPhase1Logging, AgentPhase2Logging,
    InitialRankingLog, DetailedExplanationLog, PostExplanationRankingLog,
    DemonstrationRoundLog, FinalRankingLog, DiscussionRoundLog,
    PostDiscussionLog, GeneralExperimentInfo, TargetStateStructure,
    PrincipleRankingResult
)
from models.principle_types import PrincipleRanking
from config import ExperimentConfiguration

# Use TYPE_CHECKING import to avoid circular dependency
if TYPE_CHECKING:
    from experiment_agents import ParticipantAgent


class AgentCentricLogger:
    """
    Agent-centric logging system that captures complete agent journeys
    through both phases of the experiment with granular detail.
    """
    
    def __init__(self):
        self.agent_logs: Dict[str, AgentExperimentLog] = {}
        self.general_info: Optional[GeneralExperimentInfo] = None
        self.experiment_start_time: Optional[datetime] = None
        
    def initialize_experiment(
        self, 
        participants: List["ParticipantAgent"], 
        config: ExperimentConfiguration
    ):
        """Initialize agent logs at experiment start."""
        self.experiment_start_time = datetime.now()
        
        for i, participant in enumerate(participants):
            agent_config = config.agents[i]
            
            # Create placeholder structures that will be filled during execution
            self.agent_logs[participant.name] = AgentExperimentLog(
                name=participant.name,
                model=agent_config.model,
                temperature=agent_config.temperature,
                personality=agent_config.personality,
                reasoning_enabled=agent_config.reasoning_enabled,
                phase_1=AgentPhase1Logging(
                    initial_ranking=InitialRankingLog(
                        ranking_result=PrincipleRankingResult(rankings=[], certainty=""),
                        memory_coming_in_this_round="",
                        bank_balance=0.0
                    ),
                    detailed_explanation=DetailedExplanationLog(
                        response_to_demonstration="",
                        memory_coming_in_this_round="",
                        bank_balance=0.0
                    ),
                    ranking_2=PostExplanationRankingLog(
                        ranking_result=PrincipleRankingResult(rankings=[], certainty=""),
                        memory_coming_in_this_round="",
                        bank_balance=0.0
                    ),
                    demonstrations=[],
                    ranking_3=FinalRankingLog(
                        ranking_result=PrincipleRankingResult(rankings=[], certainty=""),
                        memory_coming_in_this_round="",
                        bank_balance=0.0
                    )
                ),
                phase_2=AgentPhase2Logging(
                    rounds=[],
                    post_group_discussion=PostDiscussionLog(
                        class_put_in="",
                        payoff_received=0.0,
                        final_ranking=PrincipleRankingResult(rankings=[], certainty=""),
                        memory_coming_in_this_round="",
                        bank_balance=0.0
                    )
                )
            )
    
    def log_initial_ranking(
        self, 
        agent_name: str, 
        ranking: PrincipleRanking,
        memory_state: str,
        bank_balance: float
    ):
        """Log initial ranking in Phase 1."""
        if agent_name in self.agent_logs:
            ranking_result = PrincipleRankingResult.from_principle_ranking(ranking)
            self.agent_logs[agent_name].phase_1.initial_ranking = InitialRankingLog(
                ranking_result=ranking_result,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance
            )
    
    def log_detailed_explanation(
        self,
        agent_name: str,
        response: str,
        memory_state: str,
        bank_balance: float
    ):
        """Log detailed explanation step in Phase 1."""
        if agent_name in self.agent_logs:
            self.agent_logs[agent_name].phase_1.detailed_explanation = DetailedExplanationLog(
                response_to_demonstration=response,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance
            )
    
    def log_post_explanation_ranking(
        self,
        agent_name: str,
        ranking: PrincipleRanking,
        memory_state: str,
        bank_balance: float
    ):
        """Log ranking after detailed explanation in Phase 1."""
        if agent_name in self.agent_logs:
            ranking_result = PrincipleRankingResult.from_principle_ranking(ranking)
            self.agent_logs[agent_name].phase_1.ranking_2 = PostExplanationRankingLog(
                ranking_result=ranking_result,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance
            )
    
    def log_demonstration_round(
        self,
        agent_name: str,
        round_number: int,
        choice_principal: str,
        class_assigned: str,
        payoff: float,
        alternative_payoffs: str,
        memory_state: str,
        bank_balance_before: float,
        bank_balance_after: float
    ):
        """Log a demonstration round in Phase 1."""
        if agent_name in self.agent_logs:
            demo_log = DemonstrationRoundLog(
                number_demonstration_round=round_number,
                choice_principal=choice_principal,
                class_put_in=class_assigned,
                payoff_received=payoff,
                payoff_if_other_principles=alternative_payoffs,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance_before,
                bank_balance_after_round=bank_balance_after
            )
            self.agent_logs[agent_name].phase_1.demonstrations.append(demo_log)
    
    def log_final_ranking(
        self,
        agent_name: str,
        ranking: PrincipleRanking,
        memory_state: str,
        bank_balance: float
    ):
        """Log final ranking in Phase 1."""
        if agent_name in self.agent_logs:
            ranking_result = PrincipleRankingResult.from_principle_ranking(ranking)
            self.agent_logs[agent_name].phase_1.ranking_3 = FinalRankingLog(
                ranking_result=ranking_result,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance
            )
    
    def log_discussion_round(
        self,
        agent_name: str,
        round_number: int,
        speaking_order: int,
        internal_reasoning: str,
        public_message: str,
        initiate_vote: str,
        favored_principle: str,
        memory_state: str,
        bank_balance: float
    ):
        """Log a discussion round in Phase 2."""
        if agent_name in self.agent_logs:
            discussion_log = DiscussionRoundLog(
                number_discussion_round=round_number,
                speaking_order=speaking_order,
                internal_reasoning=internal_reasoning,
                public_message=public_message,
                initiate_vote=initiate_vote,
                favored_principle=favored_principle,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance
            )
            self.agent_logs[agent_name].phase_2.rounds.append(discussion_log)
    
    def log_post_discussion(
        self,
        agent_name: str,
        class_assigned: str,
        payoff: float,
        ranking: PrincipleRanking,
        memory_state: str,
        bank_balance: float
    ):
        """Log post-discussion state in Phase 2."""
        if agent_name in self.agent_logs:
            ranking_result = PrincipleRankingResult.from_principle_ranking(ranking)
            self.agent_logs[agent_name].phase_2.post_group_discussion = PostDiscussionLog(
                class_put_in=class_assigned,
                payoff_received=payoff,
                final_ranking=ranking_result,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance
            )
    
    def set_general_information(
        self,
        consensus_reached: bool,
        consensus_principle: Optional[str],
        public_conversation: str,
        final_vote_results: Dict[str, str],
        config_file: str
    ):
        """Set general experiment information."""
        self.general_info = GeneralExperimentInfo(
            consensus_reached=consensus_reached,
            consensus_principle=consensus_principle,
            public_conversation_phase_2=public_conversation,
            final_vote_results=final_vote_results,
            config_file_used=config_file
        )
    
    def generate_target_state(self) -> TargetStateStructure:
        """Generate the complete target state structure."""
        if not self.general_info:
            raise ValueError("General experiment information not set")
        
        agent_data = [
            agent_log.to_target_format() 
            for agent_log in self.agent_logs.values()
        ]
        
        return TargetStateStructure(
            general_information=self.general_info,
            agents=agent_data
        )
    
    def save_to_file(self, output_path: str):
        """Save the complete agent-centric log to JSON file."""
        target_state = self.generate_target_state()
        
        # Ensure parent directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(target_state.to_dict(), f, indent=2, default=self._json_serializer)
    
    def get_agent_log(self, agent_name: str) -> Optional[AgentExperimentLog]:
        """Get the log for a specific agent."""
        return self.agent_logs.get(agent_name)
    
    def get_all_agent_names(self) -> List[str]:
        """Get names of all logged agents."""
        return list(self.agent_logs.keys())
    
    @staticmethod
    def _json_serializer(obj):
        """Handle datetime and other non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'dict'):  # Pydantic models
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class MemoryStateCapture:
    """Utility class for capturing memory states during experiment execution."""
    
    @staticmethod
    def capture_pre_round_state(memory: str, bank_balance: float) -> tuple[str, float]:
        """Capture memory state and bank balance coming into a round."""
        return memory, bank_balance
    
    @staticmethod
    def format_alternative_payoffs(alternative_earnings: Dict[str, float]) -> str:
        """Format alternative payoffs for logging."""
        if not alternative_earnings:
            return "No alternative payoffs calculated"
        
        payoff_lines = []
        for principle, earnings in alternative_earnings.items():
            payoff_lines.append(f"{principle}: ${earnings:.2f}")
        
        return "; ".join(payoff_lines)
    
    # Removed extract_confidence_from_response - no longer needed with structured data
    
    @staticmethod
    def extract_vote_intention(response_text: str) -> str:
        """Extract vote initiation intention from response."""
        response_lower = response_text.lower()
        
        if any(phrase in response_lower for phrase in ["call for vote", "vote now", "let's vote", "initiate vote"]):
            return "Yes"
        else:
            return "No"