"""
Distribution generation system for the Frohlich Experiment.
"""
import random
from typing import List, Tuple, Optional, Dict, Any
from models import (
    IncomeDistribution, DistributionSet, PrincipleChoice, JusticePrinciple, IncomeClass
)
from models.experiment_types import IncomeClassProbabilities


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
    def generate_dynamic_distribution(multiplier_range: Tuple[float, float], random_gen: random.Random = None) -> DistributionSet:
        """Generate 4 distributions with random multiplier applied to base distributions.
        
        Args:
            multiplier_range: Range for random multiplier
            random_gen: Random generator to use (defaults to global random)
        """
        if random_gen is None:
            random_gen = random
        multiplier = random_gen.uniform(multiplier_range[0], multiplier_range[1])
        
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
    def get_original_values_distribution(round_number: int) -> DistributionSet:
        """Get predefined distribution set for original values mode based on round number."""
        from .original_values_data import OriginalValuesData
        
        # Map round numbers to situations:
        # Round 1 -> Situation A, Round 2 -> Situation B, etc.
        situation_map = {
            1: "a",
            2: "b", 
            3: "c",
            4: "d"
        }
        
        situation = situation_map.get(round_number)
        if not situation:
            raise ValueError(f"Original values mode only supports rounds 1-4, got round {round_number}")
            
        distributions = OriginalValuesData.get_distributions(situation)
        return DistributionSet(distributions=distributions, multiplier=1.0)

    @staticmethod
    def get_original_values_probabilities(round_number: int) -> IncomeClassProbabilities:
        """Get situation-specific probabilities for original values mode based on round number."""
        from .original_values_data import OriginalValuesData
        
        # Map round numbers to situations:
        # Round 1 -> Situation A, Round 2 -> Situation B, etc.
        situation_map = {
            1: "a",
            2: "b",
            3: "c", 
            4: "d"
        }
        
        situation = situation_map.get(round_number)
        if not situation:
            raise ValueError(f"Original values mode only supports rounds 1-4, got round {round_number}")
            
        return OriginalValuesData.get_probabilities(situation)
    
    @staticmethod
    def get_sample_distribution() -> DistributionSet:
        """Get sample distribution set for explanations in original values mode."""
        from .original_values_data import OriginalValuesData
        
        distributions = OriginalValuesData.get_distributions("sample")
        return DistributionSet(distributions=distributions, multiplier=1.0)

    @staticmethod
    def get_sample_probabilities() -> IncomeClassProbabilities:
        """Get sample probabilities for explanations in original values mode."""
        from .original_values_data import OriginalValuesData
        return OriginalValuesData.get_probabilities("sample")
    
    @staticmethod
    def apply_principle_to_distributions(
        distributions: List[IncomeDistribution],
        principle: PrincipleChoice,
        probabilities: Optional[IncomeClassProbabilities] = None,
        language_manager = None
    ) -> Tuple[IncomeDistribution, str]:
        """Apply justice principle logic and return chosen distribution + explanation."""
        
        if principle.principle == JusticePrinciple.MAXIMIZING_FLOOR:
            return DistributionGenerator._apply_maximizing_floor(distributions, language_manager)
        
        elif principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE:
            return DistributionGenerator._apply_maximizing_average(distributions, probabilities, language_manager)
        
        elif principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
            return DistributionGenerator._apply_maximizing_average_floor_constraint(
                distributions, principle.constraint_amount, probabilities, language_manager
            )
        
        elif principle.principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT:
            return DistributionGenerator._apply_maximizing_average_range_constraint(
                distributions, principle.constraint_amount, probabilities, language_manager
            )
        
        else:
            raise ValueError(f"Unknown principle: {principle.principle}")
    
    @staticmethod
    def _apply_maximizing_floor(distributions: List[IncomeDistribution], language_manager) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing floor principle - choose distribution with highest low income."""
        best_dist = max(distributions, key=lambda d: d.low)
        if language_manager:
            explanation = language_manager.get("constraint_explanations.maximizing_floor_explanation", floor_amount=best_dist.low)
        else:
            explanation = f"Chose distribution with highest floor income: ${best_dist.low}"
        return best_dist, explanation
    
    @staticmethod
    def _apply_maximizing_average(
        distributions: List[IncomeDistribution], 
        probabilities: Optional[IncomeClassProbabilities] = None,
        language_manager = None
    ) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing average principle with weighted calculation."""
        best_dist = max(distributions, key=lambda d: d.get_average_income(probabilities))
        avg_income = best_dist.get_average_income(probabilities)
        if language_manager:
            explanation = language_manager.get("constraint_explanations.maximizing_average_explanation", 
                                             weighted="weighted " if probabilities else "", 
                                             avg_income=avg_income)
        else:
            explanation = f"Chose distribution with highest {'weighted ' if probabilities else ''}average income: ${avg_income:.0f}"
        return best_dist, explanation
    
    @staticmethod
    def _apply_maximizing_average_floor_constraint(
        distributions: List[IncomeDistribution], 
        floor_constraint: int,
        probabilities: Optional[IncomeClassProbabilities] = None,
        language_manager = None
    ) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing average with floor constraint."""
        # Filter distributions that meet floor constraint
        valid_distributions = [d for d in distributions if d.low >= floor_constraint]
        
        if not valid_distributions:
            # No distribution meets constraint, choose one with highest floor
            best_dist = max(distributions, key=lambda d: d.low)
            if language_manager:
                explanation = language_manager.get("constraint_explanations.floor_constraint_fallback", 
                                                 constraint_amount=floor_constraint, 
                                                 actual_floor=best_dist.low)
            else:
                explanation = f"No distribution met floor constraint of ${floor_constraint}. Chose distribution with highest floor: ${best_dist.low}"
        else:
            # Among valid distributions, choose one with highest average
            best_dist = max(valid_distributions, key=lambda d: d.get_average_income(probabilities))
            avg_income = best_dist.get_average_income(probabilities)
            if language_manager:
                explanation = language_manager.get("constraint_explanations.floor_constraint_success", 
                                                 weighted="weighted " if probabilities else "", 
                                                 avg_income=avg_income, 
                                                 constraint_amount=floor_constraint)
            else:
                explanation = f"Chose distribution with highest {'weighted ' if probabilities else ''}average (${avg_income:.0f}) meeting floor constraint of ${floor_constraint}"
        
        return best_dist, explanation
    
    @staticmethod
    def _apply_maximizing_average_range_constraint(
        distributions: List[IncomeDistribution],
        range_constraint: int,
        probabilities: Optional[IncomeClassProbabilities] = None,
        language_manager = None
    ) -> Tuple[IncomeDistribution, str]:
        """Apply maximizing average with range constraint."""
        # Filter distributions that meet range constraint
        valid_distributions = [d for d in distributions if d.get_range() <= range_constraint]
        
        if not valid_distributions:
            # No distribution meets constraint, choose one with smallest range
            best_dist = min(distributions, key=lambda d: d.get_range())
            if language_manager:
                explanation = language_manager.get("constraint_explanations.range_constraint_fallback", 
                                                 constraint_amount=range_constraint, 
                                                 actual_range=best_dist.get_range())
            else:
                explanation = f"No distribution met range constraint of ${range_constraint}. Chose distribution with smallest range: ${best_dist.get_range()}"
        else:
            # Among valid distributions, choose one with highest average
            best_dist = max(valid_distributions, key=lambda d: d.get_average_income(probabilities))
            avg_income = best_dist.get_average_income(probabilities)
            if language_manager:
                explanation = language_manager.get("constraint_explanations.range_constraint_success", 
                                                 weighted="weighted " if probabilities else "", 
                                                 avg_income=avg_income, 
                                                 constraint_amount=range_constraint)
            else:
                explanation = f"Chose distribution with highest {'weighted ' if probabilities else ''}average (${avg_income:.0f}) meeting range constraint of ${range_constraint}"
        
        return best_dist, explanation
    
    @staticmethod
    def calculate_payoff(
        distribution: IncomeDistribution, 
        probabilities: Optional[IncomeClassProbabilities] = None,
        random_gen: random.Random = None
    ) -> Tuple[IncomeClass, float]:
        """Assign participant to income class using weighted probabilities.
        
        Args:
            distribution: Income distribution to calculate payoff from
            probabilities: Weighted probabilities for income class assignment
            random_gen: Random generator to use (defaults to global random)
        """
        if random_gen is None:
            random_gen = random
        
        income_classes = list(IncomeClass)
        
        if probabilities is None:
            # Backward compatibility: equal probabilities
            assigned_class = random_gen.choice(income_classes)
        else:
            # Weighted random selection
            weights = [
                probabilities.high,
                probabilities.medium_high,
                probabilities.medium,
                probabilities.medium_low,
                probabilities.low
            ]
            assigned_class = random_gen.choices(income_classes, weights=weights, k=1)[0]
        
        # Get income and calculate payoff
        income = distribution.get_income_by_class(assigned_class)
        payoff = round(income / 10000.0, 2)
        
        return assigned_class, payoff
    
    @staticmethod
    def calculate_alternative_earnings(
        distributions: List[IncomeDistribution],
        probabilities: Optional[IncomeClassProbabilities] = None,
        random_gen: random.Random = None
    ) -> dict:
        """Calculate what participant would have earned under each distribution.

        Args:
            distributions: List of distributions to calculate earnings for
            probabilities: Optional weighted probabilities for income class assignment
            random_gen: Random generator to use (defaults to global random)
        """
        alternative_earnings = {}

        for i, dist in enumerate(distributions):
            # For each distribution, randomly assign class and calculate earnings
            assigned_class, earnings = DistributionGenerator.calculate_payoff(
                dist,
                probabilities,
                random_gen=random_gen
            )
            alternative_earnings[f"distribution_{i+1}"] = earnings

        return alternative_earnings

    @staticmethod
    def calculate_alternative_earnings_by_principle(
        distributions: List[IncomeDistribution], 
        constraint_amount: Optional[int] = None,
        probabilities: Optional[IncomeClassProbabilities] = None,
        random_gen: random.Random = None
    ) -> dict:
        """Calculate what participant would have earned under each principle choice.

        Args:
            distributions: List of distributions to apply principles to
            constraint_amount: Optional constraint amount for constrained principles
            probabilities: Optional weighted probabilities for distribution selection and payoff
            random_gen: Random generator to use (defaults to global random)
        """
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
                    distributions,
                    choice,
                    probabilities,
                    language_manager=None
                )

                # Calculate what they would have earned with this principle
                assigned_class, earnings = DistributionGenerator.calculate_payoff(
                    chosen_distribution,
                    probabilities,
                    random_gen=random_gen
                )
                alternative_earnings[principle.value] = earnings

            except Exception as e:
                # If principle application fails, record as 0 earnings
                alternative_earnings[principle.value] = 0.0
        
        return alternative_earnings
    
    @staticmethod
    def calculate_alternative_earnings_by_principle_fixed_class(
        distributions: List[IncomeDistribution],
        assigned_class: IncomeClass,
        constraint_amount: Optional[int] = None,
        probabilities: Optional[IncomeClassProbabilities] = None
    ) -> dict:
        """
        Calculate what participant would have earned under each principle with FIXED class assignment.

        Uses appropriate constraint values for each principle type to avoid incorrect constraint reuse.
        Floor constraints use median floor value, range constraints use median range value.

        Args:
            distributions: List of distributions to apply principles to
            assigned_class: The income class assigned to the participant
            constraint_amount: DEPRECATED - Not used to avoid constraint reuse bug

        Returns:
            Dict mapping principle names to earnings
        """
        from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel

        alternative_earnings = {}

        # Determine constraint values to use for each constraint type
        # Use median values from distributions to avoid constraint reuse bug
        floor_values = sorted([d.low for d in distributions])
        floor_constraint_value = floor_values[len(floor_values) // 2]

        range_values = sorted([d.get_range() for d in distributions])
        range_constraint_value = range_values[len(range_values) // 2]

        # Define all four principles
        principles = [
            JusticePrinciple.MAXIMIZING_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]

        for principle in principles:
            try:
                # Create a principle choice with appropriate constraint value
                if principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
                    # Use floor constraint value (median floor)
                    choice = PrincipleChoice(
                        principle=principle,
                        constraint_amount=floor_constraint_value,
                        certainty=CertaintyLevel.SURE
                    )
                elif principle == JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT:
                    # Use range constraint value (median range)
                    choice = PrincipleChoice(
                        principle=principle,
                        constraint_amount=range_constraint_value,
                        certainty=CertaintyLevel.SURE
                    )
                else:
                    # No constraint needed
                    choice = PrincipleChoice(
                        principle=principle,
                        certainty=CertaintyLevel.SURE
                    )

                # Apply this principle to the distributions
                chosen_distribution, _ = DistributionGenerator.apply_principle_to_distributions(
                    distributions,
                    choice,
                    probabilities,
                    language_manager=None
                )

                # Get income for the FIXED assigned class (not random)
                income = chosen_distribution.get_income_by_class(assigned_class)

                # Calculate payoff: $1 for every $10,000 of income
                earnings = round(income / 10000.0, 2)

                alternative_earnings[principle.value] = earnings

            except Exception as e:
                # If principle application fails, record as 0 earnings
                alternative_earnings[principle.value] = 0.0

        return alternative_earnings
    
    @staticmethod
    def format_distributions_table(distributions: List[IncomeDistribution], language_manager, probabilities: Optional[IncomeClassProbabilities] = None) -> str:
        """Format distributions as a table for display to participants, with an averages row.
        If probabilities are provided, averages are weighted; otherwise unweighted.
        """
        
        # Get localized table components
        table = language_manager.get("prompts.distribution_distributions_table_header")
        table += language_manager.get("prompts.distribution_distributions_table_column_header")
        table += language_manager.get("prompts.distribution_distributions_table_separator")
        
        # Get income class names using new API
        income_class_names = {
            "high": language_manager.get("common.income_classes.high"),
            "medium_high": language_manager.get("common.income_classes.medium_high"),
            "medium": language_manager.get("common.income_classes.medium"),
            "medium_low": language_manager.get("common.income_classes.medium_low"),
            "low": language_manager.get("common.income_classes.low")
        }
        class_attrs = ["high", "medium_high", "medium", "medium_low", "low"]
        
        for attr in class_attrs:
            class_name = income_class_names[attr]
            table += f"| {class_name:<12} |"
            for dist in distributions:
                income = getattr(dist, attr)
                table += f" ${income:,} |".rjust(9)
            table += "\n"
        
        # Add averages row as part of the same Markdown table
        try:
            avg_label = language_manager.get("distributions.average_row_label")
        except Exception:
            avg_label = "Average"
        table += f"| {avg_label:<12} |"
        for dist in distributions:
            avg = dist.get_average_income(probabilities)
            # Use language manager currency format if available
            try:
                avg_str = language_manager.get('constraint_formatting.currency_format', amount=int(round(avg)))
            except Exception:
                avg_str = f"${int(round(avg)):,}"
            table += f" {avg_str} |"
        table += "\n"
        
        return table
    
    @staticmethod
    def format_principle_name_with_constraint(principle_choice, language_manager) -> str:
        """Format principle name with constraint amount for display."""
        from models.principle_types import JusticePrinciple
        # Get principle names using new API
        try:
            base_name = language_manager.get(f"common.principle_names.{principle_choice.principle.value}")
        except (KeyError, ValueError):
            base_name = str(principle_choice.principle)
        
        if principle_choice.constraint_amount and principle_choice.principle in [
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        ]:
            try:
                if language_manager:
                    if principle_choice.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
                        constraint_text = language_manager.get(
                            "results_explicit.floor_constraint_label",
                            amount=f"{principle_choice.constraint_amount:,}"
                        )
                    else:
                        constraint_text = language_manager.get(
                            "results_explicit.range_constraint_label",
                            amount=f"{principle_choice.constraint_amount:,}"
                        )
                    base_name = f"{base_name} {constraint_text}"
                else:
                    base_name += f" of ${principle_choice.constraint_amount:,}"
            except Exception:
                base_name += f" of ${principle_choice.constraint_amount:,}"

        return base_name
    
    @staticmethod
    def calculate_comprehensive_constraint_outcomes(
        distributions: List[IncomeDistribution],
        assigned_class: IncomeClass,
        language_manager,
        probabilities: Optional[IncomeClassProbabilities] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive principle outcomes testing all constraint values.
        Uses LanguageManager for all text formatting and localization.
        
        Args:
            distributions: List of available distributions
            assigned_class: Agent's assigned income class
            language_manager: LanguageManager instance for localization
            probabilities: Income class probabilities for weighted average calculation
            
        Returns:
            {
                'outcomes': List of outcome dictionaries with localized text,
                'distributions_table': Formatted table string using LanguageManager,
                'class_display_name': Localized class name
            }
        """
        from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
        
        outcomes = []
        
        # 1. Maximizing Floor - get localized name from language manager
        principle_name = language_manager.get('common.principle_names.maximizing_floor')
        best_floor_dist, explanation = DistributionGenerator._apply_maximizing_floor(distributions, language_manager)
        agent_income = best_floor_dist.get_income_by_class(assigned_class)
        
        outcomes.append({
            'principle_key': 'maximizing_floor',
            'principle_name': principle_name,
            'distribution_index': distributions.index(best_floor_dist),
            'distribution': best_floor_dist,
            'agent_income': agent_income,
            'agent_earnings': round(agent_income / 10000.0, 2),
            'explanation': explanation,
            'constraint_amount': None
        })
        
        # 2. Maximizing Average - get localized name
        principle_name = language_manager.get('common.principle_names.maximizing_average')
        best_avg_dist, explanation = DistributionGenerator._apply_maximizing_average(distributions, probabilities, language_manager)
        agent_income = best_avg_dist.get_income_by_class(assigned_class)
        
        outcomes.append({
            'principle_key': 'maximizing_average',
            'principle_name': principle_name,
            'distribution_index': distributions.index(best_avg_dist),
            'distribution': best_avg_dist,
            'agent_income': agent_income,
            'agent_earnings': round(agent_income / 10000.0, 2),
            'explanation': explanation,
            'constraint_amount': None
        })
        
        # 3. Floor Constraints - test all distribution low income values
        tested_floors = set()
        for dist in distributions:
            floor_value = dist.low
            if floor_value not in tested_floors:
                tested_floors.add(floor_value)
                
                choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                    constraint_amount=floor_value,
                    certainty=CertaintyLevel.SURE
                )
                
                best_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
                    distributions, choice, probabilities, language_manager
                )
                agent_income = best_dist.get_income_by_class(assigned_class)
                
                # Use LanguageManager for constraint formatting with full principle name
                base_principle_name = language_manager.get('common.principle_names.maximizing_average_floor_constraint')
                constraint_label = language_manager.get(
                    'constraint_formatting.floor_constraint',
                    amount=language_manager.get('constraint_formatting.currency_format', amount=floor_value)
                )
                principle_name = f"{base_principle_name} {constraint_label}"
                
                outcomes.append({
                    'principle_key': 'maximizing_average_floor_constraint', 
                    'principle_name': principle_name,
                    'distribution_index': distributions.index(best_dist),
                    'distribution': best_dist,
                    'agent_income': agent_income,
                    'agent_earnings': round(agent_income / 10000.0, 2),
                    'explanation': explanation,
                    'constraint_amount': floor_value
                })
        
        # 4. Range Constraints - test all distribution ranges
        tested_ranges = set()
        for dist in distributions:
            range_value = dist.get_range()
            if range_value not in tested_ranges:
                tested_ranges.add(range_value)
                
                choice = PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                    constraint_amount=range_value,
                    certainty=CertaintyLevel.SURE
                )
                
                best_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
                    distributions, choice, probabilities, language_manager
                )
                agent_income = best_dist.get_income_by_class(assigned_class)
                
                # Use LanguageManager for constraint formatting with full principle name
                base_principle_name = language_manager.get('common.principle_names.maximizing_average_range_constraint')
                constraint_label = language_manager.get(
                    'constraint_formatting.range_constraint',
                    amount=language_manager.get('constraint_formatting.currency_format', amount=range_value)
                )
                principle_name = f"{base_principle_name} {constraint_label}"
                
                outcomes.append({
                    'principle_key': 'maximizing_average_range_constraint',
                    'principle_name': principle_name, 
                    'distribution_index': distributions.index(best_dist),
                    'distribution': best_dist,
                    'agent_income': agent_income,
                    'agent_earnings': round(agent_income / 10000.0, 2),
                    'explanation': explanation,
                    'constraint_amount': range_value
                })
        
        # Generate distributions table using LanguageManager
        distributions_table = DistributionGenerator._format_distributions_table_comprehensive(
            distributions, language_manager, probabilities
        )
        
        # Get localized class display name
        class_display_name = language_manager.get(f'common.income_classes.{assigned_class.value}')
        
        return {
            'outcomes': outcomes,
            'distributions_table': distributions_table,
            'class_display_name': class_display_name
        }
    
    @staticmethod
    def _format_distributions_table_comprehensive(distributions: List[IncomeDistribution], language_manager, probabilities: Optional[IncomeClassProbabilities] = None) -> str:
        """Format distributions table using LanguageManager for all text with optional weighted averages."""
        
        lines = []
        
        # Header
        lines.append(language_manager.get('comprehensive_earnings.distributions_table_header'))
        lines.append("")  # Empty line
        
        # Table header with localized income class names
        header_row = f"| {language_manager.get('distributions.income_class_header')} |"
        for i in range(len(distributions)):
            column_header = language_manager.get('distributions.column_header', number=i+1)
            header_row += f" {column_header} |"
        lines.append(header_row)
        
        # Separator - create proper markdown table separator with dashes for each column
        separator = "|"
        for _ in range(len(distributions) + 1):  # +1 for income class column
            separator += "------------|"
        lines.append(separator)
        
        # Income class rows using LanguageManager
        income_class_keys = ['high', 'medium_high', 'medium', 'medium_low', 'low']
        for class_key in income_class_keys:
            class_name = language_manager.get(f'common.income_classes.{class_key}')
            row = f"| {class_name} |"

            for dist in distributions:
                income = getattr(dist, class_key)
                formatted_income = language_manager.get('constraint_formatting.currency_format', amount=income)
                row += f" {formatted_income} |"
            lines.append(row)

        # Add average row (weighted if probabilities provided)
        avg_label = language_manager.get('distributions.average_row_label')
        row = f"| {avg_label} |"
        for dist in distributions:
            avg = dist.get_average_income(probabilities)
            formatted_avg = language_manager.get('constraint_formatting.currency_format', amount=int(round(avg)))
            row += f" {formatted_avg} |"
        lines.append(row)

        return "\n".join(lines)
