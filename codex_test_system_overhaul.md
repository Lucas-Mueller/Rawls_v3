# Test System Overhaul Report

## 1. System Reality vs. Current Test Focus
The repository implements a multi-phase LLM-driven experiment pipeline:
- `core/experiment_manager.py` orchestrates async initialization, dynamic temperature detection, seeding, tracing, and sequential phase execution (`async_init`, `run_complete_experiment`).
- `core/phase1_manager.py` conducts parallel agent familiarization, intensive memory updates, and distribution sampling.
- `core/phase2_manager.py` coordinates service-based group discussion, voting, memory, and counterfactual payout logic.
- Supporting services (`core/services/*`) encapsulate speaking order, discussion prompts, voting orchestration, memory compression, and counterfactual calculations.
- Utility/participant agents interact with the OpenAI Agents SDK, apply temperature caching, and parse multilingual outputs.

The tests largely predate this architecture and concentrate on independent parsing helpers, handcrafted fixtures, or golden snapshots. Few suites exercise the orchestration surface, temperature/seeding layers, or the explicit service integrations now responsible for system behavior.

## 2. Evidence of Misalignment
| Component | Expected Behaviors | What Tests Do Today |
| --- | --- | --- |
| Experiment orchestration (`core/experiment_manager.py`) | Async initialization, temperature cache wiring, tracing metadata, sequential phase coordination | `tests/integration/test_complete_experiment_flow.py` builds a mocked manager, bypassing `async_init`, patches out all agent calls, and validates only mocked artifacts, never the real orchestration path. |
| Phase 1 lifecycle (`core/phase1_manager.py`) | Parallel tasks, distribution sampling (dynamic vs. original values), memory updates, logging | Unit tests rely on `.bak` snapshots or heavy mocks, skipping concurrency, seeding, or memory side-effects; distribution generation is forced via deterministic patches. |
| Phase 2 services (`core/services/*.py`) | Speaking order, discussion prompts, consensus locking, counterfactual payouts, memory truncation & compression | Tests patch each service in isolation, assert direct string equality, or validate method dispatch via mocks. Pivotal flows (lock contention, sequential voting, memory compression thresholds) lack coverage. |
| Utility agent parsing (`experiment_agents/utility_agent.py`) | Async LLM calls with retries, JSON extraction, multilingual normalization, temperature caching | Several tests call async methods synchronously (`tests/unit/test_parsing_engine.py`), returning coroutine objects. Others monkey-patch `run_without_tracing` to return perfect JSON, hiding retry/backoff/error paths. |
| Logging & tracing (`utils/logging`, `agents.trace`) | Agent-centric logging, trace metadata propagation, error routing | Tests rarely touch logging; when they do, they assert presence of strings rather than verifying aggregator state or trace IDs. |
| Configuration & seeding (`config/*`, `utils/seed_manager.py`) | Pydantic validation, reproducibility, dynamic configs | Only deterministic seed re-computation is tested; configuration permutations, phase settings, and validation errors are missing. |

## 3. Challenging the Existing Test Logic
- **Artificial success paths**: End-to-end tests (e.g., `tests/integration/test_complete_experiment_flow.py`) replace the entire OpenAI interaction (`agents.Runner.run`) with deterministic strings and patch utility agents to return canned objects. The resulting assertions verify that mocks were stitched together, not that the real services integrate correctly.
- **Synchronous misuse of async API**: `tests/unit/test_parsing_engine.py` invokes async parsing helpers without awaiting them, so the “result” is a coroutine. Either these tests never run or they silently fail the moment real async code executes. This indicates drift between how tests are written and how agents behave today.
- **Legacy inheritance hierarchy**: Many tests still extend `unittest.TestCase` or custom async base classes while calling pytest features. This hybrid style prevents the effective use of pytest fixtures and leads to per-test event loop juggling (`asyncio.run`) even though pytest-asyncio is already configured.
- **Overfitted string-based golden tests**: Golden prompt suites assert on exact strings assembled by mocked language managers. They offer little protection when switching to real translation files, memory guidance styles, or updated prompt templates, and they block legitimate prompt improvements.
- **Untested resilience paths**: Retry loops, exponential backoff, and selective compression logic in memory services and utility agent parsing are untested. Error handlers intended to downgrade issues (e.g., memory compression) are rarely evidenced in test expectations, so regressions likely go unnoticed.
- **Division between fixtures and production data**: Massive fixtures precompute agent utterances (`tests/integration/fixtures/experiment_fixtures.py`) to drive scripted scenarios. These disregard new capabilities such as dynamic temperature detection, seeded randomness, or updated logging requirements, leaving real participants under-tested.

