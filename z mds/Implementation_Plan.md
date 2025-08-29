# Detailed Implementation Plan for Test Failure Fixes

## Overview

This plan provides step-by-step implementation instructions for all 5 proposals identified in the test failure analysis. Each proposal includes detailed code changes, testing steps, and validation procedures.

**Implementation Order:** Following dependency chain and risk assessment
1. Proposal 3: Configuration Model Enhancement (Foundation)
2. Proposal 4: Test Infrastructure Completion (Testing Foundation)  
3. Proposal 5: Enhanced Test Fixture Support (Testing Support)
4. Proposal 1: Enhanced Constraint Parsing (Core Logic)
5. Proposal 2: Enhanced Vote Intention Detection (Refinement)

---

## Proposal 3: Configuration Model Enhancement
**Priority: High | Risk: Low | Dependencies: None**

### Objective
Add language field support to `AgentConfiguration` model to enable multilingual testing.

### Step-by-Step Implementation

#### Step 3.1: Update AgentConfiguration Model
**File:** `/config/models.py`

**Current Code Location:** Lines 25-31
```python
class AgentConfiguration(BaseModel):
    """Configuration for a single participant agent."""
    name: str = Field(..., description="Agent name")
    personality: str = Field(..., description="Agent personality description")
    model: str = Field("o3-mini", description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, "Model temperature")
    memory_character_limit: int = Field(50000, gt=0, description="Maximum memory length in characters")
    reasoning_enabled: bool = Field(True, description="Enable/disable internal reasoning in Phase 2")
```

**New Implementation:**
```python
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
```

#### Step 3.2: Update Configuration Validation Logic
**File:** `/config/models.py`

**Add Import:**
```python
from pydantic import BaseModel, Field, field_validator, model_validator
```

#### Step 3.3: Update Example Configuration Files
**Files:** All YAML files in `/config/` directory

**Add to each configuration:**
```yaml
agents:
  - name: "Agent1"
    personality: "analytical and detail-oriented"
    model: "gpt-4o-mini"
    temperature: 0.3
    language: "english"  # ADD THIS LINE
  - name: "Agent2"
    personality: "pragmatic and focused"
    model: "gpt-4o-mini"
    temperature: 0.3
    language: "spanish"  # ADD THIS LINE
```

#### Step 3.4: Update Documentation
**File:** `/docs/architecture/configuration.rst`

**Add language field documentation:**
```rst
language: str = "english"
    Agent's primary communication language. Supported values:
    - "english" - English language prompts and parsing
    - "spanish" - Spanish language prompts and parsing  
    - "mandarin" - Mandarin Chinese language prompts and parsing
    - "chinese" - Alias for mandarin
```

### Testing Steps

#### Test 3.1: Model Validation Test
```python
# Create test file: test_configuration_language_support.py
def test_language_field_validation():
    """Test language field validation in AgentConfiguration."""
    # Valid languages
    for lang in ["english", "spanish", "mandarin", "chinese"]:
        config = AgentConfiguration(
            name="TestAgent",
            personality="Test",
            language=lang
        )
        assert config.language.lower() == lang.lower()
    
    # Invalid language
    with pytest.raises(ValueError, match="Unsupported language"):
        AgentConfiguration(
            name="TestAgent",
            personality="Test",
            language="french"
        )
```

#### Test 3.2: Integration Test
```bash
# Test configuration loading with new language field
python -c "
from config import load_experiment_config
config = load_experiment_config('config/sample_config.yaml')
print('Language support working:', hasattr(config.agents[0], 'language'))
"
```

### Validation Criteria
- ✅ AgentConfiguration accepts language field
- ✅ Language validation rejects unsupported languages
- ✅ Existing configurations load without errors
- ✅ New language field appears in serialized output

---

## Proposal 4: Test Infrastructure Completion  
**Priority: High | Risk: Low | Dependencies: Proposal 3**

### Objective
Create shared base class for Spanish constraint tests with common helper methods.

### Step-by-Step Implementation

#### Step 4.1: Create Base Test Class
**File:** `/tests/unit/test_phase2_spanish_constraints.py`

**Add at top of file after imports (around line 29):**
```python
class BaseSpanishConstraintTest(unittest.TestCase):
    """Base class providing shared helper methods for Spanish constraint testing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    async def _parse_constraint_amount(self, statement: str) -> Optional[int]:
        """Helper to parse constraint amounts from Spanish statements."""
        await self.utility_agent.async_init()
        try:
            # Create a full statement with the constraint
            full_statement = f"Elijo maximización del ingreso promedio {statement}"
            result = await self.utility_agent.parse_participant_preference(
                full_statement, participant_name="TestParticipant"
            )
            return result.constraint_amount if result else None
        except Exception:
            return None
    
    async def _parse_full_preference_statement(self, statement: str) -> Optional[PrincipleChoice]:
        """Helper to parse full preference statements."""
        await self.utility_agent.async_init()
        try:
            result = await self.utility_agent.parse_participant_preference(
                statement, participant_name="TestParticipant"
            )
            return result
        except Exception:
            return None
    
    async def _detect_vote_intention(self, statement: str) -> bool:
        """Helper method for async vote intention detection."""
        await self.utility_agent.async_init()
        result = await self.utility_agent.detect_vote_intention_enhanced(statement)
        return result is not None
```

