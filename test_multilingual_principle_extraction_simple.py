#!/usr/bin/env python3
"""Simple test script to verify multilingual principle extraction fixes."""

from experiment_agents.utility_agent import UtilityAgent

def test_multilingual_parsing():
    """Test that the _parse_llm_principle_response handles multilingual anchors."""
    
    # Create a utility agent instance (without initialization)
    utility_agent = UtilityAgent("test")
    
    # Test cases with different language anchors
    test_cases = [
        # English
        ("PRINCIPLE_DETECTED: maximizing_floor | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
        ("PRINCIPLE_DETECTED: maximizing_average | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
        
        # Spanish
        ("PRINCIPIO_DETECTADO: maximizar_piso | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
        ("PRINCIPIO_DETECTADO: maximizar_promedio | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
        
        # Mandarin
        ("检测到原则：最大化底线 | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
        ("检测到原则：最大化平均 | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
        
        # Test canonical forms
        ("PRINCIPLE_DETECTED: maximizing_average_floor_constraint | constraint: $15000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
        ("PRINCIPIO_DETECTADO: maximizar_promedio_restriccion_piso | constraint: $15000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
        ("检测到原则：最大化平均底线约束 | constraint: $15000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
    ]
    
    print("Testing multilingual principle extraction...")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    for llm_response, expected_principle in test_cases:
        print(f"\nTesting: {llm_response[:50]}...")
        
        try:
            # Test the parsing method directly
            result = utility_agent._parse_llm_principle_response(llm_response)
            
            if result and result.get('principle') == expected_principle:
                print(f"✓ Successfully parsed: {result['principle']}")
                passed += 1
            else:
                print(f"✗ Failed - Expected: {expected_principle}, Got: {result.get('principle') if result else None}")
                failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1
    
    print("\n" + "-" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("Test completed!")

if __name__ == "__main__":
    test_multilingual_parsing()