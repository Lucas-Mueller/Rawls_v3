# Plan: Incorporate Payoff Notification Context into Memory Update Prompts

## Problem Statement
In Phase 1 application rounds, agents receive payoff notifications (earnings, class assignments, and counterfactual outcomes) in the same prompt where they're asked to update their memory. However, the current memory update instruction doesn't explicitly highlight this connection, potentially causing agents to overlook the significance of their financial outcomes when updating their memory.

## Current State Analysis

### Current Memory Update Prompt (English)
```
"Return your complete updated memory incorporating insights from the recent activity. Include both important information from your previous memory and new learnings. Focus on information that might influence your choices about justice principles or help you in group discussions."
```

### Where Payoff Notifications Occur
- **Phase 1 Application Rounds** (rounds 1-4): Agents receive detailed payoff information including:
  - Their assigned income class
  - Their earnings for the round
  - Comprehensive counterfactual analysis showing what they would have earned under each principle
  - This information is included in the "Recent Activity" section passed to the memory update prompt

### Affected Prompt Templates
Need to update these 8 templates across all languages:
1. `memory_memory_update_prompt` (structured style)
2. `memory_narrative_update_prompt` (narrative style)
3. `memory_memory_update_prompt_no_recent_activity` (discussion contexts)
4. `memory_narrative_update_prompt_no_recent_activity` (discussion contexts)
5. `memory_memory_update_prompt_first_round` (Phase 2 first round)
6. `memory_narrative_update_prompt_first_round` (Phase 2 first round)
7. `memory_memory_update_prompt_first_round_no_recent_activity` (Phase 2 first round, discussion)
8. `memory_narrative_update_prompt_first_round_no_recent_activity` (Phase 2 first round, discussion)

## Proposed Solution

### 1. Enhanced Memory Update Instruction
Update the core instruction with comprehensive payoff analysis guidance:

**English:**
```
"Return your complete updated memory incorporating insights from the recent activity. Include both important information from your previous memory and new learnings.

Besides your memory and your recent activity you will receive the outcome of your choice which includes the payoff you received, your class assignment and the payoffs you would have received under each principle. Please analyze and incorporate this information into your updated memory.

Focus on information that might influence your choices about justice principles or help you in group discussions. Pay particular attention to patterns in outcomes, unexpected results, and insights about how different principles perform in practice versus theory"
```

**Spanish:**
```
"Devuelve tu memoria actualizada completa incorporando las percepciones de la actividad reciente. Incluye tanto la información importante de tu memoria anterior como los nuevos aprendizajes.

Además de tu memoria y tu actividad reciente, recibirás el resultado de tu elección, que incluye el pago que recibiste, tu asignación de clase y los pagos que habrías recibido según cada principio. Analiza e incorpora esta información a tu memoria actualizada.

Concéntrate en la información que pueda influir en tus elecciones sobre los principios de justicia o ayudarte en las discusiones de grupo. Presta especial atención a los patrones en los resultados, a los resultados inesperados y a las ideas sobre cómo funcionan los diferentes principios en la práctica frente a la teoría."
```

**Mandarin:**
```
"将最近活动中的心得体会完整地更新到您的记忆中。既要包括以前记忆中的重要信息，也要包括新的学习内容。

除了你的记忆和最近的活动，你还会收到你选择的结果，其中包括你得到的回报、你的班级任务以及你在每个原则下会得到的回报。请分析这些信息，并将其纳入你的最新记忆。

重点关注可能会影响你对正义原则的选择或在小组讨论中对你有帮助的信息。请特别注意结果的模式、意外结果，以及不同原则在实践中的表现与理论上的差异。"
```

### 2. Add Conditional Payoff Notification Header
Create a prominent header that appears ONLY when actual payoff information is present:

**English:**
- `"payoff_notification_header": "=== PAYOFF NOTIFICATION ==="`

**Spanish:**
- `"payoff_notification_header": "=== NOTIFICACIÓN DE RECOMPENSA ==="`

**Mandarin:**
- `"payoff_notification_header": "=== 收益通知 ==="`

**Implementation Logic:**
```python
# Only add header when earnings_display is present
if earnings_display:
    round_content = f"{language_manager.get('memory_field_labels.payoff_notification_header')}\n{round_content}"
```

### Implementation Steps

1. **Update English prompts** (`translations/english_prompts.json`)
   - Add new `payoff_notification_header` in the `memory_field_labels` section
   - Modify all 8 memory update prompt templates with enhanced instruction

2. **Update Spanish prompts** (`translations/spanish_prompts.json`)
   - Add translated `payoff_notification_header`
   - Update all memory prompt templates with Spanish enhanced instruction

3. **Update Mandarin prompts** (`translations/mandarin_prompts.json`)
   - Add translated `payoff_notification_header`
   - Update all memory prompt templates with Mandarin enhanced instruction

4. **Update Phase 1 Manager** (`core/phase1_manager.py`)
   - Add conditional header logic in application round payoff display (around line 666)
   - Headers only appear when earnings_display is present
   - Use implementation logic: `if earnings_display: round_content = f"{header}\n{round_content}"`

5. **Fix Round Counter Bug** (`core/phase1_manager.py`)
   - Add missing `round_number` and `phase` parameters to all 6 memory update calls
   - This fixes the issue where round counter shows 0 during memory updates
   - Ensures proper template selection based on round and phase

