"""
Golden tests for VotingService prompt generation.

These tests snapshot the localized voting prompts across supported languages and
validate that the service returns exactly what the language assets define.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from string import Formatter
from unittest.mock import Mock

from core.services.voting_service import VotingService
from config.phase2_settings import Phase2Settings
from utils.language_manager import SupportedLanguage, create_language_manager

SNAPSHOT_DIR = Path(__file__).with_suffix("").parent / "test_voting_service_prompts"


def assert_snapshot(name: str, content: str) -> None:
    path = SNAPSHOT_DIR / f"{name}.txt"
    expected = path.read_text(encoding="utf-8")
    assert content == expected


class TestVotingServicePromptGolden:
    """Golden tests covering localized prompts and system messages."""

    def setup_method(self) -> None:
        self.language_managers = {
            SupportedLanguage.ENGLISH: create_language_manager(SupportedLanguage.ENGLISH),
            SupportedLanguage.SPANISH: create_language_manager(SupportedLanguage.SPANISH),
            SupportedLanguage.MANDARIN: create_language_manager(SupportedLanguage.MANDARIN),
        }

    def create_voting_service(self, language: SupportedLanguage) -> VotingService:
        """Instantiate a voting service with the requested language manager."""
        return VotingService(
            language_manager=self.language_managers[language],
            utility_agent=Mock(),
            settings=Phase2Settings.get_default(),
            logger=Mock(),
        )

    def _service_and_manager(
        self, language: SupportedLanguage
    ) -> tuple[VotingService, Mock]:
        return self.create_voting_service(language), self.language_managers[language]

    @pytest.mark.parametrize("language", list(SupportedLanguage))
    def test_vote_initiation_prompt(self, language: SupportedLanguage):
        service = self.create_voting_service(language)
        result = service._get_localized_message("prompts.vote_initiation_prompt")
        assert_snapshot(f"test_vote_initiation_prompt__{language.name.lower()}", result)

    @pytest.mark.parametrize(
        "language,statement",
        [
            (SupportedLanguage.ENGLISH, "I believe we should adopt principle A."),
            (SupportedLanguage.SPANISH, "Creo que deberíamos adoptar el principio A."),
            (SupportedLanguage.MANDARIN, "我认为我们应该采用原则A。"),
        ],
    )
    def test_vote_initiation_with_statement_prompt(
        self, language: SupportedLanguage, statement: str
    ):
        service = self.create_voting_service(language)
        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement=statement,
        )
        assert_snapshot(
            f"test_vote_initiation_with_statement_prompt__{language.name.lower()}", result
        )

    @pytest.mark.parametrize(
        "language,initiator",
        [
            (SupportedLanguage.ENGLISH, "Alice"),
            (SupportedLanguage.SPANISH, "María"),
            (SupportedLanguage.MANDARIN, "张伟"),
        ],
    )
    def test_confirmation_request_prompt(
        self, language: SupportedLanguage, initiator: str
    ):
        service = self.create_voting_service(language)
        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiator_name=initiator,
        )
        assert_snapshot(
            f"test_confirmation_request_prompt__{language.name.lower()}", result
        )

    @pytest.mark.parametrize("language", list(SupportedLanguage))
    def test_retry_instruction_prompt(self, language: SupportedLanguage):
        service = self.create_voting_service(language)
        result = service._get_localized_message("voting_prompts.retry_instruction")
        assert_snapshot(
            f"test_retry_instruction_prompt__{language.name.lower()}", result
        )

    @pytest.mark.parametrize("language", list(SupportedLanguage))
    def test_system_messages_roundtrip(self, language: SupportedLanguage):
        service, manager = self._service_and_manager(language)
        keys = (
            "system_messages.voting.confirmation_tag",
            "system_messages.voting.all_confirmed",
            "system_messages.voting.consensus_tag",
            "system_messages.voting.no_consensus_tag",
            "system_messages.voting.error_tag",
            "system_messages.voting.process_failed",
        )
        for key in keys:
            assert service._get_localized_message(key) == manager.get(key)

    @pytest.mark.parametrize(
        "language,principle,constraint",
        [
            (SupportedLanguage.ENGLISH, "Maximizing Floor", 5000),
            (SupportedLanguage.SPANISH, "Maximizar Piso", 7500),
            (SupportedLanguage.MANDARIN, "最大化最低收入", 6000),
        ],
    )
    def test_voting_results_roundtrip(
        self, language: SupportedLanguage, principle: str, constraint: int
    ):
        service, manager = self._service_and_manager(language)

        consensus = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name=principle,
        )
        expected_consensus = manager.get("voting_results.consensus_reached").format(
            principle_name=principle
        )
        assert consensus == expected_consensus

        consensus_with_constraint = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name=principle,
            constraint_amount=constraint,
        )
        expected_constraint = manager.get("voting_results.consensus_with_constraint").format(
            principle_name=principle,
            constraint_amount=constraint,
        )
        assert consensus_with_constraint == expected_constraint

        no_consensus = service._get_localized_message("voting_results.no_consensus")
        assert no_consensus == manager.get("voting_results.no_consensus")

    @pytest.mark.parametrize(
        "language,participants",
        [
            (SupportedLanguage.ENGLISH, "Alice, Bob"),
            (SupportedLanguage.SPANISH, "Carlos, María"),
            (SupportedLanguage.MANDARIN, "张伟, 李华"),
        ],
    )
    def test_declined_participants_prompt(
        self, language: SupportedLanguage, participants: str
    ):
        service = self.create_voting_service(language)
        result = service._get_localized_message(
            "system_messages.voting.voting_declined",
            declined_participants=participants,
        )
        assert_snapshot(
            f"test_declined_participants_prompt__{language.name.lower()}", result
        )

    def test_missing_translation_fallback(self):
        service, _ = self._service_and_manager(SupportedLanguage.ENGLISH)
        missing = service._get_localized_message("system_messages.voting.undefined_key")
        assert missing == "[MISSING: system_messages.voting.undefined_key]"

    def test_prompt_parameter_placeholders(self):
        formatter = Formatter()
        test_cases = [
            ("prompts.vote_initiation_with_statement_prompt", {"agent_recent_statement": "example"}),
            ("prompts.utility_voting_confirmation_request", {"initiator_name": "Alice"}),
            ("voting_results.consensus_reached", {"principle_name": "Maximizing Floor"}),
            (
                "voting_results.consensus_with_constraint",
                {"principle_name": "Maximizing Average", "constraint_amount": 1000},
            ),
            ("system_messages.voting.voting_declined", {"declined_participants": "Alice, Bob"}),
        ]

        for language in SupportedLanguage:
            manager = self.language_managers[language]
            service = self.create_voting_service(language)
            for key, params in test_cases:
                template = manager.get(key)
                placeholders = {
                    field_name
                    for _, field_name, _, _ in formatter.parse(template)
                    if field_name
                }
                expected_placeholders = set(params.keys())
                assert (
                    placeholders == expected_placeholders
                ), f"Placeholder mismatch for {key} in {language.name}"
                result = service._get_localized_message(key, **params)
                assert "[MISSING:" not in result
