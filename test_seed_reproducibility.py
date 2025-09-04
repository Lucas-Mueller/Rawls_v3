#!/usr/bin/env python3
"""
Test script to verify seed system reproducibility with 5-class system.
"""

import sys
from core.distribution_generator import DistributionGenerator
from models.experiment_types import IncomeDistribution, IncomeClass, IncomeClassProbabilities
from utils.seed_manager import SeedManager

def test_seed_reproducibility():
    """Test that same seed produces same income class assignments."""
    
    # Create test income distribution
    test_distribution = IncomeDistribution(
        high=100000,
        medium_high=75000,
        medium=50000,
        medium_low=25000,
        low=10000
    )
    
    # Create config probabilities
    config_probabilities = IncomeClassProbabilities(
        high=0.05, medium_high=0.10, medium=0.50, medium_low=0.25, low=0.10
    )
    
    print("=== Seed System Reproducibility Test ===")
    print("Testing if same seed produces identical class assignments across runs")
    print()
    
    # Test 1: Same seed should produce identical results
    seed = 12345
    num_assignments = 100
    
    print(f"Test 1: Same seed ({seed}) across multiple runs")
    print("-" * 50)
    
    # Run 1
    seed_manager_1 = SeedManager(seed)
    assignments_1 = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution, 
            config_probabilities,
            random_gen=seed_manager_1.random
        )
        assignments_1.append(assigned_class.value)
    
    # Run 2 with same seed
    seed_manager_2 = SeedManager(seed)
    assignments_2 = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution,
            config_probabilities,
            random_gen=seed_manager_2.random
        )
        assignments_2.append(assigned_class.value)
    
    # Run 3 with same seed
    seed_manager_3 = SeedManager(seed)
    assignments_3 = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution,
            config_probabilities, 
            random_gen=seed_manager_3.random
        )
        assignments_3.append(assigned_class.value)
    
    # Check if all runs are identical
    identical_12 = assignments_1 == assignments_2
    identical_23 = assignments_2 == assignments_3
    identical_13 = assignments_1 == assignments_3
    
    print(f"Run 1 vs Run 2 identical: {'✓' if identical_12 else '✗'}")
    print(f"Run 2 vs Run 3 identical: {'✓' if identical_23 else '✗'}")
    print(f"Run 1 vs Run 3 identical: {'✓' if identical_13 else '✗'}")
    print(f"All runs identical: {'✓' if identical_12 and identical_23 and identical_13 else '✗'}")
    
    if not (identical_12 and identical_23 and identical_13):
        print("\nFirst 10 assignments comparison:")
        print("Run 1:", assignments_1[:10])
        print("Run 2:", assignments_2[:10])
        print("Run 3:", assignments_3[:10])
    
    print()
    
    # Test 2: Different seeds should produce different results
    print("Test 2: Different seeds should produce different results")
    print("-" * 50)
    
    seed_a, seed_b = 11111, 99999
    
    # Run A
    seed_manager_a = SeedManager(seed_a)
    assignments_a = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution,
            config_probabilities,
            random_gen=seed_manager_a.random
        )
        assignments_a.append(assigned_class.value)
    
    # Run B  
    seed_manager_b = SeedManager(seed_b)
    assignments_b = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution,
            config_probabilities,
            random_gen=seed_manager_b.random
        )
        assignments_b.append(assigned_class.value)
    
    different_seeds = assignments_a != assignments_b
    print(f"Seed {seed_a} vs Seed {seed_b} different: {'✓' if different_seeds else '✗'}")
    
    if not different_seeds:
        print("WARNING: Different seeds produced identical results!")
        print("First 10 assignments:")
        print(f"Seed {seed_a}:", assignments_a[:10])
        print(f"Seed {seed_b}:", assignments_b[:10])
    
    print()
    
    # Test 3: Test without random_gen (should be non-reproducible)
    print("Test 3: Without random_gen parameter (expected to be non-reproducible)")
    print("-" * 50)
    
    # Run without seed system
    assignments_no_seed_1 = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution,
            config_probabilities
            # No random_gen parameter
        )
        assignments_no_seed_1.append(assigned_class.value)
    
    assignments_no_seed_2 = []
    for i in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution,
            config_probabilities
            # No random_gen parameter
        )
        assignments_no_seed_2.append(assigned_class.value)
    
    no_seed_identical = assignments_no_seed_1 == assignments_no_seed_2
    print(f"Two runs without seed identical: {'✗ (expected)' if not no_seed_identical else '✓ (unexpected!)'}")
    
    print("\n=== Summary ===")
    seed_system_working = (identical_12 and identical_23 and identical_13) and different_seeds
    print(f"Seed system working correctly: {'✓' if seed_system_working else '✗'}")
    
    if not seed_system_working:
        print("⚠️  Seed system has reproducibility issues")
        return False
    else:
        print("✅ Seed system providing proper reproducibility")
        return True

if __name__ == "__main__":
    test_seed_reproducibility()