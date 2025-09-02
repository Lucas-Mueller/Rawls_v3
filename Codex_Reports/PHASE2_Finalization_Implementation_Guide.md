# Phase 2 Finalization — Implementation Guide

Purpose: Convert the refactor into a clean, fully consolidated Phase 2 flow that always goes through services, with configurable behavior, consistent memory updates, and guardrail tests.

## TL;DR (Engineer Checklist)

- Make discussion history limit configurable via `Phase2Settings.public_history_max_length` (not hard-coded).
- Route remaining “simple” memory writes (ballot selection, amount specification) through `MemoryService` instead of `SimpleMemoryManager`.
- Add a focused integration test that asserts vote-initiation decisions are written by `MemoryService`.
- Retire the now-unused `refactored_services_enabled` flag from settings and any stale wrappers (if any remain elsewhere).
- Update docs to reflect the services-only architecture and the configurable history limit.

---

## 1) Configurable Discussion History Limit

Goal: Use config to control how much public discussion history is kept before truncation.

- Files:
  - `core/services/discussion_service.py`
  - `config/phase2_settings.py`

- Steps:
  - In `DiscussionService.__init__`, set `self.max_history_length = self.settings.public_history_max_length` instead of a hard-coded constant.
  - Ensure `manage_discussion_history_length()` uses `self.max_history_length` (it already does; just make it read from settings).

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

Goal: Eliminate direct `SimpleMemoryManager` calls for ballot selection and amount specification; use `MemoryService` for consistent truncation and guidance styles.

- Files:
  - `core/services/memory_service.py`
  - `core/services/voting_service.py` (or `core/two_stage_voting_manager.py`, depending on where events are finalized)
  - `utils/selective_memory_manager.py` (to remove residual `SimpleMemoryManager` calls for these events)

- Steps:
  1) Add dedicated MemoryService methods:
     - `async def update_ballot_selection_memory(agent, context, principle_name: str, **kwargs) -> str`
     - `async def update_amount_specification_memory(agent, context, amount: str|int, **kwargs) -> str`
     - Internally call `update_memory_selective(...)` with appropriate `MemoryEventType` and metadata. Reuse localization keys used by SimpleMemoryManager today to preserve wording.
  2) Invoke these methods from the voting flow:
     - In `VotingService` (after ballot capture) and amount specification steps (if applicable), call the new MemoryService methods with explicit values rather than relying on SelectiveMemoryManager pattern matching.
  3) Remove direct SimpleMemoryManager usage for these events:
     - In `utils/selective_memory_manager.py::_simple_memory_update`, replace branches for `BALLOT_SELECTION` and `AMOUNT_SPECIFICATION` with simple appends of preformatted content (or, better, stop calling `_simple_memory_update` for these events by moving their writes to `VotingService`).
     - If removal is staged, gate the legacy path behind an internal constant and set it to off by default.

- Acceptance criteria:
  - No direct `SimpleMemoryManager.insert_secret_ballot_choice` or `.insert_amount_specification` calls in the codebase (outside MemoryService internals, if any).
  - Ballot/amount memory lines match current phrasing but now flow through MemoryService (benefits from truncation/guidance).

---

## 3) Guardrail Integration Test (MemoryService Write Path)

Goal: Ensure vote-initiation decisions are written via `MemoryService`, guarding against regressions.

- Files:
  - `tests/integration/` (new test file, e.g., `test_phase2_memory_write_paths.py`)

- Steps:
  - Arrange: Create a minimal Phase 2 config with 2 participants, 1–2 rounds, and deterministic behavior (seeded).
  - Patch `MemoryService.update_vote_initiation_decision_memory` with `AsyncMock` to track calls.
  - Run `Phase2Manager.run_phase2(...)` until end-of-round vote prompting triggers.
  - Assert: The `MemoryService` method was called for each participant; verify the written decision aligns with the prompt response.

- Acceptance criteria:
  - Test passes locally and fails if the manager reintroduces a direct `SimpleMemoryManager` call.

---

## 4) Retire `refactored_services_enabled` Flag

Goal: Simplify configuration surface; services are now always used.

- Files:
  - `config/phase2_settings.py`
  - Any stale wrappers or conditionals in code paths outside `Phase2Manager` (most were already removed).

- Steps:
  - Deprecate: Keep the field for one release cycle but note it is unused in docstrings and comments; or remove it entirely if downstream configs are under our control.
  - Remove leftover wrapper methods or dead branches that read this flag.

- Acceptance criteria:
  - No behavior changes; fewer conditional branches; no references to the flag in orchestrator code.

---

## 5) Documentation and Logging Consistency

Goal: Reflect the services-first architecture and keep logs consistent.

- Files:
  - `README.md` or project docs location
  - `PHASE2_Refactor_Alignment_Assessment.md` (already updated; keep in sync)

- Steps:
  - Document: Ownership boundaries (DiscussionService, VotingService, MemoryService, SpeakingOrderService, CounterfactualsService) and the configurable history limit.
  - Verify `process_logger` still receives round start/complete and voting results; leave breadcrumbs for debugging (info-level is fine).

- Acceptance criteria:
  - Updated docs reflect where to add/modify behavior (by service), plus how to tune history truncation.

---

## Notes and Pointers

- Current state (verified):
  - Phase2Manager is ~534 LOC and orchestrates services; statement retrieval goes through `DiscussionService.get_participant_statement_with_retry`.
  - `MemoryService.update_vote_initiation_decision_memory` is in use from the manager; no direct SimpleMemoryManager calls remain in the manager.
  - `utils/selective_memory_manager.py` still contains direct calls to `SimpleMemoryManager` for ballot and amount — this is the main target for centralization.
  - Speaking order uses `SpeakingOrderService` with early service initialization.

- Optional future cleanups:
  - If desired, migrate all “simple event” formatting (including ballot/amount) into MemoryService and reduce SelectiveMemoryManager to a thin router only.

