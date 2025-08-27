# Implementation Plan: Academic Integrity Updates

## Overview

This document provides a concrete, step-by-step implementation plan for updating the AI agent prompts to enhance fidelity to the original Frohlich & Oppenheimer 1992 experiment while maintaining essential AI functionality.

**Estimated Implementation Time:** 2-3 hours  
**Priority Level:** High  
**Files to Modify:** 1 primary file + validation testing  

---

## Implementation Steps

### Phase 1: Justice Principle Definition Updates (60 minutes)

#### 1.1 Update File: `translations/english_prompts.json`

**Target Section:** Lines requiring justice principle definitions

**Current Issues:**
- Simplified principle descriptions lack the explanatory depth of originals
- Missing key conceptual elements that help participants understand principles

#### 1.2 Specific Text Replacements

**Replace in all relevant prompt templates:**

**Principle 1 - Maximizing the Floor Income:**
```json
OLD: "Maximizing the floor income: Choose the distribution that maximizes the lowest income in society"

NEW: "Maximizing the floor income: The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society. In judging among income distributions, the distribution which ensures the poorest person the highest income is the most just. No person's income can go up unless it increases the income of the people at the very bottom."
```

**Principle 2 - Maximizing the Average Income:**
```json
OLD: "Maximizing the average income: Choose the distribution that maximizes the average income"

NEW: "Maximizing the average income: The most just distribution of income is that which maximizes the average income in the society. For any society maximizing the average income maximizes the total income in the society."
```

**Principle 3 - Maximizing Average with Floor Constraint:**
```json
OLD: "Maximizing the average income with a floor constraint: Maximize average income while ensuring everyone gets at least a specified minimum"

NEW: "Maximizing the average income with a floor constraint: The most just distribution of income is that which maximizes the average income only after a certain specified minimum income is guaranteed to everyone. Such a principle ensures that the attempt to maximize the average is constrained so as to ensure that individuals 'at the bottom' receive a specified minimum. To choose this principle one must specify the value of the floor (lowest income)."
```

**Principle 4 - Maximizing Average with Range Constraint:**
```json
OLD: "Maximizing the average income with a range constraint: Maximize average income while keeping the gap between richest and poorest within a specified limit"

NEW: "Maximizing the average income with a range constraint: The most just distribution of income is that which attempts to maximize the average income only after guaranteeing that the difference between the poorest and the richest individuals (i.e., the range of income) in the society is not greater than a specified amount. Such a principle ensures that the attempt to maximize the average does not allow income differences between rich and poor to exceed a specified amount. To choose this principle one must specify the dollar difference between the high and low incomes."
```

#### 1.3 Affected Prompt Templates
Update these specific keys in `english_prompts.json`:
- `phase1_round0_initial_ranking`
- `phase1_round5_final_ranking` 
- `phase1_detailed_principles_explanation`
- `phase2_discussion_prompt_simple`
- `phase2_discussion_prompt_complex`
- `phase2_secret_ballot_request`

---

### Phase 2: Remove Explicit Reasoning Requirements (20 minutes)

#### 2.1 Target Prompts
**File:** `translations/english_prompts.json`

**Specific Changes:**

**Initial Ranking Prompt:**
```json
OLD: "For each principle, also indicate your certainty level (very unsure, unsure, no opinion, sure, very sure). Explain your reasoning clearly."

NEW: "For each principle, also indicate your certainty level (very unsure, unsure, no opinion, sure, very sure)."
```

**Final Ranking Prompt:**
```json
OLD: "Explain your reasoning clearly."

NEW: [Remove this instruction entirely]
```

#### 2.2 Affected Keys
- `phase1_round0_initial_ranking`
- `phase1_round5_final_ranking`
- `phase1_post_explanation_ranking_prompt`
- `phase1_initial_ranking_prompt_template`

---

### Phase 3: Combine Phase 2 Stakes Explanation (30 minutes)

#### 3.1 Update Stakes Wording
**File:** `translations/english_prompts.json`

**Target:** `phase2_discussion_prompt_complex` and `phase2_discussion_prompt_simple`

**New Combined Wording:**
```json
"**IMPORTANT: The stakes are much higher in this phase than in Phase 1.** Your payoffs in this section of the experiment will conform to the principle which you, as a group, adopt. This group decision will determine everyone's final earnings and has far greater consequences than your individual Phase 1 choices. If you, as a group, do not adopt any principle, then we will select one of the income distributions at random for you as a group. That choice of income distribution will conform to no particular characteristics."
```

---

### Phase 4: Refine Personality Instructions (15 minutes)

#### 4.1 Remove Explicit Personality Maintenance
**File:** `translations/english_prompts.json`

**Search and Remove:**
- "Stay true to your personality"
- "Maintain your assigned personality"
- "Remember to stay true to your personality while participating"

