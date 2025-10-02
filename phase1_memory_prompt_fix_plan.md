# Phase 1 Memory Prompt Fix Plan (REVISED)

## Problem Statement

Phase 1 memory update prompts contain text that makes false promises about outcomes during education/ranking rounds where no outcomes exist yet.

### Specific Issue

**Problematic text in current templates:**
```
Besides your memory and your recent activity you will receive the outcome of your choice
which includes the payoff you received, your class assignment and the payoffs you would
have received under each principle. Please analyze and incorporate this information into
your updated memory.
```

**Why this is wrong:**
- During Phase 1 education/ranking rounds (rounds -1, 0, 5), agents receive NO outcomes
- The text promises "payoff", "class assignment", and "counterfactual payoffs" that don't exist
- This creates confusion and sets false expectations

### Where This Occurs

**Phase 1 rounds where the text is misleading:**
1. Round -1: Detailed explanation (learning about principles)
2. Round 0: Initial and post-explanation rankings
3. Round 5: Final ranking

**Phase 1 rounds where outcomes DO exist:**
- Rounds 1-4: Application rounds with actual payoffs and counterfactuals

### Root Cause

The templates make **context-specific promises** but are used in **all Phase 1 contexts**. The problem isn't template selection - it's that the templates reference outcomes that don't always exist.

## Solution: Context-Neutral Rewording

### Approach

**Rewrite the problematic text to be context-neutral** - truthful in ALL scenarios without promising non-existent outcomes.

**Replace with:**
```
Review the information provided below alongside your current memory. Focus on incorporating
insights that might influence your choices about justice principles or help in group
discussions.
```

### Why This Works

✅ **Context-neutral**: Works equally well for education AND application rounds
✅ **Truthful**: Makes no false promises about outcomes
✅ **Instructional**: Still provides clear guidance on what to do
✅ **Zero code changes**: Pure template modification
✅ **Simple**: Just edit text, no new logic or templates

## Files to Modify

All three translation files require the same 4 template edits:

1. `translations/english_prompts.json`
2. `translations/spanish_prompts.json`
3. `translations/mandarin_prompts.json`

## Templates to Edit

### 4 Templates per Language (12 total edits)

1. **`prompts.memory_memory_update_prompt`** - Structured style
2. **`prompts.memory_memory_update_prompt_no_recent_activity`** - Structured, no recent activity
3. **`prompts.memory_narrative_update_prompt`** - Narrative style
4. **`prompts.memory_narrative_update_prompt_no_recent_activity`** - Narrative, no recent activity

**Note:** The `_no_recent_activity` variants are used in Phase 2 discussion interactions, but we update them for consistency.

## Detailed Text Changes

### English

**Current text to REMOVE:**
```
Besides your memory and your recent activity you will receive the outcome of your choice which includes the payoff you received, your class assignment and the payoffs you would have received under each principle. Please analyze and incorporate this information into your updated memory.
```

**Replacement text to ADD:**
```
Review the information provided below alongside your current memory. Focus on incorporating insights that might influence your choices about justice principles or help in group discussions.
```

**Keep this existing text UNCHANGED:**
```
Focus on information that might influence your choices about justice principles or help you in group discussions. Pay particular attention to patterns in outcomes, unexpected results, and insights about how different principles perform in practice versus theory
```

### Spanish

**Current text to REMOVE:**
```
Ademas de tu memoria y tu actividad reciente, recibirás el resultado de tu elección, que incluye el pago que recibiste, tu asignación de clase y los pagos que habrías recibido según cada principio. Analiza e incorpora esta información a tu memoria actualizada.
```

**Replacement text to ADD:**
```
Revisa la información proporcionada a continuación junto con tu memoria actual. Concéntrate en incorporar ideas que puedan influir en tus elecciones sobre los principios de justicia o ayudarte en las discusiones de grupo.
```

### Mandarin

**Current text to REMOVE:**
```
除了你的记忆和最近的活动，你还会收到你选择的结果，其中包括你得到的回报、你的班级任务以及你在每个原则下会得到的回报。请分析这些信息，并将其纳入你的最新记忆。
```

**Replacement text to ADD:**
```
将下面提供的信息与你当前的记忆一起审查。专注于纳入可能影响你对公正原则的选择或帮助你进行小组讨论的见解。
```

## Implementation Steps

### Step 1: Edit English Translations

Edit `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`:

1. Find `memory_memory_update_prompt` (around line 90)
2. Replace the problematic text with the new text
3. Repeat for the other 3 templates
4. Verify JSON syntax is valid

### Step 2: Edit Spanish Translations

Edit `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`:

1. Find `memory_memory_update_prompt` (around line 157)
2. Replace the problematic Spanish text with the new Spanish text
3. Repeat for the other 3 templates
4. Verify JSON syntax is valid

### Step 3: Edit Mandarin Translations

Edit `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`:

1. Find `memory_memory_update_prompt` (around line 105)
2. Replace the problematic Mandarin text with the new Mandarin text
3. Repeat for the other 3 templates
4. Verify JSON syntax is valid

### Step 4: Validation

1. **JSON validation**: Run `python -c "import json; json.load(open('translations/english_prompts.json'))"` for each file
2. **Text review**: Manually verify one edited template per language
3. **Search verification**: Grep for the old problematic text to ensure it's all removed
4. **Template count**: Verify exactly 4 templates were edited per language (12 total edits)

### Step 5: Testing (Recommended)

1. Run a quick Phase 1 experiment with `config/fast.yaml`
2. Check agent memory update logs to verify prompts look correct
3. Verify no references to non-existent outcomes in education rounds
4. Verify application rounds still work correctly

## Expected Outcome

After these changes:

- ✅ **Education rounds (0, -1, 5)**: Prompts no longer promise non-existent outcomes
- ✅ **Application rounds (1-4)**: Prompts still provide helpful guidance about incorporating outcomes
- ✅ **No code changes**: Zero modifications to `utils/memory_manager.py`
- ✅ **No new templates**: Same 4 templates per language, just improved wording
- ✅ **Maintainability**: Single source of truth for each template

## Rationale

This solution was chosen after thorough review and discussion because it:

1. **Fixes the root problem**: Templates no longer make false promises
2. **Preserves value**: Instructional guidance remains intact
3. **Maximizes simplicity**: Zero code changes, just text rewording
4. **Minimizes maintenance**: No new templates to maintain
5. **Works universally**: Context-neutral language suits all scenarios

## Notes

- **Do NOT create new templates** - just edit existing ones
- **Do NOT modify memory_manager.py** - no code changes needed
- **Keep the second paragraph** about focusing on patterns/outcomes unchanged
- **Translation quality**: The Spanish and Mandarin text should be reviewed by native speakers if possible
- **Backward compatible**: This is a pure improvement with no breaking changes
