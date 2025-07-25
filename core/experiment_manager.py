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
from experiment_agents import create_participant_agent, UtilityAgent
from core import Phase1Manager, Phase2Manager
from utils.logging_utils import ExperimentLogger

logger = logging.getLogger(__name__)


class FrohlichExperimentManager:
    """Main manager for the complete two-phase Frohlich Experiment."""
    
    def __init__(self, config: ExperimentConfiguration):
        self.config = config
        self.experiment_id = str(uuid.uuid4())
        self.participants = self._create_participants()
        self.utility_agent = UtilityAgent()
        self.phase1_manager = Phase1Manager(self.participants, self.utility_agent)
        self.phase2_manager = Phase2Manager(self.participants, self.utility_agent)
        
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
                # Phase 1: Individual familiarization (parallel)
                logger.info(f"Starting Phase 1 for experiment {self.experiment_id}")
                phase1_results = await self.phase1_manager.run_phase1(self.config)
                
                logger.info(f"Phase 1 completed. {len(phase1_results)} participants finished.")
                for result in phase1_results:
                    logger.info(f"{result.participant_name}: ${result.total_earnings:.2f} earned")
                
                # Phase 2: Group discussion (sequential)  
                logger.info(f"Starting Phase 2 for experiment {self.experiment_id}")
                phase2_results = await self.phase2_manager.run_phase2(
                    self.config, phase1_results
                )
                
                if phase2_results.discussion_result.consensus_reached:
                    logger.info(f"Phase 2 completed with consensus on {phase2_results.discussion_result.agreed_principle.principle.value}")
                else:
                    logger.info(f"Phase 2 completed without consensus after {phase2_results.discussion_result.final_round} rounds")
                
                # Compile final results
                results = ExperimentResults(
                    experiment_id=self.experiment_id,
                    timestamp=datetime.now(),
                    total_runtime=time.time() - start_time,
                    phase1_results=phase1_results,
                    phase2_results=phase2_results
                )
                
                logger.info(f"Experiment {self.experiment_id} completed successfully in {results.total_runtime:.2f} seconds")
                return results
                
            except Exception as e:
                logger.error(f"Experiment {self.experiment_id} failed: {e}")
                raise
            
    def _create_participants(self) -> List[Agent[ParticipantContext]]:
        """Create participant agents from configuration."""
        participants = []
        for agent_config in self.config.agents:
            participant = create_participant_agent(agent_config)
            participants.append(participant)
            logger.info(f"Created participant: {agent_config.name} ({agent_config.model}, temp={agent_config.temperature})")
        
        return participants
    
    def save_results(self, results: ExperimentResults, output_path: str):
        """Save experiment results to JSON file."""
        logger_instance = ExperimentLogger(output_path)
        logger_instance.log_experiment_results(results)
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