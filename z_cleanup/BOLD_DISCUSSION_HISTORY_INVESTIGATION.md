# Bold Discussion History Investigation Report

## Problem Statement

**Observed Behavior:**
- Discussion history content appears **bold** during statement generation prompts ❌
- Discussion history content appears **bold** during reasoning step prompts ❌
- Discussion history content appears **NOT bold** during memory update prompts ✅

**Expected Behavior:**
- Discussion history should NEVER contain bold formatting in any prompt type

## Investigation Methodology

This report systematically traces the discussion history flow through three different prompt types to identify where bold formatting is introduced or preserved.

---

## Part 1: Data Source Analysis

### Where Discussion History is Stored

**Primary Storage:** `GroupDiscussionState.public_history` (string)

**How statements are added:**
```python
# File: models/experiment_types.py, Line 176
def add_statement(self, participant_name: str, statement: str, language_manager=None):
    # Strip markdown emphasis from statement before storing
    clean_statement = self._strip_markdown_emphasis(statement)  # Line 186

    # ... validation ...

    # Format and add to public_history
    self.public_history += f"\n{formatted_statement}"  # Line 204
```

**Analysis:**
- ✅ Bold IS stripped before adding to `public_history`
- ✅ The stripping happens via `_strip_markdown_emphasis()` using regex pattern `(\*\*|__)(.+?)(\1)`
- ✅ This should prevent ANY bold from entering `public_history`

**Question:** If bold is stripped at source, how is it appearing in prompts?

---

## Part 2: Prompt Type Analysis

### Type 1: Statement Generation Prompt (❌ HAS BOLD)

**Code Path:**
1. `phase2_manager.py` Line 334: `self.config._current_public_history = discussion_state.public_history`
2. `participant_agent.py` Line 289: `public_history = getattr(experiment_config, '_current_public_history', '')`
3. `participant_agent.py` Line 290-295: Calls `format_phase2_discussion_instructions(discussion_history=public_history)`
4. `language_manager.py` Line 698: Uses history directly in template

**Hypothesis:** The bold is coming from somewhere BEFORE step 1.

---

### Type 2: Internal Reasoning Prompt (❌ HAS BOLD)

**Code Path:**
1. `discussion_service.py` Line 149: For round 1, uses `history_value = discussion_state.public_history`
2. `discussion_service.py` Line 150-154: Passes to language manager template
3. Template in `translations/english_prompts.json` Line 78: `phase2_internal_reasoning` includes `{discussion_history}`

**Critical Finding:**
```python
# File: discussion_service.py, Line 148-149 (Round 1)
if round_num == 1:
    history_value = discussion_state.public_history  # DIRECT ACCESS - NO STRIPPING
    return language_manager.get(
        "prompts.phase2_internal_reasoning",
        discussion_history=history_value,  # Passed directly
        ...
    )
```

**For round 2+:**
```python
# File: discussion_service.py, Line 156-161 (Round 2+)
else:
    return language_manager.get(
        "prompts.phase2_internal_reasoning_short",
        round_number=round_num,
        max_rounds=max_rounds
    )
    # NO DISCUSSION HISTORY PASSED AT ALL!
```

**Critical Discovery:**
- Round 1 reasoning prompt gets `discussion_state.public_history` directly
- Round 2+ reasoning prompts DON'T show discussion history at all (only round info)
- But the template `phase2_internal_reasoning` has a `{discussion_history}` placeholder

**Question:** Where does the history with bold come from for round 1?

---

### Type 3: Memory Update Prompt (✅ NO BOLD)

**Code Path:**
1. `participant_agent.py` Line 240-248: `format_memory_context()`
2. `language_manager.py` Line 564-569: Builds `discussion_header_section` (just header, not content!)
3. Template in `translations/english_prompts.json` Line 82: `context_memory_update_format`

**Template Content:**
```
"context_memory_update_format": "\nName: {name}\nRole Description: {role_description}\nBank Balance: ${bank_balance:.2f}\nCurrent Phase: {phase}\n{discussion_header_section}\nYou are updating your memory.\n"
```

