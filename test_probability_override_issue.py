#!/usr/bin/env python3
"""
Test script to reproduce and verify the income class probability override issue.
"""

import random
from collections import Counter
from core.distribution_generator import DistributionGenerator
from models.experiment_types import IncomeDistribution, IncomeClass, IncomeClassProbabilities

def test_probability_override_issue():
    """Test to reproduce the issue where original_values_mode overrides config probabilities."""
    
    print("=== INCOME CLASS PROBABILITY OVERRIDE ISSUE REPRODUCTION ===")
    print()
    
    # Create test distribution
    test_distribution = IncomeDistribution(
        high=100000,
        medium_high=75000, 
        medium=50000,
        medium_low=25000,
        low=10000
    )
    
    # Create config probabilities (what user expects)
    config_probabilities = IncomeClassProbabilities(
        high=0.0,      # 0%
        medium_high=0.0,   # 0%
        medium=0.0,    # 0%
        medium_low=0.0,    # 0%
        low=1.0        # 100%
    )
    
    print("USER'S CONFIG PROBABILITIES:")
    print(f"  High: {config_probabilities.high*100}% (Expected: 0%)")
    print(f"  Medium High: {config_probabilities.medium_high*100}% (Expected: 0%)")
    print(f"  Medium: {config_probabilities.medium*100}% (Expected: 0%)")
    print(f"  Medium Low: {config_probabilities.medium_low*100}% (Expected: 0%)")
    print(f"  Low: {config_probabilities.low*100}% (Expected: 100%)")
    print()
    
    # Test what user expected
    print("=== TESTING WITH USER'S CONFIG (What should happen) ===")
    num_tests = 1000
    assignments_config = []
    
    random.seed(12345)
    test_random = random.Random(12345)
    
    for _ in range(num_tests):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution, 
            config_probabilities,
            random_gen=test_random
        )
        assignments_config.append(assigned_class)
    
    config_counts = Counter(assignments_config)
    
    print("Results with USER'S CONFIG PROBABILITIES:")
    for income_class in IncomeClass:
        count = config_counts[income_class]
        actual_pct = (count / num_tests) * 100
        print(f"  {income_class.value.title().replace('_', ' ')}: {count} assignments ({actual_pct:.1f}%)")
    
    print()
    
    # Test what actually happens with original_values_mode
    print("=== TESTING WITH ORIGINAL_VALUES_MODE (What actually happens) ===")
    
    # Get original values probabilities for each round 
    for round_num in range(1, 5):
        original_probs = DistributionGenerator.get_original_values_probabilities(round_num)
        situation = ["A", "B", "C", "D"][round_num - 1]
        
        print(f"ROUND {round_num} (Situation {situation}) PROBABILITIES:")
        print(f"  High: {original_probs.high*100:.1f}%")
        print(f"  Medium High: {original_probs.medium_high*100:.1f}%")
        print(f"  Medium: {original_probs.medium*100:.1f}%")
        print(f"  Medium Low: {original_probs.medium_low*100:.1f}%")
        print(f"  Low: {original_probs.low*100:.1f}%")
        
        # Test assignments for this round
        assignments_original = []
        test_random = random.Random(12345)
        
        for _ in range(num_tests):
            assigned_class, payoff = DistributionGenerator.calculate_payoff(
                test_distribution,
                original_probs,
                random_gen=test_random
            )
            assignments_original.append(assigned_class)
        
        original_counts = Counter(assignments_original)
        
        print(f"  Actual Results Round {round_num}:")
        for income_class in IncomeClass:
            count = original_counts[income_class]
            actual_pct = (count / num_tests) * 100
            expected_pct = getattr(original_probs, income_class.value) * 100
            print(f"    {income_class.value.title().replace('_', ' ')}: {count} assignments ({actual_pct:.1f}%, expected {expected_pct:.1f}%)")
        print()
    
    # Verify the problem
    print("=== PROBLEM VERIFICATION ===")
    print("❌ USER EXPECTS: 100% Low class assignments")
    print("✅ ACTUAL RESULT: Mixed class assignments based on original_values_mode")
    print()
    print("ROOT CAUSE:")
    print("- User set income_class_probabilities with low=1.0, others=0.0")
    print("- BUT original_values_mode.enabled=true in config")
    print("- original_values_mode OVERRIDES config probabilities")
    print("- Each round uses different hardcoded probabilities from original_values_data.py")
    print()
    print("SOLUTION:")
    print("- Set original_values_mode.enabled=false to use config probabilities")
    print("- OR acknowledge that original_values_mode uses predefined probabilities")

if __name__ == "__main__":
    test_probability_override_issue()