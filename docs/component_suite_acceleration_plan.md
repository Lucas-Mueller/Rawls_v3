# Component Suite Acceleration Plan

This note captures why the component layer currently feels slow, what each
“heavy” test is validating, and how we might carve out faster alternatives that
avoid full experiment runs.

## Current Runtime and Behaviour

- **Walls-clock cost:** On a clean English-only run the component suite still
  consumes ~12–14 real minutes and ~150 OpenAI requests (rough estimate based on
  four full experiment loops with 3 participants). With multilingual rotation
  enabled the cost triples.
- **End-to-end executions:** Four files perform the full Phase 1 → Phase 2 loop,
  making them the main contributors to runtime:

| Test file | Behaviour exercised | Notes |
| --- | --- | --- |
| `tests/component/test_phase2_manager_live.py` | Full Phase1→Phase2 with three participants; asserts payoff/discussion structure | Core smoke validation |
| `tests/component/test_consensus_mechanisms.py` | Consensus/non-consensus branching | Focused on discussion metadata |
| `tests/component/test_phase2_mixed_languages_live.py` | Mixed-locale Phase 2 coverage | Ensures language heterogeneity works |
| `tests/component/test_counterfactuals_service_live.py` | Phase 2 run to collect counterfactuals | Ensures alternative payouts persist |

- **Other live calls:** Parsing, translation, memory, and voting suites hit the
  API but do not execute the full experiment; they are faster but still add
  latency.

## What Each Full Loop Is Testing

- **`test_phase2_manager_live.py`** – Smoke validation that the Phase 2 manager
  produces payoffs, discussion history, and consensus metadata when seeded with
  Phase 1 results.
- **`test_consensus_mechanisms.py`** – Ensures the manager surfaces final rounds
  and consensus flags; essentially an end-to-end behaviour check for the
  consensus branch.
- **`test_phase2_mixed_languages_live.py`** – Confirms multilingual participants
  (Spanish/English/Mandarin assignments) still play nicely in Phase 2.
- **`test_counterfactuals_service_live.py`** – Verifies counterfactual payout
  structures are present after a Phase 2 run.

All of these are behavioural checks we care about, but they only need a subset
of the work currently performed.

## Fast-Test Alternatives (No Full Experiment Runs)

## Proposed Refactor Roadmap

| Step | Objective | Approach | Owner / ETA |
| --- | --- | --- | --- |
| 1 | Capture call metrics | Instrument component run to log per-test request count & runtime; store in `reports/` | TBD, 1d |
| 2 | Extract deterministic Phase2 inputs | Snapshot Phase1 results from a known-good run; expose a factory in `tests/support` | TBD, 2d |
| 3 | Replace `test_phase2_manager_live.py` with synthetic Phase2 inputs | Use snapshot from step 2 to call `run_phase2` once; assert structural fields without live Phase1 | Depends on #2, 2d |
| 4 | Split consensus + counterfactual assertions into contract tests | Convert existing assertions into contract fixtures; drop full loop repetition | Depends on #2, 2d |
| 5 | Re-scope multilingual coverage | Keep English-only component runs; schedule a nightly matrix job that runs `pytest --run-live --languages=all` | Coordinate with CI owner, 1d |
| 6 | Add “slow profile” smoke | Extend `tests/integration/test_cli_live.py` to run once per release with full language rotation | After #5, 1d |

## Coverage Mapping

| Current Coverage | Proposed Replacement | Status |
| --- | --- | --- |
| Phase2 manager smoke (`test_phase2_manager_live.py`) | Snapshot-driven manager probe + nightly CLI smoke | Pending |
| Consensus branch (`test_consensus_mechanisms.py`) | Contract asserting discussion metadata | Pending |
| Mixed-language flow (`test_phase2_mixed_languages_live.py`) | Nightly CLI/narrowed harness test | Pending |
| Counterfactual payout structure | Contract snapshot (Phase2 results fixture) | Pending |

## Risks & Mitigations

- **Drift between live and snapshot fixtures** – Mitigate by refreshing
  snapshots whenever prompts/models change; add a weekly live sanity run.
- **Loss of multilingual signal** – Keep a scheduled CI job (nightly or weekly)
  that sets `LIVE_LANGUAGES=1` and runs the CLI smoke.
- **Incomplete parity coverage** – Ensure new contract tests assert the same
  fields we currently check (payoffs, consensus flags, discussion history). Use
  code review to confirm the mapping table is kept in sync.
- **Cost surprises** – Step 1’s metric logging should produce a baseline so we
  can compare “before/after” when refactors land.

## Next Actions

1. Collect baseline metrics for component runtimes and request counts.
2. Draft the Phase2 snapshot factory and validate it reproduces current outputs
   when fed into `run_phase2`.
3. Prototype one refactored test (e.g., replace
   `test_phase2_manager_live.py`) and measure the speedup.
4. Iterate through the mapping table, removing legacy full loops only after
   replacement coverage is in place.
5. Update contributor docs (`docs/contributing/testing.rst`) once the suite
   layout stabilises.
