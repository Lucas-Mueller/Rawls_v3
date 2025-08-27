# Utility Agent Adaptation Plan: Academic Integrity Updates

## Overview

This document provides a comprehensive plan for adapting utility agent prompts to align with the updated participant agent prompts after implementing academic integrity improvements. This ensures proper parsing, validation, and system functionality when participants use the updated, more faithful-to-original prompts.

**Prerequisites:** Implementation Plan: Academic Integrity Updates must be completed first  
**Estimated Time:** 1.5-2 hours  
**Risk Level:** Medium (parsing failures could break experiment functionality)  
**Files to Modify:** `translations/english_prompts.json` (utility agent sections)

---

## Current State Analysis

### Key Changes from Academic Integrity Updates:
1. **Justice principle definitions** now use complete original handbook wording (longer, more detailed)
2. **"Explain your reasoning clearly"** removed from ranking prompts
3. **Combined stakes explanation** includes both original and AI emphasis
4. **Personality maintenance reminders** removed while keeping descriptions

### Utility Agent Functionality:
- **Parse principle choices** from participant responses
- **Validate constraint specifications** for principles c and d
- **Detect voting intentions** in complex mode discussions
- **Parse preference statements** in simple mode
- **Format improvement and re-prompting** when parsing fails
- **Validate rankings** and consensus outcomes

---

## Impact Analysis: What Needs Updating

### ✅ **No Changes Required**
These utility functions will continue to work correctly:
- **Vote intention detection** - works with natural language patterns
- **Agreement detection** - works with response patterns
- **Constraint amount parsing** - works with dollar amount extraction
- **Consensus validation** - works with discussion content analysis

### ⚠️ **Minor Updates Needed**
These functions need small adjustments:
- **Secret ballot requests** - should include full principle definitions for clarity
- **Voting confirmation requests** - should reference updated stakes explanation
- **Constraint re-prompt messages** - should use fuller principle descriptions

### 🔄 **Major Updates Required**
These functions need significant updates:
- **Principle choice parsing examples** - must reflect longer participant responses
- **Format improvement prompts** - must account for longer principle descriptions
- **Preference detection patterns** - must handle references to full principle text

---

## Implementation Plan

### Phase 1: Update Secret Ballot and Voting Prompts (30 minutes)

#### 1.1 Update Secret Ballot Request

**Current:** Short principle descriptions
**Target:** `utility_secret_ballot_request`

**New Implementation:**
```json
"utility_secret_ballot_request": "VOTING SESSION - SECRET BALLOT\n\nPlease cast your secret ballot by selecting your preferred justice principle:\n\n(a) Maximizing the floor income: The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society.\n\n(b) Maximizing the average income: The most just distribution of income is that which maximizes the average income in the society. For any society maximizing the average income maximizes the total income in the society.\n\n(c) Maximizing the average income with a floor constraint: The most just distribution of income is that which maximizes the average income only after a certain specified minimum income is guaranteed to everyone. You MUST specify the constraint amount in dollars.\n\n(d) Maximizing the average income with a range constraint: The most just distribution of income is that which attempts to maximize the average income only after guaranteeing that the difference between the poorest and the richest individuals is not greater than a specified amount. You MUST specify the constraint amount in dollars.\n\nYour ballot is completely secret and will not be revealed to other participants.\n\nFormat your response as: \"My ballot choice is [principle] [with constraint if applicable]\"\n\nExample: \"My ballot choice is principle c with a floor constraint of $15,000\""
```

#### 1.2 Update Constraint Re-prompting

**Target:** `utility_constraint_re_prompt`

**Enhanced Version:**
```json
"utility_constraint_re_prompt": "\n{participant_name}, you chose the \"{principle_name}\" principle, but you did not specify the {constraint_type} constraint amount.\n\nReminder about your chosen principle:\n- Floor constraint: Maximizes average income only after guaranteeing everyone receives at least a specified minimum income\n- Range constraint: Maximizes average income while ensuring the difference between richest and poorest does not exceed a specified amount\n\nPlease specify the dollar amount for your {constraint_type} constraint.\n\nFor example:\n- Floor constraint: \"I choose maximizing average with a floor constraint of $15,000\"\n- Range constraint: \"I choose maximizing average with a range constraint of $20,000\""
```

---

### Phase 2: Update Principle Choice Parsing (45 minutes)

#### 2.1 Enhanced Principle Choice Parser

**Target:** `utility_llm_parse_principle_choice`

**Key Updates:**
- Recognize references to full principle descriptions
- Handle longer, more detailed responses
- Maintain existing parsing accuracy

