# Code Simplification Master Plan

**Objective**: Systematically identify and eliminate legacy/unused code and overengineered patterns while maintaining all functionality.

**Principles**:
- Simplicity over complexity
- Maintain all existing functionality
- Preserve test coverage
- Keep architecture decisions that add clear value
- Remove abstractions that don't pay for themselves

---

## Phase 1: Discovery & Inventory

### 1.1 Static Code Analysis
**Goal**: Identify unused code, dead imports, unreachable functions

**Areas to scan**:
- [ ] Unused imports across all modules
- [ ] Unreferenced functions and classes
- [ ] Dead code paths (unreachable code)
- [ ] Unused variables and parameters
- [ ] Duplicate code patterns

**Tools/Techniques**:
- `vulture` for dead code detection
- `pylint --disable=all --enable=unused-*` for unused elements
- `grep -r "^def " --include="*.py"` + cross-reference analysis
- Manual import graph analysis
- AST-based usage tracking

**Output**: `phase1_1_unused_code_inventory.md`

---

### 1.2 Architecture Layer Analysis
**Goal**: Identify over-abstraction and unnecessary indirection

**Core Services Layer** (`core/services/`):
- [ ] SpeakingOrderService: Check if randomization strategies are actually used
- [ ] DiscussionService: Validate if all validation rules are necessary
- [ ] VotingService: Review if confirmation phase could be simplified
- [ ] MemoryService: Check if both guidance styles are used in practice
- [ ] CounterfactualsService: Validate complexity of payoff calculations

**Manager Layer** (`core/`):
- [ ] FrohlichExperimentManager: Check for delegated responsibilities that could be inline
- [ ] Phase1Manager: Validate necessity of separate phase manager
- [ ] Phase2Manager: Confirm it's truly just an orchestrator (not hiding logic)
- [ ] TwoStageVotingManager: Check if two-stage is always needed or could be conditional

**Configuration Layer** (`config/`):
- [ ] Check for unused configuration options
- [ ] Validate if all Pydantic models are necessary
- [ ] Review Phase2Settings for unused parameters
- [ ] Check if configuration inheritance is overengineered

**Output**: `phase1_2_architecture_analysis.md`

---

### 1.3 Agent Implementation Review
**Goal**: Identify redundant patterns in agent implementations

**Participant Agents** (`experiment_agents/participant_agent.py`):
- [ ] Check for duplicate prompt construction logic
- [ ] Validate if all agent capabilities are used
- [ ] Review if personality system is actually leveraged
- [ ] Check for unused tool definitions

**Utility Agents** (`experiment_agents/utility_agent.py`):
- [ ] Validate necessity of separate utility agents vs simple parsers
- [ ] Check if validation logic could be regex/rule-based instead of LLM
- [ ] Review if response parsing needs full agent framework

**Output**: `phase1_3_agent_patterns.md`

---

### 1.4 Utility Module Audit
**Goal**: Find overlapping functionality and unnecessary utilities

**Modules to audit**:
- [ ] `utils/language_manager.py`: Check translation coverage vs actual usage
- [ ] `utils/cultural_adaptation.py`: Validate if cultural features are used
- [ ] `utils/experiment_runner.py`: Check for duplicate batch logic
- [ ] `utils/tracing_utils.py`: Validate tracing complexity vs value
- [ ] `utils/protocol_utils.py`: Check if protocol helpers are necessary

**Cross-cutting concerns**:
- [ ] Identify duplicate validation logic across modules
- [ ] Find overlapping data transformation functions
- [ ] Check for reinvented standard library functionality

**Output**: `phase1_4_utility_audit.md`

---

### 1.5 Test Infrastructure Review
**Goal**: Identify unnecessary test complexity and redundant coverage

**Test Layers** (`tests/`):
- [ ] Check for duplicate test cases across layers
- [ ] Validate if all test modes are used (`ultra_fast`, `dev`, `ci`, `full`)
- [ ] Review if mock utilities are overengineered
- [ ] Check for unused test fixtures
- [ ] Validate necessity of all test support modules

