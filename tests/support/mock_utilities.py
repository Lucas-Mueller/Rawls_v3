"""
Mock Utilities for Service Interface Testing

Provides realistic mock implementations of services, agents, and responses
for testing service boundaries without expensive API calls. Focuses on
multilingual support and deterministic behavior for reliable testing.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass
from enum import Enum

from models import (
    ParticipantContext, GroupDiscussionState, VoteResult, PrincipleChoice,
    JusticePrinciple, IncomeClass, PrincipleRanking, RankedPrinciple, CertaintyLevel
)
from config.phase2_settings import Phase2Settings
from utils.selective_memory_manager import MemoryEventType


class MockLanguage(Enum):
    """Supported languages for mock responses."""
    ENGLISH = "english"
    SPANISH = "spanish"
    MANDARIN = "mandarin"


@dataclass
class MockAgentResponse:
    """Mock agent response with multilingual content."""
    final_output: str
    language: MockLanguage = MockLanguage.ENGLISH


@dataclass
class MockAgentConfig:
    """Mock agent configuration."""
    language: str = "english"
    model: str = "gpt-4"
    temperature: float = 0.7
    memory_character_limit: int = 8000


class MockParticipantAgent:
    """Mock participant agent for service testing."""

    def __init__(self, name: str, language: str = "english"):
        self.name = name
        self.agent = Mock()  # Mock OpenAI Agent
        self.config = MockAgentConfig(language=language)

        # Track calls for testing
        self.call_history = []

    def add_call(self, method: str, **kwargs):
        """Track method calls for testing."""
        self.call_history.append({"method": method, "kwargs": kwargs})


class MockParticipantContext:
    """Mock participant context for service testing."""

    def __init__(self, name: str, language: str = "english"):
        self.name = name
        self.language = language
        self.phase = 2
        self.round_number = 1
        self.memory = ""
        self.bank_balance = 100.0
        self.income_class = IncomeClass.MEDIUM
        self.interaction_type: Optional[str] = None
        self.internal_reasoning = ""
        self.memory_character_limit = 8000
        self.current_round_number = 1
        self.allow_vote_tool = True
        self.role_description = f"Participant {name} in justice experiment"
        self.stage = None


class MockLanguageManager:
    """Mock language manager with multilingual responses."""

    def __init__(self, language: MockLanguage = MockLanguage.ENGLISH):
        self.language = language
        self.translations = self._build_translations()

    def _build_translations(self) -> Dict[str, Dict[str, str]]:
        """Build mock translations for testing."""
        return {
            MockLanguage.ENGLISH.value: {
                "prompts.vote_initiation_prompt": "Do you want to initiate voting? (1=Yes, 0=No)",
                "prompts.utility_voting_confirmation_request": "Do you agree to participate in voting? (1=Yes, 0=No)",
                "system_messages.voting.confirmation_tag": "[CONFIRMATION]",
                "system_messages.voting.consensus_tag": "[CONSENSUS]",
                "system_messages.voting.no_consensus_tag": "[NO CONSENSUS]",
                "voting_results.consensus_reached": "Consensus reached on {principle_name}",
                "voting_results.consensus_with_constraint": "Consensus reached on {principle_name} with constraint {constraint_amount}",
                "voting_results.no_consensus": "No consensus reached",
                "common.principle_names.maximizing_floor": "Maximizing Floor",
                "common.principle_names.maximizing_average": "Maximizing Average",
                "common.principle_names.maximizing_average_floor_constraint": "Maximizing Average with Floor Constraint",
                "common.principle_names.maximizing_average_range_constraint": "Maximizing Average with Range Constraint",
                "common.income_classes.high": "High Income",
                "common.income_classes.medium_high": "Medium-High Income",
                "common.income_classes.medium": "Medium Income",
                "common.income_classes.medium_low": "Medium-Low Income",
                "common.income_classes.low": "Low Income",
                "prompts.phase2_discussion_short_prompt": "Round {round_number}/{max_rounds}: Share your thoughts on justice principles.",
                "prompts.phase2_internal_reasoning": "Consider your position on justice principles in round {round_number}/{max_rounds}.",
                "prompts.phase2_final_ranking_prompt": "Rank the four justice principles from most to least preferred.",
                "memory.final_results_format": "Phase 2 Results:\n{result_content}",
                "system_messages.discussion.group_composition": "Group participants: {participants}",
                "system_messages.discussion.truncation_marker": "[Discussion history truncated for brevity]",
                "memory_field_labels.prompt": "Prompt:",
                "memory_field_labels.your_statement": "Your Statement:",
                "memory_field_labels.outcome": "Outcome:",
                "memory_outcomes.made_discussion_statement": "Made statement in round {round_number}",
                "voting_phases.initiation": "Voting initiation phase by {initiator_name}",
                "voting_phases.confirmation": "Voting confirmation phase",
                "voting_phases.ballot": "Secret ballot phase",
                "prompts.memory_insertions.vote_initiation_decision": "Round {round_num}: {decision}",
                "prompts.memory_insertions.initiate_voting": "Decided to initiate voting",
                "prompts.memory_insertions.continue_discussion": "Decided to continue discussion",
                "prompts.memory_insertions.confirmation_response": "{response} participate in voting",
                "prompts.memory_insertions.agreed_to": "Agreed to",
                "prompts.memory_insertions.declined_to": "Declined to",
                "prompts.memory_insertions.secret_ballot_choice": "Selected {principle_name} in secret ballot",
                "prompts.memory_insertions.amount_specification": "Specified constraint amount: {amount}",
                "manipulator.target_header": "**MANIPULATOR TARGET**",
                "manipulator.target_principle_line": "Principle: {principle}",
                "manipulator.target_method_line": "Determined via Borda count on Phase 1 rankings.",
                "manipulator.target_guidance": "Guidance: Keep this assignment confidential and steer consensus toward it.",
                "manipulator.tiebreak_note": "Note: Tiebreaker applied. Principles {tied_principles} were tied; {selected_principle} selected using deterministic order: {tiebreak_order}.",
            },
            MockLanguage.SPANISH.value: {
                "prompts.vote_initiation_prompt": "¿Quieres iniciar la votación? (1=Sí, 0=No)",
                "prompts.utility_voting_confirmation_request": "¿Estás de acuerdo en participar en la votación? (1=Sí, 0=No)",
                "system_messages.voting.confirmation_tag": "[CONFIRMACIÓN]",
                "system_messages.voting.consensus_tag": "[CONSENSO]",
                "system_messages.voting.no_consensus_tag": "[SIN CONSENSO]",
                "voting_results.consensus_reached": "Consenso alcanzado en {principle_name}",
                "voting_results.consensus_with_constraint": "Consenso alcanzado en {principle_name} con restricción {constraint_amount}",
                "voting_results.no_consensus": "No se alcanzó consenso",
                "common.principle_names.maximizing_floor": "Maximizar Piso",
                "common.principle_names.maximizing_average": "Maximizar Promedio",
                "common.principle_names.maximizing_average_floor_constraint": "Maximizar Promedio con Restricción de Piso",
                "common.principle_names.maximizing_average_range_constraint": "Maximizar Promedio con Restricción de Rango",
                "prompts.phase2_discussion_short_prompt": "Ronda {round_number}/{max_rounds}: Comparte tus pensamientos sobre principios de justicia.",
                "prompts.phase2_final_ranking_prompt": "Clasifica los cuatro principios de justicia de más a menos preferido.",
                "memory.final_results_format": "Resultados Fase 2:\n{result_content}",
                "manipulator.target_header": "**OBJETIVO DEL MANIPULADOR**",
                "manipulator.target_principle_line": "Principio: {principle}",
                "manipulator.target_method_line": "Determinado mediante conteo de Borda en las clasificaciones de la Fase 1.",
                "manipulator.target_guidance": "Orientación: Mantén esta asignación confidencial y dirige el consenso hacia ella.",
                "manipulator.tiebreak_note": "Nota: Desempate aplicado. Los principios {tied_principles} estaban empatados; {selected_principle} seleccionado usando orden determinista: {tiebreak_order}.",
            },
            MockLanguage.MANDARIN.value: {
                "prompts.vote_initiation_prompt": "你想发起投票吗？(1=是, 0=否)",
                "prompts.utility_voting_confirmation_request": "你同意参与投票吗？(1=是, 0=否)",
                "system_messages.voting.confirmation_tag": "[确认]",
                "system_messages.voting.consensus_tag": "[达成共识]",
                "system_messages.voting.no_consensus_tag": "[未达成共识]",
                "voting_results.consensus_reached": "在{principle_name}上达成了共识",
                "voting_results.consensus_with_constraint": "在{principle_name}上达成了共识，约束条件为{constraint_amount}",
                "voting_results.no_consensus": "未达成共识",
                "common.principle_names.maximizing_floor": "最大化最低收入",
                "common.principle_names.maximizing_average": "最大化平均收入",
                "common.principle_names.maximizing_average_floor_constraint": "在最低收入约束条件下最大化平均收入",
                "common.principle_names.maximizing_average_range_constraint": "在范围约束条件下最大化平均收入",
                "prompts.phase2_discussion_short_prompt": "第{round_number}/{max_rounds}轮：分享你对正义原则的想法。",
                "prompts.phase2_final_ranking_prompt": "将四个正义原则从最喜欢到最不喜欢进行排序。",
                "memory.final_results_format": "第二阶段结果：\n{result_content}",
                "manipulator.target_header": "**操纵者目标**",
                "manipulator.target_principle_line": "原则：{principle}",
                "manipulator.target_method_line": "通过第一阶段排名的博达计数确定。",
                "manipulator.target_guidance": "指导：保密此分配并引导共识朝向它。",
                "manipulator.tiebreak_note": "注意：应用了平局决胜。原则{tied_principles}平局；使用确定性顺序选择{selected_principle}：{tiebreak_order}。",
            }
        }

    def get(self, key: str, **kwargs) -> str:
        """Get localized message with substitutions."""
        lang_translations = self.translations.get(self.language.value, {})
        template = lang_translations.get(key, f"[MISSING: {key}]")

        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"[MISSING PARAM: {e} in {key}]"


class MockUtilityAgent:
    """Mock utility agent for parsing responses."""

    def __init__(self):
        self.call_history = []

    def detect_numerical_agreement(self, response: str) -> tuple[bool, Optional[str]]:
        """Mock numerical agreement detection."""
        self.call_history.append({"method": "detect_numerical_agreement", "response": response})

        # Simulate realistic parsing
        response_lower = response.lower().strip()

        # Check for 1 (yes) responses - prioritize numerical
        if "1" in response_lower:
            return True, None
        elif "0" in response_lower:
            return False, None
        # Check for clear yes/no responses (not just substring matches)
        elif response_lower.startswith("yes") or ", yes" in response_lower or "yes," in response_lower:
            return True, None
        elif response_lower.startswith("no") or ", no" in response_lower or "no," in response_lower:
            return False, None
        elif "sí" in response_lower:
            return True, None
        elif "是" in response_lower and "是否" not in response_lower:  # Avoid "是否" (whether)
            return True, None
        elif "否" in response_lower and "是否" not in response_lower:  # Avoid "是否" (whether)
            return False, None

        # Invalid/ambiguous responses should return error
        return False, f"Could not detect numerical agreement in: '{response[:50]}'"

    async def parse_principle_choice_enhanced(self, statement: str):
        """Mock principle choice parsing."""
        self.call_history.append({"method": "parse_principle_choice_enhanced", "statement": statement})

        # Mock parsing based on keywords
        if "floor" in statement.lower() or "最低" in statement:
            return PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE)
        elif "average" in statement.lower() or "平均" in statement:
            return PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_AVERAGE, certainty=CertaintyLevel.SURE)
        else:
            return PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE)

    async def parse_principle_ranking_enhanced(self, text_response: str) -> PrincipleRanking:
        """Mock principle ranking parsing."""
        self.call_history.append({"method": "parse_principle_ranking_enhanced", "text_response": text_response})

        # Return mock ranking
        return PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ],
            certainty=CertaintyLevel.SURE
        )


class MockLogger:
    """Mock logger for service testing."""

    def __init__(self):
        self.logs = []

    def log_info(self, message: str) -> None:
        """Log info message."""
        self.logs.append({"level": "info", "message": message})

    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.logs.append({"level": "warning", "message": message})

    def info(self, message: str) -> None:
        """Log info message."""
        self.log_info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.log_warning(message)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logs.append({"level": "debug", "message": message})


class MockSeedManager:
    """Mock seed manager for deterministic randomness."""

    def __init__(self, seed: int = 42):
        import random
        self._random = random.Random(seed)

    @property
    def random(self):
        """Get deterministic random instance."""
        return self._random


class MockMemoryService:
    """Mock memory service for testing."""

    def __init__(self):
        self.update_calls = []

    async def update_memory_selective(self, agent, context, content, event_type=None, **kwargs) -> str:
        """Mock memory update."""
        self.update_calls.append({
            "agent_name": agent.name,
            "content": content,
            "event_type": event_type,
            "kwargs": kwargs
        })

        # Simulate memory update
        new_memory = f"{context.memory}\n{content}" if context.memory else content
        context.memory = new_memory
        return new_memory

    async def update_discussion_memory(self, agent, context, statement, **kwargs) -> str:
        """Mock discussion memory update."""
        return await self.update_memory_selective(
            agent, context, f"Discussion: {statement}",
            event_type=MemoryEventType.DISCUSSION_STATEMENT, **kwargs
        )

    async def update_voting_phase_memory(self, agent, context, phase_name, **kwargs) -> str:
        """Mock voting phase memory update."""
        return await self.update_memory_selective(
            agent, context, f"Voting phase: {phase_name}",
            event_type=MemoryEventType.PHASE_TRANSITION, **kwargs
        )

    async def update_final_results_memory(self, agent, context, result_content, final_earnings, consensus_reached, **kwargs) -> str:
        """Mock final results memory update."""
        content = f"Final Results: ${final_earnings:.2f}\n{result_content}"
        return await self.update_memory_selective(
            agent, context, content,
            event_type=MemoryEventType.FINAL_RESULTS, **kwargs
        )


class MockGroupDiscussionState:
    """Mock group discussion state."""

    def __init__(self):
        self.public_history = ""
        self.round_number = 1
        self.vote_history = []
        self.last_vote_result = None

    def get_formatted_discussion_history(self) -> str:
        """Get formatted discussion history."""
        return self.public_history


class MockErrorHandler:
    """Mock error handler."""

    def __init__(self):
        self.handled_errors = []

    def handle_error(self, error: Exception, context: str = "") -> None:
        """Handle an error with context."""
        self.handled_errors.append({"error": str(error), "context": context})


class MockResponseGenerator:
    """Generates realistic mock responses for different scenarios."""

    @staticmethod
    def get_vote_initiation_responses(language: MockLanguage = MockLanguage.ENGLISH) -> Dict[str, str]:
        """Get vote initiation responses by language."""
        responses = {
            MockLanguage.ENGLISH: {
                "yes": "1 - I believe we should initiate voting now.",
                "no": "0 - I think we need more discussion first.",
                "ambiguous": "I'm not sure if we're ready to vote yet.",
                "invalid": "Maybe we should consider voting soon."
            },
            MockLanguage.SPANISH: {
                "yes": "1 - Creo que deberíamos iniciar la votación ahora.",
                "no": "0 - Creo que necesitamos más discusión primero.",
                "ambiguous": "No estoy seguro si estamos listos para votar.",
                "invalid": "Tal vez deberíamos considerar votar pronto."
            },
            MockLanguage.MANDARIN: {
                "yes": "1 - 我认为我们现在应该开始投票。",
                "no": "0 - 我认为我们首先需要更多的讨论。",
                "ambiguous": "我不确定我们是否准备好投票。",
                "invalid": "也许我们应该考虑很快投票。"
            }
        }
        return responses[language]

    @staticmethod
    def get_discussion_statements(language: MockLanguage = MockLanguage.ENGLISH) -> List[str]:
        """Get discussion statements by language."""
        statements = {
            MockLanguage.ENGLISH: [
                "I believe maximizing the floor is the most just principle because it helps the least fortunate.",
                "Maximizing average income benefits society as a whole and creates more wealth.",
                "We need to find a balance between helping the poor and encouraging productivity.",
                "The rawlsian approach suggests we should focus on helping the worst off members.",
            ],
            MockLanguage.SPANISH: [
                "Creo que maximizar el piso es el principio más justo porque ayuda a los menos afortunados.",
                "Maximizar el ingreso promedio beneficia a la sociedad en su conjunto y crea más riqueza.",
                "Necesitamos encontrar un equilibrio entre ayudar a los pobres y fomentar la productividad.",
                "El enfoque rawlsiano sugiere que debemos centrarnos en ayudar a los miembros más desfavorecidos.",
            ],
            MockLanguage.MANDARIN: [
                "我认为最大化最低收入是最公正的原则，因为它帮助了最不幸的人。",
                "最大化平均收入有利于整个社会，创造更多财富。",
                "我们需要在帮助穷人和鼓励生产力之间找到平衡。",
                "罗尔斯的方法建议我们应该专注于帮助最不幸的成员。",
            ]
        }
        return statements[language]

    @staticmethod
    def get_principle_rankings(language: MockLanguage = MockLanguage.ENGLISH) -> str:
        """Get principle ranking response by language."""
        rankings = {
            MockLanguage.ENGLISH: """
            1. Maximizing Floor - Most important to help the least fortunate
            2. Maximizing Average with Floor Constraint - Good balance
            3. Maximizing Average with Range Constraint - Acceptable compromise
            4. Maximizing Average - Least preferred due to inequality concerns

            Certainty: Confident
            """,
            MockLanguage.SPANISH: """
            1. Maximizar Piso - Más importante ayudar a los menos afortunados
            2. Maximizar Promedio con Restricción de Piso - Buen equilibrio
            3. Maximizar Promedio con Restricción de Rango - Compromiso aceptable
            4. Maximizar Promedio - Menos preferido por preocupaciones de desigualdad

            Certeza: Confiado
            """,
            MockLanguage.MANDARIN: """
            1. 最大化最低收入 - 帮助最不幸的人最重要
            2. 在最低收入约束条件下最大化平均收入 - 很好的平衡
            3. 在范围约束条件下最大化平均收入 - 可接受的妥协
            4. 最大化平均收入 - 由于不平等问题最不喜欢

            确定性：有信心
            """
        }
        return rankings[language].strip()


def create_mock_runner():
    """Create mock Runner for agent interactions."""
    mock_runner = AsyncMock()

    async def mock_run(agent, prompt, context=None, **kwargs):
        """Mock agent run with realistic responses."""
        # Determine language from context
        language = MockLanguage.ENGLISH
        if context and hasattr(context, 'language'):
            lang_str = context.language.lower()
            if lang_str == 'spanish':
                language = MockLanguage.SPANISH
            elif lang_str in ['mandarin', 'chinese']:
                language = MockLanguage.MANDARIN

        # Generate appropriate response based on prompt
        if "vote" in prompt.lower() and ("1=" in prompt or "0=" in prompt):
            # Vote initiation or confirmation
            responses = MockResponseGenerator.get_vote_initiation_responses(language)
            response_text = responses["yes"]  # Default to yes for testing
        elif "rank" in prompt.lower() or "principle" in prompt.lower():
            # Principle ranking
            response_text = MockResponseGenerator.get_principle_rankings(language)
        else:
            # Discussion statement
            statements = MockResponseGenerator.get_discussion_statements(language)
            response_text = statements[0]  # Default to first statement

        return MockAgentResponse(final_output=response_text, language=language)

    mock_runner.run = mock_run
    return mock_runner


# Factory functions for easy test setup

def create_mock_participants(names: List[str], language: str = "english") -> List[MockParticipantAgent]:
    """Create mock participants with specified language."""
    return [MockParticipantAgent(name, language) for name in names]


def create_mock_contexts(names: List[str], language: str = "english") -> List[MockParticipantContext]:
    """Create mock contexts with specified language."""
    return [MockParticipantContext(name, language) for name in names]


def create_multilingual_test_setup() -> Dict[str, Any]:
    """Create comprehensive multilingual test setup."""
    return {
        "english": {
            "participants": create_mock_participants(["Alice", "Bob"], "english"),
            "contexts": create_mock_contexts(["Alice", "Bob"], "english"),
            "language_manager": MockLanguageManager(MockLanguage.ENGLISH)
        },
        "spanish": {
            "participants": create_mock_participants(["Carlos", "Diana"], "spanish"),
            "contexts": create_mock_contexts(["Carlos", "Diana"], "spanish"),
            "language_manager": MockLanguageManager(MockLanguage.SPANISH)
        },
        "mandarin": {
            "participants": create_mock_participants(["李明", "王芳"], "mandarin"),
            "contexts": create_mock_contexts(["李明", "王芳"], "mandarin"),
            "language_manager": MockLanguageManager(MockLanguage.MANDARIN)
        }
    }


def create_mock_vote_result(consensus: bool = True, principle: JusticePrinciple = JusticePrinciple.MAXIMIZING_FLOOR) -> VoteResult:
    """Create mock vote result for testing."""
    if consensus:
        agreed_choice = PrincipleChoice(principle=principle, certainty=CertaintyLevel.SURE, constraint_amount=None)
        return VoteResult(
            votes=[agreed_choice, agreed_choice],  # Mock 2 unanimous votes
            consensus_reached=True,
            agreed_principle=agreed_choice,
            individual_votes=[]
        )
    else:
        vote1 = PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE)
        vote2 = PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_AVERAGE, certainty=CertaintyLevel.SURE)
        return VoteResult(
            votes=[vote1, vote2],  # Mock disagreement
            consensus_reached=False,
            agreed_principle=None,
            individual_votes=[]
        )


def create_mock_discussion_state(history: str = "", round_num: int = 1) -> MockGroupDiscussionState:
    """Create mock discussion state with specified history."""
    state = MockGroupDiscussionState()
    state.public_history = history
    state.round_number = round_num
    return state