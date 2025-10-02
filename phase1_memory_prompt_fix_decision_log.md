# Phase 1 Memory Prompt Fix - Decision Log

## Date
2025-10-02

## Issue
Memory update prompts in Phase 1 incorrectly reference outcomes ("payoff received", "class assignment", "counterfactual payoffs") during education/ranking rounds where no such outcomes exist.

## Evolution of Solution

### Initial Proposal (Rejected)
**Approach:** Create 12 new templates for Phase 1 education rounds
- 4 new templates per language × 3 languages = 12 new templates
- Update memory_manager.py with detection logic for education vs application rounds
- Keep existing templates for application rounds

**Why Rejected:**
- ✗ Overengineered - creating 12 templates to remove 2 sentences
- ✗ Violates DRY principle
- ✗ High maintenance burden
- ✗ Template duplication increases translation burden

### Plan-Reviewer Alternatives

**Alternative #1 (Conditional Parameters):**
- Add conditional `outcome_instruction` parameters to existing templates
- Memory manager passes empty strings for education, populated for application
- Requires ~20 lines of new code in memory_manager.py

**Alternative #2 (Remove Outcome Text):**
- Simply remove outcome-specific sentences from all templates
- Let `round_content` communicate what's available
- Requires 0 lines of code
- **Issue:** Loses instructional value

### Final Agreed Solution (Alternative #3)

**Approach:** Context-neutral template rewording
- Edit 4 existing templates per language (12 total edits, NOT 12 new templates)
- Replace outcome-specific text with context-neutral guidance
- Requires 0 lines of code changes

**Text Change:**

**OLD (problematic):**
```
Besides your memory and your recent activity you will receive the outcome of your
choice which includes the payoff you received, your class assignment and the payoffs
you would have received under each principle. Please analyze and incorporate this
information into your updated memory.
```

**NEW (context-neutral):**
```
Review the information provided below alongside your current memory. Focus on
incorporating insights that might influence your choices about justice principles
or help in group discussions.
```

## Why Alternative #3 Was Chosen

### Comparison Matrix

| Criterion | Initial Plan | Alt #1 | Alt #2 | **Alt #3** |
|-----------|-------------|--------|--------|------------|
| Templates to modify | 16 total | 4 + 2 fragments | 4 | **4** |
| Code changes | +15 lines | +20 lines | 0 | **0** |
| New templates | 12 | 0 | 0 | **0** |
| Instructional value | High | High | Low | **High** |
| Context-neutral | N/A | No | Yes | **Yes** |
| Maintenance burden | Very High | Medium | Low | **Low** |
| Complexity | High | Medium | Low | **Low** |

### Decision Rationale

**Alternative #3 is optimal because it:**

1. **Solves the root problem**
   - Templates no longer promise non-existent outcomes
   - Context-neutral language works for education AND application rounds

2. **Maximizes simplicity**
   - Zero code changes (no logic in memory_manager.py)
   - Zero new templates (just edit existing ones)
   - Minimal scope: 12 text edits across 3 files

3. **Preserves instructional value**
   - Still tells agents to "review" and "focus on incorporating"
   - Provides actionable guidance without false promises
   - Better than Alt #2 which removes guidance entirely

4. **Minimizes maintenance**
   - Single source of truth for each template
   - No conditional logic to maintain
   - No template proliferation

5. **Universal applicability**
   - "insights that might influence your choices" works for:
     - Education rounds: insights from learning
     - Application rounds: insights from outcomes
   - No special cases or edge cases

## Critical Discussion Points

### Question 1: Why not just remove the text (Alt #2)?

**Answer:** The text serves two purposes:
1. **Informational**: Describes what's in `round_content` (FALSE for education rounds)
2. **Instructional**: Tells agents what to DO with the information (VALUABLE)

Alt #2 preserves truthfulness but loses instructional value.
Alt #3 preserves BOTH truthfulness AND instructional value.

### Question 2: Why not use conditional parameters (Alt #1)?

**Answer:** Unnecessary complexity for minimal gain.
- Adds ~20 lines of conditional logic
- Requires parameter management
- Creates mental overhead for maintainers
- Solves the same problem as simple text rewording

**Principle:** Don't solve with code what you can solve with better UX copy.

### Question 3: Won't generic language be less helpful?

**Answer:** No, because:
- The second paragraph already provides specific guidance about patterns/outcomes
- The `round_content` itself contains the actual specific information
- Generic framing ("insights that might influence your choices") encompasses all scenarios
- Agents benefit from truthful prompts more than specific-but-false ones

## Implementation Impact

### What Changes
- 12 template text edits (4 per language × 3 languages)
- JSON files only, no Python code

### What Stays the Same
- Memory manager logic (utils/memory_manager.py)
- Template selection logic
- Number of templates (4 per language)
- Template structure and placeholders

### Backward Compatibility
- ✅ Pure improvement - no breaking changes
- ✅ Existing experiments unaffected
- ✅ All existing code continues to work

## Lessons Learned

### From This Process

1. **Start with the simplest solution**
   - I jumped to "create new templates" without considering "improve existing templates"
   - Template duplication should be a last resort, not first choice

2. **Question the framing**
   - The problem wasn't "we need different templates for different contexts"
   - The problem was "these templates make false promises"
   - Reframing led to simpler solution

3. **Preserve value while fixing bugs**
   - Don't throw out instructional guidance just to fix factual errors
   - Find wording that's both truthful AND helpful

4. **Code is a liability**
   - Zero code changes is better than well-designed code changes
   - Solve in UX/content layer when possible

### Process Value

The structured review process with plan-reviewer agent:
- ✅ Caught overengineering before implementation
- ✅ Forced consideration of alternatives
- ✅ Led to genuinely simpler solution
- ✅ Validated decision through critical discussion

## Next Steps

1. Implement the 12 template edits as specified in `phase1_memory_prompt_fix_plan.md`
2. Validate JSON syntax in all 3 translation files
3. Run Phase 1 test to verify prompts look correct
4. Optional: Get Spanish/Mandarin text reviewed by native speakers

## Sign-off

**Decision:** Implement Alternative #3 (Context-Neutral Template Rewording)

**Rationale:** Genuinely simplest solution that fully addresses the problem while preserving instructional value

**Approved by:** Structured review process with critical evaluation
