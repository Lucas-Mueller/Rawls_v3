# Proposal: Making the Voting Mechanism More Explicit

## 1. Background

Analysis of `core/phase2_manager.py` reveals that the project has a robust, multi-stage voting architecture. The process correctly separates the "agreement to vote" from the final "secret ballot," requiring unanimous consent at both stages. 

The system is not failing because the process is weak, but because the initial trigger for the process is too subtle.

## 2. The Core Problem: A Bottleneck in Vote Initiation

The entire voting cascade is initiated by the `utility_agent.detect_vote_intention_simple(statement)` function. This function attempts to infer an agent's desire to vote from the natural language of their general discussion statement. 

This inference is the single point of failure. The experiment log shows agents verbally agreeing to vote (e.g., "I'm ready to vote"), but the `utility_agent` did not recognize this phrasing as a formal proposal. This creates a frustrating "say-do" gap for the agents, who lack the sophistication to produce the precise, yet undefined, phrasing the detection model is looking for.

## 3. Proposed Solution: An Explicit Keyword Trigger

Instead of relying on nuanced NLP to infer intent, we should switch to a simple, explicit keyword that the agents can easily use. This change will be isolated to the vote initiation step, leaving the sound confirmation and balloting process intact.

### Step 1: Modify the Detection Logic

In `core/phase2_manager.py`, within the `_run_group_discussion` loop, we will replace the call to the utility agent.

*   **Current Logic:** `vote_proposal_text = await self.utility_agent.detect_vote_intention_simple(statement)`
*   **New Logic:** Implement a simple, direct string search to find a keyword phrase. For example:
    ```python
    # (Inside the loop in _run_group_discussion)
    proposal_keyword = "i propose a vote on"
    statement_lower = statement.lower()
    if proposal_keyword in statement_lower:
        # Extract the principle name that follows the keyword
        principle_text = statement_lower.split(proposal_keyword, 1)[1].strip()
        
        # (Add logic to validate the extracted principle_text)
        
        # If valid, trigger the existing confirmation process
        unanimous_agreement = await self._check_unanimous_vote_agreement(...)
        # ... etc
    ```

### Step 2: Update Agent Prompts

To close the loop, we must explicitly tell the agents how to use this new mechanism. The main discussion prompt (defined in `translations/*_prompts.json` under the key `phase2_discussion_prompt`) must be updated to include a clear instruction.

*   **Suggested addition to the prompt:** "**To call a formal vote, you must state the exact phrase: `I propose a vote on [Principle Name]`**, where `[Principle Name]` is one of the official principles being discussed."

## 4. Advantages of this Approach

*   **Removes Ambiguity:** It replaces a complex, implicit inference task with a simple, explicit keyword trigger.
*   **Lowers Cognitive Load:** Agents are given a clear, direct instruction on how to perform the action, rather than having to guess the correct phrasing.
*   **Preserves Agent Initiative:** The agents are still fully in control of when to call a vote, satisfying the project's core requirements.
*   **Minimal Code Change:** This is a small and targeted fix that leverages the existing, robust voting framework. It only changes the initial trigger.
