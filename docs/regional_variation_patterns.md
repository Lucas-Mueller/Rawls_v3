# Regional Variation Handling Patterns

This document provides comprehensive guidance on handling regional variations in the Frohlich Experiment system as implemented through **Subplan 5: Localization and Regional Variations**.

## Overview

The regional variation system ensures robust multilingual support without hardcoded assumptions about locale-specific formatting. It handles:

- Regional number formats (thousands/decimal separators)  
- Currency symbol variations across regions
- Date format preferences by locale
- Cultural context and communication styles
- Cultural number preferences and superstitions

## Architecture

### Core Components

#### 1. LocaleManager (`utils/locale_manager.py`)
Central system for managing regional format detection and parsing:

```python
from utils.locale_manager import get_locale_manager, SupportedLocale

manager = get_locale_manager()
manager.set_locale(SupportedLocale.SPANISH_MEXICO)
amount, currency = manager.parse_currency_amount("restricción de $15,000 MXN")
```

#### 2. Regional Test Modules
- `tests/unit/test_regional_formats.py` - Number and date format tests
- `tests/unit/test_currency_handling.py` - Currency symbol variation tests  
- `tests/unit/test_cultural_context.py` - Cultural communication pattern tests

#### 3. Integration with LanguageManager
Works alongside existing `utils/language_manager.py` for complete multilingual support.

## Supported Regional Formats

### Regional Number Format Matrix

| Region          | Number Format | Currency | Date Format | Example         |
|-----------------|---------------|----------|-------------|-----------------|
| US              | 1,234.56      | $        | MM/DD/YYYY  | $15,000.50      |
| Europe          | 1.234,56      | €        | DD/MM/YYYY  | €15.000,50      |
| Latin America   | 1,234.56      | Various  | DD/MM/YYYY  | $15,000.50      |
| China           | 1,234.56      | ¥        | YYYY-MM-DD  | ¥15,000.50      |
| Spain           | 1.234,56      | €        | DD/MM/YYYY  | €15.000,50      |
| Mexico          | 1,234.56      | $        | DD/MM/YYYY  | $15,000.50      |

### Currency Symbol Variations

#### USD (United States Dollar)
- **Symbols**: `$`, `USD`, `US$`
- **Positions**: Prefix (`$15000`), Suffix (`15000$`)
- **Examples**: 
  - `constraint of $15,000`
  - `limit of 15,000 USD`
  - `restriction US$15,000`

#### EUR (Euro)
- **Symbols**: `€`, `EUR`
- **Positions**: Prefix (`€15000`), Suffix (`15000€`)
- **Regional Variations**:
  - European format: `€15.000,50`
  - Text variations: `15000 euros`
  - **Examples**: 
    - `constraint of €15.000`
    - `limit of 15000 EUR`

#### CNY (Chinese Yuan)
- **Symbols**: `¥`, `CNY`, `RMB`, `元`
- **Special Features**: Chinese number units (万, 千)
- **Examples**:
  - `约束为¥15,000`
  - `限制是1万5千元` (15,000)
  - `约束CNY 15000`
  - `限制RMB 15,000`

#### MXN and Peso Variants
- **Mexican Peso**: `MXN`, `peso`, `pesos`
- **Other Pesos**: `ARS`, `COP`, `CLP`, `UYU`
- **Examples**:
  - `restricción de MXN 15,000`
  - `límite de 15,000 pesos`
  - `constraint ARS 15000`

### Date Format Handling

#### US Format (MM/DD/YYYY)
```
deadline 03/15/2024  → March 15, 2024
by 12/25/2023        → December 25, 2023
```

#### European Format (DD/MM/YYYY)  
```
deadline 15/03/2024  → March 15, 2024
by 25/12/2023        → December 25, 2023
```

#### Chinese Format (YYYY-MM-DD)
```
截止日期2024-03-15   → March 15, 2024
到2023-12-25为止     → December 25, 2023
```

## Cultural Context Patterns

### Formality Level Detection

#### English Formality Markers
- **Very Formal**: "humbly submit", "with great respect"
- **Formal**: "respectfully", "may I", "would you kindly"  
- **Neutral**: "I believe", "I think"
- **Informal**: "let's just", "how about"
- **Very Informal**: "gonna", "'m gonna"

#### Spanish Formality Markers
- **Very Formal**: "humildemente sugiero", "con gran respeto"
- **Formal**: "respetuosamente", "me permito", "sería tan amable"
- **Neutral**: "creo que", "pienso que"
- **Informal**: "vamos a", "¿qué tal si?"
- **Very Informal**: "voy a", casual contractions

#### Chinese Formality Markers
- **Very Formal**: "恭敬地", "谨慎地建议"
- **Formal**: "请允许我", "请您考虑"
- **Neutral**: "我认为", "我觉得"
- **Informal**: "我们就", "怎么样？"
- **Very Informal**: "搞", very casual particles

