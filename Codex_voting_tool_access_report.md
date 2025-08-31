# Codex Report: Phase 2 Voting Tool Access – System-Level Root Cause Analysis

This report analyzes why participant agents “don’t seem to have access to the voting tool in Phase 2 during group discussion,” traces the full experiment flow, and cross-checks the implementation against the OpenAI Agents SDK documentation included under `knowledge_base/agents_sdk`. The perspective taken is that of a participant agent, with a systems view from initialization through Phase 2 completion. Findings include where the hypothesis holds, where it likely doesn’t, and specific root-cause candidates with actionable fixes.

## Executive Summary

- The `propose_vote` function tool is implemented, registered on participant agents, and conditionally enabled for Phase 2 group discussion.
- In complex voting mode, Phase 2 Manager checks for tool calls and can kick off the two‑stage vote. In simple mode, tool calls are ignored by consensus logic (preference-only). This can look like “no access” from the outside because nothing happens when agents attempt to vote.
- The tool gating is correct for enabling during Phase 2 discussions, but final ranking gating is not actually enforced (role never switches to `"FinalRanking"`). This is orthogonal to the reported symptom but is a real defect.
- Tool‑call detection relies on brittle class‑name checks and not `isinstance` against the SDK’s result item types, risking false negatives if the SDK evolves or returns a slightly different object shape.
- Prompts and configuration mostly align with the migration plan; however, there are small inconsistencies (e.g., CLI log text still mentions “say ‘let’s vote’”) that can confuse model behavior.

Bottom line: participant agents do have the voting tool in complex mode, but the system may fail to recognize and react to tool calls due to detection fragility and mode gating. In simple mode, the tool is effectively inert by design. The hypothesis “agents don’t have access” is likely not the primary issue; the more accurate issues are “tool use not recognized” and “mode mismatch.”

## System Walkthrough (Participant Agent Perspective)

### 1) Initialization and Agent Setup

- Entry: `main.py` loads config, builds `FrohlichExperimentManager` with language manager.
- Participants created asynchronously with temperature detection: `core/experiment_manager.py -> create_participant_agents_with_dynamic_temperature()`.
- Participant agent construction: `experiment_agents/participant_agent.py`:
  - Agent is created with `tools=[propose_vote]`.
  - Instructions are dynamic via lambda, using `language_manager` and `experiment_config` to inject Phase‑specific prompts.
  - The `propose_vote` tool comes from `experiment_agents/tools/voting_tools.py` and is gated with `@function_tool(is_enabled=_is_phase2_group_discussion)`.
- Tool gating predicate: `_is_phase2_group_discussion(ctx, agent)` returns true only when `ctx.context.phase == ExperimentPhase.PHASE_2` and `role_description != "FinalRanking"`.

Conclusion: By construction, participant agents carry the voting tool, which is enabled during Phase 2 discussions if the RunContext is correctly supplied.

### 2) Phase 1 (Individual) Flow

- Managed by `core/phase1_manager.py`. Participants run without voting tools enabled (context is Phase 1). Nothing about tool access is expected here.

### 3) Transition (Phase 1 → Phase 2)

- `Phase2Manager._initialize_phase2_contexts()` creates `ParticipantContext` objects with:
  - `phase=ExperimentPhase.PHASE_2`
  - `role_description=agent_config.personality` (note: never set to `"FinalRanking"` later)
  - `memory` carried forward, sanitized.

This ensures the tool’s `is_enabled` predicate sees Phase 2.

### 4) Phase 2 Group Discussion Loop

- Core loop: `core/phase2_manager.py::_run_group_discussion()`.
- For each participant per round:
  1) Build prompt with `language_manager.get_phase2_instructions(round, voting_mode)`. In complex mode, the English prompt explicitly says “You have access to a `propose_vote` FUNCTION TOOL…” (`translations/english_prompts.json: phase2_discussion_prompt_complex`).
  2) Run: `Runner.run(participant.agent, discussion_prompt, context=ParticipantContext)`.
  3) Detect tool use: `_check_for_tool_calls(result)` scans `result.new_items` looking for tool calls; if found and tool is `propose_vote`, Phase 2 Manager calls `handle_vote_proposal_tool`.
  4) Else, in complex mode it uses keyword triggers as fallback; in simple mode it ignores tools and only tracks textual preferences.