6. **Comprehensive Testing Strategy**
   - **Core Functionality**: Run existing memory update test suites
   - **Multilingual Verification**: Test prompt display in all 3 languages
   - **Round Counter Validation**: Verify correct round numbers in memory updates
   - **Memory Length Monitoring**: Ensure enhanced prompts don't exceed token limits
   - **Conditional Header Logic**: Test headers appear only with payoff information
   - **Agent Behavior Analysis**: Compare memory content quality pre/post implementation
   - **Regression Testing**: Ensure no existing functionality is broken
   - **Fallback Planning**: Include rollback procedure if issues arise

## Files to Modify

- `/translations/english_prompts.json` (lines 80-88 for memory prompts, memory_field_labels section for header)
- `/translations/spanish_prompts.json` (corresponding memory prompt sections, memory_field_labels section for header)
- `/translations/mandarin_prompts.json` (corresponding memory prompt sections, memory_field_labels section for header)
- `/core/phase1_manager.py` (Phase 1 application round payoff display logic around line 666, plus round counter bug fixes on lines ~212, ~267, ~290, ~315, ~376, ~398)

## Key Principles

- **Simple Enhancement**: Add one sentence to highlight payoff attention
- **Preserve Existing Structure**: Don't change the overall prompt format
- **Maintain Consistency**: Apply the same enhancement pattern to all templates
- **Cultural Sensitivity**: Adapt language appropriately for each translation

## Round Counter Bug Analysis (CRITICAL FIX)

### Root Cause
All `MemoryManager.prompt_agent_for_memory_update` calls in Phase1Manager are missing the `round_number` and `phase` parameters. These parameters are required for:
- Proper template selection (e.g., first_round templates for Phase 2)
- Correct round counter display in memory prompts
- Phase-specific memory guidance

### Current Broken Calls (6 locations in core/phase1_manager.py):
1. **Line ~267**: Initial ranking memory update
2. **Line ~290**: Detailed explanation memory update
3. **Line ~315**: Post-explanation ranking memory update
4. **Line ~376**: Application rounds memory update
5. **Line ~398**: Final ranking memory update
6. **Line ~212**: Retry experience memory update

### Fix Required
Add these two parameters to all calls:
```python
round_number=context.round_number,
phase="phase_1"
```

## Expected Outcome

- **Enhanced Principle-Outcome Awareness**: Agents will be more likely to explicitly consider how different principles affect their results, leading to better integration of outcome experiences into their reasoning about justice principles.
- **Contextual Payoff Highlighting**: Headers will prominently display payoff notifications only when relevant, providing visual emphasis without noise.
- **Fixed Round Counter**: Round numbers will display correctly in memory updates instead of showing 0.
- **Proper Template Selection**: Memory update prompts will use the correct templates based on round and phase context.

### Risk Mitigation & Monitoring

**Low-Risk Factors** (monitoring recommended):
- **Prompt Length**: Enhanced instructions add ~25 words - monitor for any token limit issues
- **Cultural Adaptation**: Principle-focused language designed to be culturally neutral across all languages
- **Conditional Logic**: Headers only appear with actual payoff information, preventing unnecessary noise

**Success Metrics**:
- Memory updates reference principle-outcome relationships more frequently
- Round counters display correctly (no more "0" displays)
- No regression in memory update success rates
- Headers appear consistently in payoff contexts across all languages

**Rollback Plan**:
- If testing reveals issues: revert memory prompt changes first, keep round counter fixes
- If prompt length becomes problematic: shorten enhancement sentence while preserving key guidance
- All changes are additive and can be individually rolled back without affecting core functionality

## Plan Refinements Based on Expert Review

### Expert Review Process ✅
This plan was reviewed by a specialized plan-reviewer agent who provided comprehensive feedback and **approved the plan with minor refinements**. The review confirmed:
- ✅ Technical approach is sound and efficient
- ✅ Scope is appropriately sized (not over-engineered)
- ✅ Round counter bug analysis is accurate
- ✅ Implementation sequence is logical and safe
- ✅ Approach aligns with existing architecture patterns

### Key Refinements Made:

**1. Conditional Header Logic** *(Major Improvement)*
- **Original**: Headers on all Phase 1 memory updates
- **Refined**: Headers only when earnings_display is present
- **Justification**: More precise targeting reduces noise, improves user experience

**2. Enhanced Testing Strategy** *(Critical Addition)*
- **Added**: Memory length validation, agent behavior analysis, conditional logic testing
- **Justification**: Addresses testing gaps identified by expert review, ensures comprehensive validation

**3. User-Specified Prompt Enhancement** *(Comprehensive Improvement)*
- **Original**: Brief mention of payoff attention
- **User-Requested**: Detailed 3-paragraph instruction with explicit payoff analysis guidance
- **Justification**: User provided specific wording that comprehensively addresses payoff awareness with analytical focus

**4. Risk Mitigation Framework** *(Proactive Safeguards)*
- **Added**: Success metrics, rollback procedures, monitoring recommendations
- **Justification**: Expert review highlighted need for comprehensive risk management

### Implementation Confidence: HIGH ✅

**Reviewer Verdict**: "This is a **well-crafted, appropriately scoped plan** that demonstrates deep understanding of the codebase and follows simplicity principles. Execute this plan with the suggested refinements."

**Final Assessment**: Ready for implementation with expert-validated approach, comprehensive testing strategy, and robust risk mitigation measures in place.