# Hypothesis Evaluation Descriptive Stats Plan

## Objectives
- Provide reusable helpers to surface negotiation dynamics, voting behavior, and preference movement across hypothesis runs (1–6).
- Enable notebooks (e.g., `hypothesis_testing/hypothesis_1/Hypothesis_1_main.ipynb`) to import a single utility layer instead of re-deriving metrics.
- Standardize outputs so generated tables/plots can be compared across experiments and exported to `reports/`.

## Data Inventory
- **Result schema** (e.g., `experiment_results_*.json`):
  - `general_information`: run-level metadata (consensus, total rounds, configs).
  - `agents`: per-participant breakdown with `phase_1` rankings, `phase_2.rounds` (messages, vote intent, favored principle), and `post_group_discussion` outcomes.
  - `voting_history`: system-wide log with initiation requests per round, vote attempts, confirmations, and aggregated statistics.
- Expect identical schema for hypotheses 1–6; utilities must accept either single file paths or directories.

## Key Questions & Metrics
- **Negotiation cadence**: total rounds, per-round speaker order, message counts, average/median tokens per message, time-to-consensus (round index of `vote_rounds` success), bank balance evolution.
- **Voting behavior**: number of initiation requests by participant/round, success rate, failed parsing counts, confirmation attempts, and rounds elapsed before consensus.
- **Preference trajectory**: rank shifts from `phase_1.initial_ranking` → subsequent rankings → `phase_2.post_group_discussion.final_ranking`, certainty deltas, favored principle per round, vote alignment vs. final consensus.
- **Optional enrichments**: floor constraint evolution (if encoded in text or structured fields), agent agreement metrics (Kendall tau / Spearman footrule between rankings), sentiment proxies from `public_message` length.

## Proposed Utility Surface
| Function | Purpose | Notes |
| --- | --- | --- |
| `load_experiment(path: Path) -> ExperimentRecord` | Validate & normalize JSON into typed dataclasses | Handles schema differences and missing fields |
| `summarize_negotiation(record) -> NegotiationStats` | Aggregate rounds, speaker turns, message features | Combines `general_information` and `agents[].phase_2.rounds` |
| `summarize_voting(record) -> VotingStats` | Count initiations, attempts, confirmations, consensus timing | Uses `voting_history` |
| `summarize_preferences(record) -> List[PreferenceTrajectory]` | Track ranking shifts, certainty change, favored principle timeline | Normalizes rankings and computes distance metrics |
| `aggregate_runs(paths: Iterable[Path]) -> pd.DataFrame` | Produce cross-run summary for notebooks | Accepts files or directories; optional filters by hypothesis |
| `export_stats(stats, destination)` | Persist to CSV/JSON for reporting | Allows repeatable outputs for `reports/` |

## Implementation Outline
- Create `hypothesis_testing/analytics/descriptive_stats.py` (mirrors repo structure and keeps notebooks slim).
- Define lightweight dataclasses in `models/` if needed (e.g., `NegotiationStats`, `PreferenceTrajectory`) to keep typing consistent.
- Leverage `pandas` for tabular outputs; fall back to pure Python lists for tests.
- Include helper methods (e.g., `_extract_rankings(agent_phase_data)`) to avoid duplicating parsing logic.
- Provide safeguards for missing keys (earlier runs may lack optional sections) and log warnings rather than failing.

## Validation Strategy
- Unit tests under `tests/unit/analytics/` to cover:
  - Successful parse of known fixtures (reuse existing JSON or create minimal samples).
  - Edge cases: zero vote rounds, absent `post_group_discussion`, inconsistent round counts.
- Integration test: load a directory of results and ensure aggregated metrics match manual expectations (e.g., `rounds_conducted_phase_2` equals derived round count).
- Notebook smoke check: ensure utilities return DataFrames readily consumed within Hypothesis 1 analysis.

## Next Steps
1. Confirm schema across remaining hypothesis result files; adjust dataclasses if variants exist.
2. Implement loader + summary functions, then write fixtures/tests.
3. Wire notebooks to call new utilities and regenerate visuals/tables.
