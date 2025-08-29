**Phase 2 Failures: Root Cause Analysis (Detail‑Obsessed)**

This report identifies the underlying issues behind the two Phase 2 test failures provided, pinpoints the exact code paths involved, and proposes precise, low‑risk fixes with rationale.

Failing tests (2):
- `tests/unit/test_phase2_vote_intention_detection.py::TestVoteIntentionDetection::test_llm_fallback_behavior`
- `tests/integration/test_phase2_quarantine_behavior.py::TestPhase2QuarantineBehavior::test_agent_timeout_quarantine`

Warnings (contextual):
- Resource warning about an un‑awaited coroutine in constraint correction tests. Not a failure, but noted below.

---

**Failure 1: LLM Fallback Vote Intention Detection Returns False Positive**

- Symptom (from failure log): Expected no vote intention when LLM returns "NO_VOTE_DETECTED", but `detect_vote_intention_enhanced()` returned the original statement (non‑None), leading to assertion failure.

- Test case causing failure:
  - Statement: "Another complex statement"
  - Mocked LLM response: `"NO_VOTE_DETECTED"`
  - Expected: `None`
  - Actual: Non‑None (the input statement string)

- Code path:
  - File: `experiment_agents/utility_agent.py`
  - Function: `detect_vote_intention_enhanced()`
  - Relevant logic:
    - Builds `vote_detection_prompt` and calls `Runner.run(self.parser_agent, ...)`.
    - Parses `response = result.final_output.strip()`.
    - Detection branch:
      - If `"VOTE_INTENTION_DETECTED" in response or "VOTE_DETECTED" in response` → treat as positive → return `statement`.
      - Else → log and proceed to fallback patterns.

- Root cause (exact):
  - The positive detection branch uses substring checks. The negative token `NO_VOTE_DETECTED` contains the substring `VOTE_DETECTED`, so the condition inadvertently matches and returns a false positive.
  - Additionally, the prompt instructs the model to reply with `NO_VOTE_INTENTION`, while the test uses `NO_VOTE_DETECTED`. The code does not explicitly check for any negative tokens; it only checks for positive tokens (with substring semantics). This magnifies the issue.

- Why this is robustly reproducible:
  - Any negative response that embeds a positive token (e.g., `NO_VOTE_DETECTED`, `NOT_VOTE_DETECTED`) will trigger the substring positive branch.

- Minimal, safe fix (behavior‑preserving elsewhere):
  - Parse the LLM response with exact, uppercased, token‑level checks.
    - First, handle negative responses with precedence: exact match for `NO_VOTE_INTENTION` and `NO_VOTE_DETECTED` (case‑insensitive, whitespace‑tolerant), and do not proceed to positive branch if matched.
    - Then, detect positives with exact equality or a clear prefix (e.g., `VOTE_INTENTION_DETECTED`, `VOTE_DETECTED`, optional suffix detail after a colon) using regex with anchors or startswith.
  - Pseudocode change in `detect_vote_intention_enhanced()`:
    - `resp = response.upper().strip()`
    - `if resp.startswith("NO_VOTE_INTENTION") or resp.startswith("NO_VOTE_DETECTED"):` → return `None`.
    - `elif resp.startswith("VOTE_INTENTION_DETECTED") or resp.startswith("VOTE_DETECTED"):` → return `statement`.
    - Else → continue to fallback patterns.
  - This preserves existing tests that expect positives on `VOTE_DETECTED` or `VOTE_INTENTION_DETECTED`, while correctly respecting negatives (both the prompt‑documented `NO_VOTE_INTENTION` and the test’s `NO_VOTE_DETECTED`).

- Secondary hardening (optional, low risk):
  - Normalize model outputs by stripping punctuation and trailing explanations (e.g., `VOTE_DETECTED: clear intention`). Use `split(':', 1)[0]` before token checks.

---

**Failure 2: Quarantine Path Not Reached Due to Unhandled Timeout in Reasoning Step**

- Symptom (from failure log): Test patches `core.phase2_manager.Runner.run` to timeout; expecting `_get_participant_statement_enhanced()` to handle retries and quarantine. Instead, a `TimeoutError` is raised before quarantine logic executes.

