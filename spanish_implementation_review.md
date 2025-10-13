# Spanish Implementation Review

## Key Findings
- Spanish prompts lag the English canonical structure by 36 keys, including all new counterfactual, consensus, and retry feedback strings; Mandarin shows the same drift, signalling the non-English packs were not resynced after the latest English refresh (`translations/english_prompts.json:339`, `translations/spanish_prompts.json:138`).
- Runtime paths already rely on the missing top-level keys, so Spanish runs either raise `KeyError` or fall back to generic English text in multiple services (`core/services/counterfactuals_service.py:585`, `core/services/discussion_service.py:303`, `core/phase2_manager.py:921`, `utils/memory_content.py:387`).
- Spanish normalization inside the utility agent only recognizes a single phrasing per principle and does not tolerate accent stripping or common synonyms, unlike the more defensive English heuristics (`experiment_agents/utility_agent.py:220`, `experiment_agents/utility_agent.py:236`).
- Test scaffolding and configs exist for Spanish, but they do not cover the new result and retry branches, so regressions went unnoticed (`config/test_retry_spanish_concise.yaml:12`, `tests/golden/test_memory_service_consistency.py`).

## Translation Coverage And Structure
The English file now hosts both top-level and nested prompt entries for new features, while Spanish and Mandarin only kept the legacy nested forms. A diff of fully qualified keys shows 36 paths missing from each non-English pack, notably:

| Key group | English source | Spanish state | Mandarin state | Impact |
| --- | --- | --- | --- | --- |
| `phase2_no_consensus` & counterfactual insight strings | `translations/english_prompts.json:342-345` | Only nested under `prompts` (`translations/spanish_prompts.json:138-143`), no top-level copy | Same as Spanish | Direct `language_manager.get("phase2_no_consensus")` and insight requests throw, forcing generic fallbacks. |
| `statement_validation_feedback.*` | `translations/english_prompts.json:171-189` | Still nested under `prompts` (`translations/spanish_prompts.json:153-170`) | Same | Discussion feedback generator cannot load localized templates, so Spanish users get English text. |
| `prompts.statement_validation_classification` | `translations/english_prompts.json:149` | Missing entirely | Missing | Utility agent reverts to an English fallback classification prompt. |
| `memory_field_labels.feedback_received` / `improved_response` | `translations/english_prompts.json:280-299` | Absent (`translations/spanish_prompts.json:280-299`) | Absent | Retry memory updates lose localized labels. |
| `memory_outcomes.statement_retry_successful` | `translations/english_prompts.json:310-317` | Missing (`translations/spanish_prompts.json:310-317`) | Missing | Retry success never logged in Spanish memories. |
| `results.class_probabilities_header` | `translations/english_prompts.json:374-387` | Missing (`translations/spanish_prompts.json:240-250`) | Missing | Probability block silently skipped in comprehensive results. |

The remaining reported “missing” keys (`context_stage_prompts.*`) exist in Spanish but only under `prompts`, confirming the file was not realigned when English gained mirror copies at the top level.

## Runtime Impact
- **Consensus messaging**: `core/services/counterfactuals_service.py:585` expects `phase2_no_consensus` at the root. In Spanish this raises a `KeyError`, so the fallback `fallback_messages.no_consensus_generic` (still English) is used.
- **Counterfactual insight bullets**: `utils/memory_content.py:387` and `utils/memory_content.py:404` request the new best/worst templates. Spanish lacks those keys outside `prompts`, so extracting detailed insights will crash once the helper is enabled globally.
- **Retry memory updates**: The retry recorder in `core/phase2_manager.py:921-923` inserts localized labels for “feedback received”, “improved response”, and the success outcome. Those labels are missing, so the block throws and the retry experience is not persisted for Spanish (and Mandarin) runs.
- **Statement validation coaching**: `core/services/discussion_service.py:303-358` loads localized instructions and headings. Because the structured keys live under `prompts` in Spanish, the feature downgrades to English phrasing. The same applies to the classification prompt at `experiment_agents/utility_agent.py:1051`.
- **Phase 2 probability table**: The detailed earnings builder (`core/services/counterfactuals_service.py:483`) swallows the missing header silently, so Spanish summaries omit the probability section that appears in English.

## Utility Agent & Parsing Parity
- Spanish normalization only accepts one canonical sentence per principle (`experiment_agents/utility_agent.py:220`) and the fallback heuristics still look for English substrings such as `"floor"` or `"constraint"` (`experiment_agents/utility_agent.py:236-244`). When agents respond with accentless variants (“maximizar ingreso minimo”) or regional phrasing captured in `tests/fixtures/phase2_parsing_fixtures.py:210-233`, the parser will miss the match.
- The Mandarin mapping is similarly strict, but the fallback checks Chinese characters (`experiment_agents/utility_agent.py:241-244`), so it survives common shorthand. Spanish lacks an equivalent accent-insensitive or synonym-aware path even though `docs/spanish_test_patterns.md` enumerates the variants that should be recognized.
- Agreement detection does include several Spanish synonyms (`experiment_agents/utility_agent.py:246-248`), so the gap is concentrated in principle normalization and constraint extraction.

## Configuration And Testing Parity
- Spanish retry config (`config/test_retry_spanish_concise.yaml:12`) exercises the concise feedback path, whereas English (`config/test_retry_english_detailed.yaml:12`) and Mandarin (`config/test_retry_mandarin_max.yaml:12`) cover detailed guidance and higher retry budgets. No suite asserts that the Spanish retry feedback strings actually exist, leaving the missing labels unnoticed.
- Golden tests under `tests/golden/` snapshot Spanish prompts for discussions, voting, and memory formatting, but they predate the counterfactual/feedback additions and therefore never touch the absent keys. The same is true for Mandarin, so the regression propagated across both translations.

## Additional Observations
- Spanish prompts consistently use the formal register (“usted”) while English mixes direct imperatives. Mandarin remains neutral. If future UX decisions shift voice, the difference should be called out explicitly in docs (`docs/spanish_test_patterns.md` vs `docs/chinese_test_patterns.md`).
- `translations/spanish_prompts.json` still carries legacy utility strings (`utility_string_parser_agent_name`, etc.) that were inlined elsewhere. English retains them too, but a follow-up cleanup could centralize these into the shared prompt builder.

## Recommendations
1. Re-sync Spanish and Mandarin JSON files with the English canonical structure, ensuring every new top-level key is duplicated where the runtime expects it (counterfactual insights, consensus strings, retry feedback).
2. Extend the Spanish principle normalization to tolerate accentless words and regional synonyms (e.g., normalize `mínimo/minimo`, `rango`, `restricción/limitación`) and add regression fixtures mirroring `docs/spanish_test_patterns.md`.
3. Add multilingual tests that hit the new retry feedback and counterfactual insight paths so future drift is detected (e.g., invoke `Phase2Manager._update_memory_with_retry_experience` under Spanish and assert the localized labels are present).
