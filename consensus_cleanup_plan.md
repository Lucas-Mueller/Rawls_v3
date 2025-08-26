# Consensus Path Cleanup Plan: Remove Non-Formal Agreement Detection

## Executive Summary

This plan outlines the systematic removal of all non-formal consensus paths from Phase 2, ensuring **only formal votes count for agreement**. Currently, the system has multiple ways to reach consensus that bypass proper voting procedures, which must be eliminated.

## Current State Analysis

### Non-Formal Consensus Paths (TO BE REMOVED)

1. **Preference-Based Consensus** (`core/phase2_manager.py:401-512`)
   - Automatically triggers when all participants state matching preferences
   - Uses `detect_preference_statement()` and `check_preference_consensus()`
   - Returns consensus without formal voting
   - **LOCATION**: Lines 401-512 in `_run_group_discussion()`

2. **Agreement Detection for Voting Confirmations** (`experiment_agents/utility_agent.py:321-397`)
   - Uses `detect_agreement_multilingual()` for voting confirmations
   - Can interpret statements as agreement without explicit votes
   - **LOCATION**: `_conduct_confirmation_phase()` in phase2_manager.py:893-957

3. **Statement-Based Consensus Inference**
   - Implicit consensus detection through discussion analysis
   - Uses utility agent to infer group agreement from statements
   - **LOCATION**: Various locations in phase2_manager.py

### Formal Voting Paths (TO PRESERVE)

1. **Complex Voting Mode** (`core/phase2_manager.py:825-891`)
   - Confirmation phase with explicit agreement collection
   - Secret ballot phase with formal vote tallying
   - Uses `check_ballot_consensus()` for formal consensus verification

2. **Explicit Vote Results** 
   - `VoteResult` objects with formal vote counts
   - Stored in `discussion_state.vote_history`
   - Clear audit trail of formal voting

## Cleanup Tasks

### Phase 1: Remove Preference-Based Consensus

**Files to Modify:**
- `core/phase2_manager.py`
- `experiment_agents/utility_agent.py`

**Actions:**
1. **Remove preference detection logic** (phase2_manager.py:401-512)
   - Delete `detect_preference_statement()` calls
   - Remove `check_preference_consensus()` workflow
   - Remove automatic consensus triggers based on matching preferences

2. **Clean up utility agent methods**
   - Mark `check_preference_consensus()` as deprecated
   - Remove `detect_preference_statement()` if not used elsewhere
   - Keep methods for backward compatibility but disable functionality

3. **Update discussion flow**
   - Remove preference tracking in `discussion_state.current_round_preferences`
   - Remove automatic consensus checks after each participant speaks
   - Ensure discussion continues until formal vote is triggered

### Phase 2: Strengthen Formal Voting Requirements

**Files to Modify:**
- `core/phase2_manager.py`
- `experiment_agents/utility_agent.py`
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

**Actions:**
1. **Enforce explicit voting triggers**
   - Require explicit "call for vote" statements
   - Use `detect_vote_intention_enhanced()` exclusively for vote initiation
   - No implicit vote triggers based on discussion content

2. **Strengthen confirmation phase**
   - Require unanimous explicit agreement to proceed to voting
   - Tighten `detect_agreement_multilingual()` to be more restrictive
   - Clear rejection of ambiguous responses

3. **Make secret ballot mandatory for consensus**
   - All consensus must go through secret ballot phase
   - Remove any shortcuts that bypass formal voting
   - Ensure `check_ballot_consensus()` is the only consensus determination method

### Phase 3: Update Prompts and Language

**Files to Modify:**
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

**Actions:**
1. **Remove preference-based consensus language**
   - Update `phase2_discussion_prompt_simple` to remove preference instructions
   - Focus on discussion-only language until formal vote is called
   - Remove "consensus is automatically reached" language

2. **Emphasize formal voting requirement**
   - Add language about requiring formal votes for decisions
   - Clarify that discussion alone cannot create binding agreements
   - Update prompts to encourage calling for votes when ready

