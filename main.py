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

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager

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
        
        # Validate configuration
        logger.info(f"Configuration loaded: {len(config.agents)} participants, {config.phase2_rounds} max rounds")
        logger.info(f"  Utility agent model: {config.utility_agent_model}")
        for agent in config.agents:
            logger.info(f"  - {agent.name}: {agent.model} (temp={agent.temperature})")
        
        # Initialize and run experiment
        experiment_manager = FrohlichExperimentManager(config)
        
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
        logger.info(f"View traces at: https://platform.openai.com/traces")
        
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