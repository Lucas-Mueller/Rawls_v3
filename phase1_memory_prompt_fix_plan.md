# Phase 1 Memory Prompt Fix Plan

## Problem Statement

The Phase 1 memory update prompts contain inaccurate instructions that reference non-existent context and provide confusing guidance to agents **during education/ranking phases**.

### Specific Issues

**Issue 1: Reference to "recent activity" that doesn't exist**
- The prompts state: "Besides your memory and your recent activity you will receive the outcome of your choice..."
- **Problem**: During Phase 1 education/ranking rounds, agents have NO recent activity with outcomes
- This creates confusion as agents are told to consider activity that hasn't occurred

**Issue 2: Instruction to analyze information not yet provided**
- The prompts state: "Please analyze and incorporate this information into your updated memory."
- **Problem**: This instruction appears BEFORE agents receive any outcomes during education/ranking
- Agents are being told to analyze information they haven't received yet

### Where This Problem Does vs Doesn't Occur

**Phase 1 stages where the text is WRONG (no outcomes exist):**
1. Initial ranking (round 0) - just ranking principles
2. Detailed explanation (round -1) - learning about principles
3. Post-explanation ranking (round 0) - ranking after learning
4. Final ranking (round 5) - ranking after all application rounds

**Phase 1 stages where the text is CORRECT (outcomes exist):**
- Application rounds 1-4 - agents make choices, receive class assignments and payoffs, see counterfactuals

### Root Cause

The memory manager (`utils/memory_manager.py`) currently uses the SAME templates for all Phase 1 memory updates, without distinguishing between education/ranking rounds (no outcomes) and application rounds (with outcomes).

## Files Affected

All three translation files must be updated:
1. `translations/english_prompts.json`
2. `translations/spanish_prompts.json`
3. `translations/mandarin_prompts.json`

## Solution Overview

Create **new memory update templates** specifically for Phase 1 education/ranking rounds that exclude the problematic text about outcomes. Keep existing templates for Phase 1 application rounds where the text is correct.

### Approach

1. **Create new prompt templates** for Phase 1 education (4 per language = 12 total new prompts)
2. **Update memory manager** to detect Phase 1 education vs application rounds and select appropriate templates
3. **Keep existing templates** unchanged for Phase 1 application rounds

### Text to Remove (Only in New Education Templates)

For each language, the NEW education templates will exclude TWO specific text segments:

#### English
**Segment 1:**
```
Besides your memory and your recent activity you will receive the outcome of your choice which includes the payoff you received, your class assignment and the payoffs you would have received under each principle.
```

**Segment 2:**
```
Please analyze and incorporate this information into your updated memory.
```

#### Spanish
**Segment 1:**
```
Ademas de tu memoria y tu actividad reciente, recibirás el resultado de tu elección, que incluye el pago que recibiste, tu asignación de clase y los pagos que habrías recibido según cada principio.
```

**Segment 2:**
```
Analiza e incorpora esta información a tu memoria actualizada.
```

#### Mandarin
**Segment 1:**
```
除了你的记忆和最近的活动，你还会收到你选择的结果，其中包括你得到的回报、你的班级任务以及你在每个原则下会得到的回报。
```

**Segment 2:**
```
请分析这些信息，并将其纳入你的最新记忆。
```

### New Prompt Keys to Create

Each language file needs 4 NEW prompt keys for Phase 1 education/ranking rounds:

**New Phase 1 Education Templates (4 per language):**
1. `memory_memory_update_prompt_phase1_education` - Structured style, education rounds
2. `memory_memory_update_prompt_no_recent_activity_phase1_education` - Structured style, no recent activity variant
3. `memory_narrative_update_prompt_phase1_education` - Narrative style, education rounds
4. `memory_narrative_update_prompt_no_recent_activity_phase1_education` - Narrative style, no recent activity variant

**Total new prompts: 12 (4 prompts × 3 languages)**

### Existing Prompts to Keep Unchanged

The following existing prompts remain unchanged and continue to be used for Phase 1 **application rounds**:
- `memory_memory_update_prompt` - Used during application rounds 1-4
- `memory_memory_update_prompt_no_recent_activity`
- `memory_narrative_update_prompt`
- `memory_narrative_update_prompt_no_recent_activity`

## Expected Outcome

After these changes:
- **Phase 1 education/ranking rounds**: Memory prompts will NOT reference non-existent outcomes or recent activity
- **Phase 1 application rounds**: Memory prompts will KEEP the existing text about outcomes (correct behavior)
- Agents will receive contextually appropriate memory update instructions based on whether outcomes exist
- The memory manager will intelligently route to education vs application templates

## Implementation Steps

### Step 1: Create New Education Templates in Translation Files

**For each of the 3 language files, add 4 new prompt keys:**

1. **Edit `translations/english_prompts.json`**
   - Add `memory_memory_update_prompt_phase1_education` (copy from `memory_memory_update_prompt`, remove 2 segments)
   - Add `memory_memory_update_prompt_no_recent_activity_phase1_education` (copy from `memory_memory_update_prompt_no_recent_activity`, remove 2 segments)
   - Add `memory_narrative_update_prompt_phase1_education` (copy from `memory_narrative_update_prompt`, remove 2 segments)
   - Add `memory_narrative_update_prompt_no_recent_activity_phase1_education` (copy from `memory_narrative_update_prompt_no_recent_activity`, remove 2 segments)
   - Verify JSON formatting remains valid

2. **Edit `translations/spanish_prompts.json`**
   - Add same 4 new prompt keys with Spanish text (remove 2 segments from each)
   - Verify JSON formatting remains valid

3. **Edit `translations/mandarin_prompts.json`**
   - Add same 4 new prompt keys with Mandarin text (remove 2 segments from each)
   - Verify JSON formatting remains valid

### Step 2: Update Memory Manager Template Selection Logic

**Edit `utils/memory_manager.py`:**

Add logic to `_create_memory_update_prompt()` method (around line 280) to detect Phase 1 education rounds:

```python
# Check if this is Phase 1 education/ranking (not application)
is_phase1_education = (
    phase == "phase_1" and
    round_number in [-1, 0, 5]  # Education rounds: explanation, rankings
)

# Choose base prompt template based on memory guidance style and context
if is_phase1_education:
    # Phase 1 education uses templates without outcome references
    if guidance_style == "narrative":
        base_prompt_key = "prompts.memory_narrative_update_prompt_phase1_education"
    else:  # structured
        base_prompt_key = "prompts.memory_memory_update_prompt_phase1_education"
elif is_first_round_phase2:
    # Existing Phase 2 first round logic...
else:
    # Existing regular template logic (includes Phase 1 application rounds 1-4)
```

### Step 3: Validation

1. **JSON validation**: Ensure all translation files have valid JSON syntax
2. **Prompt review**: Check one education template per language to confirm correct text removal
3. **Template coverage**: Verify all 4 combinations are created (structured/narrative × with/without recent activity)
4. **Code review**: Ensure memory manager logic correctly routes education vs application rounds

### Step 4: Testing (Optional but Recommended)

Run a quick Phase 1 experiment and check memory update logs to verify:
- Education rounds (0, -1, 5) use new templates WITHOUT outcome text
- Application rounds (1-4) use existing templates WITH outcome text

## Notes

- **Do NOT modify existing templates** - they are correct for Phase 1 application rounds and all Phase 2 scenarios
- The new templates are ONLY for Phase 1 education/ranking rounds where no outcomes/payoffs exist yet
- Memory manager change is minimal - just add one new condition to existing template selection logic
- The "_no_recent_activity" variants are for Phase 2 discussion interactions, but we create them for Phase 1 education for consistency
