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
from experiment_agents.participant_agent import create_participant_agents_with_dynamic_temperature
from core import Phase1Manager, Phase2Manager
from utils.agent_centric_logger import AgentCentricLogger
from utils.error_handling import (
    ExperimentError, ExperimentLogicError, SystemError, AgentCommunicationError,
    ErrorSeverity, ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors, set_global_error_handler
)
from utils.language_manager import get_english_principle_name

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
        
        # Initialize managers will be done in async_init
        self.participants = None
        self.utility_agent = None
        self.phase1_manager = None
        self.phase2_manager = None
        self.agent_logger = AgentCentricLogger()
        self._initialization_complete = False
        
    async def async_init(self):
        """Asynchronously initialize the experiment manager."""
        if self._initialization_complete:
            return
            
        try:
            # Create participants with dynamic temperature detection
            self.participants = await self._create_participants()
            
            # Create utility agent (also with dynamic detection)
            self.utility_agent = UtilityAgent(self.config.utility_agent_model, self.config.utility_agent_temperature)
            await self.utility_agent.async_init()
            
            # Initialize phase managers
            self.phase1_manager = Phase1Manager(self.participants, self.utility_agent)
            self.phase2_manager = Phase2Manager(self.participants, self.utility_agent)
            
            self._initialization_complete = True
            logger.info(f"✅ Experiment manager initialized with {len(self.participants)} participants")
            
        except Exception as e:
            raise ExperimentLogicError(
                f"Failed to initialize experiment manager: {str(e)}",
                ErrorSeverity.FATAL,
                {
                    "experiment_id": self.experiment_id,
                    "config_agents_count": len(self.config.agents),
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
        
        # Ensure experiment manager is initialized
        await self.async_init()
        
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
                    # Use English principle name for system logging
                    english_principle_name = get_english_principle_name(phase2_results.discussion_result.agreed_principle.principle.value)
                    logger.info(f"Phase 2 completed with consensus on {english_principle_name}")
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
            
    async def _create_participants(self) -> List[ParticipantAgent]:
        """Create participant agents from configuration with dynamic temperature detection."""
        logger.info(f"Creating {len(self.config.agents)} participant agents...")
        
        # Use dynamic temperature detection for all participants
        participants = await create_participant_agents_with_dynamic_temperature(self.config.agents)
        
        return participants
    
    def _set_general_logging_info(self, phase2_results):
        """Set general experiment information for agent-centric logging."""
        # Build public conversation from discussion history
        if phase2_results.discussion_result.discussion_history:
            public_conversation = phase2_results.discussion_result.discussion_history
            # Ensure it ends with a newline for consistency
            if not public_conversation.endswith('\n'):
                public_conversation += '\n'
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
        
        # Extract probabilities from config for logging
        probabilities_dict = None
        if hasattr(self.config, 'income_class_probabilities') and self.config.income_class_probabilities:
            probabilities_dict = {
                "high": self.config.income_class_probabilities.high,
                "medium_high": self.config.income_class_probabilities.medium_high,
                "medium": self.config.income_class_probabilities.medium,
                "medium_low": self.config.income_class_probabilities.medium_low,
                "low": self.config.income_class_probabilities.low
            }

        # Extract original values mode info for logging
        original_values_enabled = None
        if hasattr(self.config, 'original_values_mode') and self.config.original_values_mode:
            original_values_enabled = self.config.original_values_mode.enabled

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
            config_file="default_config.yaml",  # Could be made configurable
            income_class_probabilities=probabilities_dict,
            original_values_mode_enabled=original_values_enabled
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