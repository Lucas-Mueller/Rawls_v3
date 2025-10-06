# Translation and Language Consistency Audit

Date: 2025-09-02

Scope: Systematic scan of the experiment’s user-facing text across code and translations, focusing on language consistency (no mixed-language output) and consistent naming of justice principles in English, Spanish, and Mandarin. No code changes made.

## Summary of Key Findings

- Mixed-language principle lists: Mandarin and Spanish prompts render Chinese/Spanish principle names with English descriptions due to hardcoded English strings in `get_principle_list_formatted()`.
- Phase label shows English token (e.g., “Phase 1”) inside localized templates because `{phase}` is passed as a raw English string, and there are no translated `phase_names` in the JSON.
- Memory deltas and counterfactual insight messages are generated in English, even in non-English runs; translation keys exist but are not used.
- Spanish placeholders typo: uses `{best_principio}` and `{worst_principio}` vs expected `{best_principle}` and `{worst_principle}`.
- English naming inconsistency in prompts: several variants (“Maximizing Floor Income” vs “Maximizing the floor income”; “Maximizing Average Income” vs “Maximizing average”).
- Metadata in non-English translation files is in English (title/description/supported/default). This may be intentional, but if user-facing, it’s inconsistent.

## Detailed Findings (by area)

### 1) Principle Lists and Descriptions

- File: `utils/language_manager.py`
  - Function: `get_principle_list_formatted(list_type="detailed"|"simple")`
  - Issue: The principle NAMES are localized via `common.principle_names.*`, but the accompanying DESCRIPTIONS are hardcoded in English strings. This affects any prompt that expands `{principle_list_detailed}` or `{principle_list_simple}` in non-English languages.
  - Impacted prompts:
    - Mandarin: `prompts.phase1_round0_initial_ranking`, `prompts.phase1_rounds1_4_principle_application`, `prompts.phase1_application_round` (when using `{principle_list_*}`)
    - Spanish: `prompts.phase1_round0_initial_ranking`, `prompts.phase1_rounds1_4_principle_application`, and any prompt including `{principle_list_*}`

### 2) Phase Label and Round Labels

- Template: `translations/mandarin_prompts.json` → `prompts.context_context_info_format` (label “当前阶段：{phase}”)
- Problem: The `{phase}` value is passed as an English token (e.g., “Phase 1”), not a localized phrase.
- Code:
  - `utils/language_manager.py::format_context_info(...)` uses the provided `phase` string directly.
  - `LanguageManager.get_phase_name()` exists but there is no `common.phase_names` section defined in translation files, and `format_context_info` does not call it.
- Additional English tokens in memory/log context:
  - `core/services/memory_service.py` uses default `round_prefix` fallback “Round ” if translation key isn’t found. Translations do provide `round_prefix` in Spanish/Mandarin, but ensure all call sites use `language_manager.get("memory.round_prefix")`.

### 3) Memory Deltas and Counterfactual Insights (user-visible memory)

- File: `utils/memory_content.py`
  - `extract_phase2_counterfactual_insights(...)` returns English strings (e.g., “Best alternative: Would have earned…”; “Worst alternative: …”). There are corresponding translation keys in JSON:
    - English: `phase2_counterfactual_insights_*` (present)
    - Spanish: `phase2_counterfactual_insights_*` (present, but placeholders need fix; see below)
    - Mandarin: `phase2_counterfactual_insights_*` (present)
  - Current code does not consume those translation keys; it builds messages in English.
  - Other memory deltas contain English phrases:
    - “Two-Stage Voting - Stage 1: Principle Selection”, “Selected: … (Attempts: …)”, “FAILED - Unable to …”, “Your vote: …”, “No consensus - random assignment”. These appear in memory deltas produced by:
      - `build_two_stage_voting_principle_selection_delta(...)`
      - `build_two_stage_voting_amount_specification_delta(...)`
      - `build_two_stage_voting_complete_delta(...)`
    - These are likely visible to participants if memory is appended to the context, leading to mixed language.

