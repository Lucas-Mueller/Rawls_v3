**Summary**
- **Symptom:** In `experiment_results_20250827_131625.json`, Phase 2 round logs show `favored_principle` as a localized “unspecified” placeholder (Mandarin: “未说明”) instead of a detected principle.
- **Impact:** Phase 2 discussion logs and memory deltas lose signal on participant stance; downstream analyses relying on favored principle from rounds become weaker. Final vote consensus still resolves via secret ballots, but visibility into preference evolution is degraded.

**Evidence**
- Log file: `experiment_results_20250827_131625.json`
  - `general_information.consensus_principle`: `maximizing_average` (consensus detected)
  - Phase 2 rounds contain entries with `"favored_principle": "未说明"` (e.g., lines around 159, 328, 338 via ripgrep).
- Code path that sets `favored_principle`:
  - `core/phase2_manager.py::_extract_favored_principle`
    - English-only keyword heuristics: checks for “principle a/b/c/d”, “maximizing floor/average”, “floor constraint”, “range constraint”.
    - On no match, returns `language_manager.get("prompts.phase2_default_constraint_specification")` → localized “Not specified” (Mandarin: “未说明”).
- Translations:
  - `translations/mandarin_prompts.json`: `"phase2_default_constraint_specification": "未说明"`.
  - Group discussion and agent messages are in Mandarin; therefore English-only detection fails and defaults.

**Root Cause**
- The favored principle extraction in Phase 2 uses English-only string heuristics and returns letter labels (“Principle A/B/C/D”) for matches. In a Mandarin run, these heuristics do not fire, so the method returns a localized “unspecified” placeholder.
- Additionally, LLM-based principle parsing utilities exist but are not used here. The utility agent already supports multilingual parsing for principle choice/ranking; Phase 2 logging should reuse it instead of ad-hoc heuristics.
- Secondary fragility: LLM parsing helper `_parse_llm_principle_response` in `utility_agent.py` looks for the English anchor `"PRINCIPLE_DETECTED:"`. However, the localized prompts in Mandarin instruct the model to output `检测到原则：...`. This mismatch can force fallbacks and reduce robustness in multilingual runs.

**System-Level Notes**
- Memory deltas (`utils/memory_content.build_phase2_delta`) embed `favored_principle` as provided. With the current fallback, memories will contain “未说明”, reducing interpretability across rounds.
- Voting and consensus: Secret ballot prompt is properly localized (`prompts.utility_secret_ballot_request`). Ballot parsing typically succeeds via the utility agent. The observed consensus `maximizing_average` may be correct per ballots even if earlier discussion text praised constraint principles; the code includes a cross-check (`utility_agent.validate_consensus_against_discussion`) to flag mismatches in logs.

**Recommendations (Concise Changes)**
- 1) Make favored principle detection multilingual and canonical
  - Replace heuristic in `Phase2Manager._extract_favored_principle` with a call to the utility agent parser.
  - Return normalized principle keys (`maximizing_floor`, `maximizing_average`, `maximizing_average_floor_constraint`, `maximizing_average_range_constraint`) for logs, or mapped localized names via `language_manager.get_justice_principle_name`.
  - Fallback to a dedicated key like `prompts.phase2_favored_principle_unspecified` instead of reusing the constraint placeholder.

  Minimal patch sketch:
  - Change `_extract_favored_principle` to async and use the utility agent:
    ```python
    # core/phase2_manager.py
    async def _extract_favored_principle_async(self, statement: str) -> str:
        try:
            parsed = await self.utility_agent.parse_principle_choice_enhanced(statement)
            return parsed.principle.value  # canonical key for logging
        except Exception:
            return get_language_manager().get("prompts.phase2_favored_principle_unspecified")
    ```
  - In the discussion loop, `favored_principle = await self._extract_favored_principle_async(statement)` and pass it to `logger.log_discussion_round(...)`.

- 2) Standardize LLM parsing anchors across languages
  - Option A (preferable): Update localized prompts (`utility_llm_parse_principle_choice`, `utility_llm_parse_preference_statement`, etc.) to instruct responses always to include the English anchors and canonical keys, e.g., `PRINCIPLE_DETECTED: maximizing_average_floor_constraint` regardless of UI language. This keeps the parser simple and language-agnostic.
  - Option B: Extend `_parse_llm_principle_response` to recognize localized anchors:
    - Mandarin: `检测到原则：`
    - Spanish: `PRINCIPIO_DETECTADO:`
    - Falls back to English.
  - Keep the returned principle identifiers in the canonical set.

- 3) Improve heuristic fallback (optional but cheap)
  - If retaining a sync heuristic fallback, add multilingual keyword maps:
    - Mandarin examples:
      - Floor: `"最大化最低收入"`, `"底线"`
      - Average: `"最大化平均收入"`, `"平均"`
      - Floor constraint: `"最低收入约束"`, `"底线约束"`
      - Range constraint: `"范围约束"`, `"差距限制"`
    - Map to canonical keys and use only if utility parsing is unavailable.

- 4) Logging consistency
  - Avoid storing “Principle A/B/C/D” letter labels in logs; prefer canonical keys for analysis, and display localized names where needed using `language_manager`.
  - Introduce `prompts.phase2_favored_principle_unspecified` to avoid reusing `phase2_default_constraint_specification`.

**Risk/Benefit**
- Low-risk, localized change; minimal surface area. Using the existing utility agent for parsing aligns behavior across phases and languages. Standardizing LLM output anchors reduces a class of silent failures.

**Validation Steps**
- Run an experiment in Mandarin and confirm:
  - Phase 2 logs populate `favored_principle` with canonical keys or localized names, not “未说明”.
  - Memory deltas include the detected favored principle.
  - Ballot parsing still yields the same consensus; cross-check warning logs from `validate_consensus_against_discussion` if discussion content suggests a different principle.

**Appendix: Relevant Pointers**
- `core/phase2_manager.py`: `_extract_favored_principle` and discussion loop where it’s used.
- `experiment_agents/utility_agent.py`: `parse_principle_choice_enhanced`, `_parse_llm_principle_response`.
- `utils/language_manager.py`: translation getters, canonical principle names, and English-only name helpers.
- `translations/*_prompts.json`: `phase2_default_constraint_specification`, `utility_secret_ballot_request`, `utility_llm_parse_principle_choice`.

