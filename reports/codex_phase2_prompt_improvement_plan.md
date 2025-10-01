codex Phase 2 Prompt Improvement Plan
====================================

## Assessment of Current Impressions
- Bold motive understood: the CLI renders `===` headers with emphasis even though stored history contains no Markdown bold. We can eliminate the effect by altering the section delimiters.
- Prompt construction is workable but fragmented (Phase2Manager → ParticipantAgent → LanguageManager), making reasoning about data flow difficult and increasing risk of regressions.
- Discussion history only appears in round-one reasoning prompts; short-form reasoning used in later rounds drops the transcript, so agents lack complete context after round one.

## Objectives
1. Present discussion history consistently across all Phase 2 reasoning and statement prompts without unintended styling.
2. Simplify prompt assembly so responsibilities are explicit and easier to test.
3. Ensure defensive sanitisation remains in place when reworking the pipeline.

## Workstreams & Key Tasks

### 1. Context Display Normalisation
- Replace `context_discussion_history_section_format` delimiters (`===`) with neutrally styled markers (e.g., `---`) across translations (`translations/*_prompts.json`).
- Audit other templates for the same delimiter pattern to keep visual behaviour predictable.
- Add regression test covering rendered context snippets to confirm no Markdown emphasis leaks (`tests/golden/test_phase2_prompts.py`).

### 2. Prompt Assembly Refactor
- Introduce a lightweight `DiscussionPromptBuilder` (under `core/services/` or `utils/`) that constructs reasoning/statement payloads from `GroupDiscussionState`, decoupling logic from `ParticipantAgent`.
- Migrate Phase2Manager to call the builder instead of mutating `_current_public_history`; pass state explicitly to avoid hidden globals.
- Update LanguageManager/ParticipantAgent to consume structured payloads (e.g., dataclass with `header`, `history`, `instructions`).
- Cover with service-level tests in `tests/unit/` to verify builder output for multiple rounds and languages.

### 3. Full History in Reasoning Prompts
- Extend `DiscussionService.build_internal_reasoning_prompt()` to accept a `history` parameter for all rounds; retire the "short" template or inject history into it.
- Update translation files so both long and short reasoning messages expose `{discussion_history}` (or replace short template with parameterised variant).
- Add regressions for multi-round scenarios ensuring history presence (`tests/golden/test_phase2_prompts.py`, `tests/unit/test_discussion_service.py`).

## Dependencies & Considerations
- Translation edits require sync across English, Spanish, Mandarin files; run localisation checks (`tests/component/test_language_translations.py`).
- Prompt builder introduction must stay compatible with the OpenAI Agents Runner context expectations; coordinate with any custom logging that reads `_current_public_history`.
- When modifying templates, confirm memory-update contexts remain lean to avoid bloating agent inputs.

## Next Steps
1. Prototype delimiter change and rerun prompt golden tests to validate styling fix.
2. Draft the `DiscussionPromptBuilder` API and gather feedback before refactoring call-sites.
3. Modify reasoning prompt templates and ensure regression coverage for all rounds.
