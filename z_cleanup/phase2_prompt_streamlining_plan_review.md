# Review: Phase 2 Prompt Orchestration Review and Streamlining Plan

**Reviewer**: Claude Code
**Date**: 2025-10-01
**Document Reviewed**: phase2_prompt_streamlining_plan.md

## Executive Summary

This plan demonstrates **excellent diagnostic work** in identifying prompt construction pain points, but proposes solutions that risk **overengineering** and **deviation from the established services-first architecture**. The analysis is thorough and accurate, but the proposed remediation introduces new abstractions (prompt state objects, builder modules, mega-methods) that may trade one form of complexity for another.

**Recommendation**: Accept the diagnostic analysis and baseline testing approach (Steps 1-2), but significantly simplify the architectural changes (Steps 3-7) to work **within** the existing services pattern rather than adding new layers.

---

## Strengths of the Analysis

### 1. **Accurate Problem Identification**
The plan correctly identifies the core architectural smells:
- Hidden coupling via `_current_public_history` side channel (lines 17-18)
- Duplicate prompt assembly in retry callbacks (line 18-19)
- Test coverage drift from production behavior (line 21-22)
- Scattered context mutation (line 20-21)

These are real issues that merit attention.

### 2. **Constraint Recognition**
The explicit requirement that "Prompts Must Stay Bit-for-Bit Identical" (line 24) demonstrates appropriate caution. The proposal to establish golden test baselines **before** refactoring (Step 1, lines 25-27) is sound risk management.

### 3. **Comprehensive Scope**
The review traces the full lifecycle from context headers through agent prompts to memory updates, touching all relevant modules (Phase2Manager, services, ParticipantAgent, translation helpers).

### 4. **Risk Awareness**
The "Risks & Open Questions" section (lines 57-61) shows appropriate concern about translation key management, logging sequencing, and intelligent retry preservation.

---

## Critical Concerns with Proposed Solution

### 1. **Architectural Mismatch: Builder Module Contradicts Services-First Design**

**Issue**: Step 3 proposes creating `core/prompting/phase2_prompt_builder.py` with "pure functions for each prompt type" (lines 33-37).

**Problem**: The existing codebase already follows a **services-first architecture** where prompt construction is a service responsibility:
- `DiscussionService.build_discussion_prompt()` (line 11)
- `DiscussionService.build_internal_reasoning_prompt()` (line 10)
- `VotingService` handles voting prompts (line 13)
- `CounterfactualsService` manages results prompts (line 14)

Adding a builder layer creates a **two-tier system** where services delegate to builders, increasing indirection without clear benefit. From CLAUDE.md:
> "The Phase2Manager acts as an orchestrator that delegates specific responsibilities to these services, ensuring clean separation of concerns and maintainability."

**Better Approach**: Improve the **existing service methods** rather than introducing a new abstraction layer. Make services the single source of truth for their prompt types.

---

### 2. **Mega-Method Risk: `run_turn()` Violates Single Responsibility**

**Issue**: Step 4 proposes replacing "two-step calls with a single `DiscussionService.run_turn(...)`" that handles prompt building, execution, validation, retries, and returns structured results (lines 38-43).

**Problem**: This bundles too many concerns into one method:
- Prompt construction (service concern)
- Agent execution (orchestration concern)
- Validation (service concern)
- Retry logic (orchestration concern)
- Result structuring (data modeling concern)

This shifts orchestration responsibility **from Phase2Manager into DiscussionService**, contradicting the established pattern where Phase2Manager orchestrates and services provide focused capabilities.

**Better Approach**: Keep prompt construction in services, but leave orchestration (Runner invocation, retry loops) in Phase2Manager where it belongs. The services should be **consulted**, not become orchestrators themselves.

---

### 3. **Prompt State Objects: Potential Over-Abstraction**

**Issue**: Step 2 proposes "lightweight dataclasses (e.g., `Phase2PromptState`, `Phase2TurnContext`)" to encapsulate round number, participant list, public history, etc. (lines 29-32).

**Problem**: The plan doesn't justify why these are needed when:
- `GroupDiscussionState` already exists and contains round, participants, history
- `ParticipantContext` exists for agent-specific state
- `Phase2Settings` contains configuration

