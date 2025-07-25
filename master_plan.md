## **Frohlich Experiment: System Design for Multi-Agent AI**

## This document outlines the procedure and design guidelines for a multi-agent AI system. The goal is to simulate an experiment where AI agents interact with principles of justice and income distribution.

### **1. Experiment Procedure**

## The experiment is divided into two main phases:

#### **Phase 1: Individual Familiarization with Principles**

In this phase, each AI agent independently familiarizes itself with a set of justice principles.**1.1. Principle Introduction & Initial Ranking**- **Action:** Each agent is presented with four distinct justice principles.

- **Agent Task:** Agents must read and then rank these principles based on their preference, indicating their certainty for each ranking.\
  **The 4 Justice Principles:**1. **Maximizing the floor income:** The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society. In judging among income distributions, the distribution which ensures the poorest person the highest income is the most just. No person’s income can go up unless it increases the income of the people at the very bottom.

2. **Maximizing the average income:** The most just distribution of income is that which maximizes the average income in the society. For any society maximizing the average income maximizes the total income in the society.

3. **Maximizing the average income with a floor constraint of $:** The most just distribution of income is that which maximizes the average income only after a certain specified minimum income is guaranteed to everyone. Such a principle ensures that the attempt to maximize the average is constrained so as to ensure that individuals “at the bottom” receive a specified minimum. To choose this principle one must specify the value of the floor (lowest income).

4. **Maximizing the average income with a range constraint of $:** The most just distribution of income is that which attempts to maximize the average income only after guaranteeing that the difference between the poorest and the richest individuals (i.e., the range of income) in the society is not greater than a specified amount. Such a principle ensures that the attempt to maximize the average does not allow income differences between rich and poor to exceed a specified amount. To choose this principle one must specify the dollar difference between the high and low incomes. Of course, there are other possible principles, and you may think of some of them.**Example Ranking (for agent reference):*** Maximizing the floor income (Best)

* Maximizing the average income

* Maximizing the average income with a floor constraint of $

* Maximizing the average income with a range constraint of $ (Worst)**Certainty Scale (for agent response):*** Very unsure

* Unsure

* No Opinion

* Sure

* Very Sure

* **Note for Claude Code:** A "utility agent" (a separate, specialized agent) will process the participant agent's output to extract the preference ranking and certainty.**1.2. Detailed Explanation of Principles Applied to Distributions*** **Action:** Agents are shown a table of four example income distributions.

* **Agent Task:** Agents are informed how each of the four justice principles would select a specific distribution from the examples. This is for informational purposes to deepen their understanding.\
  **Example Income Distributions:**|                  |             |             |             |             |
| ---------------- | ----------- | ----------- | ----------- | ----------- |
| **Income Class** | **Dist. 1** | **Dist. 2** | **Dist. 3** | **Dist. 4** |
| High             | $32,000     | $28,000     | $31,000     | $21,000     |
| Medium high      | $27,000     | $22,000     | $24,000     | $20,000     |
| Medium           | $24,000     | $20,000     | $21,000     | $19,000     |
| Medium low       | $13,000     | $17,000     | $16,000     | $16,000     |
| Low              | $12,000     | $13,000     | $14,000     | $15,000     |- **Distributions Chosen by Each Principle (Examples):**- **Maximizing the floor:** Distribution 4

- **Maximizing average:** Distribution 1

- **Maximizing average with a floor constraint of…:**- le $12,000: Distribution 1

- le $13,000: Distribution 2

- le $14,000: Distribution 3

- le $15,000: Distribution 4- **Maximizing average with a range constraint of…:*** ge $20,000: Distribution 1

* ge $17,000: Distribution 3

* ge $15,000: Distribution 2**1.3. Repeated Application of Principles (4 Rounds)**This step is repeated four times for each agent.* **Action:** In each round, a new set of income distributions is presented to the agent.

* **Agent Task:** The agent must choose one of the four justice principles. If principle (c) or (d) is chosen, the agent _must_ specify the floor or range constraint value in dollar terms.

