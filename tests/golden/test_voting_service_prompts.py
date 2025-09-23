"""
Golden tests for VotingService prompt generation.

These tests validate voting prompt content across different languages using
fragment-based validation to detect unintentional changes during refactoring
while allowing for reasonable prompt improvements and formatting changes.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from core.services.voting_service import VotingService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState, ParticipantContext
from tests.utils.prompt_assertions import assert_prompt_key_elements, assert_multilingual_equivalence


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
                "A participant has proposed to initiate formal voting based on this statement:\n"
                "'{initiation_statement}'\n\n"
                "Do you agree to participate in formal voting? Respond with 1 for Yes or 0 for No."
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
                "Un participante ha propuesto iniciar votación formal basándose en esta declaración:\n"
                "'{initiation_statement}'\n\n"
                "¿Está de acuerdo en participar en votación formal? Responda con 1 para Sí o 0 para No."
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
                "一位参与者基于以下声明提议发起正式投票：\n"
                "'{initiation_statement}'\n\n"
                "您同意参加正式投票吗？请回答1表示是，0表示否。"
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
    
    def test_english_vote_initiation_prompt_golden(self):
        """Golden test for English vote initiation prompt."""
        service = self.create_voting_service(self.english_translations)

        # Test basic prompt with fragment-based validation
        result = service._get_localized_message("prompts.vote_initiation_prompt")
        assert_prompt_key_elements(result, [
            "formal voting",
            "consensus",
            "justice principle",
            "1 for Yes",
            "0 for No"
        ])
    
    def test_english_vote_initiation_with_statement_golden(self):
        """Golden test for English vote initiation prompt with statement context."""
        service = self.create_voting_service(self.english_translations)

        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement="I believe we should adopt principle A"
        )

        # Validate key elements including the statement context
        assert_prompt_key_elements(result, [
            "Based on your recent statement:",
            "I believe we should adopt principle A",
            "formal voting",
            "consensus",
            "justice principle",
            "1 for Yes",
            "0 for No"
        ])
    
    def test_spanish_vote_initiation_prompt_golden(self):
        """Golden test for Spanish vote initiation prompt."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message("prompts.vote_initiation_prompt")
        assert_multilingual_equivalence(result, [
            "votación formal",
            "consenso",
            "principio de justicia",
            "1 para Sí",
            "0 para No"
        ], "Spanish")
    
    def test_spanish_vote_initiation_with_statement_golden(self):
        """Golden test for Spanish vote initiation prompt with statement context."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement="Creo que deberíamos adoptar el principio A"
        )

        assert_multilingual_equivalence(result, [
            "Basado en su declaración reciente:",
            "Creo que deberíamos adoptar el principio A",
            "votación formal",
            "consenso",
            "principio de justicia",
            "1 para Sí",
            "0 para No"
        ], "Spanish")
    
    def test_chinese_vote_initiation_prompt_golden(self):
        """Golden test for Chinese vote initiation prompt."""
        service = self.create_voting_service(self.chinese_translations)

        result = service._get_localized_message("prompts.vote_initiation_prompt")
        assert_multilingual_equivalence(result, [
            "正式投票",
            "共识",
            "正义原则",
            "1表示是",
            "0表示否"
        ], "Chinese")
    
    def test_chinese_vote_initiation_with_statement_golden(self):
        """Golden test for Chinese vote initiation prompt with statement context."""
        service = self.create_voting_service(self.chinese_translations)

        result = service._get_localized_message(
            "prompts.vote_initiation_with_statement_prompt",
            agent_recent_statement="我认为我们应该采用原则A"
        )

        assert_multilingual_equivalence(result, [
            "基于您最近的声明：",
            "我认为我们应该采用原则A",
            "正式投票",
            "共识",
            "正义原则",
            "1表示是",
            "0表示否"
        ], "Chinese")
    
    def test_english_confirmation_request_golden(self):
        """Golden test for English confirmation request prompt."""
        service = self.create_voting_service(self.english_translations)

        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiation_statement="I think we should vote on principle A"
        )

        assert_prompt_key_elements(result, [
            "participant has proposed",
            "formal voting",
            "I think we should vote on principle A",
            "agree to participate",
            "1 for Yes",
            "0 for No"
        ])
    
    def test_spanish_confirmation_request_golden(self):
        """Golden test for Spanish confirmation request prompt."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiation_statement="Creo que deberíamos votar por el principio A"
        )

        assert_multilingual_equivalence(result, [
            "participante ha propuesto",
            "votación formal",
            "Creo que deberíamos votar por el principio A",
            "de acuerdo en participar",
            "1 para Sí",
            "0 para No"
        ], "Spanish")
    
    def test_chinese_confirmation_request_golden(self):
        """Golden test for Chinese confirmation request prompt."""
        service = self.create_voting_service(self.chinese_translations)

        result = service._get_localized_message(
            "prompts.utility_voting_confirmation_request",
            initiation_statement="我认为我们应该就原则A进行投票"
        )

        assert_multilingual_equivalence(result, [
            "参与者",
            "正式投票",
            "我认为我们应该就原则A进行投票",
            "同意参加",
            "1表示是",
            "0表示否"
        ], "Chinese")
    
    def test_english_retry_instruction_golden(self):
        """Golden test for English retry instruction."""
        service = self.create_voting_service(self.english_translations)

        result = service._get_localized_message("voting_prompts.retry_instruction")
        assert_prompt_key_elements(result, [
            "clear response",
            "1 for Yes",
            "initiate voting",
            "0 for No",
            "continue discussion"
        ])
    
    def test_spanish_retry_instruction_golden(self):
        """Golden test for Spanish retry instruction."""
        service = self.create_voting_service(self.spanish_translations)

        result = service._get_localized_message("voting_prompts.retry_instruction")
        assert_multilingual_equivalence(result, [
            "respuesta clara",
            "1 para Sí",
            "iniciar votación",
            "0 para No",
            "continuar discusión"
        ], "Spanish")
    
    def test_chinese_retry_instruction_golden(self):
        """Golden test for Chinese retry instruction."""
        service = self.create_voting_service(self.chinese_translations)

        result = service._get_localized_message("voting_prompts.retry_instruction")
        assert_multilingual_equivalence(result, [
            "明确回答",
            "1表示是",
            "发起投票",
            "0表示否",
            "继续讨论"
        ], "Chinese")
    
    def test_english_system_messages_golden(self):
        """Golden test for English system messages."""
        service = self.create_voting_service(self.english_translations)

        # Test various system messages with key element validation
        confirmation_tag = service._get_localized_message("system_messages.voting.confirmation_tag")
        assert_prompt_key_elements(confirmation_tag, ["CONFIRMATION"])

        all_confirmed = service._get_localized_message("system_messages.voting.all_confirmed")
        assert_prompt_key_elements(all_confirmed, ["participants confirmed", "secret ballot"])

        consensus_tag = service._get_localized_message("system_messages.voting.consensus_tag")
        assert_prompt_key_elements(consensus_tag, ["CONSENSUS"])

        no_consensus_tag = service._get_localized_message("system_messages.voting.no_consensus_tag")
        assert_prompt_key_elements(no_consensus_tag, ["NO CONSENSUS"])

        error_tag = service._get_localized_message("system_messages.voting.error_tag")
        assert_prompt_key_elements(error_tag, ["VOTING ERROR"])

        process_failed = service._get_localized_message("system_messages.voting.process_failed")
        assert_prompt_key_elements(process_failed, ["process failed", "returning to discussion"])
    
    def test_spanish_system_messages_golden(self):
        """Golden test for Spanish system messages."""
        service = self.create_voting_service(self.spanish_translations)

        # Test various system messages with multilingual validation
        confirmation_tag = service._get_localized_message("system_messages.voting.confirmation_tag")
        assert_multilingual_equivalence(confirmation_tag, ["CONFIRMACIÓN"], "Spanish")

        all_confirmed = service._get_localized_message("system_messages.voting.all_confirmed")
        assert_multilingual_equivalence(all_confirmed, ["participantes confirmaron", "votación secreta"], "Spanish")

        consensus_tag = service._get_localized_message("system_messages.voting.consensus_tag")
        assert_multilingual_equivalence(consensus_tag, ["CONSENSO"], "Spanish")

        no_consensus_tag = service._get_localized_message("system_messages.voting.no_consensus_tag")
        assert_multilingual_equivalence(no_consensus_tag, ["SIN CONSENSO"], "Spanish")

        error_tag = service._get_localized_message("system_messages.voting.error_tag")
        assert_multilingual_equivalence(error_tag, ["ERROR DE VOTACIÓN"], "Spanish")

        process_failed = service._get_localized_message("system_messages.voting.process_failed")
        assert_multilingual_equivalence(process_failed, ["Proceso", "falló", "regresando a discusión"], "Spanish")
    
    def test_chinese_system_messages_golden(self):
        """Golden test for Chinese system messages."""
        service = self.create_voting_service(self.chinese_translations)

        # Test various system messages with multilingual validation
        confirmation_tag = service._get_localized_message("system_messages.voting.confirmation_tag")
        assert_multilingual_equivalence(confirmation_tag, ["确认"], "Chinese")

        all_confirmed = service._get_localized_message("system_messages.voting.all_confirmed")
        assert_multilingual_equivalence(all_confirmed, ["参与者已确认", "秘密投票"], "Chinese")

        consensus_tag = service._get_localized_message("system_messages.voting.consensus_tag")
        assert_multilingual_equivalence(consensus_tag, ["共识"], "Chinese")

        no_consensus_tag = service._get_localized_message("system_messages.voting.no_consensus_tag")
        assert_multilingual_equivalence(no_consensus_tag, ["无共识"], "Chinese")

        error_tag = service._get_localized_message("system_messages.voting.error_tag")
        assert_multilingual_equivalence(error_tag, ["投票错误"], "Chinese")

        process_failed = service._get_localized_message("system_messages.voting.process_failed")
        assert_multilingual_equivalence(process_failed, ["投票过程失败", "返回讨论"], "Chinese")
    
    def test_english_voting_results_golden(self):
        """Golden test for English voting result messages."""
        service = self.create_voting_service(self.english_translations)

        # Test consensus messages with key element validation
        result1 = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name="Maximizing Floor"
        )
        assert_prompt_key_elements(result1, ["Consensus reached", "Maximizing Floor"])

        result2 = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name="Maximizing Average",
            constraint_amount=5000
        )
        assert_prompt_key_elements(result2, ["Consensus reached", "Maximizing Average", "constraint", "5000"])

        result3 = service._get_localized_message("voting_results.no_consensus")
        assert_prompt_key_elements(result3, ["No consensus", "returning to discussion"])
    
    def test_spanish_voting_results_golden(self):
        """Golden test for Spanish voting result messages."""
        service = self.create_voting_service(self.spanish_translations)

        # Test consensus messages with multilingual validation
        result1 = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name="Maximizar Piso"
        )
        assert_multilingual_equivalence(result1, ["Consenso alcanzado", "Maximizar Piso"], "Spanish")

        result2 = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name="Maximizar Promedio",
            constraint_amount=5000
        )
        assert_multilingual_equivalence(result2, ["Consenso alcanzado", "Maximizar Promedio", "restricción", "5000"], "Spanish")

        result3 = service._get_localized_message("voting_results.no_consensus")
        assert_multilingual_equivalence(result3, ["No se alcanzó consenso", "regresando a discusión"], "Spanish")
    
    def test_chinese_voting_results_golden(self):
        """Golden test for Chinese voting result messages."""
        service = self.create_voting_service(self.chinese_translations)

        # Test consensus messages with multilingual validation
        result1 = service._get_localized_message(
            "voting_results.consensus_reached",
            principle_name="最大化最低收入"
        )
        assert_multilingual_equivalence(result1, ["达成共识", "最大化最低收入"], "Chinese")

        result2 = service._get_localized_message(
            "voting_results.consensus_with_constraint",
            principle_name="最大化平均收入",
            constraint_amount=5000
        )
        assert_multilingual_equivalence(result2, ["达成共识", "最大化平均收入", "约束金额", "5000"], "Chinese")

        result3 = service._get_localized_message("voting_results.no_consensus")
        assert_multilingual_equivalence(result3, ["未达成共识", "返回讨论"], "Chinese")
    
    def test_declined_participants_formatting_golden(self):
        """Golden test for declined participants message formatting."""
        service = self.create_voting_service(self.english_translations)

        result = service._get_localized_message(
            "system_messages.voting.voting_declined",
            declined_participants="Alice, Bob"
        )
        assert_prompt_key_elements(result, [
            "Voting declined",
            "Alice, Bob",
            "returning to discussion"
        ])
    
    def test_missing_translation_fallback_golden(self):
        """Golden test for fallback behavior with missing translations."""
        service = self.create_voting_service({})  # Empty translations

        result = service._get_localized_message("missing.translation.key")
        assert_prompt_key_elements(result, ["MISSING:", "missing.translation.key"])
    
    def test_prompt_parameters_consistency_golden(self):
        """Golden test to ensure prompt parameter consistency across languages."""
        # Test that all language versions expect the same parameters
        test_cases = [
            ("prompts.vote_initiation_with_statement_prompt", {"agent_recent_statement": "test"}, ["test"]),
            ("prompts.utility_voting_confirmation_request", {"initiation_statement": "test"}, ["test"]),
            ("voting_results.consensus_reached", {"principle_name": "test"}, ["test"]),
            ("voting_results.consensus_with_constraint", {"principle_name": "test", "constraint_amount": 1000}, ["test", "1000"]),
            ("system_messages.voting.voting_declined", {"declined_participants": "test"}, ["test"])
        ]

        languages = [
            ("english", self.english_translations),
            ("spanish", self.spanish_translations),
            ("chinese", self.chinese_translations)
        ]

        for key, params, expected_elements in test_cases:
            for lang_name, translations in languages:
                if key in translations:
                    service = self.create_voting_service(translations)
                    # Should not raise KeyError for missing parameters
                    result = service._get_localized_message(key, **params)
                    # Validate the result contains expected elements and no missing translation markers
                    assert "[MISSING:" not in result, f"Missing translation for {key} in {lang_name}"
                    assert_prompt_key_elements(result, expected_elements)