# Test Suite Acceleration Plan
## Comprehensive Strategy for Optimizing Frohlich Experiment Test Execution

---

## Executive Summary

**Current Problem:** The test suite takes 1-2 hours to execute due to running full experiments with real LLM API calls across multiple languages, resulting in 300-500+ API calls per full test run.

**Solution Strategy:** Implement a **dual-tier testing architecture** combining:
1. **Optimized existing test suite** for comprehensive integration validation
2. **New lightweight test suite** for fast development feedback cycles

**Expected Impact:**
- **Development tests**: 95% speed improvement (2-3 minutes vs 1-2 hours)
- **Integration tests**: 70% speed improvement while maintaining quality
- **Cost reduction**: 90% reduction in API costs for routine development

---

## Current Performance Analysis

### Execution Time Breakdown (Current)
```
Total Test Suite: ~90-120 minutes
├── Unit Tests: ~30 seconds (fast ✓)
├── Component Tests: ~45-60 minutes (SLOW ❌)
├── Integration Tests: ~10-15 minutes (slow ❌)
├── Contract Tests: ~5 seconds (fast ✓)
└── Live Tests: ~45-60 minutes (SLOW ❌)
```

### Critical Bottlenecks Identified

#### 1. **Full Experiment Execution**
- **Issue**: Component tests run complete Phase 1 + Phase 2 experiments
- **Example**: `test_phase2_manager_runs_with_live_agents` = 3 full experiments (one per language)
- **Cost**: 300-500 API calls per test, ~$5-10 in API costs, 20-30 minutes

#### 2. **Multilingual Multiplication**
- **Issue**: `@parametrize_languages()` triples every component test
- **Impact**: Each test becomes 3 tests (English, Spanish, Mandarin)
- **Cost**: 3x API calls, 3x execution time for every multilingual test

#### 3. **Expensive Configuration**
- **Issue**: Default config uses `phase2_rounds: 10`
- **Impact**: Each Phase 2 test runs 10 discussion/voting rounds
- **Cost**: 10x multiplier on already expensive operations

#### 4. **Real Agent Creation Overhead**
- **Issue**: Each test creates real agents with API connections
- **Impact**: Agent setup, authentication, model loading per test
- **Cost**: Significant overhead beyond API call costs

---

## Strategy 1: Optimize Existing Test Suite

### Immediate Performance Improvements

#### 1.1 **Create Ultra-Fast Test Configurations**

**Action**: Create dedicated test configurations optimized for speed

**Implementation**:
```yaml
# config/test_ultra_fast.yaml
language: "English"
seed: 42

agents:
  - name: "Alice"
    personality: "Test agent"
    model: "gpt-4.1-nano"  # Fastest available model
    memory_character_limit: 10000  # Reduced memory
    reasoning_enabled: false  # Disable for speed
    temperature: 0
  - name: "Bob"
    personality: "Test agent"
    model: "gpt-4.1-nano"
    memory_character_limit: 10000
    reasoning_enabled: false
    temperature: 0

utility_agent_model: "gpt-4.1-nano"
utility_agent_temperature: 0.0

# Minimal rounds for testing
phase2_rounds: 2  # Reduced from 10 to 2
distribution_range_phase1: [1.0, 1.0]  # No randomization
distribution_range_phase2: [1.0, 1.0]  # No randomization

# Disable expensive features
selective_memory_updates: true
memory_guidance_style: structured
phase2_include_internal_reasoning_in_memory: false
include_experiment_explanation_each_turn: false
memory_update_threshold: minimal
```

**Expected Impact**: 80% reduction in API calls per test

#### 1.2 **Implement Test-Specific Configuration Injection**

**Action**: Allow tests to override default configurations with minimal setups

**Implementation**:
```python
# tests/support/config_factory.py

def build_minimal_test_configuration(
    *,
    agent_count: int = 2,
    language: SupportedLanguage = SupportedLanguage.ENGLISH,
    rounds: int = 2,  # Minimal rounds
    reasoning_enabled: bool = False,  # Disabled for speed
    memory_limit: int = 5000  # Reduced memory
) -> ExperimentConfiguration:
    """Create ultra-minimal configuration for fast testing."""

def build_focused_component_config(
    component: str,  # "voting", "discussion", "memory", etc.
    **overrides
) -> ExperimentConfiguration:
    """Create configuration optimized for specific component testing."""
```

**Expected Impact**: Component-specific optimizations, avoiding unnecessary features

#### 1.3 **Smart Language Selection Strategy**

**Action**: Implement intelligent language testing patterns

