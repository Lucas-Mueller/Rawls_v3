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
    PrincipleRankingResult, VotingHistoryLog, VoteRoundDetails
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
        self.seed_used: Optional[int] = None
        self.seed_source: Optional[str] = None
        # NEW: Voting history tracking
        self.voting_history: Optional[VotingHistoryLog] = None
        self.current_vote_round: Optional[VoteRoundDetails] = None
        
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
    
    def set_seed_info(self, seed_used: Optional[int], seed_source: Optional[str]):
        """Set seed information for the experiment."""
        self.seed_used = seed_used
        self.seed_source = seed_source
    
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
        bank_balance: float,
        final_vote: Optional[str] = None,
        vote_timestamp: Optional[str] = None
    ):
        """Log post-discussion state in Phase 2."""
        if agent_name in self.agent_logs:
            ranking_result = PrincipleRankingResult.from_principle_ranking(ranking)
            self.agent_logs[agent_name].phase_2.post_group_discussion = PostDiscussionLog(
                class_put_in=class_assigned,
                payoff_received=payoff,
                final_ranking=ranking_result,
                memory_coming_in_this_round=memory_state,
                bank_balance=bank_balance,
                final_vote=final_vote,
                vote_timestamp=vote_timestamp
            )
    
    def update_agent_votes(
        self,
        agent_votes: Dict[str, str],
        vote_timestamps: Dict[str, Optional[str]]
    ):
        """Update final vote information for all agents."""
        for agent_name in agent_votes:
            if agent_name in self.agent_logs and self.agent_logs[agent_name].phase_2.post_group_discussion:
                self.agent_logs[agent_name].phase_2.post_group_discussion.final_vote = agent_votes[agent_name]
                self.agent_logs[agent_name].phase_2.post_group_discussion.vote_timestamp = vote_timestamps[agent_name]
    
    def set_general_information(
        self,
        consensus_reached: bool,
        consensus_principle: Optional[str],
        max_rounds_phase_2: int,
        rounds_conducted_phase_2: int,
        public_conversation: str,
        config_file: str,
        income_class_probabilities: Optional[Dict[str, float]] = None,
        original_values_mode_enabled: Optional[bool] = None
    ):
        """Set general experiment information."""
        self.general_info = GeneralExperimentInfo(
            consensus_reached=consensus_reached,
            consensus_principle=consensus_principle,
            max_rounds_phase_2=max_rounds_phase_2,
            rounds_conducted_phase_2=rounds_conducted_phase_2,
            public_conversation_phase_2=public_conversation,
            config_file_used=config_file,
            seed_randomness=None,  # Will be set later via set_seed_info
            income_class_probabilities=income_class_probabilities,
            original_values_mode_enabled=original_values_mode_enabled
        )
    
    def initialize_voting_history(self, voting_detection_mode: str):
        """Initialize voting history tracking."""
        self.voting_history = VotingHistoryLog(
            voting_detection_mode=voting_detection_mode,
            total_vote_attempts=0,
            successful_votes=0
        )
    
    def start_vote_round(
        self, 
        round_number: int, 
        vote_type: str,
        trigger_participant: Optional[str] = None,
        trigger_statement: Optional[str] = None
    ):
        """Start tracking a new vote round."""
        if not self.voting_history:
            raise ValueError("Voting history not initialized")
        
        self.current_vote_round = VoteRoundDetails(
            round_number=round_number,
            vote_type=vote_type,
            trigger_participant=trigger_participant,
            trigger_statement=trigger_statement,
            participant_votes=[],
            consensus_reached=False
        )
        self.voting_history.total_vote_attempts += 1
    
    def log_vote_response(
        self,
        participant_name: str,
        raw_response: str,
        assessed_choice: str,
        constraint_amount: Optional[float] = None,
        parsing_success: bool = True,
        vote_timestamp: Optional[str] = None
    ):
        """Log individual participant vote response."""
        if not self.current_vote_round:
            raise ValueError("No active vote round")
        
        vote_detail = {
            "participant_name": participant_name,
            "raw_response": raw_response,
            "assessed_choice": assessed_choice,
            "constraint_amount": constraint_amount,
            "vote_timestamp": vote_timestamp or datetime.now().isoformat(),
            "parsing_success": parsing_success
        }
        
        self.current_vote_round.participant_votes.append(vote_detail)
    
    def log_confirmation_phase(
        self,
        confirmation_results: List[Dict[str, Any]]
    ):
        """Log confirmation phase results."""
        if not self.current_vote_round:
            raise ValueError("No active vote round")
        
        self.current_vote_round.confirmation_phase_occurred = True
        self.current_vote_round.confirmation_results = confirmation_results
    
    def complete_vote_round(
        self,
        consensus_reached: bool,
        agreed_principle: Optional[str] = None,
        agreed_constraint: Optional[float] = None,
        vote_counts: Optional[Dict[str, int]] = None,
        warnings: Optional[List[str]] = None
    ):
        """Complete and store the current vote round."""
        if not self.current_vote_round or not self.voting_history:
            raise ValueError("No active vote round or voting history")
        
        self.current_vote_round.consensus_reached = consensus_reached
        self.current_vote_round.agreed_principle = agreed_principle
        self.current_vote_round.agreed_constraint = agreed_constraint
        self.current_vote_round.vote_counts = vote_counts or {}
        self.current_vote_round.warnings = warnings or []
        
        if consensus_reached:
            self.voting_history.successful_votes += 1
        
        self.voting_history.vote_rounds.append(self.current_vote_round)
        self.current_vote_round = None
    
    def log_two_stage_voting_success(
        self,
        participant_name: str,
        stage: str,
        response: str,
        value: int,
        attempt: int
    ):
        """Log successful completion of a two-stage voting stage."""
        if not self.current_vote_round:
            # Create a new vote round if one doesn't exist
            self.start_vote_round(0, "two_stage_voting", participant_name)
        
        # Store in vote round details (fields now defined in model)
        if participant_name not in self.current_vote_round.two_stage_details:
            self.current_vote_round.two_stage_details[participant_name] = {}
        
        self.current_vote_round.two_stage_details[participant_name][stage] = {
            "success": True,
            "response": response,
            "value": value,
            "attempts_used": attempt,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_two_stage_voting_retry(
        self,
        participant_name: str,
        stage: str,
        response: str,
        error_type: str,
        attempt: int
    ):
        """Log retry attempt for a two-stage voting stage."""
        if not self.current_vote_round:
            self.start_vote_round(0, "two_stage_voting", participant_name)
        
        # Store retry information (field now defined in model)
        
        retry_info = {
            "participant": participant_name,
            "stage": stage,
            "response": response,
            "error_type": error_type,
            "attempt": attempt,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_vote_round.two_stage_retries.append(retry_info)
    
    def log_two_stage_voting_failure(
        self,
        participant_name: str,
        stage: str,
        max_attempts: int
    ):
        """Log failure of a two-stage voting stage after all retries."""
        if not self.current_vote_round:
            self.start_vote_round(0, "two_stage_voting", participant_name)
        
        # Store failure information (field now defined in model)
        
        failure_info = {
            "participant": participant_name,
            "stage": stage,
            "max_attempts": max_attempts,
            "timestamp": datetime.now().isoformat()
        }
        
        self.current_vote_round.two_stage_failures.append(failure_info)
    
    def generate_target_state(self) -> TargetStateStructure:
        """Generate the complete target state structure."""
        if not self.general_info:
            raise ValueError("General experiment information not set")
        
        agent_data = [
            agent_log.to_target_format() 
            for agent_log in self.agent_logs.values()
        ]
        
        # Create a copy of general_info with seed information added
        general_info_dict = self.general_info.model_dump()
        general_info_dict['seed_randomness'] = self.seed_used
        general_info_dict['seed_used'] = self.seed_used  # Backward compatibility
        general_info_dict['seed_source'] = self.seed_source
        
        general_info_with_seed = GeneralExperimentInfo(**general_info_dict)
        
        return TargetStateStructure(
            general_information=general_info_with_seed,
            agents=agent_data,
            voting_history=self.voting_history
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
        elif hasattr(obj, 'model_dump'):  # Pydantic models
            return obj.model_dump()
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
    async def extract_vote_intention(response_text: str, utility_agent=None) -> str:
        """Extract vote initiation intention from response using enhanced detection."""
        if utility_agent is not None:
            # Use the enhanced vote detection from utility agent for consistency
            try:
                vote_result = await utility_agent.detect_vote_intention_enhanced(response_text)
                return "Yes" if vote_result is not None else "No"
            except Exception as e:
                # Fallback to basic detection if utility agent fails
                import logging
                logging.getLogger(__name__).warning(f"Enhanced vote detection failed, using fallback: {e}")
        
        # Fallback: Basic pattern matching (preserved for backward compatibility)
        response_lower = response_text.lower()
        vote_positive = [
            "i propose we vote",
            "let's vote",
            "lets vote",
            "vote now",
            "call for a vote",
            "time to vote",
            "we should vote",
            "proceed with a vote",
        ]
        vote_negative_context = [
            "should we vote?",
            "no constraints",  # domain phrase, not a refusal
        ]
        if any(p in response_lower for p in vote_positive) and not any(n in response_lower for n in vote_negative_context):
            return "Yes"
        return "No"
