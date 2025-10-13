"""
Configuration models for the Frohlich Experiment.
"""
import yaml
from pathlib import Path
from typing import List, Tuple, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from models.experiment_types import IncomeClassProbabilities
from .phase2_settings import Phase2Settings


class AgentConfiguration(BaseModel):
    """Configuration for a single participant agent."""
    name: str = Field(..., description="Agent name")
    personality: str = Field(..., description="Agent personality description")
    model: str = Field("o3-mini", description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    memory_character_limit: int = Field(50000, gt=0, description="Maximum memory length in characters")
    reasoning_enabled: bool = Field(True, description="Enable/disable internal reasoning in Phase 2")
    language: str = Field("english", description="Agent's primary language (english, spanish, mandarin)")
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate language is supported."""
        valid_languages = ["english", "spanish", "mandarin", "chinese"]  # chinese as alias for mandarin
        if v.lower() not in valid_languages:
            raise ValueError(f"Unsupported language: {v}. Must be one of {valid_languages}")
        return v.lower()


class OriginalValuesModeConfig(BaseModel):
    """Configuration for original values mode."""
    enabled: bool = Field(default=False, description="Enable original values mode for Phase 1 (automatically uses Sample for explanations, cycles A-D for rounds 1-4)")


class Phase2TransparencyConfig(BaseModel):
    """Configuration for Phase 2 enhanced transparency features."""
    enabled: bool = Field(default=True, description="Enable enhanced transparency in Phase 2 (class assignments and counterfactuals)")
    detail_level: str = Field("full", description="Detail level: 'basic', 'enhanced', or 'full'")
    include_counterfactuals: bool = Field(default=True, description="Show alternative earnings under all principles")
    include_class_assignment: bool = Field(default=True, description="Show assigned income class")
    include_insights: bool = Field(default=True, description="Show best/worst alternative insights")
    
    @field_validator('detail_level')
    @classmethod
    def validate_detail_level(cls, v):
        """Validate detail level is supported."""
        valid_levels = ["basic", "enhanced", "full"]
        if v not in valid_levels:
            raise ValueError(f"Invalid detail level: {v}. Must be one of {valid_levels}")
        return v


class LoggingConfig(BaseModel):
    """Configuration for terminal output and logging."""
    verbosity_level: str = Field("standard", description="Terminal output verbosity: 'minimal', 'standard', 'detailed', 'debug'")
    use_colors: bool = Field(True, description="Enable colored terminal output")
    show_progress_bars: bool = Field(True, description="Show progress bars during execution")
    
    @field_validator('verbosity_level')
    @classmethod
    def validate_verbosity_level(cls, v):
        """Validate verbosity level is supported."""
        valid_levels = ["minimal", "standard", "detailed", "debug"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Invalid verbosity level: {v}. Must be one of {valid_levels}")
        return v.lower()


class TranscriptLoggingConfig(BaseModel):
    """Configuration for transcript logging."""
    enabled: bool = Field(default=False, description="Enable transcript logging of agent prompts")
    output_path: Optional[str] = Field(
        default=None,
        description="Custom output path for transcript (default: transcript_<experiment_id>.json)"
    )
    include_memory_updates: bool = Field(
        default=False,
        description="Include memory consolidation calls in transcript"
    )
    include_instructions: bool = Field(
        default=False,
        description="Include system instructions in transcript (WARNING: adds performance overhead due to instruction re-generation)"
    )
    include_input_prompts: bool = Field(
        default=True,
        description="Include user input prompts in transcript"
    )
    include_agent_responses: bool = Field(
        default=True,
        description=(
            "Include agent response outputs in transcript. Defaults to True for "
            "consistency with include_input_prompts. WARNING: Agent responses may "
            "contain sensitive or unexpected content."
        )
    )

    @field_validator('output_path')
    @classmethod
    def validate_output_path(cls, value: Optional[str]) -> Optional[str]:
        """Validate output path for security and usability."""
        if value is None:
            return value

        path = Path(value)
        if '..' in path.parts:
            raise ValueError("Path traversal not allowed in output_path")

        try:
            path.resolve()
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Invalid output path: {exc}") from exc

        return value


class ExperimentConfiguration(BaseModel):
    """Complete configuration for an experiment run."""
    language: str = Field("English", description="Language for experiment prompts and messages")
    agents: List[AgentConfiguration] = Field(..., min_length=2, description="Participant agents")
    utility_agent_model: str = Field("gpt-4.1-mini", description="Model for utility agents (parser/validator)")
    utility_agent_temperature: float = Field(0.0, ge=0.0, le=2.0, description="Temperature for utility agents")
    phase2_rounds: int = Field(10, gt=0, description="Maximum rounds for Phase 2 discussion")
    randomize_speaking_order: bool = Field(True, description="Enable randomized speaking order in Phase 2 discussions")
    speaking_order_strategy: str = Field("random", description="Speaking order strategy: 'random', 'fixed', or 'conversational'")
    distribution_range_phase1: Tuple[float, float] = Field((0.5, 2.0), description="Multiplier range for Phase 1 distributions")
    distribution_range_phase2: Tuple[float, float] = Field((0.5, 2.0), description="Multiplier range for Phase 2 distributions")
    income_class_probabilities: Optional[IncomeClassProbabilities] = Field(None, description="Income class assignment probabilities (defaults to equal if not specified)")
    original_values_mode: Optional[OriginalValuesModeConfig] = Field(None, description="Original values mode configuration")
    phase2_enhanced_transparency: Optional[Phase2TransparencyConfig] = Field(None, description="Phase 2 enhanced transparency configuration")
    logging: Optional[LoggingConfig] = Field(None, description="Terminal output and logging configuration")
    transcript_logging: Optional[TranscriptLoggingConfig] = Field(
        None,
        description="Transcript logging configuration"
    )
    
    # Memory optimization config options
    memory_guidance_style: str = Field("structured", description="Memory guidance style: 'narrative' or 'structured'")
    include_experiment_explanation: bool = Field(True, description="Whether to include experiment explanation in prompts")
    include_experiment_explanation_each_turn: bool = Field(False, description="Whether to include experiment explanation on every turn (default: only first turn per phase)")
    phase2_include_internal_reasoning_in_memory: bool = Field(False, description="Whether to include internal reasoning in Phase 2 memory updates")
    
    # Selective memory update optimization
    selective_memory_updates: bool = Field(True, description="Enable selective memory updates to reduce LLM calls for simple events")
    memory_update_threshold: str = Field("moderate", description="Memory update threshold: 'minimal', 'moderate', or 'comprehensive'")
    batch_simple_events: bool = Field(False, description="Batch multiple simple memory events together (future enhancement)")

    # Voting detection configuration - removed (always uses complex mode)

    # Intelligent retry mechanism configuration
    enable_intelligent_retries: bool = Field(
        True, description="Enable intelligent retry mechanism for parsing failures"
    )
    max_participant_retries: int = Field(
        2, ge=0, le=5, description="Maximum retry attempts for ranking failures (0-5 range)"
    )
    enable_progressive_guidance: bool = Field(
        True, description="Provide more specific guidance on subsequent retry attempts"
    )
    memory_update_on_retry: bool = Field(
        True, description="Update agent memory with retry experiences and feedback"
    )
    retry_feedback_detail: Literal["concise", "detailed"] = Field(
        "concise", description="Level of detail in retry feedback: 'concise' or 'detailed'"
    )

    # Reproducibility configuration
    seed: Optional[int] = Field(None, ge=0, lt=2**31, description="Random seed for experiment reproducibility (auto-generated if not specified)")

    # Manipulator configuration (Hypothesis 3)
    manipulator: Optional[dict] = Field(None, description="Manipulator agent configuration for hypothesis testing scenarios")

    # Phase 2 specific settings
    phase2_settings: Optional[Phase2Settings] = Field(None, description="Phase 2 specific configuration settings")
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        """Validate language is supported."""
        valid_languages = ["English", "Spanish", "Mandarin"]
        if v not in valid_languages:
            raise ValueError(f"Invalid language: {v}. Must be one of {valid_languages}")
        return v
    
    @field_validator('speaking_order_strategy')
    @classmethod
    def validate_speaking_order_strategy(cls, v):
        """Validate speaking order strategy is supported."""
        valid_strategies = ["random", "fixed", "conversational"]
        if v not in valid_strategies:
            raise ValueError(f"Invalid speaking order strategy: {v}. Must be one of {valid_strategies}")
        return v
    
    @field_validator('memory_guidance_style')
    @classmethod
    def validate_memory_guidance_style(cls, v):
        """Validate memory guidance style is supported."""
        valid_styles = ["narrative", "structured"]
        if v not in valid_styles:
            raise ValueError(f"Invalid memory guidance style: {v}. Must be one of {valid_styles}")
        return v
    
    @field_validator('memory_update_threshold')
    @classmethod
    def validate_memory_update_threshold(cls, v):
        """Validate memory update threshold is supported."""
        valid_thresholds = ["minimal", "moderate", "comprehensive"]
        if v not in valid_thresholds:
            raise ValueError(f"Invalid memory update threshold: {v}. Must be one of {valid_thresholds}")
        return v

    @field_validator('retry_feedback_detail')
    @classmethod
    def validate_retry_feedback_detail(cls, v):
        """Validate retry feedback detail level is supported."""
        valid_detail_levels = ["concise", "detailed"]
        if v not in valid_detail_levels:
            raise ValueError(f"Invalid retry feedback detail level: {v}. Must be one of {valid_detail_levels}")
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
    
    def get_effective_seed(self) -> int:
        """
        ALWAYS return a seed for this experiment (specified or generated).
        
        Returns:
            The seed to use - either the explicitly specified seed or 
            a deterministically generated seed from configuration parameters.
        """
        if self.seed is not None:
            return self.seed
        
        # Import here to avoid circular dependency
        from utils.seed_manager import SeedManager
        return SeedManager.generate_seed_from_config(self)

    @classmethod
    def _validate_top_level_keys(cls, config_data: dict, source: str) -> None:
        """Ensure only recognised top-level keys are provided."""
        if not isinstance(config_data, dict):
            raise ValueError(f"Configuration file {source} did not parse into a mapping.")

        allowed_keys = set(cls.model_fields.keys())
        unknown_keys = set(config_data.keys()) - allowed_keys
        if unknown_keys:
            unknown_list = ", ".join(sorted(unknown_keys))
            raise ValueError(
                f"Unknown configuration keys in {source}: {unknown_list}. "
                "Refer to config/models.py for supported fields."
            )

    @classmethod
    def _validate_agent_definitions(cls, config_data: dict, source: str) -> None:
        """Validate agent entries before Pydantic parsing for clearer errors."""
        agents = config_data.get('agents')
        if agents is None:
            raise ValueError(f"Configuration file {source} is missing required key 'agents'.")
        if not isinstance(agents, list) or not agents:
            raise ValueError(f"Configuration file {source} expects 'agents' to be a non-empty list.")

        allowed_agent_fields = set(AgentConfiguration.model_fields.keys())
        for index, agent in enumerate(agents):
            if not isinstance(agent, dict):
                raise ValueError(
                    f"Agent entry at index {index} in {source} must be a mapping of agent attributes."
                )
            unknown_agent_keys = set(agent.keys()) - allowed_agent_fields
            if unknown_agent_keys:
                unknown_list = ", ".join(sorted(unknown_agent_keys))
                agent_name = agent.get('name', f'index {index}')
                raise ValueError(
                    f"Agent '{agent_name}' in {source} contains unsupported fields: {unknown_list}."
                )
    
    @classmethod
    def from_yaml(cls, path: str) -> 'ExperimentConfiguration':
        """Load configuration from YAML file."""
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(yaml_path, 'r') as f:
            config_data = yaml.safe_load(f)

        cls._validate_top_level_keys(config_data, source=str(yaml_path))
        cls._validate_agent_definitions(config_data, source=str(yaml_path))
        
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
