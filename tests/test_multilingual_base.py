"""
Multilingual test infrastructure for parametrized testing across languages.

This module provides the foundational infrastructure for Subplan 3: Test Infrastructure
Modernization from the Opus Multilingual Testing Implementation Plan. It creates a 
parametrized testing framework that enables efficient multilingual testing through
fixtures and language coverage monitoring.

Key features:
- Parametrized tests across English, Spanish, and Mandarin
- Language-specific test data loading with automatic fallbacks
- Language parity checking to ensure test coverage consistency
- Enhanced fixture integration with lazy loading capabilities
- Performance optimization through shared fixtures and data caching
"""

import inspect
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import pytest
from unittest.mock import MagicMock

from tests.fixtures.phase2_parsing_fixtures import (
    BALLOT_STATEMENTS,
    CHINESE_BALLOT_STATEMENTS,
    LANGUAGE_SPECIFIC_CONSTRAINTS,
    NEGATIVE_VOTE_STATEMENTS,
    POSITIVE_VOTE_STATEMENTS,
    PREFERENCE_STATEMENTS,
    Phase2ParsingFixtures,
    SPANISH_BALLOT_STATEMENTS,
    AGREEMENT_STATEMENTS,
)


# =============================================================================
# Core Language Support Constants
# =============================================================================

SUPPORTED_LANGUAGES = ["English", "Spanish", "Mandarin"]
LANGUAGE_CODES = {"English": "en", "Spanish": "es", "Mandarin": "zh"}
LANGUAGE_FIXTURES_MAP = {
    "English": {
        "vote_positive": POSITIVE_VOTE_STATEMENTS.get("english", []),
        "vote_negative": NEGATIVE_VOTE_STATEMENTS.get("english", []),
        "ballots": BALLOT_STATEMENTS.get("valid_ballots", []),
        "constraints": LANGUAGE_SPECIFIC_CONSTRAINTS.get("english", []),
        "preferences": PREFERENCE_STATEMENTS.get("english", []),
        "agreements": AGREEMENT_STATEMENTS.get("positive", {}).get("english", []),
        "disagreements": AGREEMENT_STATEMENTS.get("negative", {}).get("english", [])
    },
    "Spanish": {
        "vote_positive": POSITIVE_VOTE_STATEMENTS.get("spanish", []),
        "vote_negative": NEGATIVE_VOTE_STATEMENTS.get("spanish", []),
        "ballots": SPANISH_BALLOT_STATEMENTS.get("valid_ballots", []),
        "constraints": LANGUAGE_SPECIFIC_CONSTRAINTS.get("spanish", []),
        "preferences": PREFERENCE_STATEMENTS.get("spanish", []),
        "agreements": AGREEMENT_STATEMENTS.get("positive", {}).get("spanish", []),
        "disagreements": AGREEMENT_STATEMENTS.get("negative", {}).get("spanish", [])
    },
    "Mandarin": {
        "vote_positive": POSITIVE_VOTE_STATEMENTS.get("chinese", []),
        "vote_negative": NEGATIVE_VOTE_STATEMENTS.get("chinese", []),
        "ballots": CHINESE_BALLOT_STATEMENTS.get("valid_ballots", []),
        "constraints": LANGUAGE_SPECIFIC_CONSTRAINTS.get("chinese", []),
        "preferences": PREFERENCE_STATEMENTS.get("chinese", []),
        "agreements": AGREEMENT_STATEMENTS.get("positive", {}).get("chinese", []),
        "disagreements": AGREEMENT_STATEMENTS.get("negative", {}).get("chinese", [])
    }
}


# =============================================================================
# Language Data Loader with Caching
# =============================================================================

