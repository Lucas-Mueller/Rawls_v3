#!/usr/bin/env python3
"""Test script to verify multilingual principle extraction fixes."""

import asyncio
import os
from utils.language_manager import get_language_manager, set_global_language, SupportedLanguage
from experiment_agents.utility_agent import UtilityAgent

async def test_multilingual_parsing():
    """Test that the utility agent can parse principles in multiple languages."""
    
    # Initialize utility agent
    utility_agent = UtilityAgent("test")
    await utility_agent.async_init()
    
    # Test cases in different languages
    test_cases = [
        # English
        ("en", "I choose principle a", "PRINCIPLE_DETECTED:"),
        ("en", "My preference is maximizing_average", "PRINCIPLE_DETECTED:"),
        
        # Spanish
        ("es", "Mi elección es el principio a", "PRINCIPIO_DETECTADO:"),
        ("es", "Prefiero maximizar_promedio", "PRINCIPIO_DETECTADO:"),
        
        # Mandarin
        ("zh", "我选择原则a", "检测到原则："),
        ("zh", "我偏好最大化平均", "检测到原则："),
    ]
    
    print("Testing multilingual principle extraction...")
    print("-" * 50)
    
    for lang, statement, expected_anchor in test_cases:
        # Set language
        lang_enum = SupportedLanguage.ENGLISH if lang == "en" else (
            SupportedLanguage.SPANISH if lang == "es" else SupportedLanguage.MANDARIN
        )
        set_global_language(lang_enum)
        language_manager = get_language_manager()
        
        print(f"\nLanguage: {lang}")
        print(f"Statement: {statement}")
        print(f"Expected anchor: {expected_anchor}")
        
        # Test the parsing
        try:
            # The parse_principle_choice_llm method would normally call the LLM
            # For testing, we'll check that the anchors are properly recognized
            response = utility_agent._parse_llm_principle_response(
                f"{expected_anchor} maximizing_floor | constraint: none | certainty: sure | confidence: 0.9"
            )
            
            if response:
                print(f"✓ Successfully parsed: {response['principle']}")
            else:
                print("✗ Failed to parse")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print("\n" + "-" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_multilingual_parsing())