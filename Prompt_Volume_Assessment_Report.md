**Title**
- Prompt Volume and Message Design Assessment for the Frohlich Experiment

**Summary**
- Scope: End-to-end review of how we construct and deliver messages to agents across both phases, including context building, prompts, and memory updates.
- Verdict: Phase 1 is mostly reasonable, but Phase 2 discussion messages are overly verbose and repetitive. Several prompts and injected contexts duplicate information each turn, driving up token usage and likely distracting models. Two‑stage voting prompts are concise and good.
- Impact: High token costs, higher latency, increased risk of instruction dilution, and potential behavioral artifacts from repeated “stakes” framing and long history dumps.

**Experiment Flow**
- Phase 1 (Individual Familiarization)
  - Initial ranking → detailed explanation → four application rounds → post‑explanation ranking → final ranking.
  - Files: `core/phase1_manager.py`, `translations/*_prompts.json`.
- Phase 2 (Group Discussion + Consensus)
  - Repeated rounds of public statements with optional internal reasoning; end‑of‑round vote prompting; formal two‑stage voting with deterministic validation.
  - Files: `core/phase2_manager.py`, `core/two_stage_voting_manager.py`, `translations/*_prompts.json`.

**Where Messages Come From**
- Context + Instructions
  - Built via `ParticipantAgent` dynamic instructions: `experiment_agents/participant_agent.py` → `_generate_dynamic_instructions()`.
  - Uses `utils/language_manager.py`:
    - `format_context_info()` → `prompts.context_context_info_format` (name, role/personality, bank balance, phase, round, memory, experiment_explanation, phase instructions, language instruction).
    - Explanation gating: `include_experiment_explanation_each_turn` (default False) or first turn per phase.
    - Memory rendering: `format_memory_section()` → `prompts.context_memory_section_format`.
- Phase 1 Prompts
  - Ranking and application prompts from `translations/*_prompts.json` (e.g., `phase1_initial_ranking_prompt_template`, `phase1_application_round`, tables from `DistributionGenerator.format_distributions_table`).
  - Memory updates after each step via `utils/memory_manager.py` with narrative/structured styles; includes previous memory + recent round content.
- Phase 2 Prompts
  - Discussion prompt: `LanguageManager.get("prompts.phase2_discussion_prompt")` in `_build_discussion_prompt()` each round.
    - Injects: long “IMPORTANT: stakes” blurb, group composition, discussion history, and full “The Four Justice Principles” explanation, every round.
  - Internal reasoning prompt: `prompts.phase2_internal_reasoning` (also includes the long stakes paragraph and full discussion history) when `reasoning_enabled`.
  - End‑of‑round vote prompting: succinct (`prompts.vote_initiation_prompt` / `...with_statement_prompt`).
  - Two‑stage voting: concise numeric prompts with retries and localized error messages (`core/two_stage_voting_manager.py`).
- Memory
  - Phase 1: After each sub‑step, we construct “round content” including the full prompt and response; memory updated via agent self‑generation.
  - Phase 2: Public statements and vote phases produce deltas and insertions; discussion history is tracked separately from per‑agent memory.
  - Compression: Triggered near 80% of memory limit; further compression to ~50% when necessary.

**Key Findings**
- Phase 2 discussion prompt is overly verbose and repeated each round
  - Always includes the long “IMPORTANT: The stakes are much higher…” paragraph in `prompts.phase2_discussion_prompt` and `prompts.phase2_internal_reasoning`.
  - Always re‑prints “The Four Justice Principles” with full descriptions each round.
  - Includes the full discussion history each round; only trimmed at 100k characters via `_manage_discussion_history_length()` which is far above typical model context budgets.
- Context block repeats stable fields every turn
  - `context_context_info_format` prints name, role/personality, bank balance, phase/round, language instruction, and formatted memory every call. Personality and bank balance rarely need to repeat.
- Memory is echoed verbatim in instructions and also fed into memory‑update prompts
  - We show memory in `context_context_info_format` and again embed previous memory into memory‑update prompts, increasing redundancy.
- Phase 1 explanations are dense but one‑off
  - The detailed explanation and distribution tables are expected; these are pedagogical and occur in limited steps.
- Voting flow is crisp
  - Two‑stage voting prompts are intentionally narrow (numbers only) with clear retries and localized errors—this is a good pattern.

**Why This Matters**
- Token bloat and latency: Re‑injecting long static text and the entire discussion history each round drives up costs and slows iterations.
- Instruction dilution and distraction: Repeating stakes and long descriptions can bury the actionable request, leading to more off‑target responses.
- Behavioral artifacts: Heavy “stakes” framing every turn may bias model behavior vs. one‑time framing.
- Context collisions: Mixing stable identity/personality with long memory and full history increases the chance of conflicting cues.

