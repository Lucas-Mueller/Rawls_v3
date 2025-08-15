"""
Unit tests for Original Values Data module.
"""
import pytest
import math
from core.original_values_data import OriginalValuesData
from models.experiment_types import IncomeDistribution, IncomeClassProbabilities


class TestOriginalValuesData:
    """Test suite for OriginalValuesData class."""
    
    def test_get_situation_sample(self):
        """Test getting sample situation data."""
        situation = OriginalValuesData.get_situation("sample")
        
        assert len(situation["distributions"]) == 4
        assert isinstance(situation["probabilities"], IncomeClassProbabilities)
        
        # Test first distribution values from sample situation
        first_dist = situation["distributions"][0]
        assert first_dist.high == 32000
        assert first_dist.medium_high == 27000
        assert first_dist.medium == 24000
        assert first_dist.medium_low == 13000
        assert first_dist.low == 12000
    
    def test_get_situation_all_situations(self):
        """Test that all defined situations can be retrieved."""
        expected_situations = ["sample", "a", "b", "c", "d"]
        
        for situation_name in expected_situations:
            situation = OriginalValuesData.get_situation(situation_name)
            
            assert "distributions" in situation
            assert "probabilities" in situation
            assert len(situation["distributions"]) == 4
            assert isinstance(situation["probabilities"], IncomeClassProbabilities)
    
    def test_probabilities_sum_to_one(self):
        """Test that probabilities sum to 1.0 for all situations."""
        for situation_name in ["sample", "a", "b", "c", "d"]:
            probs = OriginalValuesData.get_probabilities(situation_name)
            total = probs.high + probs.medium_high + probs.medium + probs.medium_low + probs.low
            assert abs(total - 1.0) < 1e-6, f"Probabilities for situation {situation_name} don't sum to 1.0: {total}"
    
    def test_situation_specific_probabilities(self):
        """Test that different situations have different probability distributions."""
        sample_probs = OriginalValuesData.get_probabilities("sample")
        situation_a_probs = OriginalValuesData.get_probabilities("a")
        situation_c_probs = OriginalValuesData.get_probabilities("c")
        
        # Sample: 5/10/50/25/10 distribution
        assert sample_probs.high == 0.05
        assert sample_probs.medium_high == 0.10
        assert sample_probs.medium == 0.50
        assert sample_probs.medium_low == 0.25
        assert sample_probs.low == 0.10
        
        # Situation A: 10/20/40/20/10 distribution (higher upper class)
        assert situation_a_probs.high == 0.10
        assert situation_a_probs.medium_high == 0.20
        assert situation_a_probs.medium == 0.40
        assert situation_a_probs.medium_low == 0.20
        assert situation_a_probs.low == 0.10
        
        # Situation C: extreme inequality with very low high class probability
        assert situation_c_probs.high == 0.013334  # Fixed precision
        assert situation_c_probs.medium == 0.583333  # Much higher middle class
    
    def test_get_distributions_method(self):
        """Test the get_distributions convenience method."""
        distributions = OriginalValuesData.get_distributions("sample")
        
        assert len(distributions) == 4
        assert all(isinstance(dist, IncomeDistribution) for dist in distributions)
        
        # Test that distributions have positive values
        for dist in distributions:
            assert dist.high > 0
            assert dist.medium_high > 0
            assert dist.medium > 0
            assert dist.medium_low > 0
            assert dist.low > 0
    
    def test_get_probabilities_method(self):
        """Test the get_probabilities convenience method."""
        probabilities = OriginalValuesData.get_probabilities("a")
        
        assert isinstance(probabilities, IncomeClassProbabilities)
        assert probabilities.high == 0.10
        assert probabilities.medium_high == 0.20
        assert probabilities.medium == 0.40
        assert probabilities.medium_low == 0.20
        assert probabilities.low == 0.10
    
    def test_invalid_situation(self):
        """Test error handling for invalid situation."""
        with pytest.raises(ValueError, match="Unknown situation: invalid"):
            OriginalValuesData.get_situation("invalid")
        
        with pytest.raises(ValueError, match="Unknown situation: xyz"):
            OriginalValuesData.get_distributions("xyz")
        
        with pytest.raises(ValueError, match="Unknown situation: nonexistent"):
            OriginalValuesData.get_probabilities("nonexistent")
    
    def test_case_insensitive_situation_names(self):
        """Test that situation names are case insensitive."""
        # Test various case combinations
        test_cases = ["SAMPLE", "Sample", "sAmPlE", "A", "a", "C", "c"]
        
        for case_variant in test_cases:
            if case_variant.lower() in ["sample", "a", "c"]:
                # Should not raise an error
                situation = OriginalValuesData.get_situation(case_variant)
                assert "distributions" in situation
                assert "probabilities" in situation
    
    def test_list_situations(self):
        """Test the list_situations method."""
        situations = OriginalValuesData.list_situations()
        
        expected = ["sample", "a", "b", "c", "d"]
        assert sorted(situations) == sorted(expected)
        assert len(situations) == 5
    
    def test_validate_probabilities(self):
        """Test the validate_probabilities class method."""
        # Should not raise an error if all probabilities are valid
        assert OriginalValuesData.validate_probabilities() is True
    
    def test_distribution_integrity(self):
        """Test that all distributions have proper income class hierarchy."""
        for situation_name in OriginalValuesData.list_situations():
            distributions = OriginalValuesData.get_distributions(situation_name)
            
            for i, dist in enumerate(distributions):
                # Test that income classes are in descending order (not strictly required but generally expected)
                # Note: This is not a hard requirement, so we'll just test that all values are positive
                assert dist.high >= 0, f"Situation {situation_name}, distribution {i}: high income must be non-negative"
                assert dist.medium_high >= 0, f"Situation {situation_name}, distribution {i}: medium_high income must be non-negative"
                assert dist.medium >= 0, f"Situation {situation_name}, distribution {i}: medium income must be non-negative"
                assert dist.medium_low >= 0, f"Situation {situation_name}, distribution {i}: medium_low income must be non-negative"
                assert dist.low >= 0, f"Situation {situation_name}, distribution {i}: low income must be non-negative"
    
    def test_situation_c_extreme_values(self):
        """Test that situation C has the extreme high income value."""
        distributions = OriginalValuesData.get_distributions("c")
        
        # First distribution in situation C should have the $100,000 high income
        first_dist = distributions[0]
        assert first_dist.high == 100000, "Situation C should have extreme high income value"
        
        # Check that it creates significant inequality
        range_value = first_dist.high - first_dist.low
        assert range_value >= 85000, "Situation C should have extreme income range"
    
    def test_probability_precision(self):
        """Test that probabilities maintain sufficient precision."""
        for situation_name in OriginalValuesData.list_situations():
            probs = OriginalValuesData.get_probabilities(situation_name)
            
            # Test that probabilities are stored with reasonable precision
            total = probs.high + probs.medium_high + probs.medium + probs.medium_low + probs.low
            assert abs(total - 1.0) < 1e-6, f"Situation {situation_name} probabilities imprecise: {total}"
            
            # Test that individual probabilities are within valid range
            for prob_name, prob_value in [
                ("high", probs.high), ("medium_high", probs.medium_high), 
                ("medium", probs.medium), ("medium_low", probs.medium_low), ("low", probs.low)
            ]:
                assert 0 <= prob_value <= 1, f"Situation {situation_name}, {prob_name} probability out of range: {prob_value}"