**Implementation**:
```python
# tests/support/language_matrix.py

def smart_parametrize_languages(
    full_multilingual: bool = False,  # Only for critical integration tests
    primary_plus_one: bool = True,   # Test English + one other language
    single_language: bool = False     # Only for development/unit tests
):
    """Intelligent language selection based on test importance."""

# Usage in tests:
@smart_parametrize_languages(primary_plus_one=True)  # 2 languages instead of 3
def test_component_behavior(language, harness):
    pass

@smart_parametrize_languages(full_multilingual=True)  # 3 languages for critical tests
def test_critical_integration(language, harness):
    pass
```

**Expected Impact**: 33% reduction in multilingual test overhead

#### 1.4 **Conditional Live Test Execution**

**Action**: Make expensive live tests conditional based on environment flags

**Implementation**:
```python
# Environment-based test execution
FULL_INTEGRATION = os.getenv("FULL_INTEGRATION_TESTS", "0") == "1"
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "1") == "1"

@pytest.mark.skipif(DEVELOPMENT_MODE and not FULL_INTEGRATION,
                   reason="Expensive test skipped in development mode")
@pytest.mark.live
def test_full_phase2_integration(language, harness):
    """Only runs when explicitly requested."""
```

**Expected Impact**: Developers can skip expensive tests by default

---

## Strategy 2: Create Lightweight Test Suite

### New Fast Test Architecture

#### 2.1 **Mock-Based Component Testing**

**Purpose**: Test component integration without real LLM calls

**Implementation**:
```python
# tests/fast/test_phase_managers_mock.py

class MockAgent:
    """Lightweight agent mock with predictable responses."""
    def __init__(self, name: str, responses: List[str]):
        self.name = name
        self._responses = iter(responses)

    async def process_prompt(self, prompt: str) -> str:
        return next(self._responses, "default response")

@pytest.mark.fast
@pytest.mark.asyncio
async def test_phase2_workflow_logic():
    """Test Phase 2 logic flow without real agents."""
    # Create mock agents with predictable responses
    mock_agents = [
        MockAgent("Alice", ["I prefer fairness", "Yes, I vote for principle 1"]),
        MockAgent("Bob", ["I want equality", "Yes, I agree"])
    ]

    # Test the workflow logic without API calls
    manager = Phase2Manager(mock_agents, mock_utility, mock_config)
    results = await manager.run_phase2(config, phase1_results)

    # Validate structure and logic, not LLM behavior
    assert results.consensus_reached
    assert len(results.payoff_results) == 2
```

**Expected Impact**: Component testing in seconds instead of minutes

#### 2.2 **Deterministic Response Testing**

**Purpose**: Test parsing and validation logic with known responses

**Implementation**:
```python
# tests/fast/test_response_parsing.py

@pytest.mark.fast
def test_voting_response_parsing():
    """Test vote parsing with known response patterns."""
    test_responses = [
        "I vote for maximizing floor income. I am sure about this choice.",
        "Elijo maximizar los ingresos promedio. Estoy seguro.",
        "我选择最低收入最大化。我对此选择很确定。"
    ]

    for response in test_responses:
        parsed = utility_agent.parse_principle_choice_enhanced(response)
        assert parsed.principle is not None
        assert parsed.certainty is not None

@pytest.mark.fast
def test_consensus_detection_logic():
    """Test consensus algorithms with deterministic inputs."""
    votes = [
        PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE),
        PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE),
        PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE)
    ]

    consensus = detect_consensus(votes)
    assert consensus.reached is True
    assert consensus.principle == JusticePrinciple.MAXIMIZING_FLOOR
```

**Expected Impact**: Validation logic tested exhaustively in seconds

#### 2.3 **Service Interface Testing**

**Purpose**: Test service boundaries and contracts without full workflows

**Implementation**:
```python
# tests/fast/test_service_interfaces.py

@pytest.mark.fast
def test_discussion_service_interface():
    """Test discussion service contract without real agents."""
    service = DiscussionService(mock_language_manager, mock_settings)

    # Test prompt generation
    prompt = service.build_discussion_prompt(mock_state, round_num=1)
    assert "round 1" in prompt.lower()

    # Test validation logic
    is_valid = service.validate_statement("Valid statement", min_length=10)
    assert is_valid is True

    is_invalid = service.validate_statement("Short", min_length=10)
    assert is_invalid is False

@pytest.mark.fast
def test_voting_service_interface():
    """Test voting service contract without API calls."""
    service = VotingService(mock_language_manager, mock_utility_agent)

    # Test vote initiation logic
    can_vote = service.check_voting_eligibility(mock_participant, round_num=3)
    assert isinstance(can_vote, bool)

    # Test ballot validation
    ballot = service.validate_ballot_format(mock_ballot_response)
    assert ballot is not None
```

