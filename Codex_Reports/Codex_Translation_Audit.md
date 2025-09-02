# Codex Translation & i18n Audit Report

- Scope: Full experiment flow (Phase 1 + Phase 2), refactored services, voting, distribution, memory utils, language manager, and agent utilities.
- Goal: Identify (1) hardcoded English text sent to participant agents, (2) missing translations for Spanish and Mandarin.
- Result: Found multiple hardcoded-English fallbacks and several missing keys (especially for Phase 1 memory labels and Phase 2 voting/results messages).

## Summary
- Hardcoded English sent to agents: Yes (MemoryService final result and internal reasoning lines; TwoStageVotingManager fallbacks for ballot prompts, timeouts, and validation errors).
- Missing translation keys: Yes (Mandarin/Spanish Phase 1 memory_field_labels; Phase 2 voting tags; Phase 2 results/principle display keys).
- Root cause for your Mandarin failure: Missing keys under `memory_field_labels` (e.g., `chosen_principle`) — translation loader works, the keys are absent.

---

## Hardcoded English Sent to Agents

These strings go into prompts/memory content that are ultimately fed to the participant LLMs (via `Runner.run` or agent `update_memory`).

- core/services/memory_service.py
  - Discussion memory text (sent to agent memory update):
    - Around 180–206: generates lines such as:
      - `Round {round_num}: Your statement: {statement}`
      - `Internal reasoning: {internal_reasoning}`
    - These are English and not sourced from translations. They are included in `content` passed to `SelectiveMemoryManager.update_memory_selective` and thus to `ParticipantAgent.update_memory` → `Runner.run`.
  - Final results memory text:
    - Around 314–327: `formatted_content = f"Final Phase 2 Results: {result_content}"` is English.
  - Truncation logic relies on English markers:
    - Around 341, 366–372: Detects `Internal reasoning:` prefix to truncate. This is brittle if localized.

- core/two_stage_voting_manager.py
  - Fallback prompts (used when language manager fails):
    - ~782–790: Principle selection fallback (English):
      - "A vote has been initiated. Which of the four principles…"
      - "Respond with ONLY the number (1, 2, 3, or 4):"
    - ~793–799: Amount specification fallback (English):
      - "Please state the amount in dollars…"
      - "Respond with the amount (examples: 25000 or $25000):"
  - Error/timeout messages (fallback, English):
    - ~802–829: Validation messages like
      - "Invalid response (attempt …). You must respond with exactly one number…"
      - "Use digits…", "Zero is not a valid…", "No monetary amount found…"
    - ~318 and ~439: Timeout fallback string: "Response timed out. Please try again."

- core/phase2_manager.py
  - Most direct strings now routed to services, but legacy code previously constructed English phrases. Current English strings originate in MemoryService as above.

Remediation
- Move English strings from MemoryService to translation keys (labels for round statement, internal reasoning, final results header) and update truncation to use localized labels or structured markers.
- Ensure TwoStageVotingManager timeout/error fallbacks also request localized strings via `language_manager`, so the English fallbacks are never used.

---

## Missing Translation Keys (Spanish + Mandarin)

### A) Phase 1 memory_field_labels (cause of Mandarin failure)
- Code reference: core/phase1_manager.py ~439–460 uses:
  - `memory_field_labels.prompt`
  - `memory_field_labels.your_response`
  - `memory_field_labels.chosen_principle`
  - `memory_field_labels.constraint_amount`
  - `memory_field_labels.assigned_class`
  - `memory_field_labels.earnings`
  - `memory_field_labels.original_values_situation`
  - `memory_field_labels.distribution_multiplier`
  - `memory_field_labels.outcome`
  - `memory_outcomes.applied_principle_round` (and other outcomes during Phase 1)

- Translation presence checks (jq):
  - English: present for all above keys.
  - Spanish: missing — chosen_principle, constraint_amount, assigned_class, earnings, original_values_situation, distribution_multiplier.
  - Mandarin: missing — chosen_principle, constraint_amount, assigned_class, earnings, original_values_situation, distribution_multiplier.

- Impact
  - Directly triggers: "Translation path not found: 'memory_field_labels.chosen_principle' in Mandarin".
  - Other missing labels would fail later in Phase 1.

- Action
  - Add the missing `memory_field_labels.*` keys to translations/spanish_prompts.json and translations/mandarin_prompts.json with localized values.

