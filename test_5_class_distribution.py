#!/usr/bin/env python3
"""
Test script to verify the 5-class income distribution system.
"""

import sys
import random
from collections import Counter
from core.distribution_generator import DistributionGenerator
from models.experiment_types import IncomeDistribution, IncomeClass, IncomeClassProbabilities

def test_5_class_distribution():
    """Test the 5-class income distribution with config probabilities."""
    
    # Create test income distribution
    test_distribution = IncomeDistribution(
        high=100000,
        medium_high=75000,
        medium=50000,
        medium_low=25000,
        low=10000
    )
    
    # Create config probabilities (matching default_config.yaml)
    config_probabilities = IncomeClassProbabilities(
        high=0.05,      # 5%
        medium_high=0.10,   # 10%
        medium=0.50,    # 50%
        medium_low=0.25,    # 25%
        low=0.10        # 10%
    )
    
    print("=== 5-Class Income Distribution Test ===")
    print(f"Config probabilities:")
    print(f"  High: {config_probabilities.high*100}%")
    print(f"  Medium High: {config_probabilities.medium_high*100}%") 
    print(f"  Medium: {config_probabilities.medium*100}%")
    print(f"  Medium Low: {config_probabilities.medium_low*100}%")
    print(f"  Low: {config_probabilities.low*100}%")
    print()
    
    # Test with 10,000 assignments
    num_assignments = 10000
    assignments = []
    
    print(f"Testing {num_assignments:,} assignments...")
    
    # Set seed for reproducible test
    random.seed(42)
    test_random = random.Random(42)
    
    for _ in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution, 
            config_probabilities,
            random_gen=test_random
        )
        assignments.append(assigned_class)
    
    # Count assignments by class
    class_counts = Counter(assignments)
    
    print("Results:")
    print("Class".ljust(15) + "Count".ljust(8) + "Actual %".ljust(12) + "Expected %".ljust(12) + "Difference")
    print("-" * 60)
    
    expected_probs = {
        IncomeClass.HIGH: 0.05,
        IncomeClass.MEDIUM_HIGH: 0.10,
        IncomeClass.MEDIUM: 0.50,
        IncomeClass.MEDIUM_LOW: 0.25,
        IncomeClass.LOW: 0.10
    }
    
    total_difference = 0
    
    for income_class in IncomeClass:
        count = class_counts[income_class]
        actual_pct = (count / num_assignments) * 100
        expected_pct = expected_probs[income_class] * 100
        difference = actual_pct - expected_pct
        total_difference += abs(difference)
        
        print(f"{income_class.value.title().replace('_', ' '):<15}{count:<8}{actual_pct:<11.2f}%{expected_pct:<11.2f}%{difference:+6.2f}%")
    
    print("-" * 60)
    print(f"Total absolute difference: {total_difference:.2f}%")
    
    # Test equal probabilities fallback
    print("\n=== Testing Equal Probabilities Fallback ===")
    
    equal_assignments = []
    
    for _ in range(num_assignments):
        assigned_class, payoff = DistributionGenerator.calculate_payoff(
            test_distribution, 
            probabilities=None,  # This should trigger equal probabilities
            random_gen=test_random
        )
        equal_assignments.append(assigned_class)
    
    equal_counts = Counter(equal_assignments)
    
    print("Results with equal probabilities:")
    print("Class".ljust(15) + "Count".ljust(8) + "Actual %".ljust(12) + "Expected %".ljust(12) + "Difference")
    print("-" * 60)
    
    expected_equal = 20.0  # 100% / 5 classes = 20% each
    
    for income_class in IncomeClass:
        count = equal_counts[income_class]
        actual_pct = (count / num_assignments) * 100
        difference = actual_pct - expected_equal
        
        print(f"{income_class.value.title().replace('_', ' '):<15}{count:<8}{actual_pct:<11.2f}%{expected_equal:<11.2f}%{difference:+6.2f}%")
    
    # Verify all 5 classes are present
    print(f"\n=== Verification ===")
    print(f"Number of distinct income classes: {len(IncomeClass)}")
    print(f"Classes found in weighted test: {len(class_counts)}")
    print(f"Classes found in equal test: {len(equal_counts)}")
    print(f"All 5 classes working: {'✓' if len(class_counts) == 5 and len(equal_counts) == 5 else '✗'}")

if __name__ == "__main__":
    test_5_class_distribution()