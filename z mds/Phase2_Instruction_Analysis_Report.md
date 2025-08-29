# Phase 2 Instruction Analysis Report
## Multi-Language Evaluation of Agent Instructions in the Frohlich Experiment

**Date**: August 27, 2025  
**Analysis Scope**: Phase 2 group discussion instructions across English, Spanish, and Mandarin  
**Code Review Locations**: 
- `translations/english_prompts.json` (lines 30-31)
- `translations/spanish_prompts.json` (lines 30-31)  
- `translations/mandarin_prompts.json` (lines 30-31)
- `core/phase2_manager.py` (implementation analysis)

---

## Executive Summary

This analysis evaluates the Phase 2 instructions given to AI agents at the beginning of group discussion in the Frohlich Experiment across three languages: English, Spanish, and Mandarin. The evaluation focuses on instruction clarity, process alignment, and cross-language consistency.

**Key Findings:**
- **Critical instruction gaps**: All languages fail to adequately explain the sequential speaking order and turn-based nature of discussion 
- **Voting mechanism confusion**: Complex inconsistencies between simple and complex voting modes across languages
- **Mandarin superiority**: The Mandarin instructions demonstrate the clearest emphasis on formal voting requirements 
- **Spanish redundancy issues**: Spanish instructions contain unclear duplication and formatting problems
- **Example bias risk**: Current instructions use consistent examples (e.g., always showing principle c with $15,000) which may skew agent choices


---

## 1. Phase 2 Process Overview

Based on code analysis of `phase2_manager.py`, the actual Phase 2 process includes:

### Core Process Components:
1. **Sequential Discussion Rounds** (up to configured maximum, typically 5)
2. **Randomized Speaking Order** with anti-repetition logic  
3. **Two Voting Detection Modes**:
   - **Simple Mode**: Preference-based consensus detection
   - **Complex Mode**: Formal voting with confirmation and secret ballot phases

---

## 2. Instruction Analysis by Language

### 2.1 English Instructions

#### Structure and Content:
- **Simple Mode** (`phase2_discussion_prompt_simple`): 350+ words
- **Complex Mode** (`phase2_discussion_prompt_complex`): 280+ words
- **Stakes Emphasis**: "**IMPORTANT: The stakes are much higher in this phase than in Phase 1.**"


#### Strengths:
✅ Clear explanation of consequences ("This group decision will determine everyone's final earnings")  
✅ Detailed principle definitions with letter coding (a, b, c, d)  
✅ Clear distinction between discussion modes  

#### Weaknesses:
❌ **Critical gap**: No explanation of sequential turn-based speaking order  
❌ **Process confusion**: Instructions suggest continuous discussion but implementation is turn-based  
❌ **Example bias**: Consistent use of same examples (e.g., "$15,000 floor constraint") may influence agent choices

### 2.2 Spanish Instructions

#### Structure and Content:
- **Simple Mode** (`phase2_discussion_prompt_simple`): 400+ words
- **Complex Mode** (`phase2_discussion_prompt_complex`): 320+ words
- **Stakes Emphasis**: "**IMPORTANTE: Las apuestas son mucho más altas en esta fase que en la Fase 1.**"

#### Strengths:
✅ Most detailed principle explanations across all languages  
✅ Clear consequence messaging  
✅ Good use of formatting and structure  
✅ Comprehensive voting procedure explanation  

#### Weaknesses:
❌ **Major structural issue**: "VOTACIÓN FORMAL REQUERIDA" section in simple mode creates confusion  
❌ **Translation inconsistency**: Complex mode has different emphasis than English version  
❌ **Redundant information**: Repetitive explanation of voting requirements  
❌ **Missing turn structure**: Like English, fails to explain sequential nature of discussion  
❌ **Formatting problems**: Some formatting inconsistencies that could confuse agents  

### 2.3 Mandarin Instructions

#### Structure and Content:
- **Simple Mode** (`phase2_discussion_prompt_simple`): 320+ words
- **Complex Mode** (`phase2_discussion_prompt_complex`): 280+ words
- **Stakes Emphasis**: "**重要：这一阶段的风险远高于第1阶段。**"

