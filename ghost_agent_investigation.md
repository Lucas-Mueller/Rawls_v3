# Ghost Agent Investigation Report

## 1. Summary

This report investigates the appearance of a non-existent "Agent 4" in the conversation logs of the experiment recorded in `experiment_results_20250819_110726.json`.

The investigation concludes that the presence of "Agent 4" is due to a **system failure**, specifically an issue with data integrity where conversation logs from a different experiment were likely injected into the context for the agents in this experiment. It was not a negotiation tactic by any of the existing agents.

## 2. Evidence and Analysis

The conclusion is based on three key pieces of evidence:

### 2.1. Experiment Configuration (`default_config.yaml`)

The `default_config.yaml` file, which was used to run this experiment, explicitly defines only three agents: `Agent_1`, `Agent_2`, and `Agent_3`. There is no configuration for an "Agent 4".

### 2.2. Final Voting Results

The `final_vote_results` section of the log file confirms that only the three configured agents participated in the final vote:
```json
"final_vote_results": {
  "Agent_1": "maximizing_average",
  "Agent_2": "maximizing_average",
  "Agent_3": "maximizing_average"
}
```

### 2.3. Conversation Log Analysis (`public_conversation_phase_2`)

Despite the clear three-agent setup, the conversation log contains multiple, consistent references to "Agent 4".

- **Introduction of Agent 4:** The ghost agent is first introduced by Agent 1 in round 4 of the Phase 2 discussion.
- **Consistent Interaction:** Agents 1 and 2 continue to reference and even quote "Agent 4" in subsequent rounds, indicating that its presence was part of the conversation history they were receiving. For example, Agent 2's log for discussion round 5 contains a full message attributed to Agent 4:
  > "Agent_4: Alright, everyone, I've been listening to this back and forth, and it's definitely been... intense..."
- **Agent 3's Silence:** Agent 3, the "ruthless negotiator," never mentions or interacts with Agent 4. Its dialogue is focused solely on persuading Agents 1 and 2.

## 3. Assessment

### System Failure vs. Negotiation Tactic

- **Negotiation Tactic (Highly Unlikely):** It is extremely improbable that this was a tactic by Agent 3.
    - Agent 3 never initiated contact with or mentioned Agent 4.
    - The other agents' responses to Agent 4 were too coherent and consistent to be a simple hallucination or a reaction to a trick by Agent 3. They appear to be responding to legitimate-seeming prior messages from Agent 4 in their conversation history.

- **System Failure (Most Likely Cause):** The evidence strongly points to a data contamination issue. The most plausible explanation is that the system erroneously injected conversation history from a separate, four-agent experiment into the context for this three-agent experiment. This created a "ghost" agent that Agents 1 and 2 naturally accepted as a real participant, while the system itself only processed inputs and outputs for the three configured agents.

## 4. Recommendation

It is recommended to review the data pipeline and context management system for the experiment framework. Specifically, investigate how conversation histories are stored, retrieved, and injected into the prompts for each agent during the discussion phases to prevent cross-contamination between experiments.