### Politeness Marker Recognition

#### Universal Politeness Patterns
- **English**: "please", "would you kindly", "if I may", "thank you"
- **Spanish**: "por favor", "sería tan amable", "si me permite", "gracias"  
- **Chinese**: "请", "请您", "麻烦您", "谢谢您"

### Agreement Strength Variations

#### Strength Levels
1. **Strong**: "completely", "absolutely", "totally" / "completamente", "absolutamente" / "完全", "绝对"
2. **Moderate**: "agree", "support" / "de acuerdo", "apoyo" / "同意", "支持"  
3. **Weak**: "suppose", "maybe", "might" / "supongo", "tal vez" / "觉得", "可能"

### Cultural Number Preferences

#### Chinese Lucky/Unlucky Numbers
- **Lucky Numbers**: 8, 88, 888, 168, 518 (contain 8)
- **Unlucky Numbers**: 4, 44, 444, 14, 74 (contain 4)
- **Special Units**: 万 (10,000), 千 (1,000)

#### Western Superstitions
- **Unlucky Numbers**: 13, 113, 1313, 6666

## Implementation Guidelines

### 1. Locale Detection Strategy

```python
# Automatic locale detection from text content
def detect_locale(text: str) -> Optional[SupportedLocale]:
    """
    Priority order:
    1. Currency symbols (€, ¥, $)
    2. Language indicators (Chinese characters, Spanish terms)
    3. Number format patterns (1.234,56 vs 1,234.56)
    4. Cultural context markers
    """
    pass
```

### 2. Parsing Best Practices

#### Currency Amount Parsing
```python
# Support multiple patterns in order of preference:
patterns = [
    r'(currency)(number)',     # $1,234
    r'(number)(currency)',     # 1,234$  
    r'(number)\s+(currency)',  # 1,234 USD
]
```

#### Number Format Normalization
```python
def normalize_number(text: str, locale: SupportedLocale) -> float:
    """
    Handle different thousands/decimal separators:
    - US: 1,234.56 → 1234.56
    - EU: 1.234,56 → 1234.56
    - CN: 1万5千 → 15000.0
    """
    pass
```

### 3. Cultural Context Integration

#### Formality Level Usage
```python
def adjust_response_formality(locale: SupportedLocale) -> bool:
    """
    Return True if formal language expected by default:
    - Chinese locales: True (formal default)
    - European locales: True (formal default)
    - Latin American locales: False (informal OK)
    """
    return locale_config[locale].formal_default
```

### 4. Error Handling Patterns

#### Graceful Degradation
- **Mixed formats**: Parse what's recognizable, log ambiguities
- **Unknown currencies**: Extract numeric value, flag currency code
- **Invalid dates**: Return None rather than crash
- **Cultural conflicts**: Use primary locale rules, log conflicts

#### Validation Strategy
```python
def validate_regional_parsing(result, original_text, locale):
    """
    Validation checklist:
    1. Numeric value reasonable?
    2. Currency code valid for locale?  
    3. Format consistent with regional norms?
    4. No hardcoded assumptions violated?
    """
    pass
```

## Testing Patterns

### 1. Parameterized Testing Approach

```python
@pytest.mark.parametrize("locale,text,expected", [
    (SupportedLocale.US_ENGLISH, "$15,000", (15000, "USD")),
    (SupportedLocale.EUROPEAN_ENGLISH, "€15.000", (15000, "EUR")),  
    (SupportedLocale.CHINESE_SIMPLIFIED, "¥15,000", (15000, "CNY")),
])
def test_currency_parsing(locale, text, expected):
    result = parse_currency_amount(text, locale)
    assert result == expected
```

### 2. Cross-Locale Consistency Tests

```python
def test_no_hardcoded_assumptions():
    """Ensure same numeric value parsed correctly across locales"""
    amount = 15000
    test_cases = [
        (SupportedLocale.US_ENGLISH, "$15,000"),
        (SupportedLocale.EUROPEAN_ENGLISH, "€15.000"),
        (SupportedLocale.CHINESE_SIMPLIFIED, "¥15,000"),
    ]
    
    for locale, text in test_cases:
        result, _ = parse_currency_amount(text, locale)
        assert result == amount
```

### 3. Cultural Context Validation

```python
def test_cultural_appropriateness():
    """Ensure responses respect cultural communication norms"""
    formal_locales = [SupportedLocale.CHINESE_SIMPLIFIED, SupportedLocale.SPANISH_SPAIN]
    informal_ok_locales = [SupportedLocale.US_ENGLISH, SupportedLocale.SPANISH_MEXICO]
    
    for locale in formal_locales:
        assert is_formal_expected(locale) == True
        
    for locale in informal_ok_locales:
        assert is_formal_expected(locale) == False
```