**Updated Implementation:**
```json
"utility_llm_parse_principle_choice": "Analyze this ballot response and extract:\n\n1. Which principle they chose (a, b, c, or d)\n2. For principles c and d only: extract any constraint amount in dollars\n\nResponse: \"{response}\"\n\nThe four principles are:\n(a) Maximizing floor income - focuses on the worst-off individual, maximizing the lowest income\n(b) Maximizing average income - maximizes total income in society\n(c) Maximizing average with floor constraint - maximizes average while guaranteeing minimum income (needs constraint amount)\n(d) Maximizing average with range constraint - maximizes average while limiting income gap (needs constraint amount)\n\nParticipants may reference principles using:\n- Letters: a, b, c, d\n- Short names: floor, average, floor constraint, range constraint\n- Full descriptions: \"maximizes the floor income\", \"considers only the welfare of the worst-off\", \"guarantees minimum income\", \"limits income differences\"\n- Original handbook language: \"most just distribution\", \"ensures individuals at the bottom\", \"difference between poorest and richest\"\n\nReturn in format:\nPRINCIPLE: [a/b/c/d]\nCONSTRAINT: [dollar amount if principles c or d, otherwise \"none\"]\nCERTAINTY: [very_unsure/unsure/sure/very_sure]\n\nExamples:\n- \"My ballot choice is principle c with a floor constraint of $15,000\" → PRINCIPLE: c | CONSTRAINT: 15000 | CERTAINTY: sure\n- \"I choose the principle that considers only the welfare of the worst-off\" → PRINCIPLE: a | CONSTRAINT: none | CERTAINTY: sure\n- \"Maybe the one that maximizes average income?\" → PRINCIPLE: b | CONSTRAINT: none | CERTAINTY: unsure"
```

#### 2.2 Enhanced Preference Statement Parser

**Target:** `utility_llm_parse_preference_statement`

**Key Updates:**
- Handle references to full principle descriptions
- Recognize original handbook language
- Maintain precision in preference detection

**Updated Implementation:**
```json
"utility_llm_parse_preference_statement": "Analyze this participant statement to detect if they are stating a preference for a justice principle (SIMPLE MODE).\n\nStatement to analyze: \"{statement}\"\n\nLook for explicit preference expressions in various forms:\n- Direct: \"My preference is [principle]\", \"I prefer [principle]\"\n- Choice: \"I choose [principle]\", \"I select [principle]\"\n- Support: \"I support [principle]\", \"I favor [principle]\"\n- Decision: \"I decide on [principle]\", \"My decision is [principle]\"\n- Commitment: \"I'm going with [principle]\", \"I'll go with [principle]\"\n\nPrinciples can be referenced as:\n- Letters: a, b, c, d\n- Options: principle a, option b, choice c\n- Short names: maximizing floor, maximizing average, floor constraint, range constraint\n- Descriptions: highest minimum income, best average income, average with floor, average with limits\n- Original handbook language: \"most just distribution\", \"welfare of the worst-off\", \"ensures individuals at the bottom\", \"difference between poorest and richest\", \"maximizes total income in society\"\n\nFor constraint principles, look for constraint amounts:\n- \"principle c with floor constraint of $15,000\"\n- \"maximizing average with range constraint of 20000\"\n- \"option d with a $25k range limit\"\n- \"ensuring minimum income of $18,000 for everyone\"\n- \"limiting gap between rich and poor to $22,000\"\n\nExamples of preference statements:\n✅ \"My preference is principle a\"\n✅ \"I prefer the principle that considers only the welfare of the worst-off\"\n✅ \"I choose the most just distribution that maximizes the floor income\"\n✅ \"My preference is maximizing average while ensuring individuals at the bottom receive $18,000\"\n✅ \"I support the principle that guarantees minimum income with constraint of $22,000\"\n\nExamples of NON-preference statements:\n❌ \"I think the floor principle is interesting\" (discussion, not commitment)\n❌ \"What about maximizing average?\" (question, not preference)\n❌ \"The welfare approach might work\" (speculation, not commitment)\n❌ \"I'm still considering the options\" (deliberation, not choice)\n\nIf you detect a clear preference statement, respond with:\nPREFERENCE_DETECTED: [principle and details]\n\nExample responses:\n- \"My preference is principle a\" → PREFERENCE_DETECTED: maximizing_floor\n- \"I prefer the principle that considers welfare of worst-off\" → PREFERENCE_DETECTED: maximizing_floor\n- \"I choose maximizing average with floor constraint of $15,000\" → PREFERENCE_DETECTED: maximizing_average_floor_constraint with constraint of $15,000\n\nIf no clear preference is stated, respond with:\nNO_PREFERENCE_DETECTED\n\nBe conservative - only detect explicit preference commitments, not general discussion."
```

---

### Phase 3: Update Format Improvement Prompts (30 minutes)

