# Phase 2 Design Assessment — Memory System and Prompt Design

Author: Codex CLI
Date: 2025-09-01

## Executive Summary

- The Phase 2 implementation shows solid progress: Phase 1 memory carries forward, discussion rounds are validated with retries and timeouts, and a structured two‑stage voting system replaces brittle free‑form parsing. However, prompt and memory design choices currently create friction at the vote handoff and add avoidable noise or ambiguity.
- Primary risks to consensus and clarity:
  - Secret ballot prompts are generic and not contextualized to the group’s negotiated candidate (principle and amount), increasing divergence during ballots.
  - Consensus requires strict unanimity on both principle and exact constraint amount; tolerance and reconciliation settings exist but are not used in two‑stage consensus evaluation.
  - Mixed‑language/mixed‑style prompt fragments (e.g., English section headers) slip into localized prompts, risking degraded model performance in non‑English settings.
  - Memory compression uses translation keys inconsistently and can silently fall back to truncation; there’s opportunity to compress more semantically and to store targeted Phase 2 summaries that prime ballots.

High‑impact fixes:
- Contextualize ballot prompts with the currently negotiated principle and the latest stated constraint amount, and nudge for confirmation vs. deviation.
- Implement constraint tolerance and a one‑turn reconciliation prompt before declaring ballot failure.
- Remove English-only markers and unify all dynamic strings under the translation system.
- Fix the memory compression key mismatch and add a compact “phase2 discussion summary” memory block to carry into voting.

## Scope of Review

- Phase 2 flow: `core/phase2_manager.py` (discussion rounds, vote prompting, confirmation, secret ballot)
- Two-stage voting: `core/two_stage_voting_manager.py`
- Memory system: `utils/memory_manager.py`, `utils/simple_memory_manager.py`, `utils/memory_content.py`
- Language/i18n: `utils/language_manager.py`, `translations/english_prompts.json` (and structure assumptions for other locales)
- Configuration: `config/phase2_settings.py` (tolerances, timeouts, correction settings)

## What Works Well

- Discussion and validation
  - Statement retries with exponential backoff, minimum-length checks per language family, and clear logging of retries/fallbacks.
  - Quarantining failed responses prevents contaminating the public history.

- Memory continuity and bounded growth
  - Phase 1 memory is validated/sanitized then carried into Phase 2 contexts; discussion history is bounded to 100k characters and trimmed from the front.
  - Memory updates run through a guided prompt; compression triggers near the limit and uses a utility agent where available.

- Structured voting
  - Two-stage manager enforces numeric principle selection and integer amount entry with retry feedback, reducing parse errors.
  - Tool usage is disabled during critical voting sub-phases to avoid side effects.

## Key Issues and Risks

1) Ballot prompts are generic, not contextualized
- Where: `core/two_stage_voting_manager.py` and `translations/*_prompts.json` keys `two_stage_principle_selection` and `two_stage_amount_specification`.
- Impact: After apparent convergence in discussion, ballots reset context and ask for a fresh choice. This invites divergence and undermines consensus even when agents publicly agree.
- Symptom to watch: Discussion states like “we agree on maximizing average with a $25,000 floor” followed by secret ballots that split across options.

2) Strict unanimity without tolerance or reconciliation
- Where: `core/two_stage_voting_manager.py:_create_vote_result`
- Current behavior: Consensus requires exact identity on both principle and constraint amount. No use of `Phase2Settings.constraint_tolerance` and no reconciliation step.
- Impact: Near‑matches (e.g., $24,500 vs. $25,000) are treated as failure; single‑turn corrections could salvage consensus.

3) Mixed-language and hard-coded English fragments
- Where: `core/phase2_manager.py:_build_discussion_prompt` appends “=== YOUR INTERNAL REASONING === … Based on your internal reasoning …” in English; dynamic group composition strings are built in English.
- Also: Bracketed section tags like `[VOTING INITIATED]`, `[VOTING CONFIRMATION]` are hard-coded English.
- Impact: In non‑English settings, mixed-language prompts reduce model reliability and clarity.

