#!/usr/bin/env python3
"""
Generate English baseline translation file from extracted prompts.

This creates the english_prompts.json file that serves as the baseline
for the language manager system.
"""

import json
import os
from prompts_for_translation import *

def generate_english_prompts():
    """Generate the English prompts JSON file."""
    
    english_prompts = {
        # Core experiment explanation
        "experiment_explanation": {
            "broad_experiment_explanation": BROAD_EXPERIMENT_EXPLANATION
        },
        
        # Phase 1 instructions
        "phase1_instructions": {
            "round0_initial_ranking": PHASE1_ROUND0_INSTRUCTIONS,
            "round_neg1_detailed_explanation": PHASE1_ROUND_NEG1_INSTRUCTIONS,
            "rounds1_4_principle_application": PHASE1_ROUNDS1_4_INSTRUCTIONS_TEMPLATE,
            "round5_final_ranking": PHASE1_ROUND5_INSTRUCTIONS
        },
        
        # Phase 2 instructions
        "phase2_instructions": {
            "group_discussion": PHASE2_DISCUSSION_INSTRUCTIONS_TEMPLATE
        },
        
        # Utility agent prompts
        "utility_agent_prompts": {
            "parser_instructions": PARSER_AGENT_INSTRUCTIONS,
            "validator_instructions": VALIDATOR_AGENT_INSTRUCTIONS,
            "parse_principle_choice": PARSE_PRINCIPLE_CHOICE_PROMPT_TEMPLATE,
            "parse_principle_ranking": PARSE_PRINCIPLE_RANKING_PROMPT_TEMPLATE,
            "vote_detection": VOTE_DETECTION_PROMPT_TEMPLATE,
            "constraint_re_prompt": CONSTRAINT_RE_PROMPT_TEMPLATE,
            "format_improvement_choice": FORMAT_IMPROVEMENT_PRINCIPLE_CHOICE_PROMPT_TEMPLATE,
            "format_improvement_ranking": FORMAT_IMPROVEMENT_PRINCIPLE_RANKING_PROMPT_TEMPLATE
        },
        
        # System messages
        "system_messages": {
            "error_messages": ERROR_MESSAGES,
            "success_messages": SUCCESS_MESSAGES,
            "status_messages": STATUS_MESSAGES
        },
        
        # Context formatting
        "context_formatting": {
            "memory_section_format": MEMORY_SECTION_FORMAT,
            "memory_empty_placeholder": MEMORY_EMPTY_PLACEHOLDER,
            "context_info_format": CONTEXT_INFO_FORMAT
        },
        
        # Principle and level names
        "names_and_labels": {
            "justice_principle_names": JUSTICE_PRINCIPLE_NAMES,
            "certainty_level_names": CERTAINTY_LEVEL_NAMES,
            "phase_names": PHASE_NAMES
        },
        
        # Default/fallback text
        "fallback": {
            "default_phase_instructions": DEFAULT_PHASE_INSTRUCTIONS
        }
    }
    
    return english_prompts

def main():
    """Generate and save English prompts file."""
    
    # Create translations directory if it doesn't exist
    os.makedirs("translations", exist_ok=True)
    
    # Generate English prompts
    english_prompts = generate_english_prompts()
    
    # Save to JSON file
    with open("translations/english_prompts.json", 'w', encoding='utf-8') as f:
        json.dump(english_prompts, f, ensure_ascii=False, indent=2)
    
    print("Generated English baseline translation file: translations/english_prompts.json")
    print("The language manager system is now ready to use with English as the default language.")

if __name__ == "__main__":
    main()