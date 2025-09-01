# Phase 2 Critical Review: Prompts, Memory, and Flow Construction

Author: External code reviewer (independent)
Scope: Phase 2 design and implementation across prompts, memory, and flow, with concrete references to code paths and observed behaviors from experiment results (e.g., `experiment_results_20250901_171224.json`).

## Executive Summary

The Phase 2 implementation is ambitious and feature-rich: it integrates a structured vote process (confirmation + two‑stage secret ballot), multilingual prompts, agent-managed memory with compression, and detailed agent-centric logging. However, the current design suffers from brittleness at phase boundaries, excessive coupling of concerns inside a very large manager (`core/phase2_manager.py` ~99k chars), and prompt-context interactions that likely degrade model compliance at the most critical times (ballots).

From the provided run: 5 discussion rounds occurred, no consensus was reached, and “prompted_vote” rounds recorded empty `participant_votes` while confirmation phases “occurred”. One agent privately shifted their final ranking to the other’s preferred principle, suggesting persuasion happened but the formal consensus mechanism failed to capture it. This aligns with several design issues identified below.

Key high-impact issues:

- Ballot fragility: one participant’s ballot failure aborts the entire vote, producing `None` and no recorded `participant_votes` for the round.
- Instruction/context contamination during ballots: full context and memory are still provided to the model during numeric-only prompts, encouraging verbose answers and timeouts.
- End-of-round prompting cadence: always prompting for voting after each round can derail organic negotiation and trains models to “wait for the prompt”.
- Memory strategy mixes agent‑generated narratives with system insertions, risking drift and verbosity ballooning precisely when concise compliance is required.
- Phase2Manager is overly monolithic and intermingles concerns (prompt assembly, turn loop, memory updates, vote orchestration, parsing & logging), impeding targeted fixes.

There is also a lot to praise: the two‑stage manager is a strong step toward deterministic validation; the language manager is thoughtfully structured; logging is rich; and memory compression is present. With targeted refactors and a few policy changes, Phase 2 can become much more robust without rewiring the entire system.

## Observed Behavior vs. Intent

From `experiment_results_20250901_171224.json` (and similar results):

- Vote rounds appear as `vote_type: "prompted_vote"`, with `confirmation_phase_occurred: true`, but `participant_votes: []` and no consensus. This pattern indicates the two‑stage ballot phase either failed early or never recorded per‑agent ballots into the logger.
- Agents debated for 5 rounds. One agent eventually changed their final ranking to the other’s principle, but without a captured consensus. This is consistent with persuasion without a robust vote capture.

These symptoms match the following code-level issues.

## Design Review

### 1) Flow Construction in `Phase2Manager`

Files:
- `core/phase2_manager.py` (very large; mixes orchestration, prompt construction, retries, memory updates, parsing, logging, voting transitions)
- `core/two_stage_voting_manager.py` (structured two‑stage ballots)

Strengths:
- Clear high-level phases: discussion → optional confirmation → two-stage secret ballot.
- Aggressive validation/pruning of invalid or quarantined statements to protect the conversation state.
- Locking around consensus state shows thoughtfulness about concurrency.

Issues:
- Monolithic class: `Phase2Manager` owns too many concerns. This makes changes risky and hard to test in isolation (e.g., ballot-only bugs force you to wade through discussion/memory concerns).
- Early returns and cross-cutting side effects: voting branches rely on a mix of `discussion_state` mutations, logger calls, and context tweaks; failures in one stage can leave logging inconclusive.
- Vote prompting policy: end-of-round, every round, each participant, via `_prompt_for_vote_initiation` (around lines ~880–1060) can feel like a “system interrupt” rather than an emergent group move. Combined with the removal of organic vote detection, agents get trained to wait for the prompt rather than propose votes in content.
- Quarantine behavior: quarantined responses skip all consensus mechanisms for that turn, which can subtly stall transitions.

Recommendations:
- Split Phase 2 into smaller, testable components: `DiscussionLoop`, `VotingCoordinator` (wrapping two‑stage manager and confirmation), `MemoryUpdater`, `PromptBuilder`. Keep `Phase2Manager` as the orchestrator.
- Decouple organic vote signaling from end-of-round prompting: re-enable in-content vote detection (with conservative heuristics) and make end-of-round prompts conditional (e.g., only after N turns without measurable convergence).
- Ensure all vote attempts produce a complete log artifact, even on failure (see “Ballot robustness” below).

### 2) Two-Stage Ballot Robustness (`TwoStageVotingManager`)

Files:
- `core/two_stage_voting_manager.py`

Strengths:
- Deterministic validation (digits 1–4 for principle; culturally aware amount parsing).
- Structured retry with localized feedback via `LanguageManager`.
- Memory update for ballots via `MemoryManager` using compact deltas.

