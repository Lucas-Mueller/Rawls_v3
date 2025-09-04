"""
Unit tests for Phase2Settings reasoning configuration.

Tests the reasoning system configuration fields in Phase2Settings,
including default values, validation ranges, and configuration integrity.
"""

import pytest
from pydantic import ValidationError

from config.phase2_settings import Phase2Settings


class TestPhase2SettingsReasoningDefaults:
    """Test default reasoning configuration values."""
    
    def test_reasoning_enabled_default_true(self):
        """Test that reasoning is enabled by default."""
        settings = Phase2Settings()
        assert settings.reasoning_enabled is True
    
    def test_reasoning_timeout_default(self):
        """Test default reasoning timeout value."""
        settings = Phase2Settings()
        assert settings.reasoning_timeout_seconds == 180
    
    def test_reasoning_max_retries_default(self):
        """Test default reasoning max retries value."""
        settings = Phase2Settings()
        assert settings.reasoning_max_retries == 2


class TestPhase2SettingsReasoningValidation:
    """Test reasoning configuration field validation."""
    
    def test_reasoning_enabled_boolean_validation(self):
        """Test reasoning_enabled accepts boolean values."""
        # Test True
        settings1 = Phase2Settings(reasoning_enabled=True)
        assert settings1.reasoning_enabled is True
        
        # Test False
        settings2 = Phase2Settings(reasoning_enabled=False)
        assert settings2.reasoning_enabled is False
    
    def test_reasoning_timeout_range_validation(self):
        """Test reasoning timeout within valid range."""
        # Test minimum valid value
        settings1 = Phase2Settings(reasoning_timeout_seconds=10)
        assert settings1.reasoning_timeout_seconds == 10
        
        # Test maximum valid value
        settings2 = Phase2Settings(reasoning_timeout_seconds=300)
        assert settings2.reasoning_timeout_seconds == 300
        
        # Test mid-range value
        settings3 = Phase2Settings(reasoning_timeout_seconds=120)
        assert settings3.reasoning_timeout_seconds == 120
    
    def test_reasoning_timeout_invalid_range(self):
        """Test reasoning timeout validation fails outside valid range."""
        # Test below minimum
        with pytest.raises(ValidationError, match="greater than or equal to 10"):
            Phase2Settings(reasoning_timeout_seconds=9)
        
        # Test above maximum
        with pytest.raises(ValidationError, match="less than or equal to 300"):
            Phase2Settings(reasoning_timeout_seconds=301)
    
    def test_reasoning_max_retries_range_validation(self):
        """Test reasoning max retries within valid range."""
        # Test minimum valid value
        settings1 = Phase2Settings(reasoning_max_retries=1)
        assert settings1.reasoning_max_retries == 1
        
        # Test maximum valid value
        settings2 = Phase2Settings(reasoning_max_retries=5)
        assert settings2.reasoning_max_retries == 5
        
        # Test mid-range value
        settings3 = Phase2Settings(reasoning_max_retries=3)
        assert settings3.reasoning_max_retries == 3
    
    def test_reasoning_max_retries_invalid_range(self):
        """Test reasoning max retries validation fails outside valid range."""
        # Test below minimum
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            Phase2Settings(reasoning_max_retries=0)
        
        # Test above maximum
        with pytest.raises(ValidationError, match="less than or equal to 5"):
            Phase2Settings(reasoning_max_retries=6)