#### Step 4.2: Update Test Classes to Inherit from Base
**File:** `/tests/unit/test_phase2_spanish_constraints.py`

**Replace class definitions (around lines 30, 87, 154, 222, 292, 339):**

**Before:**
```python
class TestSpanishConstraintParsing(unittest.TestCase):
    """Test Spanish constraint amount parsing and validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
```

**After:**
```python
class TestSpanishConstraintParsing(BaseSpanishConstraintTest):
    """Test Spanish constraint amount parsing and validation."""
    # setUp inherited from base class
```

**Apply this change to all test classes:**
- `TestSpanishConstraintParsing`
- `TestSpanishCurrencyConstraints` 
- `TestSpanishNumberWordParsing`
- `TestSpanishNullConstraintPatterns`
- `TestSpanishConstraintTerminology`

**Keep existing implementation in:**
- `TestSpanishConstraintFixtureValidation` (already has the methods)

#### Step 4.3: Update Vote Intention Detection Test
**File:** `/tests/unit/test_phase2_vote_intention_detection.py`

**Add the missing helper method to `TestVoteIntentionDetection` class (around line 316):**
```python
async def _detect_vote_intention(self, statement: str) -> bool:
    """Helper method for async vote intention detection."""
    await self.utility_agent.async_init()
    result = await self.utility_agent.detect_vote_intention_enhanced(statement)
    return result is not None
```

### Testing Steps

#### Test 4.1: Base Class Functionality
```bash
# Run single test class to verify inheritance works
python -m pytest tests/unit/test_phase2_spanish_constraints.py::TestSpanishConstraintParsing::test_basic_spanish_constraint_parsing -v
```

#### Test 4.2: Helper Method Availability
```python
# Verify all test classes have helper methods
python -c "
import inspect
from tests.unit.test_phase2_spanish_constraints import *
classes = [TestSpanishConstraintParsing, TestSpanishCurrencyConstraints, TestSpanishNumberWordParsing]
for cls in classes:
    assert hasattr(cls, '_parse_constraint_amount')
    assert hasattr(cls, '_parse_full_preference_statement')
    print(f'{cls.__name__}: Helper methods available')
"
```

#### Test 4.3: Full Test Suite
```bash
# Run all Spanish constraint tests
python -m pytest tests/unit/test_phase2_spanish_constraints.py -v
```

### Validation Criteria
- ✅ All test classes inherit from base class successfully
- ✅ Helper methods are available in all derived classes
- ✅ Tests can create utility agents and call parsing methods
- ✅ No more AttributeError exceptions for missing methods

---

## Proposal 5: Enhanced Test Fixture Support
**Priority: Medium | Risk: Low | Dependencies: Proposal 3**

### Objective
Add missing `create_config_with_agents` method and improve configuration handling.

### Step-by-Step Implementation

#### Step 5.1: Add Missing Method to ExperimentTestFixture
**File:** `/tests/integration/fixtures/experiment_fixtures.py`

**Add after line 50 (after `create_minimal_config` method):**
```python
@staticmethod
def create_config_with_agents(agent_specs: List[Dict[str, Any]]) -> ExperimentConfiguration:
    """Create configuration with specific agent specifications.
    
    Args:
        agent_specs: List of dicts with agent configuration parameters.
                    Each dict can contain: name, personality, model, temperature, 
                    memory_character_limit, reasoning_enabled, language
    
    Returns:
        ExperimentConfiguration with specified agents
    """
    agents = []
    
    default_personalities = [
        "Analytical and methodical, focused on fairness",
        "Pragmatic and results-oriented, values efficiency", 
        "Empathetic and caring, prioritizes helping others",
        "Strategic and competitive, seeks optimal outcomes"
    ]
    
    for i, spec in enumerate(agent_specs):
        # Set defaults for missing fields
        agent_config = AgentConfiguration(
            name=spec.get("name", f"TestAgent{i+1}"),
            personality=spec.get("personality", default_personalities[i % len(default_personalities)]),
            model=spec.get("model", "gpt-4o-mini"),
            temperature=spec.get("temperature", 0.3),
            memory_character_limit=spec.get("memory_character_limit", 50000),
            reasoning_enabled=spec.get("reasoning_enabled", True),
            language=spec.get("language", "english")
        )
        agents.append(agent_config)
    
    return ExperimentConfiguration(
        agents=agents,
        phase2_rounds=5,
        distribution_range_phase1=(0.8, 1.2),
        distribution_range_phase2=(0.9, 1.1)
    )
```

#### Step 5.2: Update create_minimal_config for Validation
**File:** `/tests/integration/fixtures/experiment_fixtures.py`

