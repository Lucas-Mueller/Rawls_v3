"""
Unit tests for distribution generation system.
"""
import unittest
from core.distribution_generator import DistributionGenerator
from models import IncomeDistribution, JusticePrinciple, PrincipleChoice, CertaintyLevel


class TestDistributionGenerator(unittest.TestCase):
    """Test cases for the DistributionGenerator class."""
    
    def test_generate_dynamic_distribution(self):
        """Test dynamic distribution generation with multipliers."""
        # Test with different multiplier ranges
        dist_set = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0))
        
        # Should generate exactly 4 distributions
        self.assertEqual(len(dist_set.distributions), 4)
        
        # Multiplier should be within range
        self.assertGreaterEqual(dist_set.multiplier, 0.5)
        self.assertLessEqual(dist_set.multiplier, 2.0)
        
        # All distributions should have positive incomes
        for dist in dist_set.distributions:
            self.assertGreater(dist.high, 0)
            self.assertGreater(dist.medium_high, 0)
            self.assertGreater(dist.medium, 0)
            self.assertGreater(dist.medium_low, 0)
            self.assertGreater(dist.low, 0)
    
    def test_apply_principle_maximizing_floor(self):
        """Test principle application logic for maximizing floor."""
        distributions = [
            IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
            IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
            IncomeDistribution(high=31000, medium_high=24000, medium=21000, medium_low=16000, low=14000),
            IncomeDistribution(high=21000, medium_high=20000, medium=19000, medium_low=16000, low=15000)
        ]
        
        principle = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            certainty=CertaintyLevel.SURE
        )
        
        chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
            distributions, principle
        )
        
        # Should choose distribution with highest floor (15000)
        self.assertEqual(chosen_dist.low, 15000)
        self.assertIn("floor", explanation.lower())
    
    def test_apply_principle_maximizing_average(self):
        """Test principle application for maximizing average."""
        distributions = [
            IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
            IncomeDistribution(high=40000, medium_high=35000, medium=30000, medium_low=25000, low=20000)  # Higher average
        ]
        
        principle = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE,
            certainty=CertaintyLevel.SURE
        )
        
        chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
            distributions, principle
        )
        
        # Should choose distribution with higher average
        self.assertEqual(chosen_dist.high, 40000)
        self.assertIn("average", explanation.lower())
    
    def test_apply_principle_with_floor_constraint(self):
        """Test constraint principle validation and application."""
        distributions = [
            IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
            IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=15000)
        ]
        
        principle = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=14000,
            certainty=CertaintyLevel.SURE
        )
        
        chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
            distributions, principle
        )
        
        # Should choose distribution that meets floor constraint
        self.assertGreaterEqual(chosen_dist.low, 14000)
        self.assertIn("floor constraint", explanation.lower())
    
    def test_calculate_payoff(self):
        """Test payoff calculation."""
        distribution = IncomeDistribution(
            high=30000, medium_high=25000, medium=20000, medium_low=15000, low=10000
        )
        
        assigned_class, payoff = DistributionGenerator.calculate_payoff(distribution)
        
        # Should assign to one of the income classes
        from models import IncomeClass
        self.assertIn(assigned_class, list(IncomeClass))
        
        # Payoff should be income/10000
        expected_income = distribution.get_income_by_class(assigned_class)
        expected_payoff = expected_income / 10000.0
        self.assertEqual(payoff, expected_payoff)
    
    def test_format_distributions_table(self):
        """Test distribution table formatting."""
        distributions = [
            IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
            IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000)
        ]
        
        table = DistributionGenerator.format_distributions_table(distributions)
        
        # Should contain table headers
        self.assertIn("Income Class", table)
        self.assertIn("Dist. 1", table)
        self.assertIn("Dist. 2", table)
        
        # Should contain income values
        self.assertIn("$32,000", table)
        self.assertIn("$28,000", table)


if __name__ == '__main__':
    unittest.main()