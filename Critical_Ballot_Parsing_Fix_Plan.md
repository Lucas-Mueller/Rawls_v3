# Critical Ballot Parsing Fix Plan

## Executive Summary

Despite achieving 100% test pass rate, **real experiment votes are being systematically misparsed**. Analysis of `experiment_results_20250829_231553.json` reveals agents saying "My ballot choice is maximizing the floor income" but the system parsing this as `maximizing_average_floor_constraint` instead of the correct `maximizing_floor`.

**Root Cause**: Critical gap between test coverage and real-world LLM-based ballot parsing behavior across multiple languages.

## Problem Analysis

### 🔍 Critical Discovery

**What Agents Actually Say (English):**
```
"raw_response": "My ballot choice is maximizing the floor income."
```

**What System Incorrectly Parses:**
```
"assessed_choice": "maximizing_average_floor_constraint"  // ❌ WRONG!
"constraint_amount": null
```

**What It Should Parse:**
```
"assessed_choice": "maximizing_floor"  // ✅ CORRECT
"constraint_amount": null
```

### 🧐 Why Tests Don't Catch This

**The Testing Gap:**
1. **Tests use abstract patterns**: Tests verify mappings like `"maximizing the floor income"` → `"maximizing_floor"` ✅
2. **Real parsing uses LLM prompts**: Actual ballot parsing driven by `utility_llm_parse_principle_choice` prompt
3. **LLM has disambiguation failures**: The parsing prompt lacks clear examples for basic vs. constraint principles

### 🌍 Multilingual Scope

**Same issue likely affects:**

**Spanish Ballots:**
- Agent says: `"Mi elección de voto es maximización del ingreso mínimo"`
- System might parse as: `maximizing_average_floor_constraint` ❌
- Should parse as: `maximizing_floor` ✅

**Mandarin Ballots:**
- Agent says: `"我的投票选择是最大化最低收入"`
- System might parse as: `maximizing_average_floor_constraint` ❌  
- Should parse as: `maximizing_floor` ✅

### 🎯 Utility Agent Philosophy Analysis

**The Core Issue**: Our LLM-based parsing enhanced intelligence but **lacks comprehensive disambiguation examples** for the most fundamental ballot formats across languages.

## Comprehensive Fix Plan

### Phase 4: Critical Multilingual Ballot Parsing Fix

#### 4.1 **Fix English LLM Parsing Prompt** 
**Target**: `translations/english_prompts.json` → `utility_llm_parse_principle_choice`

**Enhancement**: Add comprehensive **disambiguation examples**:

```json
🚨 CRITICAL DISAMBIGUATION EXAMPLES (English):
✅ "My ballot choice is maximizing the floor income" 
   → {"principle": "maximizing_floor", "constraint_amount": null}
✅ "My ballot choice is maximizing the average income" 
   → {"principle": "maximizing_average", "constraint_amount": null}
✅ "My ballot choice is maximizing average with floor constraint of $15000" 
   → {"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000}
✅ "My ballot choice is maximizing average with range constraint of $20000"
   → {"principle": "maximizing_average_range_constraint", "constraint_amount": 20000}

🔑 CRITICAL PARSING RULES:
- "maximizing THE floor income" = maximizing_floor (NOT constraint principle)
- "maximizing THE average income" = maximizing_average (NOT constraint principle) 
- "maximizing average WITH floor constraint" = maximizing_average_floor_constraint (constraint principle)
- "maximizing average WITH range constraint" = maximizing_average_range_constraint (constraint principle)
```

#### 4.2 **Fix Spanish LLM Parsing Prompt**
**Target**: `translations/spanish_prompts.json` → `utility_llm_parse_principle_choice`

**Enhancement**: Add Spanish-specific **disambiguation examples**:

```json
🚨 EJEMPLOS CRÍTICOS DE DESAMBIGUACIÓN (Español):
✅ "Mi elección de voto es maximización del ingreso mínimo"
   → {"principle": "maximizing_floor", "constraint_amount": null}
✅ "Mi elección de voto es maximización del ingreso promedio"
   → {"principle": "maximizing_average", "constraint_amount": null}
✅ "Mi elección de voto es maximización del promedio con restricción de ingreso mínimo de €15000"
   → {"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000}
✅ "Mi elección de voto es maximización del promedio con restricción de rango de €20000"
   → {"principle": "maximizing_average_range_constraint", "constraint_amount": 20000}

🔑 REGLAS CRÍTICAS DE ANÁLISIS:
- "maximización DEL ingreso mínimo" = maximizing_floor (NO es principio de restricción)
- "maximización DEL ingreso promedio" = maximizing_average (NO es principio de restricción)
- "maximización del promedio CON restricción" = maximizing_average_floor_constraint (principio de restricción)
- "maximización del promedio CON restricción de rango" = maximizing_average_range_constraint (principio de restricción)
```

