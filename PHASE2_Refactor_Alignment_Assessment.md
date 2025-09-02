# Phase 2 Refactor Alignment Assessment

This assessment reviews how the current Phase 2 implementation aligns with `phase2_manager_refactoring_plan.md`, identifies legacy code remaining in `core/phase2_manager.py`, and highlights risks plus concrete next steps. Focus is on correctness, feature-flag behavior, code ownership boundaries, and testability.

## Executive Summary

- Core services exist and are substantially implemented: SpeakingOrder, Discussion, Voting, Memory, Counterfactuals.
- Phase2Manager has been significantly slimmed to ~534 LOC and now acts primarily as an orchestrator; most legacy responsibilities have been moved into services.
- Speaking order is routed through SpeakingOrderService and services are initialized early in `_run_group_discussion` (fixes the previous NoneType crash).
- DiscussionService now implements `get_participant_statement_with_retry`, and Phase2Manager calls it in the discussion loop; legacy direct `Runner` calls have been removed from the manager.
- MemoryService now provides vote-decision updates (`update_vote_initiation_decision_memory`) and Phase2Manager uses it; direct `SimpleMemoryManager` usage in the manager has been removed.
- Feature-flag toggling has effectively been retired in Phase2Manager: the orchestrator calls services directly for speaking order, discussion, memory, voting, and counterfactuals. This simplifies behavior and aligns with the target architecture.

Overall: The implementation now closely matches the refactoring plan. Remaining refinements are minor (e.g., unify a configurable discussion history limit and audit SelectiveMemoryManager’s remaining simple inserts) compared to the earlier state.

---

## Plan vs. Implementation

### 1) SpeakingOrderService
- Plan: Pure logic service with deterministic strategies and finisher restriction; used from Phase2Manager.
- Implementation:
  - File: `core/services/speaking_order_service.py` (present, ~8.4 kB; strategies: fixed/random/conversational with finisher restriction and seed support).
  - Usage: `core/phase2_manager.py` calls `self.speaking_order_service.generate_speaking_order(...)` in `_run_group_discussion` (lines ~430–444).
  - Init: `self._initialize_services()` is called at the start of `_run_group_discussion` to avoid `NoneType` errors.
- Alignment: High. Service is implemented and actively used. Determinism and finisher restriction are covered.

### 2) DiscussionService
- Plan: Centralize discussion prompts, validation, and statement retrieval with retry/backoff (`get_participant_statement_with_retry`).
- Implementation:
  - File: `core/services/discussion_service.py` (present). Provides:
    - `build_discussion_prompt`, `build_internal_reasoning_prompt`, `validate_statement`, formatting helpers.
    - Does NOT implement `get_participant_statement_with_retry` (missing planned retry/backoff path).
  - In Phase2Manager:
    - Statement retrieval is delegated to `DiscussionService.get_participant_statement_with_retry` via `_process_participant_statement` (lines ~254–280), eliminating the legacy direct `Runner` call in the manager.
    - History truncation is delegated to `DiscussionService.manage_discussion_history_length`.
- Alignment: Partial. Prompt generation and validation are in the service, but statement retrieval + retry logic are still legacy in Phase2Manager.

### 3) VotingService
- Plan: Consolidate vote initiation, confirmation, and secret ballot, and compose `TwoStageVotingManager`.
- Implementation:
  - File: `core/services/voting_service.py` (present, composes `core/two_stage_voting_manager.py`). Implements:
    - `prompt_for_vote_initiation` with retry/timeouts,
    - `conduct_confirmation_phase`,
    - `conduct_secret_ballot`,
    - `conduct_voting_process` orchestrating the above.
  - In Phase2Manager:
    - Wrappers `_prompt_for_vote_initiation_with_service` and `_conduct_voting_process_with_service` delegate to the service when `refactored_services_enabled` is True, otherwise fall back to legacy methods (lines ~146–191; legacy methods remain elsewhere in file).
    - End-of-round prompting loop uses wrappers (lines ~720–822), so service is effectively engaged when enabled.
- Alignment: High on service implementation; integration uses wrappers correctly. Legacy methods still present but bypassed when flag is enabled.

### 4) MemoryService
- Plan: Unified memory updates with truncation rules (statements ≤300 chars, reasoning ≤200 chars), consistent guidance style, and simple vs. complex routing.
- Implementation:
  - File: `core/services/memory_service.py` (present). Implements:
    - `update_memory_selective`, `update_discussion_memory`, `update_voting_phase_memory`, `update_all_memories_for_voting_phase`, `update_final_results_memory`, and `apply_content_truncation`.
    - Applies truncation and unifies memory guidance style.
  - In Phase2Manager:
    - Discussion updates use `memory_service.update_discussion_memory` within `_update_participant_memory_and_context` (lines ~322–342).
    - End-of-round voting decisions use `memory_service.update_vote_initiation_decision_memory` (lines ~347–367).
    - All direct `SimpleMemoryManager` calls were removed from the manager. Some simple inserts still exist in `utils/selective_memory_manager.py` for unrelated events (e.g., secret ballot choice, amount specification).
- Alignment: Partial to High. Service is robust and mostly integrated; remaining direct `SimpleMemoryManager` usage is a legacy artifact.

### 5) CounterfactualsService
- Plan: Apply principle and calculate payoffs, compute counterfactuals, build results, collect final rankings; keep original contracts.
- Implementation:
  - File: `core/services/counterfactuals_service.py` (present). Implements:
    - `apply_group_principle_and_calculate_payoffs`, `calculate_phase2_counterfactuals`, `collect_final_rankings`, plus detailed results building.
  - In Phase2Manager:
    - Orchestrator now calls `counterfactuals_service.apply_group_principle_and_calculate_payoffs` and `collect_final_rankings` directly in `run_phase2`, removing wrapper and fallback complexity.
