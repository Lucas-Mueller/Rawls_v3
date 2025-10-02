# Human vs. AI Experiment: A Comparative Review

## Introduction

This document provides a comprehensive review and comparison of the experimental process for human participants, as detailed in the "Subject Handbook," and the process for AI agents, as implemented in this repository. The goal is to analyze the similarities and differences in the experiment's flow, communication methods, and overall experience for both types of participants. This analysis focuses on the English version of the experiment and excludes the test/quiz aspects, as instructed.

## Experiment Flow Comparison

The fundamental structure of the experiment is preserved for both humans and AI agents, consisting of two main phases.

### Phase 1: Individual Familiarization

The goal of Phase 1 is to introduce the participants to the principles of justice and to gather their individual preferences.

**Human Participants:**

1.  **Introduction to Principles:** Humans read the "Subject Handbook," which explains the four principles of distributive justice.
2.  **Understanding Check:** They answer a series of questions to ensure they have understood the concepts. A moderator checks their answers.
3.  **Individual Choices:** Participants make choices in four hypothetical "Situations" (A, B, C, and D), each with different income distributions. These choices have real monetary consequences.
4.  **Ranking:** Participants rank the four principles before and after the application rounds.

**AI Agents:**

The AI experiment flow mirrors the human experiment closely, as implemented in `core/phase1_manager.py`.

1.  **Initial Ranking:** The AI agent is first asked to rank the four principles based on its initial understanding. This is handled by the `_step_1_1_initial_ranking` function, which uses the `phase1_initial_ranking_prompt` from `translations/english_prompts.json`.
2.  **Detailed Explanation:** The agent is then presented with a detailed explanation of the principles, including how they apply to a sample distribution. This is done in `_step_1_2_detailed_explanation`, using the `phase1_detailed_principles_explanation` prompt.
3.  **Post-Explanation Ranking:** After the explanation, the agent is asked to rank the principles again in `_step_1_2b_post_explanation_ranking`.
4.  **Repeated Application:** The AI agent goes through four rounds of "principle application," which correspond to the four "Situations" for humans. This is managed by the loop in `_run_single_participant_phase1` that calls `_step_1_3_principle_application`. In each round, the agent chooses a principle to apply to a set of income distributions, and its earnings are calculated.
5.  **Final Ranking:** Finally, the agent provides a final ranking of the principles in `_step_1_4_final_ranking`.

### Phase 2: Group Discussion and Consensus

Phase 2 aims to achieve a group consensus on a single principle of justice.

**Human Participants:**

1.  **Group Discussion:** Participants engage in an open discussion about the principles. They can introduce new principles as long as they don't use names.
2.  **Voting:** The group votes on the principles. A principle is adopted if it achieves unanimous support against all other principles in a series of two-way contests.
3.  **Payoffs:** The group's chosen principle determines the final payoffs for all participants. If no consensus is reached, a random distribution is chosen.

**AI Agents:**

The AI's Phase 2 is managed by `core/phase2_manager.py`.

1.  **Group Discussion:** The AI agents engage in a structured, sequential discussion. The `_run_group_discussion` function orchestrates this, with each agent making a statement in a predetermined speaking order. The `phase2_discussion_prompt` is used to elicit statements.
2.  **Voting:** The AI agents can initiate a vote. The voting process is handled by the `voting_service` and is designed to be a two-stage secret ballot, as seen in the `two_stage_principle_selection` and `two_stage_amount_specification` prompts.
3.  **Payoffs:** If consensus is reached, the chosen principle is applied to determine the final payoffs. This is handled by the `counterfactuals_service`. If no consensus is reached, a random distribution is chosen, mirroring the human experiment.

## Communication and Experience Comparison

This section analyzes the differences in how information is communicated and how the "veil of ignorance" is experienced.

### Communication Style

*   **Human Participants:** The primary communication tool is the "Subject Handbook," which is written in a formal, academic tone. The language is dense and requires careful reading. There is also direct interaction with a moderator.
*   **AI Agents:** Communication is handled through a series of prompts defined in `translations/english_prompts.json`. These prompts are more direct and conversational than the handbook. For example, the `phase1_initial_ranking_prompt` is a clear, direct instruction, whereas the handbook introduces the concepts more gradually. The AI's "personality," as defined in the `config/` files, also influences its communication style.

### The "Veil of Ignorance"

The "veil of ignorance" is a crucial element of the experiment, ensuring that participants make impartial choices.

*   **Human Participants:** The veil is created by the fact that participants do not know which income class they will be assigned to. This is explained in the handbook: "YOU WILL BE RANDOMLY PLACED IN AN INCOME CLASS IN THAT DISTRIBUTION, AND THAT DETERMINES THE MONEY YOU WILL GET."
*   **AI Agents:** The same principle is applied to the AI agents. The `distribution_generator.py`'s `calculate_payoff` function randomly assigns an income class to the agent. The prompts also reinforce this, for example, in the `phase1_application_round` prompt: "...you'll be assigned to an income class within that distribution based on realistic population probabilities...".

### Memory and Learning

A key difference is how humans and AIs handle memory and learning throughout the experiment.

*   **Human Participants:** Humans rely on their natural memory, notes, and the handbook to recall information. Their learning is a complex cognitive process.
*   **AI Agents:** The AI's memory is explicitly managed by the system. The `ParticipantAgent` has a `memory` attribute that is updated throughout the experiment. The `memory_manager.py` and the `update_memory` method in `participant_agent.py` are responsible for this. The prompts for memory updates, such as `memory_memory_update_prompt`, guide the agent on what to remember. This creates a more structured and explicit learning process.

## Key Differences and Implications

| Feature | Human Experiment | AI Experiment | Implications |
| :--- | :--- | :--- | :--- |
| **Communication** | Formal, dense handbook | Direct, conversational prompts | The difference in communication style could influence how the principles are understood and interpreted. The AI's "personality" adds another layer of variability. |
| **Memory** | Natural, implicit | Explicit, managed | The AI's explicit memory provides a more controlled and observable learning process. However, it may lack the nuances of human memory and learning. |
| **Discussion** | Open, unstructured | Sequential, structured | The AI's structured discussion may limit the spontaneity and emergent dynamics of a human conversation. |
| **Voting** | Unanimous, two-way contests | Two-stage secret ballot | The voting mechanisms are similar in their goal of achieving consensus, but the implementation details differ. The AI's voting process is more rigid and programmatic. |
| **"Personality"** | Natural human variation | Defined in configuration | The AI's personality is a configurable parameter, which allows for controlled experiments on the impact of different personality traits on decision-making. |

## Conclusion

The AI experiment successfully replicates the core structure and principles of the original human experiment. The two-phase design, the four principles of justice, and the "veil of ignorance" are all preserved.

The most significant differences lie in the communication style, the management of memory, and the structure of the group discussion. These differences are necessary adaptations to the nature of AI agents and provide opportunities for controlled experimentation.

By understanding these differences, researchers can better interpret the results of the AI experiments and draw more meaningful comparisons to the original human studies. The AI framework provides a powerful tool for exploring the complex dynamics of distributive justice in a controlled and reproducible environment.
