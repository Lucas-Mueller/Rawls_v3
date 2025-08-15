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