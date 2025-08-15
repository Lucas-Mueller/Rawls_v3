
# Procedural Review of the MAAI Framework Implementation

## Introduction

This document provides a procedural review of the Multi-Agent Artificial Intelligence (MAAI) framework, comparing its operational sequence to the experimental design outlined in the foundational `procedure_oj.md` document. The analysis confirms a high degree of fidelity between the specified procedure and its implementation, while also noting minor deviations and necessary adaptations for the agent-based environment.

## Phase 1: Individual Orientation and Learning

The individual phase is designed to systematically introduce participants to the core concepts of the experiment. The MAAI implementation adheres closely to this design.

The phase commences with a **brief explanation** of the four principles of distributive justice. The system presents this information to each agent, after which the agents provide an **initial rank-ordering** of the principles, including a self-reported confidence level. This step is fully consistent with the specified procedure.

Following the initial ranking, a **detailed explanation** is provided. The MAAI framework presents agents with the exact five-class income distribution table specified in the procedural documentation. The system also informs the agents of the explicit probabilities associated with each income class (e.g., *high*: 5%, *medium*: 50%). This aligns perfectly with the experimental design.

A minor deviation occurs at the next step. The original procedure calls for a **short test** to ensure comprehension, which participants must pass before proceeding. The current MAAI implementation omits this test. Instead, it proceeds directly to a **second rank-ordering** of the principles. While the ranking itself is part of the original procedure, its position is immediately after the explanation, not after a test.

The subsequent stage involves four **payoff-relevant practice rounds**. The implementation of this stage is robust and faithful to the design. In each of the four rounds, agents are presented with a set of income distributions and choose a governing principle. A random draw, weighted by the established probabilities, assigns the agent to an income class, and a payoff is calculated and disbursed.

A critical component of this stage is the "chit," which informs the participant of their realized payoff and the counterfactual payoffs they would have received under the other principles for that same random draw. The MAAI framework successfully implements this mechanism by calculating and presenting each agent with its outcome and the corresponding alternative outcomes, thereby preserving a key learning element of the original design.

The individual phase concludes with a **third and final ranking** of the principles, which is consistent with the procedural outline.

## Phase 2: Group Deliberation

The group phase requires participants to deliberate and reach a unanimous decision. The MAAI framework adapts the core tenets of this phase to the agent environment.

The five agents engage in a multi-round discussion with the goal of reaching **unanimous agreement** on a single principle. A notable adaptation is made regarding the discussion's duration. The procedural requirement of a minimum five-minute discussion is translated into a maximum number of discussion rounds, a necessary adjustment for a turn-based simulation.

The procedure specifies that the payoff distributions used in this phase may differ from the examples and are unknown to the participants beforehand. The implementation honors this by generating new, random distributions for the group phase, forcing agents to reason about the principles in the abstract rather than targeting a specific known outcome.

Consensus is achieved via a **confirming secret-ballot vote**. The system initiates a vote if proposed and unanimously agreed upon by the agents. If all agents select the identical principle (including any specified constraints), consensus is reached. If unanimity is not achieved by the final round, payoffs are assigned based on a random draw from a randomly selected distribution, which is fully aligned with the procedure for handling failed consensus.

The procedure notes that groups may propose a new, unenumerated principle. The current implementation does not provide a modality for this, constraining the agents to the four established principles.

Following the assignment of payoffs, participants submit a **final ranking** of the principles with a confidence rating, bringing the experiment to a close in accordance with the procedural design.

## Conclusion

The MAAI framework is a faithful and well-constructed implementation of the experimental procedure. The core mechanics of both the individual and group phases are realized with high fidelity. The noted deviations—the omission of the comprehension test and the inability for agents to propose novel principles—are minor in the context of the overall experimental flow. The adaptation of time-based constraints to round-based mechanics is an appropriate and necessary modification for the automated environment.
