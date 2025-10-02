# Hardcoded English Audit Report
## Frohlich Experiment - Phase Managers and Services

**Date:** 2025-10-02
**Scope:** Phase managers and service layer prompt construction
**Total Files Scanned:** 5 core files
**Total Issues Identified:** 20 (11 require fixes, 7 logging-only, 2 correct)

---

## Executive Summary

This audit systematically scanned all phase managers and service files for hardcoded English text that could be sent to multilingual agents. The findings reveal **11 critical and medium-severity issues** where English fallback text can reach agents in non-English experiments, potentially breaking immersion and consistency.

### Severity Classification

| Severity | Count | Description |
|----------|-------|-------------|
| **High** | 7 | English text sent directly to agents in prompts or memory |
| **Medium** | 4 | English text in memory/task completion messages |
| **Low** | 7 | Internal logging only (not visible to agents) |
| **None** | 2 | Correct implementation (translation key selection) |

**Action Required:** 11 issues need fixing (High + Medium severity)

---

## Detailed Findings by File

### 1. core/phase1_manager.py
**Status:** 🔴 **6 issues requiring fixes**

#### High Severity Issues (2)

##### Issue 1.1: Retry Memory Update Fallback - "Retry feedback:"
- **Line:** 240
- **Code:** `else 'Retry feedback:'`
- **Context:** `retry_memory_content` construction in `_update_participant_memory_with_retry`
- **Impact:** Sent to agents during retry experiences when `language_manager.retry_prompts` is not available
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `memory_field_labels.retry_feedback`

```python
# Current problematic code:
retry_memory_content = f"""{language_manager.get('memory_field_labels.retry_feedback') if hasattr(language_manager, 'retry_prompts') else 'Retry feedback:'} {feedback}
```

##### Issue 1.2: Retry Memory Update Fallback - "My retry response:"
- **Line:** 241
- **Code:** `else 'My retry response:'`
- **Context:** `retry_memory_content` construction in `_update_participant_memory_with_retry`
- **Impact:** Sent to agents during retry experiences when `language_manager.retry_prompts` is not available
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `memory_field_labels.your_response`

```python
# Current problematic code:
{language_manager.get('memory_field_labels.your_response') if hasattr(language_manager, 'retry_prompts') else 'My retry response:'} {retry_response}"""
```

#### Medium Severity Issues (4)

##### Issue 1.3: Task Completion - "Completed initial ranking"
- **Line:** 265
- **Code:** `else "Completed initial ranking"`
- **Context:** `_get_completion_message_for_task` method
- **Impact:** Memory content for task completion when translation key missing
- **Fix Required:** Ensure `memory_outcomes.completed_initial_ranking` exists in all language files

##### Issue 1.4: Task Completion - "Completed post-explanation ranking"
- **Line:** 266
- **Code:** `else "Completed post-explanation ranking"`
- **Context:** `_get_completion_message_for_task` method
- **Impact:** Memory content for task completion when translation key missing
- **Fix Required:** Ensure `memory_outcomes.completed_post_explanation_ranking` exists in all language files

##### Issue 1.5: Task Completion - "Completed final ranking"
- **Line:** 267
- **Code:** `else "Completed final ranking"`
- **Context:** `_get_completion_message_for_task` method
- **Impact:** Memory content for task completion when translation key missing
- **Fix Required:** Ensure `memory_outcomes.completed_final_ranking` exists in all language files

##### Issue 1.6: Task Completion Generic Fallback
- **Line:** 270
- **Code:** `f"Completed {task_name}"`
- **Context:** `_get_completion_message_for_task` default return
- **Impact:** Generic fallback for unknown task names
- **Fix Required:** Consider removing or translating the word "Completed"

```python
# Current problematic code:
return task_messages.get(task_name, f"Completed {task_name}")
```

---

### 2. core/phase2_manager.py
**Status:** ✅ **No fixes required** (2 logging-only issues)

#### Low Severity Issues (2)

##### Issue 2.1: Vote Initiation Logging
- **Line:** 501
- **Code:** `"Yes" if wants_vote else "No"`
- **Context:** Vote initiation logging for agent_logger
- **Impact:** Internal logging only, not visible to agents
- **Action:** None required (logging infrastructure)

##### Issue 2.2: Vote Responses Logging
- **Line:** 608
- **Code:** `"Yes" if resp is True else "No" if resp is False else "Error"`
- **Context:** Vote responses logging
- **Impact:** Internal logging only, not visible to agents
- **Action:** None required (logging infrastructure)

---

### 3. core/services/voting_service.py
**Status:** ✅ **No fixes required** (5 logging-only issues)

#### Low Severity Issues (5)

All 5 issues in this file are internal logging operations that are not sent to agents:

##### Issue 3.1-3.5: Internal Logging Operations
- **Lines:** 169, 181, 298, 301, 355
- **Context:** Various vote-related logging operations
- **Impact:** Internal logging only
- **Action:** None required (logging infrastructure)

