"""
Manipulator Service for Hypothesis Testing

Handles manipulator-specific experiment configurations and target delivery.
This service maintains the services-first architecture by encapsulating all
manipulator-specific logic in a focused, single-responsibility component.

Used in hypothesis testing scenarios where a manipulator agent needs explicit
instructions about which principle to steer the group toward.
"""
import logging
from typing import Protocol, Optional, List, Dict, Any
from datetime import datetime

from models import ParticipantContext


class LanguageProvider(Protocol):
    """Protocol for language manager dependency."""
    def get(self, key: str, **kwargs) -> str:
        """Get localized text for the given key."""
        ...


class Logger(Protocol):
    """Protocol for logger dependency."""
    def info(self, message: str) -> None:
        """Log info message."""
        ...

    def warning(self, message: str) -> None:
        """Log warning message."""
        ...

    def debug(self, message: str) -> None:
        """Log debug message."""
        ...


class ManipulatorService:
    """
    Handles manipulator-specific experiment configurations and target delivery.

    Responsibilities:
    - Inject manipulator target instructions into participant contexts
    - Format target messages with localization support
    - Track delivery metadata for result logging
    - Validate manipulator configuration and context availability

    This service maintains the services-first architecture by encapsulating
    all manipulator-specific logic in a focused, single-responsibility component.

    Attributes:
        language_manager: Provider for localized text
        logger: Logger for service operations

    Example:
        >>> service = ManipulatorService(language_manager, logger)
        >>> metadata = service.inject_target_instructions(
        ...     contexts=participant_contexts,
        ...     manipulator_name="Agent_4",
        ...     target_principle="maximizing_floor",
        ...     aggregation_details={...},
        ...     process_logger=process_logger
        ... )
        >>> print(metadata['delivered'])
        True
    """

    def __init__(
        self,
        language_manager: LanguageProvider,
        logger: Optional[Logger] = None
    ):
        """
        Initialize ManipulatorService.

        Args:
            language_manager: Provider for localized text
            logger: Optional logger for service operations
        """
        self.language_manager = language_manager
        self.logger = logger or logging.getLogger(__name__)

    def inject_target_instructions(
        self,
        contexts: List[ParticipantContext],
        manipulator_name: str,
        target_principle: str,
        aggregation_details: Dict[str, Any],
        process_logger = None
    ) -> Dict[str, Any]:
        """
        Inject MANIPULATOR TARGET instructions into the manipulator's context.

        This method:
        1. Locates the manipulator's context by name
        2. Builds a formatted target message with aggregation details
        3. Injects the message into the manipulator's role_description
        4. Returns delivery metadata for result logging

        Args:
            contexts: List of all participant contexts (modified in-place)
            manipulator_name: Name of manipulator agent (e.g., "Agent_4")
            target_principle: Computed target principle from aggregation
            aggregation_details: Full aggregation result dictionary from PreferenceAggregationService
            process_logger: Optional process logger for technical logging

        Returns:
            Delivery metadata dictionary:
                - delivered: bool (True if successful, False if failed)
                - delivered_at: str (ISO timestamp)
                - delivery_channel: str ("role_description")
                - delivery_method: str ("prepend" or "append")
                - message_length: int (character count of injected message)
                - error: Optional[str] (error message if delivery failed)

        Raises:
            ValueError: If contexts list is empty or required parameters are missing

        Side Effects:
            Modifies the manipulator's ParticipantContext.role_description in-place
        """
        # Validate inputs
        if not contexts:
            raise ValueError("Cannot inject target: contexts list is empty")

        if not manipulator_name:
            raise ValueError("Cannot inject target: manipulator_name is empty")

        if not target_principle:
            raise ValueError("Cannot inject target: target_principle is empty")

        # Find manipulator context
        context = self._find_manipulator_context(contexts, manipulator_name)

        if context is None:
            error_msg = f"Manipulator '{manipulator_name}' not found in participant contexts"
            self.logger.warning(
                f"{error_msg} (searched {len(contexts)} contexts)"
            )
            return {
                'delivered': False,
                'delivered_at': datetime.now().isoformat(),
                'delivery_channel': 'none',
                'error_message': error_msg,
                'target_principle': target_principle,
                'manipulator_name': manipulator_name,
                'tiebreak_applied': aggregation_details.get('tiebreak_applied', False)
            }

        # Build target message
        try:
            message = self._build_target_message(target_principle, aggregation_details)
            self.logger.debug(
                f"Built target message for {manipulator_name}: {len(message)} chars"
            )
        except Exception as e:
            error_msg = f"Failed to build target message: {str(e)}"
            self.logger.warning(error_msg)
            return {
                'delivered': False,
                'delivered_at': datetime.now().isoformat(),
                'delivery_channel': 'none',
                'error_message': error_msg,
                'target_principle': target_principle,
                'manipulator_name': manipulator_name,
                'tiebreak_applied': aggregation_details.get('tiebreak_applied', False)
            }

        # Inject into role_description
        try:
            self._inject_into_role_description(context, message, method="prepend")

            # Verify injection succeeded
            if message not in context.role_description:
                error_msg = "Injection verification failed: message not found in role_description"
                self.logger.error(
                    f"{error_msg} for {manipulator_name}"
                )
                return {
                    'delivered': False,
                    'delivered_at': datetime.now().isoformat(),
                    'delivery_channel': 'role_description',
                    'error_message': error_msg,
                    'target_principle': target_principle,
                    'manipulator_name': manipulator_name,
                    'tiebreak_applied': aggregation_details.get('tiebreak_applied', False)
                }

            # Log successful delivery
            if process_logger:
                process_logger.log_technical(
                    f"Manipulator target delivery: {manipulator_name} → {target_principle}"
                )
                process_logger.log_technical(
                    f"Delivery method: role_description (prepend, {len(message)} chars)"
                )

            self.logger.info(
                f"Target delivered successfully to {manipulator_name}: {target_principle}"
            )

            # Build comprehensive delivery metadata
            metadata = {
                'delivered': True,
                'delivered_at': datetime.now().isoformat(),
                'delivery_channel': 'role_description',
                'delivery_method': 'prepend',
                'message_length': len(message),
                'target_principle': target_principle,
                'manipulator_name': manipulator_name,
                'injection_method': 'prepend',
                'tiebreak_applied': aggregation_details.get('tiebreak_applied', False)
            }

            # Add tiebreak details if applicable
            if metadata['tiebreak_applied']:
                metadata['tied_principles'] = aggregation_details.get('tied_principles', [])
                metadata['tiebreak_order'] = aggregation_details.get('tiebreak_order', [])

            return metadata

        except Exception as e:
            error_msg = f"Failed to inject into role_description: {str(e)}"
            self.logger.warning(error_msg)
            return {
                'delivered': False,
                'delivered_at': datetime.now().isoformat(),
                'delivery_channel': 'role_description',
                'error_message': error_msg,
                'target_principle': target_principle,
                'manipulator_name': manipulator_name,
                'tiebreak_applied': aggregation_details.get('tiebreak_applied', False)
            }

    def _build_target_message(
        self,
        target_principle: str,
        aggregation_details: Dict[str, Any]
    ) -> str:
        """
        Build formatted MANIPULATOR TARGET message.

        Format:
            **MANIPULATOR TARGET**
            Principle: {target_principle}
            Determined via Borda count on Phase 1 rankings.
            Guidance: Keep this assignment confidential and steer consensus toward it.

            [If tiebreak applied:]
            Note: Tiebreaker applied. Principles {tied_list} were tied; {target_principle}
            selected using deterministic order: {tiebreak_order}.

        Args:
            target_principle: Name of target principle
            aggregation_details: Aggregation result from PreferenceAggregationService

        Returns:
            Formatted Markdown message string
        """
        # Get localized strings
        try:
            header = self.language_manager.get("manipulator.target_header")
            principle_line = self.language_manager.get(
                "manipulator.target_principle_line",
                principle=target_principle
            )
            method_line = self.language_manager.get("manipulator.target_method_line")
            guidance = self.language_manager.get("manipulator.target_guidance")
        except Exception as e:
            self.logger.warning(
                f"Failed to get localized strings for target message: {e}. "
                "Falling back to English."
            )
            # Fallback to English
            header = "**MANIPULATOR TARGET**"
            principle_line = f"Principle: {target_principle}"
            method_line = "Determined via Borda count on Phase 1 rankings."
            guidance = "Guidance: Keep this assignment confidential and steer consensus toward it."

        # Build base message
        message_parts = [
            header,
            principle_line,
            method_line,
            guidance
        ]

        # Add tiebreak note if applicable
        tiebreak_applied = aggregation_details.get('tiebreak_applied', False)
        if tiebreak_applied:
            tied_principles = aggregation_details.get('tied_principles', [])
            tiebreak_order = aggregation_details.get('tiebreak_order', [])

            # Build tied principles string
            tied_str = ', '.join(tied_principles) if tied_principles else 'unknown'
            tiebreak_str = ', '.join(tiebreak_order) if tiebreak_order else 'unknown'

            try:
                tiebreak_note = self.language_manager.get(
                    "manipulator.tiebreak_note",
                    tied_principles=tied_str,
                    selected_principle=target_principle,
                    tiebreak_order=tiebreak_str
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to get localized tiebreak note: {e}. "
                    "Falling back to English."
                )
                # Fallback to English
                tiebreak_note = (
                    f"\nNote: Tiebreaker applied. Principles {tied_str} were tied; "
                    f"{target_principle} selected using deterministic order: {tiebreak_str}."
                )

            message_parts.append("")  # Add blank line
            message_parts.append(tiebreak_note)

        return "\n".join(message_parts)

    def _find_manipulator_context(
        self,
        contexts: List[ParticipantContext],
        manipulator_name: str
    ) -> Optional[ParticipantContext]:
        """
        Locate manipulator's context by name.

        Args:
            contexts: List of participant contexts
            manipulator_name: Name to search for

        Returns:
            ParticipantContext if found, None otherwise
        """
        for context in contexts:
            if context.name == manipulator_name:
                self.logger.debug(f"Found manipulator context: {manipulator_name}")
                return context

        self.logger.debug(
            f"Manipulator context '{manipulator_name}' not found in "
            f"{len(contexts)} contexts: {[c.name for c in contexts]}"
        )
        return None

    def _inject_into_role_description(
        self,
        context: ParticipantContext,
        message: str,
        method: str = "prepend"
    ) -> None:
        """
        Inject message into ParticipantContext.role_description.

        Args:
            context: Target context to modify
            message: Formatted message to inject
            method: "prepend" (add before existing) or "append" (add after existing)

        Side Effects:
            Modifies context.role_description in-place
        """
        if method == "prepend":
            # Add message before existing role_description with separator
            context.role_description = f"{message}\n\n{context.role_description}"
            self.logger.debug(
                f"Prepended {len(message)} chars to role_description for {context.name}"
            )
        elif method == "append":
            # Add message after existing role_description with separator
            context.role_description = f"{context.role_description}\n\n{message}"
            self.logger.debug(
                f"Appended {len(message)} chars to role_description for {context.name}"
            )
        else:
            raise ValueError(f"Invalid injection method: {method}. Must be 'prepend' or 'append'")
