# AI Prompts vs. Human Handbook: A Detailed Comparison

## Introduction

This document provides a detailed, side-by-side comparison of the instructions given to human participants in the "Subject Handbook" (formal "justice" version) and the prompts provided to the AI agents in `translations/english_prompts.json`. The goal is to analyze the differences in language, tone, and content, and to consider the potential implications of these differences for the experiment.

## Phase 1: Individual Familiarization

### 1.1. Initial Principle Ranking

**Subject Handbook (Page 5):**

> Rank order, according to your preferences, the following 4 [principles of distributive justice] by placing the letters (a), (b), (c), (d), signifying the [principles], in the blanks below. Indicate ties by placing the tied [principles] in the same space.
> 
> most preferred _______________ least preferred
> 
> a. maximize the floor income
> b. maximize the average income
> c. maximize the average income, subject to a floor constraint
> d. maximize the average income, subject to a range constraint

**AI Prompt (`phase1_initial_ranking_prompt`):**

> This is your first time ranking these four principles of justice:
> 
> {master_principle_descriptions}
> 
Please rank the principles from best (1) to worst (4) based on your initial understanding.
> 
> RESPONSE FORMAT:
> Please structure your response as follows:
> 1. [Your best choice]
> 2. [Your second choice]
> 3. [Your third choice]
> 4. [Your worst choice]
> 
> Overall certainty: [very unsure/unsure/no opinion/sure/very sure]
> 
> IMPORTANT: You must provide all 4 principles ranked as numbered lines, not just one choice.
> 
> Provide your ranking.

**Comparison:**

*   **Clarity and Explicitness:** The AI prompt is significantly more explicit. It provides the full descriptions of the principles (`{master_principle_descriptions}`) directly in the prompt, whereas the human participants would need to refer back to previous pages in the handbook. The AI prompt also provides a very specific response format.
*   **Certainty:** The AI is asked to state its certainty level, which is not explicitly requested from the humans in this initial ranking (though it is asked later).
*   **Tone:** The AI prompt is more conversational and instructional ("This is your first time...", "Please rank..."). The handbook is more formal and assumes the participant is actively reading and following instructions.

### 1.2. Detailed Explanation of Principles

**Subject Handbook (Pages 8-9):**

The handbook provides a detailed, narrative explanation of how the principles work, using a sample distribution. It explains how to calculate the average income and how the constraints work.

**AI Prompt (`phase1_detailed_principles_explanation`):**

> Here is how each justice principle would be applied to example income distributions:
> 
> Example Distributions:
> | Income Class | Dist. 1 | ...
> 
> How each principle would choose:
> - **{principle_name_floor}**: Would choose Distribution 4 (highest low income: $15,000)
> - ...
> 
> Study these examples to understand how each principle works in practice.

**Comparison:**

*   **Conciseness:** The AI prompt is a much more concise summary of the information. It presents the information in a clear, easy-to-scan format.
*   **Level of Detail:** The handbook provides a more in-depth explanation, including how the calculations are made. The AI prompt presents the *results* of the calculations but not the process.
*   **Implication:** The AI is expected to understand the principles from the summary, while the human is guided through the logic more thoroughly. This might lead to a more superficial understanding on the part of the AI, or it might be that the AI, as a language model, can infer the underlying logic from the examples.

### 1.3. Principle Application (Rounds)

**Subject Handbook (Page 12):**

> Situation A Would you now please consider the income distributions below and choose a [principle of justice] which you feel would yield the best choice of an income distribution for the society. On your tally sheet place a check mark in the column labeled Situation A opposite your choice of [principle.] Be sure to fill in the other information required if you choose to maximize with a constraint.

**AI Prompt (`phase1_application_round`):**

> CURRENT TASK: Principle Application (Round {round_number} of 4)
> 
> You will be shown 4 income distributions and must choose ONE of these justice principles to apply.
> If you choose a constraint principle..., you MUST specify the constraint amount in dollars.
> ...
> Choose from these four justice principles:
> {principle_list_simple}
> 
> {distributions_table}
> 
> RESPONSE FORMAT:
> Please structure your response as follows:
> State your choice clearly: "I choose [principle name]"
> ...

**Comparison:**

*   **Explicitness:** Again, the AI prompt is much more explicit, providing a clear response format and reminding the agent of the rules (e.g., specifying the constraint amount).
*   **Context:** The AI prompt provides more context, such as the current round number and a reminder of the task.
*   **Interaction:** The human interacts with a "tally sheet," while the AI interacts directly with the system through its formatted response. This makes the AI's interaction more direct and less prone to transcription errors.

## Phase 2: Group Discussion and Consensus

### 2.1. Group Discussion

**Subject Handbook (Page 16):**

> You begin by having a group discussion about which [principle] you should adopt. The group can terminate this discussion anytime after 5 minutes. ... You are not restricted, in any way, to the four [principles of justice] mentioned above. Thus, you can discuss (and later adopt) other [principles.]

**AI Prompt (`phase2_discussion_prompt`):**

> {group_participants}
> 
> GROUP DISCUSSION - Round {round_number} of {max_rounds}
> 
> Discussion History:
> {discussion_history}
> 
> What is your statement to the group for this round?

**Comparison:**

*   **Structure:** The human discussion is open and unstructured. The AI discussion is sequential and structured, with each agent making a statement in turn.
*   **Freedom:** Humans are explicitly told they can introduce new principles. The AI prompts do not mention this, and the system is likely not designed to handle novel principles.
*   **Context:** The AI prompt provides the discussion history directly, ensuring all agents have the same context. Humans must rely on their memory and notes.

### 2.2. Voting

**Subject Handbook (Page 18):**

> After your discussion you, as a group, are to vote to adopt a [principle of distributive justice]. Your voting will be according to the following procedure. The group will adopt a [principle] if, and only if, that [principle] is able to secure the unanimous support of the group against all other [principles]...

**AI Prompt (`two_stage_principle_selection` and `two_stage_amount_specification`):**

> SECRET BALLOT - STEP 1 OF 2
> 
> ...Select your preferred justice principle by number...
> 
> SECRET BALLOT - STEP 2 OF 2
> 
> You selected {principle_name}.
> 
> This principle requires you to specify a constraint amount in dollars...

**Comparison:**

*   **Process:** The human voting process is described as a series of two-way contests. The AI voting process is a two-stage secret ballot. While the goal is the same (unanimous consensus), the procedure is different.
*   **Secrecy:** The AI's ballot is explicitly secret. The handbook does not specify whether the human votes are secret, though the use of a "secret ballot" is mentioned for ending discussion.
*   **Guidance:** The AI prompts provide very clear, step-by-step guidance through the voting process.

## Conclusion

The prompts for the AI agents are consistently more explicit, structured, and conversational than the instructions for human participants. This is a necessary adaptation to the nature of AI agents, which require clear and unambiguous instructions to perform tasks correctly.

The key differences are:

*   **Explicitness:** AI prompts provide detailed instructions, response formats, and reminders.
*   **Conciseness:** Information is presented to the AIs in a more summarized and easy-to-scan format.
*   **Structure:** The AI's experience is more structured, especially in the discussion and voting phases.

The implications of these differences are significant. The structured nature of the AI experiment allows for more controlled and reproducible results. However, it may also limit the emergent and spontaneous behaviors that can be observed in human interactions. The differences in language and tone could also influence how the principles are perceived and acted upon.

This comparison highlights the thoughtful design of the AI experiment, which successfully adapts the core principles of the human experiment to the unique capabilities and limitations of AI agents.
