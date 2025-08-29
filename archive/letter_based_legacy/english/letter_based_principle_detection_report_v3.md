# Repository Audit: Letter-Based Principle Detection (EN/ES/ZH)

Date: 2025-08-29

## Executive Summary
- Active system logic and participant-facing prompts are letter-free for principle identification across English, Spanish, and Mandarin.
- Core parsing in `experiment_agents/utility_agent.py` accepts only canonical principle names (and multilingual variants); there is no active mapping for letters (a/b/c/d).
- `utils/language_manager.py` deprecates lettered principle lists and auto-substitutes to names-only when encountering `{principle_list_letters}`.
- Residual letter-based content remains in non-runtime or legacy artifacts (e.g., archived backups, missing translation scaffolds). These do not affect current execution but pose a regression/documentation drift risk.

## Scope & Method
- Searched the repo for letter cues and detection patterns in code, prompts, and translations (EN/ES/ZH) using ripgrep (patterns: principle a/b/c/d, (a)/(b)/(c)/(d), Spanish “principio a/b/c/d”, generic “letter/letters”, and key parser identifiers).
- Reviewed core parsing/validation logic, language manager list-generation, and translations for participant and utility prompts.

## Findings by Area

### 1) System Logic (Parsing, Detection, Validation)
- `experiment_agents/utility_agent.py`
  - Principle parsing is LLM-first (`parse_principle_choice_llm`) with JSON extraction in `_parse_llm_principle_response`.
  - Canonical validation set: `maximizing_floor`, `maximizing_average`, `maximizing_average_floor_constraint`, `maximizing_average_range_constraint`.
  - `_map_identifier_to_principle()` maps multilingual full names (EN/ES/ZH) and synonyms (e.g., “floor_constraint”, “range_constraint”) to canonical names. No letter mapping is present. Comments emphasize “NO LETTERS SUPPORTED”.
  - Preference detection fallbacks rely on descriptive/full-name cues (e.g., “floor constraint”, “range constraint”, “minimum income”, “income gap”); no letter regex present.
  - Consensus and ballot checks group by canonical principle and constraint amounts; no letter handling.
  - Note: The `_map_identifier_to_principle` docstring says “Supports full names and legacy letters” but implementation does not support letters. This is a documentation mismatch only.

- Vote/Agreement detection (`detect_vote_intention_enhanced`, `detect_agreement_multilingual`): unrelated to letter-based principle detection.

- Models (`models/principle_types.py`): canonical enums only; no letters.

### 2) Language Manager & Principle Lists
- `utils/language_manager.py`
  - `get_principle_list_formatted('detailed'|'simple'|'names_only')` renders principle names without letters.
  - `{principle_list_letters}` is explicitly marked deprecated and substituted with `names_only` automatically when encountered in a template.
  - This prevents lettered lists from appearing even if an old template string is used.

### 3) Translations & Prompts (EN/ES/ZH)
- English (`translations/english_prompts.json`)
  - Participant prompts for Phase 1 and Phase 2 show names-only; examples are letter-free.
  - Utility prompts:
    - `utility_validator_instructions`, `utility_parse_principle_choice`, `utility_parse_principle_ranking`, `utility_preference_detection`, and vote/agreement prompts are letter-free and reference full names/descriptions only.

- Spanish (`translations/spanish_prompts.json`)
  - Participant prompts mirror English: names-only, no letter references.
  - No evidence of letter encouragement in examples.

- Mandarin (`translations/mandarin_prompts.json`)
  - Participant prompts are names-only.
  - Utility prompts (e.g., `utility_secret_ballot_request`) present principles by names/descriptions; no letter references.

### 4) Legacy/Artifacts Containing Letters (Not Active at Runtime)
- `archive/english_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup`: explicit letter-based prompts and letter-only examples.
- `archive/README.md`: notes old letter-based flows; instructs using full names now.
- `translations/missing_batch1.json`: scaffolding snippets with letter-based guidance (“principle a/b/c/d”, etc.). These appear to be draft or tooling artifacts for missing keys, not loaded by `LanguageManager`.
- Older reports under `reports/letter_based_principle_detection_report.md` describe a pre-cleanup state where letters were accepted. Newer `report_v2.md` reflects the removal. Both coexist and can cause confusion.
- Some result artifacts mention “Distribution A/B/C/D” (non-principle labeling). No principle letters in active outputs.

## Risk Assessment
- Runtime risk: Low. Active code and shipped translations do not accept or encourage letter-based principle identification.
- Regression/documentation risk: Medium.
  - Artifacts with letter guidance could be mistaken for active templates.
  - Docstring in `_map_identifier_to_principle` suggests legacy letter support that no longer exists.
  - Coexisting reports (v1 vs v2) provide conflicting snapshots.

## Recommendations
- Update documentation to reflect the current behavior:
  - Fix `_map_identifier_to_principle` docstring to remove reference to legacy letters.
  - Add a short comment in `language_manager.py` clarifying the auto-substitution behavior for `{principle_list_letters}`.
- Quarantine or remove obsolete letter-based artifacts:
  - Move `translations/missing_batch1.json` and `archive/*LETTER_BASED*` to a clearly labeled `legacy/` folder or delete if unneeded.
  - Add a README note in `archive/` that these files are deprecated and not used by the runtime.
- Align reports:
  - Deprecate `reports/letter_based_principle_detection_report.md` (pre-cleanup). Link to this report and `report_v2.md` as current references.
- Optional guardrails:
  - Add a lightweight test that renders key prompts (EN/ES/ZH) and asserts absence of `(a)`, `(b)`, `(c)`, `(d)` in principle lists to prevent regressions.

## Evidence Index (selected)
- System logic:
  - `experiment_agents/utility_agent.py`: LLM-first parsing and `_map_identifier_to_principle` with NO letter mapping; comments emphasize “NO LETTERS SUPPORTED”.
  - `models/principle_types.py`: canonical enums only.
- Language manager:
  - `utils/language_manager.py`: `get_principle_list_formatted()` renders names; `{principle_list_letters}` deprecated and mapped to `names_only`.
- Translations:
  - EN: `translations/english_prompts.json` — participant and utility prompts are letter-free.
  - ES: `translations/spanish_prompts.json` — letter-free.
  - ZH: `translations/mandarin_prompts.json` — letter-free.
- Legacy/artifacts:
  - `archive/english_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup` — letter-heavy examples and instructions.
  - `translations/missing_batch1.json` — letter-based scaffolding for missing keys (not runtime-loaded).
  - `reports/letter_based_principle_detection_report.md` — pre-cleanup view; conflicts with newer state.

## Conclusion
The repository has effectively removed letter-based detection/presentation of justice principles in active code and shipped translations across English, Spanish, and Mandarin. Remaining references are confined to legacy or scaffolding files and outdated reports. Cleaning or clearly isolating those artifacts and updating minor documentation will finalize the transition and reduce the chance of reintroducing letter-based UX.

