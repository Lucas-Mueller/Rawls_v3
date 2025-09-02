"""
Helper utilities for integration tests.
"""
import inspect
from typing import Type, List


def validate_mock_method_exists(target_class: Type, method_name: str) -> bool:
    """Validate that a method exists on the target class before mocking it.
    
    Args:
        target_class: The class to check
        method_name: The method name to validate
        
    Returns:
        True if method exists, False otherwise
        
    Raises:
        AttributeError: If method doesn't exist (with helpful message)
    """
    if not hasattr(target_class, method_name):
        available_methods = [name for name, method in inspect.getmembers(target_class, predicate=inspect.ismethod)]
        available_methods.extend([name for name, method in inspect.getmembers(target_class, predicate=inspect.isfunction)])
        
        raise AttributeError(
            f"Method '{method_name}' does not exist on {target_class.__name__}. "
            f"Available methods: {sorted(available_methods)}"
        )
    return True


def validate_utility_agent_methods(method_names: List[str]) -> bool:
    """Validate all required utility agent methods exist.
    
    Args:
        method_names: List of method names to validate
        
    Returns:
        True if all methods exist
        
    Raises:
        AttributeError: If any method doesn't exist
    """
    from experiment_agents import UtilityAgent
    
    for method_name in method_names:
        validate_mock_method_exists(UtilityAgent, method_name)
    
    return True


def get_utility_agent_mock_methods() -> List[str]:
    """Get the list of commonly mocked utility agent methods.
    
    This centralizes the method names to ensure consistency across tests
    and makes it easier to update when the API changes.
    """
    return [
        'parse_principle_ranking_enhanced',
        'parse_principle_choice_enhanced', 
        'validate_constraint_specification',
        'detect_numerical_agreement',
        'check_ballot_consensus'
    ]