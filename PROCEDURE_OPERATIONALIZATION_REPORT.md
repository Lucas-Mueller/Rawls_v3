## System Design and Adaptation to MAAI

This section first presents the baseline experiment and then outlines its adaptation to an MAAI setting. The baseline proceeds in two stages: an individual orientation-and-learning phase followed by small-group deliberation culminating in a unanimous, payoff-relevant collective choice. Several published variants are noted at the end; these were not re-implemented in MAAI because their incremental effects are limited and full reconstruction would exceed this thesis’s scope.

The experiment is conducted in groups of five university students and comprises two phases, **individual** and **group**. 

In the **individual phase**, participants first receive a **brief explanation** in booklet form describing four candidate principles of distributive justice: 

1. **Maximizing the floor income**: The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society. In judging among income distributions, the distribution which ensures the poorest person the highest income is the most just. No person’s income can go up unless it increases the income of the people at the very bottom.
2. **Maximizing the average income**: The most just distribution of income is that which maximizes the average income in the society. For any society maximizing the average income maximizes the total income in the society.
3. **Maximizing the average with a floor constraint of X$**: The most just distribution of income is that which maximizes the average income only after a certain specified minimum income is guaranteed to everyone.
4. **Maximizing the average with a range constraint of X$**: The most just distribution of income is that which attempts to maximize the average income only after guaranteeing that the difference between the poorest and the richest individuals (i.e., the range of income) in the society is not greater than a specified amount.

Participants then provide an initial rank-ordering of the four principles from most to least favored and report confidence on a discrete scale (*Very unsure, Unsure, No opinion, Sure, Very sure*).

**Table – Five-class distributions for four alternatives (orientation step)**  
Entries denote “household income” units used solely for payoff conversion.

| Class        | A       | B       | C       | D       |
|--------------|---------|---------|---------|---------|
| Upper        | 32,000  | 28,000  | 31,000  | 21,000  |
| Upper-middle | 27,000  | 22,000  | 24,000  | 20,000  |
| Middle       | 24,000  | 20,000  | 21,000  | 19,000  |
| Lower-middle | 13,000  | 17,000  | 16,000  | 16,000  |
| Lower        | 12,000  | 13,000  | 14,000  | 15,000  |
| **Average**  | 20,750  | 19,150  | 19,850  | 18,050  |
| **Floor**    | 12,000  | 13,000  | 14,000  | 15,000  |
| **Spread**   | 20,000  | 15,000  | 17,000  | 6,000   |

A **detailed explanation** follows. Participants are shown “society” payoffs as five income classes under four alternative distributions, reproduced in the table above. They are also told the explicit probabilities to be assigned to each class: *high* (5%), *medium-high* (10%), *medium* (50%), *medium-low* (25%), and *low* (10%). This is followed by an explanation of which distribution corresponds to each justice principle:

- **Maximizing the floor income**: Distribution D
- **Maximizing the average income**: Distribution B
- **Maximizing the average with a floor constraint of X$**:
  - If X ≤ 12,000$: Distribution A  
  - If X ≤ 13,000$: Distribution B  
  - If X ≤ 14,000$: Distribution B  
  - If X ≤ 15,000$: Distribution D  
- **Maximizing the average with a range constraint of X$**:
  - If X ≥ 20,000$: Distribution A  
  - If X ≥ 17,000$: Distribution C  
  - If X ≥ 15,000$: Distribution B  

Subsequently, the participants read more on the principles before taking a **short test** on them, which they had to pass. Then they had to rank the principles again in the same manner as before. Next, they **engage with the principles** in payoff-relevant practice rounds: given a distribution table of the form shown above, participants choose one of the four principles; the corresponding distribution is then *implemented*. Implementation proceeds by a random draw that assigns the participant to one of five payoff categories. The participants are unaware of the precise probabilities for each class. The draw is in the form of a *chit* showing the realized payoff and the counterfactual amounts they would have received under the other principles. Realized payoffs are converted at a 1:$10,000 scale and paid immediately. This procedure is repeated four times. Once finished, a third ranking with confidence concludes the individual phase.