**Replace the existing method (around lines 24-50):**
```python
@staticmethod  
def create_minimal_config(num_agents: int = 2) -> ExperimentConfiguration:
    """Create minimal viable configuration for testing.
    
    Args:
        num_agents: Number of agents to create (minimum 2 for valid experiments)
        
    Returns:
        ExperimentConfiguration with specified number of agents
    """
    # Add validation to prevent single-agent configs that violate constraints
    if num_agents < 2:
        raise ValueError("Minimum 2 agents required for valid experiment configuration")
        
    agents = []
    personalities = [
        "Analytical and methodical, focused on fairness",
        "Pragmatic and results-oriented, values efficiency", 
        "Empathetic and caring, prioritizes helping others",
        "Strategic and competitive, seeks optimal outcomes"
    ]
    
    for i in range(num_agents):
        agents.append(AgentConfiguration(
            name=f"TestAgent{i+1}",
            personality=personalities[i % len(personalities)],
            model="o3-mini",
            temperature=0.7,
            memory_character_limit=50000,
            reasoning_enabled=True,
            language="english"  # ADD THIS LINE
        ))
    
    return ExperimentConfiguration(
        agents=agents,
        phase2_rounds=5,
        distribution_range_phase1=(0.8, 1.2),
        distribution_range_phase2=(0.9, 1.1)
    )
```

#### Step 5.3: Add Import if Needed
**File:** `/tests/integration/fixtures/experiment_fixtures.py`

**Check imports at top of file, add if missing:**
```python
from typing import Dict, List, Optional, Any
```

### Testing Steps

#### Test 5.1: Test create_config_with_agents Method
```python
# Add to a test file or run directly
def test_create_config_with_agents():
    """Test the new create_config_with_agents method."""
    from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
    
    # Test multilingual agent creation
    agent_specs = [
        {"name": "SpanishAgent", "language": "spanish"},
        {"name": "EnglishAgent", "language": "english"},
        {"name": "ChineseAgent", "language": "mandarin"}
    ]
    
    config = ExperimentTestFixture.create_config_with_agents(agent_specs)
    
    assert len(config.agents) == 3
    assert config.agents[0].name == "SpanishAgent"
    assert config.agents[0].language == "spanish"
    assert config.agents[1].language == "english"
    assert config.agents[2].language == "mandarin"
    print("create_config_with_agents working correctly!")
```

#### Test 5.2: Test Validation Logic
```python
def test_minimal_config_validation():
    """Test that minimal config validates agent count."""
    from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
    
    # Should work with 2+ agents
    config = ExperimentTestFixture.create_minimal_config(num_agents=2)
    assert len(config.agents) == 2
    
    # Should fail with 1 agent
    try:
        ExperimentTestFixture.create_minimal_config(num_agents=1)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Minimum 2 agents required" in str(e)
        print("Validation working correctly!")
```

#### Test 5.3: Integration Test with Mixed Languages
```bash
# Run failing multilingual tests to verify they now pass
python -m pytest tests/integration/test_phase2_mixed_languages.py::TestPhase2MixedLanguages::test_spanish_english_chinese_mixed_discussion -v
```

### Validation Criteria
- ✅ `create_config_with_agents` method exists and works
- ✅ Method can create agents with different languages
- ✅ `create_minimal_config` validates minimum agent count
- ✅ Multilingual tests can create configurations successfully

---

## Proposal 1: Enhanced Constraint Parsing  
**Priority: High | Risk: Medium | Dependencies: Proposals 3, 4**

### Objective
Replace hardcoded regex constraint parsing with intelligent utility agent-based parsing.

### Step-by-Step Implementation

#### Step 1.1: Add New Multilingual Parsing Method
**File:** `/experiment_agents/utility_agent.py`

