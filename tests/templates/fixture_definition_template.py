"""
Fixture Definition Template for Language-Specific Data

Template for creating pytest fixtures that provide language-specific test data
for the Frohlich Experiment system.

Usage:
    cp tests/templates/fixture_definition_template.py tests/fixtures/your_fixture.py
    
Then customize the fixture definitions for your specific test data needs.
"""

import pytest
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Import your modules here - customize as needed
# from utils.language_manager import LanguageManager
# from models.principle_types import VALID_PRINCIPLES


class MultilingualFixtureTemplate:
    """
    Template class for organizing multilingual test fixtures.
    
    This class provides structured access to language-specific test data
    and helper methods for fixture management.
    """
    
    # =============================================================================
    # Core Language Data Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def supported_languages(self):
        """List of supported languages for testing."""
        return ["English", "Spanish", "Mandarin"]
    
    @pytest.fixture(scope="session")
    def language_codes(self):
        """Language code mappings."""
        return {
            "English": "en",
            "Spanish": "es", 
            "Mandarin": "zh"
        }
    
    @pytest.fixture(scope="session")
    def multilingual_principle_data(self):
        """
        Complete principle definitions across all languages.
        
        Customize this with your actual justice principles.
        """
        return {
            "English": {
                "Maximizing the floor income": {
                    "canonical_name": "Maximizing the floor income",
                    "variations": [
                        "maximizing the floor income",
                        "maximizing floor income",
                        "maximize the floor income",
                        "floor income maximization"
                    ],
                    "description": "Maximizes the lowest income in society"
                },
                "Maximizing the average income": {
                    "canonical_name": "Maximizing the average income",
                    "variations": [
                        "maximizing the average income",
                        "maximizing average income", 
                        "maximize the average income",
                        "average income maximization"
                    ],
                    "description": "Maximizes the average income in society"
                },
                "Maximizing the average income with a floor constraint": {
                    "canonical_name": "Maximizing the average income with a floor constraint",
                    "variations": [
                        "maximizing the average income with a floor constraint",
                        "maximizing average income with floor constraint",
                        "average income maximization with floor constraint"
                    ],
                    "description": "Maximizes average while ensuring minimum income"
                },
                "Maximizing the average income with a range constraint": {
                    "canonical_name": "Maximizing the average income with a range constraint", 
                    "variations": [
                        "maximizing the average income with a range constraint",
                        "maximizing average income with range constraint",
                        "average income maximization with range constraint"
                    ],
                    "description": "Maximizes average while limiting income gap"
                }
            },
            "Spanish": {
                "Maximizing the floor income": {
                    "canonical_name": "Maximizing the floor income",
                    "variations": [
                        "maximización del ingreso mínimo",
                        "maximización del salario mínimo",
                        "maximización del ingreso base",
                        "maximizando el ingreso mínimo",
                        "maximizar el piso de ingresos"
                    ],
                    "description": "Maximiza el ingreso más bajo de la sociedad"
                },
                "Maximizing the average income": {
                    "canonical_name": "Maximizing the average income",
                    "variations": [
                        "maximización del ingreso promedio",
                        "maximización del ingreso medio",
                        "maximización de la media de ingresos",
                        "maximizando el ingreso promedio"
                    ],
                    "description": "Maximiza el ingreso promedio de la sociedad"
                },
                "Maximizing the average income with a floor constraint": {
                    "canonical_name": "Maximizing the average income with a floor constraint",
                    "variations": [
                        "maximización del ingreso promedio con restricción de mínimo",
                        "maximización del ingreso promedio con límite inferior",
                        "maximización del ingreso medio con restricción de piso"
                    ],
                    "description": "Maximiza el promedio asegurando un ingreso mínimo"
                },
                "Maximizing the average income with a range constraint": {
                    "canonical_name": "Maximizing the average income with a range constraint",
                    "variations": [
                        "maximización del ingreso promedio con restricción de rango",
                        "maximización del ingreso promedio con límite de distancia", 
                        "maximización del ingreso medio con restricción de alcance"
                    ],
                    "description": "Maximiza el promedio limitando la brecha de ingresos"
                }
            },
            "Mandarin": {
                "Maximizing the floor income": {
                    "canonical_name": "Maximizing the floor income",
                    "variations": [
                        "最大化最低收入",
                        "最大化收入底线",
                        "最低收入最大化",
                        "收入底线最大化"
                    ],
                    "description": "最大化社会中的最低收入"
                },
                "Maximizing the average income": {
                    "canonical_name": "Maximizing the average income",
                    "variations": [
                        "最大化平均收入",
                        "平均收入最大化",
                        "最大化收入平均值",
                        "收入平均值最大化"
                    ],
                    "description": "最大化社会的平均收入"
                },
                "Maximizing the average income with a floor constraint": {
                    "canonical_name": "Maximizing the average income with a floor constraint",
                    "variations": [
                        "最大化平均收入并设置最低限制",
                        "带最低约束的平均收入最大化",
                        "在最低收入约束下最大化平均收入"
                    ],
                    "description": "在确保最低收入的同时最大化平均收入"
                },
                "Maximizing the average income with a range constraint": {
                    "canonical_name": "Maximizing the average income with a range constraint",
                    "variations": [
                        "最大化平均收入并设置范围限制",
                        "带范围约束的平均收入最大化",
                        "在收入范围约束下最大化平均收入"
                    ],
                    "description": "在限制收入差距的同时最大化平均收入"
                }
            }
        }
    
    # =============================================================================
    # Agreement/Disagreement Pattern Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session") 
    def multilingual_agreement_patterns(self):
        """Agreement and disagreement patterns for all languages."""
        return {
            "English": {
                "strong_agreement": [
                    "I completely agree",
                    "I fully support this",
                    "Absolutely, yes",
                    "This is perfect",
                    "I'm 100% on board"
                ],
                "mild_agreement": [
                    "I agree",
                    "I support this",
                    "Yes, that works",
                    "I'm okay with this",
                    "This seems reasonable"
                ],
                "conditional_agreement": [
                    "I agree if we modify X",
                    "I support this with conditions",
                    "Yes, but only if...",
                    "I'm okay with this provided that...",
                    "I agree assuming..."
                ],
                "mild_disagreement": [
                    "I'm not sure about this",
                    "I have some concerns",
                    "This might not work",
                    "I'm hesitant about this",
                    "I have reservations"
                ],
                "strong_disagreement": [
                    "I completely disagree",
                    "I strongly oppose this",
                    "Absolutely not",
                    "This is unacceptable",
                    "I cannot support this"
                ]
            },
            "Spanish": {
                "strong_agreement": [
                    "Estoy completamente de acuerdo",
                    "Apoyo totalmente esto",
                    "Absolutamente, sí",
                    "Esto es perfecto",
                    "Estoy 100% de acuerdo"
                ],
                "mild_agreement": [
                    "Estoy de acuerdo",
                    "Apoyo esto",
                    "Sí, eso funciona",
                    "Me parece bien",
                    "Esto parece razonable"
                ],
                "conditional_agreement": [
                    "Estoy de acuerdo si modificamos X",
                    "Apoyo esto con condiciones",
                    "Sí, pero solo si...",
                    "Me parece bien siempre que...",
                    "Estoy de acuerdo asumiendo que..."
                ],
                "mild_disagreement": [
                    "No estoy seguro de esto",
                    "Tengo algunas preocupaciones", 
                    "Esto podría no funcionar",
                    "Tengo dudas sobre esto",
                    "Tengo reservas"
                ],
                "strong_disagreement": [
                    "No estoy de acuerdo en absoluto",
                    "Me opongo fuertemente a esto",
                    "Absolutamente no",
                    "Esto es inaceptable", 
                    "No puedo apoyar esto"
                ]
            },
            "Mandarin": {
                "strong_agreement": [
                    "我完全同意",
                    "我完全支持这个",
                    "绝对同意",
                    "这很完美",
                    "我百分百赞成"
                ],
                "mild_agreement": [
                    "我同意",
                    "我支持这个",
                    "是的，可以",
                    "我觉得可以",
                    "这看起来合理"
                ],
                "conditional_agreement": [
                    "如果我们修改X，我同意",
                    "我有条件地支持这个",
                    "是的，但只有在...",
                    "只要...我就同意",
                    "假设...我同意"
                ],
                "mild_disagreement": [
                    "我不确定这个",
                    "我有一些担心",
                    "这可能不行",
                    "我对此有疑虑",
                    "我有保留意见"
                ],
                "strong_disagreement": [
                    "我完全不同意",
                    "我强烈反对这个",
                    "绝对不行",
                    "这是不可接受的",
                    "我不能支持这个"
                ]
            }
        }
    
    # =============================================================================
    # Vote Intention Pattern Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def multilingual_voting_patterns(self):
        """Voting intention patterns for all languages."""
        return {
            "English": {
                "vote_triggers": [
                    "Let's vote now",
                    "I propose we vote",
                    "Time to vote",
                    "We should vote",
                    "Let's make a decision",
                    "I suggest we decide",
                    "Let's put it to a vote"
                ],
                "vote_declarations": [
                    "I vote for",
                    "My vote is",
                    "I choose",
                    "My choice is",
                    "I'm voting for",
                    "I select",
                    "My decision is"
                ],
                "non_vote_patterns": [
                    "Should we vote?",
                    "When should we vote?",
                    "Before we vote",
                    "After voting",
                    "If we vote",
                    "Maybe we should vote",
                    "We might need to vote"
                ]
            },
            "Spanish": {
                "vote_triggers": [
                    "Votemos ahora",
                    "Propongo que votemos",
                    "Es hora de votar",
                    "Deberíamos votar",
                    "Tomemos una decisión",
                    "Sugiero que decidamos",
                    "Pongámoslo a votación"
                ],
                "vote_declarations": [
                    "Voto por",
                    "Mi voto es",
                    "Elijo",
                    "Mi elección es",
                    "Estoy votando por",
                    "Selecciono",
                    "Mi decisión es"
                ],
                "non_vote_patterns": [
                    "¿Deberíamos votar?",
                    "¿Cuándo deberíamos votar?",
                    "Antes de votar",
                    "Después de votar",
                    "Si votamos",
                    "Tal vez deberíamos votar",
                    "Podríamos necesitar votar"
                ]
            },
            "Mandarin": {
                "vote_triggers": [
                    "我们现在投票吧",
                    "我建议我们投票",
                    "是时候投票了",
                    "我们应该投票",
                    "让我们做决定",
                    "我建议我们决定",
                    "我们投票表决吧"
                ],
                "vote_declarations": [
                    "我投票给",
                    "我的票是",
                    "我选择",
                    "我的选择是",
                    "我投票支持",
                    "我选定",
                    "我的决定是"
                ],
                "non_vote_patterns": [
                    "我们应该投票吗？",
                    "我们什么时候投票？",
                    "投票之前",
                    "投票之后",
                    "如果我们投票",
                    "也许我们应该投票",
                    "我们可能需要投票"
                ]
            }
        }
    
    # =============================================================================
    # Number and Currency Format Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def multilingual_number_formats(self):
        """Number format patterns for different languages/regions."""
        return {
            "English": {
                "format_type": "US",
                "thousands_separator": ",",
                "decimal_separator": ".",
                "currency_symbol": "$",
                "examples": [
                    {"text": "15,000", "value": 15000},
                    {"text": "1,500.75", "value": 1500.75},
                    {"text": "$15,000", "value": 15000},
                    {"text": "constraint of $15,000", "value": 15000}
                ]
            },
            "Spanish": {
                "format_type": "Mixed",
                "european_format": {
                    "thousands_separator": ".",
                    "decimal_separator": ",",
                    "currency_symbol": "€",
                    "examples": [
                        {"text": "15.000", "value": 15000},
                        {"text": "1.500,75", "value": 1500.75},
                        {"text": "€15.000", "value": 15000},
                        {"text": "restricción de €15.000", "value": 15000}
                    ]
                },
                "latin_american_format": {
                    "thousands_separator": ",",
                    "decimal_separator": ".",
                    "currency_symbols": ["$", "MXN", "ARS", "COP"],
                    "examples": [
                        {"text": "15,000", "value": 15000},
                        {"text": "1,500.75", "value": 1500.75},
                        {"text": "$15,000", "value": 15000},
                        {"text": "MXN 15,000", "value": 15000},
                        {"text": "límite de $15,000", "value": 15000}
                    ]
                }
            },
            "Mandarin": {
                "format_type": "Chinese",
                "thousands_separator": ",",
                "decimal_separator": ".",
                "currency_symbols": ["¥", "￥", "元", "RMB", "CNY"],
                "chinese_numerals": {
                    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                    "百": 100, "千": 1000, "万": 10000
                },
                "examples": [
                    {"text": "15,000", "value": 15000},
                    {"text": "¥15,000", "value": 15000},
                    {"text": "15000元", "value": 15000},
                    {"text": "一万五千", "value": 15000},
                    {"text": "2万", "value": 20000},
                    {"text": "约束为¥15,000", "value": 15000}
                ]
            }
        }
    
    # =============================================================================
    # Edge Case and Error Scenario Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def multilingual_edge_cases(self):
        """Edge cases and challenging inputs for each language."""
        return {
            "English": {
                "empty_inputs": ["", "   ", "\n", "\t", None],
                "malformed_inputs": [
                    "I agre",  # Typo
                    "constraint of $15,00",  # Malformed number
                    "maximizing the floor",  # Incomplete principle
                    "yes no maybe",  # Ambiguous
                ],
                "boundary_cases": [
                    "I agree" * 1000,  # Very long input
                    "a",  # Single character
                    "I agree.",  # With punctuation
                    "I AGREE",  # All caps
                ]
            },
            "Spanish": {
                "empty_inputs": ["", "   ", "\n", "\t", None],
                "accent_variations": [
                    ("maximización", "maximizacion"),
                    ("restricción", "restriccion"), 
                    ("decisión", "decision"),
                    ("está bien", "esta bien")
                ],
                "regional_variations": [
                    ("vale", "Spain"),
                    ("órale", "Mexico"), 
                    ("bueno", "General"),
                    ("listo", "Latin America")
                ],
                "malformed_inputs": [
                    "estoy de acurdo",  # Typo
                    "restricción de €15.00",  # Wrong decimal format
                    "maximización del",  # Incomplete
                ]
            },
            "Mandarin": {
                "empty_inputs": ["", "   ", "\n", "\t", None],
                "character_encoding_tests": [
                    "最大化最低收入",  # Standard characters
                    "測試編碼問題",    # Traditional characters mixed
                    "test混合scripts", # Mixed scripts
                    "🎉💯🔥",          # Emojis
                ],
                "simplified_traditional_pairs": [
                    ("约束", "約束"),
                    ("决定", "決定"),
                    ("万", "萬")
                ],
                "malformed_inputs": [
                    "我同意这个",  # Incomplete
                    "约束为¥15,00",  # Malformed number
                    "最大化",  # Too short
                ]
            }
        }
    
    # =============================================================================
    # Performance Testing Data Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def multilingual_performance_data(self):
        """Performance testing data sets for different languages."""
        return {
            "small_dataset": {
                "size": 10,
                "English": self._generate_test_strings("I agree with this", 10),
                "Spanish": self._generate_test_strings("Estoy de acuerdo", 10),
                "Mandarin": self._generate_test_strings("我同意", 10)
            },
            "medium_dataset": {
                "size": 100,
                "English": self._generate_test_strings("I agree with this", 100),
                "Spanish": self._generate_test_strings("Estoy de acuerdo", 100), 
                "Mandarin": self._generate_test_strings("我同意", 100)
            },
            "large_dataset": {
                "size": 1000,
                "English": self._generate_test_strings("I agree with this", 1000),
                "Spanish": self._generate_test_strings("Estoy de acuerdo", 1000),
                "Mandarin": self._generate_test_strings("我同意", 1000)
            }
        }
    
    # =============================================================================
    # Parameterized Fixture Generators
    # =============================================================================
    
    @pytest.fixture(params=["English", "Spanish", "Mandarin"])
    def language(self, request):
        """Parameterized language fixture."""
        return request.param
    
    @pytest.fixture(params=["small_dataset", "medium_dataset", "large_dataset"])
    def dataset_size(self, request):
        """Parameterized dataset size fixture."""
        return request.param
    
    @pytest.fixture
    def language_test_data(self, language, multilingual_principle_data):
        """Get test data for a specific language."""
        return multilingual_principle_data[language]
    
    @pytest.fixture
    def agreement_patterns_for_language(self, language, multilingual_agreement_patterns):
        """Get agreement patterns for a specific language."""
        return multilingual_agreement_patterns[language]
    
    @pytest.fixture
    def voting_patterns_for_language(self, language, multilingual_voting_patterns):
        """Get voting patterns for a specific language.""" 
        return multilingual_voting_patterns[language]
    
    # =============================================================================
    # Dynamic Fixture Generators
    # =============================================================================
    
    @pytest.fixture
    def principle_variations_for_testing(self, language, multilingual_principle_data):
        """Generate all principle variations for testing."""
        language_data = multilingual_principle_data[language]
        test_cases = []
        
        for canonical_principle, data in language_data.items():
            # Add canonical form
            test_cases.append({
                "input": data["canonical_name"],
                "expected": canonical_principle,
                "variation_type": "canonical"
            })
            
            # Add variations
            for variation in data["variations"]:
                test_cases.append({
                    "input": variation,
                    "expected": canonical_principle,
                    "variation_type": "variation"
                })
        
        return test_cases
    
    @pytest.fixture
    def cross_language_principle_mapping(self, multilingual_principle_data):
        """Create mapping of principles across languages."""
        mapping = {}
        
        for canonical_principle in multilingual_principle_data["English"].keys():
            mapping[canonical_principle] = {}
            
            for language in ["English", "Spanish", "Mandarin"]:
                if canonical_principle in multilingual_principle_data[language]:
                    lang_data = multilingual_principle_data[language][canonical_principle]
                    mapping[canonical_principle][language] = {
                        "canonical": lang_data["canonical_name"],
                        "variations": lang_data["variations"],
                        "description": lang_data["description"]
                    }
        
        return mapping
    
    # =============================================================================
    # File-Based Fixture Loaders
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def load_fixture_from_file(self):
        """Factory for loading fixtures from JSON files."""
        def load_fixture(filename: str, fixture_dir: str = "tests/fixtures") -> Dict[str, Any]:
            filepath = Path(fixture_dir) / f"{filename}.json"
            
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Return empty dict if file doesn't exist
                return {}
        
        return load_fixture
    
    @pytest.fixture(scope="session")
    def save_fixture_to_file(self):
        """Factory for saving fixtures to JSON files."""
        def save_fixture(data: Dict[str, Any], filename: str, fixture_dir: str = "tests/fixtures"):
            fixture_path = Path(fixture_dir)
            fixture_path.mkdir(exist_ok=True)
            
            filepath = fixture_path / f"{filename}.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return save_fixture
    
    # =============================================================================
    # Validation and Quality Fixtures
    # =============================================================================
    
    @pytest.fixture(scope="session")
    def fixture_quality_validator(self):
        """Validator for fixture data quality."""
        def validate_fixture_quality(fixture_data: Dict[str, Any]) -> Dict[str, Any]:
            """Validate fixture data for completeness and consistency."""
            validation_results = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "stats": {}
            }
            
            # Check for required languages
            required_languages = {"English", "Spanish", "Mandarin"}
            if isinstance(fixture_data, dict):
                available_languages = set(fixture_data.keys())
                missing_languages = required_languages - available_languages
                
                if missing_languages:
                    validation_results["errors"].append(
                        f"Missing languages: {missing_languages}"
                    )
                    validation_results["is_valid"] = False
                
                # Check data consistency across languages
                english_keys = set()
                if "English" in fixture_data and isinstance(fixture_data["English"], dict):
                    english_keys = set(fixture_data["English"].keys())
                
                for language in available_languages:
                    if isinstance(fixture_data[language], dict):
                        lang_keys = set(fixture_data[language].keys())
                        if english_keys and lang_keys != english_keys:
                            validation_results["warnings"].append(
                                f"{language} has different keys than English"
                            )
                
                # Generate statistics
                validation_results["stats"] = {
                    "total_languages": len(available_languages),
                    "total_items_per_language": {
                        lang: len(data) if isinstance(data, (dict, list)) else 1
                        for lang, data in fixture_data.items()
                    }
                }
            
            return validation_results
        
        return validate_fixture_quality
    
    # =============================================================================
    # Helper Methods
    # =============================================================================
    
    def _generate_test_strings(self, base_string: str, count: int) -> List[str]:
        """Generate test strings for performance testing."""
        return [f"{base_string} {i}" for i in range(count)]
    
    def _normalize_language_key(self, language: str) -> str:
        """Normalize language key for consistent access."""
        language_mappings = {
            "en": "English",
            "es": "Spanish", 
            "zh": "Mandarin",
            "chinese": "Mandarin",
            "mandarin": "Mandarin",
            "spanish": "Spanish",
            "english": "English"
        }
        
        return language_mappings.get(language.lower(), language)
    
    def _validate_utf8_integrity(self, text: str) -> bool:
        """Validate UTF-8 encoding integrity."""
        try:
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            return text == decoded
        except (UnicodeEncodeError, UnicodeDecodeError):
            return False