```python
# Examples (not sent to agents):
result_text = 'Yes' if wants_vote else 'No'  # Line 169
vote_requests = {participant.name: "Yes" if wants_vote else "No"}  # Line 181
```

---

### 4. core/services/memory_service.py
**Status:** ✅ **Correct implementation** (2 non-issues)

#### Non-Issues (2)

##### Issue 4.1-4.2: Translation Key Selection (Correct)
- **Lines:** 452, 496
- **Context:** Dynamic translation key selection
- **Code:**
  ```python
  decision_key = "initiate_voting" if wants_vote else "continue_discussion"
  response_key = "agreed_to" if agrees_to_vote else "declined_to"
  ```
- **Impact:** None - these correctly select translation keys, not hardcoded English
- **Action:** None required (correct implementation)

---

### 5. core/services/counterfactuals_service.py
**Status:** 🔴 **5 issues requiring fixes**

#### High Severity Issues (5)

##### Issue 5.1: Retry Prompt Introduction
- **Line:** 1062
- **Code:** `else "Let me try to provide a better response."`
- **Context:** `_build_retry_prompt` method
- **Impact:** Sent directly to agents during ranking retries
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `retry_prompts.retry_needed_intro`

```python
# Current problematic code:
retry_intro = language_manager.get('retry_prompts.retry_needed_intro') if hasattr(language_manager, 'retry_prompts') else "Let me try to provide a better response."
```

##### Issue 5.2: Retry Prompt Feedback Header
- **Line:** 1068
- **Code:** `else 'Feedback on previous response:'`
- **Context:** `_build_retry_prompt` method (detailed mode)
- **Impact:** Sent directly to agents during ranking retries
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `retry_prompts.feedback_header`

##### Issue 5.3: Retry Prompt Original Request Header
- **Line:** 1070
- **Code:** `else 'Please respond to the original request:'`
- **Context:** `_build_retry_prompt` method (detailed mode)
- **Impact:** Sent directly to agents during ranking retries
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `retry_prompts.original_request`

```python
# Current problematic code:
if detail_level == "detailed":
    retry_prompt = f"""{retry_intro}

{language_manager.get('retry_prompts.feedback_header') if hasattr(language_manager, 'retry_prompts') else 'Feedback on previous response:'} {feedback}

{language_manager.get('retry_prompts.original_request') if hasattr(language_manager, 'retry_prompts') else 'Please respond to the original request:'} {original_prompt}"""
```

##### Issue 5.4: Retry Memory Update - "Retry feedback:"
- **Line:** 1103
- **Code:** `else 'Retry feedback:'`
- **Context:** `_update_participant_memory_with_retry_experience` method
- **Impact:** Sent to agents during retry memory updates
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `memory_field_labels.retry_feedback`

##### Issue 5.5: Retry Memory Update - "My retry response:"
- **Line:** 1104
- **Code:** `else 'My retry response:'`
- **Context:** `_update_participant_memory_with_retry_experience` method
- **Impact:** Sent to agents during retry memory updates
- **Affected Languages:** Spanish, Mandarin agents would see English
- **Fix Required:** Add to translation files under `memory_field_labels.your_response`

```python
# Current problematic code:
retry_memory_content = f"""{language_manager.get('memory_field_labels.retry_feedback') if hasattr(language_manager, 'retry_prompts') else 'Retry feedback:'} {feedback}
{language_manager.get('memory_field_labels.your_response') if hasattr(language_manager, 'retry_prompts') else 'My retry response:'} {retry_response}"""
```

---

## Files with No Issues

### ✅ Clean Files
- `core/experiment_manager.py` - No agent-facing hardcoded English found
- `core/two_stage_voting_manager.py` - No agent-facing hardcoded English found
- `core/services/discussion_service.py` - No agent-facing hardcoded English found
- `core/services/speaking_order_service.py` - Not scanned (no prompt construction)

---

## Translation Keys Missing from JSON Files

Based on the audit, the following translation keys need to be verified in all language files:

### Required in all language files (english_prompts.json, spanish_prompts.json, mandarin_prompts.json):

#### 1. Retry Prompts Section
```json
"retry_prompts": {
  "retry_needed_intro": "<translation>",
  "feedback_header": "<translation>",
  "original_request": "<translation>"
}
```

**English values:**
- `retry_needed_intro`: "Let me try to provide a better response."
- `feedback_header`: "Feedback on previous response:"
- `original_request`: "Please respond to the original request:"

#### 2. Memory Field Labels Section
```json
"memory_field_labels": {
  "retry_feedback": "<translation>",
  "your_response": "<translation>"
}
```

**English values:**
- `retry_feedback`: "Retry feedback:"
- `your_response`: "My retry response:"

#### 3. Memory Outcomes Section
```json
"memory_outcomes": {
  "completed_initial_ranking": "<translation>",
  "completed_post_explanation_ranking": "<translation>",
  "completed_final_ranking": "<translation>"
}
```

