codex Phase 2 Discussion History Formatting Investigation
=======================================================

## Overview
- Goal: explain why the Phase 2 discussion history looks bold when surfaced during reasoning and statement prompts but not elsewhere.
- Approach: trace discussion history through storage (`GroupDiscussionState`), prompt construction (DiscussionService + LanguageManager), and participant instruction wiring.
- Key finding: runtime strings contain no Markdown bold markers; the perceived bold styling originates from the CLI renderer interpreting header delimiters, and only reasoning/statement contexts render the history block.

## How Discussion History Is Stored
- `GroupDiscussionState.add_statement()` strips Markdown emphasis (`**`/`__`) before persisting: `models/experiment_types.py:167-209`.
- Additional direct assignments (e.g., voting summaries, truncation) keep plain text and never inject `**`.
- Verified via script that new statements with Markdown are stored without emphasis (see Reproduction section).

## How Reasoning & Statement Prompts Pull History
1. **Phase2Manager** sets the transient history snapshot before every public-turn call: `core/phase2_manager.py:320-336`.
2. **Participant instructions** read that snapshot only for Phase 2 discussion turns: `experiment_agents/participant_agent.py:274-338`.
3. **LanguageManager** formats the transcript block with defensive stripping: `utils/language_manager.py:681-705`.
4. **Internal reasoning (round 1)** reuses the same sanitized history: `core/services/discussion_service.py:129-163`.

These paths all reuse the shared `format_phase2_discussion_instructions()` output, which inserts the transcript inside `=== DISCUSSION HISTORY ===` delimiters but never adds Markdown bold.

## Evidence From Runtime Strings
We reproduced the exact instruction payload that the Runner emits:

````text
python - <<'PY'
from types import SimpleNamespace
from models import ParticipantContext, ExperimentPhase, ExperimentStage
from utils.language_manager import LanguageManager, SupportedLanguage
from experiment_agents.participant_agent import _generate_dynamic_instructions

lm = LanguageManager(); lm.set_language(SupportedLanguage.ENGLISH)
state = SimpleNamespace(
    phase2_rounds=3,
    agents=[SimpleNamespace(name=n) for n in ["Alice","Bob","Charlie"]],
    include_experiment_explanation_each_turn=True,
    _current_public_history="\nRound 1 / Speaker: Alice Statement: Hello team\nRound 1 / Speaker: Bob Statement: Let's choose floor\n",
)
ctx = ParticipantContext(
    name="Alice", role_description="Participant", bank_balance=10.0,
    memory="", round_number=1, phase=ExperimentPhase.PHASE_2,
    interaction_type="statement", internal_reasoning="",
    stage=ExperimentStage.DISCUSSION,
)
wrapper = SimpleNamespace(context=ctx)
agent_cfg = SimpleNamespace(name="Alice", personality="Thoughtful leader")
print(_generate_dynamic_instructions(wrapper, None, agent_cfg, state, lm))
PY
````

Output (abridged):

```
=== DISCUSSION HISTORY ===

Round 1 / Speaker: Alice Statement: Hello team
Round 1 / Speaker: Bob Statement: Let's choose floor

==========================
```

The transcript contains zero `**` markers; emphasis stripping works as designed. Memory sections that appear non-bold on the CLI also use the same `=== ... ===` framing, confirming the data itself is consistent.

## Why The UI Shows Bold
- The Codex CLI (via OpenAI Agents SDK) renders agent context with rich/Markdown highlighting.
- Lines wrapped in `===` are treated as section headers and displayed with stronger typography.
- Reasoning and statement prompts include the discussion transcript block, so the renderer applies the bold styling there.
- Memory update and other prompts omit the transcript entirely, explaining the visual asymmetry despite identical underlying formatting.

## Verification Checklist
- [x] Confirmed storage sanitization (`GroupDiscussionState._strip_markdown_emphasis`).
- [x] Confirmed defensive stripping on every read path (DiscussionService + LanguageManager).
- [x] Generated live instructions to inspect raw strings (see reproduction snippet).
- [x] Compared other prompt types—memory update format lacks the history block, so CLI never highlights it.

## Recommendations
1. **Keep current sanitization:** No code change required to prevent Markdown leaks; all pathways already strip emphasis.
2. **Optional display tweak:** If the bold styling is undesirable, adjust `context_discussion_history_section_format` (e.g., replace `===` delimiters with `---` or plain labels) to avoid the renderer’s auto-highlighting.
3. **Document renderer behavior:** Note in developer docs that Codex CLI stylizes certain delimiter patterns, to avoid future confusion during prompt reviews.

