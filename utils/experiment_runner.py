"""
Experiment runner module for Jupyter notebooks.
Provides functions to generate configs and run experiments.
"""
import asyncio
import logging
import sys
import json
import os
import tempfile
import random
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Union
from dotenv import load_dotenv

# For Jupyter notebook compatibility
import nest_asyncio
nest_asyncio.apply()

# Import project modules
from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from utils.language_manager import get_language_manager, set_global_language, SupportedLanguage

# Load environment variables
load_dotenv()


def generate_random_config(
    num_agents: int = 3,
    num_rounds: int = 20,
    personality: str = "Analytical and methodical. Values fairness and systematic approaches to problem-solving. Tends to think through decisions carefully and considers long-term consequences.",
    models: Union[str, List[str]] = "gpt-4.1-mini",
    temperature: Union[float, tuple] = (0.0, 1.0),
    memory_limit: int = 50000,
    reasoning_enabled: bool = True,
    utility_model: str = "gpt-4.1-mini",
    language: str = "English",
    distribution_range_phase1: List[float] = [0.5, 2.0],
    distribution_range_phase2: List[float] = [0.5, 2.0]
) -> Dict[str, Any]:
    """Generate a random configuration for the Frohlich Experiment."""
    
    agents = []
    for i in range(num_agents):
        agent_name = f"Agent_{i + 1}"
        
        if isinstance(models, list):
            selected_model = random.choice(models)
        else:
            selected_model = models
        
        if isinstance(temperature, tuple) and len(temperature) == 2:
            selected_temp = round(random.uniform(temperature[0], temperature[1]), 2)
        else:
            selected_temp = float(temperature)
        
        agent_config = {
            "name": agent_name,
            "personality": personality,
            "model": selected_model,
            "temperature": selected_temp,
            "memory_character_limit": memory_limit,
            "reasoning_enabled": reasoning_enabled
        }
        agents.append(agent_config)
    
    config = {
        "language": language,
        "agents": agents,
        "utility_agent_model": utility_model,
        "phase2_rounds": num_rounds,
        "distribution_range_phase1": distribution_range_phase1,
        "distribution_range_phase2": distribution_range_phase2
    }
    
    return config


def generate_and_save_configs(
    num_configs: int = 10,
    save_path: str = "hypothesis_2_&_4/configs/condition_1",
    **config_params
):
    """Generate multiple random configurations and save them as YAML files."""
    
    os.makedirs(save_path, exist_ok=True)
    
    configs = []
    for i in range(num_configs):
        config = generate_random_config(**config_params)
        configs.append(config)
        
        filename = f"config_{i+1:02d}.yaml"
        filepath = os.path.join(save_path, filename)
        
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        print(f"Saved {filename}")
    
    print(f"Generated and saved {num_configs} configurations in {save_path}")
    return configs


