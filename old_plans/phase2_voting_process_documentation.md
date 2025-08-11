# Phase 2 Voting Process Documentation

**Date**: August 10, 2025  
**System**: Frohlich Experiment - Multi-Agent AI Justice Principles Study  
**Phase**: Phase 2 Group Discussion and Consensus Building

## Overview

Phase 2 implements a comprehensive multi-step voting process where participant agents engage in group discussion, propose votes, achieve unanimous agreement, conduct secret ballot voting, and reach consensus on justice principles. This document outlines every step, prompt, and mechanism involved.

## Process Flow

```
1. Initialize Phase 2 Contexts (carry over Phase 1 memory)
2. GROUP DISCUSSION ROUNDS (up to config.phase2_rounds)
   ├── Generate random speaking order
   ├── For each participant in speaking order:
   │   ├── Optional: Internal Reasoning (if reasoning_enabled)
   │   ├── Public Discussion Statement
   │   ├── Vote Detection Check
   │   └── If vote detected → Unanimous Agreement Check
   │       └── If unanimous → SECRET BALLOT VOTING
3. If consensus reached → Apply principle & calculate payoffs
4. If no consensus → Random payoff assignment
5. Collect final principle rankings from all participants
```

---

## Step-by-Step Process with All Prompts

### 1. Phase 2 Context Initialization

**Purpose**: Transfer continuous memory from Phase 1 to Phase 2  
**Implementation**: `_initialize_phase2_contexts()`

**Context Transfer**:
- Participant names, personalities, and configurations
- **Bank balance**: Total earnings from Phase 1
- **Memory**: Complete Phase 1 memory state (continuous memory)
- **Phase**: Set to `PHASE_2`
- **Round number**: Reset to 0

---

### 2. Group Discussion Rounds

**Loop**: Up to `config.phase2_rounds` (default: 20)  
**Speaking Order**: Randomized each round, avoiding consecutive same starters

#### 2A. Internal Reasoning (Optional)

**Trigger**: If `agent_config.reasoning_enabled = true`  
**Purpose**: Private agent reasoning before public statement  
**Implementation**: `_build_internal_reasoning_prompt()`

**PROMPT TO AGENT**:
```
GROUP DISCUSSION - Round {round_num} (Internal Reasoning)

Discussion History:
{discussion_state.public_history or "No previous discussion."}

Before making your public statement, consider internally:
- What is your current position on which justice principle the group should adopt?
- How has the discussion so far influenced your thinking?
- What arguments do you want to make in your public statement?
- Are you ready to call for a vote, or do you need more discussion?

Provide your internal reasoning (this will not be shared with other participants).
```

**Agent Response**: Internal reasoning text (not shared with other participants)

#### 2B. Public Discussion Statement

**Purpose**: Agent makes public statement to group  
**Implementation**: `_build_discussion_prompt()`

**PROMPT TO AGENT**:
```
GROUP DISCUSSION - Round {round_num}

Discussion History:
{discussion_state.public_history or "No previous discussion."}

Your task is to work with other participants to reach consensus on which justice principle 
the group should adopt. The group's chosen principle will determine everyone's final earnings.

Guidelines:
- You may propose a vote when you think the group is ready
- All participants must agree to vote before voting begins
- Consensus requires everyone to choose the EXACT same principle (including constraint amounts)

If no consensus is reached, final earnings will be randomly determined.

What is your statement to the group for this round?
```

**Agent Response**: Public discussion statement (shared with all participants)

**Alternative Prompt** (from `translations/english_prompts.json`):
```
CURRENT TASK: Group Discussion (Round {round_number})
You are now in the group discussion phase. Work with other participants to reach consensus on which justice principle the group should adopt.

DISCUSSION RULES:
- Take turns speaking in the assigned order
- Listen to others' perspectives and reasoning  
- Share your own views based on your Phase 1 experiences
- You may propose a vote when you think the group is ready
- All participants must agree to vote before voting begins
- Consensus requires everyone to choose the EXACT same principle (including constraint amounts)

RESPONSE FORMAT:
Structure your discussion statement clearly:
1. If ready to vote, clearly state: "I propose we vote on [specific principle with constraint if applicable]"
2. End with your current preferred principle

The group's chosen principle will determine everyone's final earnings. 
If no consensus is reached, final earnings will be randomly determined.
```

#### 2C. Vote Detection

**Purpose**: Detect if agent proposed a vote in their statement  
**Implementation**: `utility_agent.extract_vote_from_statement()`

