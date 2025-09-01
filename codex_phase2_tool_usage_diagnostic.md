# Codex Report: Why Phase 2 Agents Aren’t Using Tools

## Executive Summary

- Tools are correctly attached to participant agents and enabled in Phase 2.
- Agents still don’t “use” tools because the underlying model/provider is not emitting tool calls in responses.
- The most likely cause is provider capability mismatch: models routed via LiteLLM/OpenRouter (e.g., `google/gemini-2.0-flash-lite-001`) often do not support function/tool calling in the way the OpenAI Agents SDK expects.
- Secondary contributors: brittle tool-call detection and (rare) prompt alignment issues.
- Net effect: Phase 2 works via text-based fallbacks, but true tool invocation paths don’t fire.

## What’s Working

- Tool definition: `experiment_agents/tools/voting_tools.py` defines `propose_vote` with `@function_tool(is_enabled=_is_phase2_group_discussion)` and a clear docstring description.
- Tool attachment: `ParticipantAgent.async_init()` constructs `Agent(..., tools=[propose_vote], ...)`. Tools show under `agent.tools` after the logging fix.
- Phase 2 instructions (complex mode) explicitly tell the agent to call the `propose_vote()` function tool and not to write text like “let’s vote”.
- Phase 2 detects tool calls if they are present by scanning `result.new_items` for tool call items.

## What’s Not Working (System-Level View)

1) Provider/tool-call capability mismatch (primary)
- Many runs in your logs use models like `google/gemini-2.0-flash-lite-001` (via OpenRouter). Function/tool calling support varies by provider and model.
- The OpenAI Agents SDK surfaces tools across providers only when the backend supports tool/function calls with compatible semantics. Gemini via OpenRouter frequently does not.
- Result: The model never emits tool call items, so `_check_for_tool_calls` never sees any, and the system falls back to text logic.

2) Tool-call detection robustness (secondary)
- `_check_for_tool_calls` checks class names `'ToolCallItem'`/`'ToolCallOutputItem'` instead of using the actual classes. This is brittle to SDK changes or wrappers.
- If the SDK alters item class names or wraps them, tool calls could be missed even if the model emitted them.

3) Prompt alignment (minor)
- Phase 2 complex prompt already emphasizes function-tool usage. This is unlikely the blocker, but models that don’t support tools will still ignore it and generate plain text.

## Evidence from Codebase

- Tools are exposed via `agent.tools`, not `agent._tools` (we fixed logging to reflect this correctly).
- The `propose_vote` tool is enabled in Phase 2 unless `role_description == "FinalRanking"`.
- Agent default `tool_use_behavior` is `'run_llm_again'` which supports iterative tool use; we don’t override it, which is fine.
- Complex mode Phase 2 logic first checks for tool calls, then falls back to keyword-based triggers: if tools aren’t supported by the model, the system still proceeds using text heuristics.

## Likely Real-World Cause (Why you observed no tool usage)

- Your runs used non-OpenAI models through the LiteLLM/OpenRouter path. Those backends frequently do not implement OpenAI-style function calling, so no tool calls are produced regardless of your prompts.
- When you switched to OpenAI-native models (e.g., `gpt-4.1`, `gpt-4o-mini`), you would be more likely to see tools used as intended (assuming API keys and access are properly configured).

## Recommendations (Actionable)

1) Use tool-capable models for Phase 2
- Prefer OpenAI models known to support tools in the Agents SDK: e.g., `gpt-4.1`, `gpt-4o-mini`, `gpt-4o`.
- Avoid or treat as text-only: OpenRouter/LiteLLM-wrapped models (e.g., Gemini) unless you can confirm function/tool calling support end-to-end.
- Add a config switch to force tool-capable models in Phase 2: for example, `phase2_force_openai_tool_models: true` with per-agent overrides.

2) Add a preflight tool-capability check
- At experiment startup, for each distinct model in use, run a trivial tool-capability probe:
  - Create a test `Agent` with a minimal `@function_tool` and prompt: “Call the `hello` tool now.”
  - If the model produces a `ToolCallItem`, mark it tool-capable; otherwise flag it as text-only.
  - Log a clear warning per model: “Tool calling unsupported; will rely on text fallbacks.”

3) Harden tool-call detection
- Import SDK item types: `from agents.items import ToolCallItem, ToolCallOutputItem` and use `isinstance(item, (ToolCallItem, ToolCallOutputItem))` instead of string name matching.
- Also check for a generic `result.tool_calls` attribute if exposed by the SDK version you’re pinned to.

4) Improve diagnostics
- On each `Runner.run`, if `result.new_items` exists, log their concrete types and any `function_name` fields (at debug level) for early visibility.
- Log `len(agent.tools)` and tool names on agent initialization (debug).

5) Graceful fallbacks
- Keep the current keyword-based voting triggers as a fallback path when tools aren’t supported.
- Consider switching to “simple” mode automatically if preflight finds no tool-capable models.

## Minimal Code Changes Suggested

- Detection robustness (example):
  - In `core/phase2_manager.py::_check_for_tool_calls`:
    - `from agents.items import ToolCallItem, ToolCallOutputItem`
    - Replace class-name comparisons with `isinstance(item, (ToolCallItem, ToolCallOutputItem))`.
    - Read `item.function_name` and `item.arguments` when available.

- Preflight probe (outline):
  - Add `utils/tool_diagnostics.py` with `async def model_supports_tools(model_spec) -> bool`.
  - Create a temporary `Agent` with a trivial `@function_tool` and run a short prompt. Detect presence of `ToolCallItem`.
  - Integrate into startup of `ExperimentManager` to warn and optionally flip `voting_detection_mode`.

## Quick Validation Plan

1) Run with OpenAI model (tool-capable):
- Config: set participants to `gpt-4o-mini` and utility to `gpt-4o-mini`.
- Expect: Phase 2 logs show the `propose_vote` tool and, in complex mode, at least some runs emit a tool call that triggers voting via `handle_vote_proposal_tool`.

2) Run with Gemini via OpenRouter:
- Expect: No tool call items in `result.new_items`; system relies on text fallbacks.
- Logs: Preflight probe warns that tools are not supported for this model.

## Conclusion

- The system is correctly wiring tools, but most of your observed runs used provider/models that don’t support tool calling under the OpenAI Agents SDK.
- Adopt tool-capable models for Phase 2, add a preflight capability probe, and harden tool-call detection. These steps will make tool usage reliable and diagnostics clearer while preserving current fallbacks.

