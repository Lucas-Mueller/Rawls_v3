# Spanish Test Patterns

A comprehensive guide for testing Spanish language features in the Frohlich Experiment system.

## Table of Contents
1. [Overview](#overview)
2. [Number Format Variations](#number-format-variations)
3. [Currency Handling](#currency-handling)
4. [Accent Sensitivity](#accent-sensitivity)
5. [Regional Vocabulary Variations](#regional-vocabulary-variations)
6. [Agreement and Disagreement Patterns](#agreement-and-disagreement-patterns)
7. [Vote Intention Detection](#vote-intention-detection)
8. [Common Edge Cases](#common-edge-cases)
9. [Testing Examples](#testing-examples)

## Overview

Spanish language testing requires attention to:
- **Regional number formats** (European vs Latin American)
- **Multiple currency symbols** (€, $, peso variants)
- **Accent sensitivity** (á, é, í, ó, ú, ñ)
- **Regional vocabulary differences** 
- **Formal vs informal language variations**

## Number Format Variations

### European Spanish Format
- **Thousands separator**: Period (.)
- **Decimal separator**: Comma (,)
- **Example**: `15.000,50` → 15000.50

### Latin American Spanish Format  
- **Thousands separator**: Comma (,)
- **Decimal separator**: Period (.)
- **Example**: `15,000.50` → 15000.50

### Test Pattern Examples

```python
@pytest.mark.parametrize("input_text,expected,region", [
    # European format
    ("15.000", 15000, "European"),
    ("1.500,75", 1500.75, "European"), 
    ("2.000.000", 2000000, "European"),
    
    # Latin American format
    ("15,000", 15000, "Latin American"),
    ("1,500.75", 1500.75, "Latin American"),
    ("2,000,000", 2000000, "Latin American"),
    
    # Mixed format edge cases
    ("15000", 15000, "Universal"),
    ("15 000", 15000, "Spaced"),
])
def test_spanish_number_parsing(input_text, expected, region):
    result = parse_spanish_number(input_text)
    assert result == expected
```

## Currency Handling

### Supported Currency Symbols

| Symbol | Meaning | Region | Example |
|--------|---------|---------|---------|
| `€` | Euro | Spain | `€15.000,50` |
| `$` | Dollar/Peso | Americas | `$15,000.50` |
| `MXN` | Mexican Peso | Mexico | `MXN 15,000` |
| `ARS` | Argentine Peso | Argentina | `ARS 15.000` |
| `COP` | Colombian Peso | Colombia | `COP 15,000` |
| `USD` | US Dollar | International | `USD 15,000` |

### Currency Parsing Tests

```python
SPANISH_CURRENCY_TEST_CASES = [
    # Euro formats
    ("restricción de €15.000", 15000, "EUR"),
    ("límite de 15.000 euros", 15000, "EUR"),
    ("máximo €15,000.50", 15000.50, "EUR"),
    
    # Dollar/Peso formats  
    ("constrainte de $15,000", 15000, "USD_OR_PESO"),
    ("límite de 15 mil dólares", 15000, "USD"),
    ("restricción $15.000", 15000, "USD_OR_PESO"),
    
    # Specific peso currencies
    ("límite MXN 15,000", 15000, "MXN"),
    ("restricción ARS 15.000", 15000, "ARS"),
    ("máximo COP 15,000", 15000, "COP"),
    
    # Currency words
    ("límite de quince mil pesos", 15000, "PESO"),
    ("restricción de dos mil euros", 2000, "EUR"),
]
```

## Accent Sensitivity

### Common Accent Variations

Spanish speakers may or may not include accents when typing, especially on mobile devices or non-Spanish keyboards.

```python
ACCENT_VARIATION_TESTS = [
    # Maximization variations  
    ("maximización", "maximizacion"),
    ("máximo", "maximo"),
    ("mínimo", "minimo"),
    ("promedio", "promedio"),  # No accent variation
    
    # Agreement variations
    ("está bien", "esta bien"),
    ("sí", "si"), 
    ("también", "tambien"),
    ("decisión", "decision"),
    
    # Constraint variations
    ("restricción", "restriccion"),
    ("limitación", "limitacion"),
    ("condición", "condicion"),
]

@pytest.mark.parametrize("accented,unaccented", ACCENT_VARIATION_TESTS)
def test_accent_insensitive_parsing(accented, unaccented):
    """Both accented and unaccented versions should parse identically."""
    result_accented = parse_spanish_text(accented)
    result_unaccented = parse_spanish_text(unaccented) 
    assert result_accented == result_unaccented
```

## Regional Vocabulary Variations

### Principle Name Variations

Different Spanish-speaking regions may use slightly different terminology:

```python
REGIONAL_PRINCIPLE_VARIATIONS = {
    "Maximizing the floor income": [
        "maximización del ingreso mínimo",           # Standard
        "maximización del salario mínimo",           # Alternative 1  
        "maximización del ingreso base",             # Alternative 2
        "maximizando el ingreso mínimo",            # Gerund form
        "maximizar el piso de ingresos",            # Literal translation
    ],
    
    "Maximizing the average income": [
        "maximización del ingreso promedio",         # Standard
        "maximización del ingreso medio",            # Alternative 1
        "maximización de la media de ingresos",      # Alternative 2
        "maximizando el ingreso promedio",          # Gerund form
    ],
    
    "Maximizing the average income with a floor constraint": [
        "maximización del ingreso promedio con restricción de mínimo",
        "maximización del ingreso promedio con límite inferior",
        "maximización del ingreso medio con restricción de piso",
    ],
    
    "Maximizing the average income with a range constraint": [
        "maximización del ingreso promedio con restricción de rango",
        "maximización del ingreso promedio con límite de distancia",
        "maximización del ingreso medio con restricción de alcance",
    ]
}
```

## Agreement and Disagreement Patterns

### Agreement Patterns

```python
SPANISH_AGREEMENT_PATTERNS = [
    # Strong agreement
    "estoy de acuerdo",
    "estoy completamente de acuerdo", 
    "acepto",
    "conforme",
    "perfecto",
    "exacto",
    "correcto",
    "sí, estoy de acuerdo",
    "totalmente de acuerdo",
    "me parece bien",
    "está bien",
    "de acuerdo",
    
    # Conditional agreement
    "estoy de acuerdo si",
    "acepto con la condición",
    "conforme, pero",
    "está bien, siempre que",
    
    # Regional variations
    "vale" (Spain),
    "órale" (Mexico),
    "bueno" (General),
    "listo" (Latin America),
]
```

### Disagreement Patterns

```python
SPANISH_DISAGREEMENT_PATTERNS = [
    # Strong disagreement  
    "no estoy de acuerdo",
    "no acepto",
    "me opongo",
    "rechazo",
    "no me parece",
    "no está bien",
    "no, no estoy de acuerdo",
    "totalmente en desacuerdo",
    "para nada",
    
    # Soft disagreement
    "no estoy muy de acuerdo",
    "tengo dudas",
    "no me convence",
    "no estoy seguro",
    "me parece difícil",
    
    # Regional variations
    "ni modo" (Mexico),
    "qué va" (Spain),
    "ni loco" (Argentina),
]
```

## Vote Intention Detection

### Voting Trigger Phrases

```python
SPANISH_VOTE_PATTERNS = [
    # Direct voting calls
    "votemos ahora",
    "vamos a votar", 
    "propongo que votemos",
    "es hora de votar",
    "procedamos a la votación",
    "sugiero que tomemos una decisión",
    "deberíamos decidir ya",
    "es momento de decidir",
    
    # Vote declarations
    "voto por",
    "mi voto es",
    "yo voto",
    "elijo",
    "mi elección es",
    
    # Regional variations
    "démosle" (Mexico - "let's give it"),
    "dale" (Argentina - "go ahead"),
    "venga" (Spain - "come on"),
]
```

### Non-Voting Phrases (Should NOT trigger voting)

```python
SPANISH_NON_VOTE_PATTERNS = [
    # Questions about voting
    "¿deberíamos votar?",
    "¿qué piensan de votar?",
    "¿votamos o seguimos discutiendo?",
    
    # Conditional statements
    "si votamos ahora",
    "cuando votemos",
    "antes de votar",
    "después de votar",
    
    # Discussion continuation
    "necesitamos más discusión",
    "no estoy listo para votar",
    "todavía no",
    "sigamos hablando",
]
```

## Common Edge Cases

### Case 1: Mixed Language Input
```python
def test_spanish_mixed_language_input():
    """Test handling of Spanish text with English words."""
    test_cases = [
        "estoy de acuerdo con floor constraint de €15,000",
        "voto por maximizing average income",
        "mi elección es range constraint"  
    ]
    for case in test_cases:
        result = parse_spanish_mixed_input(case)
        assert result is not None
        assert "error" not in result.lower()
```

### Case 2: Informal vs Formal Language
```python
def test_spanish_formality_levels():
    """Test handling of informal vs formal Spanish."""
    informal_formal_pairs = [
        ("¿qué tal?", "¿cómo está usted?"),           # greeting
        ("está bien", "me parece correcto"),          # agreement  
        ("ni modo", "no estoy de acuerdo"),           # disagreement
        ("órale, votemos", "propongo que votemos"),   # voting
    ]
    
    for informal, formal in informal_formal_pairs:
        informal_result = parse_spanish_text(informal)
        formal_result = parse_spanish_text(formal)
        # Both should be understood, though may normalize differently
        assert informal_result is not None
        assert formal_result is not None
```

### Case 3: Typos and Common Mistakes
```python
SPANISH_TYPO_CORRECTIONS = [
    # Common typos
    ("maximizacion", "maximización"),
    ("minimo", "mínimo"), 
    ("promedio", "promedio"),  # Already correct
    ("de aceurdo", "de acuerdo"),
    ("restirción", "restricción"),
    
    # Missing tildes
    ("restriccion", "restricción"),
    ("decision", "decisión"),
    ("condicion", "condición"),
]
```

## Testing Examples

### Complete Spanish Test Class

```python
import pytest
from utils.language_manager import LanguageManager
from experiment_agents.utility_agent import UtilityAgent

class TestSpanishParsing:
    """Comprehensive Spanish language parsing tests."""
    
    @pytest.fixture
    def spanish_language_manager(self):
        return LanguageManager("Spanish")
    
    @pytest.mark.parametrize("principle_text,expected", [
        ("maximización del ingreso mínimo", "Maximizing the floor income"),
        ("maximización del ingreso promedio", "Maximizing the average income"),
        ("maximización del ingreso promedio con restricción de mínimo", 
         "Maximizing the average income with a floor constraint"),
        ("maximización del ingreso promedio con restricción de rango",
         "Maximizing the average income with a range constraint"),
    ])
    def test_spanish_principle_parsing(self, principle_text, expected, spanish_language_manager):
        result = spanish_language_manager.parse_principle(principle_text)
        assert result == expected
    
    @pytest.mark.parametrize("constraint_text,expected_value", [
        ("restricción de €15.000", 15000),
        ("límite de $20,000", 20000), 
        ("máximo de 25 mil euros", 25000),
        ("sin restricciones", None),
        ("sin límites adicionales", None),
    ])
    def test_spanish_constraint_parsing(self, constraint_text, expected_value, spanish_language_manager):
        result = spanish_language_manager.parse_constraint(constraint_text)
        assert result == expected_value
    
    @pytest.mark.parametrize("agreement_text,expected", [
        ("estoy de acuerdo", True),
        ("no estoy de acuerdo", False),
        ("acepto esta propuesta", True),
        ("rechazo esta opción", False),
        ("me parece bien", True),
    ])
    def test_spanish_agreement_detection(self, agreement_text, expected, spanish_language_manager):
        result = spanish_language_manager.detect_agreement(agreement_text)
        assert result == expected
    
    @pytest.mark.parametrize("vote_text,should_trigger_vote", [
        ("votemos ahora", True),
        ("propongo que votemos", True), 
        ("¿deberíamos votar?", False),
        ("antes de votar", False),
        ("mi voto es", True),
    ])
    def test_spanish_vote_detection(self, vote_text, should_trigger_vote, spanish_language_manager):
        result = spanish_language_manager.detect_vote_intention(vote_text)
        assert result == should_trigger_vote
```

## Performance Considerations

### Unicode and Memory Usage
```python
def test_spanish_unicode_memory_usage():
    """Test memory efficiency with Spanish Unicode text."""
    large_spanish_text = "maximización del ingreso promedio con restricción de rango " * 1000
    
    import tracemalloc
    tracemalloc.start()
    
    result = parse_spanish_text(large_spanish_text)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Memory usage should be reasonable
    assert peak < 50 * 1024 * 1024  # Less than 50MB
    assert result is not None
```

## Quick Reference

### Command Line Testing
```bash
# Run Spanish-specific tests
pytest tests/ -k "spanish" -v

# Run with Spanish language parameter
pytest tests/ -k "multilingual" --language=Spanish -v

# Test Spanish edge cases only
pytest tests/ -k "spanish and edge_case" -v
```

### Test Data Files
- `tests/fixtures/spanish_test_data.json` - Static Spanish test cases
- `translations/spanish_prompts.json` - Spanish language prompts
- `tests/fixtures/spanish_regional_data.json` - Regional variations

---

*Created as part of Subplan 7: Documentation and Training Materials*
*Version 1.0 - Spanish Test Patterns Guide*