## Integration with Existing System

### 1. LanguageManager Integration

The regional system works alongside the existing `LanguageManager`:

```python
from utils.language_manager import get_language_manager
from utils.locale_manager import get_locale_manager

# Coordinated setup
language_manager = get_language_manager()
locale_manager = get_locale_manager()

language_manager.set_language(SupportedLanguage.SPANISH)  
locale_manager.set_locale(SupportedLocale.SPANISH_MEXICO)
```

### 2. UtilityAgent Enhancement

The `UtilityAgent` should incorporate regional parsing:

```python
async def parse_participant_preference(self, statement: str, participant_name: str):
    # Auto-detect locale from statement
    detected_locale = detect_locale_from_text_global(statement)
    
    # Parse with locale awareness
    if detected_locale:
        currency_result = parse_currency_amount_global(statement)
        # Use currency_result in preference parsing
    
    # Continue with existing parsing logic
```

### 3. Configuration File Support

Regional preferences should be configurable via experiment config:

```yaml
# config/spanish_mexico_config.yaml
language: Spanish
locale: es_MX
regional_settings:
  currency_preference: MXN
  number_format: us_style  # 1,234.56
  date_format: dd_mm_yyyy
  formality_default: false
```

## Troubleshooting Common Issues

### 1. Mixed Format Scenarios

**Problem**: Text contains multiple regional formats
```
"between €15.000 and $20,000"
```

**Solution**: Parse each currency amount separately, document ambiguity
```python
def handle_mixed_formats(text):
    amounts = []
    for pattern in currency_patterns:
        matches = re.findall(pattern, text)
        amounts.extend(matches)
    
    if len(amounts) > 1:
        log_warning("Mixed currency formats detected")
    
    return amounts
```

### 2. Locale Auto-Detection Failures

**Problem**: Cannot determine locale from text content

**Solution**: Fall back to current locale, document assumption
```python
def safe_locale_detection(text):
    detected = detect_locale_from_text(text)
    if detected:
        return detected
    else:
        log_info(f"Could not detect locale from: {text}")
        return get_current_locale()
```

### 3. Cultural Context Conflicts

**Problem**: Formal language expected but informal provided

**Solution**: Accept input, adjust response appropriately
```python
def handle_formality_mismatch(input_text, expected_formal):
    detected_formal = detect_formality_level(input_text)
    
    if expected_formal and detected_formal == FormalityLevel.INFORMAL:
        log_info("Informal input in formal context - accepting")
        # Continue processing but use formal response
    
    return True  # Always accept, adjust response style
```

## Performance Considerations

### 1. Caching Strategy

- **Locale Detection**: Cache results for identical text
- **Currency Patterns**: Pre-compile regex patterns  
- **Cultural Rules**: Cache formality/politeness assessments

### 2. Optimization Patterns

```python
# Pre-compile patterns at module level
CURRENCY_PATTERNS = {
    locale: re.compile(pattern) 
    for locale, pattern in build_currency_patterns().items()
}

# Use cached detection
@lru_cache(maxsize=1000)
def cached_locale_detection(text_hash):
    return detect_locale_from_text(text)
```

### 3. Resource Usage

- **Memory**: Pattern compilation ~5-10MB
- **CPU**: Regex matching ~1-5ms per text
- **I/O**: No additional file access required

## Future Enhancements

### 1. Additional Locales

Planned support for:
- **Arabic**: Right-to-left, Arabic-Indic numerals
- **Japanese**: Yen currency, Japanese numerals  
- **Portuguese**: Brazilian vs European variations
- **French**: Canadian vs European variations

### 2. Advanced Cultural Context

- **Hierarchical communication**: Respect levels, honorifics
- **Regional business customs**: Meeting protocols, decision-making styles
- **Cultural dimensions**: Individualism vs collectivism impact

### 3. Machine Learning Integration  

- **Locale prediction**: ML models for ambiguous cases
- **Formality classification**: Automated politeness level detection
- **Cultural adaptation**: Dynamic response style adjustment

## Conclusion

The regional variation system provides comprehensive support for multilingual and multicultural interactions without hardcoded assumptions. It ensures robust parsing across different regional formats while respecting cultural communication norms.

Key benefits:
- **Flexibility**: Supports multiple regional formats simultaneously
- **Robustness**: Graceful handling of mixed and ambiguous formats  
- **Cultural Awareness**: Respects communication norms and preferences
- **Maintainability**: Clear separation of concerns, extensible architecture
- **Testing**: Comprehensive test coverage for edge cases and variations

For implementation questions or additional regional support requirements, consult the test modules and utility code for concrete examples and patterns.