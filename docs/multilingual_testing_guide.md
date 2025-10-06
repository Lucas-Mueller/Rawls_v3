# Multilingual Testing Guide

A comprehensive guide for writing effective multilingual tests in the Frohlich Experiment system.

## Table of Contents
1. [Overview](#overview)
2. [Language-Agnostic Test Patterns](#language-agnostic-test-patterns)  
3. [Parameterization Strategies](#parameterization-strategies)
4. [Fixture Usage Best Practices](#fixture-usage-best-practices)
5. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
6. [Testing Workflow](#testing-workflow)

## Overview

The Frohlich Experiment system supports three languages: **English**, **Spanish**, and **Mandarin**. This guide provides best practices for writing tests that ensure consistent behavior across all languages while maintaining code clarity and avoiding duplication.

### Core Principles

1. **Parameterization First**: Use pytest parameterization to test multiple languages with a single test function
2. **Fixture-Driven Data**: Store language-specific test data in fixtures rather than hardcoded in tests  
3. **Separation of Concerns**: Keep language logic separate from test logic
4. **Parity Validation**: Ensure test coverage is consistent across all languages

## Language-Agnostic Test Patterns

### Pattern 1: Parameterized Language Testing

```python
import pytest
from tests.fixtures.phase2_parsing_fixtures import get_multilingual_test_data

@pytest.mark.parametrize("language", ["English", "Spanish", "Mandarin"])
def test_principle_parsing(language):
    """Test principle parsing across all supported languages."""
    test_data = get_multilingual_test_data(language)
    
    for test_case in test_data["principle_parsing"]:
        result = parse_principle(test_case["input"], language)
        assert result == test_case["expected"]
        assert result in VALID_PRINCIPLES  # Language-agnostic validation
```

### Pattern 2: Language-Specific Edge Case Testing

```python
@pytest.mark.parametrize("language,test_case", [
    ("English", {"input": "maximizing the floor income", "expected": "Maximizing the floor income"}),
    ("Spanish", {"input": "maximización del ingreso mínimo", "expected": "Maximizing the floor income"}), 
    ("Mandarin", {"input": "最大化最低收入", "expected": "Maximizing the floor income"})
])
def test_principle_normalization(language, test_case):
    """Test that different language inputs normalize to the same principle."""
    result = normalize_principle(test_case["input"], language)
    assert result == test_case["expected"]
```

### Pattern 3: Cross-Language Consistency Validation

```python
def test_principle_translation_consistency():
    """Ensure all languages have equivalent principle representations."""
    english_principles = get_all_principles("English")
    spanish_principles = get_all_principles("Spanish") 
    mandarin_principles = get_all_principles("Mandarin")
    
    # All languages should have same number of principles
    assert len(english_principles) == len(spanish_principles) == len(mandarin_principles)
    
    # All principles should map to same normalized forms
    for i in range(len(english_principles)):
        eng_norm = normalize_principle(english_principles[i], "English")
        spa_norm = normalize_principle(spanish_principles[i], "Spanish")
        man_norm = normalize_principle(mandarin_principles[i], "Mandarin")
        assert eng_norm == spa_norm == man_norm
```

## Parameterization Strategies

### Strategy 1: Simple Language Parameterization

```python
@pytest.mark.parametrize("language", ["English", "Spanish", "Mandarin"])
def test_basic_functionality(language):
    # Test logic here
    pass
```

### Strategy 2: Language + Test Data Parameterization

```python
@pytest.mark.parametrize("language,constraint_text,expected_value", [
    ("English", "constraint of $15,000", 15000),
    ("Spanish", "restricción de €15.000", 15000),
    ("Mandarin", "约束为¥15,000", 15000)
])
def test_constraint_parsing(language, constraint_text, expected_value):
    result = parse_constraint(constraint_text, language)
    assert result == expected_value
```

### Strategy 3: Nested Parameterization with IDs

```python
@pytest.mark.parametrize("language", ["English", "Spanish", "Mandarin"])
@pytest.mark.parametrize("test_scenario", [
    "basic_agreement", 
    "strong_agreement", 
    "conditional_agreement"
], ids=lambda x: f"scenario_{x}")
def test_agreement_detection(language, test_scenario):
    test_data = get_agreement_test_data(language, test_scenario)
    result = detect_agreement(test_data["input"], language)
    assert result == test_data["expected"]
```

## Fixture Usage Best Practices

### Best Practice 1: Language-Aware Fixture Design

```python
# tests/fixtures/phase2_parsing_fixtures.py
@pytest.fixture
def multilingual_test_data():
    """Provide test data for all supported languages."""
    return {
        "English": {
            "agreement_phrases": ["I agree", "I support this", "Yes, let's do this"],
            "disagreement_phrases": ["I disagree", "I oppose this", "No, I don't support this"],
            "vote_patterns": ["Let's vote", "I propose we vote", "Time to vote"]
        },
        "Spanish": {
            "agreement_phrases": ["Estoy de acuerdo", "Apoyo esto", "Sí, hagámoslo"],
            "disagreement_phrases": ["No estoy de acuerdo", "Me opongo a esto", "No, no apoyo esto"], 
            "vote_patterns": ["Votemos", "Propongo que votemos", "Es hora de votar"]
        },
        "Mandarin": {
            "agreement_phrases": ["我同意", "我支持这个", "是的，我们这样做吧"],
            "disagreement_phrases": ["我不同意", "我反对这个", "不，我不支持这个"],
            "vote_patterns": ["我们投票吧", "我提议我们投票", "是时候投票了"]
        }
    }

@pytest.fixture
def language_test_data(multilingual_test_data, request):
    """Get test data for a specific language."""
    language = getattr(request, 'param', 'English')
    return multilingual_test_data[language]
```

### Best Practice 2: Parameterized Fixtures

```python
@pytest.fixture(params=["English", "Spanish", "Mandarin"])
def language(request):
    """Parameterized language fixture."""
    return request.param

@pytest.fixture
def test_data_for_language(language, multilingual_test_data):
    """Get test data for the current parameterized language."""
    return multilingual_test_data[language]
```

### Best Practice 3: Lazy Loading for Performance

```python
@pytest.fixture(scope="session")
def multilingual_fixtures_cache():
    """Cache multilingual fixtures for performance."""
    cache = {}
    
    def get_fixtures(language):
        if language not in cache:
            cache[language] = load_language_fixtures(language)
        return cache[language]
    
    return get_fixtures
```

## Common Pitfalls and Solutions

### Pitfall 1: Hardcoded Language Assumptions

**❌ Wrong:**
```python
def test_agreement_detection():
    text = "I agree with this proposal"  # Hardcoded English
    result = detect_agreement(text)
    assert result is True
```

**✅ Correct:**
```python
@pytest.mark.parametrize("language,text,expected", [
    ("English", "I agree with this proposal", True),
    ("Spanish", "Estoy de acuerdo con esta propuesta", True),
    ("Mandarin", "我同意这个提议", True)
])
def test_agreement_detection(language, text, expected):
    result = detect_agreement(text, language)
    assert result == expected
```

### Pitfall 2: Missing Edge Cases per Language

**❌ Wrong:**
```python
def test_number_parsing():
    assert parse_number("15,000") == 15000  # Only tests English format
```

**✅ Correct:**
```python
@pytest.mark.parametrize("language,input_text,expected", [
    ("English", "15,000", 15000),      # English: comma thousands separator
    ("Spanish", "15.000", 15000),      # Spanish: period thousands separator  
    ("Mandarin", "15,000", 15000),     # Mandarin: comma thousands separator
    ("Mandarin", "1万5千", 15000),      # Mandarin: Chinese numerals
])
def test_number_parsing(language, input_text, expected):
    result = parse_number(input_text, language)
    assert result == expected
```

### Pitfall 3: Incomplete Language Coverage

**❌ Wrong:**
```python
def test_english_parsing():
    # Only tests English
    pass

def test_spanish_parsing():
    # Only tests Spanish  
    pass

# Missing Mandarin tests!
```

**✅ Correct:**
```python
@pytest.mark.parametrize("language", ["English", "Spanish", "Mandarin"])
def test_multilingual_parsing(language):
    # Tests all languages with same logic
    test_data = get_test_data_for_language(language)
    for case in test_data:
        result = parse_text(case["input"], language)
        assert result == case["expected"]
```

### Pitfall 4: Character Encoding Issues

**❌ Wrong:**
```python
def test_chinese_parsing():
    text = "最大化"  # May have encoding issues
    result = parse_principle(text)
    # Test may fail due to encoding
```

**✅ Correct:**
```python
import pytest

@pytest.mark.parametrize("language,text,expected", [
    ("Mandarin", "最大化最低收入", "Maximizing the floor income"),
], ids=["mandarin_principle_parsing"])
def test_principle_parsing_with_encoding(language, text, expected):
    # Ensure proper UTF-8 handling
    assert isinstance(text, str)
    assert text.encode('utf-8').decode('utf-8') == text
    
    result = parse_principle(text, language)
    assert result == expected
```

## Testing Workflow

### Step 1: Write Language-Agnostic Tests

1. Start with English-only test
2. Identify language-dependent components  
3. Extract language-specific data to fixtures
4. Parameterize test for all languages

### Step 2: Add Language-Specific Edge Cases

1. Research language-specific formatting (numbers, currency)
2. Identify regional variations
3. Add edge cases to fixture data
4. Validate with native speakers when possible

### Step 3: Validate Cross-Language Consistency

1. Run tests across all languages
2. Check for equivalent behavior
3. Validate normalized outputs are identical
4. Document any intentional language differences

### Step 4: Performance and Coverage Validation

1. Run performance benchmarks per language
2. Validate test coverage is consistent
3. Check for memory leaks with Unicode text
4. Verify CI/CD pipeline handles all languages

## Example Test Structure

```python
# tests/unit/test_example_multilingual.py
import pytest
from tests.fixtures.phase2_parsing_fixtures import get_multilingual_test_data

class TestMultilingualFeature:
    """Test suite for multilingual feature validation."""
    
    @pytest.mark.parametrize("language", ["English", "Spanish", "Mandarin"])
    def test_basic_functionality(self, language):
        """Test basic functionality across all languages."""
        test_data = get_multilingual_test_data(language)
        # Test logic here
    
    @pytest.mark.parametrize("language,test_case", [
        ("English", {"input": "test", "expected": "result"}),
        ("Spanish", {"input": "prueba", "expected": "resultado"}),
        ("Mandarin", {"input": "测试", "expected": "结果"})
    ])
    def test_specific_cases(self, language, test_case):
        """Test specific language cases."""
        # Test logic here
    
    def test_cross_language_consistency(self):
        """Test that all languages produce consistent results."""
        # Cross-validation logic here
```

## Quick Reference Commands

```bash
# Run multilingual tests
pytest tests/ -k "multilingual" -v

# Run tests for specific language
pytest tests/ -k "spanish" -v

# Run with coverage by language
pytest tests/ --cov --cov-report=html

# Run performance benchmarks
pytest tests/performance/ --benchmark-only
```

## Additional Resources

- [Spanish Test Patterns](spanish_test_patterns.md) - Spanish-specific edge cases
- [Chinese Test Patterns](chinese_test_patterns.md) - Chinese character handling
- [Test Templates](../tests/templates/) - Reusable test templates
- [Fixture Documentation](../tests/fixtures/README.md) - Fixture usage examples

---

*Created as part of Subplan 7: Documentation and Training Materials*
*Version 1.0 - Comprehensive Multilingual Testing Guide*