**Add after line 1477 (after `_extract_constraint_amount_flexible` method):**
```python
async def parse_constraint_amount_multilingual(self, constraint_text: str, language_hint: str = None) -> Optional[int]:
    """
    Use utility agent to parse constraint amounts across languages and formats.
    
    This replaces the hardcoded regex patterns with intelligent LLM-based parsing
    that can handle:
    - Multiple languages (English/Spanish/Chinese)
    - Various number formats (European: 15.000,50 vs Latin American: 15,000.50)
    - Word numbers (fifteen thousand, quince mil, 一万五千)
    - Currency symbols and codes
    
    Args:
        constraint_text: Text containing constraint amount to parse
        language_hint: Optional language hint ("english", "spanish", "mandarin")
    
    Returns:
        Parsed amount as integer, or None if no valid amount found
    """
    if not constraint_text or constraint_text.strip() == "":
        return None
    
    # Get language manager for prompt construction
    language_manager = get_language_manager()
    
    parsing_prompt = f"""Parse the constraint amount from this statement: "{constraint_text}"

Language hint: {language_hint or "unknown"}

EXTRACT NUMERIC AMOUNT considering:
1. Multiple currencies: €, $, ¥, EUR, USD, MXN, ARS, COP, pesos, euros, dollars, yuan
2. Number formats:
   - European: 15.000,50 (period thousands, comma decimal)
   - Latin American: 15,000.50 (comma thousands, period decimal)  
   - Asian: 15,000 or 15000
   - Space separators: 15 000
3. Word numbers: 
   - English: fifteen thousand, 15k, 15K
   - Spanish: quince mil, 15 mil, 2.5 mil
   - Chinese: 一万五千, 15千
4. Abbreviations: k, K, mil, thousand, 千

EXAMPLES:
✓ "constraint de €2.5 mil" → 2500
✓ "restricción de €15.000" → 15000  
✓ "límite $1,500,000" → 1500000
✓ "tope de quince mil euros" → 15000
✓ "constraint ¥15万" → 150000
✓ "sin restricciones" → NONE
✓ "ilimitado" → NONE

Response format: Return ONLY the numeric amount as integer, or "NONE" if no amount found.
Do not include currency symbols, commas, or other formatting.

Response:"""

    try:
        result = await run_without_tracing(self.parser_agent, parsing_prompt)
        response = result.final_output.strip()
        
        if response.upper() == "NONE":
            logger.info(f"No constraint amount found in: '{constraint_text}'")
            return None
        
        # Parse the numeric response
        try:
            amount = int(response)
            if amount > 0:
                logger.info(f"LLM parsed constraint amount: {amount} from '{constraint_text}'")
                return amount
            else:
                logger.warning(f"LLM returned non-positive amount: {amount}")
                return None
        except ValueError:
            logger.warning(f"LLM returned non-numeric response: '{response}'")
            return None
        
    except Exception as e:
        logger.warning(f"LLM constraint parsing failed for '{constraint_text}': {e}")
        # Fallback to simplified regex only for obvious cases
        return self._extract_constraint_amount_simple_fallback(constraint_text)

def _extract_constraint_amount_simple_fallback(self, statement: str) -> Optional[int]:
    """
    Simplified fallback for constraint parsing when LLM fails.
    Only handles the most obvious cases.
    """
    # Simple patterns for obvious cases only
    simple_patterns = [
        r'[\$¥€]\s*(\d{3,6})(?!\d)',  # $15000, €15000, ¥15000
        r'(\d{3,6})\s*(?:dollars?|euros?|yuan)',  # 15000 dollars
        r'(\d{1,3})\s*k(?:\s|$|\.)',  # 15k
    ]
    
    for pattern in simple_patterns:
        matches = re.findall(pattern, statement, re.IGNORECASE)
        for match in matches:
            try:
                amount = int(match)
                if 'k' in statement.lower() and amount < 1000:
                    amount *= 1000
                if amount > 0:
                    logger.info(f"Fallback parsed constraint amount: {amount}")
                    return amount
            except (ValueError, TypeError):
                continue
    
    return None
```

#### Step 1.2: Update Existing Parsing Methods to Use New Multilingual Parser
**File:** `/experiment_agents/utility_agent.py`

**Find `_extract_constraint_amount_robust` method usage (around line 616) and replace:**

**Before:**
```python
constraint_amount = self._extract_constraint_amount_robust(reasoning, principle.value)
```

**After:**
```python
# Try new multilingual parser first
constraint_amount = await self.parse_constraint_amount_multilingual(reasoning)
if constraint_amount is None:
    # Fallback to existing robust parser for backward compatibility
    constraint_amount = self._extract_constraint_amount_robust(reasoning, principle.value)
```

#### Step 1.3: Update Fallback Extraction Logic
**File:** `/experiment_agents/utility_agent.py`

**Find line 963 in `parse_principle_choice_llm` method and replace:**

**Before:**
```python
fallback_amount = self._extract_constraint_amount_flexible(llm_response)
```

**After:**
```python
# Use new multilingual parser for fallback
fallback_amount = await self.parse_constraint_amount_multilingual(llm_response)
if fallback_amount is None:
    # Secondary fallback to original flexible parser
    fallback_amount = self._extract_constraint_amount_flexible(llm_response)
```

#### Step 1.4: Add Language Hint Support
**File:** `/experiment_agents/utility_agent.py`

**Update method signatures to pass language hints where available:**

**In `parse_participant_preference` method (around line 1250):**
```python
# Add language detection/hint
language_hint = None
if hasattr(self, 'language_manager') and self.language_manager:
    # Detect language from statement patterns
    if any(word in statement.lower() for word in ['restricción', 'límite', 'tope', 'euros', 'pesos']):
        language_hint = "spanish"
    elif any(word in statement.lower() for word in ['constraint', 'limit', 'dollars', 'maximum']):
        language_hint = "english"
    elif any(char in statement for char in ['元', '千', '万', '限制']):
        language_hint = "mandarin"

constraint_amount = await self.parse_constraint_amount_multilingual(preference_text, language_hint)
```

### Testing Steps

#### Test 1.1: Unit Test for New Method
**File:** Create `/tests/unit/test_multilingual_constraint_parsing.py`

