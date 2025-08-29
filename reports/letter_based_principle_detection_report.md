# Repository Audit: Letter-Based Detection of Principles (All Languages)

## Executive Summary
- Letter-based presentation (a/b/c/d) and detection are still present in both prompts and system logic.
- Core parsing supports full principle names in English, Spanish, and Mandarin, but also retains letter mapping for backward compatibility.
- Prompts in multiple languages still reference letters directly or via the `{principle_list_simple}` / `{principle_list_letters}` templates.
- Backup/legacy prompt files with explicit letter flows remain in `translations/`, increasing the risk of regressions if restored.

Action: If the goal is to fully remove the letter system from UX while keeping compatibility in parsing, updates are needed in translations and a small cleanup in parser prompts; system logic can keep the fallback letter mapping.

---

## Principles Reference
- A: `maximizing_floor`
- B: `maximizing_average`
- C: `maximizing_average_floor_constraint`
- D: `maximizing_average_range_constraint`

---

## Findings by Area

### 1) System Logic (parsing, mapping, validation)
- `experiment_agents/utility_agent.py`
  - `_map_identifier_to_principle`: Explicit letter mapping exists for `a/b/c/d`. Also strips multilingual prefixes like `principle`, `principio` (ES), `原则` (ZH). Includes multilingual full-name keys (EN/ES/ZH) for all four principles.
  - `detect_preference_statement`: 
    - LLM-first prompt examples accept letter inputs.
    - Regex fallbacks detect letters (e.g., "my choice is b", "I prefer c").
  - `parse_principle_choice` / `parse_principle_choice_enhanced` / `parse_principle_choice_llm`:
    - LLM prompts mention legacy letters as acceptable references (EN).
  - Ranking parsing `_compile_ranking_patterns` only targets numbered lines; no letter usage here.

- `utils/language_manager.py`
  - `get_principle_list_formatted('simple')`: renders lettered options `(a)`, `(b)`, `(c)`, `(d)` with short descriptions.
  - `get_principle_list_formatted('letters_only')`: renders letters-only list for voting and other prompts.
  - These lists are injected when prompts contain `{principle_list_simple}` or `{principle_list_letters}`.

- Models/Logging
  - `models/logging_types.py` stores free-form strings such as `favored_principle`. Fixtures show outputs like "Principle A/B" being preserved from agent text.

Summary: Core logic purposefully supports letter mapping for compatibility. Letters are also surfaced by prompt templates, not just tolerated by the parser.

---

### 2) Translations and Prompts

- English (`translations/english_prompts.json`)
  - Prompts use `{principle_list_detailed}` (no letters) for initial ranking, but `{principle_list_simple}` for application flows; the latter injects `(a) ... (d)` letters via `language_manager`.
  - `utility_validator_instructions` and `utility_llm_parse_principle_choice` explicitly mention accepting legacy letters in addition to names/descriptions.
  - Format-improvement prompt encourages letter responses in examples (e.g., "principle a/b/c/d").

- Spanish (`translations/spanish_prompts.json`)
  - Uses `{principle_list_simple}` (lettered). Phase 1 application and other flows still reference letters in wording and examples.
  - Lacks or partly diverges from the latest English parser prompt style in places; format-improvement prompt examples include letters.

- Mandarin (`translations/mandarin_prompts.json`)
  - Largely uses full names for principles in user-facing sections.
  - Some utility prompts and examples still mention that letters (a/b/c/d) are acceptable references (legacy support messaging).

- Legacy/Backup files
  - `translations/english_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup` contains letter-heavy prompts, letter-only lists and explicit c/d constraint language. These are not active, but presence poses regression risk.
  - `translations/missing_batch1.json` includes multiple snippets with letter-based instructions for parsing and formatting.

Summary: Across languages, the UX still exposes letters through `{principle_list_simple}` or explicit examples. English and Spanish encourage letters more than Mandarin; Mandarin retains letter mentions in some utility prompts.

---

### 3) Tests and Artifacts
- `tests/fixtures/test_outputs/test_complex_mode_output.json` contains logs with agent text like "Principle A/B" in `favored_principle` fields; this indicates agents can and do produce letter phrasing, and the system logs it verbatim.
- No unit tests specifically assert letter-driven parsing, but parser pathways permit it.

---

## Coverage by Language: Where Letters Appear

- English
  - Prompt templates inject `(a)-(d)` via `{principle_list_simple}` and `{principle_list_letters}`.
  - Parser/validator prompts accept letter references for compatibility.
  - Examples in formatting prompts demonstrate letter usage.

- Spanish
  - Same template usage as English (letters in lists), with letter-based phrases in examples.
  - Parser prompts/examples use or imply letters; some missing parity with English’s newest JSON-style parser prompt.

- Mandarin
  - User-facing prompts typically use full names.
  - Utility prompts still note that letters can be used (backward compatibility), which may encourage letter responses.

---

## Risk Assessment
- UX consistency: Mixed guidance (letters vs. names) can confuse participants and models, leading to inconsistent outputs.
- Constraint mis-specification: Emphasizing letters for C/D can distract from stating the required constraint amounts.
- Regression risk: Backup/legacy files with letter-heavy prompts exist and could be reintroduced inadvertently.
- Internationalization: Spanish retains more letter emphasis; Mandarin mostly cleaned but mentions still exist in utility prompts.

---

## Recommendations
- Prompts
  - Replace `{principle_list_simple}` usages with a non-lettered version (new template or reuse detailed list) for all languages in user-facing instructions.
  - Remove explicit letter encouragement from examples while keeping natural-language and full-name examples.
  - Keep parser prompts tolerant of letters (for backward compatibility), but stop advertising them.

- Language Manager
  - Keep `letters_only` only if needed internally; avoid injecting it into participant-facing content.
  - Consider adding a `names_only` variant mirroring `simple` without `(a)-(d)`.

- Translations
  - English/Spanish: Update examples to show full names only; ensure constraint examples emphasize amounts clearly.
  - Mandarin: Remove residual mentions that letters are acceptable, unless strictly needed for compatibility notes in parser prompts.

- Hygiene
  - Clearly mark or remove `translations/*backup*` letter-based files to prevent accidental restoration.

- Testing
  - Add snapshot or string-based tests to assert prompts do not include letter lists in participant-facing contexts for each language.
  - Keep parser tests that verify letters still parse correctly for compatibility.

---

## Pointers to Code and Content
- Letter mapping and multilingual detection: `experiment_agents/utility_agent.py`
  - `_map_identifier_to_principle`
  - `detect_preference_statement` (regex fallbacks for letters)
  - `parse_principle_choice*` prompts accept letters (EN)
- Letter list injection: `utils/language_manager.py`
  - `get_principle_list_formatted('simple'|'letters_only')`
  - Used where prompts contain `{principle_list_simple}` / `{principle_list_letters}`
- Translations with letter examples/templates:
  - `translations/english_prompts.json`
  - `translations/spanish_prompts.json`
  - `translations/mandarin_prompts.json` (utility prompts mentioning letters)
  - Legacy backups: `translations/english_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup`, `translations/missing_batch1.json`
- Evidence in artifacts/tests: `tests/fixtures/test_outputs/test_complex_mode_output.json` (e.g., "Principle A/B" in logs)

---

## Conclusion
The codebase deliberately supports letter-based principle references across languages — both in parsing logic and in participant-facing prompts. If the design goal is to minimize or eliminate letters in UX, focus on replacing lettered lists/examples in translations and adjusting `language_manager` template usage. Maintain letter parsing in the utility agent for backward compatibility and robustness.