#### 3.1 Enhanced Format Improvement for Choices

**Target:** `utility_format_improvement_choice`

**Updated Implementation:**
```json
"utility_format_improvement_choice": "\nThe following response needs to be reformatted for clear principle choice extraction:\n\nOriginal response: \"{response}\"\n\nPlease rewrite this to clearly state:\n1. Which principle they chose (a, b, c, or d) using either:\n   - Letter: \"principle a\", \"option b\", etc.\n   - Description: \"maximizing floor income\", \"maximizing average income\", etc.\n   - Original language: \"the most just distribution that maximizes the floor\", etc.\n\n2. If they chose c or d, the specific constraint amount in dollars\n\n3. Their certainty level (very_unsure, unsure, sure, very_sure)\n\n4. Their reasoning (optional, as explicit reasoning requirements have been removed)\n\nThe four principles for reference:\n(a) Maximizing floor income - focuses on worst-off individual\n(b) Maximizing average income - maximizes total income in society\n(c) Maximizing average with floor constraint - requires minimum income specification\n(d) Maximizing average with range constraint - requires income gap limit specification\n\nFormat as: \"I choose [principle] [with constraint if applicable]. I am [certainty level] about this choice [optional reasoning].\"\n\nExamples:\n- \"I choose principle a. I am sure about this choice.\"\n- \"I choose maximizing average with floor constraint of $15,000. I am very sure about this choice.\"\n- \"I choose the principle that considers welfare of the worst-off. I am sure about this choice.\""
```

#### 3.2 Enhanced Format Improvement for Rankings

**Target:** `utility_format_improvement_ranking`

**Updated Implementation:**
```json
"utility_format_improvement_ranking": "\nThe following response needs to be reformatted for clear ranking extraction:\n\nOriginal response: \"{response}\"\n\nPlease rewrite this as a numbered list ranking all 4 principles from best (1) to worst (4):\n\n1. [principle name or description]\n2. [principle name or description]\n3. [principle name or description]\n4. [principle name or description]\n\nOverall certainty: [certainty level]\n\nPrinciples can be referenced using:\n- Short names: maximizing floor, maximizing average, floor constraint, range constraint\n- Full descriptions: \"maximizing floor income\", \"maximizing average income with floor constraint\", etc.\n- Original handbook language: \"most just distribution that maximizes floor income\", etc.\n\nNote: Explicit reasoning explanations are no longer required, but may be included if provided.\n\nExample format:\n1. Maximizing floor income\n2. Maximizing average with floor constraint\n3. Maximizing average income\n4. Maximizing average with range constraint\n\nOverall certainty: sure"
```

---

### Phase 4: Update Validation Logic (15 minutes)

#### 4.1 Enhanced Validator Instructions

**Target:** `utility_validator_instructions`

**Updated Implementation:**
```json
"utility_validator_instructions": "\nYou are a validator agent for the Frohlich Experiment.\n\nYour task is to validate parsed responses for completeness and correctness:\n\n1. Constraint Validation: If a participant chooses a constraint principle\n   (maximizing_average_floor_constraint or maximizing_average_range_constraint),\n   they MUST specify a constraint amount. Accept various reference formats:\n   - Letters: principle c, principle d\n   - Names: floor constraint, range constraint\n   - Descriptions: \"maximizing average with floor constraint\", etc.\n   - Original handbook language: \"guaranteeing minimum income\", \"limiting income differences\", etc.\n\n2. Ranking Validation: Complete rankings must include all 4 principles with ranks 1-4.\n   Accept various principle reference formats as listed above.\n\n3. Data Integrity: All required fields must be present and valid.\n   Note: Reasoning fields are now optional (explicit reasoning requirements removed).\n\n4. Principle Recognition: Validate that principle references correctly map to the four core principles:\n   - Maximizing floor (principle a)\n   - Maximizing average (principle b)\n   - Maximizing average with floor constraint (principle c)\n   - Maximizing average with range constraint (principle d)\n\nReturn is_valid=True if validation passes, is_valid=False with specific errors if not.\n\nBe flexible with language variations while maintaining accuracy in principle identification."
```

---

## Testing and Validation Strategy

### Test Case 1: Full Principle Description Parsing (20 minutes)
**Scenario:** Participants use complete original handbook language
**Test:** 
- "I prefer the most just distribution of income that maximizes the floor income in society"
- "My choice is the principle that considers only the welfare of the worst-off individual"
**Expected:** Correct parsing as principle a (maximizing_floor)

### Test Case 2: Constraint Specification with Full Language (15 minutes)
**Scenario:** Participants reference constraints using original descriptions
**Test:**
- "I choose maximizing average while guaranteeing individuals at the bottom receive $15,000"
- "My preference is ensuring income differences between rich and poor don't exceed $20,000"
**Expected:** Correct principle and constraint extraction

