# Internal Reasoning Bold Rendering Investigation

## Summary
- **Observation**: During Phase 2 discussion turns, the internal reasoning that gets echoed back to the speaking agent renders with the final paragraph in bold.
- **Finding**: No Markdown emphasis is injected by the code. The bold formatting is a rendering side-effect triggered by the delimiter used in `internal_reasoning_context_format`.
- **Root Cause**: The line of equal signs (`================================`) immediately after the reasoning content is interpreted by the Codex CLI's Markdown renderer as a Setext heading underline, so the line above it (the reasoning's final paragraph) is promoted to an H1-style heading.

## What The Code Does
1. `LanguageManager.format_context_info()` sanitizes the reasoning text and wraps it with `internal_reasoning_context_format` before embedding it in the system prompt (`utils/language_manager.py:522-566`).
2. The English translation for that format string is defined as:
   ```json
   "internal_reasoning_context_format": "=== Your Internal Reasoning ===\n{internal_reasoning}\n================================"
   ```
   (`translations/english_prompts.json:88`)
3. Because there is no blank line between `{internal_reasoning}` and the closing `================================`, the final line of reasoning sits directly above the equals-sign line at runtime.

## Why Rendering Turns The Last Paragraph Bold
- In Markdown, a line of text followed immediately by a line of `=` characters is parsed as a Setext level-1 heading.
- The Codex CLI that wraps OpenAI's Runner renders headings with bold weight.
- Therefore, whenever the reasoning block has any trailing content, its last line becomes a heading simply because of the underline delimiter—not because the agent added `**` markers.
- A similar issue was fixed earlier for the discussion transcript; note the explicit comment "blank line before closing delimiter prevents bold rendering" inside `format_phase2_discussion_instructions()` (`utils/language_manager.py:721-753`). The internal reasoning format never received the same treatment.

## Evidence Collected
- Printing the context payload locally shows plain text with `================================` underlining the reasoning. When rendered by the CLI, the line directly above the underline appears bold even though the raw payload has no emphasis markers.
- Removing the underline (or inserting a blank line between the reasoning text and the underline) during ad-hoc tests eliminates the bold effect, confirming the renderer is applying Setext heading rules.

## Recommendations (No Code Changes Applied)
1. Adjust the localized template so there is a blank line between `{internal_reasoning}` and the underline, or replace the underline with a delimiter that does not trigger heading parsing (e.g., dashes, as already used for discussion history).
2. Audit the non-English prompt files to ensure they use the same delimiter pattern; they currently mirror the English template and will exhibit the same rendering quirk.
3. Document in the prompt style guide that Markdown heading underlines should be avoided in agent-facing context strings when exact rendering matters.

