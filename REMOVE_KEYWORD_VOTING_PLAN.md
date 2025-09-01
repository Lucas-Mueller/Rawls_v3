# Plan: Remove Keyword-Based Voting Triggers

## Executive Summary

This plan outlines the complete removal of keyword-based voting trigger detection from the Frohlich Experiment framework. The system will transition to **prompt-only voting initiation**, where formal voting is triggered exclusively through end-of-round prompts rather than detecting phrases like "Let's vote" in agent statements.

## Current System Analysis

### Keyword-Based Voting Components

1. **Primary Detection System** (`core/phase2_manager.py`):
   - `_is_voting_trigger_phrase()` method
   - Multilingual trigger phrase lists (English, Spanish, Mandarin)
   - Integration in consensus detection loop

2. **Voting Mode Integration**:
   - Complex mode relies on keyword detection
   - Simple mode uses preference detection (unaffected)
   - Hybrid systems in consensus detection

3. **Fallback Systems**:
   - `core/principle_keywords.py` - keyword matching for validation
   - Two-stage voting manager may use keyword fallbacks
   - Language manager voting phrase storage

4. **Configuration Dependencies**:
   - `voting_detection_mode` configuration affects keyword usage
   - Language-specific phrase management

## System-Level Impact Analysis

### **Components Directly Affected**
- `core/phase2_manager.py` - Core voting trigger detection
- `core/two_stage_voting_manager.py` - May have keyword fallbacks  
- `utils/language_manager.py` - Voting trigger phrase translations
- `translations/*.json` - Voting trigger phrase storage
- `core/principle_keywords.py` - Potential voting trigger utilities

### **Components Indirectly Affected**
- Test suites verifying keyword detection behavior
- Documentation mentioning keyword-based voting
- Logging/debugging messages about keyword detection
- Error handling for keyword detection failures

### **Behavioral Changes**
- **Voting initiation becomes purely prompt-driven**
- **Complex mode distinction may need clarification**
- **Multilingual voting phrases become obsolete**
- **Agent statements no longer monitored for voting triggers**

## Implementation Plan

### **Phase 1: Core Removal (High Priority)**

#### **1.1 Remove Primary Detection Method**
**File:** `core/phase2_manager.py`
- **Remove:** `_is_voting_trigger_phrase()` method (lines ~1477-1514)
- **Remove:** All trigger phrase lists (English, Spanish, Mandarin arrays)
- **Impact:** 40+ lines of multilingual phrase detection code

#### **1.2 Update Consensus Detection Loop**
**File:** `core/phase2_manager.py` 
**Location:** `_run_group_discussion()` method, consensus detection section (lines ~564-584)

**Current Logic:**
```python
if config.voting_detection_mode == "complex":
    if self._is_voting_trigger_phrase(statement):  # ← REMOVE THIS
        consensus_via_voting = await self._handle_complex_voting_mode(...)
```

**New Logic:**
```python
if config.voting_detection_mode == "complex":
    # Keyword-based voting removed - only prompt-based voting remains
    # Complex mode voting now occurs exclusively via end-of-round prompts
    pass  # No automatic voting trigger from statements
```

#### **1.3 Update Complex Voting Handler**
**File:** `core/phase2_manager.py`
**Method:** `_handle_complex_voting_mode()`
- **Remove:** Keyword detection logic
- **Simplify:** Method parameters (remove statement analysis)
- **Update:** Documentation to reflect prompt-only triggering

### **Phase 2: Voting System Updates (High Priority)**

#### **2.1 Two-Stage Voting Manager Review**
**File:** `core/two_stage_voting_manager.py`
- **Audit:** Check for keyword-based fallback systems
- **Remove:** Any voting trigger phrase detection
- **Preserve:** Numerical validation systems (these are separate from trigger detection)

#### **2.2 Principle Keywords Module**
**File:** `core/principle_keywords.py`
- **Audit:** Determine if used for voting trigger detection
- **Preserve:** Principle name matching (still needed for preference detection)
- **Remove:** Only voting trigger-related functionality

### **Phase 3: Language & Configuration (Medium Priority)**

#### **3.1 Language Manager Updates**
**File:** `utils/language_manager.py`
- **Remove:** Voting trigger phrase keys/methods
- **Preserve:** All other multilingual content
- **Update:** Method signatures that may reference voting triggers

#### **3.2 Translation File Cleanup**
**Files:** `translations/english.json`, `translations/spanish.json`, `translations/mandarin.json`
- **Remove:** Voting trigger phrase entries
- **Remove:** Keys like `voting_triggers`, `vote_initiation_phrases`, etc.
- **Preserve:** All other translations

#### **3.3 Configuration System**
**Files:** `config/models.py`, configuration YAML files
- **Review:** `voting_detection_mode` setting implications
- **Update:** Documentation for mode differences
- **Consider:** Whether complex/simple mode distinction still makes sense

### **Phase 4: End-of-Round Voting (Critical Path)**

