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

# Load environment variables from .env file
load_dotenv()


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


async def main():
    """Main entry point for Frohlich Experiment."""
    
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Warn if tracing is globally disabled via environment
    try:
        import os
        disable_flags = {
            'OPENAI_AGENTS_DISABLE_TRACING': os.getenv('OPENAI_AGENTS_DISABLE_TRACING'),
            'OPENAI_DISABLE_TRACING': os.getenv('OPENAI_DISABLE_TRACING')
        }
        if any(v for v in disable_flags.values() if str(v).lower() in ['1', 'true', 'yes']):
            logger.warning("OpenAI Agents SDK tracing appears disabled via environment variables. "
                           "Participant runs will not be traced. Unset OPENAI_AGENTS_DISABLE_TRACING/OPENAI_DISABLE_TRACING to enable.")
    except Exception:
        pass
    
    # Parse command line arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default_config.yaml"
    
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"experiment_results_{timestamp}.json"
    
    try:
        # Load configuration
        config_file = Path(config_path)
        if not config_file.exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
        
        logger.info(f"Loading configuration from: {config_path}")
        config = ExperimentConfiguration.from_yaml(config_path)
        
        # Create language manager for this experiment
        try:
            language_enum = SupportedLanguage(config.language)
            language_manager = create_language_manager(language_enum)
            logger.info(f"Language set to: {config.language}")
        except ValueError:
            logger.error(f"Unsupported language: {config.language}. Using English as fallback.")
            language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        
        # Validate configuration
        logger.info(f"Configuration loaded: {len(config.agents)} participants, {config.phase2_rounds} max rounds")
        logger.info(f"  Utility agent model: {config.utility_agent_model}")
        logger.info(f"  Voting detection mode: {config.voting_detection_mode}")
        
        # Validate voting detection mode configuration
        if config.voting_detection_mode not in ["simple", "complex"]:
            logger.error(f"Invalid voting_detection_mode: {config.voting_detection_mode}. Must be 'simple' or 'complex'")
            sys.exit(1)
        
        # Check for mode/prompt alignment
        # language_manager will be created later based on config language
        if config.voting_detection_mode == "simple":
            logger.info("✅ SIMPLE MODE: Using preference-based consensus detection")
            logger.info("   • Agents will state preferences using 'My preference is [principle]'")
            logger.info("   • Consensus reached when all participants state matching preferences")
        else:
            logger.info("✅ COMPLEX MODE: Using formal voting with confirmation and secret ballot")
            logger.info("   • Agents can call for votes using 'Let's vote' or similar")
            logger.info("   • Voting requires confirmation from all participants")
            logger.info("   • Consensus reached via unanimous secret ballot")
        
        for agent in config.agents:
            logger.info(f"  - {agent.name}: {agent.model} (temp={agent.temperature})")
        
        # Initialize and run experiment
        experiment_manager = FrohlichExperimentManager(config, config_path, language_manager)
        logger.info("Tracing policy: participant-only spans; utility agents untraced")
        
        logger.info("=" * 60)
        logger.info(f"STARTING FROHLICH EXPERIMENT")
        logger.info(f"Experiment ID: {experiment_manager.experiment_id}")
        logger.info(f"Participants: {len(config.agents)}")
        logger.info(f"Max Phase 2 rounds: {config.phase2_rounds}")
        logger.info("=" * 60)
        
        # Run the complete experiment
        results = await experiment_manager.run_complete_experiment()
        
        # Save results
        experiment_manager.save_results(results, output_path)
        
        # Print summary
        logger.info("=" * 60)
        logger.info("EXPERIMENT COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        summary = experiment_manager.get_experiment_summary(results)
        print("\n" + summary)
        
        logger.info(f"\nDetailed results saved to: {output_path}")
        
        # Display trace link if available
        trace_id = experiment_manager.get_trace_id()
        if trace_id:
            # Remove 'trace_' prefix if present for proper URL format
            clean_trace_id = trace_id[6:] if trace_id.startswith('trace_') else trace_id
            # Use Observability UI path
            trace_url = f"https://platform.openai.com/observability/traces/{clean_trace_id}"
            
            # Check if OPENAI_API_KEY is set
            import os
            if os.getenv('OPENAI_API_KEY'):
                print(f"\n🔗 Trace: {trace_url}")
                logger.info(f"Trace available at: {trace_url}")
            else:
                print(f"\n⚠️  Trace ID generated: {clean_trace_id}")
                print(f"🔗 Trace URL: {trace_url}")
                print("⚠️  Note: OPENAI_API_KEY not set - trace may not be uploaded to OpenAI platform")
                logger.info(f"Trace ID: {clean_trace_id} (API key not set)")
        else:
            logger.info("No trace ID available for this experiment")
        
    except KeyboardInterrupt:
        logger.info("Experiment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
