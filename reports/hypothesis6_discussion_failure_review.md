# Hypothesis 6 Discussion Failure Review

## Scope and Approach
- Reconstructed Phase 2 timelines for `hypothesis_6_spanish_condition_30` by parsing `phase_2.rounds` in `hypothesis_testing/hypothesis_6/results/spanish/hypothesis_6_spanish_condition_30_config_results.json`.
- Compared public statements and internal reasoning across all Spanish and English Hypothesis 6 runs to flag verbatim duplicates.
- Reloaded `hypothesis_6_spanish_condition_30_config.yaml` with `ExperimentConfiguration` and regenerated the round-six prompt headers via `LanguageManager` to verify what each agent saw before speaking.
- Spot-checked Phase 2 logging/prompt plumbing in `core/phase2_manager.py`, `experiment_agents/participant_agent.py`, and `utils/language_manager.py` for evidence of statement reuse or logging bugs.

## Findings
- **Condition 30 Round 6 duplication.** `Agent_3`'s public statement is exactly the same 1 598-character block as `Agent_0`'s Round 6 message while their internal reasoning differs by 3 894 characters. The duplicated text addresses `Agent_3` in the second person (excerpt below), so the speaker-of-record is effectively criticizing themselves.

  ```text
  Agent_2, Agent_1, Agent_4, me alegra mucho ver lo productiva que se ha vuelto esta conversación…
  Agent_3, tu propuesta de un rango del 25-30% fue un gran paso…
  ```

- **Condition 30 Round 8 identity drift.** `Agent_3` does not echo a prior question; instead they recycle another agent’s framing (“Agent_4, tu pregunta es directa… Agent_3, tu aportación…”). In the same round `Agent_0` and `Agent_2` deliver an identical six-paragraph admonition, again pointing at `Agent_3`. The earlier report’s quote “I have a question for you, Agent_3...” does not appear anywhere in the JSON log.
- **Early-round leakage of internal reasoning.** In Rounds 1–2 both `Agent_0` and `Agent_3` publish blocks that start with `--- SU RAZONAMIENTO INTERNO ---`, indicating that internal-only content is sometimes surfacing in public statements.
- **Systemic duplication across Hypothesis 6.** Automated scanning found 27 duplicate public messages across 17 Spanish runs and 11 duplicates across 5 English runs. The heaviest offenders include `hypothesis_6_spanish_condition_8_config_results.json` (four rounds duplicated) and `hypothesis_6_english_condition_19_config_results.json` (six rounds duplicated). Most collisions involve agents powered by the same `gemini-2.5-flash-lite` model, but there are also cross-model duplicates (e.g., `gemini-2.5-pro` with `gemini-2.5-flash-lite`) and a few three-way matches.
- **Prompt reconstruction shows agent identity available.** Rebuilding the round-six instructions yields headers beginning with `Nombre: Agent_0` versus `Nombre: Agent_3`, different bank balances, and distinct memory payloads. That weakens the hypothesis that logging overwrote data—the two agents received different contextual inputs, yet the recorded outputs match byte for byte.

## Root-Cause Assessment
- **Model-only failure unlikely.** If the vendor model were spontaneously cloning prior outputs, we would expect matching internal reasoning or wholesale fallback markers; neither occurs. Instead, reasoning remains agent-specific while only the outward message snaps to a previous template.
- **Logging pipeline looks intact.** `phase2_manager` captures each statement immediately after the model call and appends it to both the history and the per-agent log. There is no shared cache or mutation that would overwrite another agent’s entry after the fact.
- **Most plausible: prompt/system design defect.** The agents are given identical public instructions apart from name, and nothing explicitly reinforces first-person perspective or forbids echoing another speaker. Combined with identical temperatures and probable deterministic sampling, the setup appears to let similarly-configured models converge on the same “best” response—even when that response addresses the speaker in the second person. In short: the system permits persona drift and message reuse instead of catching or correcting it.
- **Residual uncertainty.** We lack raw API transcripts (temperature, top-p, seed, safety filters). If the platform injects hidden metadata (e.g., cached completions or safety rewrites), that could also explain perfect matches. Capturing request/response logs would confirm or rule this out.

## Recommendations
1. **Instrument the pipeline.** Enable transcript logging (with instructions and responses) for a reproduction run to confirm what the model emits before any post-processing.
2. **Harden persona prompts.** Append explicit guidance such as “You are Agent_3. Speak in first person and never address yourself as Agent_3” and enforce role reminders after each round.
3. **Introduce diversity checks.** After each response, compare against the last statement from other agents; if similarity exceeds a threshold (even simple equality), trigger a reprompt with additional guidance.
4. **Stagger randomness.** Vary temperature or sampling parameters per agent (or use distinct seeds) to reduce deterministic convergence among agents sharing the same base model.
5. **Audit for reasoning leakage.** The appearance of `--- SU RAZONAMIENTO INTERNO ---` in public channels suggests the reasoning/public split is brittle; review that prompt boundary while refactoring persona instructions.

## Outstanding Questions
- Do the backend logs show identical raw completions for the duplicated rounds, or is duplication introduced post-response?
- Are we forcing a fixed random seed or cached prompt signature that would cause identical sampling paths across agents sharing a model?
- Can we replicate the issue with strengthened persona instructions to verify the fix, or is additional guardrail logic required?