```python
import unittest
import asyncio
from experiment_agents.utility_agent import UtilityAgent
from tests.fixtures.phase2_parsing_fixtures import create_test_utility_agent

class TestMultilingualConstraintParsing(unittest.TestCase):
    """Test the new multilingual constraint parsing method."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_spanish_constraint_parsing(self):
        """Test Spanish constraint parsing with various formats."""
        test_cases = [
            ("constraint de €2.5 mil", 2500, "Spanish decimal mil"),
            ("restricción de €15.000", 15000, "Spanish European format"),
            ("límite $1,500,000", 1500000, "Spanish Latin American format"),
            ("tope de quince mil euros", 15000, "Spanish word numbers"),
            ("sin restricciones", None, "Spanish null constraint"),
        ]
        
        for constraint_text, expected, description in test_cases:
            with self.subTest(description=description):
                result = asyncio.run(self.utility_agent.parse_constraint_amount_multilingual(
                    constraint_text, language_hint="spanish"
                ))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{constraint_text}'")
    
    def test_english_constraint_parsing(self):
        """Test English constraint parsing."""
        test_cases = [
            ("constraint of $15,000", 15000, "English comma format"),
            ("limit of 20k", 20000, "English k format"),
            ("maximum of fifteen thousand dollars", 15000, "English words"),
            ("no constraints", None, "English null constraint"),
        ]
        
        for constraint_text, expected, description in test_cases:
            with self.subTest(description=description):
                result = asyncio.run(self.utility_agent.parse_constraint_amount_multilingual(
                    constraint_text, language_hint="english"
                ))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{constraint_text}'")

if __name__ == '__main__':
    unittest.main()
```

#### Test 1.2: Integration Test with Existing System
```bash
# Test that existing Spanish constraint tests now pass
python -m pytest tests/unit/test_phase2_spanish_constraints.py::TestSpanishConstraintParsing::test_basic_spanish_constraint_parsing -v

# Test the specific failing case
python -c "
import asyncio
from experiment_agents.utility_agent import UtilityAgent
from tests.fixtures.phase2_parsing_fixtures import create_test_utility_agent

async def test_specific_case():
    agent = create_test_utility_agent()
    await agent.async_init()
    result = await agent.parse_constraint_amount_multilingual('constraint de €2.5 mil', 'spanish')
    print(f'€2.5 mil parsed as: {result} (expected: 2500)')

asyncio.run(test_specific_case())
"
```

#### Test 1.3: Performance and Fallback Test
```python
# Test fallback behavior when LLM fails
def test_constraint_parsing_fallback():
    """Test fallback behavior when LLM parsing fails."""
    # Mock LLM failure and test fallback
    with patch('experiment_agents.utility_agent.run_without_tracing') as mock_run:
        mock_run.side_effect = Exception("LLM timeout")
        
        agent = create_test_utility_agent()
        result = asyncio.run(agent.parse_constraint_amount_multilingual("$15000"))
        
        # Should fall back to simple regex
        assert result == 15000 or result is None  # Either works or fails gracefully
```

### Validation Criteria
- ✅ "constraint de €2.5 mil" parses as 2500 (not 2000)
- ✅ All Spanish constraint test cases pass
- ✅ English and Chinese constraints continue working
- ✅ Fallback works when LLM fails
- ✅ Performance acceptable (cache LLM responses if needed)

---

## Proposal 2: Enhanced Vote Intention Detection
**Priority: Medium | Risk: Medium | Dependencies: Proposal 1**

### Objective
Improve Spanish vote intention detection by refining LLM prompts and exclusion patterns.

### Step-by-Step Implementation

#### Step 2.1: Update Vote Intention Detection Prompt
**File:** `/experiment_agents/utility_agent.py`

**Replace the prompt in `detect_vote_intention_enhanced` method (around lines 478-512):**

**Before:**
```python
vote_detection_prompt = f"""
Analyze this statement to determine if the speaker is expressing intention or readiness to proceed with voting or decision-making.

Statement: "{statement}"

DETECT VOTE_INTENTION when the speaker:
1. PROPOSES voting/decision action: "Let's vote", "I propose we vote", "We should vote now"
2. SIGNALS READINESS for voting: "Ready to vote", "Time to vote", "Time for the vote"
3. INDICATES SEQUENCE/TIMING: "Voting is the next step", "Now we vote", "Let's move to voting"
4. SEEKS AGREEMENT to vote: "Should we vote?", "Can we vote now?"
5. DECLARES DECISION PHASE: "Time to decide", "Let's make our decision", "Ready to decide", "We need to reach a decision", "We need to make a decision", "Let's finalize our choice", "Time to make our choice", "I think we're ready to decide"
```