#### Strengths:
✅ **Superior voting clarity**: Most explicit about formal voting requirements ("⚠️ **关键规则：只有正式投票才能达成有约束力的共识！**")  
✅ **Clear visual emphasis**: Effective use of warning symbols and formatting  
✅ **Concise but complete**: Manages to convey essential information efficiently  
✅ **Cultural adaptation**: Uses appropriate Chinese linguistic structures  
✅ **Process reminders**: Strong emphasis on "讨论 ≠ 协议" (Discussion ≠ Agreement)  

#### Weaknesses:
❌ **Turn structure gap**: Same issue as other languages regarding sequential discussion  
❌ **Limited examples**: Fewer concrete examples than English/Spanish versions  
❌ **Cultural assumptions**: May assume familiarity with consensus-building processes not universal  

---

## 3. Cross-Language Comparison

### 3.1 Consistency Analysis

| Aspect | English | Spanish | Mandarin | Consistency Score |
|--------|---------|---------|----------|-------------------|
| Stakes Emphasis | Strong | Strong | Strong | ✅ High |
| Principle Definitions | Complete | Complete | Complete | ✅ High |
| Voting Procedures | Moderate | Confusing | Excellent | ❌ Low |
| Process Flow | Unclear | Unclear | Unclear | ❌ Low |
| Format Examples | Good | Good | Moderate | ⚠️ Medium |
| Turn Structure | Missing | Missing | Missing | ❌ Low |

### 3.2 Language-Specific Strengths

**English**: Balanced detail and readability, good examples  
**Spanish**: Most comprehensive content, detailed explanations  
**Mandarin**: Best voting procedure clarity, effective visual emphasis  

### 3.3 Universal Weaknesses

1. **Sequential turn explanation**: All languages fail to explain that discussion happens one participant at a time
2. **Implementation complexity**: None capture the sophisticated error handling and retry mechanisms
3. **Memory system**: No mention of how agent memory is updated during the process
4. **Timeout handling**: Instructions don't prepare agents for potential timeouts or system messages

---

## 4. Alignment with Implementation

### 4.1 Process Flow Alignment

#### What Instructions Say:
- "Work with other participants to reach consensus" (suggests free-form discussion)
- "Share your thoughts and reasoning" (implies open communication)

#### What Actually Happens:
- **Sequential speaking order**: Participants speak one at a time in randomized order
- **Turn-based rounds**: Up to 5 structured rounds with speaking positions
- **Individual memory updates**: Each participant's memory updated after their turn
- **Anti-repetition logic**: Complex algorithms prevent same participant starting and ending consecutive rounds

**Alignment Score**: ❌ **Poor** - Major disconnect between described and actual process

### 4.2 Voting Mechanism Alignment

#### What Instructions Say:
**Simple Mode**: "When ready to commit, clearly state: 'My preference is [your choice]'"  
**Complex Mode**: "When you feel ready to vote, express your desire: 'I think we should vote'"

#### What Actually Happens:
- **Simple Mode**: Uses `detect_preference_statement()` to identify commitments, checks for unanimous preferences (working as intended)
- **Complex Mode**: Uses `detect_vote_intention_enhanced()`, runs confirmation phase with all participants, conducts secret ballot

**Alignment Score**: ✅ **Good** - Both modes work as designed, though simple mode mechanism could be explained more clearly

---

## 5. Identified Problems and Impacts

### 5.1 Critical Issues

#### **Problem 1: Turn Structure Misrepresentation**
- **Description**: Instructions suggest free-form group discussion but implementation is strictly sequential
- **Impact**: Agents may be confused when they can't interrupt or respond immediately to other participants
- **Evidence**: Lines 377-483 in `phase2_manager.py` show clear sequential processing
- **Severity**: 🔴 **High**

#### **Problem 2: Voting Mode Confusion** (Spanish)
- **Description**: Spanish simple mode contains formal voting requirements, creating contradiction
- **Impact**: Spanish-speaking agents receive conflicting instructions about how consensus works
- **Evidence**: Lines 30-31 in `spanish_prompts.json` show contradictory messaging
- **Severity**: 🔴 **High**

#### **Problem 3: Example Bias Risk**
- **Description**: All languages consistently use the same examples (e.g., "$15,000 floor constraint", "principle c")
- **Impact**: May inadvertently bias agents toward specific principles or constraint amounts
- **Evidence**: Repeated use of identical examples across all prompts in translation files
- **Severity**: 🟡 **Medium**

### 5.2 Systemic Issues

