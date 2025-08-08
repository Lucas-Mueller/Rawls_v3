"""
All prompts and user-facing text for the Frohlich Experiment system that need translation.
This file contains all English text that agents receive as input from the system.

MISSING TRANSLATIONS IDENTIFIED FROM MULTILINGUAL ISSUE ANALYSIS
================================================================
These are the hardcoded strings causing English text to appear even when 
language is set to Mandarin or Spanish. They need to be translated and
integrated with the language_manager.

Output files after running translate_prompts.py:
- translations/missing_english_prompts.json  (backup current English)
- translations/missing_spanish_prompts.json (new Spanish translations)  
- translations/missing_mandarin_prompts.json (new Mandarin translations)
"""

# =============================================================================
# PHASE 1 MANAGER - HARDCODED STRINGS (core/phase1_manager.py)
# =============================================================================

# Counterfactual table header and explanation
COUNTERFACTUAL_TABLE_HEADER = """This assigns you to the following income class: {assigned_class}

For each principle of justice the following income would be received by each member of this income class. You will receive a payoff of $1 for each $10,000 of income.

Principle of Justice                          Income    Payoff"""

# Justice principle display names
PRINCIPLE_DISPLAY_NAMES = {
    "maximizing_floor": "Maximizing the floor",
    "maximizing_average": "Maximizing the average", 
    "maximizing_average_floor_constraint": "Maximizing the average with a floor constraint",
    "maximizing_average_range_constraint": "Maximizing the average with a range constraint"
}

# Memory round content template
ROUND_MEMORY_TEMPLATE = """Prompt: {application_prompt}
Your Response: {text_response}
Your Choice: {chosen_principle_display}

ROUND {round_num} OUTCOME:
{counterfactual_table}

Your actual earnings this round: ${earnings:.2f}
Your total earnings so far: ${total_earnings:.2f}"""

# Detailed explanation of principles (THE MAIN ISSUE REPORTED)
DETAILED_PRINCIPLES_EXPLANATION = """Here is how each justice principle would be applied to example income distributions:

Example Distributions:
| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |
|--------------|---------|---------|---------|----------|
| High         | $32,000 | $28,000 | $31,000 | $21,000 |
| Medium high  | $27,000 | $22,000 | $24,000 | $20,000 |
| Medium       | $24,000 | $20,000 | $21,000 | $19,000 |
| Medium low   | $13,000 | $17,000 | $16,000 | $16,000 |
| Low          | $12,000 | $13,000 | $14,000 | $15,000 |

How each principle would choose:
- **Maximizing the floor**: Would choose Distribution 4 (highest low income: $15,000)
- **Maximizing average**: Would choose Distribution 1 (highest average: $21,600)
- **Maximizing average with floor constraint ≤ $13,000**: Would choose Distribution 1
- **Maximizing average with floor constraint ≤ $14,000**: Would choose Distribution 3  
- **Maximizing average with range constraint ≥ $20,000**: Would choose Distribution 1
- **Maximizing average with range constraint ≥ $15,000**: Would choose Distribution 2

Study these examples to understand how each principle works in practice."""

# Post-explanation ranking prompt
POST_EXPLANATION_RANKING_PROMPT = """After learning how each justice principle is applied to income distributions, please rank the four principles again from best (1) to worst (4):

1. **Maximizing the floor income**: Choose the distribution that maximizes the lowest income
2. **Maximizing the average income**: Choose the distribution that maximizes the average income  
3. **Maximizing the average income with a floor constraint**: Maximize average while ensuring minimum income
4. **Maximizing the average income with a range constraint**: Maximize average while limiting income gap

Consider:
- How each principle works in practice based on the examples you just studied
- Whether the detailed explanations changed your understanding
- Your preference for how income should be distributed

Indicate your overall certainty level for the entire ranking: very_unsure, unsure, no_opinion, sure, or very_sure.

Provide your ranking with reasoning, noting any changes from your initial ranking and why."""

# Initial ranking prompt template
INITIAL_RANKING_PROMPT_TEMPLATE = """This is your first time ranking these four principles of justice:

1. **Maximizing the floor income**: Choose the distribution that maximizes the lowest income
2. **Maximizing the average income**: Choose the distribution that maximizes the average income  
3. **Maximizing the average income with a floor constraint**: Maximize average while ensuring minimum income
4. **Maximizing the average income with a range constraint**: Maximize average while limiting income gap

Please rank the principles from best (1) to worst (4) based on your initial understanding.

Indicate your overall certainty level for the entire ranking: very_unsure, unsure, no_opinion, sure, or very_sure.

Provide your ranking with clear reasoning for your preferences."""

# =============================================================================
# DISTRIBUTION GENERATOR - HARDCODED STRINGS (core/distribution_generator.py)
# =============================================================================

# Distribution table header
DISTRIBUTIONS_TABLE_HEADER = "Income Distributions:\n\n"
DISTRIBUTIONS_TABLE_COLUMN_HEADER = "| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |\n"
DISTRIBUTIONS_TABLE_SEPARATOR = "|--------------|---------|---------|---------|----------|\n"

# Income class names in distribution tables  
INCOME_CLASS_NAMES = {
    "high": "High",
    "medium_high": "Medium high", 
    "medium": "Medium",
    "medium_low": "Medium low",
    "low": "Low"
}

# Base principle names used in formatting
BASE_PRINCIPLE_NAMES = {
    "maximizing_floor": "Maximizing the floor",
    "maximizing_average": "Maximizing the average",
    "maximizing_average_floor_constraint": "Maximizing the average with a floor constraint",
    "maximizing_average_range_constraint": "Maximizing the average with a range constraint"
}

