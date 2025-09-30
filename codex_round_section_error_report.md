# Round Section Placeholder Regression Analysis

## Summary
A recent translation update introduced the placeholder `{round_section}` inside the context header string (`prompts.context_context_info_format`). The formatting helper in `utils/language_manager.py` still passes only `phase` and `round_number`, so the newly required placeholder is missing. During string interpolation Python raises a `KeyError('round_section')`, which bubbles up as the `ExperimentLogicError` observed when Phase 1 tries to render the first agent instructions.

## Where it Fails
- **Translation change**: `translations/english_prompts.json:71` (and corresponding Spanish/Mandarin files) now include `Current Phase: {phase}{round_section}`.
- **Formatter**: `utils/language_manager.py:445-468` builds the kwargs for `prompts.context_context_info_format`. The dictionary does not contain `round_section`, triggering the failure when `str.format()` runs.
- **Stack trace**: Any call to `language_manager.format_context_info(...)`, which is the default instruction generator for participant agents, hits this code path before the participant even produces a response.

## Impact
- Phase 1 and Phase 2 instruction prompts fail on the first turn, aborting experiment execution.
- Any other caller relying on `format_context_info` is equally affected, so the regression is blocking.

## Proposed Fix
1. **Augment `format_context_info` arguments**
   - Compute a string such as:
     ```python
     round_section = ""
     if round_number is not None and round_number > 0:
         round_section = f" – Round {round_number}"
     ```
   - Pass `round_section=round_section` into the `self.get("prompts.context_context_info_format", ...)` call.
   - For contexts where round numbers are intentionally suppressed, the helper will already receive `None`; we should treat that the same as “no label.”

2. **Align translations**
   - Keep the `{round_section}` placeholder in each language file now that the formatter will provide it.
   - No further translation change is required once the helper supplies the new argument.

3. **Regression test**
   - Extend the language manager unit tests (or add a targeted one) to cover the new placeholder, ensuring `format_context_info` succeeds both when `round_number` is present and when it is `None`.

## Verification Plan
- Run `tests/unit/test_language_manager.py` (or the appropriate module) after adding the helper change to confirm formatting works with and without rounds.
- Execute a Phase 1 smoke test (`python -m pytest tests/integration/test_phase1_flow.py` or run `python main.py`) to ensure instruction rendering now completes.

## Notes
- This change remains simple: no refactoring of formatters or translations beyond supplying the missing parameter.
- Keep an eye on any other templates that may have gained new placeholders during translation updates; the same audit approach can prevent similar regressions.