4) Memory compression key mismatch and semantic compression gaps
- Where: `utils/memory_manager.py` uses `language_manager.get("prompts.memory_compression_prompt")` in one path and `language_manager.get("memory_compression_prompt")` in the utility-agent path.
- Impact: The latter likely misses the intended key (lacks `prompts.` prefix) and falls back to truncation more often than necessary.
- Opportunity: Structured compression and a dedicated “Phase 2 discussion summary” block can improve salience and reduce bloat.

5) Prompt verbosity and cognitive load
- Where: `prompts.phase2_discussion_prompt` includes long principle descriptions and stakes text on every turn; `_build_discussion_prompt` duplicates context and inserts internal-reasoning headers.
- Impact: Longer prompts increase token use and dilute the most important ask for the turn.

## Detailed Findings

### Memory System

- Strengths
  - Validates and sanitizes Phase 1 memory before Phase 2 start; keeps memory as the single source of agent context.
  - Compression heuristic: trigger at ~80% of limit, allow up to 115% once, then compress to ~50–60% target; use utility agent when available.
  - Lightweight factual insertions (vote initiation decision, confirmation, secret ballot choice) avoid extra LLM calls for trivial facts.

- Gaps/Risks
  - Key mismatch: `MemoryManager._compress_memory_with_utility_agent` calls `language_manager.get("memory_compression_prompt", ...)` (no `prompts.`) while prompts are defined under `prompts.memory_compression_prompt`; likely causes fallback truncation.
  - Compression quality varies: generic narrative compression can retain noise. There is no dedicated Phase 2 “discussion state summary” to prime later prompts (especially ballots).
  - Duplicate insertion keys in translations increase maintenance risk (multiple `memory_insertions` blocks); prefer a single canonical path.
  - English-only section headers leak into memory content via `_build_discussion_prompt` and can reappear in memory since round deltas echo prompts.

- Recommendations
  - Fix translation key for compression in `_compress_memory_with_utility_agent` to use `prompts.memory_compression_prompt`.
  - Add a compact, standardized Phase 2 summary memory block each round:
    - Fields: “last consensus candidate (principle)”, “latest stated constraint amount(s) with speaker)”, “open disagreements”, “readiness to vote snapshot”.
    - Store under a single memory delta line (e.g., `Phase 2 Summary: Candidate=..., Amount=$..., Disagreements=..., ReadyToVote=...`).
  - Switch to structured compression template when over limit: headings for “Decisions”, “Amounts”, “Rationales”, “Outcomes”; avoid story-like rehashes.
  - De-duplicate translation keys: consolidate `memory_insertions` under one section.

### Prompt Design

- Discussion prompts
  - Good: Language-managed templates and dynamic inclusion of history.
  - Issues: Verbose, includes English-only internal reasoning headers; group composition string hard-coded in English; no succinct reminder of the current candidate principle/amount.

- Vote initiation and confirmation
  - Strength: Uses numeric 1/0 with retries and timeouts; disables voting tool during confirmation/ballot.
  - Issue: No reinforcement of the current candidate principle/amount at the moment of asking to initiate voting.

- Two-stage ballot prompts
  - Good: Deterministic validation removes messy parsing; retry feedback is localized via `LanguageManager` helpers.
  - Issues: Prompts are generic; they do not mention the negotiated candidate. Amount specification has no “confirm or edit” nudge relative to the last discussed amount.
  - Consensus function ignores tolerance; no reconciliation step to converge near‑matches.

## Concrete Improvements

1) Contextualize ballots with the negotiated candidate
- Principle stage prompt (new template idea):
  - “Based on the discussion so far, the group appears to converge on {candidate_principle_name}. If you agree, reply with its number. If you disagree, select another number.”
- Amount stage prompt (new template idea):
  - “The most recently discussed amount for {principle_name} was ${last_amount}. If you agree, reply with {last_amount}. Otherwise, reply with your amount as a whole number.”

2) Add constraint tolerance and reconciliation
- Logic in `_create_vote_result` (or a wrapper):
  - If all votes share the same principle and all amounts fall within `±constraint_tolerance`, treat as consensus at the median or most-frequent amount.
  - If not within tolerance, run a one‑turn reconciliation prompt: “Amounts differ: {a,b}. Propose a compromise in [min,max] or confirm your amount.” If convergence achieved, finalize; otherwise fail.