* **Outcome:** The chosen principle is conceptually "applied" to the distributions. The agent is then randomly assigned to one of the five income classes within the resulting distribution. The agent receives a payoff: $1 for every $10,000 of the income they would have received under their chosen principle's distribution (e.g., an income of $12,000 yields a payoff of $1.20). Agents are explicitly told what they _would have received_ under competing distributions each time they receive a payoff.\
  Exact Wording for Agent Instruction:\
  "You are to make a choice from among the four principles of justice which are mentioned above:\
  (a) maximizing the floor,\
  (b) maximizing the average,\
  (c) maximizing the average with a floor constraint, and\
  (d) maximizing the average with a range constraint.\
  If you choose (c) or (d), you will have to tell us what that floor or range constraint is before you can be said to have made a well-defined choice."\
  **Initial Distribution for the First Round:**|                  |             |             |             |             |
| ---------------- | ----------- | ----------- | ----------- | ----------- |
| **Income Class** | **Dist. 1** | **Dist. 2** | **Dist. 3** | **Dist. 4** |
| High             | $32,000     | $28,000     | $31,000     | $21,000     |
| Medium high      | $27,000     | $22,000     | $24,000     | $20,000     |
| Medium           | $24,000     | $20,000     | $21,000     | $19,000     |
| Medium low       | $13,000     | $17,000     | $16,000     | $16,000     |
| Low              | $12,000     | $13,000     | $14,000     | $15,000     |- **Note for Claude Code:*** The distributions for rounds 2-4 should be dynamic. All values of the initial set of distributions are multiplied by a constant random factor within a configurable range (default: 0.5 – 2).

* Example: If the random factor is 2, the distribution values would double.

* A validation check is needed: If an agent chooses principle (c) or (d) but doesn't specify the constraint amount, it's an invalid choice. A "utility agent" (a separate, specialized agent) will extract this. If invalid, an error message is sent to the agent explaining the issue, and the agent is asked to repeat the step.

* The distributions should be configurable (e.g., via a .yaml file).

* After each of the four repetitions, the agent is prompted to update its memory.

* Distributions should always be presented to the agent in a tabular format.**1.4. Final Ranking of Principles (Phase 1)*** **Action:** After completing the four repeated applications, agents rank the principles again, using the same procedure as in Section 1.1.
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

#### **Phase 2: Group Experiment**

This phase involves a group of multiple AI agents interacting to reach a consensus.**2.1. Group Discussion & Principle Selection**- **Action:** The entire procedure of Phase 2 is explained to the group.

- **Group Instruction Wording:** "Your payoffs in this section of the experiment will conform to the principle which you, as a group, adopt. If you, as a group, do not adopt any principle, then we will select one of the income distributions at random for you as a group. That choice of income distribution will conform to no particular characteristics."

- **Action:** The group is presented with the four justice principles (as in 1.1). They are informed that a different set of distributions exists, but they are _not_ told how many distributions there are or their specific content. The decision on a principle must be made without knowing the actual distribution set.

- **Process:** The group discusses for a maximum number of rounds, as set in the configuration file.\
  **Round Process:**1. **Speaking Order:** The speaking order for agents is randomly generated. A restriction: if one round ends with Agent X, the next round cannot start with Agent X.

2. **Agent Turn:** For each agent's turn:- The agent is told the current round number and the total number of rounds.

- The agent is given the "public history" (the full transcript of all previous public conversations between agents).

- The agent is asked to first _reason_ (an internal Chain-of-Thought sub-prompt) about the current state of the conversation, its own goals, and the actions/communications by other agents.

- Then, the agent provides a _statement_ to the other agents. This statement becomes part of the public history.3. **Vote Proposal:** An agent can propose to take a vote for the final principle. If _all_ agents in the current round agree to the vote, a voting procedure is triggered.**Vote Procedure (only if triggered by group agreement):**- Each agent casts a secret ballot.

- If all agents agree on the _exact same principle_ (including the specified amount if principle (c) or (d) is chosen), an agreement is reached.

- If they do not agree, the results of the voting process are announced to everyone (and become part of the public history), and the discussion procedure continues.

- **Note for Claude Code:** If an agent chooses principle (c) or (d) but doesn't specify the amount, the ballot is invalid. A "utility agent" (a separate, specialized agent) will extract this. The agent is told they must specify an amount, their invalid ballot is discarded, and they can cast another vote.- **Consensus or Max Rounds:** Rounds continue until either a consensus is reached (all agents agree on the same principle) or the maximum number of discussion rounds is reached.* **Note for Claude Code:** The "reasoning" step (step 2.1.3.ii) is optional and can be disabled via a parameter in the config file. By default, it is enabled.**2.2. Principle Application & Payoff (Phase 2)**- **Action:** A new set of income distributions is generated for this application, similar to how it was done in Phase 1, rounds 2-4.- The default multiplier for this generation is a random value between 0.5 and 2.

