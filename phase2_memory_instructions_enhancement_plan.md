# Phase 2 First Round Memory Update Enhancement Plan

## Problem Statement

Currently, the first internal reasoning prompt in Phase 2 contains detailed Phase 2-specific instructions that are NOT present in the first memory update prompt. This creates an inconsistency where agents receive important context during reasoning but not during memory consolidation.

### Current Situation

**First Reasoning Prompt (phase2_internal_reasoning) includes:**
```
You are in Phase 2:
In this part of the experiment you, as a group, are to choose one principle for yourselves. This choice will determine the payoff you get in this part of the experiment. Your payoffs will be determined as follows. The distributions do not need resemble the distributions in Part I.
THE STAKES IN THIS PART OF THE EXPERIMENT ARE MUCH HIGHER THAN IN THE FIRST PART.
Your choice of principle will be used to pick out those distribution schedules which conform to your principle.
Thus, for example, if you picked the principle to maximize the average income, you would be saying that the group wants to pick out a distribution with the highest average income. Each of you will then be randomly assigned an income from that distribution. That is your payoff for Part II. The group's chosen principle will then be applied to determine everyone's final earnings.

Important: the group must adopt exactly one of the four principles you studied in Phase 1—no new principles can be created.
You are now working with a higher-stakes distribution distinct from the Phase 1 examples, and its exact payoffs remain unknown to participants by design.

Each round of Phase 2 follows this flow:
1. Discussion
2. Voting

Voting process: Participants can initiate voting, which requires unanimous confirmation (1=Yes, 0=No). If confirmed, a two-stage secret ballot occurs: principle selection (1-4), then constraint specification for principles 3-4. Consensus requires all participants to agree on both principle and constraint amount (if applicable).
```

**First Memory Update Prompts (memory_memory_update_prompt_first_round and memory_narrative_update_prompt_first_round) currently have:**
- General experiment explanation (already in context)
- Basic Phase 2 info BUT MISSING the detailed Phase 2 mechanics above

## Desired Behavior

The first memory update prompt in Phase 2 should include the SAME Phase 2-specific instructions that appear in the reasoning prompt. This ensures agents can properly consolidate their understanding of:
- Higher stakes in Phase 2
- How group choice determines payoffs
- The principle selection constraint (one of four)
- Higher-stakes distribution characteristics
- Round flow (Discussion → Voting)
- Voting process mechanics

## Implementation Plan

### Step 1: Update Translation Files (All Languages)

**English (`translations/english_prompts.json`):**
- Update `memory_memory_update_prompt_first_round` (lines 95-99)
- Update `memory_memory_update_prompt_first_round_no_recent_activity` (lines 100-104)
- Update `memory_narrative_update_prompt_first_round` (lines 105-109)
- Update `memory_narrative_update_prompt_first_round_no_recent_activity` (lines 110-114)

**Spanish (`translations/spanish_prompts.json`):**
- Update corresponding Spanish prompts (lines 162-165)

**Mandarin (`translations/mandarin_prompts.json`):**
- Update corresponding Mandarin prompts (lines 110-113)

### Step 2: Extract Phase 2 Instructions Block

**Create a reusable content block that includes:**
```
You are in Phase 2:
In this part of the experiment you, as a group, are to choose one principle for yourselves. This choice will determine the payoff you get in this part of the experiment. Your payoffs will be determined as follows. The distributions do not need resemble the distributions in Part I.
THE STAKES IN THIS PART OF THE EXPERIMENT ARE MUCH HIGHER THAN IN THE FIRST PART.
Your choice of principle will be used to pick out those distribution schedules which conform to your principle.
Thus, for example, if you picked the principle to maximize the average income, you would be saying that the group wants to pick out a distribution with the highest average income. Each of you will then be randomly assigned an income from that distribution. That is your payoff for Part II. The group's chosen principle will then be applied to determine everyone's final earnings.

Important: the group must adopt exactly one of the four principles you studied in Phase 1—no new principles can be created.
You are now working with a higher-stakes distribution distinct from the Phase 1 examples, and its exact payoffs remain unknown to participants by design.

Each round of Phase 2 follows this flow:
1. Discussion
2. Voting

Voting process: Participants can initiate voting, which requires unanimous confirmation (1=Yes, 0=No). If confirmed, a two-stage secret ballot occurs: principle selection (1-4), then constraint specification for principles 3-4. Consensus requires all participants to agree on both principle and constraint amount (if applicable).
```

### Step 3: Update Memory Prompt Structure

**For each first-round memory prompt:**
1. Keep the general experiment explanation (Phase 1 & 2 overview)
2. **ADD** the detailed Phase 2 instructions block
3. Maintain existing structure for memory update guidance

**Target structure:**
```
[Standard memory update instruction header]

Your Previous Memory:
{current_memory}

[General experiment explanation - Phase 1 & 2 overview]

[DETAILED Phase 2 instructions block - NEW]

[Recent Activity or Discussion History section]

RETURN: [Memory format instructions]
```

### Step 4: Placement in Prompts

The Phase 2 instructions should be placed:
- **After** the general experiment explanation
- **Before** the "Recent Activity" or "Discussion History" section
- This mirrors the structure in `phase2_internal_reasoning`

### Step 5: Verification

**Test that:**
1. First round memory updates include full Phase 2 instructions
2. Subsequent round memory updates continue using standard prompts (without Phase 2 instructions)
3. All three languages have consistent content
4. The logic in `utils/memory_manager.py` (lines 279-317) correctly routes to first-round vs standard templates

### Step 6: Affected Files

**Translation files:**
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

**Code files (no changes needed, verification only):**
- `utils/memory_manager.py` - Already has logic for first round detection (line 280)
- `core/services/memory_service.py` - Uses memory manager

## Benefits

1. **Consistency**: Agents receive same Phase 2 context during reasoning AND memory consolidation
2. **Better Memory**: Agents can properly encode Phase 2 mechanics in their memory
3. **Reduced Confusion**: No information gap between reasoning and memory phases
4. **Alignment**: Memory prompts now match the detail level of reasoning prompts

## Notes

- The general experiment explanation remains (though technically already in context) for consistency
- This change ONLY affects the first round of Phase 2 memory updates
- Subsequent rounds continue using standard memory update prompts
- No code changes required - only prompt content updates