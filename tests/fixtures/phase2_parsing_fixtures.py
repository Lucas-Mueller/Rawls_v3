"""
Test fixtures and utilities for Phase 2 parsing tests.

Provides reusable test data, mock objects, and utility functions for:
1. Realistic participant statements across languages
2. Mock agent configurations and contexts
3. Test data for various parsing scenarios
4. Utility functions for async test execution
5. Assertion helpers for parsing validation
6. Mock LLM response generators

This fixture module supports all Phase 2 parsing test suites by providing
consistent, realistic test data and reducing code duplication.
"""

import asyncio
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass

from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel, PrincipleRanking, RankedPrinciple
from models.experiment_types import ParticipantContext, GroupDiscussionState, ExperimentPhase
from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
from experiment_agents.utility_agent import UtilityAgent
from experiment_agents.participant_agent import ParticipantAgent


# =============================================================================
# Test Data Constants
# =============================================================================

# Realistic statements that should trigger vote intention detection
POSITIVE_VOTE_STATEMENTS = {
    "english": [
        "Let's vote on this",
        "I think we should vote now", 
        "We should vote on the principles",
        "Time to vote",
        "I propose we vote",
        "Let's call for a vote",
        "We need to reach a decision",
        "Let's finalize our choice",
        "I suggest we vote on the matter"
    ],
    "chinese": [
        "我们投票吧",
        "现在投票吧", 
        "我认为我们应该投票",
        "是时候投票了",
        "让我们投票",
        "我们应该投票决定",
        "投票表决吧"
    ],
    "spanish": [
        "Votemos",
        "Creo que deberíamos votar",
        "Es hora de votar",
        "Propongo que votemos",
        "Deberíamos votar sobre esto"
    ]
}

# Statements that should NOT trigger vote intention (exclusion patterns)
NEGATIVE_VOTE_STATEMENTS = {
    "english": [
        "Should we vote later?",
        "Do you think we should vote?",
        "We need more discussion before voting",
        "I don't think we should vote yet", 
        "Not ready to vote",
        "We need to discuss more",
        "What if we vote?",
        "When should we vote?"
    ],
    "chinese": [
        "我们应该稍后投票吗？",
        "我们需要更多讨论",
        "还没准备好投票",
        "什么时候投票？"
    ]
}

# Realistic ballot statements for parsing tests
BALLOT_STATEMENTS = {
    "valid_ballots": [
        {
            "statement": "My ballot choice is maximizing floor income",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None
        },
        {
            "statement": "I choose maximizing average income with floor constraint of $15,000",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "expected_constraint": 15000
        },
        {
            "statement": "My vote is for maximizing average income with range constraint of $20000",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "expected_constraint": 20000
        },
        {
            "statement": "I support maximizing the floor income with no additional constraints",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None
        }
    ],
    "problematic_ballots": [
        {
            "statement": "maximizing floor income with no additional constraints",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Critical vulnerability case"
        },
        {
            "statement": "My ballot choice is Maximizing the average income with a floor constraint with a floor constraint of $13,000",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "expected_constraint": 13000,
            "description": "Alice's specific case"
        }
    ]
}

# Comprehensive Chinese ballot statements  
CHINESE_BALLOT_STATEMENTS = {
    "valid_ballots": [
        {
            "statement": "我选择最大化最低收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Full principle name"
        },
        {
            "statement": "我选择最大化平均收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
            "expected_constraint": None,
            "description": "Full average principle name"
        },
        {
            "statement": "我选择在最低收入约束条件下最大化平均收入，约束条件是15000元",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "expected_constraint": 15000,
            "description": "Full floor constraint principle with Yuan word"
        },
        {
            "statement": "我选择在范围约束条件下最大化平均收入，约束为18千",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "expected_constraint": 18000,
            "description": "Full range constraint with thousands format"
        }
    ],
    "critical_vulnerability_cases": [
        {
            "statement": "最大化最低收入没有额外约束条件",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Chinese equivalent of critical vulnerability case"
        },
        {
            "statement": "我的投票选择是最大化最低收入，没有任何约束",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Extended Chinese vulnerability case"
        },
        {
            "statement": "我选择最大化最低收入，无约束条件",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Full name vulnerability case"
        }
    ]
}

