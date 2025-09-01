# Codex Issue Report: Phase 2 Voting Tool Re-Entrancy During Sub‑Phases

Date: 2025-08-31

## Executive Summary

Participant agents can still call the `propose_vote` tool after a vote has been initiated, including during the confirmation (1/0) step and during the two‑stage secret ballot. Because those sub‑phases are expecting strict numeric text responses (not tool calls), re‑entrant tool calls disrupt parsing and can cause the vote to fail after retries. This is not deliberate; it is a gating/handling gap.

High-level fixes:
- Disable the voting tool during confirmation and secret ballot via a context flag or subphase role.
- Additionally, detect and gracefully handle re‑entrant tool calls in those sub‑phases to avoid misclassifying them as malformed text.
- Strengthen prompts at these steps to explicitly prohibit tool use and request only the required numeric response.

---

## Symptoms You May Observe

- Monitoring shows repeated `propose_vote` tool calls while a vote is already in progress.
- Confirmation step fails because agents never respond with a clean “1” or “0”.
- Two‑stage ballot fails because agents return tool calls instead of “1–4” or a dollar amount.
- The process retries several times and aborts back to discussion despite agents being willing to vote.

---

## Affected Components

- `experiment_agents/tools/voting_tools.py`
  - Tool gate: `@function_tool(is_enabled=_is_phase2_group_discussion)`
  - Predicate: enabled for Phase 2 whenever `context.phase == PHASE_2` and `role_description != "FinalRanking"`.
- `core/phase2_manager.py`
  - Orchestration of group discussion, vote initiation, confirmation (`_conduct_confirmation_phase`), and ballot (`_conduct_secret_ballot_phase`).
  - Voting-in-progress guard: `self._voting_in_progress` is respected when tool calls are routed through `handle_vote_proposal_tool(...)`.
  - Sub‑phase I/O: confirmation expects “1/0” in `final_output` text only.
- `core/two_stage_voting_manager.py`
  - Stage 1: principle selection expects a single digit (1–4) as `final_output`.
  - Stage 2: amount specification expects a whole dollar amount as `final_output`.

---

## Current Flow (Relevant Parts)

- Discussion (complex mode):
  1) Agents can call `propose_vote` → `Phase2Manager` detects and triggers voting.
  2) `self._voting_in_progress = True`, `discussion_state.active_vote_in_progress = True`.
- Confirmation sub‑phase:
  - Each participant is prompted to respond “1” (yes) or “0” (no).
  - The code reads `result.final_output` and parses numerically.
  - It does NOT check for tool calls in `result.new_items` during this step.
- Two‑Stage Secret Ballot sub‑phase:
  - Stage 1: respond “1–4”. Stage 2: respond with a dollar amount.
  - The code reads `result.final_output` and validates text numerically.
  - It does NOT check for tool calls in `result.new_items` during these steps.

As a consequence, if an agent calls `propose_vote` again during confirmation or the ballot, the SDK emits a tool call (not the expected numeric text), the parser sees an invalid/missing number, and the step retries/fails.

---

## Evidence in Code (Key Points)

- Tool enablement is too broad for sub‑phases:
  - `experiment_agents/tools/voting_tools.py::_is_phase2_group_discussion(ctx, agent)` returns True for all Phase 2 contexts except when `role_description == "FinalRanking"`. Nothing in confirmation/ballot toggles this off.
- Sub‑phases do not detect tool calls:
  - `core/phase2_manager.py::_conduct_confirmation_phase(...)` only reads `result.final_output` and parses via `detect_numerical_agreement(...)`. No `_check_for_tool_calls(...)` call.
  - `core/two_stage_voting_manager.py::_conduct_principle_selection_with_retry(...)` and `_conduct_amount_specification_with_retry(...)` only read and validate `final_output`. No tool-call scan.
- Voting-in-progress guard cannot help if tool calls are never routed to it:
  - `self._voting_in_progress` is enforced in `handle_vote_proposal_tool(...)` and `_handle_complex_voting_mode(...)`, but sub‑phases never route tool calls into those paths.

---

## Reproduction Scenario

1) Run in complex mode so the tool is available during discussion.
2) One agent calls `propose_vote` → voting starts.
3) During confirmation, one participant again calls `propose_vote` instead of replying “1/0”.
4) The confirmation parser can’t find a valid digit → marks response invalid → retries → after max attempts, confirmation fails and discussion resumes.
5) Similarly, during the ballot steps, a re‑entrant tool call prevents the system from receiving the required “1–4” or amount.

---

## Impact

- Failed or delayed voting despite agents’ intent to comply.
- Confusing transcripts and wasted retries.
- Increased likelihood of falling back to discussion without reaching a ballot or consensus.

