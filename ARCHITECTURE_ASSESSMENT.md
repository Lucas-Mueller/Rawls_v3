# Core Architecture Assessment

This document evaluates the current architecture of the experiment’s core logic with respect to modularity, simplicity, separation of concerns, and maintainability. It focuses on the Phase 2 orchestration while considering the broader system components (models, utils, configuration, translations, and logging).

## Executive Summary

Overall, the architecture demonstrates solid intent: clearly defined data models, a separation between orchestration (managers) and domain logic (distribution generation, voting), and thoughtful internationalization, logging, and error handling. Recent refactors toward structured voting (`TwoStageVotingManager`) and compact memory deltas have reduced complexity and made key flows more deterministic.

However, `core/phase2_manager.py` has grown into a very large orchestrator (≈1.8–2.0k LOC, ≈100 KB), accumulating multiple responsibilities (prompt construction, IO/retries, validation, voting flow coordination, memory updates, analytics logging). This size and scope create complexity hotspots that make the code harder to reason about, test, and evolve. There are also minor consistency gaps around translation keys and a mixture of memory manager approaches.

Bottom line: the system is on the right path, but would benefit from extracting targeted submodules, consolidating memory update pathways, and tightening translation key validation. These focused changes will improve simplicity, testability, and robustness without altering core behavior.

## System Overview (Current Responsibilities)

- `core/experiment_manager.py`: Top-level orchestration across phases and result saving.
- `core/phase1_manager.py`: Individual rounds and learning (not the focus of this review).
- `core/phase2_manager.py`: Phase 2 group discussion orchestration: speaking order, prompts, retries/timeouts, vote prompting/confirmation, secret ballot integration, result application, memory updates, and final rankings.
- `core/two_stage_voting_manager.py`: Deterministic two-stage voting (principle selection → amount specification), validation, memory deltas, and vote result synthesis.
- `core/distribution_generator.py`: Domain logic for generating distributions and applying justice principles; payoff and counterfactual computation.
- `models/*`: Pydantic models and enums defining experiment data structures and state.
- `utils/*`: Memory managers, language/translation handling, logging, error handling, cultural formatting, etc.
- `translations/*`: Language-specific prompts and system messages.

## Strengths

- Clear domain modeling:
  - Pydantic models (`GroupDiscussionState`, `VoteResult`, `PrincipleChoice`, `Phase2Results`, etc.) provide structure and validation.
  - `DistributionGenerator` encapsulates principle application logic cleanly.
- Deterministic voting flow:
  - `TwoStageVotingManager` replaces free-form LLM parsing with regex/keyword validation and retry/timeouts, greatly improving correctness and simplicity of the voting core.
- Robust orchestration and resilience:
  - Timeouts, exponential backoff, quarantining failed/empty statements, and a consensus lock prevent deadlocks and state corruption.
  - Logging hooks (agent-centric and process) enable traceability and post-hoc analysis.
- Internationalization & formatting:
  - Central `LanguageManager` methods for two-stage voting prompts, errors, and timeouts; cultural amount formatting; wrapper methods in orchestrators.
- Memory footprint improvements:
  - Compact deltas via `utils/memory_content.py` reduce token costs while keeping salient context.

## Key Risks and Complexity Hotspots

1) Overloaded `Phase2Manager`
- Responsibilities include: topic prompts, retries/backoff, validation, speaking order strategy, voting initiation prompts, confirmation, secret ballot coordination, consensus detection plumbing, per-round/process logging, counterfactual building, and final memory updates.
- Impact: Reduced readability, higher regression risk during changes, and limited unit-testability for isolated concerns.

2) Mixed memory update pathways
- Both `SelectiveMemoryManager.update_memory_selective` and `MemoryManager.prompt_agent_for_memory_update` are used. This may be intentional, but increases variability and complexity in configuration and testing.

3) Translation key consistency gaps
- Example: English missing `phase2_no_consensus`, present in ES/ZH (falls back to `[MISSING: ...]`).
- Example: Income class display uses `results.income_classes` keys that don’t match enumerations (`medium_high`, `medium_low`), whereas `common.income_classes` does.
- Impact: Subtle user-facing issues and higher support/debug overhead.

4) Tight coupling of orchestration to i18n and formatting
- `Phase2Manager` builds prompts using language manager directly. This is practical, but makes it harder to unit test logic without translations and increases surface area for failure.

5) Inconsistent logging and analytics boundaries
- While logging is comprehensive, determination of what is logged and where (manager vs. submodule) is somewhat ad hoc, increasing cognitive load and duplication risk.

## Modularity & Simplicity Assessment