#### 4.3 **Fix Mandarin LLM Parsing Prompt**
**Target**: `translations/mandarin_prompts.json` → `utility_llm_parse_principle_choice`

**Enhancement**: Add Mandarin-specific **disambiguation examples**:

```json
🚨 关键消歧示例 (中文):
✅ "我的投票选择是最大化最低收入"
   → {"principle": "maximizing_floor", "constraint_amount": null}
✅ "我的投票选择是最大化平均收入"
   → {"principle": "maximizing_average", "constraint_amount": null}
✅ "我的投票选择是在最低收入约束条件下最大化平均收入，约束为¥15000"
   → {"principle": "maximizing_average_floor_constraint", "constraint_amount": 15000}
✅ "我的投票选择是在范围约束条件下最大化平均收入，约束为¥20000"
   → {"principle": "maximizing_average_range_constraint", "constraint_amount": 20000}

🔑 关键解析规则:
- "最大化最低收入" = maximizing_floor (不是约束原则)
- "最大化平均收入" = maximizing_average (不是约束原则)
- "在最低收入约束条件下最大化平均收入" = maximizing_average_floor_constraint (约束原则)
- "在范围约束条件下最大化平均收入" = maximizing_average_range_constraint (约束原则)
```

#### 4.4 **Add Comprehensive Test Coverage**
**Target**: Create tests for **exact real-world ballot formats** across all languages

```python
class TestRealWorldBallotParsing(unittest.TestCase):
    """Test exact ballot formats used in real experiments across languages."""
    
    def test_english_real_world_ballots(self):
        """Test English ballot parsing with real experiment formats."""
        real_ballot_cases = [
            ("My ballot choice is maximizing the floor income.", "maximizing_floor", None),
            ("My ballot choice is maximizing the average income.", "maximizing_average", None),
            ("My ballot choice is maximizing average with floor constraint of $15000.", 
             "maximizing_average_floor_constraint", 15000),
            ("My ballot choice is maximizing average with range constraint of $20000.", 
             "maximizing_average_range_constraint", 20000),
        ]
        
    def test_spanish_real_world_ballots(self):
        """Test Spanish ballot parsing with real experiment formats."""
        spanish_ballot_cases = [
            ("Mi elección de voto es maximización del ingreso mínimo.", "maximizing_floor", None),
            ("Mi elección de voto es maximización del ingreso promedio.", "maximizing_average", None),
            ("Mi elección de voto es maximización del promedio con restricción de €15000.", 
             "maximizing_average_floor_constraint", 15000),
        ]
        
    def test_mandarin_real_world_ballots(self):
        """Test Mandarin ballot parsing with real experiment formats."""
        mandarin_ballot_cases = [
            ("我的投票选择是最大化最低收入。", "maximizing_floor", None),
            ("我的投票选择是最大化平均收入。", "maximizing_average", None),
            ("我的投票选择是在最低收入约束条件下最大化平均收入，约束为¥15000。", 
             "maximizing_average_floor_constraint", 15000),
        ]
```

#### 4.5 **Add Runtime Parsing Validation**
**Target**: Add multilingual validation to detect parsing mismatches

```python
async def validate_ballot_parsing_consistency(self, raw_response: str, parsed_result: PrincipleChoice, language: str = "english") -> bool:
    """Validate ballot parsing matches expected patterns across languages."""
    
    # English validation patterns
    english_patterns = {
        "maximizing the floor income": JusticePrinciple.MAXIMIZING_FLOOR,
        "maximizing the average income": JusticePrinciple.MAXIMIZING_AVERAGE,
        "maximizing average with floor constraint": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        "maximizing average with range constraint": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
    }
    
    # Spanish validation patterns
    spanish_patterns = {
        "maximización del ingreso mínimo": JusticePrinciple.MAXIMIZING_FLOOR,
        "maximización del ingreso promedio": JusticePrinciple.MAXIMIZING_AVERAGE,
        "maximización del promedio con restricción": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        "restricción de rango": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
    }
    
    # Mandarin validation patterns  
    mandarin_patterns = {
        "最大化最低收入": JusticePrinciple.MAXIMIZING_FLOOR,
        "最大化平均收入": JusticePrinciple.MAXIMIZING_AVERAGE,
        "在最低收入约束条件下": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        "在范围约束条件下": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
    }
    
    # Select appropriate patterns based on language
    validation_patterns = {
        "english": english_patterns,
        "spanish": spanish_patterns, 
        "mandarin": mandarin_patterns
    }.get(language, english_patterns)
    
    # Check for obvious mismatches
    response_lower = raw_response.lower()
    for pattern, expected_principle in validation_patterns.items():
        if pattern in response_lower:
            if parsed_result.principle != expected_principle:
                logger.error(f"🚫 BALLOT PARSING MISMATCH [{language.upper()}]: '{raw_response}' parsed as {parsed_result.principle.value}, expected {expected_principle.value}")
                return False
                
    return True
```