**Test Configuration** (`tests/support/`):
- [ ] config_factory.py: Check if all builder methods are used
- [ ] language_matrix.py: Validate complexity vs coverage value
- [ ] mock_utilities.py: Check for unused mock patterns

**Standalone Test Scripts**:
- [ ] Review test_*.py scripts in root directory
- [ ] Check if they're redundant with test suite
- [ ] Determine if they should be integrated or removed

**Output**: `phase1_5_test_complexity.md`

---

### 1.6 Data Model Analysis
**Goal**: Identify over-specified models and unused fields

**Models to review** (`models/`):
- [ ] ExperimentConfiguration: Check for unused configuration fields
- [ ] JusticePrinciple: Validate all attributes are used
- [ ] IncomeDistribution: Check calculation complexity vs needs
- [ ] Response types: Validate if all structured parsing is necessary

**Pydantic overhead**:
- [ ] Check if all validations add value
- [ ] Identify fields that are never accessed
- [ ] Review if simple dataclasses would suffice in some cases

**Output**: `phase1_6_data_models.md`

---

### 1.7 Language & Translation System
**Goal**: Validate multilingual complexity vs actual usage

**Translation System** (`translations/`):
- [ ] Check which language files are actually used
- [ ] Validate if all prompt templates are necessary
- [ ] Review if translation keys have unused variants

**Language Manager**:
- [ ] Check if fallback mechanisms are overengineered
- [ ] Validate number formatting complexity
- [ ] Review if cultural adaptations are actually applied

**Output**: `phase1_7_language_system.md`

---

### 1.8 Voting & Consensus System
**Goal**: Validate voting system complexity vs requirements

**Components to review**:
- [ ] Two-stage voting: Check if both stages are always needed
- [ ] Numerical validation: Review if deterministic parsing is simpler approach
- [ ] Keyword fallback: Check if this is actually used in practice
- [ ] Principle name manager: Validate terminology consistency needs

**Questions to answer**:
- Can voting be simplified to single-stage for some experiments?
- Is the confirmation phase always necessary?
- Could secret ballot be optional based on configuration?

**Output**: `phase1_8_voting_system.md`

---

### 1.9 Memory Management Review
**Goal**: Check if memory system is appropriately complex

**MemoryService analysis**:
- [ ] Validate if both guidance styles ("narrative", "structured") are used
- [ ] Check if truncation logic is overengineered
- [ ] Review if event routing complexity is justified
- [ ] Validate character limit enforcement mechanisms

**Questions to answer**:
- Is unified memory management necessary or could agents manage their own?
- Are the truncation algorithms too complex for the value they provide?
- Could simpler FIFO truncation work just as well?

**Output**: `phase1_9_memory_management.md`

---

## Phase 2: Pattern Detection

### 2.1 Over-Abstraction Patterns
**Goal**: Identify abstraction that doesn't pay for itself

**Patterns to look for**:
- [ ] Single-implementation interfaces/protocols
- [ ] Factory patterns with only one product
- [ ] Strategy patterns with only one strategy
- [ ] Builder patterns for simple objects
- [ ] Wrapper classes that add no functionality

**Output**: `phase2_1_abstraction_patterns.md`

---

### 2.2 Premature Optimization
**Goal**: Find optimization that adds complexity without measured benefit

**Areas to check**:
- [ ] Caching mechanisms that may not be needed
- [ ] Complex data structures where simple ones would work
- [ ] Algorithmic complexity beyond data size requirements
- [ ] Async/parallel code where sequential would suffice

**Output**: `phase2_2_premature_optimization.md`

---

### 2.3 Feature Flags & Dead Branches
**Goal**: Find configuration options and branches no longer used

**Patterns to look for**:
- [ ] Commented-out code blocks
- [ ] Environment variables that are never set
- [ ] Configuration options with only one used value
- [ ] Conditional branches that are never taken

**Output**: `phase2_3_dead_branches.md`

---

### 2.4 Redundant Error Handling
**Goal**: Identify overly defensive code

**Patterns to check**:
- [ ] Multiple layers of try-except for same error
- [ ] Validation that repeats at multiple levels
- [ ] Error messages that are never seen
- [ ] Retry logic that's unnecessarily complex