3. **Strengthen voting language**
   - Make voting confirmation prompts more explicit
   - Require clear "YES" or "NO" responses for vote confirmations
   - Add warnings about the formal nature of voting

### Phase 4: Clean Up Data Models and Logging

**Files to Modify:**
- `models/experiment_types.py`
- `utils/agent_centric_logger.py`
- `core/phase2_manager.py`

**Actions:**
1. **Remove preference consensus tracking**
   - Clean up `GroupDiscussionState` to remove preference tracking
   - Remove preference-related fields and methods
   - Update logging to reflect formal voting only

2. **Update logging categories**
   - Remove "preference_consensus" vote types
   - Ensure only "formal_vote" types are logged
   - Update result structures to reflect formal voting paths only

3. **Simplify consensus detection**
   - Remove multiple consensus detection methods
   - Centralize on ballot-based consensus only
   - Clean up validation and error handling

## Implementation Strategy

### Step-by-Step Execution

1. **Backup and Branch Creation**
   ```bash
   git checkout -b consensus-cleanup-formal-votes-only
   git add -A && git commit -m "Pre-cleanup backup commit"
   ```

2. **Phase 1 Implementation**
   - Comment out preference-based consensus code first
   - Test that discussions continue without auto-consensus
   - Ensure formal voting still works

3. **Phase 2 Implementation** 
   - Strengthen formal voting requirements
   - Test confirmation and ballot phases
   - Verify unanimous voting requirement

4. **Phase 3 Implementation**
   - Update all language files
   - Test multilingual support
   - Verify prompt clarity

5. **Phase 4 Implementation**
   - Clean up data models
   - Update logging and results
   - Remove deprecated methods

### Testing Requirements

**Test Cases:**
1. **Discussion-only scenarios**: Verify discussions continue without consensus
2. **Formal voting scenarios**: Verify votes work correctly
3. **Mixed scenarios**: Ensure no preference-based shortcuts exist
4. **Multilingual scenarios**: Test in all supported languages
5. **Edge cases**: Test with agent failures, incomplete responses

**Validation Criteria:**
- No consensus reached without formal voting
- All agreements require secret ballot completion
- Clear audit trail of formal voting process
- No implicit or inferred consensus paths remain

## Risk Mitigation

### Potential Issues

1. **Increased discussion rounds**: Without auto-consensus, discussions may run longer
2. **Agent confusion**: Agents may expect preference-based consensus
3. **Logging inconsistencies**: Historical data may reference removed mechanisms

### Mitigation Strategies

1. **Update agent instructions** to clarify formal voting requirements
2. **Add timeout mechanisms** if discussions become too long
3. **Maintain backward compatibility** for result analysis
4. **Comprehensive testing** before deployment

## Success Metrics

- [ ] Zero preference-based consensus paths remain active
- [ ] All consensus requires completed formal voting process  
- [ ] Clear separation between discussion and voting phases
- [ ] Comprehensive test coverage for formal voting scenarios
- [ ] Multilingual support maintained for formal voting
- [ ] Historical result compatibility preserved

## Timeline

- **Phase 1**: 2-3 hours (code removal and basic testing)
- **Phase 2**: 3-4 hours (voting strengthening and testing)  
- **Phase 3**: 2-3 hours (prompt updates and multilingual testing)
- **Phase 4**: 2-3 hours (cleanup and final testing)
- **Total Estimated Time**: 9-13 hours

## Files Requiring Changes

### Core Logic Files
- `core/phase2_manager.py` (primary changes)
- `experiment_agents/utility_agent.py` (method deprecation)
- `models/experiment_types.py` (data model cleanup)

### Language Files
- `translations/english_prompts.json`
- `translations/spanish_prompts.json` 
- `translations/mandarin_prompts.json`

### Support Files
- `utils/agent_centric_logger.py`
- Configuration files as needed

This plan ensures a clean, systematic removal of all non-formal consensus paths while preserving and strengthening the formal voting mechanisms that should be the only way to reach agreement in Phase 2.