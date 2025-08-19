# Gemini Report: Comparison of Implemented Procedure vs. `procedure_oj.md`

This document provides a detailed, step-by-step comparison between the experimental procedure outlined in `procedure_oj.md` and the current implementation in the Rawls codebase.

## High-Level Configuration

The analysis begins with the `config/default_config.yaml` file, which serves as the primary configuration for the experiment.

| Procedural Point (`procedure_oj.md`) | Implementation (`default_config.yaml`) | Analysis |
| :--- | :--- | :--- |
| Conducted in groups of five. | `agents:` list contains 5 agent configurations. | **Full Alignment.** The number of participants is correctly configured. |
| Explicit income class probabilities are explained. | `income_class_probabilities:` section defines the exact probabilities (high: 5%, medium-high: 10%, etc.). | **Full Alignment.** The implementation uses the precise probabilities specified in the procedure. |
| Use of a specific orientation table (A, B, C, D). | `original_values_mode: enabled: true` and `situation: "sample"`. | **Full Alignment.** The system is configured to use a predefined set of values for the initial explanation, which directly corresponds to the "Original Values Mode". |

---

## Phase 1: Individual Phase

This phase focuses on individual learning and interaction with the principles.

### 1. Brief Explanation & Initial Ranking

| Procedural Point | Implementation Analysis | Alignment Status |
| :--- | :--- | :--- |
| Participants receive a "brief explanation" of the four principles. | In `Phase1Manager`, `_step_1_1_initial_ranking` calls `_build_ranking_prompt`, which loads a template from the `LanguageManager`. This template contains the descriptions of the four principles. | **Full Alignment.** The agents are presented with the principles before their first task. |
| Participants provide an initial rank-ordering. | The `_step_1_1_initial_ranking` function prompts the agent for a ranking, which is then parsed by the `UtilityAgent`. | **Full Alignment.** The system correctly captures the initial ranking. |
| Participants report confidence on a discrete scale (e.g., *Very sure*). | The `PrincipleRanking` model in `models/response_types.py` includes a `certainty` field. The `UtilityAgent` is designed to parse this from the agent's response. | **Full Alignment.** The data model and parsing logic exist to capture the confidence level. |

### 2. Detailed Explanation & Post-Explanation Ranking

| Procedural Point | Implementation Analysis | Alignment Status |
| :--- | :--- | :--- |
| Participants are shown a specific payoff table (A, B, C, D). | `Phase1Manager`'s `_step_1_2_detailed_explanation` function checks if `original_values_mode` is enabled. If so, it loads the `"sample"` situation from `core/original_values_data.py` and formats it into a table for the agent. The data in `original_values_data.py` for `"sample"` **exactly matches** the table in `procedure_oj.md`. | **Full Alignment.** The implementation perfectly reproduces the specified orientation table. |
| Participants are told the explicit probabilities. | The `income_class_probabilities` are defined in the config and used by `DistributionGenerator.calculate_payoff`. The explanation prompt itself also details the principles. | **Full Alignment.** |
| An explanation of which distribution corresponds to each principle is given. | The `_build_detailed_explanation_prompt` in `phase1_manager.py` retrieves a detailed explanation from the language manager which contains this information. | **Full Alignment.** |
| Participants take a "short test" which they had to pass. | The codebase **does not** contain any logic for administering a test to the agents. | **Discrepancy.** This step is not implemented. |
| Participants rank the principles again after the test. | `Phase1Manager` implements `_step_1_2b_post_explanation_ranking` which prompts the agent for a second ranking immediately after the detailed explanation. | **Partial Alignment.** A second ranking is performed, but it's not preceded by a test. |

### 3. Payoff-Relevant Practice Rounds

| Procedural Point | Implementation Analysis | Alignment Status |
| :--- | :--- | :--- |
| Procedure is repeated four times. | The main loop in `_run_single_participant_phase1` of `Phase1Manager` iterates `for round_num in range(1, 5):`, correctly executing four rounds. | **Full Alignment.** |
| Participants choose one of the four principles. | In `_step_1_3_principle_application`, the agent is prompted to choose a principle, and the `UtilityAgent` parses this choice. | **Full Alignment.** |
| The corresponding distribution is implemented via a random draw. | `DistributionGenerator.apply_principle_to_distributions` selects the correct distribution. Then, `DistributionGenerator.calculate_payoff` performs a weighted random draw using the configured probabilities to assign an income class and calculate the payoff. | **Full Alignment.** |
| Participants are unaware of the precise probabilities for each class. | This is a subtle point. The procedure states they are *told* the probabilities in the explanation, but are "unaware" during the practice rounds. The implementation uses the probabilities for the draw, but the prompt for the practice rounds (`_build_application_prompt`) does not re-state them, focusing only on the choice. This matches the spirit of the procedure. | **Alignment.** |
| The draw is in the form of a "chit" showing realized payoff and counterfactuals. | In `_step_1_3_principle_application`, after calculating the payoff, the system calculates `alternative_earnings_same_class` by seeing what the agent *would have earned* under the other principles given the *same income class draw*. This is formatted into a "counterfactual table" and sent back to the agent. This is a direct implementation of the "chit". | **Full Alignment.** |
| Realized payoffs are converted at a 1:$10,000 scale and paid immediately. | `DistributionGenerator.calculate_payoff` calculates `payoff = income / 10000.0`. `update_participant_context` then adds this to the agent's `bank_balance`. | **Full Alignment.** |
| A third ranking with confidence concludes the phase. | `Phase1Manager` executes `_step_1_4_final_ranking` after the four rounds are complete, which prompts for a final ranking and certainty. | **Full Alignment.** |

