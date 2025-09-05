"""
Configuration settings for Phase 2 behavior and validation.
"""
from pydantic import BaseModel, Field


class Phase2Settings(BaseModel):
    """Configurable settings for Phase 2 execution."""
    
    # Statement validation settings
    min_statement_length: int = Field(
        default=10,
        ge=1,
        description="Minimum character length for valid statements"
    )
    min_statement_length_cjk: int = Field(
        default=5,
        ge=1,
        description="Minimum character length for CJK languages (Chinese, Japanese, Korean)"
    )
    
    # Retry settings
    max_statement_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for invalid statements"
    )
    max_memory_retries: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum retry attempts for memory updates"
    )
    retry_backoff_factor: float = Field(
        default=1.5,
        ge=1.0,
        le=3.0,
        description="Exponential backoff factor for retries"
    )
    
    # Timeout settings
    statement_timeout_seconds: int = Field(
        default=600,
        ge=10,
        le=600,
        description="Timeout for agent statement responses"
    )
    confirmation_timeout_seconds: int = Field(
        default=600,
        ge=10,
        le=600,
        description="Timeout for voting confirmation responses"
    )
    ballot_timeout_seconds: int = Field(
        default=600,
        ge=10,
        le=600,
        description="Timeout for secret ballot responses"
    )
    
    # Reasoning system settings
    reasoning_enabled: bool = Field(
        default=True,
        description="Enable two-step reasoning (internal reasoning + public statement)"
    )
    reasoning_timeout_seconds: int = Field(
        default=600,
        ge=10,
        le=600,
        description="Timeout for internal reasoning calls"
    )
    reasoning_max_retries: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum retry attempts for reasoning calls"
    )
    
    # Memory settings
    memory_compression_threshold: float = Field(
        default=0.9,
        ge=0.5,
        le=0.95,
        description="Threshold for memory compression (percentage of limit)"
    )
    memory_validation_strict: bool = Field(
        default=True,
        description="Strict validation of memory integrity"
    )
    
    # Consensus settings
    constraint_tolerance: int = Field(
        default=0,
        ge=0,
        description="Tolerance for constraint amount matching (0 = exact match)"
    )
    
    # Public history settings
    public_history_max_length: int = Field(
        default=50000,
        ge=10000,
        description="Maximum length of public history before compression"
    )
    quarantine_failed_responses: bool = Field(
        default=True,
        description="Quarantine failed agent responses from public history"
    )
    
    # Agent group settings
    min_agents_for_experiment: int = Field(
        default=2,
        ge=2,
        description="Minimum number of agents required for valid experiment"
    )
    
    # Constraint correction settings
    constraint_correction_enabled: bool = Field(
        default=True,
        description="Enable constraint correction for principles C and D"
    )
    constraint_correction_timeout_seconds: int = Field(
        default=600,
        ge=10,
        le=600,
        description="Timeout for constraint correction attempts"
    )
    max_constraint_correction_attempts: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum attempts for constraint correction"
    )
    
    # Two-stage voting settings
    two_stage_voting_enabled: bool = Field(
        default=True,
        description="Enable two-stage structured voting"
    )
    
    two_stage_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts per voting stage"
    )
    two_stage_timeout_seconds: float = Field(
        default=600.0,
        ge=10.0,
        le=600.0,
        description="Timeout for each voting stage"
    )
    
    # Amount validation settings
    amount_range_validation: bool = Field(
        default=True,
        description="Enable reasonable amount range validation"
    )
    amount_min_reasonable: int = Field(
        default=1000,
        ge=1,
        description="Minimum reasonable constraint amount"
    )
    amount_max_reasonable: int = Field(
        default=10000000,
        ge=100,
        description="Maximum reasonable constraint amount"
    )
    
    # Vote initiation settings (formal voting only)
    prompt_based_voting: bool = Field(
        default=True,
        description="Use prompt-based voting initiation (only supported method)"
    )
    
    # Logging settings
    log_statement_preview_length: int = Field(
        default=100,
        ge=50,
        le=500,
        description="Length of statement preview in logs"
    )
    
    @classmethod
    def get_default(cls) -> "Phase2Settings":
        """Get default Phase 2 settings."""
        return cls()
    
    def is_cjk_language(self, language: str) -> bool:
        """Check if language uses CJK characters."""
        cjk_languages = {"Mandarin", "Chinese", "Japanese", "Korean"}
        return language in cjk_languages
    
    def get_min_statement_length(self, language: str) -> int:
        """Get minimum statement length based on language."""
        if self.is_cjk_language(language):
            return self.min_statement_length_cjk
        return self.min_statement_length