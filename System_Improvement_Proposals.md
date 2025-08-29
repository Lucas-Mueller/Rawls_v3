# System Improvement Proposals: Utility Agent Enhancement

## Executive Summary

Following the analysis of 22 test failures, this document proposes system improvements that adhere to the project's philosophy of **utility agent-first processing** rather than hardcoded regex patterns. The core philosophy is to enhance the UtilityAgent's intelligence and prompt engineering to handle complex multilingual parsing tasks.

## Core Philosophy Adherence

**"Rather use a utility agent to extract information or if one already exists, modify the prompt to the utility agents. Hardcoded logic like regex and json parsing is less good and only suitable for some cases."**

All proposed improvements focus on:
- Enhancing UtilityAgent prompt engineering for multilingual capabilities
- Adding missing methods with AI-driven parsing logic
- Leveraging the existing LLM-based parsing infrastructure
- Avoiding regex-based solutions for complex text analysis

## Improvement Proposals

### 1. **Critical Priority: Add Missing UtilityAgent Methods**

#### 1.1 Add `_extract_constraint_amount_flexible` Method
**Root Cause**: Method referenced by Phase2Manager and 6 failing tests but doesn't exist.

**Proposal**: Add method that leverages existing `parse_constraint_amount_multilingual`:

```python
async def _extract_constraint_amount_flexible(self, constraint_text: str) -> Optional[int]:
    """
    Flexible constraint amount extraction using utility agent intelligence.
    This method wraps the existing multilingual parsing infrastructure.
    """
    await self.async_init()
    
    if not constraint_text or constraint_text.strip() == "":
        return None
    
    # Detect language hint for better parsing
    language_hint = self._detect_language_hint(constraint_text)
    
    # Use existing multilingual parsing with enhanced error handling
    try:
        amount = await self.parse_constraint_amount_multilingual(constraint_text, language_hint)
        if amount and amount > 0:
            return amount
        return None
    except Exception as e:
        logger.warning(f"Flexible constraint extraction failed: {e}")
        return None
```

**Benefits**: 
- Reuses existing LLM-based parsing infrastructure
- Maintains consistency with project architecture
- No hardcoded regex patterns

#### 1.2 Add `parse_participant_preference` Method
**Root Cause**: Spanish tests expect this method but it doesn't exist.

**Proposal**: Add method that combines preference detection with constraint parsing:

```python
async def parse_participant_preference(self, statement: str, participant_name: str = None) -> Optional[PrincipleChoice]:
    """
    Parse participant preference statements with constraint amounts.
    Uses LLM-based analysis for multilingual support.
    """
    await self.async_init()
    
    # Use existing preference detection logic
    preference = await self.detect_preference_statement(statement)
    
    if preference:
        # If constraint amount is missing but principle requires it, try enhanced extraction
        if (preference.constraint_amount is None and 
            preference.principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                                   JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]):
            
            # Use flexible constraint extraction
            extracted_amount = await self._extract_constraint_amount_flexible(statement)
            if extracted_amount:
                # Create new preference with extracted amount
                return PrincipleChoice(
                    principle=preference.principle,
                    constraint_amount=extracted_amount,
                    certainty=preference.certainty,
                    reasoning=preference.reasoning
                )
        
        return preference
    
    return None
```

### 2. **High Priority: Enhance Spanish Constraint Parsing**

#### 2.1 Improve `parse_constraint_amount_multilingual` Prompt
**Root Cause**: All 11 Spanish constraint parsing tests return None instead of expected amounts.

**Current Issues**:
- Spanish terminology not properly handled
- European number formats (15.000) not parsed correctly  
- Spanish currency symbols and words not recognized
- Spanish number words (quince mil) not understood

**Proposal**: Enhance the parsing prompt in the method with Spanish-specific expertise:

```python
# Enhanced parsing prompt with comprehensive Spanish support
parsing_prompt = f"""You are an expert at parsing constraint amounts from multilingual text.

PARSE CONSTRAINT AMOUNT from: "{constraint_text}"
Language hint: {language_hint or "unknown"}

CRITICAL SPANISH LANGUAGE SUPPORT:
1. **Spanish Terminology Recognition**:
   - "restricción" = constraint/restriction
   - "límite" = limit 
   - "tope" = cap/ceiling
   - "cota" = bound
   - "barrera" = barrier
   - "frontera" = boundary
   - "umbral" = threshold
   - "máximo" = maximum
   - "limitación" = limitation
   - "condición" = condition

2. **Spanish Number Formats**:
   - European format: €15.000 = 15000 (period as thousands separator)
   - Latin American format: $15,000 = 15000 (comma as thousands separator)
   - Mixed format: €2.250.500 = 2,250,500
   - Decimal handling: €125.750,25 = 125750 (ignore decimal part)

3. **Spanish Currency Support**:
   - Euros: €, EUR, euros, euro
   - Pesos: $, MXN, ARS, COP, pesos, peso
   - US Dollars: $, USD, dólares, dólar

4. **Spanish Number Words**:
   - "quince mil" = 15000 (fifteen thousand)
   - "veinte mil" = 20000 (twenty thousand)
   - "cinco mil" = 5000 (five thousand)
   - "diez mil" = 10000 (ten thousand)
   - "treinta mil" = 30000 (thirty thousand)
   - "veinticinco mil" = 25000 (twenty-five thousand)
   - "cincuenta mil" = 50000 (fifty thousand)
   - "15 mil" = 15000 (numeric + mil)
   - "2.5 mil" = 2500 (decimal + mil)

5. **Spanish Prepositions**:
   - "con restricción de" = with constraint of
   - "bajo restricción de" = under constraint of  
   - "dentro del límite de" = within limit of
   - "sujeto a restricción de" = subject to constraint of
   - "mediante restricción de" = through constraint of
   - "según restricción de" = according to constraint of
   - "por restricción de" = by constraint of

EXAMPLES OF SPANISH CONSTRAINTS:
✓ "restricción de €15.000" → 15000
✓ "límite de $15,000" → 15000  
✓ "tope de quince mil euros" → 15000
✓ "con restricción de €15000" → 15000
✓ "barrera de 2.5 mil euros" → 2500
✓ "constraint MXN 45.000" → 45000
✓ "límite de 30 mil pesos" → 30000
✓ "restricción €18.500,50" → 18500
✗ "sin restricciones" → NONE
✗ "ilimitado" → NONE

PARSING RULES:
1. Extract the numeric amount ignoring currency symbols
2. Handle both European (15.000) and Latin American (15,000) formats
3. Convert number words to digits
4. Ignore decimal parts for constraint amounts
5. Return only positive integer amounts
6. Return NONE if no valid amount found

Response format: Return ONLY the numeric amount as integer, or "NONE".
Do not include explanations, currency symbols, or formatting.

Response:"""
```

#### 2.2 Add Spanish Language Detection Enhancement
**Proposal**: Improve `_detect_language_hint` method with comprehensive Spanish detection:

```python
def _detect_language_hint(self, statement: str) -> str:
    """Enhanced language detection with comprehensive Spanish support."""
    statement_lower = statement.lower()
    
    # Enhanced Spanish indicators
    spanish_words = [
        'restricción', 'límite', 'tope', 'barrera', 'frontera', 'umbral', 'máximo',
        'limitación', 'condición', 'cota', 'euros', 'pesos', 'mil', 'con', 'de', 
        'sin', 'condiciones', 'limitaciones', 'bajo', 'dentro', 'sujeto', 'mediante',
        'según', 'por', 'quince', 'veinte', 'cinco', 'diez', 'treinta', 'veinticinco',
        'cincuenta', 'dólares', 'euro', 'peso'
    ]
    
    # Count Spanish indicators for confidence
    spanish_count = sum(1 for word in spanish_words if word in statement_lower)
    
    if spanish_count >= 2:  # Higher confidence threshold
        return "spanish"
    elif spanish_count == 1 and any(word in statement_lower for word in ['restricción', 'límite', 'tope']):
        return "spanish"  # Single strong indicator
    
    # Rest of method unchanged...
```

### 3. **Medium Priority: Fix Test Infrastructure Issues**

#### 3.1 Fix Mixed Language Test Configuration
**Root Cause**: 3 tests failing due to single-agent configuration validation errors.

**Proposal**: Update test configuration to respect minimum agent requirements:

```python
# In test files, replace:
# config = ExperimentTestFixture.create_minimal_config(num_agents=1)

# With:
config = ExperimentTestFixture.create_minimal_config(num_agents=2)
# Then modify test logic to focus on single agent behavior within multi-agent context
```

#### 3.2 Fix Async/Await Usage in Tests
**Root Cause**: Incorrect await usage in `test_spanish_english_chinese_mixed_discussion`.

**Proposal**: Fix await syntax:

```python
# Replace:
result = await mock_phase2.run_phase2.return_value

# With:
result = mock_phase2.run_phase2.return_value
# or if truly async:
result = await mock_phase2.run_phase2()
```