---

## Phase 2: Group Phase

This phase focuses on group deliberation and consensus.

| Procedural Point | Implementation Analysis | Alignment Status |
| :--- | :--- | :--- |
| Five participants deliberate to reach unanimous agreement. | `Phase2Manager` orchestrates the discussion. The goal is consensus, checked by `_check_exact_consensus`, which requires all votes to be identical. | **Full Alignment.** |
| They may propose a new principle. | The current prompts and parsing logic are strictly tied to the four established principles and their constraints. There is no mechanism for proposing or parsing a novel principle. | **Discrepancy.** This is not implemented. |
| Payoff distributions may differ from examples. | `Phase2Manager` calls `DistributionGenerator.generate_dynamic_distribution` with `config.distribution_range_phase2`, creating entirely new distributions for the final payoff, not the static ones from Phase 1. | **Full Alignment.** |
| Participants do not know the concrete distributions. | The agents are not shown the new distribution table during Phase 2 deliberation. They must choose a principle abstractly. | **Full Alignment.** |
| Discussion must last at least five minutes. | This is a human-centric constraint. The implementation adapts this into a configurable number of rounds (`phase2_rounds: 4` in the config). The discussion proceeds in rounds until consensus is reached or the maximum number of rounds is exceeded. | **Adaptation.** The time-based constraint is adapted to a round-based one, which is appropriate for an AI agent simulation. |
| Culminates in a verbal consensus and a confirming secret-ballot vote. | The flow is slightly different but achieves the same goal. An agent can propose a vote. If all agents agree to vote (checked via `_check_unanimous_vote_agreement`), a "secret ballot" is conducted where each agent sends its vote directly to the `Phase2Manager`. The manager then checks for unanimity. | **Full Alignment.** The implementation correctly models a consensus-driven vote. |
| If unanimity fails, payoffs are assigned by a random draw from a randomly selected distribution. | In `_apply_group_principle_and_calculate_payoffs`, if `discussion_result.consensus_reached` is false, the code iterates through the participants and assigns them a payoff from a `random.choice` of the available distributions. | **Full Alignment.** |
| After payment, participants submit a final ranking with confidence. | `Phase2Manager` calls `_collect_final_rankings` after payoffs are determined. This prompts each agent for a final ranking and certainty. | **Full Alignment.** |

---

## Summary of Findings

The current codebase is a remarkably faithful implementation of the procedure described in `procedure_oj.md`. The alignment is very high on nearly all procedural points, including the specific data for the orientation phase, the structure of the individual practice rounds (especially the "chit" mechanism), and the rules of the group deliberation phase.

### Key Alignments:
*   **Configuration:** Group size, income probabilities, and the use of "Original Values Mode" are all correctly configured.
*   **Phase 1 Structure:** The sequence of initial ranking, detailed explanation, practice rounds, and final ranking is perfectly implemented.
*   **The "Chit":** The counterfactual earnings mechanism is fully implemented, showing agents what they would have earned under different principles for the same random event.
*   **Phase 2 Logic:** The core mechanics of deliberation, unknown future distributions, secret ballot voting, and handling of non-consensus outcomes are all present and correct.

### Key Discrepancies:
1.  **No "Short Test":** The procedure mentions a short, mandatory test after the detailed explanation in Phase 1. This is not implemented in the current codebase. The system moves directly from the explanation to a second ranking.
2.  **No "New Principle" Proposal:** The procedure notes that groups may propose a new principle in Phase 2. The implementation does not support this; agents are constrained to the four existing principles.

### Adaptations for MAAI (Multi-Agent AI):
*   The "five-minute discussion" rule is sensibly adapted to a `phase2_rounds` configuration parameter, which is more suitable for a turn-based agent simulation.

Overall, the implementation is a robust and accurate translation of the experimental design into a multi-agent framework, with only minor deviations from the documented procedure.
