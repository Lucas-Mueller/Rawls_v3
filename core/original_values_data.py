"""
Original Values Data Store for the Frohlich Experiment.

This module contains predefined distribution situations for Original Values Mode,
where Phase 1 uses fixed distributions instead of randomly generated ones.
"""
from typing import List, Dict
from models.experiment_types import IncomeDistribution, IncomeClassProbabilities


class OriginalValuesData:
    """Storage for predefined distribution situations."""
    
    SITUATIONS = {
        "sample": {
            "distributions": [
                IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
                IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
                IncomeDistribution(high=31000, medium_high=24000, medium=21000, medium_low=16000, low=14000),
                IncomeDistribution(high=21000, medium_high=20000, medium=19000, medium_low=16000, low=15000)
            ],
            "probabilities": IncomeClassProbabilities(
                high=0.050000, medium_high=0.100000, medium=0.500000, 
                medium_low=0.250000, low=0.100000
            )
        },
        "a": {
            "distributions": [
                IncomeDistribution(high=28000, medium_high=25000, medium=20000, medium_low=15000, low=12000),
                IncomeDistribution(high=35000, medium_high=30000, medium=25000, medium_low=15000, low=10000),
                IncomeDistribution(high=30000, medium_high=29000, medium=28000, medium_low=27000, low=6000),
                IncomeDistribution(high=25000, medium_high=22000, medium=19000, medium_low=16000, low=13000)
            ],
            "probabilities": IncomeClassProbabilities(
                high=0.100000, medium_high=0.200000, medium=0.400000, 
                medium_low=0.200000, low=0.100000
            )
        },
        "b": {
            "distributions": [
                IncomeDistribution(high=17000, medium_high=16000, medium=15000, medium_low=14000, low=13000),
                IncomeDistribution(high=30000, medium_high=25000, medium=20000, medium_low=15000, low=12500),
                IncomeDistribution(high=40000, medium_high=30000, medium=25000, medium_low=20000, low=8000),
                IncomeDistribution(high=26000, medium_high=24000, medium=22000, medium_low=20000, low=11000)
            ],
            "probabilities": IncomeClassProbabilities(
                high=0.063060, medium_high=0.208333, medium=0.283333, 
                medium_low=0.345274, low=0.100000
            )
        },
        "c": {
            "distributions": [
                IncomeDistribution(high=100000, medium_high=30000, medium=20000, medium_low=15000, low=13000),
                IncomeDistribution(high=35000, medium_high=30000, medium=25000, medium_low=20000, low=8000),
                IncomeDistribution(high=30000, medium_high=25000, medium=23000, medium_low=15000, low=12000),
                IncomeDistribution(high=24000, medium_high=23000, medium=22000, medium_low=21000, low=11000)
            ],
            "probabilities": IncomeClassProbabilities(
                high=0.013334, medium_high=0.043333, medium=0.583333, 
                medium_low=0.260000, low=0.100000
            )
        },
        "d": {
            "distributions": [
                IncomeDistribution(high=35000, medium_high=30000, medium=25000, medium_low=20000, low=13000),
                IncomeDistribution(high=30000, medium_high=28000, medium=26000, medium_low=24000, low=12000),
                IncomeDistribution(high=20000, medium_high=18000, medium=16000, medium_low=14000, low=12000),
                IncomeDistribution(high=30000, medium_high=28000, medium=24000, medium_low=20000, low=14000)
            ],
            "probabilities": IncomeClassProbabilities(
                high=0.050000, medium_high=0.208333, medium=0.283333, 
                medium_low=0.358334, low=0.100000
            )
        }
    }
    
    @classmethod
    def get_situation(cls, situation_name: str) -> Dict:
        """Get distributions and probabilities for a situation."""
        situation = cls.SITUATIONS.get(situation_name.lower())
        if not situation:
            raise ValueError(f"Unknown situation: {situation_name}. Valid situations: {list(cls.SITUATIONS.keys())}")
        return situation
    
    @classmethod
    def get_distributions(cls, situation_name: str) -> List[IncomeDistribution]:
        """Get distributions for a situation."""
        return cls.get_situation(situation_name)["distributions"]
    
    @classmethod
    def get_probabilities(cls, situation_name: str) -> IncomeClassProbabilities:
        """Get probabilities for a situation."""
        return cls.get_situation(situation_name)["probabilities"]
    
    @classmethod
    def list_situations(cls) -> List[str]:
        """Get list of available situation names."""
        return list(cls.SITUATIONS.keys())
    
    @classmethod
    def validate_probabilities(cls) -> bool:
        """Validate that all situation probabilities sum to 1.0."""
        for situation_name, situation_data in cls.SITUATIONS.items():
            probs = situation_data["probabilities"]
            total = probs.high + probs.medium_high + probs.medium + probs.medium_low + probs.low
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"Probabilities for situation '{situation_name}' sum to {total}, not 1.0")
        return True