Issues:
- Fatal all-or-nothing behavior: `conduct_full_voting_process` returns `None` when any participant fails stage 1 or 2. In practice, this yields vote rounds with confirmation but no `participant_votes`, obscuring root causes and losing partial signal.
- Instruction contamination: ballots run via `Runner.run(agent, prompt, context=context)` while `ParticipantAgent` still injects the full instruction header (memory, phase instructions, personality). For numeric-only ballots, this pushes the model toward verbose narrative answers and increases timeouts or multi-number responses. The validator tries to be forgiving, but it is compensating for prompt layering, not fixing it.
- Timeouts are aggressive relative to model behavior under verbose contexts; the code retries, but repeated timeouts still fail the entire vote.

Recommendations:
- Do not abort the entire vote on one participant’s failure. Record per-agent ballot results, mark failures as “abstain” or “invalid”, and still compute consensus if all valid ballots agree. Always write `participant_votes` to the log, including failures and error types. This alone will make debugging and analysis far easier.
- Use a “ballot micro-context” for Stage 1/2: temporarily switch to a minimal instruction set that contains only the ballot prompt and a tiny reminder to “answer ONLY with a number”. Concretely:
  - Add a lightweight `BallotContext` or set a flag on `ParticipantContext` consumed by `_generate_dynamic_instructions` to output a minimal system message during ballots (no memory dump, no phase explanation, no personality prose).
  - Alternatively, call `Runner.run` against a cloned agent with stripped instructions for ballots.
- Consider tool/form outputs if the model supports function calling, or apply strict pattern-checked echo prompts (e.g., “Print only a single digit on its own line. Any other text will be ignored.”) with a final validator that extracts the last line of digits.
- Extend timeouts slightly during ballots (e.g., 45–60s) or make them adaptive on first failure.

### 3) Prompt Design and Interaction Policies

Files:
- `utils/language_manager.py` + `translations/*_prompts.json`
- `core/phase2_manager.py` prompt builders: `_build_internal_reasoning_prompt`, `_build_discussion_prompt`, vote prompts

Strengths:
- Rich, localized content; principle names and messages are cleanly keyed.
- Two-stage prompts clearly enumerate numeric expectations.

Issues:
- Cognitive overload: discussion prompts are long and repeated; internal reasoning can be injected into the next public prompt (`_build_discussion_prompt`), potentially reinforcing verbosity.
- Ballot prompt fights the instruction header: formatted memory sections and phase guidance contradict “answer ONLY with a number”. This is likely a major contributor to failures and inconsistent replies.
- End-of-round vote initiation prompt every round can bias agents toward delaying genuine proposals; it also increases prompt churn and dilutes the discussion.

Recommendations:
- Slim the discussion prompt once the group gets going: after round 2, present only the last K statements plus a crisp call-to-action.
- Keep internal reasoning separate; don’t append it back into the public prompt. If retained, ensure it is not re-shown to the model as part of the next task’s input.
- For ballots and confirmation, use a minimal instruction header. Consider a style like: “System: You are filling a ballot form. Output exactly one number line. No other text.”
- Make vote prompting conditional: only trigger at end of round if heuristics suggest readiness (e.g., converging favored principles, explicit “let’s vote” content, or a maximum idle rounds threshold).

### 4) Memory Implementation and Strategy

Files:
- `utils/memory_manager.py` (agent-driven updates + compression)
- `utils/simple_memory_manager.py` (system insertions)
- `utils/memory_content.py` (delta builders)

Strengths:
- Memory compression pre-check and utility-agent fallback are thoughtful and pragmatic.
- Narrative/structured guidance mode with retry logic is a good abstraction.
- Delta builders target specific events (discussion, voting), which is clean.

Issues:
- Mixed authorship: both the agent and the system write to memory (insertions + agent narrative). This can create incoherence, repetitive lines, and mid-phase drift. It can also inflate context size, exacerbating ballot compliance failures.
- Compression guardrails use a 15% tolerance and sometimes fallback to truncation that appends meta text; if this happens repeatedly, memory becomes noisy.
- Memory updates happen immediately before vote prompting and ballots, which is precisely when you need the smallest, cleanest context.

Recommendations:
- Introduce a “memory write schedule”: avoid agent-generated memory updates right before ballots; use only minimal system insertions for clear, factual entries (e.g., “Agreed to vote”). Defer long-form narrative updates until after the vote concludes.
- Consolidate memory writers: prefer either agent-generated narrative OR minimal system insertions per phase boundary, but not both at the same time. If both are required, partition them: “narrative” section vs. “events” section, and keep the events section ultra-compact.
- Add a post-update validator that enforces maximum lines, removes boilerplate, and strips prior “compression meta lines” to avoid cascading noise.

### 5) Logging and Diagnostics

Files:
- `utils/agent_centric_logger.py`
- `models/logging_types.py` (implied by logger usage)

Strengths:
- Rich, per-agent logging with phase breakdowns, memory snapshots, and vote history.
- Voting history scaffolding includes `two_stage_details`, retries, and failure capture.

Issues:
- When `TwoStageVotingManager` returns `None`, `Phase2Manager` often completes vote rounds without any `participant_votes`. That is an information vacuum for forensic analysis.
- Some early returns skip populating details that would clarify which stage/participant failed.