# Comprehensive Spanish ballot statements
SPANISH_BALLOT_STATEMENTS = {
    "valid_ballots": [
        {
            "statement": "Elijo la maximización del ingreso mínimo",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Full principle name"
        },
        {
            "statement": "Elijo la maximización del ingreso promedio",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
            "expected_constraint": None,
            "description": "Full average principle name"
        },
        {
            "statement": "Mi elección es maximización del ingreso promedio bajo restricción de ingreso mínimo con restricción de 15.000 euros",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "expected_constraint": 15000,
            "description": "Full floor constraint principle with European format"
        },
        {
            "statement": "Elijo maximización del ingreso promedio bajo restricción de rango con restricción de 18k euros",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "expected_constraint": 18000,
            "description": "Full range constraint with k format"
        }
    ],
    "critical_vulnerability_cases": [
        {
            "statement": "maximización del ingreso mínimo sin restricciones adicionales",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Spanish equivalent of critical vulnerability case"
        },
        {
            "statement": "Mi elección de voto es maximización del ingreso mínimo sin ninguna restricción",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Extended Spanish vulnerability case"
        },
        {
            "statement": "Elijo maximización del ingreso mínimo sin condiciones restrictivas",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
            "expected_constraint": None,
            "description": "Full name Spanish vulnerability case"
        }
    ]
}

# Language-specific constraint amount formats
LANGUAGE_SPECIFIC_CONSTRAINTS = {
    "chinese": [
        # Various Yuan formats
        ("约束为¥15,000", 15000, "Yuan with comma separator"),
        ("约束条件是15000元", 15000, "Yuan with Chinese character"),  
        ("约束为¥15000", 15000, "Yuan without separator"),
        ("约束是15千", 15000, "Chinese thousands format"),
        ("约束条件¥18,500", 18500, "Yuan with decimal thousands"),
        ("约束为14k", 14000, "Chinese k format"),
        # More traditional Chinese number expressions
        ("约束为一万五千", 15000, "Traditional Chinese number words"),
        ("约束条件是2万", 20000, "Chinese wan (10,000) format")
    ],
    "spanish": [
        # Various Euro formats  
        ("con restricción de €15,000", 15000, "Euro with comma separator"),
        ("restricción de 15.000 euros", 15000, "European dot separator with word"),
        ("con restricción €15000", 15000, "Euro without separator"),
        ("restricción de €18,500", 18500, "Euro with decimal thousands"),
        ("con restricción de 15k euros", 15000, "Spanish k format with euros"),
        ("restricción €14.500", 14500, "Euro European format"),
        # Alternative Spanish formats
        ("restricción de quince mil euros", 15000, "Spanish number words"),
        ("con límite de €20000", 20000, "Spanish limit terminology")
    ],
    "english": [
        # Standard US formats for comparison
        ("constraint of $15,000", 15000, "US dollar with comma"),
        ("constraint $15000", 15000, "US dollar without comma"),
        ("with $15k constraint", 15000, "US k format"),
        ("constraint of 15 thousand", 15000, "US number words"),
        ("$18,500 constraint", 18500, "US decimal thousands")
    ]
}

