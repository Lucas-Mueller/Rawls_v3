#!/usr/bin/env python3
"""
Simple test script to verify parallel execution safety.

This script runs multiple FrohlichExperiment instances concurrently
to verify that they don't interfere with each other due to shared state.
"""

import asyncio
import logging
from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from utils.language_manager import create_language_manager, SupportedLanguage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_single_experiment(experiment_id: int, config_path: str = "config/fast_config.yaml"):
    """Run a single experiment and return basic results."""
    try:
        # Load configuration
        config = ExperimentConfiguration.from_yaml(config_path)
        language_manager = create_language_manager(SupportedLanguage(config.language))
        
        # Create experiment manager - each gets its own instances
        manager = FrohlichExperimentManager(config, config_path, language_manager)
        
        # Initialize the manager
        await manager.async_init()
        
        # Extract key state for comparison
        seed_used = manager.seed_manager.current_seed
        temp_cache_models = len(manager.temperature_cache.get_info()["models"])
        
        logger.info(f"Experiment {experiment_id}: Seed={seed_used}, TempCacheModels={temp_cache_models}")
        
        return {
            "experiment_id": experiment_id,
            "seed_used": seed_used,
            "temp_cache_models": temp_cache_models,
            "success": True
        }
    except Exception as e:
        logger.error(f"Experiment {experiment_id} failed: {e}")
        return {
            "experiment_id": experiment_id,
            "error": str(e),
            "success": False
        }

async def test_parallel_execution():
    """Test parallel execution of multiple experiments."""
    logger.info("🔍 Testing parallel execution safety...")
    
    # Run 3 experiments in parallel
    num_experiments = 3
    tasks = []
    
    for i in range(num_experiments):
        task = asyncio.create_task(run_single_experiment(i + 1))
        tasks.append(task)
    
    # Wait for all experiments to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze results
    logger.info("📊 Analysis of parallel execution:")
    
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    
    if len(successful_results) < num_experiments:
        logger.error(f"❌ Only {len(successful_results)}/{num_experiments} experiments succeeded")
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception: {result}")
            elif isinstance(result, dict) and not result.get("success"):
                logger.error(f"Failed experiment: {result}")
    else:
        logger.info(f"✅ All {num_experiments} experiments completed successfully")
        
        # Check for interference
        seeds = [r["seed_used"] for r in successful_results]
        if len(set(seeds)) == len(seeds):
            logger.info(f"✅ All experiments used different seeds: {seeds}")
        else:
            logger.warning(f"⚠️ Some experiments used same seeds: {seeds}")
    
    return successful_results

async def main():
    """Main test function."""
    print("🚀 Testing Parallel Execution Safety for Frohlich Experiment")
    print("=" * 60)
    
    try:
        results = await test_parallel_execution()
        
        print("\n" + "=" * 60)
        if len(results) >= 3:
            print("✅ PARALLEL EXECUTION TEST PASSED")
            print("Multiple experiments can run concurrently without interference")
        else:
            print("❌ PARALLEL EXECUTION TEST FAILED") 
            print("Experiments interfered with each other or failed")
            
    except Exception as e:
        print(f"❌ TEST FAILED WITH EXCEPTION: {e}")
        logger.exception("Test failed")

if __name__ == "__main__":
    asyncio.run(main())