- Cohesion: High within domain-specific modules (`DistributionGenerator`, `TwoStageVotingManager`). Lower within `Phase2Manager` due to its breadth of responsibilities.
- Coupling: Managed between orchestrator and supporting utilities. However, `Phase2Manager` couples to many concerns (prompt building, validation, memory, voting, translations) directly.
- Interface boundaries: Agent interfaces are implicit (through `Runner`), and module boundaries are mostly clear. Some interfaces (e.g., for participant statement retrieval / prompting) could benefit from explicit classes or protocols for testability.
- Error handling: Centralized via `ExperimentErrorHandler` and explicit catching in high-risk areas. Good practice.
- Configuration: `ExperimentConfiguration`, `Phase2Settings`, and the language manager keep runtime behavior adjustable. Strong point.

## Concurrency & State

- Phase 2 runs rounds sequentially; within a round, calls are awaited with timeouts. A dedicated `_consensus_lock` and `_voting_in_progress` guard against re-entrant voting.
- `GroupDiscussionState` collects statements and voting history. State mutations are simple and explicit, which is good.
- Consideration: As features grow, a small explicit state machine (e.g., Discussion → VoteConfirmation → SecretBallot → Results) could make transitions safer, though this may be unnecessary if scope remains stable.

## Testing Posture

- Integration tests and logger fixture usage indicate a healthy testing strategy.
- Opportunities: Add more unit tests around sub-components if `Phase2Manager` is decomposed. Add regression tests for translation key presence and income class label mapping.

## Recommendations (Prioritized)

1) Decompose `Phase2Manager` into smaller, testable components
- Proposed structure:
  - `discussion_service.py`: statement prompting, retries/backoff, quarantine, and validation.
  - `voting_coordinator.py`: vote initiation prompting and confirmation flow (keep `TwoStageVotingManager` for ballots).
  - `memory_update_service.py`: centralized Phase 2 memory updates (discussion deltas, voting transitions, final results).
  - `prompt_builder.py`: prompt construction and i18n lookup helpers (reduce i18n coupling in orchestrators).
- Benefits: Lower cognitive load, improved testability, easier ownership for contributors.

2) Standardize memory update approach
- Choose one pathway (`SelectiveMemoryManager.update_memory_selective` or `MemoryManager.prompt_agent_for_memory_update`) for Phase 2, or define a simple routing policy and apply it consistently.
- Add a small wrapper with a consistent interface to minimize call-site branching.

3) Harden i18n contracts
- Add a translation validation step at startup or test-time to catch missing keys (e.g., `phase2_no_consensus`, voting prompts, and result keys).
- Align income class labels in `Phase 2` results to `common.income_classes.*` or add the missing keys to `results.income_classes`.

4) Clarify module boundaries for logging
- Define what gets logged where:
  - Orchestrators: lifecycle events, state transitions, and high-level metrics.
  - Sub-services: detailed operational logs (retries, parsing results, validation reasons).

5) Introduce typed interfaces (Protocols) for agents and language manager interactions
- Define minimal interfaces for `Runner` integration, language access, and memory updates to simplify mocking and improve type safety.

6) Performance & cost hygiene
- Continue using compact memory deltas and limit prompt previews in logs.
- Consider configurable caps on per-round statement length beyond current validation (e.g., truncate before logging and memory updates).

7) Documentation
- Add a concise architectural map under `docs/` illustrating Phase 2 call graph and responsibilities.
- Include a short “How to add a new voting method” guide to codify extension points.

## Specific Quick Fixes (Low-Risk)

- Translation: Add `phase2_no_consensus` in English to mirror ES/ZH.
- Localization: Use `common.income_classes.*` for assigned class display in Phase 2 results.
- Backoff log: Log the actual waited duration before multiplying the backoff factor.
- Remove legacy tool-call remnants: Clean up unused imports and branches related to tool detection.

## Architectural Maturity Score (Subjective)

- Domain modeling: 8.5/10
- Voting core determinism: 9/10
- Orchestration modularity: 6/10 (primary improvement area)
- I18n cohesion: 7/10 (mostly solid; a few key gaps)
- Testability: 7/10 (will rise with decomposition)

Overall: 7.5/10 — solid foundation with clear, tractable paths to improve modularity and simplicity.

## Appendix: Hotspots & Candidates for Extraction

- `core/phase2_manager.py`
  - Statement retrieval and validation methods (`_get_participant_statement_*`, retry/backoff, quarantine).
  - Vote initiation prompting/confirmation (`_prompt_for_vote_initiation`, `_conduct_confirmation_phase`).
  - Memory updates scattered across discussion/voting/final ranking (centralize via a service).
  - Prompt building methods (`_build_discussion_prompt`, `_build_internal_reasoning_prompt`).

- `utils/memory_content.py`
  - Strong basis for delta construction; consider adding small formatters for class names and principle names to reduce repetition in managers.

- `translations/*` and `utils/language_manager.py`
  - Add a test or startup validation routine to verify required keys for Phase 2 paths (discussion, voting, results).

