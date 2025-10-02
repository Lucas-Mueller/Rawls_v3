# Plan: Optimize Two-Phase Experiment Explanation in Memory Updates

## Problem
The two-phase experiment explanation text is currently included in **every memory update prompt**, even though it only needs to be shown once (at the first memory update including that update call).

**Current repetitive text:**
```
"You are participating in an experiment studying principles of justice and income distribution.

The experiment has two main phases:

PHASE 1: You will individually learn about and apply four different principles of justice to income distributions...

PHASE 2: You will join a group discussion to reach consensus on which principle of justice the group should adopt...

Throughout the experiment, engage thoughtfully with the principles and other participants."
```

## Current State

### 1. Context Prompts (Already Optimized)
- Config parameter `include_experiment_explanation_each_turn` (defaults to `False`)
- Only shows explanation on first turn per phase
- **No changes needed here**

### 2. Memory Update Prompts (Need Optimization)
The explanation is hardcoded in these prompt templates (in `translations/english_prompts.json`, `spanish_prompts.json`, `mandarin_prompts.json`):

- `memory_memory_update_prompt` (line 90)
- `memory_narrative_update_prompt` (line 92)
- `memory_memory_update_prompt_first_round` (line 95)
- `memory_narrative_update_prompt_first_round` (line 97)
- Plus their `_no_recent_activity` variants (lines 91, 93, 96, 98)

## Solution Approach

### Step 1: Track First Memory Update State
**File**: `models/experiment_types.py` - `ParticipantContext` class

Add field:
```python
has_received_experiment_explanation: bool = False
```

### Step 2: Create Prompt Templates Without Explanation
**Files**: All 3 translation JSON files

For each of the 8 memory update prompts, create a variant that **excludes** the two-phase explanation block. Keep everything else identical.

Example naming:
- `memory_memory_update_prompt` → `memory_memory_update_prompt_without_explanation`
- `memory_narrative_update_prompt` → `memory_narrative_update_prompt_without_explanation`
- etc.

### Step 3: Update Memory Manager Logic
**File**: `utils/memory_manager.py` - `_create_memory_update_prompt()` method

Modify template selection logic (around line 283-317):
1. Check if `context.has_received_experiment_explanation` is `False`
2. If False: Use existing templates (with explanation) and set flag to `True`
3. If True: Use new `_without_explanation` templates

### Step 4: Pass Context to Memory Manager
**File**: Check where `prompt_agent_for_memory_update()` is called

Ensure `context` parameter is passed so we can check/update the flag.

## Implementation Steps

1. **Add tracking field** to `ParticipantContext` in `models/experiment_types.py`
2. **Create new prompt templates** in all 3 language JSON files (8 templates × 3 languages = 24 new prompts)
3. **Update `_create_memory_update_prompt()`** in `utils/memory_manager.py` to:
   - Accept `context` parameter
   - Check the flag
   - Select appropriate template
4. **Update `prompt_agent_for_memory_update()`** to:
   - Accept and use `context` parameter
   - Update flag after first memory update with explanation
5. **Update all call sites** to pass `context`
6. **Test** with a sample experiment to verify explanation shows exactly once

## Files to Modify

1. `models/experiment_types.py` - Add tracking field
2. `translations/english_prompts.json` - Add 8 new templates
3. `translations/spanish_prompts.json` - Add 8 new templates
4. `translations/mandarin_prompts.json` - Add 8 new templates
5. `utils/memory_manager.py` - Update template selection logic
6. Call sites of `prompt_agent_for_memory_update()` - Pass context

## Expected Outcome

- First memory update: Shows full two-phase explanation
- All subsequent memory updates: No explanation (cleaner, less repetitive)
- Reduces token usage and cognitive load
- Maintains necessary information when it matters most