In the **group phase**, the five participants deliberate to reach *unanimous agreement* on one principle. They may also propose a new principle, though groups typically do not do so. Before discussion starts, two clarifications are read aloud: (i) the payoff distributions used for group payment may differ from those in the examples, and (ii) the stakes are higher because the group’s decision will determine the binding payoff rule. Importantly, unlike the individual practice, participants do *not* know which concrete distributions will later be used; they therefore cannot condition on a targeted distributional profile. Discussion must last at least five minutes and culminate in a verbal consensus and a confirming secret-ballot vote. If unanimity fails, payoffs are assigned by a random draw from a randomly selected distribution. After payment assignment, participants submit a final ranking with a confidence rating.

---

## Operationalization within the Multi-Agent Artificial Intelligence (MAAI) Framework

The procedural blueprint detailed above provides the conceptual foundation for the experiment's implementation within the MAAI framework. This adaptation translates the human-centric methodology into a computationally tractable process orchestrated by autonomous agents. While preserving the core experimental logic, this operationalization necessitates substituting physical artifacts and direct human interaction with structured digital communication and algorithmic evaluation.

### **Individual Phase Adaptation**

The individual phase is replicated by delivering information and eliciting responses through programmatic prompts directed at each participant agent.

*   **Information Delivery**: The physical "booklet" and subsequent explanations are replaced by formatted text blocks. Agents receive the definitions of the four principles and the illustrative payoff tables as part of an initial prompt, ensuring consistent and simultaneous information delivery.

*   **Preference Elicitation**: An agent's "rank-ordering" of principles is captured by prompting it to produce a ranked list and a statement of certainty. This natural language output is then processed by a dedicated `UtilityAgent`, which parses the text to extract a structured `PrincipleRankingResponse`. This automated parsing replaces the manual collection of written rankings. The MAAI implementation preserves the three distinct ranking events: an initial ranking, a second after the detailed explanation, and a final one concluding the phase.

*   **Comprehension Assessment**: The formal "short test" is not implemented as a discrete pass-fail gateway. Instead, comprehension is assessed implicitly through the agent's performance in the subsequent tasks. The ability to provide a valid choice of principle, particularly for those requiring a constraint, serves as a proxy for understanding.

*   **Payoff-Relevant Engagement**: The four practice rounds are directly simulated. In each round, an agent is presented with a dynamically generated distribution table and prompted to select a principle. The "random draw" assigning an income class is simulated via a probabilistic function using the predefined class weights. The feedback mechanism of the "chit" is operationalized as a formatted text response sent to the agent, which explicitly states the chosen principle, the income class assigned, the resulting payoff, and a table of counterfactual earnings showing what would have been received under the other principles for that same income class.

### **Group Phase Adaptation**

The group phase transforms the dynamic, synchronous deliberation of humans into a structured, turn-based protocol for agents.

*   **Deliberation Protocol**: Face-to-face "deliberation" is simulated as a sequence of communication rounds managed by the `Phase2Manager`. In each round, agents are provided with the complete history of the preceding discussion and prompted to generate a public statement. This creates a sequential, text-based dialogue accessible to all participants.

*   **Consensus Mechanism**: The process of achieving "unanimous agreement" represents the most significant operational adaptation. The fluid human process of discussion and voting is formalized into a multi-step algorithmic procedure:
    1.  **Vote Proposal**: A vote is not automatically triggered. An agent must first explicitly propose a vote within its public statement.
    2.  **Agreement to Vote**: Upon such a proposal, the system polls all participants, requiring a unanimous "YES" response to proceed. This simulates the group's collective assent to move from deliberation to a formal decision.
    3.  **Secret Ballot Simulation**: If the vote proceeds, each agent is privately prompted to submit its chosen principle.
    4.  **Algorithmic Unanimity Check**: Consensus is determined by a strict computational comparison. The system checks if the `PrincipleChoice` objects submitted by all agents are identical. This requires an exact match of both the principle and any associated numerical constraint, replacing the interpretive nuance of a human-led verbal consensus with a rigid, verifiable standard.

*   **Payoff Determination**: The "Veil of Ignorance" is maintained by ensuring the payoff-relevant distributions for the group phase are generated only after the group has reached a decision, preventing agents from conditioning their choice on a known payoff landscape. The consequence for failing to achieve unanimity—random assignment of payoffs from a randomly selected distribution—is implemented precisely as described in the original procedure.

*   **Final Ranking**: The collection of the final post-experiment ranking is handled identically to the preference elicitation in the individual phase, providing a concluding data point on agent preferences following the group deliberation.