Conclusion: In complex mode, a tool call should be seen and acted upon; in simple mode, a tool call will not be used for consensus.

### 5) Complex Mode Voting Sequencing

- Tool trigger path: `handle_vote_proposal_tool(...)` sets `vote_triggered` and `_voting_in_progress`, logs, runs confirmation via `_conduct_confirmation_phase(...)`, then secret ballot via `_conduct_secret_ballot_phase(...)`, both reusing existing logic.
- This path mirrors `_handle_complex_voting_mode(...)` (keyword‑trigger fallback). If detection fails, it appears as if the tool was “not available.”

### 6) Final Ranking

- `Phase2Manager._get_final_ranking()` runs a separate prompt to collect individual final rankings. Context’s `role_description` never changes to `"FinalRanking"`, so the tool gating condition intended to disable tools during final ranking is never triggered. This is a real but separate defect.

## Findings (Where Hypothesis Holds vs. Not)

### A. Tool Registration and Availability (Likely OK)

- Code paths show participants are created with `tools=[propose_vote]` (participant agent `async_init`).
- Tool `is_enabled` predicate will be true during Phase 2 group discussion because `phase == PHASE_2` and `role_description != "FinalRanking"`.
- Prompts in complex mode explicitly instruct calling the function tool.

Assessment: Participants do have access in complex mode. The hypothesis that they don’t have access is likely not the main issue.

### B. Mode Gating (Source of “Nothing Happens”)

- Complex mode: tool calls are recognized and used to initiate voting (intended behavior).
- Simple mode: code never handles tool calls. It only checks `detect_preference_statement(...)` and `check_preference_consensus_simple_mode(...)`. Tools are thus effectively inert, which can be perceived as “no access.”

Assessment: If a run uses simple mode (custom config), tool calls won’t take effect. Verify `voting_detection_mode` at runtime.

### C. Tool Call Detection Fragility (Probable Root Cause)

- `_check_for_tool_calls(result)` relies on comparing `item.__class__.__name__` to `'ToolCallItem'` or `'ToolCallOutputItem'` and manual attribute fishing on `raw_item`.
- The Agents SDK docs (`knowledge_base/agents_sdk/results.md`) indicate using `result.new_items` of types `ToolCallItem` and `ToolCallOutputItem`. Relying on class name strings is brittle to version changes or wrappers.
- If detection fails, the system won’t invoke `handle_vote_proposal_tool(...)`, making it look like the tool wasn’t available.

Assessment: Replace class‑name string checks with robust `isinstance` checks against the SDK’s item classes, and handle both ToolCall and ToolCallOutput consistently.

### D. Final Ranking Tool Gating (Real Bug, Opposite Direction)

- Gating condition checks `role_description != "FinalRanking"` to disable the tool during final ranking.
- The system never sets `role_description` to `"FinalRanking"` during the final ranking prompt, so the tool stays enabled at the wrong time.

Assessment: Not the cause of “no access,” but a correctness issue to fix: switch context role for final ranking or adjust gating.

### E. Prompting and Instruction Mismatch (Minor Confusion)

- `translations/english_prompts.json` complex prompt correctly instructs use of the function tool.
- `main.py` log message under complex mode still mentions “Agents can call for votes using 'Let's vote' or similar” (legacy text). This is not agent‑visible, but it reflects a lingering conceptual mismatch.

Assessment: Update developer/console messaging to match the new tool behavior for clarity.

### F. SDK Alignment Checks

- Tools: Defined via `@function_tool` per `knowledge_base/agents_sdk/tools.md`, optionally gated by `is_enabled(ctx, agent)`.
- Results: Tool calls are surfaced via `result.new_items` with `ToolCallItem` and `ToolCallOutputItem` (`knowledge_base/agents_sdk/results.md`). Code should use these types directly where possible.
- Context: Agents are generic over context; `ParticipantContext` is a Pydantic model, acceptable as a RunContext object (`knowledge_base/agents_sdk/agents.md`).

Assessment: The implementation is broadly consistent with SDK guidance, with detection that could be more robust.

## Root-Cause Candidates (Ranked)

1) Detection brittleness in `_check_for_tool_calls` (high probability)
   - Class name string matching and ad‑hoc attribute probing can miss valid tool calls depending on SDK version or item shape.
   - Impact: Tool calls appear to be ignored → perceived as “no access.”

