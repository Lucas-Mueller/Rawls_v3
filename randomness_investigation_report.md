# Phase 2 Randomness Divergence Investigation

## Context
Two sequential experiment runs with identical configuration, seeded `ExperimentConfiguration`, and temperature=0 local models stayed perfectly aligned through Phase 1 but diverged as soon as Phase 2 began. The expected behaviour is bit‑for‑bit replayability whenever the configuration seed is reused, so any drift indicates an uncontrolled randomness source in the Phase 2 pipeline.

This note documents the controls that are already in place, the additional randomness we discovered while tracing Phase 2, and recommended fixes. File references use 1-based line numbers.

## What Is Already Deterministic
- The experiment-scoped `SeedManager` seeds Python’s RNG once per run and exposes an experiment-local `random.Random` instance (`utils/seed_manager.py:62`).
- Phase 1 relies on per-participant RNGs derived from the effective seed, so task-level concurrency does not interfere (`core/phase1_manager.py:170`).
- Phase 2 services that explicitly consume randomness (speaking order, payoff distributions) are wired to the shared `SeedManager.random` (`core/services/speaking_order_service.py:115`, `core/services/counterfactuals_service.py:172`).

These pieces confirm the seed plumbing is functioning and explains why Phase 1 replayed exactly.

## Unseeded or Time-Based Inputs Introduced In Phase 2
The Phase 2 stack layers several dynamic values that are not anchored to the experiment seed:

1. **New UUIDs**
   - `FrohlichExperimentManager` generates a new `experiment_id` with `uuid.uuid4()` every run (`core/experiment_manager.py:69`).
   - `GroupDiscussionState` creates its own `experiment_id` the same way (`models/experiment_types.py:167`).
   - These IDs bleed into logging and can be serialized into transcripts or downstream tooling. If any prompt or memory template references them (directly or via formatted summaries), replayability breaks.

2. **Wall-Clock Timestamps**
   - Every discussion statement stores `timestamp=datetime.now()` by default (`models/experiment_types.py:145`).
   - `VoteResult` embeds a `timestamp` and `TwoStageVotingManager` writes per-participant `vote_timestamp` fields with `datetime.now().isoformat()` (`models/principle_types.py:110`, `core/two_stage_voting_manager.py:920`, `core/two_stage_voting_manager.py:982`).
   - Manipulator delivery metadata also logs `datetime.now()` (`core/services/manipulator_service.py:144` et seq.).
   - These values enter `discussion_state.vote_history` and memory payloads. The Phase 2 discussion header uses `discussion_state.public_history`; if earlier statements injected timestamps or the vote history is echoed back to agents, the prompts differ between runs even before any RNG usage.

3. **Shared RNG Consumption Without Phase Isolation**
   - Speaking order shuffles and payoff sampling draw from the same `SeedManager.random`. Any extra draw (for example, manipulator targeting code paths or future features) shifts the RNG stream and produces a new speaking order. Today that risk is low, but the single-stream design leaves Phase 2 fragile.

4. **Asynchronous Tasks With Implicit Timing**
   - `CounterfactualsService.collect_final_rankings_streamlined` launches concurrent tasks (`core/services/counterfactuals_service.py:1259`). If any task later calls into seeded randomness or reads time-sensitive state, the completion order could diverge run-to-run. This does not yet affect the first Phase 2 round but is worth flagging because the RNG stream is shared.

## Likely Root Cause For The Observed Divergence
Because the transcripts match through Phase 1, the deterministic RNG pipeline is intact up to Phase 2. The first Phase 2 prompt is constructed from:

1. The freshly built `ParticipantContext`, which inherits Phase 1 memory.
2. The Phase 2 discussion header produced by `language_manager.format_phase2_discussion_instructions`, which pulls from `discussion_state.public_history`.

`discussion_state.public_history` is seeded with the current round’s statement plus any system annotations. The system annotations come from `VotingService`, manipulator monitoring, and discussion truncation helpers. The presence of `datetime.now()` and `uuid.uuid4()` in those components means the very first prompt an agent sees in Phase 2 can carry per-run timestamps or IDs, even when earlier statements were deterministic. Once the prompt differs, the (otherwise deterministic) model can legitimately produce a different answer—matching the divergence you observed.

## Recommendations
1. **Eliminate Time/UUID Noise From Agent-Facing State**
   - Replace `uuid.uuid4()` with deterministic IDs derived from the experiment seed, or keep the UUIDs internal to logging and strip them before they reach contexts (`models/experiment_types.py:167`, `core/experiment_manager.py:69`).
   - Remove `datetime.now()` defaults from `DiscussionStatement` and `VoteResult`, or gate them behind a flag so deterministic runs can disable timestamps (`models/experiment_types.py:145`, `models/principle_types.py:110`).
   - Audit the memory and prompt builders to ensure `vote_timestamp`, `delivered_at`, and similar fields are not echoed back to agents. If they must be retained for auditing, store them separately from the text fed to models.

2. **Split RNG Streams Per Concern**
   - Instantiate dedicated `random.Random` streams for speaking order, payoff sampling, and any future stochastic behaviour. Derive each stream’s seed from the master seed (e.g., seed+phase offset) to keep them reproducible yet independent. This prevents future features from perturbing the speaking order sequence.

3. **Add Regression Coverage**
   - Introduce an integration test that runs Phase 1+2 with mocked deterministic agents and asserts byte-for-byte equality of the generated prompts/transcripts. This test will fail whenever a timestamp/UUID leaks into the prompt surface.
   - Log the RNG draw count right before Phase 2 speaking order generation (debug-only). A mismatch across runs pinpoints unexpected consumers.

4. **Triage Concurrent Code Paths**
   - Review asynchronous sections (`CounterfactualsService.collect_final_rankings_streamlined`) to confirm they do not call into the shared RNG or inject time-sensitive markers. If they must, guard them with deterministic schedulers or per-task RNGs seeded from the master seed.

Implementing the first two bullet points should remove the observed divergence. Once timestamps and UUIDs stop contaminating prompts, the existing seed-based controls ought to ensure Phase 2 behaves as deterministically as Phase 1.