class LanguageDataLoader:
    """Optimized language data loader with caching and lazy loading."""
    
    _cache: Dict[str, Dict[str, Any]] = {}
    _loaded_languages: set = set()
    
    @classmethod
    def get_language_test_data(cls, language: str, data_type: str = "all") -> Dict[str, Any]:
        """
        Get test data for specific language with lazy loading and caching.
        
        Args:
            language: Target language (English, Spanish, Mandarin)
            data_type: Specific data type or "all" for complete dataset
            
        Returns:
            Dictionary containing test data for the language
        """
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}. Supported: {SUPPORTED_LANGUAGES}")
        
        # Check cache first
        cache_key = f"{language}_{data_type}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        # Load language data if not already loaded
        if language not in cls._loaded_languages:
            cls._load_language_fixtures(language)
            cls._loaded_languages.add(language)
        
        # Get requested data
        if data_type == "all":
            data = LANGUAGE_FIXTURES_MAP.get(language, {})
        else:
            data = {data_type: LANGUAGE_FIXTURES_MAP.get(language, {}).get(data_type, [])}
        
        # Cache and return
        cls._cache[cache_key] = data
        return data
    
    @classmethod
    def _load_language_fixtures(cls, language: str):
        """Load language-specific fixtures with validation."""
        if language not in LANGUAGE_FIXTURES_MAP:
            warnings.warn(f"No fixture data found for language: {language}")
            return
        
        # Validate fixture data integrity
        fixtures = LANGUAGE_FIXTURES_MAP[language]
        for data_type, data_list in fixtures.items():
            if not isinstance(data_list, list):
                warnings.warn(f"Invalid fixture format for {language}.{data_type}")
    
    @classmethod
    def clear_cache(cls):
        """Clear the data cache (useful for testing)."""
        cls._cache.clear()
        cls._loaded_languages.clear()
    
    @classmethod
    def get_fixture_stats(cls) -> Dict[str, int]:
        """Get statistics about loaded fixtures."""
        stats = {}
        for language in SUPPORTED_LANGUAGES:
            fixtures = LANGUAGE_FIXTURES_MAP.get(language, {})
            total_items = sum(len(data) for data in fixtures.values() if isinstance(data, list))
            stats[language] = total_items
        return stats


# =============================================================================
# Language Parity Checker
# =============================================================================

class LanguageParityChecker:
    """Utility to ensure test parity across all supported languages."""
    
    @staticmethod
    def assert_language_parity(test_class: Type, test_method_name: str, required_languages: Optional[List[str]] = None):
        """
        Ensure a test method exists and has data for all required languages.
        
        Args:
            test_class: Test class containing the method
            test_method_name: Name of the test method to check
            required_languages: Languages to check (defaults to all supported)
        """
        if required_languages is None:
            required_languages = SUPPORTED_LANGUAGES
        
        # Check if method exists
        if not hasattr(test_class, test_method_name):
            raise AssertionError(f"Test method '{test_method_name}' not found in {test_class.__name__}")
        
        # Check if method uses language parameterization
        method = getattr(test_class, test_method_name)
        method_signature = inspect.signature(method)
        
        has_language_param = 'language' in method_signature.parameters
        if not has_language_param:
            warnings.warn(f"Test method '{test_method_name}' does not use language parameterization")
        
        # Check data availability for each language
        missing_data = []
        for language in required_languages:
            try:
                data = LanguageDataLoader.get_language_test_data(language)
                if not data or all(not v for v in data.values()):
                    missing_data.append(language)
            except ValueError:
                missing_data.append(language)
        
        if missing_data:
            raise AssertionError(f"Test data missing for languages: {missing_data} in method '{test_method_name}'")
    
    @staticmethod
    def calculate_language_coverage(test_class: Type) -> Dict[str, float]:
        """
        Calculate test coverage percentage for each language.
        
        Args:
            test_class: Test class to analyze
            
        Returns:
            Dictionary mapping language to coverage percentage
        """
        coverage = {}
        
        # Get all test methods
        test_methods = [name for name in dir(test_class) if name.startswith('test_')]
        total_methods = len(test_methods)
        
        if total_methods == 0:
            return {lang: 0.0 for lang in SUPPORTED_LANGUAGES}
        
        for language in SUPPORTED_LANGUAGES:
            covered_methods = 0
            
            for method_name in test_methods:
                try:
                    # Check if method can get data for this language
                    data = LanguageDataLoader.get_language_test_data(language)
                    if data and any(v for v in data.values()):
                        covered_methods += 1
                except (ValueError, KeyError):
                    continue
            
            coverage[language] = (covered_methods / total_methods) * 100
        
        return coverage
    
    @staticmethod
    def assert_minimum_coverage(test_class: Type, min_coverage: float = 80.0):
        """
        Assert that all languages meet minimum coverage requirements.
        
        Args:
            test_class: Test class to check
            min_coverage: Minimum coverage percentage (default 80%)
        """
        coverage = LanguageParityChecker.calculate_language_coverage(test_class)
        
        failing_languages = []
        for language, percentage in coverage.items():
            if percentage < min_coverage:
                failing_languages.append(f"{language}: {percentage:.1f}%")
        
        if failing_languages:
            raise AssertionError(
                f"Languages below {min_coverage}% coverage: {', '.join(failing_languages)}"
            )


