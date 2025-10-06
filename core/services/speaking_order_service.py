"""
Speaking Order Service for Phase 2 Discussion Management.

Handles all speaking order strategies and finisher restriction rules
with deterministic reproducibility via seed management.
"""

import random
from typing import List, Optional, Protocol
from config.phase2_settings import Phase2Settings


class SeedManager(Protocol):
    """Protocol for seed managers that provide deterministic randomness."""
    @property
    def random(self) -> random.Random:
        """Get a deterministic random instance."""
        ...


class Logger(Protocol):
    """Protocol for logging warnings."""
    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        ...


class SpeakingOrderService:
    """
    Manages speaking order strategies with deterministic finisher restriction rules.
    
    Supports three strategies:
    - fixed: Same sequence every round with rotation
    - random: Shuffled order with finisher restriction
    - conversational: Weighted selection excluding recent speakers
    """
    
    def __init__(self, seed_manager: Optional[SeedManager] = None, 
                 settings: Optional[Phase2Settings] = None,
                 logger: Optional[Logger] = None):
        """
        Initialize speaking order service.
        
        Args:
            seed_manager: For reproducible randomness (optional)
            settings: Phase 2 settings for validation (optional)
            logger: For logging warnings (optional)
        """
        self.seed_manager = seed_manager
        self.settings = settings or Phase2Settings.get_default()
        self.logger = logger
        
    def _log_warning(self, message: str) -> None:
        """Log warning message if logger is available."""
        if self.logger:
            self.logger.log_warning(message)
    
    def generate_speaking_order(self, round_num: int, num_participants: int, 
                               randomize_speaking_order: bool, strategy: str,
                               last_round_finisher: Optional[int] = None) -> List[int]:
        """
        Generate speaking order with finisher restriction.
        
        Args:
            round_num: Current round number (1-based)
            num_participants: Number of participants  
            randomize_speaking_order: Whether to randomize order
            strategy: Speaking order strategy ('fixed', 'random', 'conversational')
            last_round_finisher: Index of participant who finished last round
            
        Returns:
            List of participant indices (0-based) in speaking order
            
        Implements restriction: if round N ends with Agent X, round N+1 cannot start with Agent X.
        """
        participant_indices = list(range(num_participants))
        
        # Validate minimum participants
        if num_participants < self.settings.min_agents_for_experiment:
            self._log_warning(f"Only {num_participants} agents, below minimum of {self.settings.min_agents_for_experiment}")
            # Continue anyway but log warning
        
        if not randomize_speaking_order or strategy == "fixed":
            return self._generate_fixed_order(participant_indices, round_num, last_round_finisher)
        
        if strategy == "random":
            return self._generate_random_order(participant_indices, last_round_finisher)
        
        elif strategy == "conversational":
            return self._generate_conversational_order(participant_indices, last_round_finisher)
        
        # Fallback to fixed order for unknown strategies
        self._log_warning(f"Unknown speaking order strategy '{strategy}', falling back to fixed")
        return self._generate_fixed_order(participant_indices, round_num, last_round_finisher)
    
    def _generate_fixed_order(self, participant_indices: List[int], round_num: int,
                             last_round_finisher: Optional[int]) -> List[int]:
        """Generate fixed order with rotation to avoid same finisher-starter pattern."""
        num_participants = len(participant_indices)
        
        # Fixed order: same sequence every round, but apply rotation for small groups
        if last_round_finisher is not None and num_participants > 1:
            # Rotate the list to avoid same finisher-starter pattern
            rotation_amount = (round_num - 1) % num_participants
            participant_indices = participant_indices[rotation_amount:] + participant_indices[:rotation_amount]
        
        return participant_indices
    
    def _generate_random_order(self, participant_indices: List[int],
                              last_round_finisher: Optional[int]) -> List[int]:
        """Generate random order with finisher restriction."""
        num_participants = len(participant_indices)
        
        # Shuffle using seed manager for reproducibility
        if self.seed_manager:
            self.seed_manager.random.shuffle(participant_indices)
        else:
            random.shuffle(participant_indices)
        
        # Apply finisher restriction
        if last_round_finisher is not None and num_participants > 1:
            participant_indices = self.apply_finisher_restriction(
                participant_indices, last_round_finisher, num_participants
            )
        
        return participant_indices
    
    def _generate_conversational_order(self, participant_indices: List[int],
                                      last_round_finisher: Optional[int]) -> List[int]:
        """Generate conversational order with weighted selection excluding last finisher."""
        num_participants = len(participant_indices)
        
        # Enhanced conversational order based on discussion flow
        if last_round_finisher is not None and num_participants > 2:
            # Start with someone who hasn't spoken recently
            # Create weighted selection excluding last finisher
            weights = [1.0] * num_participants
            weights[last_round_finisher] = 0.0  # Exclude last finisher from starting
            
            # Weighted random selection for first speaker
            try:
                import numpy as np
                probabilities = np.array(weights) / sum(weights)
                # Use seed manager's random for reproducible selection
                if self.seed_manager:
                    first_speaker = self.seed_manager.random.choices(participant_indices, weights=probabilities, k=1)[0]
                else:
                    first_speaker = np.random.choice(participant_indices, p=probabilities)
            except ImportError:
                # Fallback if numpy not available - manual weighted selection
                available_indices = [i for i in participant_indices if i != last_round_finisher]
                if available_indices:
                    # Use seed manager's random for reproducible selection
                    if self.seed_manager:
                        first_speaker = self.seed_manager.random.choice(available_indices)
                    else:
                        first_speaker = random.choice(available_indices)
                else:
                    first_speaker = participant_indices[0]
            
            # Remove first speaker and shuffle rest
            remaining = [i for i in participant_indices if i != first_speaker]
            if self.seed_manager:
                self.seed_manager.random.shuffle(remaining)
            else:
                random.shuffle(remaining)
            
            participant_indices = [first_speaker] + remaining
        else:
            # Fallback to random for first round or small groups
            if self.seed_manager:
                self.seed_manager.random.shuffle(participant_indices)
            else:
                random.shuffle(participant_indices)
        
        return participant_indices
    
    def apply_finisher_restriction(self, order: List[int], last_finisher: int, 
                                 num_participants: int) -> List[int]:
        """
        Apply restriction: if round N ends with Agent X, round N+1 cannot start with Agent X.
        
        Args:
            order: Current speaking order
            last_finisher: Index of participant who finished last round
            num_participants: Total number of participants
            
        Returns:
            Modified order with finisher restriction applied
        """
        # Check if last finisher is first in new order
        if order[0] == last_finisher:
            if num_participants == 2:
                # For 2 agents, just swap them
                order[0], order[1] = order[1], order[0]
            else:
                # For larger groups, find a non-adjacent position
                # Move the last finisher to middle of the list
                mid_position = num_participants // 2
                order[0], order[mid_position] = order[mid_position], order[0]
        
        return order