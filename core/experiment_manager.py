"""
Main experiment manager orchestrating the complete Frohlich Experiment.
"""
import uuid
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from agents import Agent, trace

from models import ExperimentResults, ParticipantContext
from config import ExperimentConfiguration
from config.models import TranscriptLoggingConfig
from experiment_agents import create_participant_agent, UtilityAgent, ParticipantAgent
from experiment_agents.participant_agent import create_participant_agents_with_dynamic_temperature
from core import Phase1Manager, Phase2Manager
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.logging import TranscriptLogger
from utils.error_handling import (
    ExperimentError, ExperimentLogicError, SystemError, AgentCommunicationError,
    ErrorSeverity, ExperimentErrorCategory, get_global_error_handler,
    handle_experiment_errors, set_global_error_handler
)
from utils.language_manager import get_english_principle_name

logger = logging.getLogger(__name__)


class FrohlichExperimentManager:
    """Main manager for the complete two-phase Frohlich Experiment.
    
    This class orchestrates the full experimental lifecycle, managing both
    phases of the Frohlich Experiment: individual agent familiarization 
    (Phase 1) and group discussion with consensus building (Phase 2).
    
    The manager handles:
    - Asynchronous agent initialization with multi-model provider support
    - Experiment tracing through OpenAI SDK integration
    - Comprehensive error handling and recovery mechanisms  
    - Agent-centric logging throughout the experiment
    - Results compilation and statistical reporting
    
    Args:
        config (ExperimentConfiguration): Complete experiment configuration 
            including agent definitions, phase parameters, and system settings.
            
    Attributes:
        config (ExperimentConfiguration): The experiment configuration
        experiment_id (str): Unique identifier for this experiment instance
        participants (List[ParticipantAgent]): List of participant agents
        utility_agent (UtilityAgent): Agent for response parsing and validation
        phase1_manager (Phase1Manager): Manager for individual familiarization
        phase2_manager (Phase2Manager): Manager for group discussion
        agent_logger (AgentCentricLogger): Centralized logging system
        
    Example:
        >>> config = ExperimentConfiguration.from_yaml("config.yaml")
        >>> manager = FrohlichExperimentManager(config)
        >>> results = await manager.run_complete_experiment()
        >>> print(f"Consensus: {results.phase2_results.consensus_reached}")
    """
    
    def __init__(self, config: ExperimentConfiguration, config_file_path: str = "default_config.yaml", language_manager = None):
        self.config = config
        self.config_file_path = config_file_path
        self.language_manager = language_manager
        self.experiment_id = str(uuid.uuid4())
        
        # Create experiment-scoped instances to prevent parallel experiment interference
        from utils.dynamic_model_capabilities import TemperatureCache
        from utils.error_handling import ExperimentErrorHandler
        from utils.seed_manager import SeedManager
        
        self.temperature_cache = TemperatureCache()
        self.seed_manager = SeedManager()
        
        # Create experiment-scoped error handler (no global state)
        experiment_logger = logging.getLogger(f"experiment.{self.experiment_id}")
        self.error_handler = ExperimentErrorHandler(experiment_logger)
        
        # Initialize managers will be done in async_init
        self.participants = None
        self.utility_agent = None
        self.phase1_manager = None
        self.phase2_manager = None
        self.agent_logger = AgentCentricLogger()
        transcript_config = config.transcript_logging or TranscriptLoggingConfig()
        self.transcript_logger = TranscriptLogger(
            config=transcript_config,
            experiment_id=self.experiment_id,
            config_path=config_file_path
        )
        self._last_transcript_path: Optional[str] = None
        self._initialization_complete = False
        
    async def async_init(self):
        """Asynchronously initialize the experiment manager.
        
        Performs async initialization of all experiment components including:
        - Participant agents with dynamic temperature configuration
        - Utility agent for response parsing and validation
        - Phase 1 manager for parallel individual processing
        - Phase 2 manager for sequential group discussion
        
        This method must be called before running the experiment. It handles
        model provider detection, agent initialization, and error recovery.
        
        Raises:
            ExperimentLogicError: If initialization fails after all retry attempts
            
        Note:
            This method is idempotent - multiple calls are safe and will not
            re-initialize already initialized components.
        """
        if self._initialization_complete:
            return
            
        try:
            # Create participants with dynamic temperature detection
            self.participants = await self._create_participants()
            
            # Create utility agent with experiment language (also with dynamic detection)
            self.utility_agent = UtilityAgent(
                self.config.utility_agent_model, 
                self.config.utility_agent_temperature,
                self.config.language,
                self.language_manager,
                self.temperature_cache
            )
            await self.utility_agent.async_init()
            
            # Initialize phase managers with experiment-scoped instances
            self.phase1_manager = Phase1Manager(
                self.participants,
                self.utility_agent,
                self.language_manager,
                self.error_handler,
                self.seed_manager,
                transcript_logger=self.transcript_logger
            )
            self.phase2_manager = Phase2Manager(
                self.participants,
                self.utility_agent,
                self.config,
                self.language_manager,
                self.error_handler,
                self.seed_manager,
                self.agent_logger,
                transcript_logger=self.transcript_logger
            )
            
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
    async def run_complete_experiment(self, process_logger=None) -> ExperimentResults:
        """Run complete two-phase experiment with tracing."""
        
        # Ensure experiment manager is initialized
        start_init_time = time.time()
        self._last_transcript_path = None
        
        # Initialize agent creation with ProcessFlowLogger
        if process_logger:
            agent_configs = [{'name': a.name, 'model': a.model} for a in self.config.agents]
            process_logger.initialize_agents(agent_configs)
        
        await self.async_init()
        
        # Log agent initialization completion
        if process_logger:
            init_time = time.time() - start_init_time
            for i, participant in enumerate(self.participants):
                config = self.config.agents[i]
                process_logger.agent_initialized(participant.name, config.model, 0.0)  # Individual timing not available
            process_logger.agents_ready(init_time)
        
        # ALWAYS initialize reproducibility for every experiment (instance-based)
        effective_seed = self.seed_manager.initialize_from_config(self.config)
        seed_source = "explicit" if self.config.seed else "generated"
        if process_logger:
            process_logger.log_technical(f"Experiment seed: {effective_seed} ({seed_source})")
        else:
            logger.info(f"Experiment seed: {effective_seed} ({seed_source})")
        
        # Create trace for the entire experiment
        trace_name = f"Frohlich Experiment - {self.experiment_id}"
        trace_metadata = {
            "experiment_id": str(self.experiment_id),
            "participant_count": str(len(self.participants)),
            "config_file": str(Path(self.config_file_path).name),
            "language": str(getattr(self.config, 'language', 'en')),
            "voting_system": "formal_voting",
            "phase2_max_rounds": str(getattr(self.config, 'phase2_rounds', 10)),
            "participant_names": ", ".join([p.name for p in self.participants]),
            "participant_models": ", ".join([p.config.model for p in self.participants])
        }
        
        start_time = time.time()
        
        with trace(trace_name, metadata=trace_metadata) as experiment_trace:
            if process_logger:
                process_logger.log_technical(f"Tracing experiment: {trace_name}")
                process_logger.log_technical(f"Trace ID: {experiment_trace.trace_id}")
            else:
                logger.info(f"🔍 Tracing experiment: {trace_name}")
                logger.info(f"🔗 Trace ID: {experiment_trace.trace_id}")
            
            # Store trace_id for later display
            self._trace_id = experiment_trace.trace_id
            
            try:
                # Initialize agent-centric logging
                self.agent_logger.initialize_experiment(self.participants, self.config)
                
                # Phase execution begins
                # Phase 1: Individual familiarization (parallel)
                if process_logger:
                    process_logger.start_phase1(len(self.participants))
                else:
                    logger.info(f"Starting Phase 1 for experiment {self.experiment_id}")
                
                phase1_start_time = time.time()
                try:
                    phase1_results = await self.phase1_manager.run_phase1(self.config, self.agent_logger, process_logger)
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
                
                phase1_duration = time.time() - phase1_start_time
                
                if process_logger:
                    results_summary = [{'name': r.participant_name, 'earnings': r.total_earnings} for r in phase1_results]
                    process_logger.phase1_completed(results_summary, phase1_duration)
                else:
                    logger.info(f"Phase 1 completed. {len(phase1_results)} participants finished.")
                    for result in phase1_results:
                        logger.info(f"{result.participant_name}: ${result.total_earnings:.2f} earned")
                
                # Phase 2: Group discussion (sequential)  
                if process_logger:
                    process_logger.start_phase2(self.config.phase2_rounds)
                else:
                    logger.info(f"Starting Phase 2 for experiment {self.experiment_id}")
                
                phase2_start_time = time.time()
                try:
                    phase2_results = await self.phase2_manager.run_phase2(
                        self.config, phase1_results, self.agent_logger, process_logger
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
                
                phase2_duration = time.time() - phase2_start_time
                
                if process_logger:
                    payoff_summary = phase2_results.payoff_results if hasattr(phase2_results, 'payoff_results') else None
                    process_logger.phase2_completed(
                        phase2_results.discussion_result.consensus_reached,
                        phase2_results.discussion_result.final_round,
                        phase2_duration,
                        payoff_summary
                    )
                else:
                    if phase2_results.discussion_result.consensus_reached:
                        # Use English principle name for system logging
                        english_principle_name = get_english_principle_name(phase2_results.discussion_result.agreed_principle.principle.value, self.language_manager)
                        logger.info(f"Phase 2 completed with consensus on {english_principle_name}")
                    else:
                        logger.info(f"Phase 2 completed without consensus after {phase2_results.discussion_result.final_round} rounds")
                
                # Set general experiment information for logging
                try:
                    self._set_general_logging_info(phase2_results)
                except Exception as e:
                    # Log the error but don't fail the experiment
                    if process_logger:
                        process_logger.log_warning(f"Failed to set general logging info: {e}")
                    else:
                        logger.warning(f"Failed to set general logging info: {e}")
                    # Set minimal fallback general information to prevent save failure
                    self._set_fallback_general_info(phase2_results)
                
                # Compile final results
                results = ExperimentResults(
                    experiment_id=self.experiment_id,
                    timestamp=datetime.now(),
                    total_runtime=time.time() - start_time,
                    phase1_results=phase1_results,
                    phase2_results=phase2_results,
                    seed_used=effective_seed,
                    seed_source=seed_source
                )
                
                if process_logger:
                    process_logger.log_technical(f"Experiment {self.experiment_id} completed successfully in {results.total_runtime:.2f} seconds")
                else:
                    logger.info(f"Experiment {self.experiment_id} completed successfully in {results.total_runtime:.2f} seconds")
                
                # Validate consensus against discussion content if applicable
                if hasattr(self, '_consensus_validation_info') and self._consensus_validation_info:
                    try:
                        consensus_valid, validation_warnings = await self.utility_agent.validate_consensus_against_discussion(
                            self._consensus_validation_info['discussion_content'], 
                            self._consensus_validation_info['consensus_principle']
                        )
                        
                        if not consensus_valid:
                            if process_logger:
                                process_logger.log_warning("AI assessment: Discussion content doesn't clearly support the voted consensus")
                                for warning in validation_warnings:
                                    process_logger.log_technical(f"Consensus validation: {warning}")
                            else:
                                logger.warning("AI assessment: Discussion content doesn't clearly support the voted consensus")
                                for warning in validation_warnings:
                                    logger.warning(f"Consensus validation: {warning}")
                        else:
                            if process_logger:
                                process_logger.log_technical("Consensus validation successful - discussion aligns with recorded consensus")
                            else:
                                logger.info("Consensus validation successful - discussion aligns with recorded consensus")
                            
                    except Exception as e:
                        if process_logger:
                            process_logger.log_warning(f"Consensus validation encountered error: {e}")
                        else:
                            logger.warning(f"Consensus validation encountered error: {e}")
                
                # Log error statistics
                error_stats = self.error_handler.get_error_statistics()
                total_errors = error_stats.get("total_errors", 0)
                if total_errors > 0:
                    if process_logger:
                        process_logger.log_technical(f"Experiment completed with {total_errors} recoverable errors")
                    else:
                        logger.info(f"Experiment completed with {total_errors} recoverable errors")

                if self.transcript_logger and self.transcript_logger.is_enabled():
                    try:
                        transcript_path = self.transcript_logger.save_transcript()
                        self._last_transcript_path = transcript_path
                        if process_logger:
                            process_logger.log_technical(f"Transcript saved to: {transcript_path}")
                        else:
                            logger.info(f"Transcript saved to: {transcript_path}")
                    except Exception as transcript_error:
                        warning_message = f"Failed to save transcript: {transcript_error}"
                        if process_logger:
                            process_logger.log_warning(warning_message)
                        else:
                            logger.warning(warning_message)

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
    
    def get_trace_id(self) -> Optional[str]:
        """Get the trace ID from the current experiment, if available."""
        return getattr(self, '_trace_id', None)

    def get_last_transcript_path(self) -> Optional[str]:
        """Return the path of the most recently saved transcript, if available."""
        return self._last_transcript_path
            
    async def _create_participants(self) -> List[ParticipantAgent]:
        """Create participant agents from configuration with dynamic temperature detection."""
        # ProcessFlowLogger handles agent creation logging at higher level
        # Use dynamic temperature detection for all participants
        participants = await create_participant_agents_with_dynamic_temperature(
            self.config.agents, 
            self.config, 
            self.language_manager, 
            self.temperature_cache
        )
        
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
        
        # Track vote timestamps
        vote_timestamps = {}
        
        # Extract vote timestamps from voting history if available
        if (self.agent_logger.voting_history and 
            self.agent_logger.voting_history.vote_rounds and 
            len(self.agent_logger.voting_history.vote_rounds) > 0):
            
            # Get the most recent vote round
            last_vote_round = self.agent_logger.voting_history.vote_rounds[-1]
            
            # Extract vote timestamps from participant_votes array
            if last_vote_round.participant_votes:
                for vote_detail in last_vote_round.participant_votes:
                    participant_name = vote_detail["participant_name"]
                    vote_timestamp = vote_detail.get("vote_timestamp")
                    vote_timestamps[participant_name] = vote_timestamp
            
            # Fill in any missing participants with no timestamp
            for participant in self.participants:
                if participant.name not in vote_timestamps:
                    vote_timestamps[participant.name] = None
        else:
            # Fallback: If no voting history, set no timestamps
            for participant in self.participants:
                vote_timestamps[participant.name] = None
        
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

        # Extract manipulator target info if available (Hypothesis 3)
        manipulator_target_info = None
        if hasattr(self.phase2_manager, '_manipulator_target_info') and self.phase2_manager._manipulator_target_info:
            manipulator_target_info = self.phase2_manager._manipulator_target_info

        # Set the general information
        self.agent_logger.set_general_information(
            consensus_reached=phase2_results.discussion_result.consensus_reached,
            consensus_principle=(
                phase2_results.discussion_result.agreed_principle.principle.value
                if phase2_results.discussion_result.agreed_principle
                else None
            ),
            max_rounds_phase_2=self.config.phase2_rounds,
            rounds_conducted_phase_2=phase2_results.discussion_result.final_round,
            public_conversation=public_conversation,
            config_file=Path(self.config_file_path).name,
            income_class_probabilities=probabilities_dict,
            original_values_mode_enabled=original_values_enabled,
            manipulator_target_info=manipulator_target_info
        )
        
        # Update individual agent vote information for audit trail
        # Extract individual votes from voting history if available
        agent_votes = {}
        if (self.agent_logger.voting_history and 
            self.agent_logger.voting_history.vote_rounds and 
            len(self.agent_logger.voting_history.vote_rounds) > 0):
            
            last_vote_round = self.agent_logger.voting_history.vote_rounds[-1]
            if last_vote_round.participant_votes:
                for vote_detail in last_vote_round.participant_votes:
                    participant_name = vote_detail["participant_name"]
                    assessed_choice = vote_detail["assessed_choice"]
                    agent_votes[participant_name] = assessed_choice
        
        # Fill in any missing participants
        for participant in self.participants:
            if participant.name not in agent_votes:
                agent_votes[participant.name] = "No vote"
        
        self.agent_logger.update_agent_votes(agent_votes, vote_timestamps)
        
        # Store information for later consensus validation
        self._consensus_validation_info = None
        if phase2_results.discussion_result.consensus_reached and phase2_results.discussion_result.agreed_principle:
            self._consensus_validation_info = {
                'consensus_principle': phase2_results.discussion_result.agreed_principle.principle.value,
                'discussion_content': phase2_results.discussion_result.discussion_history
            }
    
    def _set_fallback_general_info(self, phase2_results):
        """Set minimal general information as fallback when main method fails."""
        try:
            # Set minimal general information
            self.agent_logger.set_general_information(
                consensus_reached=phase2_results.discussion_result.consensus_reached,
                consensus_principle=(
                    phase2_results.discussion_result.agreed_principle.principle.value
                    if phase2_results.discussion_result.agreed_principle
                    else None
                ),
                max_rounds_phase_2=self.config.phase2_rounds,
                rounds_conducted_phase_2=phase2_results.discussion_result.final_round,
                public_conversation=phase2_results.discussion_result.discussion_history or "No discussion recorded",
                config_file=Path(self.config_file_path).name
            )
            
            logger.info("Fallback general information set successfully")
            
        except Exception as e:
            logger.error(f"Even fallback general information failed: {e}")
            # Last resort - set absolute minimum information
            try:
                self.agent_logger.set_general_information(
                    consensus_reached=False,
                    consensus_principle=None,
                    max_rounds_phase_2=self.config.phase2_rounds,
                    rounds_conducted_phase_2=0,
                    public_conversation="Logging error occurred",
                    config_file=Path(self.config_file_path).name
                )
            except Exception as final_e:
                logger.error(f"Absolute fallback also failed: {final_e}")
    
    def save_results(self, results: ExperimentResults, output_path: str):
        """Save experiment results to JSON file using agent-centric logging."""
        # Add seed info to the logger before saving
        self.agent_logger.set_seed_info(results.seed_used, results.seed_source)
        self.agent_logger.save_to_file(output_path)
        logger.info(f"Results saved to: {output_path}")
        logger.info(f"Seed used: {results.seed_used} ({results.seed_source})")

    
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