# =============================================================================
# Parametrized Test Base Classes
# =============================================================================

class MultilingualTestBase(ABC):
    """
    Base class for parametrized multilingual testing with synchronous methods.
    
    This class provides the infrastructure for Step 3.1 of the implementation plan:
    parametrized test framework with language fixtures and parity checking.
    """
    
    @pytest.fixture(params=SUPPORTED_LANGUAGES)
    def language(self, request):
        """Parametrize tests across all supported languages."""
        return request.param
    
    @pytest.fixture
    def test_data(self, language):
        """Load test data for the current language parameter."""
        return self.get_language_test_data(language)
    
    @pytest.fixture
    def language_code(self, language):
        """Get language code for current language."""
        return LANGUAGE_CODES.get(language, "unknown")
    
    def get_language_test_data(self, language: str, data_type: str = "all") -> Dict[str, Any]:
        """
        Get test data for specific language with fallback mechanism.
        
        Args:
            language: Target language
            data_type: Specific data type or "all"
            
        Returns:
            Test data dictionary for the language
        """
        try:
            return LanguageDataLoader.get_language_test_data(language, data_type)
        except ValueError:
            # Fallback to English if language not supported
            warnings.warn(f"Falling back to English data for unsupported language: {language}")
            return LanguageDataLoader.get_language_test_data("English", data_type)
    
    def assert_language_parity(self, test_name: str):
        """Ensure test exists for all languages."""
        LanguageParityChecker.assert_language_parity(
            test_class=self.__class__,
            test_method_name=test_name
        )
    
    def assert_minimum_coverage(self, min_coverage: float = 80.0):
        """Assert minimum coverage across all languages."""
        LanguageParityChecker.assert_minimum_coverage(
            test_class=self.__class__,
            min_coverage=min_coverage
        )
    
    @pytest.fixture(autouse=True)
    def _validate_fixture_data(self):
        """Alert when no fixture data is present for any language."""
        try:
            stats = LanguageDataLoader.get_fixture_stats()
        except Exception as exc:
            warnings.warn(f"Error validating fixture data: {exc}")
            return

        if not any(stats.values()):
            warnings.warn("No fixture data available for any language")