**English values:**
- `completed_initial_ranking`: "Completed initial ranking"
- `completed_post_explanation_ranking`: "Completed post-explanation ranking"
- `completed_final_ranking`: "Completed final ranking"

---

## Recommended Fix Strategy

### Phase 1: Add Missing Translation Keys (Priority: HIGH)

1. **Add to `translations/english_prompts.json`:**
   - Create/update `retry_prompts` section with 3 keys
   - Create/update `memory_field_labels` section with 2 keys
   - Create/update `memory_outcomes` section with 3 keys

2. **Translate and add to `translations/spanish_prompts.json`:**
   - All 8 keys with proper Spanish translations

3. **Translate and add to `translations/mandarin_prompts.json`:**
   - All 8 keys with proper Mandarin translations

### Phase 2: Update Code to Remove Fallbacks (Priority: MEDIUM)

After translation keys are added, consider updating the code to either:

**Option A: Remove fallbacks entirely (strict mode)**
```python
# Fail fast if translation missing
retry_intro = language_manager.get('retry_prompts.retry_needed_intro')
if not retry_intro:
    raise ValueError(f"Missing translation key: retry_prompts.retry_needed_intro")
```

**Option B: Log warnings when fallbacks used**
```python
# Keep fallbacks but warn developers
retry_intro = language_manager.get('retry_prompts.retry_needed_intro')
if not retry_intro:
    logger.warning("Missing translation: retry_prompts.retry_needed_intro, using English fallback")
    retry_intro = "Let me try to provide a better response."
```

**Option C: Keep current behavior (document only)**
- Document that English fallbacks exist
- Ensure all translation keys are present to avoid fallbacks

### Phase 3: Add Translation Tests (Priority: LOW)

Create tests to verify all translation keys exist:
```python
def test_all_translation_keys_present():
    """Ensure all required translation keys exist in all language files"""
    required_keys = [
        'retry_prompts.retry_needed_intro',
        'retry_prompts.feedback_header',
        'retry_prompts.original_request',
        'memory_field_labels.retry_feedback',
        'memory_field_labels.your_response',
        'memory_outcomes.completed_initial_ranking',
        'memory_outcomes.completed_post_explanation_ranking',
        'memory_outcomes.completed_final_ranking'
    ]

    for language in ['english', 'spanish', 'mandarin']:
        language_manager = LanguageManager(language)
        for key in required_keys:
            assert language_manager.get(key) is not None, f"Missing {key} in {language}"
```

---

## Impact Assessment

### Current State
- **7 High-severity issues** where agents may receive English prompts/memory in Spanish/Mandarin experiments
- **4 Medium-severity issues** where agents may receive English task completion messages
- **Trigger conditions:** These fallbacks activate when:
  - `language_manager` doesn't have `retry_prompts` attribute
  - Translation keys are missing from JSON files
  - `hasattr()` checks fail

### Risk Level
- **High Risk:** Retry scenarios in Phase 1 and Phase 2 (counterfactuals_service)
- **Medium Risk:** Task completion messages
- **Low Risk:** Internal logging (no agent impact)

### Mitigation Status
Translation files (`spanish_prompts.json`, `mandarin_prompts.json`) may already contain these keys. If not, they need to be added urgently.

---

## Verification Checklist

- [ ] Verify `retry_prompts` section exists in all 3 language files
- [ ] Verify `memory_field_labels` section exists in all 3 language files
- [ ] Verify `memory_outcomes` section exists in all 3 language files
- [ ] Test Spanish experiment with retry scenario (Phase 1)
- [ ] Test Mandarin experiment with retry scenario (Phase 1)
- [ ] Test Spanish experiment with ranking task completion
- [ ] Test Mandarin experiment with ranking task completion
- [ ] Test Spanish experiment with counterfactuals retry (Phase 2)
- [ ] Test Mandarin experiment with counterfactuals retry (Phase 2)
- [ ] Add translation key presence tests to test suite
- [ ] Document fallback behavior in code comments
- [ ] Consider removing fallbacks after keys verified present

---

## Appendix: Code References

### Files Scanned
1. `core/phase1_manager.py` - Phase 1 orchestration
2. `core/phase2_manager.py` - Phase 2 orchestration
3. `core/experiment_manager.py` - Experiment-level orchestration
4. `core/two_stage_voting_manager.py` - Voting system
5. `core/services/discussion_service.py` - Discussion service
6. `core/services/voting_service.py` - Voting service
7. `core/services/memory_service.py` - Memory management service
8. `core/services/counterfactuals_service.py` - Counterfactuals and results service

### Methodology
- Systematic grep-based search for hardcoded English patterns
- Manual code review for context and severity assessment
- Line-by-line verification of agent-facing vs internal text
- Classification by impact on agent experience

### Report Prepared By
Claude Code automated audit system

---

**End of Report**
