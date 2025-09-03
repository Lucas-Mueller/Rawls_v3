# Ranking Prompt Redundancy Fix Plan

## Problem Statement

When agents are asked to rank justice principles, they receive principle information **twice**:

1. **System Instructions**: Principle names via `{randomized_example}` placeholder
2. **Input Prompt**: Detailed principle descriptions via `{master_principle_descriptions}` placeholder

This redundancy occurs in all ranking rounds across all three languages (English, Spanish, Mandarin).

## Affected Components

### Ranking Rounds
- Phase 1 Round 0: Initial ranking
- Phase 1 Round 0 (post-explanation): Second ranking  
- Phase 1 Round 5: Final ranking
- Phase 2 Final: End-of-experiment ranking

### Code Locations
- **System Instructions**: `utils/language_manager.py:_generate_randomized_example()`
- **Input Prompts**: `translations/{language}_prompts.json` ranking templates

## Solution

**Remove principle names from system instructions, keep detailed descriptions in input prompts only.**

### Implementation Steps

#### Step 1: Remove Randomized Examples from System Instructions
- **File**: `translations/english_prompts.json`
- **Target**: `phase1_round0_initial_ranking` template
- **Change**: Remove `{randomized_example}` placeholder and example section
- **Repeat**: Apply to Spanish and Mandarin translation files

#### Step 2: Update Language Manager
- **File**: `utils/language_manager.py`
- **Target**: `get_phase1_instructions()` method
- **Change**: Remove `_generate_randomized_example()` call for round 0
- **Impact**: System instructions will contain no principle information

#### Step 3: Verify Input Prompts Remain Complete
- **Files**: All ranking prompt templates in translation files
- **Ensure**: `{master_principle_descriptions}` placeholders remain active
- **Result**: Agents receive principle details only when making ranking decisions

## Expected Outcome

- **System Instructions**: Generic experiment context only
- **Input Prompts**: Complete principle descriptions when needed
- **Result**: Single-source principle delivery, zero redundancy

## Validation

Test that agents can still complete ranking tasks with principle information delivered only through input prompts, not system instructions.