def setup_logging():
    """Set up logging configuration for Jupyter."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def run_experiment_from_config(
    config_dict: dict,
    output_path: str = None,
    verbose: bool = True
) -> dict:
    """Run Frohlich Experiment from a configuration dictionary in Jupyter notebook."""
    
    if verbose:
        setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            yaml.dump(config_dict, temp_file, default_flow_style=False, indent=2)
            temp_config_path = temp_file.name
        
        # Load configuration
        config = ExperimentConfiguration.from_yaml(temp_config_path)
        os.unlink(temp_config_path)
        
        # Initialize language manager
        try:
            language_enum = SupportedLanguage(config.language)
            set_global_language(language_enum)
            if verbose:
                logger.info(f"Language set to: {config.language}")
        except ValueError:
            if verbose:
                logger.error(f"Unsupported language: {config.language}. Using English as fallback.")
            set_global_language(SupportedLanguage.ENGLISH)
        
        # Log configuration details
        if verbose:
            logger.info(f"Configuration: {len(config.agents)} participants, {config.phase2_rounds} max rounds")
            for agent in config.agents:
                logger.info(f"  - {agent.name}: {agent.model} (temp={agent.temperature})")
        
        # Initialize and run experiment
        experiment_manager = FrohlichExperimentManager(config)
        
        if verbose:
            logger.info("=" * 50)
            logger.info(f"STARTING EXPERIMENT {experiment_manager.experiment_id}")
            logger.info("=" * 50)
        
        results = await experiment_manager.run_complete_experiment()
        
        # Set output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Default to logs directory to match parallel execution behavior
            output_path = f"hypothesis_2_&_4/logs/experiment_results_{timestamp}.json"
        
        # Save results
        experiment_manager.save_results(results, output_path)
        
        if verbose:
            logger.info("=" * 50)
            logger.info("EXPERIMENT COMPLETED SUCCESSFULLY")
            logger.info("=" * 50)
            logger.info(f"Results saved to: {output_path}")
        
        return results
        
    except Exception as e:
        if verbose:
            logger.error(f"Experiment failed: {e}")
        raise e


def run_experiment(config_dict: dict, output_path: str = None, verbose: bool = True) -> dict:
    """Synchronous wrapper for running experiments in Jupyter notebooks."""
    return asyncio.run(run_experiment_from_config(config_dict, output_path, verbose))


async def run_experiments_parallel_async(
    config_files: List[str],
    max_parallel: int = 5,
    output_dir: str = "hypothesis_2_&_4/logs",
    verbose: bool = True
) -> List[dict]:
    """
    Run multiple experiments in parallel with controlled concurrency.
    
    Parameters:
    - config_files: List of paths to config YAML files
    - max_parallel: Maximum number of experiments to run concurrently
    - output_dir: Directory to save results
    - verbose: Whether to enable verbose logging
    
    Returns:
    - List of experiment results dictionaries
    """
    if verbose:
        setup_logging()
    logger = logging.getLogger(__name__)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load all configurations
    configs_and_files = []
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                config_dict = yaml.safe_load(f)
            configs_and_files.append((config_dict, config_file))
        except Exception as e:
            if verbose:
                logger.error(f"Failed to load config {config_file}: {e}")
            continue
    
    if verbose:
        logger.info(f"Loaded {len(configs_and_files)} configurations")
        logger.info(f"Running with max {max_parallel} parallel experiments")
    
    # Semaphore to control concurrency
    semaphore = asyncio.Semaphore(max_parallel)
    
    async def run_single_experiment(config_dict: dict, config_file: str):
        """Run a single experiment with semaphore control."""
        async with semaphore:
            try:
                # Generate output path based on config file name
                config_name = Path(config_file).stem
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"{config_name}_results_{timestamp}.json")
                
                if verbose:
                    logger.info(f"Starting experiment: {config_name}")
                
                # Run the experiment
                result = await run_experiment_from_config(
                    config_dict, 
                    output_path, 
                    verbose=False  # Disable individual experiment logging to reduce noise
                )
                
                if verbose:
                    logger.info(f"Completed experiment: {config_name} -> {output_path}")
                
                return {
                    'config_file': config_file,
                    'output_path': output_path,
                    'status': 'success',
                    'result': result
                }
                
            except Exception as e:
                if verbose:
                    logger.error(f"Failed experiment {config_file}: {e}")
                return {
                    'config_file': config_file,
                    'status': 'failed',
                    'error': str(e)
                }
    
    # Create tasks for all experiments
    tasks = []
    for config_dict, config_file in configs_and_files:
        task = run_single_experiment(config_dict, config_file)
        tasks.append(task)
    
    # Run all experiments with controlled concurrency
    if verbose:
        logger.info("Starting parallel experiment execution...")
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful_results = []
    failed_results = []
    
    for result in results:
        if isinstance(result, Exception):
            failed_results.append({'error': str(result), 'status': 'exception'})
        elif result.get('status') == 'success':
            successful_results.append(result)
        else:
            failed_results.append(result)
    
    if verbose:
        logger.info("=" * 60)
        logger.info("PARALLEL EXECUTION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Successful experiments: {len(successful_results)}")
        logger.info(f"Failed experiments: {len(failed_results)}")
        
        if successful_results:
            logger.info("\nSuccessful experiments:")
            for result in successful_results:
                logger.info(f"  - {Path(result['config_file']).name} -> {result['output_path']}")
        
        if failed_results:
            logger.info("\nFailed experiments:")
            for result in failed_results:
                config_name = Path(result.get('config_file', 'unknown')).name if 'config_file' in result else 'unknown'
                logger.info(f"  - {config_name}: {result.get('error', 'Unknown error')}")
    
    return results


def run_experiments_parallel(
    config_files: List[str],
    max_parallel: int = 5,
    output_dir: str = "hypothesis_2_&_4/logs",
    verbose: bool = True
) -> List[dict]:
    """
    Synchronous wrapper for running experiments in parallel.
    
    Parameters:
    - config_files: List of paths to config YAML files
    - max_parallel: Maximum number of experiments to run concurrently
    - output_dir: Directory to save results
    - verbose: Whether to enable verbose logging
    
    Returns:
    - List of experiment results dictionaries
    """
    return asyncio.run(run_experiments_parallel_async(config_files, max_parallel, output_dir, verbose))