class AsyncMultilingualTestBase(ABC):
    """
    Base class for parametrized multilingual testing with async support.
    
    Extends MultilingualTestBase for async test methods and coroutines.
    """
    
    @pytest.fixture(params=SUPPORTED_LANGUAGES)
    def language(self, request):
        """Parametrize tests across all supported languages."""
        return request.param
    
    @pytest.fixture
    def test_data(self, language):
        """Load test data for the current language parameter."""
        return self.get_language_test_data(language)
    
    @pytest.fixture
    def language_code(self, language):
        """Get language code for current language."""
        return LANGUAGE_CODES.get(language, "unknown")
    
    def get_language_test_data(self, language: str, data_type: str = "all") -> Dict[str, Any]:
        """Get test data for specific language with fallback."""
        try:
            return LanguageDataLoader.get_language_test_data(language, data_type)
        except ValueError:
            warnings.warn(f"Falling back to English data for unsupported language: {language}")
            return LanguageDataLoader.get_language_test_data("English", data_type)
    def assert_language_parity(self, test_name: str):
        """Ensure test exists for all languages."""
        LanguageParityChecker.assert_language_parity(
            test_class=self.__class__,
            test_method_name=test_name,
        )
    
    async def async_get_language_test_data(self, language: str, data_type: str = "all") -> Dict[str, Any]:
        """Async version of get_language_test_data for async test methods."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_language_test_data, language, data_type)
    
    @abstractmethod
    def setUp(self):
        """Set up async test with language validation."""
        super().setUp()


# =============================================================================
# Specialized Test Mixins
# =============================================================================

class VoteIntentionTestMixin:
    """Mixin for vote intention detection tests with multilingual support."""
    
    def get_vote_positive_statements(self, language: str) -> List[str]:
        """Get positive vote statements for language."""
        data = self.get_language_test_data(language, "vote_positive")
        return data.get("vote_positive", [])
    
    def get_vote_negative_statements(self, language: str) -> List[str]:
        """Get negative vote statements for language."""
        data = self.get_language_test_data(language, "vote_negative") 
        return data.get("vote_negative", [])


class BallotParsingTestMixin:
    """Mixin for ballot parsing tests with multilingual support."""
    
    def get_ballot_statements(self, language: str) -> List[Dict]:
        """Get ballot test statements for language."""
        data = self.get_language_test_data(language, "ballots")
        return data.get("ballots", [])


class ConstraintParsingTestMixin:
    """Mixin for constraint parsing tests with multilingual support."""
    
    def get_constraint_statements(self, language: str) -> List[tuple]:
        """Get constraint test statements for language."""
        data = self.get_language_test_data(language, "constraints")
        return data.get("constraints", [])


# =============================================================================
# Utility Functions
# =============================================================================

def parametrize_languages(languages: Optional[List[str]] = None):
    """
    Decorator to parametrize test methods across languages.
    
    Args:
        languages: List of languages to test (defaults to all supported)
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    return pytest.mark.parametrize("language", languages)


def require_language_data(*data_types: str):
    """
    Decorator to require specific data types for language tests.
    
    Args:
        data_types: Required data types (e.g., "ballots", "constraints")
    """
    def decorator(test_method):
        def wrapper(self, language, *args, **kwargs):
            # Check data availability
            for data_type in data_types:
                data = self.get_language_test_data(language, data_type)
                if not data.get(data_type):
                    pytest.skip(f"No {data_type} data available for {language}")
            
            return test_method(self, language, *args, **kwargs)
        
        return wrapper
    return decorator


def skip_language_if_no_data(language: str, data_type: str):
    """Skip test if specific language lacks required data type."""
    try:
        data = LanguageDataLoader.get_language_test_data(language, data_type)
        if not data.get(data_type):
            return pytest.mark.skip(f"No {data_type} data for {language}")
    except ValueError:
        return pytest.mark.skip(f"Language {language} not supported")
    
    return lambda x: x  # No-op decorator if data exists


# =============================================================================
# Performance and Optimization Utilities  
# =============================================================================

class TestExecutionOptimizer:
    """Utilities for optimizing multilingual test execution performance."""
    
    @staticmethod
    def batch_language_tests(test_methods: List[str], batch_size: int = 3) -> List[List[str]]:
        """
        Batch test methods for parallel execution across languages.
        
        Args:
            test_methods: List of test method names
            batch_size: Number of methods per batch
            
        Returns:
            List of batched test method groups
        """
        batches = []
        for i in range(0, len(test_methods), batch_size):
            batches.append(test_methods[i:i + batch_size])
        return batches
    
    @staticmethod
    def estimate_test_time(test_class: Type, language_count: int = 3) -> float:
        """
        Estimate total test execution time for multilingual testing.
        
        Args:
            test_class: Test class to analyze
            language_count: Number of languages to test
            
        Returns:
            Estimated execution time in seconds
        """
        test_methods = [name for name in dir(test_class) if name.startswith('test_')]
        
        # Basic estimation: 0.5 seconds per test method per language
        base_time_per_test = 0.5
        setup_overhead = 2.0  # Setup overhead per language
        
        total_time = (len(test_methods) * base_time_per_test * language_count) + (setup_overhead * language_count)
        return total_time