# =============================================================================
# Standalone Fixtures (can be used without class)
# =============================================================================

@pytest.fixture(scope="session")
def multilingual_test_principles():
    """Standalone fixture for principle test data."""
    fixture_manager = MultilingualFixtureTemplate()
    return fixture_manager.multilingual_principle_data()


@pytest.fixture(scope="session") 
def multilingual_test_agreements():
    """Standalone fixture for agreement test data."""
    fixture_manager = MultilingualFixtureTemplate()
    return fixture_manager.multilingual_agreement_patterns()


@pytest.fixture(scope="session")
def multilingual_test_voting():
    """Standalone fixture for voting test data."""
    fixture_manager = MultilingualFixtureTemplate()
    return fixture_manager.multilingual_voting_patterns()


@pytest.fixture(scope="session")
def multilingual_test_numbers():
    """Standalone fixture for number format test data."""
    fixture_manager = MultilingualFixtureTemplate()
    return fixture_manager.multilingual_number_formats()


# =============================================================================
# Configuration and Utility Functions
# =============================================================================

def pytest_configure(config):
    """Configure pytest with multilingual fixture markers."""
    config.addinivalue_line(
        "markers",
        "multilingual_fixture: mark test as using multilingual fixtures"
    )
    config.addinivalue_line(
        "markers", 
        "fixture_validation: mark test as fixture validation test"
    )


