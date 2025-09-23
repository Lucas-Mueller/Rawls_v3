# Current vs Ideal Test Suite Gaps

## Structural Mismatch
- The new `tests/component/` pilots exist, but most behaviour-heavy scenarios still live under `tests/integration`; although several Phase 2 suites were retired, the majority remain and continue to incur integration-time cost.
- Legacy `.bak` suites persist (`tests/unit/test_phase1_manager.py.bak:94`, `tests/unit/test_phase2_manager.py.bak:100`) and continue to model the old two-stage voting manager, preventing us from pruning dead code paths.
- Language responsibilities are fragmented: English scenarios dominate while Spanish and Mandarin parity is left to ad hoc fixtures, violating the multilingual fidelity principle.

## LLM Parity Violations
- Critical paths install monkeypatches to short-circuit the model layer (`tests/unit/test_phase2_voting_complete_flow.py:70`, `tests/integration/test_complete_experiment_flow.py:169`), so the suite never exercises the real prompts even though production always does.
- Dozens of bespoke mocks and `.bak` scaffolds keep synthetic JSON responses alive, creating drift between tests and the live language behaviour the ideal system insists on covering.
- The absence of shared helpers for authenticated agent creation means every test re-implements brittle workarounds instead of embracing the "call what production calls" rule.
- Multilingual prompts are rarely validated end-to-end; even where Spanish or Mandarin inputs appear, their responses are mocked, so we do not observe real language nuances or regressions.

## Execution Cost & Focus
- Archived performance suites still appear as deletions (`archive/tests_performance/*`), but equivalent coverage has not been re-imagined or replaced with slimmer smoke checks.
- Even nominal "unit" coverage still includes sleep-based timing assertions (`tests/unit/test_phase1_manager.py.bak:132`), which contradicts the fast-feedback goal.
- Coverage tooling explicitly omits application code by excluding the entire `tests/` tree from measurement without adding focused targets elsewhere (`pytest.ini:13`), so there is no signal on what the current suite actually exercises.

## Maintainability & Signal
- The archived directories and `.bak` files remain in the tree as deletions, but until they are purged from main the diff noise obscures the true surface area.
- Many tests obsess over narrow parsing edge cases while core orchestration (seed initialisation, process logger wiring, consensus validation) lacks targeted assertions, leaving the high-value behaviours from the ideal map uncovered.
- Language coverage is incidental: there is no documented rotation or baseline to guarantee each run exercises all supported locales, making failures surface late in production.

## Net Effect
- The suite is sprawling, slow, and tightly coupled to implementation details, the opposite of the focused layers, deterministic doubles, and opt-in live coverage defined in `docs/ideal_test_system.md`. Delivering the ideal system will require pruning legacy scaffolding, centralising reusable fakes, re-partitioning by responsibility, and adding crisp behavioural assertions for each experiment phase before reintroducing carefully gated live scenarios.
