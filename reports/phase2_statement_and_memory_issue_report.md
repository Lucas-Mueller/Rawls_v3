# Phase 2 Statement/Memory Emptiness – Root Cause Analysis and Fix Proposal

## Summary
- Observed: During Phase 2, the internal reasoning step shows correct discussion history. However:
  - The “make your statement” output is perceived as empty in logs.
  - Immediate memory updates “right after statement” are empty.
  - Voting-phase memory insertions are empty.
  - End-of-round memory updates are correct.
- Root causes are primarily translation-key path mismatches in MemoryService and a minor key variant mismatch for voting.
- Proposed fix: Correct translation key paths and add safe fallback formatting in MemoryService. No overengineering or structural changes.

## Symptoms and Where They Originate
- Statement appears empty when asked to “make their statement”:
  - Statement text is produced via `DiscussionService.get_participant_statement_with_retry()` and is appended to public history with `GroupDiscussionState.add_statement(...)`.
  - Public history formatting uses `discussion_format.round_speaker_format` which exists in all translation files, so history displays are correct.
  - The perceived “emptiness” generally shows up in follow‑up prompts and memory logs that embed the latest statement (see next bullets).
- Immediate memory update after statement is empty:
  - Implemented in `MemoryService.update_discussion_memory(...)` (core/services/memory_service.py).
  - Builds content using non‑existent translation paths, resulting in empty or failed content prior to passing to `SelectiveMemoryManager`.
- Voting process memory insertions are empty:
  - `MemoryService.update_voting_phase_memory(...)` uses a `_with_initiator` key variant that does not exist in translations.
  - This can fail and be skipped (warnings logged), leading to “empty” voting-phase memory markers.
- End‑of‑round memory updates are correct:
  - These go through `MemoryManager.prompt_agent_for_memory_update(...)` which uses existing `prompts.*` keys and a robust fallback path. Hence they succeed.

## Systematic Investigation
- Statement and reasoning flow
  - Code path: `Phase2Manager._process_participant_statement(...)` → `DiscussionService.get_participant_statement_with_retry(...)`.
  - Discussion prompt uses `prompts.phase2_discussion_prompt` (exists in translations), and internal reasoning prompt uses `prompts.phase2_internal_reasoning` (exists).
  - Public history formatting uses `discussion_format.round_speaker_format` (exists). Therefore statements are captured and appended correctly.
- Immediate discussion memory update
  - Code path: `Phase2Manager._update_participant_memory_and_context(...)` → `MemoryService.update_discussion_memory(...)`.
  - Current code calls `language_manager.get("memory.round_statement_format", ...)` and `language_manager.get("memory.internal_reasoning_format", ...)`.
  - Actual translation keys are top‑level: `round_statement_format` and `internal_reasoning_format` (no `memory.` namespace). See translations/*_prompts.json.
  - Result: KeyError or missing content before the update is sent to `SelectiveMemoryManager`, producing empty memory insertions.
- Voting-phase memory
  - Code path: `MemoryService.update_voting_phase_memory(...)`.
  - When `initiator_name` is present, code tries `voting_phases.{phase_name}_with_initiator`.
  - Actual translations only define `voting_phases.initiation` (already templated with `{initiator_name}`), `voting_phases.confirmation`, `voting_phases.secret_ballot`, `voting_phases.results` — no `_with_initiator` variants.
  - Result: Missing-key lookups lead to skipped updates (warnings), perceived as empty voting memory.

## Root Causes
- Incorrect translation key paths in MemoryService:
  - `memory.round_statement_format` → should be `round_statement_format` (top-level)
  - `memory.internal_reasoning_format` → should be `internal_reasoning_format` (top-level)
- Nonexistent `_with_initiator` translation variants:
  - `voting_phases.{phase_name}_with_initiator` → no such keys in translations; use `voting_phases.initiation` with `{initiator_name}` formatting instead.
- Absence of safe get/fallback in MemoryService before formatting strings increases fragility compared to Discussion/Voting services which wrap lookups with a fallback method.

## Focused Fix (Not Overengineered)
1. MemoryService: correct key paths for discussion-round memory content
   - In `update_discussion_memory(...)`:
     - Replace `self.language_manager.get("memory.round_statement_format", ...)` with `self.language_manager.get("round_statement_format", ...)`.
     - Replace `self.language_manager.get("memory.internal_reasoning_format", ...)` with `self.language_manager.get("internal_reasoning_format", ...)`.
2. MemoryService: fix voting-phase message lookup
   - In `update_voting_phase_memory(...)`:
     - If `initiator_name` is provided and `phase_name == "initiation"`, call `self.language_manager.get("voting_phases.initiation", initiator_name=initiator_name)`.
     - Otherwise, call `self.language_manager.get(f"voting_phases.{phase_name}")`.
     - Do not use `_with_initiator` suffix.
3. MemoryService: add a tiny safe-get helper (optional but recommended)
   - Mirror `DiscussionService._get_localized_message()` pattern to catch missing keys and return `[MISSING: <key>]` placeholders instead of raising.
   - Use this safe-get just for MemoryService’s own pre-formatting strings to avoid hard failures.

These changes are local, minimal, and align with existing translation files and the other services’ patterns.

## Validation Plan
- Unit smoke checks (no network required):
  - Reference the three calls in MemoryService and verify `LanguageManager.get(...)` resolves without KeyError using English/Spanish/Mandarin.
- Targeted integration run (short):
  - Run a single Phase 2 round and confirm:
    - Public history shows non-empty “Speaker/Statement” lines (unchanged behavior).
    - Immediate memory update after statement contains the statement and optional reasoning in the localized format.
    - Voting-phase memory entries show non-empty initiation/confirmation/ballot status strings.
    - End-of-round memory updates remain correct.
- Log sampling: confirm process logs no longer show warnings about missing keys for those paths.

## Possible Side Effects
- None expected beyond the intended behavior restoration. Translation paths match current files.
- If custom/non-English files diverge, the safe-get helper prevents crashes and surfaces `[MISSING: ...]` placeholders.

## References (Key Code Locations)
- MemoryService (core/services/memory_service.py)
  - `update_discussion_memory(...)` and `update_voting_phase_memory(...)` – incorrect keys
- DiscussionService (core/services/discussion_service.py)
  - Healthy pattern for `_get_localized_message()` and correct prompt usage
- GroupDiscussionState (models/experiment_types.py)
  - Uses `discussion_format.round_speaker_format` (present in all translations)
- Translations (translations/*_prompts.json)
  - `round_statement_format`, `internal_reasoning_format` (top-level)
  - `voting_phases.*` (no `_with_initiator` variants)

## Next Steps
- If you’d like, I can implement the key-path corrections and the safe-get wrapper in MemoryService, then run a quick local verification to confirm the emptiness issues are resolved.

