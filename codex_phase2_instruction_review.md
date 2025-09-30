# Phase 2 Instruction Review

## TODO Checklist
- [x] Inventory the prompts that shape Phase 2 behaviour (context scaffolding, discussion, internal reasoning, voting).
- [x] Evaluate clarity and guardrails from an agent perspective, including weaker LLMs.
- [x] Map observed failure modes to instruction gaps.
- [x] Propose actionable options (status quo vs. copy tweaks) with recommended wording.

## Instruction Inventory (key excerpts)
- `translations/english_prompts.json:64` – Global experiment explainer reused in Phase 2; reminds that there are four principles but does not enumerate them here.
- `utils/language_manager.py:446` + `translations/english_prompts.json:147` – Stage prompt for discussion: "Phase 2 – Group discussion. Contribute to the shared dialogue this round." No mention of the allowed principle set.
- `translations/english_prompts.json:188` – `phase2_internal_reasoning` block shown before private reasoning. Explicitly says the group must choose "one principle" but never repeats what the valid options are.
- `translations/english_prompts.json:204` – `phase2_discussion_prompt` used for the public statement. Asks for a statement with no guardrail about sticking to the canonical four principles.
- `translations/english_prompts.json:211` – Two-stage secret ballot instructions enumerate the four principles and enforce numeric answers; this is the only Phase 2 prompt that hard-limits choices.

## Agent Perspective Assessment
- **Context scaffold:** The experiment explainer is long and front-loaded. On first Phase 2 turn it competes with memory output and discussion history, making the subtle "four principles" reminder easy to miss—especially for smaller models that skim.
- **Internal reasoning prompt:** Reads like classic behavioural instructions and never restates the principle menu. A literal model can infer "principle" means "one of the known set," but weaker models may assume ideation is welcome, particularly after seeing "Your choice will be used to pick out those distribution schedules" without constraints.
- **Public discussion prompt:** Entirely open-ended, so brainstorming a brand-new principle still satisfies the literal request to contribute a statement.
- **Voting stage:** Provides a strong guardrail, but it arrives only after the discussion stage. By then the conversation may already be off-track, and low-ability models may dig in when their invented principle cannot be voted on.

## Failure Mode Analysis
- The observed run (with "less smart" models) shows the agent fabricating a new principle in Phase 2. Given the prompts above, the model never encounters an explicit "Do not invent new principles" instruction until voting. From the agent's vantage point, proposing a novel compromise seems aligned with "higher stakes" and "group discussion" messaging. The lack of immediate correction signal means the behaviour persists across rounds.

## Ambiguity Scan (What Might Encourage Novel Principles)
- `translations/english_prompts.json:78` – The phrase "you, as a group, are to choose one principle for yourselves" centres autonomy and can be read as permission to craft a bespoke principle rather than reuse a known one.
- `translations/english_prompts.json:78` – "Your choice of principle will be used to pick out those distribution schedules which conform to your principle" reinforces the idea that the principle originates with the group; weaker models may interpret this as "define whatever rule you want."
- `translations/english_prompts.json:78` – The follow-up example references picking the average-income principle but never restates that there are exactly four options, so the preceding general language dominates.
- `translations/english_prompts.json:95` – The memory update prompt replays the same paragraph every Phase 2 round, repeatedly priming agents with the "choose one principle for yourselves" framing, compounding the autonomy signal.
- `translations/english_prompts.json:95` – "Focus on information that might influence your choices about justice principles" lacks any reminder about the fixed menu, nudging models toward reinterpretation if they believe new constraints or principles are allowed.

## Options & Recommendations
1. **Status quo (accept failure):** Keeps prompts cleaner but relies on models inferring implicit constraints. Works for capable models yet fails open when comprehension is limited. Suitable only if you are comfortable discarding those runs.
2. **Targeted copy tweak (recommended):** Add a single sentence in both `phase2_internal_reasoning` and `phase2_discussion_prompt` clarifying that only the four Phase 1 principles are admissible. Example injection:
   - Internal reasoning addition: "Important: the group must adopt exactly one of the four principles you studied in Phase 1—no new principles can be created." 
   - Public discussion addition: "Focus on reaching consensus on one of the four Phase 1 principles (max floor income, max average income, max average with floor constraint, max average with range constraint)."
   These edits stay subtle, reinforce existing knowledge, and do not lengthen the prompts substantially.
3. **Stronger guardrails (optional escalation):** Expand the discussion-stage template (`context_stage_prompts.discussion`) to mention the valid principle set, or append a brief bulleted reminder after the discussion history. This ensures the restriction survives any alternate prompt flow (short forms, retries) but adds repetition.

## Suggested Next Steps
- Decide whether to pursue Option 2 immediately; it offers the best balance between clarity and brevity.
- If adopted, update the translation strings above and run `python run_tests.py` to ensure no formatting regressions. Consider adding a low-temperature regression test emulating a weaker model to verify compliance.
- Should failures persist, revisit Option 3 and/or instrument logging to flag when agents mention unrecognized principles so the run can be auto-aborted.