## 4. Core Coverage Gaps by Scenario
1. **Initialization & Dependency Wiring**: No test verifies that `FrohlichExperimentManager.async_init` wires temperature caches, seed manager, participants, and utility agent end-to-end. Failures here would only surface at runtime.
2. **Parallel Phase 1 Execution**: Lack of tests around concurrent participant loops hides issues like shared seed usage, memory guidance propagation, or logging capture when exceptions occur mid-gather.
3. **Phase 2 Lifecycles**: The bespoke services have little collaborative coverage: speaking order vs. voting readiness vs. counterfactual payouts vs. memory updates. Consensus locks, voting retry limits, and memory truncation thresholds are unverified.
4. **Dynamic Model Capability Detection**: `utils/dynamic_model_capabilities` introduces caching, retries, and concurrency. No tests confirm behavior with supported/unsupported models or cache invalidation.
5. **Error Routing & Recovery**: The experiment pipeline wraps operations in `handle_experiment_errors`; tests rarely assert on severity categorization, fallback flows, or metrics recorded by `AgentCentricLogger`.
6. **Configuration Matrix**: Default vs. custom YAML, language selection, phase settings, and memory guidance styles remain untested, risking runtime schema mismatches.

## 5. Target Testing Principles
- **Scenario-driven acceptance**: Execute the full experiment with a deterministic stubbed LLM backend. Validate outputs on `ExperimentResults` (phase summaries, consensus status, payouts) rather than mock call sequences.
- **Service contract tests**: Replace string golden tests with structural assertions (e.g., prompt includes participant names, round metadata, localized strings). Test each service with real language managers and minimal mocks.
- **Async-native unit tests**: Adopt pytest fixtures and `pytest.mark.asyncio` everywhere. Remove manual event loops and ensure all async methods are awaited, enabling genuine coverage of retry/backoff flows.
- **Stateful memory checks**: Build tests that start with known participant memory, invoke memory service updates, and assert on truncation/compression outcomes plus context mutation.
- **Resilience verification**: Introduce tests that force parsing failures, timeout scenarios, and memory overflows to validate error-handling pathways.
- **Configurability validation**: Parameterize tests across languages, memory guidance styles, and distribution modes to ensure the system honors configuration-driven behavior.

## 6. Proposed Overhaul Roadmap

### Phase A — Foundations (1-2 sprints)
1. Standardize on pytest; drop unittest inheritance and the custom runner. Add `tests/conftest.py` with fixtures for stubbing LLM interactions, tracing disablement, and seeded randomness.
2. Introduce a deterministic `StubRunner` fixture for `agents.Runner.run` that can replay scripted conversations while preserving prompt history for assertions.
3. Replace golden tests with structure-aware assertions (e.g., schema validation) and remove `.bak` files.
4. Create focused acceptance tests that call `FrohlichExperimentManager.run_complete_experiment` using stubbed agents, asserting on real `ExperimentResults` fields.

### Phase B — Service Contracts & Resilience (2-3 sprints)
1. Write contract tests for each service (`MemoryService`, `VotingService`, `DiscussionService`, `CounterfactualsService`) with real settings and language managers.
2. Cover error-handling flows by simulating parsing failures, memory limit breaches, and consensus lock contention.
3. Add tests for temperature cache behavior, ensuring supported/unsupported models are cached, retried, and surfaced correctly.
4. Validate configuration parsing across languages, memory guidance styles, and original-values mode.

### Phase C — Observability & Regression Defenses (ongoing)
1. Assert on `AgentCentricLogger` and process logger outputs to ensure traceability.
2. Capture metrics snapshots (e.g., voting rounds, consensus outcomes) as structured data rather than string logs.
3. Re-introduce lightweight regression suites that compare scenario outputs via JSON fixtures, focusing on high-signal invariants (consensus count, payout distribution) instead of prompts.
4. Establish CI jobs for acceptance (stubbed LLM), unit/service contracts, and optional long-running performance checks gated by markers.

## 7. Immediate Action Checklist
- [ ] Create pytest fixtures for stubbed `Runner.run`, seeded randomness, and tracing disablement; remove manual event loop management.
- [ ] Write the first acceptance test that executes `FrohlichExperimentManager.run_complete_experiment` end-to-end with two stubbed agents and asserts on consensus plus payout summary.
- [ ] Audit async tests to ensure all utility agent methods are awaited; fix or skip suites that currently consume coroutine objects.
- [ ] Delete or quarantine `.bak` files, legacy templates, and golden strings; replace with schema-based assertions.
- [ ] Document the new testing strategy and contributor guidelines in `docs/` and the README.

## 8. Risks & Mitigations
- **High refactor surface**: Modernizing tests while features evolve risks merge conflicts. Mitigate by working incrementally and landing foundational fixtures before rewriting suites.
- **Stub fidelity**: Deterministic stubs must mimic enough of the LLM behavior to be meaningful. Maintain a central stub module and feed it structured scripts to avoid drift.
- **Performance suites**: Heavy performance tests should become optional (`pytest -m slow`) to keep CI lean while still offering profiling capabilities when needed.

## 9. Suggested Structure for New Suites
- `tests/acceptance/`: Full experiment runs with stubs and scenario assertions.
- `tests/services/`: Contract tests per service with minimal mocking.
- `tests/agents/`: Utility and participant agent behavior, including retries and temperature detection.
- `tests/config/`: YAML validation, configuration defaults, and overrides.
- `tests/integration/`: Cross-service flows requiring multiple components without full experiment execution.

By replacing brittle, heavily mocked tests with scenario-driven and contract-based coverage, the suite can validate the actual experiment mechanics, reveal regressions early, and simplify contributor onboarding.