Recommendations:
- Always log per-participant stage results (success/failure) even if the overall vote fails; attach error types (“timeout”, “invalid_format”, “retries_exhausted”). Populate `participant_votes` with explicit failure entries, not just successes.
- Summarize disagreement type in public history even on failure (you already do this for successful ballots without consensus); on failure, note “ballot failed for X participants”, which will help interpret dynamics post-hoc.

## Root-Cause Hypotheses for the Provided Run

Why did `participant_votes` end up empty after confirmation?

1) One participant failed Stage 1 or 2 repeatedly (timeout or invalid format), triggering `conduct_full_voting_process` to return `None`. Because the design aborts the entire ballot on any failure, no votes get recorded.
2) Instruction contamination: ballots ran within the full participant instruction header (memory, phase text). The model likely produced narrative text or multiple candidate numbers; despite forgiving digit parsing, a chain of retries and timeouts could still fail under the set timeout.
3) Prompt cadence: constant end-of-round prompting may have created “yes to vote” responses even when agents weren’t actually ready to comply with strict ballots, raising the chance of ballot failure.

These combined make it plausible to see confirmation occur but no ballots recorded.

## Strengths Worth Preserving

- Language and prompt localization are thoughtfully abstracted in `LanguageManager` and JSON files. The approach scales.
- The move to deterministic two-stage ballots is absolutely the right direction.
- Memory compression and the concept of delta-based memory updates (vs. wholesale rewrites) are solid.
- Agent-centric logging is rich and forward-looking (e.g., `two_stage_details`).

## Prioritized Recommendations

Short-term fixes (surgical, highest impact):
- Ballot robustness: Do not return `None` for the entire vote when one participant fails. Record partials, mark failures, compute consensus if possible. Always populate `participant_votes` and failure reasons.
- Ballot micro-context: Add a ``ballot`` interaction mode that disables the normal instruction header entirely. For `Runner.run` during ballots, provide a minimal system message that forces a single numeric output.
- Logging completeness: On any failure, log which stage and why (timeout, invalid format, retries exhausted). Surface this in `vote_history` and in the exported JSON.

Medium-term improvements:
- Refactor `Phase2Manager` into subcomponents: `DiscussionLoop`, `VotingCoordinator`, `PromptBuilder`, `MemoryUpdater`. Reduce file size and cross-concern coupling.
- Conditional vote prompting: Only prompt at end-of-round if heuristics indicate readiness (signal from recent statements, convergence, or an organic proposal). Re-enable organic proposal detection as a parallel trigger.
- Memory hygiene: During voting sub-phases, suppress narrative memory updates; use minimal system insertions only. After voting, re-enable narrative updates.

Long-term enhancements:
- Consider model-level constraints (function calling / JSON mode) for ballots where supported.
- Add property-based tests or scripted sims for Phase 2 flows (timeouts, malformed ballots, mixed-language ballots) to regression-proof changes.
- Explore structural deliberation aids (e.g., agenda, summaries, position trackers) that compress discussion context and reduce prompt size by round 3+.

## Concrete Implementation Pointers

- Two-stage voting return path:
  - In `core/two_stage_voting_manager.py:conduct_full_voting_process`, replace early `return None` on per-agent failure with per-agent failure recording. Build `VoteResult` with whatever valid votes exist; attach failure metadata.

- Minimal ballot context:
  - In `experiment_agents/participant_agent.py:_generate_dynamic_instructions`, gate on `context.interaction_type == "ballot"` (and also `"confirmation"`) to return a minimal system string, not the full memory/phase block.
  - Alternatively, create a cloned agent with stripped instructions just for ballots.

- Prompt silos:
  - Do not append internal reasoning back into public prompts (`_build_discussion_prompt`). Keep that siloed.
  - Reduce discussion history size shown after the first two rounds; keep last K lines only.

- Logging parity:
  - In `utils/agent_centric_logger.py`, ensure two‑stage failure paths attach to the current vote round even if consensus fails. You already have `two_stage_failures`; make sure the manager always calls these hooks.

## Final Assessment of the Hypothesis

Your hypothesis that Phase 2 has fundamental design flaws—especially in prompts, memory implementation, and flow construction—is substantially correct. The main issues are not conceptual (the overall design is sound) but are in integration boundaries and ergonomics under real model behavior:

- The ballot stage is fragile to a single agent’s failure.
- The prompts and instruction headers are misaligned at critical times (ballots/confirmation), leading to avoidable model non‑compliance.
- Memory updates and verbose context encodings likely degrade ballot reliability.
- The orchestration class is too large, making logic brittle and fixes costly.

However, the underlying architecture is close to excellent. With the targeted changes above—especially making ballots robust to partial failures and using a minimal ballot micro-context—you should see a significant increase in successful vote captures, better alignment between private rankings and public outcomes, and more organic, less prompt-driven transitions to voting.

I recommend starting with the short-term fixes in a focused branch, instrumenting a few synthetic tests (two agents; varied language; forced timeouts) to validate improvements, then iterating on the medium-term refactors.

