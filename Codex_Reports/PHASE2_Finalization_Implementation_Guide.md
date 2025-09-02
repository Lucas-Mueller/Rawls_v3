# Phase 2 Finalization — Implementation Guide

Purpose: Convert the refactor into a clean, fully consolidated Phase 2 flow that always goes through services, with configurable behavior, consistent memory updates, and guardrail tests.

## TL;DR (Engineer Checklist)

- [completed] Make discussion history limit configurable via `Phase2Settings.public_history_max_length` (not hard-coded).
- [partial] Route remaining “simple” memory writes (ballot selection, amount specification) through `MemoryService` instead of `SimpleMemoryManager`.
- [completed] Add a focused integration test that asserts vote-initiation decisions are written by `MemoryService`.
- [completed] Retire the now-unused `refactored_services_enabled` flag from settings and any stale wrappers (if any remain elsewhere).
- [partial] Update docs to reflect the services-only architecture and the configurable history limit.

---

## 1) Configurable Discussion History Limit

Status: completed

Goal: Use config to control how much public discussion history is kept before truncation.

- Files:
  - `core/services/discussion_service.py`
  - `config/phase2_settings.py`

- Steps implemented:
  - `DiscussionService.manage_discussion_history_length()` now reads `self.settings.public_history_max_length` directly for both threshold and truncation size.
  - The previous hard-coded `100000` constant was removed.

- Example change (DiscussionService):
  - Before:
    - `self.max_history_length = 100000`
  - After:
    - `self.max_history_length = self.settings.public_history_max_length`

- Acceptance criteria:
  - Changing `phase2_settings.public_history_max_length` in config changes truncation behavior without code changes.
  - No regressions in prompt generation or history logging.

---

## 2) Centralize “Simple” Memory Writes in MemoryService

Status: partial

Goal: Eliminate direct `SimpleMemoryManager` calls for ballot selection and amount specification; use `MemoryService` for consistent truncation and guidance styles.

- Files:
  - `core/services/memory_service.py`
  - `core/services/voting_service.py` (or `core/two_stage_voting_manager.py`, depending on where events are finalized)
  - `utils/selective_memory_manager.py` (to remove residual `SimpleMemoryManager` calls for these events)

- Steps implemented:
  - New methods exist in `MemoryService`:
    - `update_ballot_selection_memory(...)` at core/services/memory_service.py:485
    - `update_amount_specification_memory(...)` at core/services/memory_service.py:524
  - `utils/selective_memory_manager.py` no longer imports or calls `SimpleMemoryManager`; simple events append preformatted content.

- Remaining work:
  - Call `MemoryService.update_ballot_selection_memory` and `update_amount_specification_memory` from the voting flow when those events occur:
    - Preferred: `VotingService` or `TwoStageVotingManager` invokes these methods at the moment of ballot choice and amount specification.
  - Confirm that preformatted content paths actually run (add or adjust unit tests around ballot/amount writes).

- Acceptance criteria:
  - No direct `SimpleMemoryManager.insert_secret_ballot_choice` or `.insert_amount_specification` calls in the codebase (outside MemoryService internals, if any).
  - Ballot/amount memory lines match current phrasing but now flow through MemoryService (benefits from truncation/guidance).

---

## 3) Guardrail Integration Test (MemoryService Write Path)

Status: completed

Goal: Ensure vote-initiation decisions are written via `MemoryService`, guarding against regressions.

- Files:
  - `tests/integration/test_phase2_memory_write_paths.py`

- Steps:
  - Arrange: Create a minimal Phase 2 config with 2 participants, 1–2 rounds, and deterministic behavior (seeded).
  - Patch `MemoryService.update_vote_initiation_decision_memory` with `AsyncMock` to track calls.
  - Run `Phase2Manager.run_phase2(...)` until end-of-round vote prompting triggers.
  - Assert: The `MemoryService` method was called for each participant; verify the written decision aligns with the prompt response.

- Acceptance criteria:
  - Test passes locally and fails if the manager reintroduces a direct `SimpleMemoryManager` call.

---

## 4) Retire `refactored_services_enabled` Flag

Status: completed

Goal: Simplify configuration surface; services are now always used.

- Files:
  - `config/phase2_settings.py`
  - Any stale wrappers or conditionals in code paths outside `Phase2Manager` (most were already removed).

- Steps implemented:
  - `refactored_services_enabled` has been removed from `Phase2Settings`.
  - Orchestrator and services no longer gate behavior on this flag.

- Acceptance criteria:
  - No behavior changes; fewer conditional branches; no references to the flag in orchestrator code.

---

## 5) Documentation and Logging Consistency

Status: partial

Goal: Reflect the services-first architecture and keep logs consistent.

- Files:
  - `README.md` or project docs location
  - `PHASE2_Refactor_Alignment_Assessment.md` (already updated; keep in sync)

- Suggested steps:
  - Document: Ownership boundaries (DiscussionService, VotingService, MemoryService, SpeakingOrderService, CounterfactualsService) and the configurable history limit.
  - Verify `process_logger` still receives round start/complete and voting results; leave breadcrumbs for debugging (info-level is fine).
  - Update any public docs or CONTRIBUTING notes to reflect that services are always on and flag was removed.

- Acceptance criteria:
  - Updated docs reflect where to add/modify behavior (by service), plus how to tune history truncation.

---

## Notes and Pointers

- Current state (verified):
  - Phase2Manager is ~534 LOC and orchestrates services; statement retrieval goes through `DiscussionService.get_participant_statement_with_retry`.
  - `MemoryService.update_vote_initiation_decision_memory` is in use from the manager; no direct `SimpleMemoryManager` calls remain in the manager.
  - `utils/selective_memory_manager.py` no longer uses `SimpleMemoryManager`; it now appends preformatted content for simple events.
  - Voting flow has not yet been wired to call `MemoryService.update_ballot_selection_memory` and `.update_amount_specification_memory` — recommended to add.
  - Speaking order uses `SpeakingOrderService` with early service initialization.

- Optional future cleanups:
  - If desired, migrate all “simple event” formatting (including ballot/amount) into MemoryService and reduce SelectiveMemoryManager to a thin router only.