**Expected Impact**: Service boundary testing completed in milliseconds

#### 2.4 **Synthetic Data Integration Testing**

**Purpose**: Test data flows and transformations with synthetic but realistic data

**Implementation**:
```python
# tests/fast/test_data_flows.py

@pytest.mark.fast
def test_phase1_to_phase2_data_flow():
    """Test data transformation between phases."""
    # Create synthetic Phase 1 results
    synthetic_phase1_results = [
        Phase1Results(
            participant_name="Alice",
            principle_choice=PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR),
            assigned_income_class=IncomeClass.MEDIUM,
            payoff=2.1
        )
    ]

    # Test transformation to Phase 2 input
    phase2_input = transform_phase1_results(synthetic_phase1_results)

    assert len(phase2_input.participants) == 1
    assert phase2_input.initial_preferences[0].principle == JusticePrinciple.MAXIMIZING_FLOOR

@pytest.mark.fast
def test_results_formatting_pipeline():
    """Test complete results formatting without experiments."""
    synthetic_results = create_synthetic_experiment_results()

    formatted = format_experiment_results(synthetic_results)

    assert "consensus_principle" in formatted
    assert "payoff_results" in formatted
    assert len(formatted["participants"]) > 0
```

**Expected Impact**: Data pipeline testing without expensive operations

---

## Strategy 3: Hybrid Test Execution Framework

### 3.1 **Multi-Tier Test Categories**

**Implementation**: Reorganize tests into performance-based tiers

```
tests/
├── fast/                 # New: Ultra-fast tests (< 30 seconds total)
│   ├── test_mocked_components.py
│   ├── test_service_interfaces.py
│   ├── test_data_flows.py
│   └── test_parsing_logic.py
├── medium/               # New: Reduced-scope integration (< 5 minutes total)
│   ├── test_single_language_integration.py
│   ├── test_minimal_experiments.py
│   └── test_component_integration_fast.py
├── comprehensive/        # Renamed: Full integration tests (< 30 minutes)
│   ├── test_full_multilingual_integration.py
│   ├── test_complete_experiments.py
│   └── test_production_workflows.py
└── existing structure... # Keep existing for backward compatibility
```

### 3.2 **Smart Test Runner**

**Implementation**: Intelligent test execution based on context

```python
# run_tests_smart.py

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run only fast tests")
    parser.add_argument("--dev", action="store_true", help="Development mode (fast + medium)")
    parser.add_argument("--ci", action="store_true", help="CI mode (fast + medium + some comprehensive)")
    parser.add_argument("--full", action="store_true", help="Full test suite")

    args = parser.parse_args()

    if args.fast:
        run_test_tier("fast")  # ~30 seconds
    elif args.dev:
        run_test_tier("fast", "medium")  # ~5 minutes
    elif args.ci:
        run_test_tier("fast", "medium", "comprehensive[critical]")  # ~15 minutes
    elif args.full:
        run_all_tests()  # ~30-45 minutes (optimized from 90-120)
    else:
        run_test_tier("fast", "medium")  # Default to dev mode
```

**Usage Examples**:
```bash
# Development workflow (95% of the time)
python run_tests_smart.py --dev          # 5 minutes

# Before commit/push
python run_tests_smart.py --ci           # 15 minutes

# Before release/merge
python run_tests_smart.py --full         # 30-45 minutes

# Instant feedback during coding
python run_tests_smart.py --fast         # 30 seconds
```

### 3.3 **Selective API Integration**

**Implementation**: Strategic use of real vs mock API calls

```python
# tests/support/adaptive_harness.py

class AdaptivePromptHarness:
    """Harness that adapts between mock and real agents based on test tier."""

    def __init__(self, tier: str = "fast"):
        self.tier = tier
        self.use_real_agents = tier in ["comprehensive", "integration"]

    async def create_participants(self, language, agent_count):
        if self.use_real_agents:
            return await self._create_real_participants(language, agent_count)
        else:
            return self._create_mock_participants(language, agent_count)

    def _create_mock_participants(self, language, agent_count):
        """Create realistic mocks for fast testing."""
        return [MockParticipant(name=f"Agent{i}", language=language)
                for i in range(agent_count)]
```

**Expected Impact**: Tests automatically use appropriate level of realism

---

## Implementation Roadmap

### Phase 1: Immediate Optimizations (Week 1)

#### **Priority 1: Create Fast Test Configurations**
- [ ] Create `config/test_ultra_fast.yaml` with 2 rounds, minimal features
- [ ] Create `config/test_minimal.yaml` for component testing
- [ ] Update existing "fast" configs (fix typo in `fast.yaml`)