**Recommendations**
- Phase 2 prompt simplification and gating
  - Move the long “IMPORTANT: stakes” paragraph to only the first discussion round; add a one‑line reminder variant for subsequent rounds.
  - Show “The Four Justice Principles” only on round 1; in later rounds, include a short “principle names only” line or omit entirely.
  - Limit discussion history in prompts to a rolling window (e.g., last 6–10 turns) with a localized truncation marker; keep the 100k hard cap as a safety net only.
- Context block slimming
  - In `format_context_info()`, add fine‑grained switches to include memory/personality/bank balance conditionally:
    - Memory: short summary or last N memory bullets, not the full memory string.
    - Personality: first round per phase only.
    - Bank balance: show only when it changes or when a step requires it.
  - Keep `language_instruction` and the immediate task instructions prominent; push stable metadata after the task.
- Memory handling
  - Do not echo complete memory in the main instructions each turn. Prefer a concise “Memory highlights since last turn” assembled via `utils/memory_content` builders.
  - Keep the self‑update prompts as is, but avoid duplicating the same content in both the instruction header and the memory‑update prompt on the same turn.
  - Lower the discussion history cap used inside prompts (e.g., 8–12k chars), independent from the global 100k storage.
- Internal reasoning
  - If `reasoning_enabled`, use a lightweight reasoning prompt per round without re‑injecting the long stakes paragraph or the full history; link to “Recent discussion summary” instead.
- Configuration toggles
  - Expose new flags in `ExperimentConfiguration` and translation templates to control:
    - `phase2_include_stakes_each_round` (default false).
    - `phase2_include_principle_explanations_each_round` (default false).
    - `context_include_personality_each_turn` (default false).
    - `context_memory_mode` in {none, highlights, full} (default highlights).
    - `discussion_history_max_chars_in_prompt` (default ~10,000).

**Quick Wins (Low Lift, High Value)**
- Remove repeated “stakes” paragraph from Phase 2 prompts after round 1; swap a one‑line reminder.
- Replace the full “Four Justice Principles” block with names only after round 1.
- Reduce injected discussion history to last 6–10 turns (and ~10k chars) when building `phase2_discussion_prompt` and `phase2_internal_reasoning`.
- In `format_context_info()`, render a short memory summary (e.g., last 3 highlights) instead of the entire memory string.
- Keep two‑stage voting prompts unchanged—they are already minimal and effective.

**Appendix: Key Sources and Touchpoints**
- Context + Instructions
  - `experiment_agents/participant_agent.py` → `_generate_dynamic_instructions()` calls `language_manager.format_context_info()` and `format_memory_section()`.
  - `utils/language_manager.py` → explanation gating and context formatting; `prompts.context_context_info_format` in `translations/*_prompts.json`.
- Phase 1
  - `core/phase1_manager.py` builds ranking/explanation/application prompts and writes rich “round content” for memory.
- Phase 2
  - `core/phase2_manager.py`
    - Discussion prompt: `_build_discussion_prompt()` → `prompts.phase2_discussion_prompt` (injects stakes, principles, group composition, full history every round).
    - Internal reasoning: `_build_internal_reasoning_prompt()` → `prompts.phase2_internal_reasoning` (also repeats stakes, injects full history).
    - End‑of‑round vote prompting: concise numeric prompts (`prompts.vote_initiation_prompt`, `...with_statement_prompt`).
    - History cap: `_manage_discussion_history_length()` trims only at 100k chars—too high for prompt injection.
- Two‑Stage Voting
  - `core/two_stage_voting_manager.py` prompts are minimized (numeric responses, clear retries) and should be preserved.

**Voting System Communication Assessment**

**Current Voting System Flow Analysis**
After detailed examination of the experiment flow and prompts, the voting system explanation to agents has significant communication issues despite the technical implementation being sound:

**Problem 1: Fragmented Information Architecture**
- Initial voting mention: Brief 3-line description in `phase2_discussion_prompt` ("COMPLEX VOTING SYSTEM: Discuss... If voting initiated... Secret ballots... Consensus requires unanimous agreement")
- Vote initiation: Binary choice prompt with minimal context (`vote_initiation_prompt`: "Do you want to initiate a vote... Please respond with 1 or 0")
- Voting execution: Abrupt transition to numerical selection (`two_stage_principle_selection`: "Which of the four principles... Respond with ONLY the number")
- Result: Agents experience jarring context switches without understanding the complete process

