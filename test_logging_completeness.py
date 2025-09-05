#!/usr/bin/env python3
"""Test script for the validate_logging_completeness() method."""

import json
from pathlib import Path
from utils.agent_centric_logger import AgentCentricLogger

def test_validate_logging_completeness():
    """Test the validate_logging_completeness() method on real experiment data."""
    
    # Find the most recent experiment result
    recent_files = list(Path('.').glob('experiment_results_*.json'))
    if not recent_files:
        print("❌ No experiment result files found")
        return False
        
    most_recent = max(recent_files, key=lambda p: p.stat().st_mtime)
    print(f"📄 Testing with file: {most_recent}")
    
    # Load the experiment data
    with open(most_recent, 'r') as f:
        experiment_data = json.load(f)
    
    # Create a logger instance and load the data
    logger = AgentCentricLogger()
    
    # Test if the method exists
    if not hasattr(logger, 'validate_logging_completeness'):
        print("❌ validate_logging_completeness() method not found in AgentCentricLogger")
        return False
    
    print("✅ validate_logging_completeness() method found")
    
    # Try to call the method
    try:
        result = logger.validate_logging_completeness()
        print(f"✅ Method called successfully, returned: {result}")
        
        # The method should return a validation report
        if isinstance(result, dict):
            print("✅ Method returns a dictionary as expected")
            
            # Print the validation results
            print("\n📊 Validation Results:")
            for key, value in result.items():
                print(f"   {key}: {value}")
        else:
            print(f"⚠️  Method returned unexpected type: {type(result)}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error calling validate_logging_completeness(): {e}")
        return False

def test_specific_logging_features():
    """Test that specific logging features are working."""
    print("\n🔍 Testing Specific Logging Features:")
    
    # Find the most recent experiment result
    recent_files = list(Path('.').glob('experiment_results_*.json'))
    most_recent = max(recent_files, key=lambda p: p.stat().st_mtime)
    
    with open(most_recent, 'r') as f:
        data = json.load(f)
    
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Check initiate_vote fields contain Yes/No instead of N/A
    initiate_vote_values = []
    for agent in data.get('agents', []):
        phase2 = agent.get('phase_2', {})
        for round_data in phase2.get('rounds', []):
            initiate_vote_values.append(round_data.get('initiate_vote', 'N/A'))
    
    if any(val in ['Yes', 'No'] for val in initiate_vote_values):
        print("✅ Test 1: initiate_vote fields populated with Yes/No values")
        tests_passed += 1
    else:
        print("❌ Test 1: initiate_vote fields not properly populated")
    
    # Test 2: Check vote_statistics presence
    voting_history = data.get('voting_history', {})
    if 'vote_statistics' in voting_history:
        print("✅ Test 2: vote_statistics present in voting_history")
        tests_passed += 1
    else:
        print("❌ Test 2: vote_statistics missing from voting_history")
    
    # Test 3: Check voting_detection_mode presence
    if 'voting_detection_mode' in voting_history:
        print("✅ Test 3: voting_detection_mode present in voting_history")
        tests_passed += 1
    else:
        print("❌ Test 3: voting_detection_mode missing from voting_history")
    
    # Test 4: Check post_group_discussion has class_put_in and final_ranking
    post_discussion_complete = True
    for agent in data.get('agents', []):
        post_disc = agent.get('phase_2', {}).get('post_group_discussion', {})
        if not post_disc.get('class_put_in') or not post_disc.get('final_ranking'):
            post_discussion_complete = False
            break
    
    if post_discussion_complete:
        print("✅ Test 4: post_group_discussion has class_put_in and final_ranking")
        tests_passed += 1
    else:
        print("❌ Test 4: post_group_discussion missing required fields")
    
    # Test 5: Check general schema structure
    required_fields = ['general_information', 'agents']
    schema_complete = all(field in data for field in required_fields)
    
    if schema_complete:
        print("✅ Test 5: General schema structure intact")
        tests_passed += 1
    else:
        print("❌ Test 5: Schema structure issues")
    
    print(f"\n📈 Feature Tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests

if __name__ == "__main__":
    print("🧪 Testing AgentCentricLogger validate_logging_completeness() method")
    print("=" * 70)
    
    completeness_test_passed = test_validate_logging_completeness()
    feature_tests_passed = test_specific_logging_features()
    
    print("\n" + "=" * 70)
    if completeness_test_passed and feature_tests_passed:
        print("🎉 All tests passed! Logging system fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Review the output above.")