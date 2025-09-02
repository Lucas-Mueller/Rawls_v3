# Memory System Deep Analysis

Assessment date: 2025-09-02

This report explains how the repository’s memory system works, evaluates it in the context of the experiment, and recommends concrete, code‑level improvements.

## Architecture & Flow (What Exists)
- Core components:
  - `utils/memory_manager.py` (MemoryManager): orchestrates agent‑driven memory updates, pre/post length checks, compression, retries.
  - `utils/selective_memory_manager.py` (SelectiveMemoryManager): routes events to simple insertions vs. full LLM updates based on classification and metadata.
  - `utils/simple_memory_manager.py`: appends structured, localized snippets for factual events (vote initiation/confirmation, ballot choice, amounts, status).
  - `utils/memory_content.py`: composes compact “delta” strings for Phase 1/2 rounds and voting.
  - `utils/memory_summarizer.py`: generates compact context summaries for display to agents.
  - `experiment_agents/participant_agent.py`: formats instructions; uses memory summaries in context; uses “full” memory during voting, “compact” otherwise.
- Integration points:
  - Phase 1: `core/phase1_manager.py` updates memory after ranking/explanation/application/final ranking using `MemoryManager.prompt_agent_for_memory_update()`.
  - Phase 2: `core/phase2_manager.py` uses `SelectiveMemoryManager.update_memory_selective()` for discussion deltas, phase transitions, and final results; simple insertions capture vote decisions.
  - Two‑stage voting: `core/two_stage_voting_manager.py` builds compact voting deltas then calls `MemoryManager` to update agent memory.

## Detailed Behavior
- Update loop: `prompt_agent_for_memory_update()` builds a localized prompt (narrative/structured), calls `ParticipantAgent.update_memory()`, then enforces a base character limit with a 15% tolerance. If still too long, it compresses via a utility agent or truncates with an annotation when no utility agent is provided.
- Pre‑update compression: when existing memory exceeds 80% of the limit, `_compress_memory_if_needed()` asks the participant agent to compress to ~60% target.
- Compression via utility agent: `_compress_memory_with_utility_agent()` prompts the utility agent to produce a target‑length version; if it fails or exceeds target, truncation fallback is used.
- Selective routing: `SelectiveMemoryManager` classifies events (metadata first, then heuristics) and either appends via `SimpleMemoryManager` or falls back to the full MemoryManager path.
- Display to agents: `ParticipantAgent` injects memory using `LanguageManager.format_memory_section()`. Voting contexts render full memory to reduce “compromise forgetting”; discussion/application render compact summaries.

## Strengths (What Works Well)
- Delta‑based content: `memory_content.py` keeps memory focused and compact across phases.
- Cost control knobs: pre‑update compression, 15% tolerance, and a utility‑agent compression path.
- Selective updates: cheap inserts for factual voting events avoid extra LLM calls.
- Context‑aware display: compact vs. full memory renders reduce token load while preserving critical details during voting.
- Error framework: standardized categories, severities, and retry logic wrap memory operations.

## Risks & Issues (Observed in Code)
- Incoherent fallbacks: truncation markers preserve length limits but can destroy semantic continuity, especially near decision points.
- Bypass of constraints in simple inserts: `SimpleMemoryManager` appends without enforcing `memory_character_limit`, validation, or summarization. Memory can silently exceed limits until a later full update.
- Validation is shallow: MemoryManager validates length, not coherence; `SimpleMemoryManager.validate_memory_coherence()` is minimal and unused in write paths.
- Concurrency ordering: memory updates happen concurrently across agents; there is no per‑agent lock to prevent interleaving when multiple update sites write to the same `context` (e.g., a simple insert racing with a full update). Tests probe general isolation but no explicit locking guarantees.
- Event classification fragility: string‑pattern heuristics in `SelectiveMemoryManager._classify_event()` can misclassify; over‑ or under‑routing affects cost and fidelity.
- Prompt key inconsistency bug: `_compress_memory_with_utility_agent()` calls `language_manager.get("memory_compression_prompt", ...)`, while other paths use `"prompts.memory_compression_prompt"`. This likely misses the localized prompt key and should be fixed.
- Utility agent bottleneck: single parser agent compresses for all participants; failure or latency cascades to memory updates under load.

## In‑Experiment Implications
- Phase 1: frequent agent‑driven updates (ranking/explanation/application/finishing) produce O(rounds) LLM calls per agent; compression frequency grows with memory size.
- Phase 2 discussion: each statement generates a delta and a memory update. Costs balloon with rounds × participants unless selective routing and deltas remain tight.
- Voting: selective inserts reduce cost but risk growth without limits; the system partially addresses “compromise forgetting” by using full memory during voting.

## Recommendations

Immediate (low risk, high impact)
- Fix prompt key: change `_compress_memory_with_utility_agent()` to use `"prompts.memory_compression_prompt"` to align with other paths.
- Enforce limits on simple inserts: before appending, check projected length; when exceeding a threshold, summarize older segments (via `MemorySummarizer`) or call MemoryManager’s compression path. Add optional `max_append_bytes` and a “rotate + summarize tail” strategy.
- Per‑agent locking: introduce an `asyncio.Lock` per participant (e.g., in `ParticipantAgent` or a small `MemoryUpdateGate`) and ensure all write sites acquire it around `context.memory` mutations (both simple and full updates). This prevents interleaving.
- Minimal coherence checks: after any update, run a light validator that checks for sudden removals of recent deltas, malformed lines, or extreme repetition; log warnings and snapshot pre‑update memory for rollback if configured.
- Instrumentation: log memory lengths before/after updates, compression triggers, and fallback mode used; add counters for selective vs. full updates.

Near‑term
- Strengthen routing: prefer explicit `event_type` + metadata from call sites; reserve heuristic classification as a fallback only. Add unit tests covering each event path.
- Structured memory sections: split memory into labeled sections (Phase 1 summary, Discussion highlights, Voting history, Final outcomes). Store as structured text and render via `LanguageManager`. This enables targeted summarization and safer rotation/compression per section.
- Utility agent pool: allow N utility agents or a semaphore to parallelize compression and cap latency; add timeouts and circuit‑breakers with backoff.
- Tests: add unit tests for `SelectiveMemoryManager` routing, simple‑insert overflow handling, and the utility compression prompt path; add property tests for summarizer retention of key constraints during voting.

Longer‑term
- Constrained schema updates: replace free‑form agent memory updates with a constrained JSON (parsed by utility agent), then render to display text. This preserves structure and supports lossless compression.
- Checkpointing and audit: snapshot memory after milestones; persist an audit trail with diffs, lengths, and classifier decisions; expose a small validator CLI.
- Adaptive summarization: pin critical items (e.g., compromise amounts, final agreements) into a “sticky” section surfaced in all contexts until superseded.

## Quick Code Pointers
- Enforce simple insert limits: update `utils/simple_memory_manager.py` to consult `context.memory_character_limit` and summarize/rotate when needed.
- Locking: add a `self._memory_lock = asyncio.Lock()` in `ParticipantAgent` and wrap all update sites (Phase 1/2 managers and simple inserts) via a shared helper.
- Prompt key fix: in `utils/memory_manager.py` `_compress_memory_with_utility_agent()`, switch to `language_manager.get("prompts.memory_compression_prompt", ...)`.
- Routing tests: create `tests/unit/test_selective_memory_manager.py` to cover each `MemoryEventType` path with and without metadata overrides.

Overall, the system is well‑designed for clarity and token control, but it needs guardrails (limit enforcement on simple inserts, locking, prompt fix, and basic coherence validation) to be robust under load and during edge‑case failures.

