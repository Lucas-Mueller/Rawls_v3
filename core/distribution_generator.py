"""
Distribution generation system for the Frohlich Experiment.
"""
import random
from typing import List, Tuple, Optional
from models import (
    IncomeDistribution, DistributionSet, PrincipleChoice, JusticePrinciple, IncomeClass
)


class DistributionGenerator:
    """Generates and applies justice principles to income distributions."""
    
    # Base distribution from the master plan
    BASE_DISTRIBUTION = IncomeDistribution(
        high=32000,
        medium_high=27000, 
        medium=24000,
        medium_low=13000,
        low=12000
    )
    
    # Additional base distributions for the 4-distribution set
    BASE_DISTRIBUTIONS = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
        IncomeDistribution(high=31000, medium_high=24000, medium=21000, medium_low=16000, low=14000),
        IncomeDistribution(high=21000, medium_high=20000, medium=19000, medium_low=16000, low=15000)
    ]
    
    @staticmethod
    def generate_dynamic_distribution(multiplier_range: Tuple[float, float]) -> DistributionSet:
        """Generate 4 distributions with random multiplier applied to base distributions."""
        multiplier = random.uniform(multiplier_range[0], multiplier_range[1])
        
        distributions = []
        for base_dist in DistributionGenerator.BASE_DISTRIBUTIONS:
            scaled_dist = IncomeDistribution(
                high=int(base_dist.high * multiplier),
                medium_high=int(base_dist.medium_high * multiplier),
                medium=int(base_dist.medium * multiplier),
                medium_low=int(base_dist.medium_low * multiplier),
                low=int(base_dist.low * multiplier)
            )
            distributions.append(scaled_dist)
        
        return DistributionSet(distributions=distributions, multiplier=multiplier)
    
    @staticmethod
    def apply_principle_to_distributions(
        distributions: List[IncomeDistribution],
        principle: PrincipleChoice
    ) -> Tuple[IncomeDistribution, str]:
        """Apply justice principle logic and return chosen distribution + explanation."""
        
        if principle.principle == JusticePrinciple.MAXIMIZING_FLOOR:
            return DistributionGenerator._apply_maximizing_floor(distributions)
        
        elif principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE:
            return DistributionGenerator._apply_maximizing_average(distributions)
        
        elif principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
            return DistributionGenerator._apply_maximizing_average_floor_constraint(
                distributions, principle.constraint_amount
            )
        
        elif principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT:
            return DistributionGenerator._apply_maximizing_average_range_constraint(
                distributions, principle.constraint_amount
            )
        
        else:
            raise ValueError(f"Unknown principle: {principle.principle}")
    
    @staticmethod
    def _apply_maximizing_floor(distributions: List[IncomeDistribution]) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing floor principle - choose distribution with highest low income."""
        best_dist = max(distributions, key=lambda d: d.low)
        explanation = f"Chose distribution with highest floor income: ${best_dist.low}"
        return best_dist, explanation
    
    @staticmethod
    def _apply_maximizing_average(distributions: List[IncomeDistribution]) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing average principle - choose distribution with highest average."""
        best_dist = max(distributions, key=lambda d: d.get_average_income())
        explanation = f"Chose distribution with highest average income: ${best_dist.get_average_income():.0f}"
        return best_dist, explanation
    
    @staticmethod
    def _apply_maximizing_average_floor_constraint(
        distributions: List[IncomeDistribution], 
        floor_constraint: int
    ) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing average with floor constraint."""
        # Filter distributions that meet floor constraint
        valid_distributions = [d for d in distributions if d.low >= floor_constraint]
        
        if not valid_distributions:
            # No distribution meets constraint, choose one with highest floor
            best_dist = max(distributions, key=lambda d: d.low)
            explanation = f"No distribution met floor constraint of ${floor_constraint}. Chose distribution with highest floor: ${best_dist.low}"
        else:
            # Among valid distributions, choose one with highest average
            best_dist = max(valid_distributions, key=lambda d: d.get_average_income())
            explanation = f"Chose distribution with highest average (${best_dist.get_average_income():.0f}) meeting floor constraint of ${floor_constraint}"
        
        return best_dist, explanation
    
    @staticmethod
    def _apply_maximizing_average_range_constraint(
        distributions: List[IncomeDistribution],
        range_constraint: int
    ) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing average with range constraint."""
        # Filter distributions that meet range constraint
        valid_distributions = [d for d in distributions if d.get_range() <= range_constraint]
        
        if not valid_distributions:
            # No distribution meets constraint, choose one with smallest range
            best_dist = min(distributions, key=lambda d: d.get_range())
            explanation = f"No distribution met range constraint of ${range_constraint}. Chose distribution with smallest range: ${best_dist.get_range()}"
        else:
            # Among valid distributions, choose one with highest average
            best_dist = max(valid_distributions, key=lambda d: d.get_average_income())
            explanation = f"Chose distribution with highest average (${best_dist.get_average_income():.0f}) meeting range constraint of ${range_constraint}"
        
        return best_dist, explanation
    
    @staticmethod
    def calculate_payoff(distribution: IncomeDistribution) -> Tuple[IncomeClass, float]:
        """Randomly assign participant to income class and calculate payoff."""
        # Randomly assign to one of the five income classes
        income_classes = list(IncomeClass)
        assigned_class = random.choice(income_classes)
        
        # Get income for assigned class
        income = distribution.get_income_by_class(assigned_class)
        
        # Calculate payoff: $1 for every $10,000 of income
        payoff = income / 10000.0
        
        return assigned_class, payoff
    
    @staticmethod
    def calculate_alternative_earnings(distributions: List[IncomeDistribution]) -> dict:
        """Calculate what participant would have earned under each distribution."""
        alternative_earnings = {}
        
        for i, dist in enumerate(distributions):
            # For each distribution, randomly assign class and calculate earnings
            assigned_class, earnings = DistributionGenerator.calculate_payoff(dist)
            alternative_earnings[f"distribution_{i+1}"] = earnings
        
        return alternative_earnings
    
    @staticmethod
    def calculate_alternative_earnings_by_principle(
        distributions: List[IncomeDistribution], 
        constraint_amount: Optional[int] = None
    ) -> dict:
        """Calculate what participant would have earned under each principle choice."""
        from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
        
        alternative_earnings = {}
        
        # Define all four principles
        principles = [
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE, 
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]
        
        for principle in principles:
            try:
                # Create a principle choice (use provided constraint_amount or default)
                if principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 
                               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
                    # Use provided constraint or a reasonable default
                    constraint = constraint_amount if constraint_amount is not None else 15000
                    choice = PrincipleChoice(
                        principle=principle,
                        constraint_amount=constraint,
                        certainty=CertaintyLevel.SURE
                    )
                else:
                    choice = PrincipleChoice(
                        principle=principle,
                        certainty=CertaintyLevel.SURE
                    )
                
                # Apply this principle to the distributions
                chosen_distribution, _ = DistributionGenerator.apply_principle_to_distributions(
                    distributions, choice
                )
                
                # Calculate what they would have earned with this principle
                assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution)
                alternative_earnings[principle.value] = earnings
                
            except Exception as e:
                # If principle application fails, record as 0 earnings
                alternative_earnings[principle.value] = 0.0
        
        return alternative_earnings
    
    @staticmethod
    def calculate_alternative_earnings_by_principle_fixed_class(
        distributions: List[IncomeDistribution], 
        assigned_class: IncomeClass,
        constraint_amount: Optional[int] = None
    ) -> dict:
        """Calculate what participant would have earned under each principle with FIXED class assignment."""
        from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
        
        alternative_earnings = {}
        
        # Define all four principles
        principles = [
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE, 
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]
        
        for principle in principles:
            try:
                # Create a principle choice (use provided constraint_amount or default)
                if principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 
                               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
                    # Use provided constraint or a reasonable default
                    constraint = constraint_amount if constraint_amount is not None else 15000
                    choice = PrincipleChoice(
                        principle=principle,
                        constraint_amount=constraint,
                        certainty=CertaintyLevel.SURE
                    )
                else:
                    choice = PrincipleChoice(
                        principle=principle,
                        certainty=CertaintyLevel.SURE
                    )
                
                # Apply this principle to the distributions
                chosen_distribution, _ = DistributionGenerator.apply_principle_to_distributions(
                    distributions, choice
                )
                
                # Get income for the FIXED assigned class (not random)
                income = chosen_distribution.get_income_by_class(assigned_class)
                
                # Calculate payoff: $1 for every $10,000 of income
                earnings = income / 10000.0
                
                alternative_earnings[principle.value] = earnings
                
            except Exception as e:
                # If principle application fails, record as 0 earnings
                alternative_earnings[principle.value] = 0.0
        
        return alternative_earnings
    
    @staticmethod
    def format_distributions_table(distributions: List[IncomeDistribution]) -> str:
        """Format distributions as a table for display to participants."""
        table = "Income Distributions:\n\n"
        table += "| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |\n"
        table += "|--------------|---------|---------|---------|----------|\n"
        
        income_classes = ["High", "Medium high", "Medium", "Medium low", "Low"]
        class_attrs = ["high", "medium_high", "medium", "medium_low", "low"]
        
        for class_name, attr in zip(income_classes, class_attrs):
            table += f"| {class_name:<12} |"
            for dist in distributions:
                income = getattr(dist, attr)
                table += f" ${income:,} |".rjust(9)
            table += "\n"
        
        return table
    
    @staticmethod
    def format_principle_name_with_constraint(principle_choice) -> str:
        """Format principle name with constraint amount for display."""
        from models.principle_types import JusticePrinciple
        
        base_names = {
            JusticePrinciple.MAXIMIZING_FLOOR: "Maximizing the floor",
            JusticePrinciple.MAXIMIZING_AVERAGE: "Maximizing the average",
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT: "Maximizing the average with a floor constraint",
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT: "Maximizing the average with a range constraint"
        }
        
        base_name = base_names.get(principle_choice.principle, str(principle_choice.principle))
        
        if principle_choice.constraint_amount and principle_choice.principle in [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]:
            base_name += f" of ${principle_choice.constraint_amount:,}"
        
        return base_name