# =============================================================================  
# PHASE 2 MANAGER - HARDCODED STRINGS (core/phase2_manager.py)
# =============================================================================

# Income class assignment descriptions
INCOME_CLASS_ASSIGNMENT_NAMES = {
    "high": "High",
    "medium_high": "Medium high",
    "medium": "Medium", 
    "medium_low": "Medium low",
    "low": "Low"
}

# Default constraint specification
DEFAULT_CONSTRAINT_SPECIFICATION = "Not specified"

# =============================================================================
# UTILITY AGENT - REMAINING HARDCODED STRINGS (experiment_agents/utility_agent.py)  
# =============================================================================

# Agent names for internal agents
PARSER_AGENT_NAME = "Response Parser"
VALIDATOR_AGENT_NAME = "Response Validator"

# Validation error messages
VALIDATION_ERROR_INCOMPLETE_RANKING = "Incomplete ranking - missing principles or invalid ranks"

# =============================================================================
# ADDITIONAL SYSTEM STRINGS FOUND IN ANALYSIS
# =============================================================================

# Common formatting strings
EARNINGS_DISPLAY_FORMAT = "Your actual earnings this round: ${earnings:.2f}"
TOTAL_EARNINGS_FORMAT = "Your total earnings so far: ${total_earnings:.2f}"
BANK_BALANCE_FORMAT = "Bank Balance: ${bank_balance:.2f}"

# Round and phase identifiers  
ROUND_OUTCOME_HEADER = "ROUND {round_num} OUTCOME:"
CURRENT_PHASE_FORMAT = "Current Phase: {phase}"
ROUND_NUMBER_FORMAT = "Round: {round_number}"

# Class assignment template
CLASS_ASSIGNMENT_FORMAT = "This assigns you to the following income class: {assigned_class}"

# Constraint examples for re-prompting
FLOOR_CONSTRAINT_EXAMPLE = "Floor constraint: \"I choose maximizing average with a floor constraint of $15,000\""
RANGE_CONSTRAINT_EXAMPLE = "Range constraint: \"I choose maximizing average with a range constraint of $20,000\""

# =============================================================================
# TRANSLATION PROMPT CATEGORIES (UPDATED)
# =============================================================================

TRANSLATION_CATEGORIES = {
    "phase1_manager_strings": [
        "COUNTERFACTUAL_TABLE_HEADER",
        "PRINCIPLE_DISPLAY_NAMES", 
        "ROUND_MEMORY_TEMPLATE",
        "DETAILED_PRINCIPLES_EXPLANATION",
        "POST_EXPLANATION_RANKING_PROMPT",
        "INITIAL_RANKING_PROMPT_TEMPLATE"
    ],
    "distribution_generator_strings": [
        "DISTRIBUTIONS_TABLE_HEADER",
        "DISTRIBUTIONS_TABLE_COLUMN_HEADER", 
        "DISTRIBUTIONS_TABLE_SEPARATOR",
        "INCOME_CLASS_NAMES",
        "BASE_PRINCIPLE_NAMES"
    ],
    "phase2_manager_strings": [
        "INCOME_CLASS_ASSIGNMENT_NAMES",
        "DEFAULT_CONSTRAINT_SPECIFICATION"
    ],
    "utility_agent_strings": [
        "PARSER_AGENT_NAME",
        "VALIDATOR_AGENT_NAME", 
        "VALIDATION_ERROR_INCOMPLETE_RANKING"
    ],
    "system_formatting_strings": [
        "EARNINGS_DISPLAY_FORMAT",
        "TOTAL_EARNINGS_FORMAT",
        "BANK_BALANCE_FORMAT",
        "ROUND_OUTCOME_HEADER", 
        "CURRENT_PHASE_FORMAT",
        "ROUND_NUMBER_FORMAT",
        "CLASS_ASSIGNMENT_FORMAT",
        "FLOOR_CONSTRAINT_EXAMPLE",
        "RANGE_CONSTRAINT_EXAMPLE"
    ]
}

# =============================================================================
# INSTRUCTION FOR DEVELOPER
# =============================================================================

DEVELOPER_NOTE = """
NEXT STEPS:

1. Run the translation script to generate missing translations:
   ```bash
   export DEEPL_API_KEY="your_key_here"
   python translate_prompts.py
   ```

2. This will create these files:
   - translations/missing_english_prompts.json   (current English baseline)
   - translations/missing_spanish_prompts.json  (Spanish translations)
   - translations/missing_mandarin_prompts.json (Mandarin translations)

3. After translations are generated, the following files need to be updated to use 
   these translations via the language_manager:
   
   - core/phase1_manager.py (add language_manager import and replace hardcoded strings)
   - core/distribution_generator.py (add language_manager import and replace hardcoded strings) 
   - core/phase2_manager.py (add language_manager import and replace hardcoded strings)
   - experiment_agents/utility_agent.py (replace remaining hardcoded strings)

4. The existing translation files will need to be merged with the new ones:
   - translations/english_prompts.json (merge with missing_english_prompts.json)
   - translations/spanish_prompts.json (merge with missing_spanish_prompts.json)  
   - translations/mandarin_prompts.json (merge with missing_mandarin_prompts.json)

5. Update utils/language_manager.py to handle the new prompt keys if needed.

This addresses the core issue where English text appears even when language is set 
to Mandarin or Spanish - these are the missing translations that need to be integrated.
"""