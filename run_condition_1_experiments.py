#!/usr/bin/env python3
"""
Script to run all config files in hypothesis_2_&_4/configs/condition_1 sequentially
and save the results to hypothesis_2_&_4/logs directory.
"""

import os
import sys
import glob
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

def main():
    # Set up paths
    project_root = Path(__file__).parent
    config_dir = project_root / "hypothesis_2_&_4" / "configs" / "condition_1"
    logs_dir = project_root / "hypothesis_2_&_4" / "logs"
    
    # Ensure logs directory exists
    logs_dir.mkdir(exist_ok=True)
    
    # Get all config files sorted by name
    config_files = sorted(glob.glob(str(config_dir / "*.yaml")))
    
    if not config_files:
        print(f"No config files found in {config_dir}")
        return 1
    
    print(f"Found {len(config_files)} config files to run:")
    for config_file in config_files:
        print(f"  - {Path(config_file).name}")
    print()
    
    successful_runs = 0
    failed_runs = 0
    
    for i, config_file in enumerate(config_files, 1):
        config_name = Path(config_file).stem
        print(f"[{i}/{len(config_files)}] Running experiment with {config_name}...")
        
        try:
            # Run the experiment
            result = subprocess.run([
                sys.executable, "main.py", config_file
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print(f"  ✓ Successfully completed {config_name}")
                
                # Find the most recent experiment results file
                result_files = glob.glob(str(project_root / "experiment_results_*.json"))
                if result_files:
                    latest_result = max(result_files, key=os.path.getctime)
                    
                    # Move to logs directory with descriptive name
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_name = f"{config_name}_results_{timestamp}.json"
                    destination = logs_dir / new_name
                    
                    shutil.move(latest_result, destination)
                    print(f"  → Results saved to {destination.relative_to(project_root)}")
                
                successful_runs += 1
            else:
                print(f"  ✗ Failed to run {config_name}")
                print(f"    Error: {result.stderr}")
                failed_runs += 1
                
        except Exception as e:
            print(f"  ✗ Exception running {config_name}: {e}")
            failed_runs += 1
        
        print()
    
    # Summary
    print("="*50)
    print("EXPERIMENT BATCH SUMMARY")
    print("="*50)
    print(f"Total configs: {len(config_files)}")
    print(f"Successful runs: {successful_runs}")
    print(f"Failed runs: {failed_runs}")
    print(f"Results saved to: {logs_dir.relative_to(project_root)}")
    
    return 0 if failed_runs == 0 else 1

if __name__ == "__main__":
    sys.exit(main())