### B) Phase 2 voting messages (public history)
- Code reference: core/services/voting_service.py ~300–308, ~360–395 uses:
  - `system_messages.voting.all_confirmed` — MISSING (EN/ES/ZH)
  - `system_messages.voting.voting_declined` — MISSING (EN/ES/ZH)
  - `system_messages.voting.consensus_tag` — MISSING (EN/ES/ZH)
  - `system_messages.voting.no_consensus_tag` — MISSING (EN/ES/ZH)
  - Note: `system_messages.voting.result_tag`, `.result_summary`, `.agreed_principle` are present.

- Impact
  - When these keys are invoked, they will raise translation errors.

- Action
  - Add the 4 missing `system_messages.voting.*` keys in all languages.

### C) Phase 2 results formatting keys
- Code reference: core/services/counterfactuals_service.py
  - Uses:
    - `results.phase2_header` — PRESENT (EN/ES/ZH)
    - `results.assigned_income_class` — MISSING (EN/ES/ZH)
    - `results.counterfactuals_header` — MISSING (EN/ES/ZH)
    - `principles.maximizing_floor` — MISSING (EN/ES/ZH)
    - `principles.maximizing_average` — MISSING (EN/ES/ZH)
    - `principles.maximizing_average_with_floor` — MISSING (EN/ES/ZH)
    - `principles.maximizing_average_with_range` — MISSING (EN/ES/ZH)
  - It also uses `common.income_classes.{assigned_class}` — PRESENT (EN/ES/ZH)

- Observed mismatch
  - Translations define principle names under `principle_names.*` (also `common.principle_names.*`), but CounterfactualsService expects `principles.*`.

- Impact
  - Missing keys during Phase 2 results composition; errors or degraded display.

- Actions (choose one)
  - Preferably change CounterfactualsService to reference `principle_names.*` consistently with Phase 1.
  - Or add new entries under `principles.*` in all language files.
  - Add `results.assigned_income_class` and `results.counterfactuals_header` in all language files.

### D) Confirmed present keys (no action required)
- Discussion prompts & voting prompts:
  - `prompts.phase2_discussion_prompt`, `prompts.phase2_internal_reasoning`, `voting_prompts.internal_reasoning_section`, `voting_prompts.reasoning_prompt`
  - `prompts.vote_initiation_prompt`, `prompts.vote_initiation_with_statement_prompt`
  - `prompts.utility_voting_confirmation_request`
- Distribution display:
  - `prompts.distribution_distributions_table_header`, `prompts.distribution_distributions_table_column_header`, `prompts.distribution_distributions_table_separator`
- Group composition:
  - `system_messages.discussion.group_composition`
- Common income classes:
  - `common.income_classes.high|medium_high|medium|medium_low|low`

---

## Code References (selected)
- Phase 1 round content generation:
  - core/phase1_manager.py ~439–460
- Voting service consensus/no-consensus and confirmation history:
  - core/services/voting_service.py ~300–308, ~360–395
- Phase 2 results and counterfactuals display:
  - core/services/counterfactuals_service.py (header, income class label, counterfactuals header, principle names)
- Memory service English strings and truncation dependency:
  - core/services/memory_service.py ~180–206, ~314–327, ~341, ~366–372
- Two-stage voting fallbacks and messages:
  - core/two_stage_voting_manager.py ~318, ~439, ~782–829

---

## Remediation Checklist

1) Phase 1 (add to ES/ZH)
- memory_field_labels.chosen_principle
- memory_field_labels.constraint_amount
- memory_field_labels.assigned_class
- memory_field_labels.earnings
- memory_field_labels.original_values_situation
- memory_field_labels.distribution_multiplier

2) Phase 2 Voting (add to EN/ES/ZH)
- system_messages.voting.all_confirmed
- system_messages.voting.voting_declined
- system_messages.voting.consensus_tag
- system_messages.voting.no_consensus_tag

3) Phase 2 Results (add to EN/ES/ZH or update code)
- results.assigned_income_class
- results.counterfactuals_header
- principles.maximizing_floor
- principles.maximizing_average
- principles.maximizing_average_with_floor
- principles.maximizing_average_with_range
  - Alternatively, switch code to use `principle_names.*` (preferred for consistency with Phase 1).

4) Reduce English in agent-facing text
- Move MemoryService strings to translation keys; update truncation logic to match localized prefixes, or use structured markers that are language-agnostic.
- Ensure TwoStageVotingManager always gets timeout/error messages from language_manager instead of hardcoded fallbacks.

---

## Notes
- The Mandarin error confirms translation files are loaded. Failures stem from missing keys rather than “translations not being loaded”.
- Aligning principle name keys between Phase 1 and Phase 2 (favor `principle_names.*`) will reduce drift and maintenance overhead.
- Consider a CI check: verify all required keys exist across languages, especially when adding new code that references translation keys.

