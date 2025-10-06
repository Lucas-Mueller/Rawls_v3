"""
Error classification system for statement validation failures in the Frohlich Experiment.

This module provides intelligent error categorization for statement validation failures,
enabling targeted retry strategies and improved discussion quality. The classification
system identifies common validation failure patterns and supports the intelligent
retry mechanism for Phase 2 discussions.

The error types are designed based on analysis of real validation failures and
support multilingual experiments with targeted feedback generation.
"""

from enum import Enum


class StatementValidationFailureType(Enum):
    """
    Classification of statement validation failure types for intelligent retry strategies.

    Each type represents a distinct category of validation failure that can be
    addressed with specific feedback and retry approaches in Phase 2 discussions.
    """

    TOO_SHORT = "too_short"
    """
    Statement below minimum length threshold for meaningful discussion.
    Common when agents provide brief responses without sufficient detail.
    Retry strategy: Encourage detailed reasoning and explanation.
    """

    EMPTY_RESPONSE = "empty_response"
    """
    Empty or whitespace-only statement provided by agent.
    Occurs when agents fail to provide any substantive response.
    Retry strategy: Request thoughts, analysis, or preferences on discussion topic.
    """

    MINIMAL_CONTENT = "minimal_content"
    """
    Brief agreement without substantive reasoning or analysis.
    Statement meets length requirements but lacks depth for meaningful discussion.
    Retry strategy: Request explanation of reasoning and additional perspective.
    """