**Output**: `phase2_4_error_handling.md`

---

## Phase 3: Dependency Analysis

### 3.1 External Dependencies
**Goal**: Identify unused or overweight dependencies

**Analysis tasks**:
- [ ] Parse requirements.txt for all dependencies
- [ ] Cross-reference with actual imports in codebase
- [ ] Identify dependencies used for single features
- [ ] Check for dependencies that overlap in functionality

**Output**: `phase3_1_dependencies.md`

---

### 3.2 Internal Module Dependencies
**Goal**: Find circular dependencies and tight coupling

**Analysis tasks**:
- [ ] Build module dependency graph
- [ ] Identify circular import patterns
- [ ] Find modules with excessive fan-out (imports many things)
- [ ] Find modules with excessive fan-in (imported by many things)

**Tools**:
- `pydeps` for visualization
- Custom AST analysis for detailed coupling metrics

**Output**: `phase3_2_module_coupling.md`

---

## Phase 4: Prioritization & Classification

### 4.1 Impact Assessment
**Goal**: Categorize findings by impact and risk

**Classification matrix**:

| Category | Definition | Priority |
|----------|------------|----------|
| **Dead Code** | Never executed, safe to remove | HIGH |
| **Unused Abstraction** | Single implementation of interface | MEDIUM |
| **Over-Validation** | Redundant checks at multiple layers | MEDIUM |
| **Premature Optimization** | Complexity without measured benefit | LOW |
| **Nice-to-Remove** | Simplifies but requires careful testing | LOW |

**Effort matrix**:

| Effort | Definition | Examples |
|--------|------------|----------|
| **Trivial** | <30 min, low risk | Unused imports, dead variables |
| **Easy** | <2 hours, low risk | Unused functions, simple refactors |
| **Medium** | <1 day, medium risk | Service simplification, model changes |
| **Hard** | >1 day, high risk | Architecture changes, test rewrites |

**Output**: `phase4_1_prioritization_matrix.md`

---

### 4.2 Risk Assessment
**Goal**: Identify what could break if we simplify

**For each finding, assess**:
- [ ] Test coverage in affected area
- [ ] Number of dependent modules
- [ ] Presence in public API vs internal implementation
- [ ] Age/stability of the code
- [ ] Complexity of replacement/removal

**Output**: `phase4_2_risk_assessment.md`

---

## Phase 5: Action Plan

### 5.1 Quick Wins (Week 1)
**Goal**: Remove obviously dead code with minimal risk

**Tasks**:
- [ ] Remove unused imports (automated with `autoflake`)
- [ ] Delete unreferenced functions (after verification)
- [ ] Remove commented-out code blocks
- [ ] Clean up unused variables
- [ ] Delete standalone test scripts if redundant

**Expected impact**: 5-10% code reduction, no functionality change

---

### 5.2 Service Layer Simplification (Week 2-3)
**Goal**: Simplify services while maintaining separation of concerns

**Tasks**:
- [ ] Identify service methods that could be private functions
- [ ] Merge services if responsibilities overlap significantly
- [ ] Simplify service interfaces (fewer parameters)
- [ ] Remove unused configuration options in Phase2Settings
- [ ] Inline trivial delegation methods

**Expected impact**: 15-20% reduction in service layer code

---

### 5.3 Configuration Simplification (Week 3)
**Goal**: Streamline configuration system

**Tasks**:
- [ ] Remove unused configuration fields
- [ ] Flatten nested configuration where possible
- [ ] Merge duplicate validation logic
- [ ] Simplify Pydantic models (use dataclasses if validation not needed)

**Expected impact**: 10-15% reduction in config code

---

### 5.4 Test Infrastructure Streamlining (Week 4)
**Goal**: Maintain coverage while reducing test complexity

**Tasks**:
- [ ] Merge duplicate test cases
- [ ] Simplify mock utilities (remove unused patterns)
- [ ] Consolidate test configuration builders
- [ ] Remove redundant test modes if not actively used
- [ ] Integrate standalone test scripts or remove