**Keep:**
- Personality descriptions in agent configurations
- "PERSONALITY: {personality}" context information

#### 4.2 Target Context Templates
- `context_context_info_format`
- `context_memory_update_format`

---

## Testing and Validation Plan

### Test Case 1: Principle Definition Verification (15 minutes)
1. Run experiment with updated definitions
2. Verify agents receive complete principle descriptions
3. Check that constraint specification requirements are clear
4. Confirm no parsing errors in principle selection

### Test Case 2: Ranking Behavior Verification (10 minutes)
1. Test initial and final ranking prompts
2. Verify agents no longer receive explicit reasoning requirements
3. Confirm certainty levels still captured correctly
4. Check that agents provide rankings without format errors

### Test Case 3: Phase 2 Stakes Communication (10 minutes)
1. Verify combined stakes explanation appears correctly
2. Check that both original content and AI emphasis are present
3. Confirm no duplication or formatting issues

### Test Case 4: Personality Instruction Check (5 minutes)  
1. Verify personality maintenance reminders removed
2. Confirm personality descriptions still included in context
3. Check that agents behave according to personalities without explicit reminders

---

## File Backup and Safety

### Before Implementation:
1. **Create backup:** `cp translations/english_prompts.json translations/english_prompts.json.backup`
2. **Document current state:** Save current prompt versions for rollback if needed
3. **Test environment:** Verify changes in test configuration before production

### Rollback Plan:
```bash
# If issues occur, restore backup
cp translations/english_prompts.json.backup translations/english_prompts.json
```

---

## Implementation Checklist

### Preparation ✅
- [ ] Read and understand the comparison report
- [ ] Backup current `english_prompts.json`
- [ ] Set up test environment
- [ ] Prepare test configuration files

### Phase 1: Justice Principles ✅
- [ ] Update Principle 1 definition (Maximizing Floor)
- [ ] Update Principle 2 definition (Maximizing Average)  
- [ ] Update Principle 3 definition (Floor Constraint)
- [ ] Update Principle 4 definition (Range Constraint)
- [ ] Verify all affected prompt templates updated
- [ ] Test principle definition display

### Phase 2: Reasoning Requirements ✅
- [ ] Remove "Explain your reasoning clearly" from initial ranking
- [ ] Remove reasoning requirements from final ranking
- [ ] Update post-explanation ranking prompt
- [ ] Test ranking prompts function correctly

### Phase 3: Stakes Explanation ✅
- [ ] Update complex mode stakes explanation
- [ ] Update simple mode stakes explanation (if applicable)
- [ ] Verify combined wording displays correctly
- [ ] Test Phase 2 introduction messaging

### Phase 4: Personality Instructions ✅
- [ ] Remove "Stay true to your personality" references
- [ ] Remove "Maintain your assigned personality" references
- [ ] Verify personality descriptions preserved
- [ ] Test personality context inclusion

### Testing and Validation ✅
- [ ] Run Test Case 1: Principle definitions
- [ ] Run Test Case 2: Ranking behavior
- [ ] Run Test Case 3: Phase 2 stakes
- [ ] Run Test Case 4: Personality instructions
- [ ] Complete end-to-end experiment test
- [ ] Verify no parsing errors or system failures

### Documentation ✅
- [ ] Document changes made
- [ ] Update any configuration guides if needed
- [ ] Confirm implementation matches comparison report recommendations

---

## Success Criteria

### Primary Goals Achieved:
1. ✅ **Justice principle definitions match original handbook exactly**
2. ✅ **Explicit reasoning requirements removed from rankings**
3. ✅ **Combined stakes explanation includes both original and AI content**
4. ✅ **Personality maintenance reminders removed while preserving descriptions**

### System Integrity Maintained:
1. ✅ **No parsing errors or system failures**
2. ✅ **All existing functionality preserved**
3. ✅ **Memory management and structured formats intact**
4. ✅ **Voting system and error handling unchanged**

### Academic Fidelity Enhanced:
1. ✅ **Improved alignment with original human experiment**
2. ✅ **Reduced potential for unintended bias**
3. ✅ **Maintained essential AI-specific adaptations**
4. ✅ **Preserved experimental validity and technical functionality**

---

## Post-Implementation

### Monitoring (First Week):
- Run several test experiments to verify stable operation
- Monitor for any unexpected agent behaviors
- Collect feedback on principle clarity and understanding

### Documentation Updates:
- Update any user guides or documentation
- Note changes in experiment logs
- Prepare summary of improvements for research team

### Future Considerations:
- Monitor agent responses for improved academic fidelity
- Consider additional refinements based on experimental results
- Document lessons learned for future AI experiment adaptations

---

*Implementation Plan Created: August 27, 2025*  
*Based on: AI Agent Prompts vs Original Human Instructions Comparison Report*  
*Priority: High - Academic Integrity Enhancement*