# Multilingual preference statements - Comprehensive coverage
PREFERENCE_STATEMENTS = {
    "english": [
        {
            "statement": "My preference is maximizing floor income",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
        },
        {
            "statement": "I prefer maximizing average income",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
        },
        {
            "statement": "I choose maximizing average income with floor constraint of $15,000", 
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            "expected_constraint": 15000
        },
        {
            "statement": "I support maximizing average income with range constraint of $20,000",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            "expected_constraint": 20000
        },
        {
            "statement": "Preference: maximizing floor income",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
        },
        {
            "statement": "Choice: maximizing average income without constraints",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
        }
    ],
    "chinese": [
        {
            "statement": "我的偏好是最大化最低收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
        },
        {
            "statement": "我的选择是最大化平均收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
        },
        {
            "statement": "我选择在最低收入约束条件下最大化平均收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        },
        {
            "statement": "我支持在范围约束条件下最大化平均收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        },
        {
            "statement": "偏好：最大化最低收入",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
        },
        {
            "statement": "选择：最大化平均收入无约束条件",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
        }
    ],
    "spanish": [
        {
            "statement": "Mi preferencia es la maximización del ingreso mínimo",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
        },
        {
            "statement": "Mi elección es la maximización del ingreso promedio",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
        },
        {
            "statement": "Elijo maximización del ingreso promedio bajo restricción de ingreso mínimo",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        },
        {
            "statement": "Apoyo maximización del ingreso promedio bajo restricción de rango",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
        },
        {
            "statement": "Preferencia: maximización del ingreso mínimo",
            "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
        },
        {
            "statement": "Elección: maximización del ingreso promedio sin restricciones",
            "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE
        }
    ]
}

# Agreement/disagreement statements for multilingual testing
AGREEMENT_STATEMENTS = {
    "positive": {
        "english": [
            "Yes, I agree",
            "I agree to proceed", 
            "Yes, let's do it",
            "Agreed",
            "I'm in favor",
            "Count me in",
            "Yes, maximizing floor income with NO CONSTRAINTS"  # Domain exception test
        ],
        "chinese": [
            "是的，我同意",
            "好的，我同意",
            "同意",
            "我赞成"
        ],
        "spanish": [
            "Sí, estoy de acuerdo",
            "Acepto",
            "De acuerdo"
        ]
    },
    "negative": {
        "english": [
            "No, I disagree",
            "I don't agree",
            "No way",
            "I oppose this",
            "Count me out"
        ],
        "chinese": [
            "不，我不同意",
            "我不赞成",
            "不行"
        ],
        "spanish": [
            "No, no estoy de acuerdo",
            "No acepto",
            "Me opongo"
        ]
    }
}


# =============================================================================
# Mock Data Classes
# =============================================================================

@dataclass
class MockLLMResponse:
    """Mock LLM response for testing."""
    final_output: str
    
    def __str__(self):
        return self.final_output


@dataclass 
class TestParticipant:
    """Test participant data."""
    name: str
    agent_config: Dict[str, Any]
    context: ParticipantContext
    expected_responses: Dict[str, str]


# =============================================================================
# Fixture Classes
# =============================================================================

class Phase2ParsingFixtures:
    """Main fixture provider for Phase 2 parsing tests."""
    
    @staticmethod
    def create_test_utility_agent(model: str = "gpt-4o-mini", temperature: float = 0.0) -> UtilityAgent:
        """Create utility agent for testing."""
        return UtilityAgent(utility_model=model, temperature=temperature)
    
    @staticmethod
    def create_mock_participant_agent(name: str) -> ParticipantAgent:
        """Create mock participant agent."""
        agent = MagicMock(spec=ParticipantAgent)
        agent.name = name
        agent.agent = MagicMock()
        return agent
    
    @staticmethod
    def create_test_participant_context(
        name: str, 
        memory: str = "Test memory",
        round_number: int = 1
    ) -> ParticipantContext:
        """Create participant context for testing."""
        return ParticipantContext(
            name=name,
            role_description=f"Test participant {name}",
            bank_balance=1000.0,
            memory=memory,
            round_number=round_number,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=50000
        )
    
    @staticmethod
    def create_test_experiment_config(
        num_agents: int = 3,
        voting_mode: str = "complex",
        language: str = "English"
    ) -> ExperimentConfiguration:
        """Create test experiment configuration."""
        config = MagicMock(spec=ExperimentConfiguration)
        config.phase2_rounds = 5
        config.voting_detection_mode = voting_mode
        config.language = language
        config.phase2_settings = Phase2Settings.get_default()
        
        # Create agent configs
        config.agents = []
        for i in range(num_agents):
            agent_config = MagicMock(spec=AgentConfiguration)
            agent_config.name = f"TestAgent{i+1}"
            agent_config.personality = f"Test personality {i+1}"
            agent_config.memory_character_limit = 50000
            config.agents.append(agent_config)
        
        return config
    
    @staticmethod
    def create_principle_choice(
        principle: JusticePrinciple,
        constraint: Optional[int] = None,
        certainty: CertaintyLevel = CertaintyLevel.SURE
    ) -> PrincipleChoice:
        """Create principle choice for testing."""
        return PrincipleChoice.create_for_parsing(
            principle=principle,
            constraint_amount=constraint,
            certainty=certainty,
            reasoning="Test choice"
        )
    
    @staticmethod
    def create_test_ranking() -> PrincipleRanking:
        """Create test principle ranking."""
        rankings = [
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
        ]
        return PrincipleRanking(rankings=rankings, certainty=CertaintyLevel.SURE)


# =============================================================================
# Mock Response Generators
# =============================================================================

class MockResponseGenerator:
    """Generates realistic mock responses for testing."""
    
    @staticmethod
    def generate_llm_principle_response(
        principle: str,
        constraint_amount: Optional[int] = None,
        certainty: str = "sure",
        include_extra_text: bool = False
    ) -> str:
        """Generate mock LLM response for principle parsing."""
        response_data = {
            "principle": principle,
            "constraint_amount": constraint_amount,
            "certainty": certainty,
            "confidence": 0.9
        }
        
        json_str = str(response_data).replace("'", '"').replace("None", "null")
        
        if include_extra_text:
            return f"Based on the analysis, I can extract: {json_str}"
        else:
            return json_str
    
    @staticmethod
    def generate_vote_detection_response(detected: bool, reasoning: str = "") -> str:
        """Generate mock response for vote intention detection."""
        if detected:
            return f"VOTE_DETECTED{': ' + reasoning if reasoning else ''}"
        else:
            return f"NO_VOTE_DETECTED{': ' + reasoning if reasoning else ''}"
    
    @staticmethod
    def generate_preference_detection_response(
        preference: Optional[str] = None,
        constraint: Optional[int] = None
    ) -> str:
        """Generate mock response for preference detection."""
        if preference:
            base = f"PREFERENCE_DETECTED: {preference}"
            if constraint:
                base += f" with ${constraint:,}"
            return base
        else:
            return "NO_PREFERENCE_DETECTED"
    
    @staticmethod
    def generate_agreement_response(agrees: bool) -> str:
        """Generate mock response for agreement detection."""
        return "AGREES" if agrees else "DISAGREES"


# =============================================================================
# Test Utilities
# =============================================================================

class ParsingTestUtils:
    """Utility functions for parsing tests."""
    
    @staticmethod
    async def run_async_test(async_func, *args, **kwargs):
        """Helper to run async test functions."""
        return await async_func(*args, **kwargs)
    
    @staticmethod
    def assert_principle_choice_equal(
        actual: PrincipleChoice,
        expected_principle: JusticePrinciple,
        expected_constraint: Optional[int] = None,
        message: str = ""
    ):
        """Assert that principle choice matches expected values."""
        assert actual is not None, f"Principle choice should not be None. {message}"
        assert actual.principle == expected_principle, \
               f"Expected principle {expected_principle.value}, got {actual.principle.value}. {message}"
        assert actual.constraint_amount == expected_constraint, \
               f"Expected constraint {expected_constraint}, got {actual.constraint_amount}. {message}"
    
    @staticmethod
    def assert_consensus_result(
        consensus: bool,
        agreed_principle: Optional[PrincipleChoice],
        warnings: List[str],
        expected_consensus: bool,
        expected_principle: Optional[JusticePrinciple] = None,
        message: str = ""
    ):
        """Assert consensus result matches expectations."""
        assert consensus == expected_consensus, \
               f"Expected consensus {expected_consensus}, got {consensus}. {message}"
        
        if expected_consensus:
            assert agreed_principle is not None, f"Expected agreed principle but got None. {message}"
            if expected_principle:
                assert agreed_principle.principle == expected_principle, \
                       f"Expected agreed principle {expected_principle.value}, got {agreed_principle.principle.value}. {message}"
        else:
            assert agreed_principle is None, f"Expected no agreed principle but got {agreed_principle}. {message}"
    
    @staticmethod
    def create_mock_runner_responses(responses: List[str]) -> AsyncMock:
        """Create mock runner that returns specific responses in sequence."""
        mock_runner = AsyncMock()
        
        # Create mock results for each response
        mock_results = []
        for response in responses:
            mock_result = MagicMock()
            mock_result.final_output = response
            mock_results.append(mock_result)
        
        mock_runner.side_effect = mock_results
        return mock_runner
    
    @staticmethod
    def get_test_statement_by_language(
        statement_dict: Dict[str, List],
        language: str,
        index: int = 0
    ) -> str:
        """Get test statement by language and index."""
        lang_key = language.lower()
        if lang_key in statement_dict:
            statements = statement_dict[lang_key]
            if index < len(statements):
                return statements[index]
        
        # Fallback to English
        if "english" in statement_dict and index < len(statement_dict["english"]):
            return statement_dict["english"][index]
        
        raise ValueError(f"No statement found for language {language} at index {index}")


# =============================================================================
# Specialized Fixtures
# =============================================================================

class QuarantineTestFixtures:
    """Fixtures specifically for quarantine behavior testing."""
    
    @staticmethod
    def create_failing_agent_mock() -> MagicMock:
        """Create mock agent that fails consistently."""
        agent = MagicMock()
        agent.side_effect = asyncio.TimeoutError("Agent timeout")
        return agent
    
    @staticmethod
    def create_quarantined_response(participant_name: str, neutral_message: str = None) -> str:
        """Create quarantined response string."""
        if neutral_message is None:
            neutral_message = f"{participant_name} is temporarily unavailable"
        return f"__QUARANTINED__{neutral_message}"


class ConstraintCorrectionFixtures:
    """Fixtures for constraint correction testing."""
    
    @staticmethod
    def create_ballots_needing_correction() -> List[PrincipleChoice]:
        """Create ballots that need constraint corrections."""
        return [
            PrincipleChoice.create_for_parsing(
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                None,  # Missing constraint
                CertaintyLevel.SURE
            ),
            PrincipleChoice.create_for_parsing(
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                None,  # Missing constraint
                CertaintyLevel.SURE
            )
        ]
    
    @staticmethod
    def create_corrected_ballots(constraint_amount: int = 15000) -> List[PrincipleChoice]:
        """Create ballots with corrections applied."""
        return [
            PrincipleChoice.create_for_parsing(
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount,
                CertaintyLevel.SURE
            ),
            PrincipleChoice.create_for_parsing(
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                constraint_amount,
                CertaintyLevel.SURE
            )
        ]


# =============================================================================
# Export convenience functions
# =============================================================================

# Convenience functions for easy import
create_test_utility_agent = Phase2ParsingFixtures.create_test_utility_agent
create_mock_participant = Phase2ParsingFixtures.create_mock_participant_agent  
create_test_context = Phase2ParsingFixtures.create_test_participant_context
create_test_config = Phase2ParsingFixtures.create_test_experiment_config
create_principle_choice = Phase2ParsingFixtures.create_principle_choice

# Test data exports
VOTE_POSITIVE = POSITIVE_VOTE_STATEMENTS
VOTE_NEGATIVE = NEGATIVE_VOTE_STATEMENTS
BALLOTS = BALLOT_STATEMENTS
CHINESE_BALLOTS = CHINESE_BALLOT_STATEMENTS
SPANISH_BALLOTS = SPANISH_BALLOT_STATEMENTS
CONSTRAINTS = LANGUAGE_SPECIFIC_CONSTRAINTS
PREFERENCES = PREFERENCE_STATEMENTS
AGREEMENTS = AGREEMENT_STATEMENTS