**Expected impact**: 20-25% reduction in test support code

---

### 5.5 Utility Consolidation (Week 5)
**Goal**: Reduce utility module sprawl

**Tasks**:
- [ ] Merge overlapping utility functions
- [ ] Remove reinvented standard library features
- [ ] Simplify or remove overly complex helpers
- [ ] Consolidate validation logic

**Expected impact**: 10-20% reduction in utility code

---

### 5.6 Agent Simplification (Week 6)
**Goal**: Reduce agent implementation complexity

**Tasks**:
- [ ] Replace LLM-based parsing with deterministic parsing where possible
- [ ] Simplify utility agents or remove if simple functions suffice
- [ ] Reduce prompt construction complexity
- [ ] Remove unused agent capabilities

**Expected impact**: 15-20% reduction in agent code

---

### 5.7 Documentation Update (Week 7)
**Goal**: Update documentation to reflect simplified codebase

**Tasks**:
- [ ] Update CLAUDE.md with architectural changes
- [ ] Update Sphinx documentation
- [ ] Remove documentation for deleted features
- [ ] Simplify setup instructions if dependencies reduced
- [ ] Update configuration examples

---

## Success Metrics

### Code Metrics
- **Target**: 30-40% reduction in total lines of code
- **Target**: 25-35% reduction in cyclomatic complexity (average)
- **Target**: 20% reduction in import graph complexity
- **Target**: 15-20% reduction in external dependencies

### Quality Metrics
- **Maintain**: 100% of existing test coverage
- **Maintain**: All existing functionality
- **Improve**: Code readability scores (subjective review)
- **Improve**: New developer onboarding time (track anecdotally)

### Performance Metrics
- **Maintain**: Same experiment execution time
- **Maintain**: Test execution time (or improve)
- **Improve**: IDE responsiveness (fewer imports, simpler structure)

---

## Safeguards

### Before Each Change
1. **Run full test suite**: `python run_tests.py --mode full`
2. **Review affected areas**: Check import graph for dependencies
3. **Document reasoning**: Why is this safe to remove/simplify?
4. **Create branch**: Isolate changes for easy rollback

### After Each Change
1. **Run full test suite again**: Ensure nothing broke
2. **Manual smoke test**: Run sample experiment end-to-end
3. **Review git diff**: Ensure no unintended changes
4. **Update documentation**: Keep docs in sync with code

### Red Flags (STOP if encountered)
- Test coverage drops below baseline
- Any integration test fails
- Experiment results differ from baseline
- Performance degrades >10%
- Breaking changes to public APIs without migration plan

---

## Deliverables

### Phase 1-2 Outputs (Discovery)
- 9 detailed audit reports (one per subsection)
- Inventory of all unused/overengineered code

### Phase 3 Outputs (Analysis)
- Dependency analysis reports
- Module coupling visualization

### Phase 4 Outputs (Prioritization)
- Prioritization matrix with all findings
- Risk assessment for each change

### Phase 5 Outputs (Execution)
- Simplified codebase (series of PRs)
- Updated documentation
- Migration guide (if needed)
- Final audit report with metrics

---

## Timeline

| Phase | Duration | Key Milestone |
|-------|----------|---------------|
| Phase 1: Discovery | 2 weeks | Complete inventory |
| Phase 2: Pattern Detection | 1 week | Pattern catalog |
| Phase 3: Dependency Analysis | 3 days | Dependency graphs |
| Phase 4: Prioritization | 2 days | Sorted action list |
| Phase 5: Execution | 7 weeks | Simplified codebase |
| **Total** | **11 weeks** | **Production-ready** |

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Set up tracking** (GitHub project board or similar)
3. **Begin Phase 1.1**: Static code analysis with `vulture`
4. **Schedule regular check-ins** (weekly progress reviews)
5. **Establish rollback procedures** (backup branches, revert plans)

---

## Notes

- This is a living document; update as we learn
- Some findings may reveal the complexity IS justified
- Focus on wins that improve developer experience
- Don't sacrifice functionality for simplicity
- When in doubt, measure before removing
