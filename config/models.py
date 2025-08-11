"""
Configuration models for the Frohlich Experiment.
"""
import yaml
from pathlib import Path
from typing import List, Tuple
from pydantic import BaseModel, Field, field_validator


class AgentConfiguration(BaseModel):
    """Configuration for a single participant agent."""
    name: str = Field(..., description="Agent name")
    personality: str = Field(..., description="Agent personality description")
    model: str = Field("o3-mini", description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    memory_character_limit: int = Field(50000, gt=0, description="Maximum memory length in characters")
    reasoning_enabled: bool = Field(True, description="Enable/disable internal reasoning in Phase 2")


class ExperimentConfiguration(BaseModel):
    """Complete configuration for an experiment run."""
    language: str = Field("English", description="Language for experiment prompts and messages")
    agents: List[AgentConfiguration] = Field(..., min_items=2, description="Participant agents")
    utility_agent_model: str = Field("gpt-4.1-mini", description="Model for utility agents (parser/validator)")
    phase2_rounds: int = Field(10, gt=0, description="Maximum rounds for Phase 2 discussion")
    distribution_range_phase1: Tuple[float, float] = Field((0.5, 2.0), description="Multiplier range for Phase 1 distributions")
    distribution_range_phase2: Tuple[float, float] = Field((0.5, 2.0), description="Multiplier range for Phase 2 distributions")
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate language is supported."""
        valid_languages = ["English", "Spanish", "Mandarin"]
        if v not in valid_languages:
            raise ValueError(f"Invalid language: {v}. Must be one of {valid_languages}")
        return v
    
    @field_validator('distribution_range_phase1', 'distribution_range_phase2')
    @classmethod
    def validate_distribution_range(cls, v):
        """Validate distribution range is positive and properly ordered."""
        if len(v) != 2:
            raise ValueError("Distribution range must be a tuple of (min, max)")
        min_val, max_val = v
        if min_val <= 0 or max_val <= 0:
            raise ValueError("Distribution range values must be positive")
        if min_val >= max_val:
            raise ValueError("Distribution range min must be less than max")
        return v
    
    @field_validator('agents')
    @classmethod
    def validate_unique_agent_names(cls, v):
        """Ensure all agent names are unique."""
        names = [agent.name for agent in v]
        if len(names) != len(set(names)):
            raise ValueError("Agent names must be unique")
        return v
    
    @classmethod
    def from_yaml(cls, path: str) -> 'ExperimentConfiguration':
        """Load configuration from YAML file."""
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(yaml_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        yaml_path = Path(path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and handle tuples for YAML serialization
        config_dict = self.model_dump()
        
        # Convert tuples to lists for YAML compatibility
        if 'distribution_range_phase1' in config_dict:
            config_dict['distribution_range_phase1'] = list(config_dict['distribution_range_phase1'])
        if 'distribution_range_phase2' in config_dict:
            config_dict['distribution_range_phase2'] = list(config_dict['distribution_range_phase2'])
        
        with open(yaml_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)