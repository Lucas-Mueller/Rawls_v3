"""
Unit tests for data models.
"""
import unittest
from pydantic import ValidationError

from models import (
    JusticePrinciple, PrincipleChoice, PrincipleRanking, RankedPrinciple,
    IncomeDistribution, DistributionSet, CertaintyLevel
)


class TestPrincipleModels(unittest.TestCase):
    """Test cases for justice principle models."""
    
    def test_principle_choice_validation(self):
        """Test PrincipleChoice validation rules."""
        # Valid choice without constraint
        choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            certainty=CertaintyLevel.SURE
        )
        self.assertEqual(choice.principle, JusticePrinciple.MAXIMIZING_FLOOR)
        
        # Valid choice with constraint
        choice_with_constraint = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=15000,
            certainty=CertaintyLevel.SURE
        )
        self.assertEqual(choice_with_constraint.constraint_amount, 15000)
        
        # Invalid: constraint principle without amount
        with self.assertRaises(ValidationError):
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                certainty=CertaintyLevel.SURE
            )
        
        # Invalid: negative constraint amount
        with self.assertRaises(ValidationError):
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=-1000,
                certainty=CertaintyLevel.SURE
            )
    
    def test_principle_ranking_validation(self):
        """Test PrincipleRanking validation."""
        # Valid complete ranking
        rankings = [
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
        ]
        
        ranking = PrincipleRanking(rankings=rankings, certainty=CertaintyLevel.SURE)
        self.assertEqual(len(ranking.rankings), 4)
        self.assertEqual(ranking.certainty, CertaintyLevel.SURE)
        
        # Invalid: missing principle
        incomplete_rankings = rankings[:3]  # Only 3 principles
        with self.assertRaises(ValidationError):
            PrincipleRanking(rankings=incomplete_rankings, certainty=CertaintyLevel.SURE)
        
        # Invalid: duplicate ranks
        duplicate_rankings = [
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),  # Duplicate rank
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
        ]
        with self.assertRaises(ValidationError):
            PrincipleRanking(rankings=duplicate_rankings, certainty=CertaintyLevel.SURE)


class TestIncomeModels(unittest.TestCase):
    """Test cases for income distribution models."""
    
    def test_income_distribution_methods(self):
        """Test IncomeDistribution helper methods."""
        distribution = IncomeDistribution(
            high=30000, medium_high=25000, medium=20000, medium_low=15000, low=10000
        )
        
        # Test floor income
        self.assertEqual(distribution.get_floor_income(), 10000)
        
        # Test average income
        expected_avg = (30000 + 25000 + 20000 + 15000 + 10000) / 5
        self.assertEqual(distribution.get_average_income(), expected_avg)
        
        # Test range
        self.assertEqual(distribution.get_range(), 20000)  # 30000 - 10000
    
    def test_income_distribution_validation(self):
        """Test IncomeDistribution validation."""
        # Valid distribution
        distribution = IncomeDistribution(
            high=30000, medium_high=25000, medium=20000, medium_low=15000, low=10000
        )
        self.assertIsInstance(distribution, IncomeDistribution)
        
        # Invalid: negative income
        with self.assertRaises(ValidationError):
            IncomeDistribution(
                high=-1000, medium_high=25000, medium=20000, medium_low=15000, low=10000
            )
        
        # Invalid: zero income
        with self.assertRaises(ValidationError):
            IncomeDistribution(
                high=30000, medium_high=25000, medium=20000, medium_low=15000, low=0
            )
    
    def test_distribution_set_validation(self):
        """Test DistributionSet validation."""
        distributions = [
            IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
            IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
            IncomeDistribution(high=31000, medium_high=24000, medium=21000, medium_low=16000, low=14000),
            IncomeDistribution(high=21000, medium_high=20000, medium=19000, medium_low=16000, low=15000)
        ]
        
        # Valid set with 4 distributions
        dist_set = DistributionSet(distributions=distributions, multiplier=1.5)
        self.assertEqual(len(dist_set.distributions), 4)
        self.assertEqual(dist_set.multiplier, 1.5)
        
        # Invalid: wrong number of distributions
        with self.assertRaises(ValidationError):
            DistributionSet(distributions=distributions[:3], multiplier=1.5)  # Only 3
        
        # Invalid: negative multiplier
        with self.assertRaises(ValidationError):
            DistributionSet(distributions=distributions, multiplier=-0.5)


if __name__ == '__main__':
    unittest.main()