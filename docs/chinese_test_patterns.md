# Chinese Test Patterns

A comprehensive guide for testing Chinese/Mandarin language features in the Frohlich Experiment system.

## Table of Contents
1. [Overview](#overview)
2. [Character Encoding Considerations](#character-encoding-considerations)
3. [Simplified vs Traditional Chinese](#simplified-vs-traditional-chinese)
4. [Number Format Systems](#number-format-systems)
5. [Currency Handling](#currency-handling)
6. [Agreement and Disagreement Patterns](#agreement-and-disagreement-patterns)
7. [Vote Intention Detection](#vote-intention-detection)
8. [Pinyin Fallback Handling](#pinyin-fallback-handling)
9. [Common Edge Cases](#common-edge-cases)
10. [Testing Examples](#testing-examples)

## Overview

Chinese language testing requires special attention to:
- **UTF-8 encoding** handling for Chinese characters
- **Simplified vs Traditional** character variants
- **Mixed numbering systems** (Arabic, Chinese numerals, and combinations)
- **Multiple currency representations** (¥, RMB, CNY, 元)
- **Context-dependent meanings** in Chinese text
- **Pinyin romanization** as fallback mechanism

## Character Encoding Considerations

### UTF-8 Validation

All Chinese text must be properly handled as UTF-8:

```python
def test_chinese_utf8_encoding():
    """Test proper UTF-8 handling of Chinese characters."""
    chinese_texts = [
        "最大化最低收入",          # Maximizing floor income
        "最大化平均收入",          # Maximizing average income  
        "我同意这个提议",          # I agree with this proposal
        "我们应该投票决定",        # We should vote to decide
    ]
    
    for text in chinese_texts:
        # Validate UTF-8 encoding/decoding
        assert isinstance(text, str)
        encoded = text.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert text == decoded
        
        # Test processing doesn't corrupt characters
        result = parse_chinese_text(text)
        assert result is not None
        assert all(ord(char) < 1114112 for char in text)  # Valid Unicode range
```

### Character Range Validation

```python
def is_chinese_character(char):
    """Check if character is in Chinese Unicode ranges."""
    return (
        '\u4e00' <= char <= '\u9fff' or      # CJK Unified Ideographs
        '\u3400' <= char <= '\u4dbf' or      # CJK Extension A
        '\uf900' <= char <= '\ufaff'         # CJK Compatibility Ideographs
    )

def test_chinese_character_recognition():
    """Test recognition of valid Chinese character ranges."""
    test_cases = [
        ("最", True),   # Common character
        ("龘", True),   # Complex character  
        ("a", False),   # Latin character
        ("1", False),   # Arabic numeral
        ("，", False),   # Chinese punctuation (handled separately)
    ]
    
    for char, expected in test_cases:
        result = is_chinese_character(char)
        assert result == expected
```

## Simplified vs Traditional Chinese

### Character Mapping

Some principles may be expressed in both Simplified and Traditional Chinese:

```python
SIMPLIFIED_TRADITIONAL_MAPPINGS = {
    # Principle-related terms
    "最大化": "最大化",      # Same in both (maximize)
    "收入": "收入",          # Same in both (income)
    "平均": "平均",          # Same in both (average)  
    "约束": "約束",          # Different (constraint)
    "限制": "限制",          # Same in both (limit)
    "决定": "決定",          # Different (decide)
    "投票": "投票",          # Same in both (vote)
    "同意": "同意",          # Same in both (agree)
    
    # Numbers
    "万": "萬",              # Different (ten thousand)
    "千": "千",              # Same in both (thousand)
}

@pytest.mark.parametrize("simplified,traditional", [
    ("约束为¥15,000", "約束為¥15,000"),
    ("我决定投票", "我決定投票"),
    ("限制是2万元", "限制是2萬元"),
])
def test_simplified_traditional_equivalence(simplified, traditional):
    """Test that simplified and traditional forms parse identically."""
    result_simplified = parse_chinese_text(simplified)
    result_traditional = parse_chinese_text(traditional)
    assert normalize_chinese_result(result_simplified) == normalize_chinese_result(result_traditional)
```

## Number Format Systems

### Chinese Numeral System

Chinese uses a unique number system that must be handled:

```python
CHINESE_NUMBER_MAPPINGS = {
    # Basic digits
    "〇": 0, "零": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
    
    # Place values
    "十": 10, "百": 100, "千": 1000, "万": 10000,
    "十万": 100000, "百万": 1000000, "千万": 10000000, "亿": 100000000,
}

CHINESE_NUMBER_TEST_CASES = [
    # Pure Chinese numerals
    ("一万五千", 15000),
    ("二万", 20000),
    ("十五万", 150000),
    ("一千万", 10000000),
    ("三千五百", 3500),
    
    # Mixed Arabic and Chinese
    ("15千", 15000),
    ("2万", 20000),
    ("1.5万", 15000),
    ("25万元", 250000),
    
    # Pure Arabic (should also work)
    ("15000", 15000),
    ("15,000", 15000),
    ("1,500,000", 1500000),
]

@pytest.mark.parametrize("chinese_number,expected", CHINESE_NUMBER_TEST_CASES)
def test_chinese_number_parsing(chinese_number, expected):
    """Test parsing of Chinese number formats."""
    result = parse_chinese_number(chinese_number)
    assert result == expected
```

### Complex Number Combinations

```python
def test_chinese_complex_numbers():
    """Test complex Chinese number combinations."""
    complex_cases = [
        # Formal written numbers
        ("一千五百万", 15000000),
        ("三千二百五十万", 32500000),
        ("九万八千七百", 98700),
        
        # Mixed with currency
        ("约束为一万五千元", 15000),
        ("限制是2万5千人民币", 25000),
        
        # Decimal combinations (less common but possible)
        ("一点五万", 15000),        # 1.5 * 10000
        ("三点二万", 32000),        # 3.2 * 10000
    ]
    
    for text, expected in complex_cases:
        result = extract_number_from_chinese_text(text)
        assert result == expected
```

## Currency Handling

### Chinese Currency Formats

```python
CHINESE_CURRENCY_FORMATS = [
    # Yuan symbol variations
    ("¥15,000", 15000, "CNY"),
    ("￥15,000", 15000, "CNY"),  # Full-width yuan symbol
    ("15000元", 15000, "CNY"),
    ("15000人民币", 15000, "CNY"),
    ("15,000 RMB", 15000, "CNY"),
    ("CNY 15,000", 15000, "CNY"),
    
    # Mixed format with Chinese numerals
    ("¥一万五千", 15000, "CNY"),
    ("2万元", 20000, "CNY"),
    ("十五万人民币", 150000, "CNY"),
    
    # Hong Kong/Taiwan dollars  
    ("HK$15,000", 15000, "HKD"),
    ("NT$15,000", 15000, "TWD"),
]

@pytest.mark.parametrize("currency_text,expected_amount,currency_code", CHINESE_CURRENCY_FORMATS)
def test_chinese_currency_parsing(currency_text, expected_amount, currency_code):
    """Test parsing of various Chinese currency formats."""
    result = parse_chinese_currency(currency_text)
    assert result["amount"] == expected_amount
    assert result["currency"] == currency_code
```

## Agreement and Disagreement Patterns

### Agreement Patterns

```python
CHINESE_AGREEMENT_PATTERNS = [
    # Strong agreement
    "我同意",                   # I agree
    "我完全同意",               # I completely agree
    "我赞成",                   # I approve/support
    "我支持",                   # I support
    "没问题",                   # No problem
    "好的",                     # Good/OK
    "可以",                     # OK/Can do
    "行",                       # OK (informal)
    "对",                       # Right/Correct
    "是的",                     # Yes
    
    # Conditional agreement
    "如果...我同意",            # If... I agree
    "我基本同意",               # I basically agree
    "我大致同意",               # I generally agree
    "在这种情况下我同意",       # In this case I agree
    
    # Formal agreement
    "我赞同这个提议",           # I endorse this proposal
    "我接受这个方案",           # I accept this plan
    "我认为这是正确的",         # I think this is correct
]
```

### Disagreement Patterns

```python
CHINESE_DISAGREEMENT_PATTERNS = [
    # Strong disagreement
    "我不同意",                 # I disagree
    "我反对",                   # I oppose
    "我拒绝",                   # I refuse
    "不行",                     # No way
    "不可以",                   # Cannot/Not allowed
    "我不赞成",                 # I don't approve
    "我不支持",                 # I don't support
    
    # Soft disagreement  
    "我不太同意",               # I don't really agree
    "我有不同看法",             # I have a different view
    "我觉得不太好",             # I think it's not very good
    "我有些担心",               # I have some concerns
    "这样不太合适",             # This is not quite appropriate
    
    # Questioning disagreement
    "这样真的好吗？",           # Is this really good?
    "我们是否应该重新考虑？",   # Should we reconsider?
    "也许还有更好的方案？",     # Maybe there's a better plan?
]
```

## Vote Intention Detection

### Voting Trigger Phrases

```python
CHINESE_VOTE_PATTERNS = [
    # Direct voting calls
    "我们投票吧",               # Let's vote
    "现在投票",                 # Vote now
    "开始投票",                 # Start voting
    "进行投票",                 # Proceed with voting
    "我提议投票",               # I propose we vote
    "该投票了",                 # It's time to vote
    "我们做决定吧",             # Let's make a decision
    "表决吧",                   # Let's vote (formal)
    
    # Vote declarations
    "我投票给",                 # I vote for
    "我选择",                   # I choose
    "我的选择是",               # My choice is
    "我决定选择",               # I decide to choose
    "我支持",                   # I support (can indicate vote)
    
    # Formal voting language
    "开始投票程序",             # Start voting procedure
    "进入投票环节",             # Enter voting phase
    "我们来表决",               # Let's vote (formal)
]
```

### Non-Voting Phrases

```python
CHINESE_NON_VOTE_PATTERNS = [
    # Questions about voting
    "我们应该投票吗？",         # Should we vote?
    "是否需要投票？",           # Do we need to vote?
    "什么时候投票？",           # When should we vote?
    
    # Conditional statements
    "如果我们投票",             # If we vote
    "投票之前",                 # Before voting
    "投票之后",                 # After voting
    "当我们投票时",             # When we vote
    
    # Discussion continuation
    "我们需要更多讨论",         # We need more discussion
    "还没准备好投票",           # Not ready to vote yet
    "让我们继续讨论",           # Let's continue discussing
    "需要更多时间考虑",         # Need more time to consider
]
```

## Pinyin Fallback Handling

### Pinyin Recognition

Sometimes users might input Pinyin (romanized Chinese) instead of characters:

```python
PINYIN_TO_CHINESE_MAPPINGS = {
    # Principle terms
    "zuida hua": "最大化",           # maximize
    "zuixiao": "最小",               # minimum
    "pingjun": "平均",               # average
    "shouru": "收入",                # income
    "yueshu": "约束",                # constraint
    
    # Agreement terms
    "tongyi": "同意",                # agree
    "zhancheng": "赞成",             # support
    "fandui": "反对",                # oppose
    
    # Voting terms  
    "toupiao": "投票",               # vote
    "jueding": "决定",               # decide
    "xuanze": "选择",                # choose
}

@pytest.mark.parametrize("pinyin_input,expected_chinese", [
    ("wo tongyi", "我同意"),         # I agree
    ("women toupiao ba", "我们投票吧"), # Let's vote
    ("zuida hua pingjun shouru", "最大化平均收入"), # Maximize average income
])
def test_pinyin_fallback(pinyin_input, expected_chinese):
    """Test Pinyin to Chinese conversion fallback."""
    result = convert_pinyin_to_chinese(pinyin_input)
    assert expected_chinese in result or result == expected_chinese
```

## Common Edge Cases

### Edge Case 1: Mixed Script Input

```python
def test_chinese_mixed_script():
    """Test handling of mixed Chinese, English, and numbers."""
    mixed_cases = [
        "我选择maximizing average income",
        "约束为$15,000美元",
        "我同意floor constraint方案",
        "投票选择principle 3",
    ]
    
    for case in mixed_cases:
        result = parse_chinese_mixed_input(case)
        assert result is not None
        assert "error" not in str(result).lower()
```

### Edge Case 2: Punctuation Sensitivity

```python
def test_chinese_punctuation_handling():
    """Test proper handling of Chinese punctuation."""
    punctuation_cases = [
        ("我同意。", "我同意"),           # Chinese period
        ("好的，我支持", "好的我支持"),   # Chinese comma
        ("投票吧！", "投票吧"),           # Chinese exclamation
        ("这样可以吗？", "这样可以吗"),   # Chinese question mark
    ]
    
    for with_punct, without_punct in punctuation_cases:
        result_with = parse_chinese_text(with_punct)
        result_without = parse_chinese_text(without_punct) 
        # Should parse similarly regardless of punctuation
        assert normalize_result(result_with) == normalize_result(result_without)
```

### Edge Case 3: Regional Variants

```python
def test_chinese_regional_variants():
    """Test handling of regional Chinese variations."""
    regional_cases = [
        # Mainland vs Taiwan/Hong Kong terms
        ("计算机", "電腦"),              # computer  
        ("软件", "軟體"),                # software
        ("信息", "資訊"),                # information
        ("网络", "網路"),                # network
        
        # Different expressions for same concept
        ("没问题", "没有问题"),           # no problem
        ("可以", "行"),                   # OK/possible
    ]
    
    for variant1, variant2 in regional_cases:
        result1 = parse_chinese_text(f"我同意{variant1}")
        result2 = parse_chinese_text(f"我同意{variant2}")
        # Should understand both variants
        assert result1 is not None
        assert result2 is not None
```

## Testing Examples

### Complete Chinese Test Class

```python
import pytest
from utils.language_manager import LanguageManager

class TestChineseParsing:
    """Comprehensive Chinese language parsing tests."""
    
    @pytest.fixture
    def chinese_language_manager(self):
        return LanguageManager("Mandarin")
    
    @pytest.mark.parametrize("principle_text,expected", [
        ("最大化最低收入", "Maximizing the floor income"),
        ("最大化平均收入", "Maximizing the average income"),
        ("最大化平均收入并设置最低限制", "Maximizing the average income with a floor constraint"),
        ("最大化平均收入并设置范围限制", "Maximizing the average income with a range constraint"),
    ])
    def test_chinese_principle_parsing(self, principle_text, expected, chinese_language_manager):
        result = chinese_language_manager.parse_principle(principle_text)
        assert result == expected
    
    @pytest.mark.parametrize("constraint_text,expected_value", [
        ("约束为¥15,000", 15000),
        ("限制是2万元", 20000),
        ("最高25万人民币", 250000),
        ("无限制", None),
        ("没有约束", None),
    ])
    def test_chinese_constraint_parsing(self, constraint_text, expected_value, chinese_language_manager):
        result = chinese_language_manager.parse_constraint(constraint_text)
        assert result == expected_value
    
    @pytest.mark.parametrize("agreement_text,expected", [
        ("我同意", True),
        ("我不同意", False),
        ("我赞成这个提议", True),
        ("我反对这个方案", False),
        ("好的", True),
        ("不行", False),
    ])
    def test_chinese_agreement_detection(self, agreement_text, expected, chinese_language_manager):
        result = chinese_language_manager.detect_agreement(agreement_text)
        assert result == expected
    
    @pytest.mark.parametrize("vote_text,should_trigger_vote", [
        ("我们投票吧", True),
        ("现在开始投票", True),
        ("我们应该投票吗？", False),
        ("投票之前", False),
        ("我投票给", True),
    ])
    def test_chinese_vote_detection(self, vote_text, should_trigger_vote, chinese_language_manager):
        result = chinese_language_manager.detect_vote_intention(vote_text)
        assert result == should_trigger_vote
        
    def test_chinese_utf8_integrity(self):
        """Test UTF-8 encoding integrity throughout processing."""
        chinese_texts = [
            "最大化最低收入约束为¥15,000",
            "我完全同意这个提议",
            "让我们投票决定",
        ]
        
        for text in chinese_texts:
            # Ensure text survives encoding round-trip
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert text == decoded
            
            # Ensure processing doesn't corrupt text
            result = parse_chinese_text(text)
            assert result is not None
```

### Performance Testing

```python
def test_chinese_character_processing_performance():
    """Test performance with large amounts of Chinese text."""
    import time
    
    large_chinese_text = "最大化平均收入并设置范围约束¥25,000我完全同意这个提议让我们投票" * 100
    
    start_time = time.time()
    result = parse_chinese_text(large_chinese_text)
    end_time = time.time()
    
    processing_time = end_time - start_time
    assert processing_time < 5.0  # Should complete within 5 seconds
    assert result is not None
```

## Quick Reference

### Command Line Testing

```bash
# Run Chinese-specific tests
pytest tests/ -k "chinese or mandarin" -v

# Run with Chinese language parameter  
pytest tests/ -k "multilingual" --language=Mandarin -v

# Test Chinese edge cases
pytest tests/ -k "chinese and edge_case" -v

# Test UTF-8 handling
pytest tests/ -k "chinese and utf8" -v
```

### Test Data Files

- `tests/fixtures/chinese_test_data.json` - Static Chinese test cases
- `translations/mandarin_prompts.json` - Chinese language prompts  
- `tests/fixtures/chinese_number_mappings.json` - Chinese numeral mappings
- `tests/fixtures/pinyin_fallback_data.json` - Pinyin conversion data

### Debugging Chinese Issues

```python
# Check character encoding
def debug_chinese_encoding(text):
    print(f"Original: {text}")
    print(f"UTF-8 bytes: {text.encode('utf-8')}")
    print(f"Character codes: {[ord(c) for c in text]}")
    print(f"Is valid UTF-8: {text.encode('utf-8').decode('utf-8') == text}")

# Check character classification
def debug_chinese_characters(text):
    for char in text:
        print(f"'{char}': Chinese={is_chinese_character(char)}, "
              f"Code={ord(char)}, UTF-8={char.encode('utf-8')}")
```

---

*Created as part of Subplan 7: Documentation and Training Materials*
*Version 1.0 - Chinese Test Patterns Guide*