**Problem 2: Poor Mental Model Building**
- Agents don't understand what "secret ballot" means in practice (individual numerical responses vs. group discussion)
- Consensus requirement unclear ("unanimous agreement" mentioned once but not reinforced)
- Process stages not sequentially explained (initiation → confirmation → ballot → consensus checking)
- Missing explanation of why numerical format is used instead of descriptive responses

**Problem 3: Decision Points Without Context**
- Vote initiation asks "Do you want to initiate voting now?" without explaining what happens next
- Agents must decide to start a process they don't fully understand
- No preparation for format changes (discussion prose → 1/0 binary → 1-4 numerical → dollar amounts)
- Timing element ("now") creates urgency without procedural clarity

**Problem 4: Cognitive Load and Context Switching**
- Agents process discussion history, then switch to binary decision-making, then to numerical selection
- Multiple decision formats require different reasoning modes
- Constraint amount requests appear without sufficient context about their role in consensus

**From Agents' Perspective: Key Issues**
1. **"What happens if I say yes to voting?"** - Unclear process flow
2. **"Why numbers instead of names?"** - Format rationale not explained  
3. **"What does 'secret' mean here?"** - Implementation unclear
4. **"How does consensus work?"** - Unanimous requirement not reinforced
5. **"What if we don't reach consensus?"** - Failure case unclear

**Recommended Improvements: Progressive Disclosure Approach**

**Phase 2 Initial Explanation (Round 1 Only)**
Replace the current brief voting mention with:
```
VOTING PROCESS OVERVIEW:
When any participant feels ready, they can initiate formal voting. Here's how it works:

1. INITIATION: Any participant can request to start voting
2. CONFIRMATION: All participants must agree to proceed (1=Yes, 0=No)  
3. SECRET BALLOT: Each participant privately selects their preferred principle using numbers (1-4)
4. CONSENSUS CHECK: If all participants select the same principle and constraint amounts, consensus is reached
5. RESULT: The agreed principle determines final earnings; if no consensus, discussion continues

This voting process uses numbers instead of text to ensure precise, unambiguous responses that can be fairly compared across participants.
```

**Enhanced Vote Initiation Prompt**
Replace current `vote_initiation_prompt` with:
```
VOTING DECISION POINT

The discussion has progressed and you may feel ready to move to formal voting.

If you choose to initiate voting:
- All participants will be asked to confirm agreement (1=Yes, 0=No)
- If everyone agrees, you'll proceed to secret numerical ballots (1-4)
- Consensus requires all participants to select the same principle
- If reached, that principle determines final earnings
- If not reached, discussion continues

Do you want to initiate this voting process now?
- 1 if you want to start the voting process
- 0 if you want to continue discussion

Your response (1 or 0):
```

**Improved Two-Stage Voting Instructions**
Replace current `two_stage_principle_selection` with:
```
SECRET BALLOT - STEP 1 OF 2

All participants agreed to vote. Your ballot is completely private - other participants will not see your individual choice.

Select your preferred justice principle by number:

1. Maximizing Floor Income
2. Maximizing Average Income  
3. Maximizing Average with Floor Constraint
4. Maximizing Average with Range Constraint

Important: Principles 3 and 4 require constraint amounts in the next step.

Your private ballot choice (1, 2, 3, or 4):
```

**Enhanced Amount Specification**
Replace current `two_stage_amount_specification` with:
```
SECRET BALLOT - STEP 2 OF 2

You selected {principle_name}.

This principle requires you to specify a constraint amount in dollars. This amount will be compared with other participants' amounts to determine if consensus is reached.

For consensus, all participants must choose:
- The same principle number AND
- The same constraint amount (if applicable)

Please specify your constraint amount as a whole dollar amount:
```

**Impact of These Changes**
- **Reduced Cognitive Load**: Clear process overview eliminates guesswork
- **Better Decision Making**: Agents understand consequences before choosing
- **Improved User Experience**: Smooth transitions between discussion and voting modes
- **Higher Success Rates**: Better understanding likely leads to more successful consensus
- **Maintained Brevity**: Despite more detail, prompts remain focused and actionable

**Implementation Notes**
- Use progressive disclosure (full explanation only in round 1, shorter reminders later)
- Maintain existing technical voting logic - only improve communication
- Consider A/B testing original vs. improved prompts to measure effectiveness
- Add configuration flags for prompt versions to allow experimentation

**Next Steps**
- If you want, I can implement the quick wins behind non‑breaking config flags, and add short translation strings for "round > 1" variants. Then we can run `python run_tests.py` and a short integration run to validate behavior and token savings.