---

## Recommended Fixes (Surgical, Low Risk)

1) Disable tool during sub‑phases
- Introduce a context-level flag or subphase role that the tool gate checks.
  - Option A: Add `allow_vote_tool: bool` to `ParticipantContext` (default True in discussion).
    - Set to False in `_conduct_confirmation_phase` and throughout `TwoStageVotingManager` steps.
    - Restore to True when returning to discussion.
  - Option B: Reuse `role_description` as a subphase marker (e.g., `"VotingConfirmation"`, `"SecretBallot"`) and update `_is_phase2_group_discussion` to return True only for discussion roles.
- Benefit: Prevents re‑entrant tool calls at the source; SDK won’t surface a tool call button during these steps.

2) Detect and gracefully handle tool calls in sub‑phases (defense‑in‑depth)
- After each `Runner.run(...)` in confirmation and in both two-stage steps, call the same `_check_for_tool_calls(result)` used elsewhere.
- If `propose_vote` is detected:
  - If `self._voting_in_progress` is True: do not treat as an invalid numeric response. Instead, re‑prompt with a concise message: “Voting is already in progress. Please respond with the requested number only.”
  - Count it as a soft retry (or do not increment attempts) to avoid unnecessary failures.

3) Strengthen sub‑phase prompts
- Add a first-line instruction to confirmation/ballot prompts: “Do not call tools during this step. Respond only with the required number.”
- This reduces accidental tool use even if gating fails.

4) Optional: Keep textual fallbacks consistent
- If an agent types “let’s vote” during sub‑phases, respond with a reminder: “Voting is already in progress; please provide the requested number.”

---

## Implementation Sketch

Tool gate (predicate):
```python
# experiment_agents/tools/voting_tools.py

def _is_phase2_group_discussion(ctx, agent) -> bool:
    if not ctx or not hasattr(ctx, 'context') or not ctx.context:
        return False
    c = ctx.context
    # Prefer explicit allow flag if present
    allow_tool = getattr(c, 'allow_vote_tool', None)
    if allow_tool is not None:
        return c.phase == ExperimentPhase.PHASE_2 and allow_tool is True
    # Fallback to role-based gating
    return (c.phase == ExperimentPhase.PHASE_2 and c.role_description in (None, '', 'Discussion', c.role_description))
```

Confirmation sub‑phase (set flag and detect calls):
```python
# core/phase2_manager.py::_conduct_confirmation_phase
# before Runner.run(...): set context.allow_vote_tool = False for each participant
# after Runner.run(...): has_tool, info = self._check_for_tool_calls(result)
# if has_tool and info.get('tool_name') == 'propose_vote':
#     self._log_info("Duplicate vote proposal during confirmation; re-prompting for 1/0")
#     # re-prompt without counting as a hard failure
```

Two-stage ballot steps (similar pattern):
```python
# core/two_stage_voting_manager.py::_conduct_principle_selection_with_retry / _conduct_amount_specification_with_retry
# temporarily disable tool via context flag; detect tool calls and re-prompt for numeric input
```

Restoring the flag:
```python
# After confirmation/ballot conclude (success or failure), restore context.allow_vote_tool = True
```

---

## Risks and Trade‑offs

- Adding a context flag requires passing the updated context instance into `Runner.run(...)` in sub‑phases. This is already done, so the change is localized.
- Using `role_description` as a subphase marker is less explicit than a dedicated flag and may need careful integration with logging/memory.
- Tool-call detection in sub‑phases adds minimal overhead and improves robustness even if gating fails.

---

## Acceptance Criteria

- During confirmation and secret ballot runs:
  - The tool is not available in the UI (or, if surfaced, is ignored gracefully and the participant is re-prompted).
  - Legitimate “1/0”, “1–4”, and amount responses are parsed and progress the flow.
  - Re‑entrant `propose_vote` calls do not cause malformed-response failures or abort the vote.
- In discussion mode (complex):
  - Agents can call `propose_vote` to initiate voting as intended.

---

## Related Observations (FYI)

- The round‑3 voting reminder previously checked `hasattr(discussion_state, 'vote_triggered')`, which is always true due to the field’s presence. Use `if round_num == 3 and not discussion_state.vote_triggered:` instead.
- Consider not adding the placeholder “[Tool call in reasoning]” to public history when the tool is called during the internal reasoning turn, for cleaner transcripts.

---

By addressing the gating in sub‑phases and adding defensive detection, the voting process becomes robust to re‑entrant tool calls and aligns with the intended flow: propose → confirm (1/0) → secret ballot → consensus evaluation.