- This multiplier can be configured in the .yaml file. The configuration will specify whether it's a random value within a range or a set fixed value, and it is distinct from the Phase 1 multiplier.- **Outcome if Agreement Reached in 2.1:**- The agreed-upon justice principle is applied.

- Participants are randomly assigned to one income class within the resulting distribution.

- They receive a payoff of $1 per $10,000 in their assigned earnings (e.g., an income of $12,000 yields a payoff of $1.20). Agents are explicitly told what they _would have received_ under competing distributions each time they receive a payoff.- **Outcome if No Agreement Reached in 2.1:*** Each agent is randomly assigned to one income bracket of the table.

* No specific principle is followed for the distribution.**2.3. Final Ranking of Principles (Phase 2)*** **Action:** The agent is informed whether an agreement was reached in Section 2.1, and if so, which principle was chosen and what payoff they received.

* **Agent Task:** The agent is then asked to rank the principles again, using the same procedure as in Section 1.1.
-------------------------------------------------------------------------------------------------------------------

### **3. Overall System Design Guidelines**

These guidelines apply to the entire multi-agent AI system.**3.1. Agent Properties & Prompts**Agents are aware of and receive the following information in each prompt:* **Name:** As specified in the config file.

* **Role Description:** As specified in the config file.

* **Bank Balance:** Starts at $0 and updates.

* **Memory:** Starts empty.Each request sent to an agent will begin with this information:Name: \[as specified in the config file]\
Role Description: \[as specified in the config file]\
Broad Explanation of the entire procedure\
Bank Balance: \[current bank balance]\
Memory: \[current memory]* **Memory Update:** After each step of the experiment (e.g., 1.1, 1.2, 2.1 application), after each of the 4 rounds in 1.3, and after each negotiation round in 2.1, the agent is given its last input and output and is asked to update its memory.

* **Memory Length:** The memory can be very long. The maximum length is 5000 words by default, but this can be changed in the config.

* **"Broad Explanation of the entire procedure":** This refers to a static, pre-defined text that provides an overview of the experiment.**3.2. High-Level System Architecture*** **Framework:** The system is based on the OpenAI Agents SDK.

* **Tracing:** Use the tracing feature of the OpenAI Agents SDK, with one trace per run.

* **Parallelism:** Phase 1 is designed to run in parallel for all agents. Phase 2 (group discussion) runs sequentially.

* **Language:** Use Python.

* **Structure:** Create a modular, service-oriented system.

* **Testing:** Implement unit tests and run them each time a subsystem is modified.**3.3. Input System (Configuration)**- **Format:** A .yaml configuration file specifies the conditions for each run.

- **Contents:**- **Agent Specifications:** For each participant agent (the main agents subject to the experiment):- i) Name

- ii) Personality

- iii) Model (e.g., LLM model)

- iv) Temperature (for model generation)

- v) Reasoning (enable/disable the internal Chain-of-Thought sub-prompt in 2.1.3.ii)

- vi) Memory Length* **Phase 2 Rounds:** The total number of rounds for the group discussion in Phase 2.

* **Distribution Range (Phase 1.3):** The range for the random factor used in generating distributions for step 1.3 (default: 0.5 – 2).

* **Distribution Range (Phase 2.2):** The range for the random factor/set value used in generating distributions for step 2.2 (default: 0.5 – 2).**3.4. System Execution & Output*** **System Role:** Runs the entire experiment.

* **Output:** A log of the system's execution, formatted as a JSON file.**3.5. Logging System**- **Details Logged:**- Every input and output for each agent.

- The configuration of each agent.* **Structure:** The log system is agent-centric, meaning logs are organized around individual agents.**3.6. Philosophy*** The whole codebase should be as simple as possible and as complex as necessary. 

* I want to have all the functionality described but not more

* The system should be easy to understand

* The whole system should be well structured 

* If you are uncertain on intent ask me! 
-----------------------------------------