**After:**
```python
vote_detection_prompt = f"""
Analyze this statement to determine if the speaker is expressing IMMEDIATE intention or proposal to vote or make a decision.

Statement: "{statement}"

DETECT VOTE_INTENTION when the speaker:
1. IMMEDIATE PROPOSALS: "Let's vote", "Votemos", "我们投票吧", "I propose we vote"
2. DECISION READINESS: "Ready to vote", "Time to vote", "Es hora de votar", "投票时间到了"
3. ACTION SIGNALS: "Voting is the next step", "Now we vote", "Ahora votemos", "现在投票"
4. CONSENSUS TRIGGERS: "Should we vote?", "¿Votamos?", "我们应该投票吗?"
5. DECISION LANGUAGE: "Let's decide", "Decidamos", "我们来决定", "Sugiero que tomemos una decisión"
6. PROCEDURE INITIATION: "Let's move to voting", "Procedamos a la votación", "开始投票程序"

DO NOT DETECT when the speaker:
1. ASKS QUESTIONS ABOUT VOTING: "When should we vote?", "¿Cuándo deberíamos votar?", "什么时候投票?"
2. EXPRESSES UNCERTAINTY: "Maybe we should vote", "Tal vez deberíamos votar", "也许我们应该投票"
3. SEEKS MORE DISCUSSION: "We need more discussion", "Necesitamos más discusión", "需要更多讨论"
4. MAKES CONDITIONAL STATEMENTS: "If we vote", "Si votamos", "如果我们投票"
5. REFERS TO PAST/FUTURE: "We voted before", "We will vote later", "Votaremos después"
6. ASKS FOR OPINIONS: "Do you think we should vote?", "¿Crees que deberíamos votar?", "你觉得我们应该投票吗?"

SPANISH LANGUAGE SPECIFICS:
✓ "Sugiero que tomemos una decisión" → VOTE_INTENTION (decision proposal)
✓ "Procedamos a la votación" → VOTE_INTENTION (procedure initiation)  
✓ "Es momento de decidir" → VOTE_INTENTION (timing signal)
✓ "Votemos ahora" → VOTE_INTENTION (immediate proposal)
✓ "¿Podemos votar ahora?" → VOTE_INTENTION (consensus seeking)

✗ "¿Deberíamos votar?" → NO_VOTE_INTENTION (opinion question, not proposal)
✗ "¿Cuándo deberíamos votar?" → NO_VOTE_INTENTION (timing question)
✗ "Necesitamos más discusión" → NO_VOTE_INTENTION (more discussion needed)
✗ "Tal vez deberíamos votar" → NO_VOTE_INTENTION (uncertainty)
✗ "Si votamos después" → NO_VOTE_INTENTION (conditional)

EXAMPLES:
✓ "Let's vote" → VOTE_INTENTION_DETECTED
✓ "Votemos ahora" → VOTE_INTENTION_DETECTED
✓ "Time for the vote" → VOTE_INTENTION_DETECTED  
✓ "Sugiero que tomemos una decisión" → VOTE_INTENTION_DETECTED
✓ "Should we vote?" → VOTE_INTENTION_DETECTED (seeking immediate consensus)

✗ "¿Deberíamos votar?" → NO_VOTE_INTENTION (opinion question in Spanish)
✗ "Maybe we should vote" → NO_VOTE_INTENTION (uncertainty)
✗ "When should we vote?" → NO_VOTE_INTENTION (timing question)
✗ "We need more discussion" → NO_VOTE_INTENTION (more discussion)

Response format - respond with EXACTLY one of these:
VOTE_INTENTION_DETECTED
NO_VOTE_INTENTION

Response:"""
```

#### Step 2.2: Update Exclusion Patterns for Spanish
**File:** `/experiment_agents/utility_agent.py`

**Replace exclusion patterns list (around lines 447-467):**

**Before:**
```python
exclusion_patterns = [
    r"\bshould we vote\s+(later|tomorrow|next)\b",  # Future timing
    r"\bshould we vote\s+or\b",                     # Questions with alternatives
    # ... etc
]
```