**PROMPT TO UTILITY AGENT**:
```
Analyze this group discussion statement to determine if the participant is proposing a vote:

Statement: "{statement}"

Look for indicators that they want to:
- Start a vote/voting process 
- Move to consensus/decision
- Finalize the group decision
- Call for a vote on a principle

Phrases that indicate voting intent:
- "I propose we vote"
- "Let's vote on"
- "Ready to vote"
- "Call for a vote"
- "Should we vote"
- "Time to vote"
- "Proceed with a vote"
- "propose that we vote"
- "moving forward with a vote"

If the participant IS proposing a vote, respond with:
VOTE_PROPOSAL: [brief description of what they want to vote on]

If the participant is NOT proposing a vote, respond with:
NO_VOTE

Be generous in detection - if there's reasonable indication they want to vote, detect it.
```

**Utility Agent Response**: Either `VOTE_PROPOSAL: [description]` or `NO_VOTE`

**System Action**: 
- If `VOTE_PROPOSAL` detected → Proceed to Unanimous Agreement Check
- If `NO_VOTE` → Continue to next participant in speaking order

---

### 3. Unanimous Agreement Check

**Trigger**: Vote proposal detected  
**Purpose**: Ensure all participants agree to proceed with voting  
**Implementation**: `_check_unanimous_vote_agreement()`

**PROMPT TO ALL AGENTS** (parallel async execution):
```
A vote has been proposed. Do you agree to conduct a vote now?

Respond with either "YES" or "NO".
If you think more discussion is needed, respond "NO".
If you think the group is ready to vote, respond "YES".
```

**Agent Responses**: Each agent responds with "YES" or "NO"

**System Processing**:
- Extract all responses
- Check if ALL responses contain "YES" (case-insensitive)
- Log detailed agreement analysis:
  ```
  === UNANIMOUS AGREEMENT DEBUG ===
  Alice response: 'YES. Based on our discussion...' -> Contains YES: True
  Bob response: 'NO. I believe more discussion...' -> Contains YES: False
  Donald response: 'YES. I think we should vote...' -> Contains YES: True
  All agreements: [True, False, True]
  Unanimous result: False
  ```

**Outcomes**:
- **If unanimous YES**: Proceed to Secret Ballot Voting
- **If not unanimous**: Continue discussion rounds

---

### 4. Secret Ballot Voting

**Trigger**: Unanimous agreement achieved  
**Purpose**: Conduct individual secret votes on justice principles  
**Implementation**: `_conduct_group_vote()`

#### 4A. Individual Vote Collection

**PROMPT TO EACH AGENT** (parallel async execution):
```
SECRET BALLOT VOTE

Choose ONE of the four justice principles for the group to adopt:
(a) maximizing the floor
(b) maximizing the average  
(c) maximizing the average with a floor constraint
(d) maximizing the average with a range constraint

**IMPORTANT**: If you choose (c) or (d), you MUST specify the exact constraint amount in dollars.

This is your final vote. The group needs unanimous agreement (everyone choosing the exact same principle with the exact same constraint amount) to reach consensus.

What is your vote?
```

**Agent Response**: Text description of their vote choice

#### 4B. Vote Parsing and Validation

**Implementation**: `utility_agent.parse_principle_choice_enhanced()`

**PROMPT TO UTILITY AGENT**:
```
Parse the following participant response to extract their justice principle choice:

Response: "{response}"

Extract:
- Which principle they chose
- Constraint amount (if applicable)
- Their certainty level
- Their reasoning

Return the parsed data as a dictionary with keys: principle, constraint_amount, certainty, reasoning
```

**Validation Check**: `vote_choice.is_valid_constraint()`
- If constraint principle (c or d) chosen but no amount specified → Re-prompt

#### 4C. Constraint Re-prompting (if needed)

**Trigger**: Invalid constraint specification  
**Implementation**: `_re_prompt_for_valid_vote()`

**PROMPT TO UTILITY AGENT** (generates re-prompt):
```
{participant_name}, you chose the "{principle_name}" principle, but you did not specify the {constraint_type} constraint amount.

Please specify the dollar amount for your {constraint_type} constraint.

For example:
- Floor constraint: "I choose maximizing average with a floor constraint of $15,000"
- Range constraint: "I choose maximizing average with a range constraint of $20,000"
```

**PROMPT TO PARTICIPANT AGENT**: Re-prompt text from utility agent

**Agent Response**: Corrected vote with constraint amount

#### 4D. Consensus Check

**Purpose**: Check if all votes are exactly identical  
**Implementation**: `_check_exact_consensus()`

**Logic**:
- Compare first vote against all other votes
- Must match on BOTH principle AND constraint amount
- Return consensus principle if all match, None otherwise

**Vote Counting**: `_count_votes()`
- Creates dictionary of vote counts
- Key format: `principle_value` or `principle_value_$amount`
- Example: `{"maximizing_average_floor_constraint_$10000": 3}`

---

### 5. Vote Result Processing

**Implementation**: Returns `VoteResult` object with:
- `votes`: List of all individual votes
- `consensus_reached`: Boolean (true if all votes identical)
- `agreed_principle`: The agreed principle (if consensus)
- `vote_counts`: Vote distribution dictionary

