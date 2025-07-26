"""
Main experiment manager orchestrating the complete Frohlich Experiment.
"""
import uuid
import time
import logging
from datetime import datetime
from typing import List
from agents import Agent, trace

from models import ExperimentResults, ParticipantContext
from config import ExperimentConfiguration
from experiment_agents import create_participant_agent, UtilityAgent, ParticipantAgent
from core import Phase1Manager, Phase2Manager
from utils.agent_centric_logger import AgentCentricLogger
from utils.error_handling import (
    ExperimentError, ExperimentLogicError, SystemError, AgentCommunicationError,
    ErrorSeverity, ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors, set_global_error_handler
)

logger = logging.getLogger(__name__)


class FrohlichExperimentManager:
    """Main manager for the complete two-phase Frohlich Experiment."""
    
    def __init__(self, config: ExperimentConfiguration):
        self.config = config
        self.experiment_id = str(uuid.uuid4())
        self.error_handler = get_global_error_handler()
        
        # Initialize error handler with custom logger
        experiment_logger = logging.getLogger(f"experiment.{self.experiment_id}")
        set_global_error_handler(type(self.error_handler)(experiment_logger))
        self.error_handler = get_global_error_handler()
        
        try:
            self.participants = self._create_participants()
            self.utility_agent = UtilityAgent()
            self.phase1_manager = Phase1Manager(self.participants, self.utility_agent)
            self.phase2_manager = Phase2Manager(self.participants, self.utility_agent)
            self.agent_logger = AgentCentricLogger()
        except Exception as e:
            raise ExperimentLogicError(
                f"Failed to initialize experiment manager: {str(e)}",
                ErrorSeverity.FATAL,
                {
                    "experiment_id": self.experiment_id,
                    "config_agents_count": len(config.agents),
                    "initialization_error": str(e)
                },
                cause=e
            )
        
    @handle_experiment_errors(
        category=ExperimentErrorCategory.EXPERIMENT_LOGIC_ERROR,
        severity=ErrorSeverity.FATAL,
        operation_name="run_complete_experiment"
    )
    async def run_complete_experiment(self) -> ExperimentResults:
        """Run complete two-phase experiment with tracing."""
        
        start_time = time.time()
        
        with trace(
            "Frohlich Experiment",
            trace_id=f"trace_{self.experiment_id}",
            group_id="frohlich_experiments",
            metadata={
                "experiment_type": "justice_principles",
                "num_participants": str(len(self.participants)),
                "phase2_rounds": str(self.config.phase2_rounds)
            }
        ) as experiment_trace:
            
            try:
                # Initialize agent-centric logging
                self.agent_logger.initialize_experiment(self.participants, self.config)
                
                # Phase 1: Individual familiarization (parallel)
                logger.info(f"Starting Phase 1 for experiment {self.experiment_id}")
                
                try:
                    phase1_results = await self.phase1_manager.run_phase1(self.config, self.agent_logger)
                except Exception as e:
                    raise ExperimentLogicError(
                        f"Phase 1 execution failed: {str(e)}",
                        ErrorSeverity.FATAL,
                        {
                            "experiment_id": self.experiment_id,
                            "phase": "phase_1",
                            "participants_count": len(self.participants),
                            "phase1_error": str(e)
                        },
                        cause=e
                    )
                
                logger.info(f"Phase 1 completed. {len(phase1_results)} participants finished.")
                for result in phase1_results:
                    logger.info(f"{result.participant_name}: ${result.total_earnings:.2f} earned")
                
                # Phase 2: Group discussion (sequential)  
                logger.info(f"Starting Phase 2 for experiment {self.experiment_id}")
                
                try:
                    phase2_results = await self.phase2_manager.run_phase2(
                        self.config, phase1_results, self.agent_logger
                    )
                except Exception as e:
                    raise ExperimentLogicError(
                        f"Phase 2 execution failed: {str(e)}",
                        ErrorSeverity.FATAL,
                        {
                            "experiment_id": self.experiment_id,
                            "phase": "phase_2",
                            "phase1_completed": True,
                            "phase2_error": str(e)
                        },
                        cause=e
                    )
                
                if phase2_results.discussion_result.consensus_reached:
                    logger.info(f"Phase 2 completed with consensus on {phase2_results.discussion_result.agreed_principle.principle.value}")
                else:
                    logger.info(f"Phase 2 completed without consensus after {phase2_results.discussion_result.final_round} rounds")
                
                # Set general experiment information for logging
                try:
                    self._set_general_logging_info(phase2_results)
                except Exception as e:
                    # Log the error but don't fail the experiment
                    logger.warning(f"Failed to set general logging info: {e}")
                
                # Compile final results
                results = ExperimentResults(
                    experiment_id=self.experiment_id,
                    timestamp=datetime.now(),
                    total_runtime=time.time() - start_time,
                    phase1_results=phase1_results,
                    phase2_results=phase2_results
                )
                
                logger.info(f"Experiment {self.experiment_id} completed successfully in {results.total_runtime:.2f} seconds")
                
                # Log error statistics
                error_stats = self.error_handler.get_error_statistics()
                if error_stats.get("total_errors", 0) > 0:
                    logger.info(f"Experiment completed with {error_stats['total_errors']} recoverable errors")
                
                return results
                
            except ExperimentError:
                raise  # Re-raise experiment errors as-is
            except Exception as e:
                # Wrap unexpected errors
                raise ExperimentLogicError(
                    f"Unexpected error during experiment execution: {str(e)}",
                    ErrorSeverity.FATAL,
                    {
                        "experiment_id": self.experiment_id,
                        "runtime_seconds": time.time() - start_time,
                        "unexpected_error": str(e)
                    },
                    cause=e
                )
            
    def _create_participants(self) -> List[ParticipantAgent]:
        """Create participant agents from configuration."""
        participants = []
        for agent_config in self.config.agents:
            participant = create_participant_agent(agent_config)
            participants.append(participant)
            logger.info(f"Created participant: {agent_config.name} ({agent_config.model}, temp={agent_config.temperature})")
        
        return participants
    
    def _set_general_logging_info(self, phase2_results):
        """Set general experiment information for agent-centric logging."""
        # Build public conversation from discussion history
        public_conversation = ""
        if phase2_results.discussion_result.discussion_history:
            for statement in phase2_results.discussion_result.discussion_history:
                public_conversation += f"{statement}\n"
        else:
            public_conversation = "No public discussion recorded."
        
        # Build final vote results
        final_vote_results = {}
        if phase2_results.discussion_result.vote_history:
            last_vote = phase2_results.discussion_result.vote_history[-1]
            # Since votes are anonymous (stored as list), we'll map them to participant names by order
            for i, participant in enumerate(self.participants):
                if i < len(last_vote.votes):
                    vote = last_vote.votes[i]
                    final_vote_results[participant.name] = vote.principle.value if vote else "No vote"
                else:
                    final_vote_results[participant.name] = "No vote"
        else:
            # If no votes, use participant names with "No vote"
            for participant in self.participants:
                final_vote_results[participant.name] = "No vote"
        
        # Set the general information
        self.agent_logger.set_general_information(
            consensus_reached=phase2_results.discussion_result.consensus_reached,
            consensus_principle=(
                phase2_results.discussion_result.agreed_principle.principle.value
                if phase2_results.discussion_result.agreed_principle
                else None
            ),
            public_conversation=public_conversation,
            final_vote_results=final_vote_results,
            config_file="default_config.yaml"  # Could be made configurable
        )
    
    def save_results(self, results: ExperimentResults, output_path: str):
        """Save experiment results to JSON file using agent-centric logging."""
        self.agent_logger.save_to_file(output_path)
        logger.info(f"Results saved to: {output_path}")
    
    def get_experiment_summary(self, results: ExperimentResults) -> str:
        """Generate a human-readable summary of the experiment."""
        summary = []
        summary.append(f"Frohlich Experiment Results (ID: {results.experiment_id})")
        summary.append(f"Completed in {results.total_runtime:.2f} seconds")
        summary.append("")
        
        # Phase 1 Summary
        summary.append("PHASE 1 RESULTS:")
        total_phase1_earnings = 0
        for result in results.phase1_results:
            total_phase1_earnings += result.total_earnings
            initial_top = result.initial_ranking.rankings[0].principle.value
            final_top = result.final_ranking.rankings[0].principle.value
            summary.append(f"  {result.participant_name}: ${result.total_earnings:.2f} "
                         f"(Initial pref: {initial_top}, Final pref: {final_top})")
        
        avg_phase1 = total_phase1_earnings / len(results.phase1_results)
        summary.append(f"  Average Phase 1 earnings: ${avg_phase1:.2f}")
        summary.append("")
        
        # Phase 2 Summary
        summary.append("PHASE 2 RESULTS:")
        if results.phase2_results.discussion_result.consensus_reached:
            agreed_principle = results.phase2_results.discussion_result.agreed_principle
            summary.append(f"  Consensus reached on: {agreed_principle.principle.value}")
            if agreed_principle.constraint_amount:
                summary.append(f"  Constraint amount: ${agreed_principle.constraint_amount}")
            summary.append(f"  Rounds to consensus: {results.phase2_results.discussion_result.final_round}")
        else:
            summary.append(f"  No consensus reached after {results.phase2_results.discussion_result.final_round} rounds")
            summary.append(f"  Payoffs randomly assigned")
        
        summary.append("  Phase 2 earnings:")
        total_phase2_earnings = 0
        for name, earnings in results.phase2_results.payoff_results.items():
            total_phase2_earnings += earnings
            summary.append(f"    {name}: ${earnings:.2f}")
        
        avg_phase2 = total_phase2_earnings / len(results.phase2_results.payoff_results)
        summary.append(f"  Average Phase 2 earnings: ${avg_phase2:.2f}")
        summary.append("")
        
        # Total Summary
        summary.append("TOTAL EARNINGS:")
        total_earnings = {}
        for result in results.phase1_results:
            total_earnings[result.participant_name] = result.total_earnings
        
        for name, phase2_earnings in results.phase2_results.payoff_results.items():
            total_earnings[name] += phase2_earnings
        
        for name, total in sorted(total_earnings.items(), key=lambda x: x[1], reverse=True):
            summary.append(f"  {name}: ${total:.2f}")
        
        winner = max(total_earnings.items(), key=lambda x: x[1])
        summary.append(f"\nHIGHEST EARNER: {winner[0]} with ${winner[1]:.2f}")
        
        return "\n".join(summary)