def validate_all_fixtures():
    """Validate all multilingual fixtures for quality and consistency."""
    fixture_manager = MultilingualFixtureTemplate()
    validator = fixture_manager.fixture_quality_validator()
    
    fixtures_to_validate = [
        ("principle_data", fixture_manager.multilingual_principle_data()),
        ("agreement_patterns", fixture_manager.multilingual_agreement_patterns()),
        ("voting_patterns", fixture_manager.multilingual_voting_patterns()),
        ("number_formats", fixture_manager.multilingual_number_formats()),
        ("edge_cases", fixture_manager.multilingual_edge_cases())
    ]
    
    validation_report = {}
    
    for fixture_name, fixture_data in fixtures_to_validate:
        validation_report[fixture_name] = validator(fixture_data)
    
    return validation_report


# =============================================================================
# Usage Instructions and Examples
# =============================================================================

"""
USAGE INSTRUCTIONS:

1. Copy this template:
   cp tests/templates/fixture_definition_template.py tests/fixtures/your_fixtures.py

2. Customize the fixture data for your specific needs:
   - Replace principle data with your actual principles
   - Update agreement patterns for your domain
   - Modify currency and number formats as needed
   - Add domain-specific edge cases

3. Common usage patterns:

   # Basic parameterized test with language fixture:
   def test_feature(self, language, language_test_data):
       data = language_test_data[language]
       # Use data for testing
   
   # Using specific pattern fixtures:
   def test_agreements(self, agreement_patterns_for_language):
       for pattern in agreement_patterns_for_language["strong_agreement"]:
           result = detect_agreement(pattern)
           assert result is True
   
   # Cross-language validation:
   def test_cross_language(self, cross_language_principle_mapping):
       for principle, translations in cross_language_principle_mapping.items():
           # Validate consistency across languages

4. File-based fixtures (for large datasets):
   # Save fixture data to file:
   save_fixture = save_fixture_to_file()
   save_fixture(my_data, "my_test_data")
   
   # Load fixture data from file:
   load_fixture = load_fixture_from_file()
   test_data = load_fixture("my_test_data")

5. Validate fixture quality:
   python -c "from tests.fixtures.your_fixtures import validate_all_fixtures; print(validate_all_fixtures())"

EXAMPLE CUSTOMIZATION:

# Custom principle fixture for your domain:
@pytest.fixture(scope="session")
def custom_principle_data(self):
    return {
        "English": {
            "Your Principle 1": {
                "canonical_name": "Your Principle 1",
                "variations": ["variation 1", "variation 2"],
                "description": "Description of principle"
            }
        },
        # Add Spanish and Mandarin translations
    }

# Custom agreement patterns:
@pytest.fixture(scope="session")
def domain_specific_agreements(self):
    return {
        "English": {
            "technical_agreement": ["looks good technically", "implementation is sound"],
            "business_agreement": ["makes business sense", "financially viable"]
        }
        # Add other languages
    }

Remember to:
- Keep fixture data synchronized across languages
- Include both positive and negative test cases
- Add edge cases specific to your domain
- Validate UTF-8 encoding for Chinese text
- Test regional variations for Spanish
- Include performance test data for benchmarking
- Document any domain-specific patterns
"""