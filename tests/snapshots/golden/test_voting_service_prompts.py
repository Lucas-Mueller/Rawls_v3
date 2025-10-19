"""
Golden tests for VotingService prompt generation.

These tests create snapshots of voting prompt content across different languages
to detect unintentional changes during refactoring. They help ensure that
the VotingService produces identical prompts to the original Phase2Manager.
"""

import pytest
import asyncio
from string import Formatter
from unittest.mock import Mock, patch
from core.services.voting_service import VotingService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState, ParticipantContext


class TestVotingServicePromptGolden:
    """Golden tests for VotingService prompt generation across languages."""
    
    def setup_method(self):
        """Set up test fixtures with realistic translations."""
        # English translations
        self.english_translations = {
            "prompts.vote_initiation_prompt": (
                "Do you want to initiate formal voting to reach a consensus on the justice principle? "
                "Respond with 1 for Yes or 0 for No."
            ),
            "prompts.vote_initiation_with_statement_prompt": (
                "Based on your recent statement: '{agent_recent_statement}'\n\n"
                "Do you want to initiate formal voting to reach a consensus on the justice principle? "
                "Respond with 1 for Yes or 0 for No."
            ),
            "prompts.utility_voting_confirmation_request": (
                "{initiator_name} has requested to vote on the justice principles.\n\n"
                "Do you agree to participate in a voting session now?\n\n"
                "Respond with exactly one number:\n"
                "- Reply 1 if you want to vote now\n"
                "- Reply 0 if you want to continue discussion\n\n"
                "Your response will be visible to all participants."
            ),
            "voting_prompts.retry_instruction": (
                "Please provide a clear response: 1 for Yes (initiate voting) or 0 for No (continue discussion)."
            ),
            "system_messages.voting.confirmation_tag": "[CONFIRMATION]",
            "system_messages.voting.all_confirmed": "All participants confirmed - proceeding to secret ballot phase.",
            "system_messages.voting.voting_declined": "Voting declined by: {declined_participants} - returning to discussion.",
            "system_messages.voting.consensus_tag": "[CONSENSUS]",
            "system_messages.voting.no_consensus_tag": "[NO CONSENSUS]",
            "system_messages.voting.error_tag": "[VOTING ERROR]",
            "system_messages.voting.process_failed": "Voting process failed - returning to discussion.",
            "voting_results.consensus_reached": "Consensus reached on: {principle_name}",
            "voting_results.consensus_with_constraint": "Consensus reached on: {principle_name} with constraint amount: {constraint_amount}",
            "voting_results.no_consensus": "No consensus reached - returning to discussion.",
            "principle_names.maximizing_floor": "Maximizing Floor",
            "principle_names.maximizing_average": "Maximizing Average"
        }
        
        # Spanish translations
        self.spanish_translations = {
            "prompts.vote_initiation_prompt": (
                "¿Desea iniciar una votación formal para alcanzar consenso sobre el principio de justicia? "
                "Responda con 1 para Sí o 0 para No."
            ),
            "prompts.vote_initiation_with_statement_prompt": (
                "Basado en su declaración reciente: '{agent_recent_statement}'\n\n"
                "¿Desea iniciar una votación formal para alcanzar consenso sobre el principio de justicia? "
                "Responda con 1 para Sí o 0 para No."
            ),
            "prompts.utility_voting_confirmation_request": (
                "{initiator_name} ha solicitado votar sobre los principios de justicia.\n\n"
                "¿Está de acuerdo en participar en una sesión de votación ahora?\n\n"
                "Responda con exactamente un número:\n"
                "- Responda 1 si quiere votar ahora\n"
                "- Responda 0 si quiere continuar la discusión\n\n"
                "Su respuesta será visible para todos los participantes."
            ),
            "voting_prompts.retry_instruction": (
                "Por favor proporcione una respuesta clara: 1 para Sí (iniciar votación) o 0 para No (continuar discusión)."
            ),
            "system_messages.voting.confirmation_tag": "[CONFIRMACIÓN]",
            "system_messages.voting.all_confirmed": "Todos los participantes confirmaron - procediendo a votación secreta.",
            "system_messages.voting.voting_declined": "Votación rechazada por: {declined_participants} - regresando a discusión.",
            "system_messages.voting.consensus_tag": "[CONSENSO]",
            "system_messages.voting.no_consensus_tag": "[SIN CONSENSO]",
            "system_messages.voting.error_tag": "[ERROR DE VOTACIÓN]",
            "system_messages.voting.process_failed": "Proceso de votación falló - regresando a discusión.",
            "voting_results.consensus_reached": "Consenso alcanzado en: {principle_name}",
            "voting_results.consensus_with_constraint": "Consenso alcanzado en: {principle_name} con restricción: {constraint_amount}",
            "voting_results.no_consensus": "No se alcanzó consenso - regresando a discusión.",
            "principle_names.maximizing_floor": "Maximizar Piso",
            "principle_names.maximizing_average": "Maximizar Promedio"
        }
        
        # Chinese translations
        self.chinese_translations = {
            "prompts.vote_initiation_prompt": (
                "您是否想要发起正式投票以就正义原则达成共识？"
                "请回答1表示是，0表示否。"
            ),
            "prompts.vote_initiation_with_statement_prompt": (
                "基于您最近的声明：'{agent_recent_statement}'\n\n"
                "您是否想要发起正式投票以就正义原则达成共识？"
                "请回答1表示是，0表示否。"
            ),
            "prompts.utility_voting_confirmation_request": (
                "{initiator_name} 请求对公正原则进行投票。\n\n"
                "现在请确认你的选择：\n"
                "- 回答 1：是的，我确认开始正式投票\n"
                "- 回答 0：不，我需要更多讨论时间\n\n"
                "请只回答数字：1 或 0\n"
                "你的回答将对所有参与者可见。"
            ),
            "voting_prompts.retry_instruction": (
                "请提供明确回答：1表示是（发起投票）或0表示否（继续讨论）。"
            ),
            "system_messages.voting.confirmation_tag": "[确认]",
            "system_messages.voting.all_confirmed": "所有参与者已确认 - 进入秘密投票阶段。",
            "system_messages.voting.voting_declined": "投票被拒绝，拒绝者：{declined_participants} - 返回讨论。",
            "system_messages.voting.consensus_tag": "[共识]",
            "system_messages.voting.no_consensus_tag": "[无共识]",
            "system_messages.voting.error_tag": "[投票错误]",
            "system_messages.voting.process_failed": "投票过程失败 - 返回讨论。",
            "voting_results.consensus_reached": "在以下方面达成共识：{principle_name}",
            "voting_results.consensus_with_constraint": "在以下方面达成共识：{principle_name}，约束金额：{constraint_amount}",
            "voting_results.no_consensus": "未达成共识 - 返回讨论。",
            "principle_names.maximizing_floor": "最大化最低收入",
            "principle_names.maximizing_average": "最大化平均收入"
        }
    
    def create_mock_language_manager(self, translations):
        """Create a mock language manager with given translations."""
        manager = Mock()
        manager.get.side_effect = lambda key, **kwargs: translations.get(key, f"[MISSING: {key}]").format(**kwargs)
        return manager
    
    def create_voting_service(self, translations):
        """Create a VotingService with mock language manager."""
        language_manager = self.create_mock_language_manager(translations)
        utility_agent = Mock()
        settings = Phase2Settings.get_default()
        logger = Mock()
        
        return VotingService(
            language_manager=language_manager,
            utility_agent=utility_agent,
            settings=settings,
            logger=logger
        )
    
    def create_mock_participant(self, name):
        """Create a mock participant with given name."""
        participant = Mock()
        participant.name = name
        participant.agent = Mock()
        return participant
    
    def create_mock_context(self, name):
        """Create a mock context with given name."""
        context = Mock()
        context.name = name
        context.interaction_type = "discussion"
        return context
    
    def test_english_vote_initiation_prompt_golden(self, text_regression):
        """Golden test for English vote initiation prompt."""
        service = self.create_voting_service(self.english_translations)

        # Test basic prompt
        result = service._get_localized_message("prompts.vote_initiation_prompt")
        text_regression.check(result)

    def test_english_vote_initiation_with_statement_golden(self, text_regression):
        """Golden test for English vote initiation prompt with statement context."""
        service = self.create_voting_service(self.english_translations)

        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement="I believe we should adopt principle A"
        )
        text_regression.check(result)

    def test_spanish_vote_initiation_prompt_golden(self, text_regression):
        """Golden test for Spanish vote initiation prompt."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message("prompts.vote_initiation_prompt")
        text_regression.check(result)

    def test_spanish_vote_initiation_with_statement_golden(self, text_regression):
        """Golden test for Spanish vote initiation prompt with statement context."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement="Creo que deberíamos adoptar el principio A"
        )
        text_regression.check(result)
    
    def test_chinese_vote_initiation_prompt_golden(self, text_regression):
        """Golden test for Chinese vote initiation prompt."""
        service = self.create_voting_service(self.chinese_translations)
        
        result = service._get_localized_message("prompts.vote_initiation_prompt")
        text_regression.check(result)

    def test_chinese_vote_initiation_with_statement_golden(self, text_regression):
        """Golden test for Chinese vote initiation prompt with statement context."""
        service = self.create_voting_service(self.chinese_translations)
        
        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement="我认为我们应该采用原则A"
        )
        text_regression.check(result)
    
    def test_english_confirmation_request_golden(self, text_regression):
        """Golden test for English confirmation request prompt."""
        service = self.create_voting_service(self.english_translations)

        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiator_name="Sophie"
        )
        text_regression.check(result)

    def test_spanish_confirmation_request_golden(self, text_regression):
        """Golden test for Spanish confirmation request prompt."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiator_name="María"
        )
        text_regression.check(result)

    def test_chinese_confirmation_request_golden(self, text_regression):
        """Golden test for Chinese confirmation request prompt."""
        service = self.create_voting_service(self.chinese_translations)
        
        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiator_name="苏菲"
        )
        text_regression.check(result)

    def test_english_retry_instruction_golden(self, text_regression):
        """Golden test for English retry instruction."""
        service = self.create_voting_service(self.english_translations)
        
        result = service._get_localized_message("voting_prompts.retry_instruction")
        text_regression.check(result)

    def test_spanish_retry_instruction_golden(self, text_regression):
        """Golden test for Spanish retry instruction."""
        service = self.create_voting_service(self.spanish_translations)
        
        result = service._get_localized_message("voting_prompts.retry_instruction")
        text_regression.check(result)

    def test_chinese_retry_instruction_golden(self, text_regression):
        """Golden test for Chinese retry instruction."""
        service = self.create_voting_service(self.chinese_translations)
        
        result = service._get_localized_message("voting_prompts.retry_instruction")
        text_regression.check(result)
    
    def test_english_system_messages_golden(self):
        """Golden test for English system messages."""
        service = self.create_voting_service(self.english_translations)
        
        # Test various system messages
        assert service._get_localized_message("system_messages.voting.confirmation_tag") == "[CONFIRMATION]"
        assert service._get_localized_message("system_messages.voting.all_confirmed") == "All participants confirmed - proceeding to secret ballot phase."
        assert service._get_localized_message("system_messages.voting.consensus_tag") == "[CONSENSUS]"
        assert service._get_localized_message("system_messages.voting.no_consensus_tag") == "[NO CONSENSUS]"
        assert service._get_localized_message("system_messages.voting.error_tag") == "[VOTING ERROR]"
        assert service._get_localized_message("system_messages.voting.process_failed") == "Voting process failed - returning to discussion."
    
    def test_spanish_system_messages_golden(self):
        """Golden test for Spanish system messages."""
        service = self.create_voting_service(self.spanish_translations)
        
        # Test various system messages
        assert service._get_localized_message("system_messages.voting.confirmation_tag") == "[CONFIRMACIÓN]"
        assert service._get_localized_message("system_messages.voting.all_confirmed") == "Todos los participantes confirmaron - procediendo a votación secreta."
        assert service._get_localized_message("system_messages.voting.consensus_tag") == "[CONSENSO]"
        assert service._get_localized_message("system_messages.voting.no_consensus_tag") == "[SIN CONSENSO]"
        assert service._get_localized_message("system_messages.voting.error_tag") == "[ERROR DE VOTACIÓN]"
        assert service._get_localized_message("system_messages.voting.process_failed") == "Proceso de votación falló - regresando a discusión."
    
    def test_chinese_system_messages_golden(self):
        """Golden test for Chinese system messages."""
        service = self.create_voting_service(self.chinese_translations)
        
        # Test various system messages
        assert service._get_localized_message("system_messages.voting.confirmation_tag") == "[确认]"
        assert service._get_localized_message("system_messages.voting.all_confirmed") == "所有参与者已确认 - 进入秘密投票阶段。"
        assert service._get_localized_message("system_messages.voting.consensus_tag") == "[共识]"
        assert service._get_localized_message("system_messages.voting.no_consensus_tag") == "[无共识]"
        assert service._get_localized_message("system_messages.voting.error_tag") == "[投票错误]"
        assert service._get_localized_message("system_messages.voting.process_failed") == "投票过程失败 - 返回讨论。"
    
    def test_english_voting_results_golden(self):
        """Golden test for English voting result messages."""
        service = self.create_voting_service(self.english_translations)
        
        # Test consensus messages
        result1 = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name="Maximizing Floor"
        )
        assert result1 == "Consensus reached on: Maximizing Floor"
        
        result2 = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name="Maximizing Average",
            constraint_amount=5000
        )
        assert result2 == "Consensus reached on: Maximizing Average with constraint amount: 5000"
        
        result3 = service._get_localized_message("voting_results.no_consensus")
        assert result3 == "No consensus reached - returning to discussion."
    
    def test_spanish_voting_results_golden(self):
        """Golden test for Spanish voting result messages."""
        service = self.create_voting_service(self.spanish_translations)
        
        # Test consensus messages
        result1 = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name="Maximizar Piso"
        )
        assert result1 == "Consenso alcanzado en: Maximizar Piso"
        
        result2 = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name="Maximizar Promedio",
            constraint_amount=5000
        )
        assert result2 == "Consenso alcanzado en: Maximizar Promedio con restricción: 5000"
        
        result3 = service._get_localized_message("voting_results.no_consensus")
        assert result3 == "No se alcanzó consenso - regresando a discusión."
    
    def test_chinese_voting_results_golden(self):
        """Golden test for Chinese voting result messages."""
        service = self.create_voting_service(self.chinese_translations)
        
        # Test consensus messages
        result1 = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name="最大化最低收入"
        )
        assert result1 == "在以下方面达成共识：最大化最低收入"
        
        result2 = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name="最大化平均收入",
            constraint_amount=5000
        )
        assert result2 == "在以下方面达成共识：最大化平均收入，约束金额：5000"
        
        result3 = service._get_localized_message("voting_results.no_consensus")
        assert result3 == "未达成共识 - 返回讨论。"
    
    def test_declined_participants_formatting_golden(self, text_regression):
        """Golden test for declined participants message formatting."""
        service = self.create_voting_service(self.english_translations)
        
        result = service._get_localized_message(
            "system_messages.voting.voting_declined",
            declined_participants="Alice, Bob"
        )
        text_regression.check(result)
    
    def test_missing_translation_fallback_golden(self):
        """Golden test for fallback behavior with missing translations."""
        service = self.create_voting_service({})  # Empty translations
        
        result = service._get_localized_message("missing.translation.key")
        assert result == "[MISSING: missing.translation.key]"
    
    def test_prompt_parameters_consistency_golden(self):
        """Golden test to ensure prompt parameter consistency across languages."""
        # Test that all language versions expect the same parameters
        test_cases = [
            ("prompts.vote_initiation_with_statement_prompt", {"agent_recent_statement": "test"}),
            ("prompts.utility_voting_confirmation_request", {"initiator_name": "test"}),
            ("voting_results.consensus_reached", {"principle_name": "test"}),
            ("voting_results.consensus_with_constraint", {"principle_name": "test", "constraint_amount": 1000}),
            ("system_messages.voting.voting_declined", {"declined_participants": "test"})
        ]
        
        languages = [
            ("english", self.english_translations),
            ("spanish", self.spanish_translations), 
            ("chinese", self.chinese_translations)
        ]
        
        formatter = Formatter()

        for key, params in test_cases:
            for lang_name, translations in languages:
                if key in translations:
                    template = translations[key]
                    placeholders = {
                        field_name for _, field_name, _, _ in formatter.parse(template)
                        if field_name
                    }
                    expected_placeholders = set(params.keys())
                    assert placeholders == expected_placeholders, (
                        f"Placeholder mismatch for {key} in {lang_name}: "
                        f"expected {expected_placeholders}, found {placeholders}"
                    )

                    service = self.create_voting_service(translations)
                    # Should not raise KeyError for missing parameters
                    result = service._get_localized_message(key, **params)
                    assert "[MISSING:" not in result, f"Missing translation for {key} in {lang_name}"
