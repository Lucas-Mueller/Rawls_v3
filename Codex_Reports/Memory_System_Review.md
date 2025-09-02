# Memory System Review and Evaluation

## Executive Summary
The repository implements a two-tier memory system that combines (1) LLM-authored narrative memory updates with length controls and retries, and (2) selective direct insertions for simple facts to reduce cost. In Phase 1, memory is updated after each learning/application step via LLM prompts with compression safeguards. In Phase 2, a unified MemoryService orchestrates truncation, event classification, and delegation to either full LLM updates or simple append-only insertions. Overall, the system does its job: it preserves continuity across phases, records key actions and outcomes, and controls growth. A few issues merit attention, notably a translation key bug in utility-agent compression, and the absence of global-length checks when performing simple insertions.

## Architecture Overview
- LLM-based updates: `utils/memory_manager.py` (MemoryManager)
  - Builds localized prompts, retries on errors, and compresses near/exceeding limits.
  - Participant execution via `experiment_agents/participant_agent.py:update_memory()` with a minimal “MemoryUpdate” context.
- Selective routing: `utils/selective_memory_manager.py` (SelectiveMemoryManager)
  - Routes simple events (vote initiation/confirmations, ballot, amount) to direct appends; complex events (discussion statements, final results) to full LLM updates.
- Unified Phase 2 facade: `core/services/memory_service.py` (MemoryService)
  - Applies content truncation (statement ≤300 chars, reasoning ≤200), enforces guidance style, and calls SelectiveMemoryManager.
- Simple appends: `utils/simple_memory_manager.py` (used in tests; Phase 2 uses pre-formatted content + direct append in SelectiveMemoryManager).
- Display and summarization: `utils/language_manager.py` + `utils/memory_summarizer.py` for on-prompt memory inclusion and compact display.

## Phase 1 Flow (Does It Work?)
- Round content assembled in `core/phase1_manager.py` (ranking, explanations, applications, outcomes).
- Memory updated via `MemoryManager.prompt_agent_for_memory_update()` with `language_manager` prompts and `memory_guidance_style`.
- Near-limit handling: pre-update compression prompt; post-update tolerance (≤115%) with utility-agent fallback to compress; else safe truncation with annotation.
- Result: Narrative memory captures learning, choices, assignments, and earnings. Tests validate retries, limit enforcement, and error wrapping (`tests/unit/test_memory_manager.py`).

Observations
- Strength: Clear prompts, retries, compression before and after updates, localized content.
- Gap: Occasional direct `participant.update_memory(...)` in Phase 1 (e.g., constraint retry) bypasses the central validator/tolerance logic. Low risk given short content, but consider using MemoryService/MemoryManager for consistency.

## Phase 2 Flow (Does It Work?)
- Memory carried forward: `core/phase2_manager.py::_initialize_phase2_contexts()` validates/sanitizes Phase 1 memory via `MemoryService.validate_and_sanitize_memory()` and transfers it.
- Discussion rounds: `MemoryService.update_discussion_memory()` builds localized content, truncates parts, then routes to SelectiveMemoryManager.
- Voting: Voting-stage memory (initiation, confirmation, ballot, amount) uses localized insertions; routed as simple events (append-only) for efficiency.
- Final results: `update_final_results_memory()` formats outputs and routes for LLM update.

Observations
- Strength: Unified entry point, consistent formatting, event-aware truncation, proper routing, and strong unit coverage (`tests/unit/test_memory_service.py`).
- Gap: Simple append path in `SelectiveMemoryManager._simple_memory_update()` never checks overall memory length; extreme long-run histories could exceed character caps without triggering compression.

## Event Classification & Content Rules
- Classification rules in `SelectiveMemoryManager._classify_event()` cover vote initiation/confirmation, ballot, amount, discussion, phase transitions, and final results with pattern-based detection plus metadata hints.
- Truncation policy in `MemoryService.apply_content_truncation()` targets just the bloating segments of discussion entries (statement/reasoning), preserving fidelity while preventing runaway growth.
- Tests demonstrate contract compatibility and routing behavior, including config flag to disable selective updates (`test_selective_memory_updates.py`).

## Limits, Compression, and Prompts
- Pre-update compression: when memory >80% of limit, MemoryManager prompts the participant to compress to ~60%.
- Post-update tolerance: memories up to 115% of limit are accepted to avoid excessive churn; beyond that, a utility agent attempts compression to 50%; final fallback is truncation with an audit hint.
- Prompt localization: All prompts and memory insertions route through `LanguageManager`, with context-aware formatting. Display in non-memory steps uses full memory; compact summaries exist but are not used in Participant instructions currently.

Issue: Translation key mismatch
- In `MemoryManager._compress_memory_with_utility_agent()`, the code calls `language_manager.get("memory_compression_prompt", ...)` while the rest of the codebase uses `"prompts.memory_compression_prompt"`. This likely triggers a missing-key fallback and should be corrected.

## Error Handling and Telemetry
- Decorated with `handle_experiment_errors` for consistent categorization as `MEMORY_ERROR`, severity tagging, and logging via a global handler.
- Retries on transient failures; escalates to FATAL after max attempts, surfacing structured context (agent, attempt, limit).
- Phase 2 logs selective routing outcomes and warns on failures while re-raising to upstream handlers.

## Test Coverage Snapshot
- Unit tests validate MemoryManager length checks, retries, exception wrapping, and successful paths.
- MemoryService tests cover truncation behavior, routing to SelectiveMemoryManager, content formatting and metadata, and config fallback.
- Additional scripts validate summarization and selective update heuristics; golden tests assert API contracts.

## Does It Do Its Job?
Yes. The system:
- Captures and preserves salient information across phases.
- Keeps token and character growth in check with targeted truncation and compressions.
- Reduces LLM calls by routing routine events to low-cost append-only updates.
- Provides localized, consistent memory content and on-prompt display support.

## Risks and Edge Cases
- Global length drift on simple insertions: Append-only path can grow unbounded across many rounds if limits are never re-validated.
- Compression prompt key bug: Wrong translation key in utility-agent compression path can degrade compression quality or fall back to truncation.
- Inconsistent paths: A few direct `participant.update_memory(...)` calls bypass MemoryManager; minimal risk given content size, but weakens uniformity.
- Summarization use: Participant instructions always use full memory; compact summaries exist but are unused, increasing prompt size and cost.

## Recommendations
1) Fix translation key
- Change `language_manager.get("memory_compression_prompt", ...)` to `language_manager.get("prompts.memory_compression_prompt", ...)` in `utils/memory_manager.py`.

2) Re-validate after simple insertions
- After any simple append, if `len(context.memory) > 0.9 * limit`, call MemoryManager’s compression path to keep memory within guardrails. This can live in `MemoryService.update_memory_selective()` when event_type ∈ SIMPLE.

3) Standardize Phase 1 direct updates
- Route ad-hoc memory notes (e.g., constraint retry) through MemoryService or MemoryManager for consistent compression/tolerance behavior and localization.

4) Consider compact display for instructions
- For non-memory operations, use `LanguageManager.format_memory_section(..., display_mode="compact")` in participant instructions to reduce tokens while keeping key insights.

5) Instrumentation
- Track per-event memory deltas, compression invocations, and final memory size at Phase 2 end; log anomalies and add assertions in tests for runaway growth scenarios.

With these adjustments, the memory system remains robust, cost-efficient, and scalable across long Phase 2 discussions while preserving continuity and clarity.