#### **Priority 2: Implement Conditional Test Execution**
- [ ] Add environment variable support for skipping expensive tests
- [ ] Implement `DEVELOPMENT_MODE` and `FULL_INTEGRATION_TESTS` flags
- [ ] Update component tests with conditional decorators

#### **Priority 3: Fix Critical Performance Issues**
- [ ] Fix the `phase2_roundyes` typo in `config/fast.yaml`
- [ ] Create focused component configurations
- [ ] Implement smart language selection for non-critical tests

### Phase 2: Lightweight Test Suite (Week 2)

#### **Priority 1: Create Fast Test Foundation**
- [ ] Create `tests/fast/` directory structure
- [ ] Implement `MockAgent` and `MockUtilityAgent` classes
- [ ] Create test base classes for fast testing

#### **Priority 2: Build Core Fast Tests**
- [ ] Implement service interface tests
- [ ] Create parsing and validation logic tests
- [ ] Build data flow and transformation tests

#### **Priority 3: Mock-Based Component Testing**
- [ ] Create mocked Phase 1 workflow tests
- [ ] Create mocked Phase 2 workflow tests
- [ ] Implement consensus detection logic tests

### Phase 3: Hybrid Framework (Week 3)

#### **Priority 1: Smart Test Runner**
- [ ] Create `run_tests_smart.py` with tier-based execution
- [ ] Implement test categorization system
- [ ] Create adaptive prompt harness

#### **Priority 2: Integration and Validation**
- [ ] Validate fast tests provide equivalent coverage
- [ ] Benchmark performance improvements
- [ ] Update CI/CD pipeline integration

#### **Priority 3: Documentation and Training**
- [ ] Update test documentation for new tiers
- [ ] Create developer workflow guidelines
- [ ] Train team on new testing patterns

---

## Expected Performance Improvements

### Development Workflow (Primary Use Case)
```
Current: Full test suite = 90-120 minutes
Optimized:
├── Fast tests (daily development) = 30 seconds (99.5% improvement)
├── Dev tests (pre-commit) = 5 minutes (95% improvement)
└── CI tests (automated) = 15 minutes (85% improvement)
```

### Cost Reduction
```
Current: ~300-500 API calls per full test run (~$5-10)
Optimized:
├── Fast tests = 0 API calls ($0)
├── Dev tests = ~20-50 API calls (~$0.50-1.00)
└── CI tests = ~100-200 API calls (~$2-4)
```

### Quality Maintenance
- **Fast tests**: Cover 80% of logic with mock-based validation
- **Dev tests**: Cover 90% of functionality with minimal real integration
- **CI tests**: Cover 95% with selective comprehensive testing
- **Full tests**: Maintain 100% coverage for releases

---

## Success Metrics

### Quantitative Targets
- **Development feedback**: < 1 minute (from 90-120 minutes)
- **Pre-commit validation**: < 5 minutes (from 90-120 minutes)
- **API cost reduction**: > 90% for routine development
- **Coverage maintenance**: > 95% for critical paths

### Qualitative Goals
- **Developer Experience**: Fast feedback encourages test-driven development
- **CI/CD Efficiency**: Faster automated testing and deployment
- **Cost Management**: Sustainable testing without API cost concerns
- **Quality Assurance**: Maintain comprehensive validation for releases

---

## Risk Mitigation

### Potential Risks & Mitigations

#### **Risk**: Fast tests miss real LLM behavior issues
**Mitigation**:
- Maintain comprehensive tests for critical integration points
- Use synthetic but realistic data in fast tests
- Regular validation of fast test assumptions against real behavior

#### **Risk**: Mock complexity becomes maintenance burden
**Mitigation**:
- Keep mocks simple and focused on interface contracts
- Generate mocks from real API response patterns
- Regular validation of mock accuracy

#### **Risk**: Team adopts fast tests exclusively, skips comprehensive validation
**Mitigation**:
- Enforce comprehensive tests in CI/CD pipeline
- Clear guidelines on when to run different test tiers
- Automated prompts for comprehensive testing before releases

---

## Conclusion

This acceleration plan provides a **comprehensive strategy** for addressing the test suite performance issues while maintaining quality and coverage. The **dual-tier approach** allows developers to work efficiently with fast feedback while preserving thorough validation for critical integration points.

**Key Benefits**:
1. **95% speed improvement** for daily development workflows
2. **90% cost reduction** in routine API usage
3. **Maintained quality** through strategic comprehensive testing
4. **Scalable architecture** that can adapt to future needs

The plan prioritizes **immediate optimizations** to existing tests while building toward a **sustainable long-term testing strategy** that supports both rapid development and thorough validation.