### 4) Spanish Placeholder Typos (critical for formatting)

- File: `translations/spanish_prompts.json`
  - Keys:
    - `phase2_counterfactual_insights_best_more`: uses `{best_principio}` → should be `{best_principle}`
    - `phase2_counterfactual_insights_worst_more`: uses `{worst_principio}` → should be `{worst_principle}`
  - Consequence: `.format()` will raise KeyError or display literal placeholder if fed `{best_principle}/{worst_principle}`.

### 5) English Naming Variants (canonical vs. variants)

- Canonical English display names used by fallbacks in `core/principle_name_manager.PrincipleNameManager`:
  - “Maximizing Floor Income”
  - “Maximizing Average Income”
  - “Maximizing Average with Floor Constraint”
  - “Maximizing Average with Range Constraint”
- English prompt files have variants:
  - “Maximizing the floor income” / “Maximizing the floor”
  - “Maximizing the average income” / “Maximizing average”
  - Also mixed capitalization across different sections.
- Recommendation: Standardize English phrasing across `translations/english_prompts.json` to match canonical forms used in code fallbacks and menus.

### 6) Translation Metadata in Non-English Files

- Files: `translations/spanish_prompts.json`, `translations/mandarin_prompts.json`
  - Fields: `experiment_title`, `experiment_description`, `supported_languages`, `default_language` are in English.
  - If these are user-facing in UI/CLI, provide localized values. If programmatic only, this is optional.

### 7) Two-Stage Voting Prompts and Errors

- Two-stage voting prompts are retrieved via `LanguageManager` and appear properly localized in each language file. However, fallback error messages inside `get_two_stage_error_message()` are hardcoded in English for missing keys.
- Ensure all error keys used under `errors.two_stage_*` exist in non-English JSON to avoid English fallback.

## Cross-Checks Per File

- `translations/mandarin_prompts.json`
  - Good:
    - Names under `common.principle_names` are correct and consistent with canonical keys.
    - `language_instruction` localized.
    - `round_prefix` provided (“第”).
  - Issues:
    - Principle descriptions injected via `{principle_list_detailed}` / `{principle_list_simple}` are English (from code), causing mixed language in lists.
    - Phase token inside “当前阶段：{phase}” will show “Phase 1/2” (English) unless localized upstream.
  - Observed example: First prompt shows Chinese headers but English descriptions for the four principles.

- `translations/spanish_prompts.json`
  - Good:
    - Names under `common.principle_names` are correct.
    - `round_prefix` provided (“Ronda ”).
  - Issues:
    - `{principle_list_detailed}` / `{principle_list_simple}` will inject English descriptions (from code).
    - Placeholder typos `{best_principio}` / `{worst_principio}`.
    - Metadata fields English by default (optional to localize).

- `translations/english_prompts.json`
  - Issues:
    - Inconsistent English naming variants for principles in multiple sections (“Maximizing the floor income” vs canonical names). Should align with canonical forms.

- `utils/memory_content.py`
  - Issues:
    - English-only strings for counterfactual insights and two-stage voting deltas.
    - Likely user-visible as part of “memory” shown in context.

- `core/principle_name_manager.py`
  - Good:
    - Uses translated names via `language_manager.get_justice_principle_name()`; has English fallbacks.
  - Mixed:
    - Constraint formatting strings within `format_principle_with_constraint()` are localized, but the English fallback path is English-only (acceptable as fallback behavior).

- `core/services/memory_service.py`
  - Mixed:
    - Uses `round_prefix` from translations (good), with default fallback “Round ” (English) if missing.

## Fix Plan (Sequenced)

1) Localize Principle Descriptions in Lists
   - Add localized description strings for each principle under a new path, e.g., `common.principle_descriptions`:
     - floor, average, floor_constraint, range_constraint
   - Update `get_principle_list_formatted()` to compose lists by pulling both the localized name and localized description from translations, instead of hardcoded English.
   - Ensure both “detailed” and “simple” variants map to appropriate localized texts.

