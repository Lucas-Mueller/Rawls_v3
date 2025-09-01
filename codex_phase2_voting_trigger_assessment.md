# Codex Assessment: Phase 2 Voting Trigger (Tool) — System-Level Gap Analysis

Date: 2025-08-31

## Executive Summary

- The `propose_vote` tool is present and enabled in Phase 2. Prompts in complex mode instruct agents to use it.
- Voting flow often does not trigger even when the tool is usable because the system only checks for tool calls on the public “discussion statement” turn — but the internal reasoning turn sometimes elicits the tool call first. Those tool calls are ignored.
- Additional contributors: brittle tool-call detection (class-name string checks), mixed prompting (reminders to “say let’s vote”), and configuration-mode interactions.
- Net effect: Monitoring may show tool calls; the experiment fails to initiate the two‑stage vote because that tool call is not observed on the specific turn the manager inspects.

Actionable fixes:
1) Detect tool calls in both internal reasoning and public statement runs (or forbid tool use during reasoning by prompt).
2) Harden `_check_for_tool_calls` to use SDK types/fields reliably.
3) Remove/align textual vote reminders and keep tool-only initiation in complex mode.
4) Add startup preflight + runtime diagnostics to make enablement and tool events explicit.

---

## What the Migration Plan Requires vs. What’s Implemented

Plan: `voting_trigger_tool_migration_plan.md`
- Replace keyword trigger detection with an explicit tool-call (`propose_vote`).
- Handle the tool-call in Phase 2 Manager → confirmation → two-stage secret ballot.
- Update prompts to emphasize the tool; remove “say ‘let’s vote’” text paths.

Current implementation highlights:
- Tool wiring: `experiment_agents/tools/voting_tools.py` defines `@function_tool(is_enabled=_is_phase2_group_discussion)` and is added to participant agents in `participant_agent.py`.
- Complex-mode prompts (English) do instruct: “You have access to a `propose_vote` FUNCTION TOOL… DO NOT say ‘let’s vote’.”
- Phase 2 checks for tool calls and then falls back to keyword triggers (`_handle_complex_voting_mode`).
- Voting orchestration (confirmation + two-stage ballot) is implemented in `Phase2Manager` + `TwoStageVotingManager`.

Gaps vs. plan:
- Tool-call detection occurs only on the public statement run, not on the internal reasoning run.
- Keyword fallback remains active and reminder messages still suggest “say ‘let’s vote’,” contrary to the plan’s end-state.
- Detection is brittle and can miss valid tool calls.

---

## Root Causes (Ranked)

1) Tool calls during internal reasoning are ignored (high impact)
- Where: `core/phase2_manager.py::_get_participant_statement_enhanced`
  - First, runs internal reasoning: `Runner.run(..., reasoning_prompt)`
  - Then runs the public discussion statement with `_get_participant_statement_with_retry()`
- Detection: `_check_for_tool_calls` is only called inside `_get_participant_statement_with_retry()` (the statement turn). If the model calls `propose_vote` in the reasoning turn (prompt explicitly asks “Are you ready to call for a vote?”), the manager never sees it.
- Symptom: Monitoring shows a tool call, but the system doesn’t trigger voting because it occurred in the reasoning run.

2) Brittle tool-call detection (medium impact)
- Where: `core/phase2_manager.py::_check_for_tool_calls`
- Issue: Relies on `item.__class__.__name__ in ['ToolCallItem','ToolCallOutputItem']` and ad-hoc attribute probing. If the SDK wraps/renames result items, valid tool calls are overlooked.
- Result: Even on the statement turn, some tool calls can be missed.

3) Mixed prompting / legacy text path (medium impact)
- Where:
  - `core/phase2_manager.py::_get_voting_reminder_message` still tells agents to “say ‘Let’s vote’,” contradicting the tool-only instruction.
  - Complex prompt is correct, but reminders create ambiguity and can shift model behavior.
- Result: Agents may produce text requests or call the tool in a turn the system ignores (e.g., reasoning), leading to non-triggering.

4) Mode behavior and expectations (contextual)
- In simple mode, tool calls are ignored by design (preference-only). Default config is complex, but custom configs could be simple and appear “broken.”
- Not the primary cause here, but keep in mind when reproducing.

5) Non-blocking but relevant issues
- Logging of available tools checks `participant.agent._tools` for display (agents may expose `agent.tools`). This is just logging, not functional.
- Final ranking gating (`role_description == "FinalRanking"`) is never set; tool stays enabled during final ranking. Not the trigger issue, but correctness/safety debt.

---

## Code Evidence Map

- Tool defined/enabled:
  - `experiment_agents/tools/voting_tools.py`: `@function_tool(is_enabled=_is_phase2_group_discussion)`; enabled if `context.phase == PHASE_2` and `role_description != "FinalRanking"`.
  - `experiment_agents/participant_agent.py`: tools set to `[propose_vote]`.