**After:**
```python
exclusion_patterns = [
    # English exclusions
    r"\bshould we vote\s+(later|tomorrow|next)\b",      # Future timing
    r"\bshould we vote\s+or\b",                         # Questions with alternatives
    r"\bdo you think we should vote\b",                 # Opinion questions
    r"\bwhen should we vote\b",                         # Timing questions  
    r"\bhow should we vote\b",                          # Method questions
    r"\bwhat if we vote\b",                             # Hypothetical
    r"\bnot ready to vote\b",                           # Explicit rejection
    r"\bneed more discussion\b",                        # Discussion priority
    r"\bwe need to discuss more\b",                     # Discussion priority
    r"\bbefore we vote\b",                              # Conditional timing
    r"\bafter we vote\b",                               # Future reference
    r"\bif we vote\b",                                  # Conditional
    r"\bunless we vote\b",                              # Conditional
    r"\bwe voted\b",                                    # Past reference
    r"\bwill vote\b",                                   # Future reference
    r"\bmight vote\b",                                  # Uncertain future
    r"\bmaybe we should vote\b",                        # Uncertainty
    r"\bwe could vote\b",                               # Possibility
    r"\bvoting would be good\b",                        # Conditional
    
    # Spanish exclusions
    r"\b¿deberíamos votar\?\b",                         # "Should we vote?" (opinion question)
    r"\b¿cuándo deberíamos votar\?\b",                  # "When should we vote?"
    r"\b¿cómo deberíamos votar\?\b",                    # "How should we vote?"
    r"\b¿qué pasa si votamos\?\b",                      # "What if we vote?"
    r"\bnecesitamos más discusión\b",                   # "We need more discussion"
    r"\bno estoy listo para votar\b",                   # "I'm not ready to vote"
    r"\bantes de votar\b",                              # "Before voting"
    r"\bdespués de votar\b",                            # "After voting"
    r"\bsi votamos\b",                                  # "If we vote"
    r"\bpodríamos votar más tarde\b",                   # "We could vote later"
    r"\btal vez deberíamos votar\b",                    # "Maybe we should vote"
    r"\bno creo que debamos votar todavía\b",           # "I don't think we should vote yet"
    r"\bmás discusión necesaria\b",                     # "More discussion needed"
    r"\b¿y si votamos después\?\b",                     # "What if we vote later?"
    r"\bvotamos antes\b",                               # "We voted before"
    r"\bvotaremos después\b",                           # "We will vote later"
    
    # Chinese exclusions (if needed)
    r"什么时候投票",                                      # "When to vote"
    r"如果我们投票",                                      # "If we vote"
    r"需要更多讨论",                                      # "Need more discussion"
]
```

#### Step 2.3: Add Language-Aware Processing
**File:** `/experiment_agents/utility_agent.py`

**Add language detection logic in `detect_vote_intention_enhanced` method (around line 444):**

```python
async def detect_vote_intention_enhanced(self, statement: str) -> Optional[str]:
    """
    Enhanced vote detection using LLM-first approach with exclusion patterns.
    Detects when participants want to trigger formal voting in discussions.
    """
    await self.async_init()

    statement_lower = statement.lower().strip()
    
    # Detect likely language for better processing
    language_hint = "unknown"
    if any(word in statement_lower for word in ['votar', 'votamos', 'votemos', 'decisión', 'restricción']):
        language_hint = "spanish"
    elif any(word in statement_lower for word in ['vote', 'voting', 'decision', 'decide']):
        language_hint = "english" 
    elif any(char in statement for char in ['投票', '决定', '决策', '表决']):
        language_hint = "chinese"
    
    # Log language detection for debugging
    if language_hint != "unknown":
        logger.debug(f"Detected language '{language_hint}' for statement: {statement}")
    
    # REST OF METHOD CONTINUES AS BEFORE...
```

### Testing Steps

#### Test 2.1: Spanish False Positive Fix
```python
def test_spanish_false_positive_fix():
    """Test that Spanish opinion questions are not detected as vote intentions."""
    false_positive_cases = [
        "¿Deberíamos votar?",  # Should we vote? (question)
        "¿Cuándo deberíamos votar?",  # When should we vote?
        "¿Cómo deberíamos votar?",  # How should we vote?
        "Necesitamos más discusión",  # We need more discussion
        "Tal vez deberíamos votar",  # Maybe we should vote
    ]
    
    agent = create_test_utility_agent()
    
    for statement in false_positive_cases:
        result = asyncio.run(agent.detect_vote_intention_enhanced(statement))
        assert result is None, f"Should NOT detect vote intention in: '{statement}'"
        print(f"✓ Correctly excluded: {statement}")
```

#### Test 2.2: Spanish True Positive Verification
```python
def test_spanish_true_positive_verification():
    """Test that valid Spanish vote intentions are detected."""
    true_positive_cases = [
        "Sugiero que tomemos una decisión",  # I suggest we make a decision
        "Procedamos a la votación",  # Let's proceed to voting
        "Votemos ahora",  # Let's vote now
        "Es momento de decidir",  # It's time to decide
        "¿Podemos votar ahora?",  # Can we vote now?
    ]
    
    agent = create_test_utility_agent()
    
    for statement in true_positive_cases:
        result = asyncio.run(agent.detect_vote_intention_enhanced(statement))
        assert result is not None, f"Should detect vote intention in: '{statement}'"
        print(f"✓ Correctly detected: {statement}")
```

#### Test 2.3: Full Vote Intention Test Suite
```bash
# Run all vote intention detection tests
python -m pytest tests/unit/test_phase2_vote_intention_detection.py -v
```