- Test setup highlights (fixtures):
  - `QuarantineTestFixture.create_test_experiment_config()` sets `reasoning_enabled=True` for the first agent.
  - Test patches `Runner.run` to raise `asyncio.TimeoutError("Agent timeout")` globally for `core.phase2_manager` module.
  - Test also patches `_validate_statement` to `False` (forcing retries to exhaust), expecting neutral quarantine output.

- Code path:
  - File: `core/phase2_manager.py`
  - Function: `_get_participant_statement_enhanced()`
  - Relevant logic:
    - If `agent_config.reasoning_enabled`:
      - `reasoning_result = await Runner.run(participant.agent, reasoning_prompt, context=context)`
      - No timeout wrapper. No try/except around this call.
    - Then, in a try/except, it calls `_get_participant_statement_with_retry(...)` which does have timeout handling, validation, retries, and the quarantine fallback on `AgentCommunicationError`.

- Root cause (exact):
  - The internal reasoning call is made before entering the try/except that wraps statement retrieval. Since `Runner.run` is patched to raise `TimeoutError`, the exception propagates out of `_get_participant_statement_enhanced()` immediately, bypassing the retry/quarantine path entirely.
  - In short: missing timeout + exception handling for the reasoning prompt.

- Why this is robustly reproducible:
  - Any failure (timeout or exception) in reasoning with `reasoning_enabled=True` will abort before quarantine fallback.

- Minimal, safe fix (behavior‑preserving elsewhere):
  - Wrap the reasoning step with the same timeout and error handling pattern used for statements. On timeout or exception:
    - Log a warning.
    - Set `internal_reasoning = ""` (or a neutral placeholder) and continue to the statement acquisition step.
    - Do not raise; allow subsequent retry/quarantine logic to execute.
  - Concretely in `_get_participant_statement_enhanced()`:
    - Replace the direct `await Runner.run(...)` with:
      - `try: result = await asyncio.wait_for(Runner.run(...), timeout=self.settings.statement_timeout_seconds)`
      - `internal_reasoning = result.final_output if result else ""`
      - `except asyncio.TimeoutError: log + internal_reasoning = ""`
      - `except Exception as e: log + internal_reasoning = ""`
  - Optionally increment validation stats for reasoning timeouts (new counter) if you want observability; not strictly required to satisfy current tests.

---

**Related Warning (Not a Failure): Un‑awaited Coroutine**

- Log excerpt:
  - `RuntimeWarning: coroutine 'Runner.run' was never awaited` in `tests/integration/test_phase2_constraint_correction_scenarios.py`.
- Likely cause:
  - A `patch('asyncio.wait_for', ...)` or a `patch` that returns a non‑awaited `MagicMock` in a context where an async function is expected, causing an awaitable not to be awaited (or replaced by a non‑coroutine).
  - Alternatively, patching `Runner.run` with a non‑async mock in a code path that expects an awaitable.
- Recommendation:
  - When patching async functions, use `AsyncMock` (Python 3.8+) to preserve awaitability (the suite already does this in most places). Ensure any patched `wait_for` returns a proper awaitable, or avoid patching `asyncio.wait_for` directly—instead, simulate timeouts by patching `Runner.run` to raise `asyncio.TimeoutError` as done elsewhere.

---

**Summary of Root Causes & Fixes**

- Vote intention false positives:
  - Cause: substring match for positives (`"VOTE_DETECTED" in response`) also matches negative `NO_VOTE_DETECTED`.
  - Fix: Normalize response and use exact token checks. Give negatives precedence.

- Quarantine path unreachable due to reasoning timeout:
  - Cause: No timeout/exception handling on the internal reasoning prompt when `reasoning_enabled=True`.
  - Fix: Wrap reasoning `Runner.run` with `asyncio.wait_for` and catch `TimeoutError`/`Exception`, continuing with empty reasoning.

Both fixes are localized, low‑risk, and align with existing test expectations and code patterns used elsewhere in the codebase.

If you’d like, I can implement these two fixes now and run the phase 2 tests to validate the outcomes.

