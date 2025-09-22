# Phase B Implementation Plan — Service Contracts & Resilience

## Legend
- ☐ Not started
- ◐ In progress
- ☑ Completed

## Status Review (2025-09-22)
- ✅ Core service contract suites exist (`tests/services/*`) and agent-centric logging coverage landed.
- ⚠️ Resilience work is still partial: only voting service timeouts are covered; phase manager retries and broader failure fixtures remain outstanding.
- ⚠️ Trace metadata validation and partial integration flows have not been implemented.
- 📌 Follow-up documentation/decision items remain open. Phase B is therefore **not finished** and should be revisited to close the remaining tasks before Phase C completes.

## 1. Service Contract Tests
- ☑ Catalogue core services (`SpeakingOrderService`, `DiscussionService`, `VotingService`, `MemoryService`, `CounterfactualsService`) and identify public methods that require contract coverage.
- ☑ Design pytest fixtures providing realistic inputs (participant contexts, mock language manager, stubbed utility agent) for each service.
- ◐ Implement contract tests validating success paths:
  - ☑ Speaking order reproducibility with seeded randomness (`tests/services/test_speaking_order_service.py`).
  - ☑ Discussion prompt formatting across languages (`tests/services/test_discussion_service.py`).
  - ☑ Voting workflow hooks (initiation, confirmation, consensus tracking) (`tests/services/test_voting_service.py`).
  - ☑ Memory truncation/compression logic with edge-case payloads (`tests/services/test_memory_service_contracts.py`).
  - ☑ Counterfactual payoff calculations versus known baselines (`tests/services/test_counterfactuals_service.py`).
- ◐ Capture service logs/metrics in assertions to ensure observability (partial logging assertions added; expand for counterfactuals).

## 2. Error & Resilience Scenarios
- ◐ Enumerate critical failure modes (utility agent timeouts, language manager lookup failures, memory limit overflows, counterfactual exceptions) — initial timeouts and translation failures covered in `tests/resilience/test_voting_service_resilience.py`.
- ◐ Build reusable fixtures that simulate these failures using `pytest.raises` and stubbed runner scripts (timeout fixture implemented for voting service; expand to other managers).
- ☐ Write tests asserting graceful degradation/retry behaviour within `Phase1Manager`, `Phase2Manager`, and service layers.
- ☑ Ensure `ExperimentErrorHandler` categorises severity correctly and increments metrics (`tests/resilience/test_error_handler.py`).

## 3. Trace & Logging Validation
- ☑ Add tests confirming `AgentCentricLogger` captures expected events (initial rankings) (`tests/logging/test_agent_centric_logger.py`).
- ☐ Validate experiment-level trace metadata (experiment id, participant list, language) through stubbed trace provider hooks.
- ☐ Verify logging with concurrent experiments to ensure isolation (no cross-experiment leakage).

## 4. Integration Scenarios (Targeted)
- ☐ Construct targeted integration tests running partial flows (e.g., Phase 2 discussion with real services) using stubbed agent transcripts.
- ☐ Assert final `ExperimentResults` structure and intermediate service outputs (discussion history, vote counts, counterfactual summaries).
- ☐ Include multilingual variants to ensure localisation resilience.

- ☑ Extend transcript library with error-focused scripts (timeouts, malformed JSON, contradictory statements) — initial set added under `tests/data/acceptance/`.
- ☑ Introduce helper assertions for prompt/schema validation (JSON Schema or dataclass comparisons) to replace golden strings (`tests/utils/prompt_assertions.py` with adoption in `tests/golden/test_phase2_prompts.py`).
- ☑ Update docs (`docs/testing.md`, onboarding) with guidance on writing contract/resilience tests and using new helpers.
- ☑ Enhance CI to run new contract/resilience suites (e.g., `pytest -m contracts`, `pytest -m resilience`) as separate jobs.

## 6. Follow-up & Phase C Preparation
- ☐ Document remaining gaps once contract/resilience coverage lands (e.g., performance monitoring, regression baselines).
- ☐ Evaluate need for load/performance harness refactor in Phase C.
- ☐ Capture lessons learned in `docs/DECISIONS.md` for future contributors.