2) Localize Phase Names
   - Add `common.phase_names` to translation files with keys like `phase1`, `phase2` (and any others used).
   - Update `format_context_info(...)` to call `get_phase_name(phase_key)` or accept a phase key instead of a literal label, ensuring a localized `{phase}` value.
   - Audit all call sites where a raw “Phase 1/2” string is passed and replace with keys.

3) Localize Memory Deltas and Insights
   - Refactor `utils/memory_content.py` so user-visible strings are retrieved via `LanguageManager.get(...)` with keys:
     - For counterfactual insights: use `phase2_counterfactual_insights_*` already present in translations, and pass `{best_principle}` / `{worst_principle}` and diffs.
     - For two-stage voting deltas: add new translation keys for section headers, success/failure lines, attempts, and vote summaries (e.g., `memory.two_stage.stage1_header`, `memory.two_stage.selected`, `memory.two_stage.attempts`, `memory.two_stage.failed_selection`, `memory.two_stage.stage2_header`, `memory.two_stage.failed_amount`, `memory.two_stage.vote_info`, `memory.two_stage.no_consensus`, etc.).
   - Ensure formatting variables are consistent across languages.

4) Fix Spanish Placeholders
   - Replace `{best_principio}` → `{best_principle}` and `{worst_principio}` → `{worst_principle}` in `translations/spanish_prompts.json`.

5) Standardize English Canonical Names in Prompts
   - Replace non-canonical variants in `translations/english_prompts.json` with the canonical forms:
     - “Maximizing Floor Income”
     - “Maximizing Average Income”
     - “Maximizing Average with Floor Constraint”
     - “Maximizing Average with Range Constraint”
   - Ensure consistency across all sections (lists, examples, explanations).

6) Ensure Two-Stage Voting Errors Fully Localized
   - Verify that all `errors.two_stage_*` keys referenced in `get_two_stage_error_message()` exist in Spanish and Mandarin files to avoid English fallback.

7) Optional: Localize Metadata
   - If `experiment_title`, `experiment_description`, `supported_languages`, `default_language` are displayed to participants, provide localized versions. If they’re purely programmatic, leave as-is.

## Validation Plan

- Grep-based checks:
  - Search non-English outputs for English sentences in rendered prompts:
    - After changes, run the app in Spanish and Mandarin and capture the first round’s full prompt to confirm zero English sentences in lists and memory blocks.
  - Scan `utils/memory_content.py` for any remaining hardcoded English.
  - Ensure `get_principle_list_formatted()` contains no English prose.
- Unit/integration tests:
  - Add tests for `get_principle_list_formatted("detailed")` in Spanish/Mandarin asserting absence of ASCII-only English sentences and presence of localized descriptions.
  - Tests for `extract_phase2_counterfactual_insights` to use translation paths.
  - Test that `format_context_info(...)` uses localized phase names when provided (mock `common.phase_names`).

## Appendix: Representative Evidence

- Hardcoded English descriptions in code:
  - `utils/language_manager.py::get_principle_list_formatted()` returns English descriptions alongside localized principle names.
- English-only memory deltas:
  - `utils/memory_content.py`: “Two-Stage Voting - Stage 1: Principle Selection”, “Selected: …”, “FAILED - …”, “Best alternative: Would have earned …”.
- Phase token mixing:
  - `prompts.context_context_info_format` (Mandarin) shows “当前阶段：{phase}”, where `{phase}` is currently “Phase 1/2”.
- Spanish placeholder issues:
  - `translations/spanish_prompts.json` uses `{best_principio}` / `{worst_principio}` instead of `{best_principle}` / `{worst_principle}`.

---

No code has been changed in this audit. The above plan lists minimal, targeted changes to eliminate mixed-language occurrences and standardize naming across the experiment flow.

