#!/usr/bin/env python3
"""
Test script to verify parallel experiment execution safety.
"""
import asyncio
import time
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


async def test_parallel_experiments():
    """Test running multiple experiments in parallel."""

    # Use a fast config for testing
    config_path = "config/fast.yaml"

    if not Path(config_path).exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    print("🧪 Testing parallel experiment execution...")

    # Run 3 experiments in parallel
    num_experiments = 3

    def run_experiment(exp_id):
        """Run a single experiment via subprocess."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"test_parallel_results_{exp_id}_{timestamp}.json"

        cmd = [sys.executable, "main.py", config_path, output_path]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=Path.cwd()
            )
            return {
                'exp_id': exp_id,
                'returncode': result.returncode,
                'output_path': output_path,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0 and Path(output_path).exists()
            }
        except subprocess.TimeoutExpired:
            return {
                'exp_id': exp_id,
                'returncode': -1,
                'output_path': output_path,
                'stdout': '',
                'stderr': 'TIMEOUT',
                'success': False
            }

    # Run experiments in parallel
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_experiments) as executor:
        futures = [executor.submit(run_experiment, i) for i in range(num_experiments)]
        results = []

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            print(f"Experiment {result['exp_id']}: {status}")

    total_time = time.time() - start_time

    # Analyze results
    successful = sum(1 for r in results if r['success'])
    print("
📊 Results Summary:"    print(f"   Total experiments: {num_experiments}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {num_experiments - successful}")
    print(".2f"
    # Check for interference
    output_files = [r['output_path'] for r in results if r['success']]
    if len(output_files) == len(set(output_files)):
        print("✅ No file conflicts detected")
    else:
        print("❌ File conflicts detected!")
        return False

    # Clean up test files
    for result in results:
        if Path(result['output_path']).exists():
            Path(result['output_path']).unlink()

    print("🧹 Cleaned up test files")

    return successful == num_experiments


if __name__ == "__main__":
    success = asyncio.run(test_parallel_experiments())
    if success:
        print("\n🎉 Parallel execution test PASSED")
        sys.exit(0)
    else:
        print("\n💥 Parallel execution test FAILED")
        sys.exit(1)