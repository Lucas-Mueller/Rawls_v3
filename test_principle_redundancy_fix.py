#!/usr/bin/env python3
"""
Test script to verify that principle information redundancy has been eliminated.

This script verifies that principle descriptions only appear in the 
unified_ranking_prompt_template and not in other system context templates.
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.language_manager import LanguageManager, SupportedLanguage
from models import ExperimentPhase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_principle_redundancy_elimination():
    """Test that principle information is only in unified_ranking_prompt_template"""
    
    print("=== Testing Principle Information Redundancy Elimination ===\n")
    
    # Create language manager
    language_manager = LanguageManager()
    language_manager.set_language(SupportedLanguage.ENGLISH)
    
    # Test 1: Check that phase1_application_round no longer contains principle_list_simple
    print("Test 1: Checking phase1_application_round template...")
    phase1_app_template = language_manager.get("prompts.phase1_application_round", 
                                               round_number=1, distributions_table="[TABLE]")
    
    if "principle_list_simple" in phase1_app_template:
        print("❌ FAIL: phase1_application_round still contains {principle_list_simple} placeholder")
        return False
    elif "Maximizing Floor Income" in phase1_app_template:
        print("❌ FAIL: phase1_application_round contains principle descriptions")
        return False
    else:
        print("✅ PASS: phase1_application_round does not contain principle information")
    
    # Test 2: Check that phase1_round0_initial_ranking no longer contains principle_list_detailed
    print("\nTest 2: Checking phase1_round0_initial_ranking template...")
    phase1_initial_template = language_manager.get("prompts.phase1_round0_initial_ranking", 
                                                   randomized_example="[EXAMPLE]")
    
    if "principle_list_detailed" in phase1_initial_template:
        print("❌ FAIL: phase1_round0_initial_ranking still contains {principle_list_detailed} placeholder")
        return False
    elif "Maximizing Floor Income" in phase1_initial_template:
        print("❌ FAIL: phase1_round0_initial_ranking contains principle descriptions")
        return False
    else:
        print("✅ PASS: phase1_round0_initial_ranking does not contain principle information")
    
    # Test 3: Check that phase1_rounds1_4_principle_application no longer contains principle_list_simple
    print("\nTest 3: Checking phase1_rounds1_4_principle_application template...")
    phase1_rounds_template = language_manager.get("prompts.phase1_rounds1_4_principle_application", 
                                                  round_number=2)
    
    if "principle_list_simple" in phase1_rounds_template:
        print("❌ FAIL: phase1_rounds1_4_principle_application still contains {principle_list_simple} placeholder")
        return False
    elif "Maximizing Floor Income" in phase1_rounds_template:
        print("❌ FAIL: phase1_rounds1_4_principle_application contains principle descriptions")
        return False
    else:
        print("✅ PASS: phase1_rounds1_4_principle_application does not contain principle information")
    
    # Test 4: Verify that unified_ranking_prompt_template DOES contain principle information
    print("\nTest 4: Checking unified_ranking_prompt_template contains principle information...")
    unified_template = language_manager.get("unified_ranking_prompt_template", 
                                           context_description="Test ranking",
                                           additional_instructions="")
    
    if "Maximizing Floor Income" not in unified_template:
        print("❌ FAIL: unified_ranking_prompt_template should contain principle descriptions")
        return False
    elif "Maximizing Average Income" not in unified_template:
        print("❌ FAIL: unified_ranking_prompt_template should contain all principle descriptions")
        return False
    else:
        print("✅ PASS: unified_ranking_prompt_template contains principle information as expected")
    
    # Test 5: Test context formatting doesn't inject principle information
    print("\nTest 5: Testing system context formatting...")
    
    # Mock experiment config
    class MockExperimentConfig:
        include_experiment_explanation_each_turn = True
    
    mock_config = MockExperimentConfig()
    
    # Test context info formatting
    context_info = language_manager.format_context_info(
        name="TestAgent",
        role_description="Test Role",
        bank_balance=100.0,
        phase="Phase 1", 
        round_number=1,
        formatted_memory="Test memory",
        personality="Test personality",
        phase_instructions="Test instructions",
        experiment_config=mock_config
    )
    
    # Check that no principle descriptions leaked into system context
    if "Maximizing Floor Income" in context_info:
        print("❌ FAIL: System context contains principle descriptions")
        print("Context snippet containing principle info:")
        lines = context_info.split('\n')
        for i, line in enumerate(lines):
            if "Maximizing Floor Income" in line:
                print(f"  Line {i}: {line}")
        return False
    else:
        print("✅ PASS: System context does not contain principle descriptions")
    
    print("\n=== ALL TESTS PASSED ===")
    print("✅ Principle information redundancy has been successfully eliminated!")
    print("✅ Principle descriptions only appear in unified_ranking_prompt_template")
    return True

def test_multilingual_support():
    """Test that the fix works across all supported languages"""
    
    print("\n=== Testing Multilingual Support ===\n")
    
    languages_to_test = [
        (SupportedLanguage.ENGLISH, "Maximizing Floor Income"),
        (SupportedLanguage.SPANISH, "Maximizar los ingresos mínimos"),
        (SupportedLanguage.MANDARIN, "最低收入最大化")
    ]
    
    for language, principle_example in languages_to_test:
        print(f"Testing {language.value}...")
        language_manager = LanguageManager()
        language_manager.set_language(language)
        
        # Test phase1_application_round doesn't contain principles
        phase1_app_template = language_manager.get("prompts.phase1_application_round", 
                                                   round_number=1, distributions_table="[TABLE]")
        
        if principle_example in phase1_app_template:
            print(f"❌ FAIL: {language.value} phase1_application_round contains principle descriptions")
            return False
        
        # Test unified template DOES contain principles
        unified_template = language_manager.get("unified_ranking_prompt_template", 
                                               context_description="Test ranking",
                                               additional_instructions="")
        
        if principle_example not in unified_template:
            print(f"❌ FAIL: {language.value} unified_ranking_prompt_template missing principle descriptions")
            return False
        
        print(f"✅ PASS: {language.value} redundancy eliminated correctly")
    
    print("\n✅ All languages pass redundancy elimination test")
    return True

if __name__ == "__main__":
    print("Testing principle information redundancy elimination...")
    
    try:
        success1 = test_principle_redundancy_elimination()
        success2 = test_multilingual_support()
        
        if success1 and success2:
            print("\n🎉 ALL TESTS PASSED! The principle redundancy fix is working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please check the output above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)