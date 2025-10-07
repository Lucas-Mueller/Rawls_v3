"""
Main entry point for the Frohlich Experiment.

Usage:
    python main.py [config_path] [output_path]
    
Arguments:
    config_path: Path to YAML configuration file (default: config/default_config.yaml)
    output_path: Path for JSON results output (default: experiment_results_TIMESTAMP.json)
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# OpenAI Agents SDK tracing is enabled for experiment tracking

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from utils.language_manager import create_language_manager, SupportedLanguage
from utils.logging.process_flow_logger import create_process_logger

# Load environment variables from .env file
load_dotenv()


def setup_logging(verbosity_level: str = "debug"):
    """Set up logging configuration based on verbosity level."""
    # For debug verbosity, show all technical logs
    # For other levels, reduce or eliminate technical logging
    if verbosity_level == "debug":
        level = logging.INFO
    elif verbosity_level == "detailed":
        level = logging.WARNING
    else:
        level = logging.ERROR
        
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


async def main():
    """Main entry point for Frohlich Experiment."""
    
    # Parse command line arguments first to get config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default_config.yaml"
    
    # Load configuration to determine logging settings
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"❌ Configuration file not found: {config_path}")
            sys.exit(1)
        
        config = ExperimentConfiguration.from_yaml(config_path)
        
        # Get logging configuration
        logging_config = config.logging if config.logging else None
        verbosity_level = logging_config.verbosity_level if logging_config else "standard"
        use_colors = logging_config.use_colors if logging_config else True
        
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        # Fallback to standard logging
        verbosity_level = "standard"
        use_colors = True
        
    # Set up both loggers
    setup_logging(verbosity_level)
    logger = logging.getLogger(__name__)
    process_logger = create_process_logger(verbosity_level, use_colors)
    
    # Warn if tracing is globally disabled via environment (only in detailed/debug mode)
    if verbosity_level in ["detailed", "debug"]:
        try:
            import os
            disable_flags = {
                'OPENAI_AGENTS_DISABLE_TRACING': os.getenv('OPENAI_AGENTS_DISABLE_TRACING'),
                'OPENAI_DISABLE_TRACING': os.getenv('OPENAI_DISABLE_TRACING')
            }
            if any(v for v in disable_flags.values() if str(v).lower() in ['1', 'true', 'yes']):
                process_logger.log_warning("OpenAI tracing disabled via environment variables")
        except Exception:
            pass
    
    # Determine output path
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"experiment_results_{timestamp}.json"
    
    try:
        # Configuration already loaded above
        process_logger.log_technical(f"Loading configuration from: {config_path}")
        
        # Create language manager for this experiment with seed
        try:
            language_enum = SupportedLanguage(config.language)
            effective_seed = config.get_effective_seed()
            language_manager = create_language_manager(language_enum, effective_seed)
            process_logger.log_technical(f"Language set to: {config.language}")
        except ValueError:
            process_logger.log_error(f"Unsupported language: {config.language}. Using English as fallback.")
            effective_seed = config.get_effective_seed()
            language_manager = create_language_manager(SupportedLanguage.ENGLISH, effective_seed)
        
        # Initialize and run experiment
        experiment_manager = FrohlichExperimentManager(config, config_path, language_manager)
        
        # Start experiment with clean logging
        config_summary = {
            'agents': [{'name': a.name, 'model': a.model, 'temperature': a.temperature} for a in config.agents],
            'language': config.language,
            'phase2_rounds': config.phase2_rounds,
            'config_file': Path(config_path).name
        }
        
        process_logger.start_experiment(experiment_manager.experiment_id, config_summary)
        
        # Technical details only shown in debug mode
        process_logger.log_debug("✅ FORMAL VOTING: Using structured consensus building with confirmation and secret ballot")
        process_logger.log_debug("   • Voting initiated via end-of-round prompts only")
        process_logger.log_debug("   • Voting requires confirmation from all participants")
        process_logger.log_debug("   • Consensus reached via unanimous secret ballot")
        process_logger.log_technical("Tracing policy: participant-only spans; utility agents untraced")
        
        # Run the complete experiment (this now includes ProcessFlowLogger integration)
        results = await experiment_manager.run_complete_experiment(process_logger)
        
        # Save results
        experiment_manager.save_results(results, output_path)
        process_logger.log_technical(f"Results saved to: {output_path}")
        
        # Prepare experiment completion summary
        experiment_summary = {
            'consensus_reached': results.phase2_results.discussion_result.consensus_reached,
            'chosen_principle': results.phase2_results.discussion_result.agreed_principle.principle.value if results.phase2_results.discussion_result.agreed_principle else None,
            'total_errors': 0,  # Will be filled by experiment manager
            'results_file': output_path
        }

        transcript_path = experiment_manager.get_last_transcript_path()
        if transcript_path:
            experiment_summary['transcript_file'] = transcript_path
        
        # Display trace link if available
        trace_id = experiment_manager.get_trace_id()
        if trace_id:
            # Ensure trace_id has trace_ prefix for proper URL format
            full_trace_id = trace_id if trace_id.startswith('trace_') else f'trace_{trace_id}'
            # Use correct logs/trace URL path
            trace_url = f"https://platform.openai.com/logs/trace?trace_id={full_trace_id}"
            experiment_summary['trace_url'] = trace_url

            # Check if OPENAI_API_KEY is set and show trace in detailed/debug modes
            import os
            if verbosity_level in ["detailed", "debug"]:
                if os.getenv('OPENAI_API_KEY'):
                    process_logger.log_debug(f"Trace: {trace_url}")
                else:
                    process_logger.log_debug(f"Trace ID: {full_trace_id} (API key not set)")
        
        # Show experiment completion
        process_logger.experiment_completed(experiment_summary)
        
        # Show detailed summary only in detailed/debug modes
        if verbosity_level in ["detailed", "debug"]:
            summary = experiment_manager.get_experiment_summary(results)
            print("\n" + summary)
        
    except KeyboardInterrupt:
        process_logger.log_error("Experiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        process_logger.log_error(f"Experiment failed: {e}")
        if verbosity_level == "debug":
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