class TestPhase2SettingsReasoningConfiguration:
    """Test reasoning configuration combinations."""
    
    def test_custom_reasoning_configuration(self):
        """Test creating settings with custom reasoning configuration."""
        settings = Phase2Settings(
            reasoning_enabled=False,
            reasoning_timeout_seconds=60,
            reasoning_max_retries=1
        )
        
        assert settings.reasoning_enabled is False
        assert settings.reasoning_timeout_seconds == 60
        assert settings.reasoning_max_retries == 1
        # Ensure other settings remain default
        assert settings.statement_timeout_seconds == 300  # Default
        assert settings.max_statement_retries == 3  # Default
    
    def test_reasoning_disabled_with_custom_timeouts(self):
        """Test reasoning disabled with custom timeout values still validates."""
        settings = Phase2Settings(
            reasoning_enabled=False,
            reasoning_timeout_seconds=45,
            reasoning_max_retries=4
        )
        
        assert settings.reasoning_enabled is False
        assert settings.reasoning_timeout_seconds == 45
        assert settings.reasoning_max_retries == 4
    
    def test_reasoning_configuration_independence(self):
        """Test reasoning config doesn't affect other timeout settings."""
        settings = Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=90,
            reasoning_max_retries=3,
            statement_timeout_seconds=120,  # Different from reasoning timeout
            confirmation_timeout_seconds=180
        )
        
        # Reasoning settings
        assert settings.reasoning_enabled is True
        assert settings.reasoning_timeout_seconds == 90
        assert settings.reasoning_max_retries == 3
        
        # Other timeout settings should be independent
        assert settings.statement_timeout_seconds == 120
        assert settings.confirmation_timeout_seconds == 180
    
    def test_get_default_includes_reasoning_settings(self):
        """Test that get_default() creates settings with reasoning configuration."""
        settings = Phase2Settings.get_default()
        
        # All reasoning settings should have expected defaults
        assert hasattr(settings, 'reasoning_enabled')
        assert hasattr(settings, 'reasoning_timeout_seconds')
        assert hasattr(settings, 'reasoning_max_retries')
        
        assert settings.reasoning_enabled is True
        assert settings.reasoning_timeout_seconds == 180
        assert settings.reasoning_max_retries == 2


class TestPhase2SettingsReasoningDocumentation:
    """Test reasoning field documentation and descriptions."""
    
    def test_reasoning_enabled_field_info(self):
        """Test reasoning_enabled field has proper description."""
        model_fields = Phase2Settings.__fields__
        reasoning_enabled_field = model_fields.get('reasoning_enabled')
        
        assert reasoning_enabled_field is not None
        assert reasoning_enabled_field.description is not None
        assert "two-step reasoning" in reasoning_enabled_field.description.lower()
    
    def test_reasoning_timeout_field_info(self):
        """Test reasoning_timeout_seconds field has proper description."""
        model_fields = Phase2Settings.__fields__
        reasoning_timeout_field = model_fields.get('reasoning_timeout_seconds')
        
        assert reasoning_timeout_field is not None
        assert reasoning_timeout_field.description is not None
        assert "reasoning" in reasoning_timeout_field.description.lower()
        assert "timeout" in reasoning_timeout_field.description.lower()
    
    def test_reasoning_retries_field_info(self):
        """Test reasoning_max_retries field has proper description."""
        model_fields = Phase2Settings.__fields__
        reasoning_retries_field = model_fields.get('reasoning_max_retries')
        
        assert reasoning_retries_field is not None
        assert reasoning_retries_field.description is not None
        assert "reasoning" in reasoning_retries_field.description.lower()
        assert "retry" in reasoning_retries_field.description.lower()


class TestPhase2SettingsCompatibility:
    """Test backward compatibility and integration with existing settings."""
    
    def test_all_existing_settings_preserved(self):
        """Test that adding reasoning settings doesn't break existing functionality."""
        settings = Phase2Settings()
        
        # Verify all key existing settings are still present and functional
        assert hasattr(settings, 'min_statement_length')
        assert hasattr(settings, 'max_statement_retries')
        assert hasattr(settings, 'statement_timeout_seconds')
        assert hasattr(settings, 'memory_compression_threshold')
        assert hasattr(settings, 'public_history_max_length')
        
        # Test that existing methods still work
        assert settings.get_min_statement_length('english') == 10
        assert settings.get_min_statement_length('Mandarin') == 5
        assert settings.is_cjk_language('Mandarin') is True
        assert settings.is_cjk_language('english') is False
    
    def test_reasoning_settings_coexist_with_validation_settings(self):
        """Test reasoning settings work alongside statement validation settings."""
        settings = Phase2Settings(
            # Reasoning settings
            reasoning_enabled=True,
            reasoning_timeout_seconds=120,
            reasoning_max_retries=3,
            # Statement validation settings
            min_statement_length=15,
            max_statement_retries=5,
            statement_timeout_seconds=240
        )
        
        # Both types of settings should be properly set
        assert settings.reasoning_enabled is True
        assert settings.reasoning_timeout_seconds == 120
        assert settings.reasoning_max_retries == 3
        assert settings.min_statement_length == 15
        assert settings.max_statement_retries == 5
        assert settings.statement_timeout_seconds == 240


if __name__ == '__main__':
    pytest.main([__file__])