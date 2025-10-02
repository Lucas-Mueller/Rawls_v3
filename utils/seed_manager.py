"""
Seed management for experiment reproducibility.
Provides centralized control over all randomness in the experiment system.
"""
import json
import random
import hashlib
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config import ExperimentConfiguration

logger = logging.getLogger(__name__)


def _serialize_for_seed(value: Any) -> str:
    """Serialize arbitrary values into a stable string for seed hashing."""
    if value is None:
        return "None"
    if hasattr(value, "model_dump"):
        try:
            return json.dumps(value.model_dump(), sort_keys=True)
        except Exception:
            return str(value)
    if isinstance(value, dict):
        try:
            return json.dumps(value, sort_keys=True)
        except Exception:
            return str(value)
    if isinstance(value, (list, tuple, set)):
        return "[" + ",".join(_serialize_for_seed(item) for item in value) + "]"
    return str(value)


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
        raw_components = [
            # Basic experiment structure
            len(config.agents),
            config.phase2_rounds,
            config.language,

            # Agent configurations
            sorted([agent.name for agent in config.agents]),
            sorted([agent.model for agent in config.agents]),
            sorted([agent.personality for agent in config.agents]),
            sorted([agent.temperature for agent in config.agents]),
            sorted([agent.reasoning_enabled for agent in config.agents]),

            # Distribution settings
            getattr(config, 'distribution_range_phase1', None),
            getattr(config, 'distribution_range_phase2', None),

            # Utility agent
            config.utility_agent_model,
            getattr(config, 'utility_agent_temperature', 0.0),

            # Income class probabilities if present
            config.income_class_probabilities,

            # Original values mode if present
            getattr(config, 'original_values_mode', None),

            # Speaking order configuration
            getattr(config, 'randomize_speaking_order', None),
            getattr(config, 'speaking_order_strategy', None),

            # Memory and retry configuration
            getattr(config, 'memory_guidance_style', None),
            getattr(config, 'include_experiment_explanation_each_turn', None),
            getattr(config, 'phase2_include_internal_reasoning_in_memory', None),
            getattr(config, 'selective_memory_updates', None),
            getattr(config, 'memory_update_threshold', None),
            getattr(config, 'batch_simple_events', None),
            getattr(config, 'enable_intelligent_retries', None),
            getattr(config, 'enable_progressive_guidance', None),
            getattr(config, 'memory_update_on_retry', None),
            getattr(config, 'max_participant_retries', None),
            getattr(config, 'retry_feedback_detail', None),

            # Phase 2 specific settings
            getattr(config, 'phase2_settings', None),

            # Logging configuration
            getattr(config, 'logging', None),
        ]

        # Create deterministic hash from components
        config_string = "|".join(_serialize_for_seed(component) for component in raw_components)
        config_hash = hashlib.sha256(config_string.encode('utf-8')).hexdigest()
        
        # Convert hash to positive 32-bit integer
        seed = int(config_hash[:8], 16) % (2**31)  # Use first 8 hex chars, ensure positive
        
        logger.info(f"Generated seed {seed} from configuration hash")
        logger.debug(f"Configuration components used for seed: {len(raw_components)} elements")
        
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