#### 4.6 **Add Multilingual Integration Tests**
**Target**: End-to-end tests with real experiment simulation

```python
@pytest.mark.asyncio
async def test_multilingual_ballot_parsing_integration(self):
    """Integration test for real-world multilingual ballot parsing."""
    
    test_scenarios = [
        {
            "language": "english",
            "ballot": "My ballot choice is maximizing the floor income.",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None
        },
        {
            "language": "spanish", 
            "ballot": "Mi elección de voto es maximización del ingreso mínimo.",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None
        },
        {
            "language": "mandarin",
            "ballot": "我的投票选择是最大化最低收入。",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None
        }
    ]
    
    utility_agent = UtilityAgent()
    await utility_agent.async_init()
    
    for scenario in test_scenarios:
        result = await utility_agent.parse_principle_choice_llm(scenario["ballot"])
        
        assert result["principle"] == scenario["expected_principle"].value
        assert result["constraint_amount"] == scenario["expected_constraint"]
```

## Implementation Priority

### **Critical Priority (Week 1)**
1. **Fix English parsing prompt** - Addresses immediate issue
2. **Add English real-world tests** - Prevents regression
3. **Add runtime validation** - Catches future mismatches

### **High Priority (Week 2)**  
1. **Fix Spanish parsing prompt** - Covers major language 
2. **Add Spanish real-world tests** - Complete Spanish coverage
3. **Test Spanish ballot scenarios** - Validate fixes

### **Medium Priority (Week 3)**
1. **Fix Mandarin parsing prompt** - Complete multilingual support
2. **Add Mandarin real-world tests** - Full language coverage  
3. **Integration testing** - End-to-end validation

### **Monitoring (Ongoing)**
1. **Runtime validation alerts** - Early detection
2. **Experiment result audits** - Quality assurance
3. **Cross-language consistency checks** - Maintain accuracy

## Expected Outcomes

### **Immediate Benefits**
- ✅ **Accurate English ballot parsing** - Core issue resolved
- ✅ **Experiment result integrity** - Votes match agent intentions  
- ✅ **Runtime error detection** - Early problem identification

### **Long-term Benefits**
- ✅ **Complete multilingual accuracy** - All languages parse correctly
- ✅ **Robust test coverage** - Real-world scenarios covered
- ✅ **Maintainable architecture** - Following utility agent philosophy
- ✅ **Scalable validation system** - Easy to add new languages

## Risk Assessment

### **Low Risk**
- Prompt enhancements (backwards compatible)
- Additional test coverage (no breaking changes)

### **Medium Risk**
- LLM behavioral changes (extensive testing required)
- Cross-language consistency (validation needed)

### **Mitigation Strategies**
- **Comprehensive testing** before deployment
- **Gradual rollout** with validation monitoring  
- **Rollback plan** for prompt changes
- **Multi-language expert review** of disambiguation examples

## Utility Agent Philosophy Compliance

✅ **Enhanced LLM intelligence** through comprehensive disambiguation examples  
✅ **No hardcoded regex patterns** - maintains smart parsing approach
✅ **Multilingual expertise** - leverages utility agent capabilities across languages
✅ **Systematic validation** - intelligent error detection and prevention
✅ **Scalable architecture** - easy to extend to additional languages

## Conclusion

This plan addresses the **critical gap** between test coverage and real-world ballot parsing behavior across English, Spanish, and Mandarin. By enhancing the LLM parsing prompts with comprehensive disambiguation examples and adding robust validation, we maintain our utility agent philosophy while ensuring **accurate vote parsing in all supported languages**.

The systematic approach ensures this issue is resolved not just for the current problem, but provides a foundation for reliable multilingual ballot parsing in future experiments.