**Critical Finding:**
- Memory update context does NOT include actual discussion history content!
- It only includes `discussion_header_section` which is just "Group Discussion - Round X of Y\n\nParticipants: ..."
- NO actual statement content is shown!

**This explains why memory update has no bold - it never shows the history content at all!**

---

## Part 3: Template Analysis

### Internal Reasoning Template (Round 1)

**File:** `translations/english_prompts.json` Line 78

```json
"phase2_internal_reasoning": "You are in Phase 2: ...[long explanation]...\n\nGROUP DISCUSSION - Round {round_number} of {max_rounds} (Internal Reasoning)\n\nBefore making your public statement, consider internally:\n- What is your current position...\n\nProvide your internal reasoning (this will not be shared with other participants)."
```

**Contains:** `{discussion_history}` placeholder

**But wait!** Let me check if this template actually uses the placeholder...

Looking at the template more carefully, I don't see `{discussion_history}` in the short version!

Let me check the actual template content again...

---

## Part 4: The Smoking Gun

Let me trace through what ACTUALLY happens when we call `build_internal_reasoning_prompt()`:

```python
# discussion_service.py Line 148-154
if round_num == 1:
    history_value = discussion_state.public_history  # Gets the history
    return language_manager.get(
        "prompts.phase2_internal_reasoning",
        discussion_history=history_value,  # Passes as kwarg
        round_number=round_num,
        max_rounds=max_rounds
    )
```

The template must use `{discussion_history}` somewhere. Let me check the actual template...

**AH! I found it in the full template - it's probably embedded in the long explanation at the top!**

But I removed the stripping from `build_internal_reasoning_prompt()` thinking it was redundant!

---

## Part 5: Root Cause Hypothesis

### Hypothesis 1: Old Data in Public History
- Maybe `public_history` contains statements from BEFORE we implemented stripping?
- **Likelihood:** HIGH if running against existing discussion state
- **Test:** Check if `public_history` actually contains bold markers

### Hypothesis 2: Template Embeds Bold
- Maybe the translation template itself contains bold markdown?
- **Likelihood:** LOW - templates are static
- **Test:** Inspect translation JSON files

### Hypothesis 3: The Stripping Was Removed
- We removed `self._strip_markdown_emphasis()` from `build_internal_reasoning_prompt()`
- **Likelihood:** CRITICAL - THIS IS THE ISSUE!
- **Test:** Check if `discussion_state.public_history` has bold when passed to prompt

### Hypothesis 4: Config Transient Field Not Set
- Maybe `config._current_public_history` is not being set before some prompt calls?
- **Likelihood:** MEDIUM
- **Test:** Check if config field is set before ALL reasoning/statement prompts

---

## Part 6: Critical Code Locations

### Location 1: Statement Addition (✅ Working)
```python
# models/experiment_types.py:186
clean_statement = self._strip_markdown_emphasis(statement)
```
**Status:** CORRECT - bold is stripped here

### Location 2: Internal Reasoning Prompt Round 1 (❌ SUSPECT)
```python
# discussion_service.py:149
history_value = discussion_state.public_history  # No stripping!
```
**Status:** REMOVED STRIPPING - might be the issue if public_history has old data

### Location 3: Statement Generation (❌ SUSPECT)
```python
# participant_agent.py:289
public_history = getattr(experiment_config, '_current_public_history', '')
```
**Status:** Uses transient field - depends on when it's set

### Location 4: Config Field Setting
```python
# phase2_manager.py:334
self.config._current_public_history = discussion_state.public_history
```
**Status:** Should be clean IF public_history is clean

---

## Part 7: The Real Question

**If we strip bold when adding statements, why does `public_history` contain bold?**

### Possibility A: It doesn't - the bold is added later during formatting
- Need to check if `format_phase2_discussion_instructions()` adds bold
- Need to check translation templates

### Possibility B: Public history has old statements from before the fix
- Need to check when the experiment starts - is public_history empty?
- Need to verify that ALL statements go through `add_statement()`