Adding new state objects risks:
- **Data duplication**: Copying data from existing models into new ones
- **Synchronization burden**: Keeping multiple state representations in sync
- **Unclear ownership**: Which object is the source of truth?

**Better Approach**: If state passing is the issue, pass the **existing state objects** more explicitly rather than creating new ones. The problem isn't missing abstractions—it's inappropriate coupling (e.g., `_current_public_history` side channel).

---

### 4. **Insufficient Migration Strategy**

**Issue**: Step 7 proposes retiring `_current_public_history` (lines 53-56) but provides minimal detail on how to accomplish this safely.

**Problem**: This attribute is deeply integrated:
- Set by Phase2Manager before agent calls (line 9)
- Read by ParticipantAgent.format_context_info() (line 17)
- Required by memory services (line 17)

Simply "migrating ParticipantAgent to receive formatted context directly" (line 54) glosses over:
- How to inject the context without using the config attribute
- How to ensure memory services get the same history
- How to maintain thread safety if running parallel operations
- How to verify the migration maintains prompt identity

**Better Approach**: Provide a detailed, testable migration plan with intermediate states and rollback options.

---

### 5. **Golden Test Strategy Needs Refinement**

**Issue**: Step 1 proposes extending golden tests to "snapshot the *actual* prompts generated in production flows" (line 26).

**Concern**: The plan doesn't address:
- **Where** to capture these snapshots (at service output? at Runner input? at agent final prompt?)
- **How** to handle dynamic content (timestamps, randomized speaking orders, agent-specific context)
- **What** to do when legitimate changes require updating dozens of snapshots

**Better Approach**: Define a clear snapshot strategy with:
- Minimal number of snapshot points (prefer testing service outputs, not end-to-end flows)
- Parameterization to handle dynamic content
- Clear update policy when intentional changes occur

---

## Alignment with Codebase Principles

The CLAUDE.md file emphasizes:
> "Obey the principle of simplicity, do not overengineer things. Stay effective"

**Evaluation**:
- ✅ **Problem diagnosis**: Simple, clear, effective
- ⚠️ **Proposed solution**: Complex, introduces new layers, risks overengineering

The plan's architectural additions (builder modules, prompt state objects, mega-methods) seem to violate this principle.

---

## Specific Recommendations

### **Recommended Approach: Incremental Service Improvement**

Rather than the 7-step plan, consider a **3-phase incremental approach**:

#### **Phase 1: Establish Safety Net**
1. Add golden tests for **service-level prompt outputs** (not end-to-end)
   - Test `DiscussionService.build_discussion_prompt()` output
   - Test `DiscussionService.build_internal_reasoning_prompt()` output
   - Test voting service prompt outputs
   - Parameterize tests to handle dynamic content (round numbers, agent names)
   - Cover English/Spanish/Mandarin variants

2. Add integration tests for `_current_public_history` usage
   - Verify it's set before agent calls
   - Verify it's read by ParticipantAgent correctly
   - Verify memory services use it consistently

#### **Phase 2: Eliminate Hidden Coupling**
1. Add explicit history parameter to service methods
   - `build_discussion_prompt(discussion_state, public_history)` instead of relying on config
   - `build_internal_reasoning_prompt(..., public_history)` same pattern
   - Pass history explicitly in Phase2Manager before each service call

2. Update ParticipantAgent to receive formatted context
   - Add `formatted_context_header: Optional[str]` to ParticipantContext
   - When present, use it instead of calling `format_context_info()`
   - Phase2Manager pre-formats and injects this before Runner calls

3. Deprecate `_current_public_history` gradually
   - Mark as deprecated, add warnings if used
   - Remove only after all callers migrated to explicit passing
   - Golden tests verify prompts unchanged throughout

#### **Phase 3: Consolidate Duplicate Logic**
1. Eliminate retry callback duplication
   - Extract prompt reconstruction into reusable service method
   - Both normal flow and retry callback use same method
   - No need for mega-method—keep retry orchestration in manager