- Prompts:
  - `translations/english_prompts.json` → `phase2_discussion_prompt_complex`: instructs to use `propose_vote` and not text.
  - `phase2_internal_reasoning`: asks if agents are “ready to call for a vote,” which can cause tool use during reasoning.

- Detection only on statement turn:
  - `core/phase2_manager.py::_get_participant_statement_enhanced`:
    - Runs internal reasoning turn (no tool detection) → runs statement turn (with `_check_for_tool_calls`).

- Tool-call detector (brittle):
  - `core/phase2_manager.py::_check_for_tool_calls`: class-name string checks, manual attribute fishing.

- Voting orchestration:
  - `core/phase2_manager.py::handle_vote_proposal_tool` → `_conduct_confirmation_phase` → `_conduct_secret_ballot_phase`.
  - `core/two_stage_voting_manager.py`: robust two-stage voting with numeric validation.

- Legacy reminders:
  - `core/phase2_manager.py::_get_voting_reminder_message`: tells participants to “say ‘Let’s vote’,” which diverges from the plan.

---

## Reproduction Scenarios

- Complex mode, reasoning-enabled:
  1) Agent reads the complex prompt and the internal reasoning prompt.
  2) Model calls `propose_vote` during internal reasoning (monitor shows tool call).
  3) Manager ignores it (not checked), then requests public statement.
  4) No tool call on that turn → voting never triggers → appears “broken.”

- Complex mode, statement-only tool call with brittle detection:
  1) Model calls the tool during statement; SDK returns a wrapped item not matching string name checks.
  2) `_check_for_tool_calls` misses it → keyword fallback may or may not detect text → no vote triggered.

- Simple mode config:
  1) Model calls tool; Phase 2 Manager ignores tool in simple mode by design.
  2) Only preference statements matter → perceived as “tool not working.”

---

## Recommendations (Prioritized)

1) Observe tool calls on both turns
- Option A (preferable): Add `_check_for_tool_calls` on the internal reasoning result and handle it immediately (trigger confirmation+ballot), then skip the statement request for that participant.
- Option B: Change the internal reasoning prompt to explicitly forbid tool calls (“Do not call tools in this internal step; you may do so in your public statement”).

2) Harden `_check_for_tool_calls`
- Import and use SDK types where possible (e.g., `from agents.items import ToolCallItem, ToolCallOutputItem`) and switch to `isinstance(item, (ToolCallItem, ToolCallOutputItem))`.
- Also check for any standardized `result.tool_calls` field if exposed by your SDK version.
- Always log item types and any available `function_name` to debug.

3) Align prompts with the plan
- Remove or change `_get_voting_reminder_message` to reference the tool (not keyword phrases).
- Keep complex mode tool‑only. If fallbacks are retained, demote them and be explicit they are non-binding.

4) Diagnostics and safety rails
- Preflight: Run a small probe at startup in PHASE_2 context to verify tool calls surface; warn if not.
- Runtime logs: For each `Runner.run`, debug-log whether tools are enabled (`_is_phase2_group_discussion`), list tool names, and summarize any new_items types.

5) Optional guardrails
- If a participant says text like “let’s vote” in complex mode, issue a short follow-up reminding them to call `propose_vote` and re-prompt once, before falling back.
- During final ranking, set `role_description="FinalRanking"` to disable tools as intended.

---

## Implementation Sketch (Surgical)

A) Detect tool calls in internal reasoning
- In `Phase2Manager._get_participant_statement_enhanced`, after `reasoning_result = Runner.run(...)`, call `_check_for_tool_calls(reasoning_result)`. If `propose_vote`, immediately call `handle_vote_proposal_tool(...)` and return a no-op statement for this participant (or mark consensus result if reached).

B) Harden detector
- In `_check_for_tool_calls`, replace string-name checks with `isinstance` against SDK types if available. Add a fallback path that looks for a generic `function_name` attribute across items. Keep robust logging.

C) Prompt alignment
- Update `_get_voting_reminder_message` to instruct the tool path only.
- Optionally add a top-of-prompt “Tool Available: propose_vote” banner in complex mode to reduce dilution by long histories.

D) Diagnostics
- Add debug logs showing: tools enabled status for the context, tool names count, and `new_items` inspection summaries for every `Runner.run` in Phase 2.

---

## Why This Explains Your Observation

- You observed tool use in the monitoring UI, yet the system did not trigger voting. The most consistent explanation is that the tool call happened during the internal reasoning run, which is currently ignored by the manager. Secondary issues (brittle detection, mixed prompts) amplify the effect.

By capturing tool calls on both turns and hardening detection, the voting flow will reliably trigger as the migration plan intends.

---

## Next Steps (Offer)

If you want, I can:
- Patch `Phase2Manager` to detect tool calls on the reasoning turn and harden `_check_for_tool_calls`.
- Update reminder messaging to be tool-only.
- Add minimal diagnostics (debug-logs) for visibility during runs.

These are surgical changes that won’t alter unrelated functionality.

