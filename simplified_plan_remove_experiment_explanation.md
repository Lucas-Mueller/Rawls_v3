# Simplified Plan: Remove Experiment Explanation During Ranking Tasks

## Problem
Participants get principle explanations **twice** during ranking tasks:
1. In system prompt via `{experiment_explanation}` 
2. In user prompt with detailed principle definitions

This creates unnecessary duplication and longer prompts.

## Simple Solution

### Step 1: Add Ranking Detection to Language Manager
Add a simple set of ranking prompt keys and modify `format_context_info()` to exclude experiment explanation when using these prompts.

**In `utils/language_manager.py`:**
```python
# Add at top of class
RANKING_PROMPT_KEYS = {
    'phase1_initial_ranking_prompt_template',
    'phase1_post_explanation_ranking_prompt', 
    'phase1_final_ranking_after_experience',
    'phase1_round5_final_ranking',
    'phase1_round0_initial_ranking',
    'phase2_final_ranking_prompt'
}

# Modify format_context_info method to accept optional prompt_key
def format_context_info(self, name, role_description, bank_balance, phase, 
                       round_number, formatted_memory, personality, 
                       phase_instructions, experiment_config=None, 
                       current_prompt_key=None):
    
    # Existing logic for first turn tracking...
    
    # Simple ranking detection - if it's a ranking prompt, skip experiment explanation
    if current_prompt_key in self.RANKING_PROMPT_KEYS:
        experiment_explanation = ""
    else:
        # Use existing logic for non-ranking tasks
        experiment_explanation = self.get_experiment_explanation() if include_explanation else ""
```

### Step 2: Pass Prompt Key When Needed
Find where ranking prompts are used and pass the prompt key to `format_context_info()`.

## Files That Need the Full Principle Explanations (Keep as User Prompts)

**English:**
- `phase1_initial_ranking_prompt_template` - Initial ranking with full definitions
- `phase1_post_explanation_ranking_prompt` - Post-learning ranking with definitions  
- `phase1_final_ranking_after_experience` - Final ranking with full definitions
- `phase1_round5_final_ranking` - Alternative final ranking (seems duplicate?)
- `phase2_final_ranking_prompt` - Phase 2 ranking with definitions

**Spanish:**
- `phase1_round0_initial_ranking` - Initial ranking  
- `phase1_round5_final_ranking` - Final ranking
- `phase1_final_ranking_after_experience` - Alternative final ranking (duplicate?)
- `phase2_final_ranking_prompt` - Phase 2 ranking

**Mandarin:**
- Same pattern as Spanish

## Expected Outcome
- **System prompts** during ranking: Just name, personality, bank balance, memory, phase info
- **User prompts** during ranking: Complete principle definitions and ranking instructions  
- **All other tasks**: Keep existing behavior with full experiment explanation in system prompt

## Key Principles
- **Simple**: One boolean check, no complex configuration
- **Targeted**: Only affects ranking tasks, everything else unchanged
- **No information loss**: Principle definitions remain complete in user prompts
- **Backward compatible**: Non-ranking tasks work exactly as before

## Note on Duplicate Prompts
Both English and Spanish seem to have duplicate final ranking prompts (`phase1_final_ranking_after_experience` and `phase1_round5_final_ranking`). This might need cleanup, but the ranking detection should handle both variants.