### Possibility C: There's another way statements enter public_history
- Check for direct assignments like `public_history = "something with **bold**"`
- Check for deserialization from JSON

---

## Next Steps for Investigation

1. **Add debug logging** to verify bold presence at each stage:
   - Log `public_history` immediately after `add_statement()`
   - Log `config._current_public_history` before instruction generation
   - Log the actual prompt shown to agents

2. **Check translation templates** for embedded `{discussion_history}` usage

3. **Verify stripping regex** is working correctly for all cases

4. **Check if public_history persists** between runs or is loaded from somewhere

---

## Part 8: Debug Testing Results

### Test with Fresh Data (2025-01-XX)

Running comprehensive test with freshly created `GroupDiscussionState`:

```python
state = GroupDiscussionState(round_number=1)
statement_with_bold = "I believe **maximizing the floor income** is the best approach"
state.add_statement("Alice", statement_with_bold, lm)
```

**Results:**
- ✅ Bold count in original statement: 2
- ✅ Bold count after `add_statement()`: 0
- ✅ Bold count in `public_history`: 0
- ✅ Bold count in `config._current_public_history`: 0
- ✅ Bold count in formatted instructions: 0

**Conclusion:** The stripping at source IS working correctly for new data!

### Critical Discovery: Direct Assignments

**File:** `core/services/discussion_service.py` Line 667
```python
discussion_state.public_history = truncated_history  # BYPASSES add_statement()
```

**File:** `core/services/voting_service.py` Lines 261, 299, 310, 319, 326, 331, 395, 493, 532
```python
discussion_state.public_history += f"\n{some_text}"  # BYPASSES add_statement()
```

**Impact:**
- These direct assignments/appends bypass the `add_statement()` method
- If any of this text contains bold, it won't be stripped
- HOWEVER, system messages from voting service are unlikely to contain bold

---

## Part 9: The Real Issue - Possible Causes

### Cause 1: OLD DATA FROM PREVIOUS RUNS ⚠️ HIGH PROBABILITY
If the user ran an experiment BEFORE we implemented bold stripping (before this session), and then looks at that old output, they would see bold.

**Evidence:**
- `GroupDiscussionState()` is created fresh each run (Line 644)
- No deserialization of old state
- No persistence between runs
- **BUT** results are saved to JSON files

### Cause 2: TERMINAL/UI RENDERING 🤔 MEDIUM PROBABILITY
The user might be confusing markdown RENDERING with actual bold characters.

**Example:**
- Terminal shows: `=== DISCUSSION HISTORY ===` in bold formatting
- But the actual text doesn't contain `**`
- User perceives this as "bold in discussion history"

### Cause 3: DIRECT ACCESS IN build_internal_reasoning_prompt() ⚠️ LIKELY
For Round 1 reasoning prompts, we removed the stripping but the template includes history:

```python
# discussion_service.py:149
history_value = discussion_state.public_history  # NO STRIPPING
```

If `public_history` somehow has bold, it will pass through unfiltered.

---

## Conclusion

**Most Likely Root Cause:**

The user is either:

1. **Looking at OLD experiment results** saved before we implemented bold stripping
2. **Confusing markdown rendering** in their terminal with actual bold characters
3. **Experiencing a defensive gap** where we removed stripping from read paths

**Evidence Supporting Fresh Data Works:**
- Debug test shows 0 bold markers through entire flow
- `add_statement()` correctly strips bold
- All core paths use clean data

**The Asymmetry Explained:**
- Memory update doesn't show discussion history content AT ALL
- Only reasoning/statement prompts show discussion history
- Therefore only reasoning/statement prompts could show bold

**Definitive Fix:**

Implement **DEFENSIVE STRIPPING** in all read paths:
1. ✅ Keep stripping at source (`add_statement()`)
2. ✅ Add stripping in `build_internal_reasoning_prompt()` before template
3. ✅ Add stripping in `format_phase2_discussion_instructions()` before template
4. ✅ Add stripping when truncating history

This ensures NO BOLD can ever appear regardless of data source.