**System Actions**:
- **If consensus reached**: 
  - Update all participants' memory with vote outcome
  - Return successful `GroupDiscussionResult`
  - Proceed to payoff calculation
- **If no consensus**: Continue discussion rounds

---

### 6. Memory Updates

**After each statement**: `MemoryManager.prompt_agent_for_memory_update()`

**PROMPT TO AGENT**:
```
Review what just happened and update your memory with whatever you think will be important for future decisions in this experiment. Focus on information that might influence your choices about justice principles or help you in group discussions.

Current Memory:
{current_memory}

Recent Activity:
{round_content}
```

**After vote**: All participants' memory updated with vote outcome

---

### 7. Payoff Calculation

**Implementation**: `_apply_group_principle_and_calculate_payoffs()`

**If Consensus Reached**:
- Generate new income distribution set for Phase 2
- Apply agreed principle to select optimal distribution
- Assign each participant to income class
- Calculate earnings: `$1 per $10,000 of income`

**If No Consensus**:
- Random assignment from random distributions
- Each participant gets random income class from random distribution

---

### 8. Final Principle Rankings

**Purpose**: Collect post-experiment principle rankings  
**Implementation**: `_collect_final_rankings()`

**PROMPT TO EACH AGENT**:
```
After participating in both Phase 1 (individual experience) and Phase 2 (group discussion), 
please provide your final ranking of the four justice principles from best (1) to worst (4).

Reflect on:
- Your Phase 1 experiences with applying the principles
- The group discussion and different perspectives you heard
- The final outcome and your earnings
- How your understanding of the principles has evolved

Provide your final ranking with an overall certainty level for the entire ranking and explain how the complete experiment 
influenced your final preferences.
```

**Parsing**: `utility_agent.parse_principle_ranking_enhanced()`

---

## Key Features and Mechanisms

### 1. Continuous Memory System
- Agents maintain persistent memory across all phases
- Memory updates after each significant event
- Character limit enforced (default: 50,000)
- Agent-managed memory structure

### 2. Tracing and Logging
- OpenAI Agents SDK tracing enabled
- Comprehensive debug logging for vote detection
- Detailed unanimous agreement analysis
- Agent-centric logging system

### 3. Error Handling and Validation
- Vote validation with automatic re-prompting
- Constraint specification validation
- Enhanced utility agent parsing with retry logic
- Standardized error categorization

### 4. Multi-language Support
- All prompts loaded from translation files
- English, Spanish, Mandarin supported
- Language manager handles prompt retrieval
- Consistent format across languages

### 5. Randomization and Fairness
- Random speaking order generation
- Avoid same participant starting consecutive rounds
- Random income distribution generation
- Random assignment if no consensus

---

## Current Issues and Limitations

### 1. Unanimous Agreement Failure ❌
**Problem**: Agents inconsistently respond to unanimous agreement prompts  
**Symptom**: Same agents say YES then NO to identical proposals  
**Impact**: Prevents experiments from completing

### 2. Conservative Response Bias
**Problem**: Agreement prompt encourages "NO" responses  
**Cause**: "If you think more discussion is needed, respond 'NO'" guidance  
**Impact**: Experiments get stuck in discussion loops

### 3. Lack of Context Awareness
**Problem**: Agents don't consider discussion progress  
**Missing**: Round count, position convergence, previous attempts  
**Impact**: Redundant discussions, no progress recognition

---

## Technical Implementation Files

| Component | File | Key Methods |
|-----------|------|-------------|
| Main Process | `core/phase2_manager.py` | `run_phase2()`, `_run_group_discussion()` |
| Vote Detection | `experiment_agents/utility_agent.py` | `extract_vote_from_statement()` |
| Agreement Check | `core/phase2_manager.py` | `_check_unanimous_vote_agreement()` |
| Secret Voting | `core/phase2_manager.py` | `_conduct_group_vote()`, `_get_participant_vote()` |
| Consensus Logic | `core/phase2_manager.py` | `_check_exact_consensus()` |
| Prompts | `translations/english_prompts.json` | All translated prompt templates |
| Memory Management | `utils/memory_manager.py` | `prompt_agent_for_memory_update()` |
| Logging | `utils/agent_centric_logger.py` | Discussion and vote logging |

---

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `phase2_rounds` | 20 | Maximum discussion rounds |
| `memory_character_limit` | 50,000 | Agent memory limit |
| `reasoning_enabled` | varies | Enable internal reasoning prompts |
| `temperature` | varies | Agent response randomness |
| `utility_agent_model` | `gpt-4.1-mini` | Model for parsing/validation |

---

This documentation captures the complete Phase 2 voting process as currently implemented, including all prompts, mechanisms, and technical details.