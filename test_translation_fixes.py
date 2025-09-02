#!/usr/bin/env python3
"""
Test script to validate translation fixes for Mandarin and Spanish experiments.
Tests that previously missing translation keys can now be accessed properly.
"""

import json
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.language_manager import LanguageManager, SupportedLanguage

def test_translation_key_access():
    """Test that specific translation keys can be accessed for all languages."""
    print("="*60)
    print("TESTING TRANSLATION KEY ACCESS")
    print("="*60)
    
    # Keys that were previously missing
    critical_keys = [
        "memory_outcomes.applied_principle_round",
        "phase2_no_consensus", 
        "counterfactual_insights.maximin_payoffs_best",
        "counterfactual_insights.maximin_payoffs_worst",
        "counterfactual_insights.floor_constraint_payoffs_best",
        "counterfactual_insights.floor_constraint_payoffs_worst",
        "phase2_counterfactual_insights_best_more",
        "phase2_counterfactual_insights_best_same", 
        "phase2_counterfactual_insights_worst_more",
        "phase2_counterfactual_insights_worst_same"
    ]
    
    language_enums = [SupportedLanguage.ENGLISH, SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN]
    results = {}
    
    for language_enum in language_enums:
        language = language_enum.value
        print(f"\n--- Testing {language} ---")
        results[language] = {}
        
        try:
            # Initialize language manager
            lang_manager = LanguageManager()
            lang_manager.set_language(language_enum)
            
            for key in critical_keys:
                try:
                    # Test key access
                    value = lang_manager.get(key, round_number=1)  # Provide format args for keys that need them
                    if value and value != key:  # Successful translation
                        results[language][key] = "✅ FOUND"
                        print(f"✅ {key}: {value[:50]}..." if len(str(value)) > 50 else f"✅ {key}: {value}")
                    else:
                        results[language][key] = "❌ NOT_FOUND"
                        print(f"❌ {key}: NOT FOUND")
                        
                except Exception as e:
                    results[language][key] = f"❌ ERROR: {str(e)}"
                    print(f"❌ {key}: ERROR - {str(e)}")
                    
        except Exception as e:
            print(f"❌ Failed to initialize LanguageManager for {language}: {e}")
            
    return results

def test_translation_completeness():
    """Test completeness of translation files by comparing key counts."""
    print("\n" + "="*60)
    print("TESTING TRANSLATION COMPLETENESS")
    print("="*60)
    
    translation_files = {
        "English": "translations/english_prompts.json",
        "Spanish": "translations/spanish_prompts.json", 
        "Mandarin": "translations/mandarin_prompts.json"
    }
    
    def count_keys(data, prefix=""):
        """Recursively count all keys in nested dictionary."""
        count = 0
        for key, value in data.items():
            if isinstance(value, dict):
                count += count_keys(value, f"{prefix}{key}.")
            else:
                count += 1
        return count
    
    key_counts = {}
    
    for lang, file_path in translation_files.items():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                key_counts[lang] = count_keys(data)
                print(f"{lang}: {key_counts[lang]} total translation keys")
        except Exception as e:
            print(f"❌ Error reading {lang} translations: {e}")
            key_counts[lang] = 0
    
    # Check for consistency
    english_count = key_counts.get("English", 0)
    print(f"\nCompleteness check (compared to English baseline of {english_count} keys):")
    
    for lang, count in key_counts.items():
        if lang == "English":
            continue
        percentage = (count / english_count * 100) if english_count > 0 else 0
        status = "✅" if percentage >= 95 else "⚠️" if percentage >= 80 else "❌"
        print(f"{status} {lang}: {count} keys ({percentage:.1f}% of English)")
        
    return key_counts

def test_specific_error_keys():
    """Test the specific keys that were causing errors."""
    print("\n" + "="*60) 
    print("TESTING SPECIFIC ERROR-CAUSING KEYS")
    print("="*60)
    
    # These were the exact keys mentioned in the error
    error_keys = [
        "memory_outcomes.applied_principle_round",
        "phase2_no_consensus",
        "prompts.phase2_no_consensus"  # Check if this is the correct path
    ]
    
    language_enums = [SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN]  # English was working
    
    for language_enum in language_enums:
        language = language_enum.value
        print(f"\n--- Testing {language} Error Keys ---")
        try:
            lang_manager = LanguageManager()
            lang_manager.set_language(language_enum)
            
            for key in error_keys:
                try:
                    value = lang_manager.get(key, round_number=1)
                    print(f"✅ {key}: {value}")
                except Exception as e:
                    print(f"❌ {key}: {str(e)}")
                    
        except Exception as e:
            print(f"❌ Failed to test {language}: {e}")

def main():
    """Run all translation tests."""
    print("FROHLICH EXPERIMENT - TRANSLATION FIXES VALIDATION")
    print("="*60)
    print("Testing translation fixes for Mandarin and Spanish experiments")
    print("Focus: Previously missing keys that caused experiment failures")
    
    try:
        # Test 1: Key access
        key_results = test_translation_key_access()
        
        # Test 2: Translation completeness
        completeness_results = test_translation_completeness()
        
        # Test 3: Specific error keys
        test_specific_error_keys()
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY OF TRANSLATION FIXES")
        print("="*60)
        
        # Count successes and failures
        for language in ["Spanish", "Mandarin"]:
            if language in key_results:
                total_keys = len(key_results[language])
                successful_keys = sum(1 for status in key_results[language].values() if "✅" in status)
                success_rate = (successful_keys / total_keys * 100) if total_keys > 0 else 0
                
                status_symbol = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
                print(f"{status_symbol} {language}: {successful_keys}/{total_keys} critical keys working ({success_rate:.1f}%)")
        
        print(f"\n{'✅ TRANSLATION FIXES VALIDATION COMPLETED' if all('❌' not in str(results) for results in key_results.values()) else '⚠️ SOME ISSUES FOUND - SEE DETAILS ABOVE'}")
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)