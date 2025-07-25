"""
Response types for structured agent outputs.
"""
from pydantic import BaseModel, Field
from typing import Optional
from .principle_types import PrincipleChoice, PrincipleRanking, JusticePrinciple, CertaintyLevel


class PrincipleRankingResponse(BaseModel):
    """Response format for principle ranking requests."""
    ranking_explanation: str = Field(..., description="Participant's explanation of their ranking")
    principle_rankings: PrincipleRanking


class PrincipleChoiceResponse(BaseModel):
    """Response format for principle choice requests."""
    choice_explanation: str = Field(..., description="Participant's reasoning for their choice")
    principle_choice: PrincipleChoice


class GroupStatementResponse(BaseModel):
    """Response format for group discussion statements."""
    internal_reasoning: Optional[str] = Field(None, description="Internal reasoning (not shared with group)")
    public_statement: str = Field(..., description="Statement to share with the group")
    vote_proposal: Optional[str] = Field(None, description="If proposing a vote, the proposal text")


class VotingResponse(BaseModel):
    """Response format for voting requests."""
    vote_reasoning: Optional[str] = Field(None, description="Internal reasoning for vote")
    vote_choice: PrincipleChoice


class ParsedResponse(BaseModel):
    """Generic parsed response from utility agent."""
    success: bool
    parsed_data: Optional[dict] = None
    error_message: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of response validation."""
    is_valid: bool
    validation_errors: list = Field(default_factory=list)
    corrected_data: Optional[dict] = None


class ParticipantResponse(BaseModel):
    """Generic participant response that can be one of several types."""
    response_type: str
    content: str
    structured_data: Optional[dict] = None