### 4. **Medium Priority: Improve Quarantine Detection**

#### 4.1 Enhance Multilingual Letter Detection
**Root Cause**: Quarantine logic only detects 2 out of 4 expected problematic messages.

**Proposal**: Enhance the quarantine detection in Phase2Manager through utility agent intelligence:

Add to UtilityAgent:
```python
async def detect_problematic_content_multilingual(self, statement: str) -> Optional[Dict[str, Any]]:
    """
    Detect problematic content using utility agent intelligence.
    Replaces regex-based quarantine detection.
    """
    await self.async_init()
    
    detection_prompt = f"""Analyze this statement for problematic content:

Statement: "{statement}"

DETECT these problems:
1. **Letter-based principle references** (CRITICAL):
   - English: "principle a", "principle b", "choose a", "prefer b"
   - Spanish: "principio a", "principio b", "elijo a", "prefiero b"  
   - Mixed: "principle a", "选择a", any single letters after preference words

2. **Premature voting intentions**:
   - "Let's vote for a", "Votemos por b", "我投票给a"
   - Combining letter reference with voting language

3. **Invalid preference expressions**:
   - Any preference statement using single letters
   - Mixed language letter references

EXAMPLES:
✓ "I choose principle a" → PROBLEM: letter_reference
✓ "Mi elección es principio b" → PROBLEM: letter_reference  
✓ "Let's vote for option b" → PROBLEM: letter_reference + voting
✓ "Votemos por la opción a" → PROBLEM: letter_reference + voting
✗ "I prefer maximizing floor income" → NO_PROBLEM
✗ "Mi elección es maximización del ingreso promedio" → NO_PROBLEM

If problem detected, respond with:
PROBLEM_DETECTED: [type] - [reason]

If no problem, respond with:
NO_PROBLEM_DETECTED

Response:"""

    try:
        result = await run_without_tracing(self.parser_agent, detection_prompt)
        response = result.final_output.strip()
        
        if "PROBLEM_DETECTED:" in response:
            parts = response.split("PROBLEM_DETECTED:")[1].strip().split(" - ", 1)
            return {
                "type": parts[0].strip(),
                "reason": parts[1].strip() if len(parts) > 1 else "Unknown reason",
                "message": statement
            }
        
        return None
        
    except Exception as e:
        logger.warning(f"Problematic content detection failed: {e}")
        return None
```

### 5. **Implementation Priority and Timeline**

#### Phase 1: Critical Missing Methods (Week 1)
1. Add `_extract_constraint_amount_flexible` method
2. Add `parse_participant_preference` method  
3. Test basic functionality

#### Phase 2: Spanish Parsing Enhancement (Week 2)
1. Enhance `parse_constraint_amount_multilingual` prompt
2. Improve `_detect_language_hint` method
3. Test all Spanish parsing scenarios

#### Phase 3: Test Infrastructure Fixes (Week 3)  
1. Fix test configuration issues
2. Fix async/await usage
3. Update quarantine detection

#### Phase 4: Advanced Features (Week 4)
1. Add multilingual quarantine detection
2. Performance optimization
3. Documentation updates

## Expected Outcomes

### Immediate Benefits
- **17 failing tests** (77%) will pass due to enhanced constraint parsing
- **Spanish language support** will be fully functional
- **Missing methods** will be available for system integration

### Long-term Benefits
- **Maintainable architecture** following utility agent paradigm
- **Scalable multilingual support** for future language additions
- **Consistent parsing behavior** across all system components
- **Reduced technical debt** from hardcoded regex patterns

## Risk Assessment

### Low Risk
- Adding missing methods (backwards compatible)
- Enhancing prompts (improves existing functionality)

### Medium Risk  
- Test configuration changes (require validation)
- Prompt modifications (need extensive testing)

### Mitigation Strategies
- **Comprehensive testing** after each phase
- **Gradual rollout** with feature flags if needed
- **Rollback plan** for prompt changes if LLM behavior degrades

## Conclusion

These proposals align with the project's core philosophy of leveraging utility agent intelligence over hardcoded patterns. The phased implementation approach ensures minimal risk while maximizing the improvement of multilingual constraint parsing capabilities.

The focus on Spanish language support addresses the largest category of test failures (11 tests) while the missing method implementations resolve the structural issues causing the remaining failures.

All improvements maintain the existing architecture and enhance rather than replace the current LLM-based parsing approach.