2. Consolidate voting prompt logic
   - Ensure VotingService and TwoStageVotingManager share prompt helpers
   - Extract common formatting (transcript, participant list) into utility functions
   - Keep utilities as **private module functions**, not a new builder class

3. Standardize context mutation
   - Add helper methods to ParticipantContext for common operations
   - `prepare_for_final_ranking()` clears reasoning, sets interaction type, etc.
   - Services call these helpers rather than manually mutating fields

---

### **Specific Line-by-Line Feedback**

**Lines 33-37 (Builder Module)**:
> "Create `core/prompting/phase2_prompt_builder.py` housing pure functions..."

**Feedback**: Don't create a new module. Improve existing service methods instead. If code sharing is needed, use **private utility functions within services** or a small `_prompt_utils.py` helper, not a public builder API.

**Lines 38-43 (run_turn mega-method)**:
> "Replace the current two-step calls with a single `DiscussionService.run_turn(...)`"

**Feedback**: Keep orchestration in Phase2Manager. Services should provide prompts, not execute turns. If you want to reduce duplication, extract a `_execute_discussion_turn_with_retry()` helper in Phase2Manager that both normal and retry flows use.

**Lines 29-32 (Prompt State Objects)**:
> "Add lightweight dataclasses (e.g., `Phase2PromptState`, `Phase2TurnContext`)"

**Feedback**: Only add these if you can demonstrate they eliminate existing duplication. Otherwise, pass `GroupDiscussionState` and `ParticipantContext` more explicitly—don't create parallel state hierarchies.

**Lines 53-56 (Retire _current_public_history)**:
> "Once the builder accepts explicit history input..."

**Feedback**: This should be its own detailed sub-plan with migration phases, not a single step. Consider a compatibility mode where both old (config attribute) and new (explicit param) work temporarily during migration.

---

## Unanswered Questions

1. **What specific prompt construction code is duplicated?**
   - The plan mentions duplication (line 18-19) but doesn't show concrete examples
   - Without seeing the duplication, hard to evaluate if proposed solutions actually eliminate it

2. **Why are current prompts insufficient?**
   - The plan identifies that `build_discussion_prompt()` "ignores most of its parameters" (line 19)
   - But doesn't explain **why** those parameters exist or what they should do
   - Is the issue that parameters are unused, or that they're used incorrectly?

3. **What's the rollback strategy?**
   - If the refactor causes subtle prompt changes or breaks experiments mid-stream, how do you revert?
   - Feature flags mentioned briefly (line 64) but not detailed

4. **How do you handle in-flight experiments?**
   - If configuration files or saved states contain old prompt structures, does the refactor break them?
   - Need compatibility plan for existing experiment checkpoints

---

## Risk Assessment

**High Risk Areas in Proposed Plan**:
1. **Prompt identity preservation** (criticality: HIGH)
   - Any deviation breaks experiment validity
   - Golden tests must cover all execution paths, not just happy path

2. **Services-first architecture violation** (criticality: MEDIUM)
   - Builder layer and mega-methods diverge from established patterns
   - Future developers may not know where to add prompt logic

3. **Migration complexity** (criticality: HIGH)
   - Multiple interdependent changes (state objects, builder, run_turn, retire _current_public_history)
   - Hard to test incrementally if changes must happen together

**Lower Risk Areas**:
1. **Baseline testing** (Step 1) - low risk, high value
2. **Translation key consolidation** - low risk if done carefully with fallbacks
3. **Context mutation helpers** - low risk, incremental improvement

---

## Conclusion

**Accept**: The problem analysis (lines 8-23) and risk identification (lines 57-61)

**Revise**: The proposed solution architecture (lines 24-56)

**Recommended Next Steps**:
1. Implement Phase 1 of the simplified approach (golden tests, integration tests)
2. Create a **prototype branch** that eliminates `_current_public_history` without adding builder/state abstractions
3. Measure whether the prototype actually reduces coupling and complexity
4. If prototype succeeds, proceed with incremental rollout
5. If prototype doesn't clearly improve things, consider the problem "documented but not urgent"

The current system, while imperfect, is **functional and testable**. Refactoring should make it **meaningfully simpler**, not just differently complex. Apply the project's own principle: "Obey the principle of simplicity, do not overengineer things."
