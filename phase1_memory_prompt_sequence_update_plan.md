# Phase 1 Memory Prompt Sequencing Update Plan

## Overview
Refine Phase 1 prompt sequencing so every participant sees the long introduction on the very first agent exchange and again on the first memory update, then receives the shorter two-phase reminder on each subsequent Phase 1 memory update across every supported language.

## Current Behavior
- `utils/language_manager.py:430` (`format_context_info`) uses a per-phase first-turn tracker; Phase 1 memory updates get the long explanation once and an empty string afterwards, so later memory updates lack any reminder.
- `utils/memory_manager.py:329` (`_create_memory_update_prompt`) checks `context.first_memory_update` and injects the short explanation on the first Phase 1 memory update instead of the long one, leaving later updates blank because `experiment_explanation` stays empty.
- Translation resources already expose `prompts.initial_experiment_explanation` and `prompts.experiment_explanation` in English, but Spanish and Mandarin files presently point `prompts.experiment_explanation` to a passthrough placeholder, so the short reminder would still be empty for those locales.
- **Newly Observed Issue (post-implementation)**: `experiment_agents.update_participant_context()` rebuilds `ParticipantContext` instances without preserving `first_memory_update`, so every memory update behaves as if it were the first. After introducing the long/short logic this causes the long introduction to reappear on every memory update call. The flag must persist across context refreshes to unlock the short reminder behaviour.

## Desired Behavior
1. First Phase 1 agent call → long introduction (`initial_experiment_explanation`).
2. First Phase 1 memory update → long introduction.
3. All remaining Phase 1 memory updates → short reminder (`experiment_explanation`).
4. Phase 2 logic and other interaction types remain unchanged.

## Proposed Changes
- **Memory prompt assembly** (`utils/memory_manager.py:329-339`)
  - Keep relying on `context.first_memory_update` for the first-update check.
  - When the flag is true and the phase is `phase_1`, fetch `initial_experiment_explanation`; when false, fetch `experiment_explanation` so follow-up memory updates get the short reminder.
  - Ensure the method still returns an empty string for non-Phase-1 contexts that do not need explanations.
- **Context header formatting** (`utils/language_manager.py:430-496`)
  - Adjust the Phase 1 memory-update branch to set `experiment_explanation` to the long text on the first turn and the short text on subsequent turns, keeping the existing behavior for all other roles/phases.
  - Verify phase string comparisons (`"Phase 1"` vs. `"phase_1"`) stay consistent with upstream callers.
- **Translation resources** (`translations/english_prompts.json`, `translations/spanish_prompts.json`, `translations/mandarin_prompts.json`)
  - Confirm each file contains the full long and short strings.
  - Replace the Spanish and Mandarin `prompts.experiment_explanation` placeholders with localized short explanations so the new logic renders correctly.
- **Flag lifecycle review** (`utils/memory_manager.py`, Phase 1 manager, `experiment_agents.update_participant_context`)
  - Reconfirm `context.first_memory_update` flips to `False` after the first update (current code around `utils/memory_manager.py:150-190`) and persists when the context is recreated via helper utilities.
  - Update `update_participant_context()` (and any other context factories) to carry forward `first_memory_update` so subsequent calls can reliably switch to the short reminder.

## Testing Strategy
- Extend or add unit coverage in `tests/unit/test_memory_manager.py` (and any language manager tests) to assert the long/short swap based on the first-update flag and phase.
- Run targeted integration smoke tests for Phase 1 in English, Spanish, and Mandarin to verify prompt contents.
- Spot-check manual experiment runs (or captured logs) to ensure Phase 2 behavior is unchanged.

## Risks & Mitigations
- **Translation gaps**: Missing or placeholder short explanations would surface as blank prompts—addressed by auditing and updating each locale before code changes.
- **Phase detection mismatches**: Divergent phase labels could bypass the new logic—mitigate by tracing inputs from Phase 1 manager and adding assertions/tests.
- **Context reconstruction resets**: Helper utilities that rebuild `ParticipantContext` may drop future tracking fields; add regression tests to ensure `first_memory_update` stays stable after updates.
- **Regression in other roles**: Changes must leave discussion/voting prompts untouched—guard with unit tests covering non-memory-update paths.