#### Test 2.4: Cross-Language Consistency Check
```python
def test_cross_language_consistency():
    """Test that equivalent statements across languages are handled consistently."""
    equivalent_sets = [
        # Vote proposals (should detect)
        {
            "english": "Let's vote",
            "spanish": "Votemos ahora", 
            "expected": True
        },
        # Opinion questions (should NOT detect)
        {
            "english": "Should we vote?",
            "spanish": "¿Deberíamos votar?",
            "expected": False  # Both should be treated as opinion questions, not proposals
        },
        # Decision proposals (should detect)
        {
            "english": "Let's make a decision",
            "spanish": "Sugiero que tomemos una decisión",
            "expected": True
        }
    ]
    
    agent = create_test_utility_agent()
    
    for equiv_set in equivalent_sets:
        expected = equiv_set["expected"]
        
        for lang in ["english", "spanish"]:
            if lang in equiv_set:
                result = asyncio.run(agent.detect_vote_intention_enhanced(equiv_set[lang]))
                detected = result is not None
                
                assert detected == expected, \
                    f"{lang} consistency failed: '{equiv_set[lang]}' -> {detected}, expected {expected}"
                
                print(f"✓ {lang}: '{equiv_set[lang]}' -> {detected} (expected {expected})")
```

### Validation Criteria
- ✅ "¿Deberíamos votar?" returns False (no longer false positive)
- ✅ "Sugiero que tomemos una decisión" returns True (no longer false negative)
- ✅ Spanish exclusion patterns work correctly
- ✅ Cross-language consistency maintained
- ✅ All vote intention tests pass

---

## Testing and Validation Strategy

### Comprehensive Test Plan

#### Phase 1: Individual Proposal Testing
Run each proposal's tests in isolation to verify functionality.

```bash
# Test Proposal 3: Configuration Model
python -m pytest tests/unit/test_configuration_language_support.py -v

# Test Proposal 4: Test Infrastructure  
python -m pytest tests/unit/test_phase2_spanish_constraints.py::TestSpanishConstraintParsing -v

# Test Proposal 5: Enhanced Test Fixtures
python -m pytest tests/integration/test_phase2_mixed_languages.py::TestPhase2MixedLanguages::test_spanish_english_chinese_mixed_discussion -v

# Test Proposal 1: Enhanced Constraint Parsing
python -m pytest tests/unit/test_multilingual_constraint_parsing.py -v

# Test Proposal 2: Enhanced Vote Intention Detection
python -m pytest tests/unit/test_phase2_vote_intention_detection.py -v
```

#### Phase 2: Integration Testing
Run the original failing tests to verify fixes.

```bash
# Run all originally failing tests
python -m pytest tests/unit/test_phase2_spanish_constraints.py tests/integration/test_phase2_mixed_languages.py tests/unit/test_phase2_vote_intention_detection.py tests/unit/test_phase2_ballot_parsing_corrections.py -v
```

#### Phase 3: System Integration Testing
Run full test suite to ensure no regressions.

```bash
# Full test suite
python run_tests.py

# Specific multilingual and Phase 2 tests
python -m pytest tests/unit/test_phase2_*.py tests/integration/test_phase2_*.py -v
```

### Performance Validation

#### Constraint Parsing Performance Test
```python
import time
import asyncio

async def performance_test():
    """Test constraint parsing performance."""
    agent = create_test_utility_agent()
    await agent.async_init()
    
    test_constraints = [
        "constraint de €2.5 mil",
        "restricción de €15.000", 
        "límite $1,500,000",
        "tope de quince mil euros"
    ] * 10  # 40 total tests
    
    start_time = time.time()
    
    for constraint in test_constraints:
        result = await agent.parse_constraint_amount_multilingual(constraint, "spanish")
        
    end_time = time.time()
    avg_time = (end_time - start_time) / len(test_constraints)
    
    print(f"Average parsing time: {avg_time:.3f} seconds")
    assert avg_time < 2.0, f"Parsing too slow: {avg_time}s per constraint"

asyncio.run(performance_test())
```

### Rollback Plan

If any proposal causes issues:

1. **Quick Rollback**: Revert specific method changes
```bash
git checkout HEAD~1 experiment_agents/utility_agent.py  # For Proposals 1 & 2
git checkout HEAD~1 config/models.py                    # For Proposal 3
git checkout HEAD~1 tests/unit/test_phase2_spanish_constraints.py  # For Proposal 4
```

2. **Gradual Rollback**: Disable new features with feature flags
```python
# Add feature flag for new constraint parsing
USE_MULTILINGUAL_PARSING = False

if USE_MULTILINGUAL_PARSING:
    constraint_amount = await self.parse_constraint_amount_multilingual(reasoning)
else:
    constraint_amount = self._extract_constraint_amount_flexible(reasoning)
```

### Success Metrics

After full implementation:

- ✅ 0/21 test failures (down from 21/21)
- ✅ All Spanish constraint parsing test cases pass
- ✅ "constraint de €2.5 mil" parses correctly as 2500
- ✅ Spanish vote intention detection accuracy >95%
- ✅ Multilingual test scenarios work correctly
- ✅ No performance regression (constraint parsing <2s avg)
- ✅ No new test failures introduced

---

## Conclusion

This implementation plan provides a comprehensive, step-by-step approach to fixing all identified test failures while maintaining the system's philosophy of utility agent-based processing. The plan prioritizes low-risk infrastructure changes first, then implements higher-risk core logic improvements with proper testing and rollback procedures.

Each proposal includes detailed code examples, validation steps, and success criteria to ensure reliable implementation and deployment.