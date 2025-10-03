# Voting Regression Caused by Round Header Placeholders

## 1. Symptom Recap
- Every Phase 2 vote attempt is recorded as an `Error` in recent experiment results (e.g., `experiment_results_20251003_104256.json` → `voting_history.vote_initiation_requests` shows both Alice and Sophie failing each round).
- No confirmation prompts or secret ballots are triggered; Phase 2 returns to open discussion after each failed attempt.

## 2. What Changed
- Recent translation updates added the header `"VOTING DECISION POINT - Round {round_number} of {max_rounds}"` to the vote initiation prompts (`translations/english_prompts.json:75-77`, same for Spanish/Mandarin).
- The corresponding service code (`core/services/voting_service.py:124-132`) still calls `language_manager.get("prompts.vote_initiation_with_statement_prompt", agent_recent_statement=...)` without providing `round_number` / `max_rounds`.

## 3. How the Failure Manifests
1. When a participant has a recent public statement (the common case), the voting service chooses the *_with_statement* template.
2. `LanguageManager.get()` receives one keyword argument (`agent_recent_statement`). Because `format_kwargs` is non-empty, it executes `current.format(**format_kwargs)` (`utils/language_manager.py:166-182`).
3. The template also references `{round_number}` and `{max_rounds}`, which are missing. Python raises `KeyError('round_number')`.
4. The generic `KeyError` is caught and re-raised as `KeyError("Translation path not found ...")`, so the caller just sees a path error.
5. The exception propagates back to `_attempt_end_of_round_voting()` where it is caught and logged as a generic "Error during voting process" (`core/phase2_manager.py:585`), aborting the voting attempt.

Reproduction snippet (current main branch):
```bash
python - <<'PY'
from utils.language_manager import LanguageManager, SupportedLanguage
lm = LanguageManager('translations')
lm.set_language(SupportedLanguage.ENGLISH)
print('Expect KeyError due to missing round placeholders:')
try:
    lm.get('prompts.vote_initiation_with_statement_prompt', agent_recent_statement='Demo')
except Exception as exc:
    print(type(exc).__name__, exc)
PY
```
Output:
```
Expect KeyError due to missing round placeholders:
KeyError "Translation path not found: 'prompts.vote_initiation_with_statement_prompt' in English"
```

## 4. Why Confirmation Was Believed to Be the Issue
- The earlier regression stemmed from `{initiator_name}` vs `{initiation_statement}`. Fixing only that left this new placeholder mismatch hidden because the vote initiation exception happens before the confirmation phase ever starts.
- The new round header affects only the initiation prompts, so confirmation remained untouched (hence no new logs there).

## 5. Recommended Fix
1. **Update prompt construction** in `VotingService.prompt_for_vote_initiation()` so every template receives the full set of placeholders:
   - Pass `round_number` and `max_rounds` (and `internal_reasoning` when required) to `language_manager.get()`.
   - Use `context.round_number` (already tracked in `ParticipantContext`) and `self.settings.phase2_rounds` or `self.config.phase2_rounds` to derive `max_rounds`.
2. **Add regression tests** that exercise the real templates, ensuring all required placeholders are supplied. Suggested locations:
   - `tests/golden/test_voting_service_prompts.py`: new test verifying formatted vote initiation prompt with statement includes resolved round values.
   - A lightweight unit test in `tests/unit/test_language_manager_formatting.py` that loads the actual translation and asserts `KeyError` is not raised when the correct kwargs are provided.
3. **Consider tightening error messages** in `LanguageManager.get()` so formatting errors report missing placeholders explicitly (optional but aids debugging).

## 6. Validation Plan
- After adjusting the prompt construction, rerun `python run_tests.py unit` (or the scoped golden tests) to confirm the snapshot expectations pass.
- Execute a fast experiment (e.g., `python main.py config/fast.yaml`) and confirm `voting_history.total_vote_attempts` increments and the confirmation phase fires.

## 7. Next Actions
- Implement the prompt formatting fix plus tests.
- Re-run the failing experiment to ensure voting progresses to confirmation and secret ballot.
- Only if further issues arise do we revisit caching or confirmation logic; current evidence indicates the initiation prompt mismatch is the sole blocker introduced with the round headers.
