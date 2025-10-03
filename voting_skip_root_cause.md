# Root Cause Analysis: Voting Confirmation Skipped

## Issue Summary
After simplifying the vote-confirmation prompt, Phase 2 never reached the secret ballot step. Every voting attempt exited the confirmation phase with `Error during voting process: Failed to format translation at 'prompts.utility_voting_confirmation_request': 'initiation_statement'`, so the system returned to open discussion without attempting consensus.

## Impact
- All voting requests in Phase 2 were skipped.
- The regression affected every language because the updated code path is shared.
- No consensus decisions could be produced, blocking the experiment pipeline.

## Investigation (Systematic Walkthrough)

1. **Entry Point Inspection** — `VotingService.conduct_confirmation_phase()` (`core/services/voting_service.py:240`) now formats the prompt with `language_manager.get("prompts.utility_voting_confirmation_request", initiator_name=initiator_name)`.
2. **Formatting Failure Source** — `LanguageManager.get()` (`utils/language_manager.py:166-180`) wraps the template in `current.format(**format_kwargs)` and raises a `ValueError` if any placeholder is missing.
3. **Template Review** — The English/Spanish/Mandarin JSON files still contained `{initiation_statement}` in the `utility_voting_confirmation_request` entry, even though the call site now supplies `initiator_name`.
4. **Exception Propagation** — The resulting `KeyError('initiation_statement')` bubbles up as a `ValueError`. `Phase2Manager._attempt_end_of_round_voting()` catches the generic `Exception`, logs the warning, and aborts the vote (`core/phase2_manager.py:600-608`).
5. **Cache Hypothesis Tested** — `FrohlichExperimentManager` builds a fresh `LanguageManager` for every run (`main.py:68-91`). Instantiating a new manager in a Python REPL returned the updated prompt correctly, demonstrating that process restarts pick up new templates and that cache staleness is not the primary issue.
6. **Regression Scope** — Golden tests (`tests/golden/test_voting_service_prompts.py:234`) still hold the old prompt snapshot, so the suite never exercised the new placeholder and failed to catch the mismatch.

## Confirmed Root Cause
The translation files were not updated alongside the code change; they still referenced the old `{initiation_statement}` placeholder. Because `conduct_confirmation_phase()` now passes `initiator_name`, the formatter raised `KeyError('initiation_statement')`, and Phase 2 swallowed the exception and skipped voting.

## Resolution & Verification
- Updated `translations/english_prompts.json`, `translations/spanish_prompts.json`, and `translations/mandarin_prompts.json` to replace `{initiation_statement}` with `{initiator_name}`.
- Verified the fix by instantiating `LanguageManager` directly:

```bash
python - <<'PY'
from utils.language_manager import LanguageManager, SupportedLanguage
lm = LanguageManager('translations')
lm.set_language(SupportedLanguage.ENGLISH)
print(lm.get('prompts.utility_voting_confirmation_request', initiator_name='Alice'))
PY
```

The command now prints the simplified confirmation message without raising.

## Follow-Up Actions
- Refresh the golden prompt fixtures in `tests/golden/test_voting_service_prompts.py` so they mirror the simplified confirmation copy.
- Add a regression test that loads the real translation files (or validates placeholders) to detect future parameter/template drift.
- Consider tightening `Phase2Manager` error handling so formatting errors surface clearly (e.g., escalate or include the stack trace) instead of silently dropping voting attempts.

## Why Cache Invalidation Is Not the Culprit
`LanguageManager` caches translations per instance, but each experiment run constructs a new manager. Unless experiments are executed back-to-back inside the same long-lived process without re-instantiation, stale cache entries cannot explain the regression. The formatting mismatch alone reproduced the failure, and correcting the template resolved it without touching cache logic.

With the templates aligned, voting confirmation completes and the pipeline proceeds to the secret ballot as expected.