#### **Issue 1: Simple vs Complex Mode Clarity**
- **Description**: Simple mode works via preference detection (by design), but this isn't clearly explained
- **Impact**: Users may expect explicit voting in simple mode when preference-based consensus is the intended mechanism
- **Severity**: 🟡 **Medium**

---

## 6. Recommendations

### 6.1 Immediate Priority Fixes

#### **1. Add Turn Structure Explanation** 🔴 **High Priority**
**For all languages**, add section explaining:
```
DISCUSSION PROCESS:
- Discussion proceeds in turns with randomized speaking order
- You will be prompted when it's your turn to speak
```

#### **2. Fix Spanish Mode Contradiction** 🔴 **High Priority**
**Spanish only**: Remove or clarify the "VOTACIÓN FORMAL REQUERIDA" section in simple mode. Simple mode should emphasize preference statements, not formal voting.

#### **3. Standardize Voting Clarity** 🔴 **High Priority**
**All languages**: Use Mandarin's superior voting instruction clarity as a model. Add clear visual warnings about voting requirements.

### 6.2 Content Improvements

#### **4. Vary Examples to Prevent Bias** 🟡 **Medium Priority**
**For all languages**, diversify examples:
- Use different constraint amounts across different instructions ($12,000, $18,000, $22,000)
- Vary which principles are used in examples (rotate between a, b, c, d)
- Ensure no single principle or constraint amount appears disproportionately
- Give a big fat warning that this is only for demonstration purposes and that agents are free to choose whathever they think is best

#### **5. Clarify Simple Mode Mechanism** 🟡 **Medium Priority**
**For all languages**, better explain simple mode:
```
SIMPLE MODE CONSENSUS:
- Consensus is reached when all participants state clear preferences for the same principle
- No formal voting is required - preference statements are sufficient
- Look for others' preference statements to understand group direction
```

#### **6. Improve Spanish Formatting** 🟡 **Medium Priority**
- **Spanish only**: Fix formatting inconsistencies and reduce redundancy in voting instructions

### 6.3 Advanced Recommendations

#### **7. Create Dynamic Instructions** 🔵 **Low Priority**
Consider generating instructions that adapt based on:
- Number of participants in the experiment
- Voting detection mode configuration

#### **8. Add Instruction Validation** 🔵 **Low Priority**
Implement system to verify that instructions accurately reflect current implementation, preventing future divergence.

#### **9. Cultural Adaptation Enhancement** 🔵 **Low Priority**
- **English**: Add more explicit cooperation guidance
- **Spanish**: Emphasize group harmony and collective decision-making
- **Mandarin**: Leverage cultural familiarity with consensus processes

---

## 7. Implementation Suggestions

### 7.1 Code Changes Required

#### **Location**: `translations/*.json` files
- Update `phase2_discussion_prompt_simple` and `phase2_discussion_prompt_complex` in all three language files
- Ensure consistency across languages while preserving cultural adaptations

#### **Validation Points**: `core/phase2_manager.py`
- Lines 1097-1119: `_build_discussion_prompt()` method would use updated prompts
- Lines 376-583: Sequential discussion logic should be explained in instructions


---

## 8. Conclusion

The Phase 2 instructions across all three languages suffer from significant gaps between what they describe and what actually happens in the implementation. While each language has unique strengths—English's balance, Spanish's detail, and Mandarin's voting clarity—all fail to adequately prepare agents for the sequential, turn-based nature of the discussion process.

**Priority Actions:**
1. **Immediate**: Fix critical turn structure explanation and Spanish voting contradictions
2. **Short-term**: Address example bias and clarify simple mode mechanism  
3. **Long-term**: Consider dynamic instructions based on experiment configuration

**Expected Outcomes:**
- Clearer understanding of turn-based discussion process
- Reduced bias from consistent examples across experiments
- Better agent performance through improved process understanding
- More valid experimental results across languages

**Quality Assurance:**
The current instruction-process alignment is **MODERATE to GOOD** for voting mechanisms but **POOR** for turn structure explanation. With the recommended changes focusing on the key issues identified, this could improve to **GOOD to EXCELLENT**, enhancing experimental validity without overwhelming agents with unnecessary implementation details.

---

*This analysis was conducted through systematic code review and cross-language comparison. All line numbers and code references are accurate as of the analysis date.*