### Test Case 3: Mixed Language References (15 minutes)
**Scenario:** Participants mix short names and full descriptions
**Test:**
- "I prefer principle a, which focuses on the welfare of the worst-off"
- "Maximizing average with floor constraint - the one that ensures minimum income of $18,000"
**Expected:** Successful parsing despite mixed terminology

### Test Case 4: Ranking Without Explicit Reasoning (10 minutes)
**Scenario:** Rankings without "explain your reasoning clearly" prompts
**Test:** 
- Simple numbered lists without detailed explanations
- Rankings with brief justifications (still allowed)
**Expected:** Successful parsing with optional reasoning fields

---

## Implementation Checklist

### Preparation ✅
- [ ] Verify Academic Integrity Updates are fully implemented
- [ ] Backup current utility agent prompts
- [ ] Prepare test cases and validation scenarios

### Phase 1: Voting and Ballot Updates ✅
- [ ] Update `utility_secret_ballot_request` with full principle definitions
- [ ] Update `utility_constraint_re_prompt` with enhanced explanations
- [ ] Update `utility_voting_confirmation_request` if needed
- [ ] Test secret ballot display and constraint prompting

### Phase 2: Principle Choice Parsing ✅
- [ ] Update `utility_llm_parse_principle_choice` with expanded recognition
- [ ] Update `utility_llm_parse_preference_statement` with handbook language
- [ ] Test parsing with various principle reference formats
- [ ] Verify constraint amount extraction accuracy

### Phase 3: Format Improvement ✅
- [ ] Update `utility_format_improvement_choice` with flexible formatting
- [ ] Update `utility_format_improvement_ranking` for optional reasoning
- [ ] Test re-prompting scenarios with updated formats
- [ ] Verify improved format suggestions work correctly

### Phase 4: Validation Logic ✅
- [ ] Update `utility_validator_instructions` with expanded validation rules
- [ ] Test validation with various language formats
- [ ] Verify constraint validation works with full descriptions
- [ ] Confirm ranking validation handles optional reasoning

### Testing and Validation ✅
- [ ] Run Test Case 1: Full principle description parsing
- [ ] Run Test Case 2: Constraint specification with full language
- [ ] Run Test Case 3: Mixed language references
- [ ] Run Test Case 4: Ranking without explicit reasoning
- [ ] Complete end-to-end experiment test
- [ ] Verify no parsing failures or system errors

---

## Risk Mitigation

### High Risk: Parsing Failures
**Mitigation:** 
- Comprehensive testing with various language formats
- Gradual rollout with fallback to current prompts
- Multiple parsing attempts with different strategies

### Medium Risk: Performance Impact
**Mitigation:**
- Monitor parsing response times
- Optimize prompt length while maintaining accuracy
- Cache common parsing patterns

### Low Risk: User Confusion
**Mitigation:**
- Clear constraint specification prompts
- Helpful examples in re-prompting scenarios
- Consistent terminology across all utility prompts

---

## Success Criteria

### Primary Goals:
1. ✅ **Accurate parsing of responses using full principle descriptions**
2. ✅ **Successful constraint extraction with original handbook language**
3. ✅ **Flexible principle recognition across all reference formats**
4. ✅ **Proper handling of optional reasoning in rankings**

### System Integrity:
1. ✅ **No increase in parsing error rates**
2. ✅ **Maintained experiment completion success rates**
3. ✅ **Proper validation of constraint specifications**
4. ✅ **Continued accuracy in consensus detection**

### Enhanced Functionality:
1. ✅ **Better alignment with participant language patterns**
2. ✅ **Improved user experience in ballot casting**
3. ✅ **More natural constraint specification process**
4. ✅ **Robust handling of academic integrity improvements**

---

## Post-Implementation Monitoring

### Week 1: Active Monitoring
- Track parsing success rates across all utility functions
- Monitor constraint specification accuracy
- Check for any unexpected participant language patterns
- Collect feedback on ballot clarity and ease of use

### Week 2-4: Performance Analysis
- Analyze parsing performance with longer principle descriptions
- Review any parsing edge cases or failures
- Document successful language pattern recognition
- Optimize prompts based on real usage patterns

### Ongoing: Maintenance and Improvements
- Regular testing with new participant language variations
- Updates to recognition patterns as needed
- Documentation of effective parsing strategies
- Preparation for potential future academic integrity updates

---

*Utility Agent Adaptation Plan Created: August 27, 2025*  
*Dependency: Implementation Plan: Academic Integrity Updates*  
*Priority: High - Essential for System Functionality*