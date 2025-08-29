# Repository Audit (v2): Letter-Based Detection of Justice Principles (All Languages)

## Executive Summary
- Participant-facing prompts are now letter-free across languages via `LanguageManager` updates.
- Core parsing in `UtilityAgent` no longer accepts letter identifiers; it requires full principle names (with multilingual mappings).
- Residual letter references remain in English utility prompts (parser/validator guidance) and in legacy/backup translation files and test fixtures.
- Non-principle letters are still used for distribution labels (A–D) in `core/original_values_data.py` — these are unrelated to principle selection.

Overall: Letter-based UX has been removed; parser now enforces full names. Cleanup remains for developer/LLM guidance text and backups to avoid mixed signals.

---

## What Changed Since Last Scan
- `utils/language_manager.py` now:
  - Renders `simple` lists without letters (names + descriptions only).
  - Treats `{principle_list_letters}` as deprecated and substitutes `names_only` automatically (no letters).
- `experiment_agents/utility_agent.py` now:
  - Validates principle values against canonical names only; mapping excludes letter identifiers.
  - Fallback regex for preference detection uses full-name cues only (e.g., “floor constraint”, “range constraint”).
  - Multilingual mappings (EN/ES/ZH) remain for canonical names.

---

## Current Letter-Based Occurrences (by area)

### A) Language and Prompt Templates
- utils/language_manager.py
  - Deprecation shim for `{principle_list_letters}` → maps to `names_only` (no letters).
  - `get_principle_list_formatted('simple')`: shows names only (no (a)/(b)/(c)/(d)).
  - `get_principle_list_formatted('names_only')`: names only (for voting prompts), no letters.

- translations/english_prompts.json
  - Participant prompts (Phase 1/2) use `{principle_list_simple}` which now renders names only.
  - Utility prompts still mention letters in examples/guidance:
    - `prompts.utility_validator_instructions`: lists “principle a/b/c/d” as acceptable references.
    - `prompts.utility_format_improvement_choice`: says “Which principle they chose (a, b, c, or d) … examples include (a)/(c)/(d)”.
    - `prompts.utility_llm_parse_preference_statement`: example includes “My preference is principle a …”.

- translations/spanish_prompts.json
  - Participant prompts use `{principle_list_simple}` (names-only now). No direct letter examples detected.

- translations/mandarin_prompts.json
  - Participant and utility prompts do not include letter references.

- Legacy translation files (risk of regression if reintroduced):
  - translations/english_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup
  - translations/spanish_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup
  - translations/missing_batch1.json (multiple snippets and examples still reference a/b/c/d)

### B) System Logic (parsing/validation)
- experiment_agents/utility_agent.py
  - Principle parsing (`parse_principle_choice_llm` + `_parse_llm_principle_response`) accepts only canonical names: `maximizing_floor`, `maximizing_average`, `maximizing_average_floor_constraint`, `maximizing_average_range_constraint`. Letter identifiers are no longer mapped.
  - `_map_identifier_to_principle` includes EN/ES/ZH name mappings, but no letter entries.
  - Preference detection fallback patterns use descriptive/full-name cues; letter regex has been removed.

- core/phase2_manager.py
  - No direct letter checks found in current code for ballot/consensus logic.

- core/original_values_data.py
  - Uses keys `"a".."d"` for distribution variants (Situations A–D). This is unrelated to principle-letter selection.

### C) Tests and Fixtures
- tests/fixtures/test_outputs/test_complex_mode_output.json
  - Contains `favored_principle` strings like “Principle A/B” from prior runs. These are artifacts, not active prompts/logic.

---

## Risk Assessment
- Mixed messaging: English utility prompts still suggest letters are acceptable, while the parser now enforces full names. This could confuse LLM-based parsers or contributors.
- Legacy file drift: Backup JSONs with letter-based prompts remain; accidental reintroduction could regress UX.
- Artifacts in fixtures may imply letter usage; harmless but can mislead reviewers.

---

## Recommendations
- English utility prompts:
  - Remove references to “principle a/b/c/d” in `utility_validator_instructions`, `utility_format_improvement_choice`, and `utility_llm_parse_preference_statement`. Present only full-name examples.
- Translations hygiene:
  - Archive or clearly mark `*_LETTER_BASED_VERSION_OUTDATED.json.backup` and `missing_batch1.json` to prevent reuse.
- Tests/fixtures:
  - Update fixtures to reflect name-based principles or add a note that letter phrasing is legacy.
- Continue to accept multilingual full names (EN/ES/ZH) and keep constraint extraction robust.

---

## Quick Pointers
- Names-only rendering and deprecation wiring:
  - utils/language_manager.py (list formatting and `{principle_list_letters}` handling)
- Canonical-name-only parsing:
  - experiment_agents/utility_agent.py (`parse_principle_choice_llm`, `_parse_llm_principle_response`, `_map_identifier_to_principle`)
- Residual letter examples (to update):
  - translations/english_prompts.json (utility prompts mentioned above)
  - translations/missing_batch1.json (multiple snippets)
- Non-principle letters (safe):
  - core/original_values_data.py (distribution setups A–D)

---

## Conclusion
The repository has effectively removed letter-based UX and parsing for justice principles, defaulting to full names across languages. Remaining letter mentions are confined to some English utility prompt guidance and legacy files. Cleaning those will finalize the transition and reduce any residual confusion.