2) Mode mismatch: using simple mode while expecting tool‑based voting (medium probability)
   - In simple mode, Phase 2 Manager never triggers voting from tool calls.
   - Impact: No voting even if agents call the tool.

3) Model/toolability mismatch (medium/low probability)
   - If a model variant does not reliably perform tool calling (or if a provider adapts responses oddly), tools might rarely be invoked by the LLM.
   - Impact: Appears as “no access” despite correct registration.

4) Prompting clarity or round budget (low probability)
   - If prompts are truncated or too long, tool usage instructions could be missed. Less likely given current prompt sizes.

5) Final ranking gating bug (real but unrelated)
   - Tool remains enabled during final ranking; not the cause of “no access” but should be corrected for correctness and safety.

## Evidence Map (Key Files and Behaviors)

- Tool definition and gating:
  - `experiment_agents/tools/voting_tools.py` – `@function_tool(is_enabled=_is_phase2_group_discussion)` with Phase 2 + non‑FinalRanking predicate.
- Tool registration on participants:
  - `experiment_agents/participant_agent.py` – Agent constructed with `tools=[propose_vote]`.
- Tool availability messaging to agents (complex mode):
  - `translations/english_prompts.json: phase2_discussion_prompt_complex` – explicitly instructs use of the `propose_vote` function tool.
- Mode gating in Phase 2 logic:
  - `core/phase2_manager.py::_run_group_discussion()` – only in `voting_detection_mode == "complex"` does it check `tool_call_info` → `handle_vote_proposal_tool(...)`.
- Tool call detection:
  - `core/phase2_manager.py::_check_for_tool_calls` – scans `result.new_items` with brittle class name string comparisons.
- Final ranking gating (bug):
  - `core/phase2_manager.py::_get_final_ranking` uses the same context; role is never switched to disable the tool.

## Recommended Fixes

1) Harden tool call detection
   - Import and use SDK item classes directly:
     - `from agents.items import ToolCallItem, ToolCallOutputItem`
     - Replace class‑name string checks with `isinstance(item, (ToolCallItem, ToolCallOutputItem))`.
     - Reliably extract `function_name` and arguments from the item’s accessor methods/properties.
   - Log full `result.new_items` types once per round at debug level for visibility.

2) Respect tool calls in simple mode (optional, but reduces confusion)
   - Either document that tools do nothing in simple mode or add a small branch: if a tool call occurs in simple mode, short‑circuit to complex voting flow (or at least emit a system reminder that formal voting is disabled in simple mode).

3) Fix final‑ranking tool gating
   - Before final ranking, clone the participant context with `role_description="FinalRanking"` or add a dedicated flag in context.
   - Alternatively, change gating to use an explicit boolean in context (e.g., `context.is_final_ranking`), avoiding brittle string checks.

4) Align developer logs
   - Update `main.py` complex‑mode messaging to reference function tools rather than “let’s vote” textual triggers.

5) Add targeted tests
   - Unit: simulate a `RunResult` with `ToolCallItem`/`ToolCallOutputItem` and verify `_check_for_tool_calls` picks up `propose_vote`.
   - Integration: in complex mode, mock a participant calling the tool and assert `handle_vote_proposal_tool` path runs.
   - Regression: ensure no tool path is taken in simple mode unless explicitly desired.

## Quick Verification Steps (Manual)

- Run with complex mode (default config shows `voting_detection_mode: "complex"`).
- Increase logging to DEBUG and run a short experiment. Confirm logs show:
  - Tool listing on agent creation (optional debug print of `agent.tools`).
  - Per round, `_check_for_tool_calls` logs: `Result has new_items …` and item types.
  - If a tool is invoked, `✅ Detected propose_vote tool call!` should appear followed by the confirmation/ballot logs.
- Switch to simple mode and confirm tool calls are ignored; ensure the behavior matches expectations/documentation.

## Conclusion

The tool is correctly defined and attached to participant agents. In complex mode, the system is intended to react to `propose_vote` tool calls but may fail to detect them due to brittle result‑item inspection. In simple mode, tool calls are ignored by design, which can be misinterpreted as lack of access. Additionally, tool gating for final ranking is incorrectly implemented (tool remains enabled). Addressing the detection robustness, clarifying or extending simple‑mode behavior, and fixing final‑ranking gating will resolve the observed issues and align the implementation with the migration plan and the Agents SDK’s documented patterns.

