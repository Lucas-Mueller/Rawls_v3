# Codex Prompt & Memory Update Deep Dive

- Focus: Prompt structure and memory updates in Phase 1 and Phase 2
- Key files: `utils/memory_manager.py`, `experiment_agents/participant_agent.py`, `core/phase1_manager.py`, `core/phase2_manager.py`, `utils/language_manager.py`, `translations/*.json`, `utils/agent_centric_logger.py`

## Executive Summary
- Current behavior repeats large amounts of prior content (full prompts, tables, experiment explanation) across turns and inside memory updates.
- This leads to token bloat, lower signal-to-noise, higher costs, and maintainability risks.
- Final, aligned direction: keep memory free‑flowing but concise and delta‑focused (no strict schema), avoid restating rules/transcripts/prompts, and unify lightweight round “delta” builders across phases.

## Decisions & Final Recommendations (Aligned)
- Working memory stays free‑form and narrative, but focused on new insights (delta‑only in spirit). Full prompts/tables/transcripts live in logs.
- Use soft guidance in the memory‑update prompt (short narrative, avoid restating rules/past conversation, focus on what changed and why). No enforced bullet/char caps.
- Show the full experiment explanation only on the first turn per phase (or gated by config).
- Replace ad hoc round content with standardized, lightweight “round delta” builders for Phase 1 and Phase 2; stop embedding full prompts and tables in memory.
- Add optional config for guidance style and summarization behavior; remove duplicate constructions and stray logic.

## Findings
- Duplicate prompt layering each turn
  - `ParticipantAgent._generate_dynamic_instructions()` renders `context_context_info_format` with the entire experiment explanation and full current memory on every run.
  - Immediately after, `MemoryManager.prompt_agent_for_memory_update()` shows the whole current memory again plus “Recent Activity”.
- Round content embeds full prompts/tables back into memory
  - Phase 1 `round_content` includes the full application prompt, complete distributions table, full response, plus a long counterfactual table.
  - Phase 2 `round_content` includes the full discussion prompt and statement; then the next turn reprints the updated memory again.
- Phase 2 constructs round content twice
  - `_get_participant_statement_with_retry()` returns `(statement, round_content)`, then `_get_participant_statement_enhanced()` rebuilds a second, slightly different `round_content` and discards the first.
- Heavy context header always included
  - `format_context_info` (LanguageManager) injects the entire “experiment explanation” into every turn (even mid-phase, later rounds).
- Weak memory schema
  - `prompts.memory_memory_update_prompt` encourages “whatever you think is important” without strict structure. Length is enforced only as a hard limit after generation.

## Why This Matters
- Token bloat: Slower runs, higher cost, more truncation risk.
- Noise: Replaying prompts and large tables makes it harder for the model to focus on the few new facts that matter.
- Drift risk: Long, unstructured memory encourages anchoring on stale details and accidental duplication.
- Maintenance: Multiple ad hoc builders, duplicated content, and inconsistent formats between phases.

## Recommendations
- Separate Archive vs Working Memory
  - Keep transcripts, tables, and full prompts in logs only (`AgentCentricLogger`).
  - Keep `context.memory` concise, cumulative, and focused on new insights; allow free‑flow narrative.
- Redesign memory update prompt (soft guidance)
  - Keep it free‑flowing but instructive: “Summarize  new, relevant insights from the recent activity to use in future interactions; avoid restating rules, prompts, or transcripts unless you think they are necessary. You will always have access to the transcritps and current rules.”
  - Encourage brevity and relevance without hard caps; rely on the overall `memory_character_limit` as the primary constraint.

- Remove repeated experiment explanation per turn
  - Only include the big explanation on first turn per phase (or behind a config flag `include_experiment_explanation_each_turn: false`).
- Normalize round delta construction and deduplicate
  - Add `utils/memory_content.py: build_phase1_delta(...)` and `build_phase2_delta(...)` returning compact deltas:
    - Phase 1: round, chosen principle+constraint, assigned class, payoff, 1–2 counterfactual highlights (not full table), short rationale if brief.
    - Phase 2: round, speaking order, stance, vote-intention (Y/N), favored principle, vote events, consensus/no-consensus + agreed principle if any.
  - Use a single delta in Phase 2 (remove the second construction in `_get_participant_statement_enhanced`).
- Stop echoing full prompts/tables into memory
  - Replace “Prompt: …” and large tables with short identifiers or a one-line note (e.g., “Round used dynamic distributions (x1.32)” or “Situation B (Original Values mode)”).
- Add knobs in config
  - `memory_guidance_style: "narrative"|"structured"` (default: narrative), `include_experiment_explanation_each_turn` (default: false), `phase2_include_internal_reasoning_in_memory` (default: false).
- Rolling summarization/compression
  - Before updating memory, if `len(memory) > 0.8 * limit`, request a short narrative summary of the storyline so far and prune older details.

- Remove legagacy code
  - Do not ensure backward compaitbility, scrap the old system
  
- Quick low-risk cleanups
  - Fix the duplicate `continue` and remove double round-content building in Phase 2.
  - Replace Phase 1’s memory injection of full distribution tables with a short delta as above.

## Concrete Examples
- Memory update guidance (template)
  - “Update your working memory with new, relevant insights from the recent activity. You are free to use your memory as you seem fit."


## Implementation Plan (Ordered)
1) Gate experiment explanation display
   - File: `experiment_agents/participant_agent.py`
   - Change: In `_generate_dynamic_instructions`, add logic/flag to include the experiment explanation only on first call per phase (or `config.include_experiment_explanation_each_turn == True`).

2) Introduce narrative, delta‑focused memory guidance
   - Files: `utils/memory_manager.py`, `translations/*`
   - Change: Update `prompts.memory_memory_update_prompt` to a soft‑guidance narrative style (concise paragraph, focus on new insights, avoid restating rules/transcripts/prompts). Keep hard constraint only at `memory_character_limit`.

3) Add standardized round delta builders
   - New file: `utils/memory_content.py`
   - Functions: `build_phase1_delta(...)`, `build_phase2_delta(...)` producing compact deltas (no prompt/table echoes).
   - Refactor: Use these builders in `core/phase1_manager.py` and `core/phase2_manager.py` instead of inline long-form round content.

4) Config knobs for control
   - File: `config/models.py`
   - Add fields (with defaults): `memory_guidance_style` (default: narrative), `include_experiment_explanation_each_turn` (default: false), `phase2_include_internal_reasoning_in_memory` (default: false).

5) Rolling compression
   - File: `utils/memory_manager.py`
   - Change: Before update, if `len(memory) > 0.8 * limit`, request a short narrative summary of history + prune older details.

6) Cleanups and correctness
   - File: `core/phase2_manager.py`
   - Remove duplicate round-content construction and stray `continue`.
   - Replace full-prompt echoes with delta text and/or identifiers.

## Next Steps I Can Implement (On Request)
- Draft and integrate the new narrative memory‑update prompt and gentle retries.
- Add `utils/memory_content.py` and refactor Phase 1/2 to use deltas.
- Add config flags and gating for explanation inclusion.
- Introduce narrative rolling summarization when approaching memory limits.
