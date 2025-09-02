# Phase 2 Refactor Alignment Assessment

This assessment reviews how the current Phase 2 implementation aligns with `phase2_manager_refactoring_plan.md`, identifies legacy code remaining in `core/phase2_manager.py`, and highlights risks plus concrete next steps. Focus is on correctness, feature-flag behavior, code ownership boundaries, and testability.

## Executive Summary

- Core services exist and are substantially implemented: SpeakingOrder, Discussion, Voting, Memory, Counterfactuals.
- Phase2Manager is not yet a lean orchestrator (~200 LOC as planned). It remains ~1,013 LOC with several legacy concerns in place.
- Speaking order now routed through a service, but initialization was missing and caused a runtime error; this was fixed by initializing services at the start of `_run_group_discussion`.
- Voting and Memory are partially integrated via wrapper methods; however, some direct legacy calls remain (e.g., `SimpleMemoryManager.insert_vote_initiation_decision`).
- DiscussionService lacks the planned “get statement with retry/backoff” implementation; Phase2Manager still performs direct `Runner` calls for statements.
- Feature-flag (`refactored_services_enabled`) behavior is inconsistent: some fallbacks still delegate to services, effectively bypassing the flag’s intent.

Overall: The service extraction is well underway and functionally rich, but Phase2Manager still owns responsibilities that should be in services. Work remains to finish integration, enforce consistent flagging, and reduce orchestration code to the intended scope.

---

## Plan vs. Implementation

### 1) SpeakingOrderService
- Plan: Pure logic service with deterministic strategies and finisher restriction; used from Phase2Manager.
- Implementation:
  - File: `core/services/speaking_order_service.py` (present, ~8.4 kB; strategies: fixed/random/conversational with finisher restriction and seed support).
  - Usage: `core/phase2_manager.py` calls `self.speaking_order_service.generate_speaking_order(...)` in `_run_group_discussion` at lines ~608–617 (post-fix).
  - Init: `self._initialize_services()` now called at the start of `_run_group_discussion` to avoid `NoneType` error.
- Alignment: High. Service is implemented and actively used. Determinism and finisher restriction are covered.

### 2) DiscussionService
- Plan: Centralize discussion prompts, validation, and statement retrieval with retry/backoff (`get_participant_statement_with_retry`).
- Implementation:
  - File: `core/services/discussion_service.py` (present). Provides:
    - `build_discussion_prompt`, `build_internal_reasoning_prompt`, `validate_statement`, formatting helpers.
    - Does NOT implement `get_participant_statement_with_retry` (missing planned retry/backoff path).
  - In Phase2Manager:
    - `_build_discussion_prompt` and `_build_internal_reasoning_prompt` call DiscussionService when `refactored_services_enabled` is True; otherwise include legacy prompt building inline (lines ~984–1029).
    - Statement retrieval remains in `_get_participant_statement` (lines ~830–869), directly calling `Runner.run(...)` without retry/backoff or DiscussionService involvement.
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
    - Wrappers (`_update_memory_selective_with_service`, `_update_discussion_memory_with_service`, `_update_voting_phase_memories_with_service`, `_update_final_results_memory_with_service`) correctly delegate when enabled.
    - Discussion updates within main loop route through `_update_discussion_memory_with_service` (lines ~652–668).
    - However, Phase2Manager also directly uses `SimpleMemoryManager.insert_vote_initiation_decision` (line ~782), bypassing MemoryService for that event; similar direct calls may appear within `utils/selective_memory_manager.py`.
- Alignment: Partial to High. Service is robust and mostly integrated; remaining direct `SimpleMemoryManager` usage is a legacy artifact.

### 5) CounterfactualsService
- Plan: Apply principle and calculate payoffs, compute counterfactuals, build results, collect final rankings; keep original contracts.
- Implementation:
  - File: `core/services/counterfactuals_service.py` (present). Implements:
    - `apply_group_principle_and_calculate_payoffs`, `calculate_phase2_counterfactuals`, `collect_final_rankings`, plus detailed results building.
  - In Phase2Manager:
    - Wrappers `_apply_group_principle_and_calculate_payoffs_with_service` and `_collect_final_rankings_with_service` exist.
    - Fallbacks (`_apply_group_principle_and_calculate_payoffs` and `_collect_final_rankings`) exist and simply delegate to the service anyway (lines ~344–420), ensuring consistent behavior regardless of flag.
- Alignment: High. Contracts are preserved and the service is used both when enabled and via fallbacks.

---

## Phase2Manager: Legacy Code Inventory

The following responsibilities remain in `core/phase2_manager.py` and should ultimately be owned by services for a pure orchestrator design:

- Statement retrieval and prompt usage
  - `_get_participant_statement` (lines ~830–869): Direct `Runner.run(...)` without retry/backoff.
  - `_build_discussion_prompt` and `_build_internal_reasoning_prompt`: Contain legacy prompt-building logic when the flag is disabled (lines ~964–1029), though they already delegate to DiscussionService when enabled.

- Validation duplication
  - `_validate_statement` (lines ~374–417): Duplicates logic that also exists in DiscussionService; currently delegates when flag enabled, else uses inline validation.

- Voting-related memory updates
  - `_update_all_memories_for_voting_phase` and `_build_voting_phase_memory_content` (lines ~970–1029): Logic that overlaps with MemoryService’s `update_voting_phase_memory` and `update_all_memories_for_voting_phase`.
  - Direct `SimpleMemoryManager.insert_vote_initiation_decision` usage in the discussion loop (line ~782) bypasses MemoryService.

- Discussion history management
  - `_manage_discussion_history_length` (lines ~853+): History trimming should become MemoryService or DiscussionService concern.

- Context initialization and memory sanitization
  - `_validate_and_sanitize_memory` and `_initialize_phase2_contexts` (lines ~457–628): Reasonable to keep in orchestrator, but could be partially moved into MemoryService or a dedicated helper if desired.

- Orchestrator size
  - File length ~1,013 lines (`wc -l core/phase2_manager.py`), far above the ~200 lines target in the plan.

---

## Feature Flag Consistency Review

- Intended behavior: `phase2_settings.refactored_services_enabled` toggles use of services with safe fallbacks.
- Current behavior:
  - Voting and Memory wrappers honor the flag.
  - Speaking order is unconditionally routed to SpeakingOrderService (now safe after initialization fix). This is okay, as the service is pure logic and tested.
  - Counterfactuals fallbacks call the service anyway, ignoring the flag’s intent but keeping logic centralized and consistent. This reduces rollback semantics but simplifies maintenance.
- Recommendation: Choose one of these options and apply consistently:
  1) Always use services (preferred; remove flag and legacy code paths progressively), or
  2) Honor the flag strictly by providing functioning legacy fallbacks until fully removed.

---

## Risks and Recent Bug Root Cause

- Bug: `AttributeError: 'NoneType' object has no attribute 'generate_speaking_order'` when generating speaking order in `_run_group_discussion`.
- Cause: `speaking_order_service` initialization missing before use.
- Fix: Call `self._initialize_services()` at the start of `_run_group_discussion` so the service is available.
- Broader learning: When services are referenced in hot paths regardless of the feature flag, they must be initialized eagerly (constructor) or at the entry of the path.

---

## Test Coverage Observations

- Unit tests exist for services:
  - `tests/unit/test_speaking_order_service.py` present.
  - `tests/unit/test_counterfactuals_service.py` present.
- Gaps:
  - No test found for DiscussionService retry path (not implemented yet).
  - Integration path in Phase2Manager’s discussion loop still exercises legacy `_get_participant_statement`; needs tests once DiscussionService handles retrieval.

---

## Recommendations (Prioritized)

1) Implement DiscussionService statement retrieval with retry/backoff
- Add `get_participant_statement_with_retry(participant, context, discussion_state, agent_config, max_retries)`.
- Replace Phase2Manager `_get_participant_statement` usage with the new service method behind a wrapper (similar to voting/memory/counterfactuals).
- Add unit tests covering timeouts, retries, and minimal/invalid outputs.

2) Remove direct SimpleMemoryManager calls from Phase2Manager
- Replace `SimpleMemoryManager.insert_vote_initiation_decision` in the loop with `MemoryService.update_voting_phase_memory` or `update_all_memories_for_voting_phase` via the existing wrapper.
- Audit `utils/selective_memory_manager.py` for places delegating to `SimpleMemoryManager` for voting events; re-route those paths through MemoryService to centralize policy.

3) Consolidate prompt building and validation fully in DiscussionService
- Phase2Manager methods `_build_discussion_prompt` and `_build_internal_reasoning_prompt` should only delegate to the service; remove legacy branches.
- Keep `_validate_statement` as a thin wrapper to the service (or remove it and call the service directly).

4) Normalize feature flag semantics
- Decide whether to keep the flag. If keeping, make all wrappers respect it consistently and retain working legacy fallbacks temporarily.
- Preferably, drop the flag and fully adopt services, removing duplicate logic and slimming the orchestrator.

5) Reduce Phase2Manager size and responsibility
- After 1–4, remove legacy methods and helpers now owned by services.
- Target a ~200–300 LOC orchestrator that sequences services and manages cross-cutting concerns (locks, high-level logging, process_logger wiring).

6) Expand tests where services newly assume ownership
- Add unit tests for DiscussionService retries, MemoryService voting phase updates replacing SimpleMemoryManager, and end-to-end discussion+voting flow under both “consensus” and “no consensus” paths.

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