3) Remove English-only fragments and fully localize
- Move “=== YOUR INTERNAL REASONING === …” and bracketed section tags into translations. Provide localized section markers or remove section headers entirely in favor of more concise instructions.
- Localize group composition strings in `_build_discussion_prompt` via templates like `prompts.phase2_group_participants` with pluralization variants.

4) Reduce verbosity and chunk information
- Shorten per‑turn principle descriptions; include the detailed “Four Principles” block only on the first turn per participant/phase (the language manager already tracks first turns for experiment explanation; extend that pattern for detailed principle text).
- Prepend a 1–2 line “Discussion Snapshot” (candidate, last amount, disagreements) sourced from the new Phase 2 summary memory block.

5) Memory system fixes and enhancements
- Fix key path in `_compress_memory_with_utility_agent` to `prompts.memory_compression_prompt`.
- Add a structured memory-guidance style for Phase 2 when over limit (e.g., `memory_guidance_style="structured"`), and ensure `translations/*_prompts.json` has a concise, sectioned compression template.
- Add tests that simulate memory near limits to confirm that utility-agent compression is called and that the correct template key is retrieved.

## Example Prompt Revisions (English)

- Discussion prompt (concise, contextual, localized)
  - Header: “Group Discussion — Round {round_number}/{max_rounds}”
  - Snapshot: “Candidate: {candidate_principle} | Latest amount: ${last_amount or ‘—’} | Ready to vote: {yes/no}”
  - Request: “State your position or propose a change. Keep it brief.”

- Vote initiation prompt (contextual)
  - “You recently said: ‘{agent_recent_statement}’. Move to voting now? Reply 1=Yes or 0=No.”

- Two-stage ballot prompts (contextualized)
  - Stage 1: “We appear to converge on {candidate_principle_name}. If you agree, reply with its number. Otherwise, pick 1–4.”
  - Stage 2: “Last discussed amount was ${last_amount}. Reply with {last_amount} to confirm, or a different whole number.”

Corresponding translation keys to add:
- `prompts.phase2_snapshot_line`
- `prompts.phase2_group_participants` (with pluralization variants)
- `prompts.two_stage_principle_selection_contextual`
- `prompts.two_stage_amount_specification_contextual`
- `prompts.section_headers.internal_reasoning` (localized equivalent)
- `prompts.section_headers.voting_initiated`, `prompts.section_headers.voting_confirmation`, etc.

## Code-Level To‑Dos (surgical)

- Two-stage consensus tolerance
  - Update `core/two_stage_voting_manager.py:_create_vote_result` to use `Phase2Settings.constraint_tolerance` when judging equality of amounts for constraint principles.
  - Add a small reconciliation step (one retry) if outside tolerance, using a new `prompts.two_stage_amount_reconcile` template.

- Memory compression key fix
  - In `utils/memory_manager.py:_compress_memory_with_utility_agent`, change `language_manager.get("memory_compression_prompt", ...)` to `language_manager.get("prompts.memory_compression_prompt", ...)`.

- Localize English fragments
  - Replace hard-coded group composition strings in `_build_discussion_prompt` with a localized template.
  - Move English section headers and bracket tags to translation keys; ensure `language_manager` supplies the localized variants.

- Snapshot memory block
  - After each speaking turn, compute and insert a single compact snapshot into memory via `utils/memory_content.build_phase2_delta` extension or a new helper (e.g., `build_phase2_snapshot`). Use this snapshot to build contextual ballot prompts.

## Validation Plan

- Unit tests
  - Memory compression path: verify correct key usage and that utility-agent compression triggers and reduces size.
  - Two-stage tolerance: surface tests where amounts differ within tolerance and confirm consensus.
  - Reconciliation: simulate small divergences beyond tolerance and confirm one‑turn reconciliation flow.

- Integration tests
  - Simulate a discussion where both agents verbally converge on principle and amount; ensure ballots converge with contextual prompts and/or tolerance.
  - Multilingual smoke tests (e.g., Mandarin) to catch mixed-language artifacts in prompts.

## Closing

The current Phase 2 scaffolding is strong: resilient statement collection, consistent memory progression, and a deterministic voting mechanism. The remaining gaps are largely about aligning prompts and consensus rules with the social context established in discussion. Contextualizing ballots, enabling small tolerances and reconciliation, and fully localizing dynamic text will reduce false “no-consensus” outcomes and make the system more robust across languages.

