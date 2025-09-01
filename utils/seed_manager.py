"""
Seed management for experiment reproducibility.
Provides centralized control over all randomness in the experiment system.
"""
import random
import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import ExperimentConfiguration

logger = logging.getLogger(__name__)


class SeedManager:
    """Instance-based seed management for experiment reproducibility.
    
    Each experiment gets its own Random instance to prevent interference
    between parallel experiments.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize seed manager with experiment-scoped random generator.
        
        Args:
            seed: Initial seed value (optional)
        """
        self._random = random.Random()
        self._current_seed = None
        if seed is not None:
            self.set_seed(seed)
    
    def set_seed(self, seed: int) -> None:
        """
        Set seed for this experiment's random operations.
        
        Args:
            seed: Positive integer to use as random seed
        """
        if not isinstance(seed, int) or seed < 0 or seed >= 2**31:
            raise ValueError(f"Seed must be a positive integer less than 2^31, got: {seed}")
        
        # Set this experiment's random generator seed
        self._random.seed(seed)
        self._current_seed = seed
        
        logger.info(f"Experiment random seed set to: {seed}")
    
    @property
    def random(self) -> random.Random:
        """Get the experiment-scoped random generator."""
        return self._random
    
    @property
    def current_seed(self) -> int:
        """Get the current seed value."""
        return self._current_seed
    
    def initialize_from_config(self, config: 'ExperimentConfiguration') -> int:
        """
        Initialize this seed manager from experiment configuration.
        
        Args:
            config: Experiment configuration
            
        Returns:
            The seed that was set (either explicit or generated)
        """
        effective_seed = config.get_effective_seed()
        self.set_seed(effective_seed)
        return effective_seed
    
    # Static methods kept for backward compatibility
    @staticmethod
    def set_experiment_seed(seed: int) -> None:
        """
        DEPRECATED: Set global random seed for all experiment operations.
        Use instance-based seed management instead.
        
        Args:
            seed: Positive integer to use as random seed
        """
        logger.warning("set_experiment_seed is deprecated. Use instance-based SeedManager instead.")
        if not isinstance(seed, int) or seed < 0 or seed >= 2**31:
            raise ValueError(f"Seed must be a positive integer less than 2^31, got: {seed}")
        
        # Set Python's random module seed
        random.seed(seed)
        
        logger.info(f"Global random seed set to: {seed}")
    
    @staticmethod
    def generate_seed_from_config(config: 'ExperimentConfiguration') -> int:
        """
        Generate deterministic seed from configuration parameters.
        Same configuration will always produce the same seed.
        
        Args:
            config: Experiment configuration to generate seed from
            
        Returns:
            Positive 32-bit integer seed
        """
        # Collect configuration elements that affect experiment behavior
        seed_components = [
            # Basic experiment structure
            len(config.agents),
            config.phase2_rounds,
            config.language,
            
            # Agent configurations
            str(sorted([agent.name for agent in config.agents])),
            str(sorted([agent.model for agent in config.agents])),
            str(sorted([agent.personality for agent in config.agents])),
            str(sorted([agent.temperature for agent in config.agents])),
            str(sorted([agent.reasoning_enabled for agent in config.agents])),
            
            # Distribution settings
            str(config.distribution_range_phase1) if hasattr(config, 'distribution_range_phase1') else "default_phase1",
            str(config.distribution_range_phase2) if hasattr(config, 'distribution_range_phase2') else "default_phase2",
            
            # Utility agent
            config.utility_agent_model,
            getattr(config, 'utility_agent_temperature', 0.0),
            
            # Income class probabilities if present
            str(config.income_class_probabilities) if hasattr(config, 'income_class_probabilities') else "default_probs",
            
            # Original values mode if present
            str(getattr(config, 'original_values_mode', {})),
        ]
        
        # Create deterministic hash from components
        config_string = "|".join(str(component) for component in seed_components)
        config_hash = hashlib.sha256(config_string.encode('utf-8')).hexdigest()
        
        # Convert hash to positive 32-bit integer
        seed = int(config_hash[:8], 16) % (2**31)  # Use first 8 hex chars, ensure positive
        
        logger.info(f"Generated seed {seed} from configuration hash")
        logger.debug(f"Configuration components used for seed: {len(seed_components)} elements")
        
        return seed
    
    @staticmethod
    def initialize_reproducibility(config: 'ExperimentConfiguration') -> int:
        """
        DEPRECATED: ALWAYS initialize reproducibility and return the seed used.
        Use instance-based approach instead.
        
        Args:
            config: Experiment configuration
            
        Returns:
            The seed that was set (either explicit or generated)
        """
        logger.warning("initialize_reproducibility is deprecated. Use instance-based SeedManager instead.")
        effective_seed = config.get_effective_seed()
        SeedManager.set_experiment_seed(effective_seed)
        return effective_seed
    
    @staticmethod
    def validate_seed(seed: int) -> bool:
        """
        Validate that a seed value is acceptable.
        
        Args:
            seed: Seed value to validate
            
        Returns:
            True if seed is valid, False otherwise
        """
        return isinstance(seed, int) and 0 <= seed < 2**31