#### **4.1 Strengthen Prompt-Based Voting**
**File:** `core/phase2_manager.py`
**Method:** `_prompt_for_vote_initiation()` (lines ~861-906)
- **Enhance:** Make this the primary voting initiation method
- **Improve:** Error handling and retry logic
- **Optimize:** Timeout and response validation

#### **4.2 Vote Prompting Integration**
**Current Location:** End-of-round voting prompts (lines ~661-685)
- **Verify:** This system works reliably without keyword backup
- **Enhance:** User experience for vote initiation
- **Add:** Logging for vote prompt responses

### **Phase 5: Testing & Validation (High Priority)**

#### **5.1 Test Suite Updates**
**Files:** `tests/unit/test_phase2_manager.py`, `tests/integration/test_voting_*.py`
- **Remove:** Tests verifying keyword detection (`test_voting_trigger_phrases`, etc.)
- **Remove:** Tests for multilingual voting triggers
- **Update:** Tests for prompt-based voting to be more comprehensive

#### **5.2 Integration Testing**
- **Verify:** Complex mode still functions with prompt-only triggering
- **Test:** All language configurations work without keyword detection
- **Validate:** End-of-round prompting covers all voting scenarios

#### **5.3 Regression Testing**
- **Ensure:** Simple mode (preference-based) remains unaffected
- **Verify:** Memory management and discussion flow unchanged
- **Test:** Error handling doesn't rely on removed keyword systems

### **Phase 6: Documentation & Cleanup (Medium Priority)**

#### **6.1 Code Documentation**
- **Update:** Docstrings mentioning keyword-based voting
- **Remove:** Comments about trigger phrase detection
- **Clarify:** Complex vs simple mode differences

#### **6.2 User Documentation**
**Files:** `CLAUDE.md`, `README.md`, architecture docs
- **Remove:** References to "Let's vote" trigger phrases
- **Update:** Voting initiation explanations
- **Clarify:** How agents can initiate voting (prompt-based only)

#### **6.3 Logging & Debug Messages**
- **Remove:** Log messages about keyword detection
- **Update:** Voting initiation logging to reflect prompt-based system
- **Preserve:** All other Phase 2 logging

## Risk Analysis & Mitigation

### **High Risk Areas**

#### **1. Reduced Voting Accessibility**
**Risk:** Agents may not initiate voting as frequently without keywords
**Mitigation:** 
- Strengthen end-of-round vote prompting
- Consider adding mid-round vote prompts
- Monitor voting frequency in test runs

#### **2. Complex Mode Behavioral Change**
**Risk:** Complex mode becomes identical to simple mode for triggering
**Mitigation:**
- Clearly document the new distinction
- Consider renaming modes to reflect prompt-based triggering
- Ensure voting process itself remains different

#### **3. Test Coverage Gaps**
**Risk:** Removing keyword tests may miss voting edge cases
**Mitigation:**
- Expand prompt-based voting test coverage
- Add integration tests for voting accessibility
- Test multilingual vote prompting thoroughly

### **Medium Risk Areas**

#### **1. Configuration Confusion**
**Risk:** `voting_detection_mode` setting may become confusing
**Mitigation:**
- Update configuration documentation
- Consider deprecation warnings for keyword-related settings
- Provide migration guidance

#### **2. Language-Specific Issues**
**Risk:** Some languages may lose voting capability
**Mitigation:**
- Test all supported languages thoroughly
- Verify prompt-based voting works in Spanish and Mandarin
- Ensure number parsing works across cultures

## Implementation Timeline

### **Week 1: Core Removal**
- Remove `_is_voting_trigger_phrase()` method
- Update consensus detection loop
- Remove trigger phrase lists

### **Week 2: System Updates**
- Audit two-stage voting manager
- Update language manager and translations
- Test prompt-based voting extensively

### **Week 3: Testing & Validation**
- Update test suites
- Run comprehensive integration tests
- Validate multilingual functionality

### **Week 4: Documentation & Polish**
- Update all documentation
- Clean up logging messages
- Final regression testing

## Success Criteria

1. **Functional:** All voting functionality works via prompts only
2. **Multilingual:** Spanish, Mandarin, and English experiments work identically
3. **Performance:** No decrease in voting accessibility or success rates
4. **Maintainability:** Codebase is simpler without keyword detection complexity
5. **Backward Compatible:** Existing configurations continue to work

## Post-Implementation Monitoring

### **Metrics to Track**
- Voting initiation frequency in test runs
- Success rate of prompt-based vote initiation
- Agent response quality to vote prompts
- Overall consensus rates before/after change

### **Rollback Plan**
- Maintain git branch with keyword system before removal
- Document any configuration changes needed for rollback
- Keep removed code in separate branch for potential future reference

---

**Implementation Lead:** Development team
**Review Required:** Architecture team, QA team
**Timeline:** 4 weeks
**Priority:** Medium (system improvement, not critical bug fix)