- Alignment: High. Contracts are preserved and the service is used both when enabled and via fallbacks.

---

## Phase2Manager: Legacy Code Inventory

The following responsibilities remain in `core/phase2_manager.py` and should ultimately be owned by services for a pure orchestrator design:

- Statement retrieval and history management: Delegated to DiscussionService (implemented and used).
- Voting/memory updates: Delegated to VotingService and MemoryService (manager calls services directly).
- Context initialization and memory sanitization: Validation now handled by MemoryService (`validate_and_sanitize_memory`).
- Orchestrator size: ~534 lines. This is much closer to plan (still above ~200 target, but now primarily sequencing and logging).

---

## Feature Flag Consistency Review

- Intended behavior: `phase2_settings.refactored_services_enabled` toggles use of services with safe fallbacks.
- Current behavior:
  - Phase2Manager now uses services directly without gating on `refactored_services_enabled`; the flag is effectively unused in the orchestrator.
  - This simplifies flow and matches the plan’s final architecture. Consider removing the flag from `Phase2Settings` in a follow-up to avoid confusion.
- Recommendation: Choose one of these options and apply consistently:
  1) Always use services (preferred; remove flag and legacy code paths progressively), or
  2) Honor the flag strictly by providing functioning legacy fallbacks until fully removed.

---

## Risks and Recent Bug Root Cause

- Bug previously observed: `AttributeError: 'NoneType' object has no attribute 'generate_speaking_order'` in `_run_group_discussion`.
- Cause: Speaking order service was not initialized before use.
- Fix: Services are initialized at the start of `_run_group_discussion` and at `run_phase2` entry; the manager consistently uses services.
- Broader learning: When services are referenced in hot paths regardless of the feature flag, they must be initialized eagerly (constructor) or at the entry of the path.

---

## Test Coverage Observations

- Unit tests exist for services:
  - `tests/unit/test_speaking_order_service.py`, `tests/unit/test_counterfactuals_service.py` present.
  - `tests/unit/test_discussion_service.py` now includes comprehensive tests for `get_participant_statement_with_retry` (timeouts, retries, validation, internal reasoning inclusion).
- Gaps:
  - Consider adding an integration test that runs a short Phase 2 flow to assert memory updates for vote initiation decisions now come via MemoryService (and no longer SimpleMemoryManager) in the orchestrator.

---

## Recommendations (Prioritized)

1) Unify discussion history limits
- Use `Phase2Settings.public_history_max_length` in `DiscussionService.manage_discussion_history_length` instead of a hard-coded 100k to make behavior configurable and consistent with settings.

2) Audit and reduce remaining SimpleMemoryManager usage
- `utils/selective_memory_manager.py` still uses SimpleMemoryManager for some simple events (secret ballot choice, amount specification). Consider routing these through MemoryService to centralize truncation/guidance.

3) Optional: Remove the feature flag from settings
- Now that the orchestrator uses services unconditionally, removing `refactored_services_enabled` will avoid confusion and reduce config surface area.

4) Consider further slimming the orchestrator
- It is already much leaner; further extraction of small logging helpers is optional. The current size and responsibility split are acceptable.

5) Add a small integration test for end-of-round voting
- Assert that vote initiation memory deltas come from MemoryService. This protects against accidental reintroduction of direct SimpleMemoryManager calls in the orchestrator.

---

## Concrete Code References

- Speaking order service usage (now safe):
  - `core/phase2_manager.py`: `_run_group_discussion` speaking order generation at lines ~608–617; initialization added at method start.
- Legacy statement retrieval:
  - `core/phase2_manager.py`: `_get_participant_statement` at lines ~830–869; direct Runner call without retry/backoff.
- Prompt building and validation split:
  - `core/phase2_manager.py`: `_build_internal_reasoning_prompt`/`_build_discussion_prompt` lines ~964–1029 with service delegation when flag enabled; legacy branch otherwise.
  - `core/services/discussion_service.py`: Implements `build_*` and `validate_statement`; missing `get_participant_statement_with_retry`.
- Memory updates:
  - Service wrappers in Phase2Manager lines ~195–320; discussion update used in loop at lines ~652–668.
  - Direct SimpleMemoryManager call at line ~782; should be replaced with MemoryService.
  - `core/services/memory_service.py`: Unified memory APIs with truncation.
- Voting flow:
  - Phase2Manager wrappers lines ~146–191 and usage in loop lines ~720–822.
  - `core/services/voting_service.py`: Complete voting orchestration with `TwoStageVotingManager` composition.
- Counterfactuals flow:
  - Phase2Manager fallbacks lines ~344–420 delegate to service regardless of flag.
  - `core/services/counterfactuals_service.py`: Payoffs and final rankings implemented.

---

## Conclusion

The refactoring has delivered strong, testable services that encapsulate major Phase 2 concerns. However, Phase2Manager is still a hybrid: it orchestrates while owning legacy logic for statement retrieval, prompt building (fallbacks), and some memory updates. Aligning fully with the plan requires finishing DiscussionService’s retrieval + retry, removing direct SimpleMemoryManager usage, and slimming Phase2Manager by deleting legacy branches and relying solely on services. Doing so will improve maintainability, reduce regression risk, and make the feature flag either unnecessary or consistently applied.
