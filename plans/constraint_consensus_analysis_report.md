# The Constraint Consensus Problem: Analysis Report

## Executive Summary

This report analyzes a critical phenomenon in the Frohlich Experiment system where agents consistently prefer "maximizing average income with floor constraint" in Phase 1 but fail to reach consensus on this principle in Phase 2. The analysis reveals this is primarily a **constraint value specification problem** rather than an agent intelligence or principle preference issue.

## Key Findings

### The Core Problem: Constraint Value Ambiguity

The fundamental issue lies in the **lack of structured constraint value learning and standardization** across experimental phases:

1. **Phase 1**: Agents learn preferences through individual trial-and-error with constraint values
2. **Phase 2**: Agents must agree on exact constraint amounts without systematic coordination mechanisms
3. **Validation**: Consensus requires identical constraint amounts, creating unnecessary failure points

### Critical System Design Issues

#### 1. **Absence of Constraint Value Guidance** (`phase1_manager.py:436-458`)

In Phase 1 application rounds, agents receive no guidance on reasonable constraint ranges:

```python
def _build_application_prompt(self, distribution_set, round_num: int) -> str:
    """Build prompt for principle application."""
    return f"""
ROUND {round_num}

{distributions_table}

You are to make a choice from among the four principles of justice...
If you choose (c) or (d), you will have to tell us what that floor or range constraint is before you can be said to have made a well-defined choice.

Your chosen principle will determine which distribution is selected...
What is your choice and reasoning?
"""
```

**Problem**: Agents specify constraint values in isolation without reference points or contextual anchoring.

#### 2. **Fragmented Memory Architecture** (`experiment_agents/participant_agent.py:48`)

While agents maintain continuous memory across phases, the memory update process doesn't systematically capture constraint value learning:

```python
# Update memory with agent
context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, round_content
)
```

**Problem**: Memory updates are unstructured, leading to inconsistent constraint value recall and application.

#### 3. **Overly Strict Consensus Requirements** (`core/phase2_manager.py:432-444`)

Phase 2 consensus mechanism requires exact matching including constraint amounts:

```python
def _check_exact_consensus(self, votes: List[PrincipleChoice]) -> PrincipleChoice:
    """Check if all votes are exactly identical (including constraint amounts)."""
    if not votes:
        return None
        
    first_vote = votes[0]
    for vote in votes[1:]:
        if (vote.principle != first_vote.principle or 
            vote.constraint_amount != first_vote.constraint_amount):
            return None
    
    return first_vote
```

**Problem**: Consensus fails even when agents agree on principle but differ slightly on constraint amounts (e.g., $15,000 vs $16,000).

#### 4. **Inadequate Constraint Value Context** (`translations/english_prompts.json:387-394`)

Phase 2 voting prompt provides minimal constraint guidance:

```json
"**IMPORTANT**: If you choose (c) or (d), you MUST specify the exact constraint amount in dollars.

This is your final vote. The group needs unanimous agreement (everyone choosing the exact same principle with the exact same constraint amount) to reach consensus."
```

**Problem**: Agents lack shared reference points for appropriate constraint values, leading to arbitrary specifications.

## Phase 1 vs Phase 2 Behavioral Differences

### Phase 1: Individual Learning Success

**Strengths:**
- Agents effectively learn through 4 rounds of application
- Trial-and-error with different constraint values
- Personal memory accumulation of outcomes
- Individual optimization without coordination pressure

**Evidence from Code:**
- Robust parsing with retry mechanisms (`utility_agent.py:264-282`)
- Comprehensive counterfactual analysis (`phase1_manager.py:320-368`)
- Memory-guided preference evolution

### Phase 2: Coordination Failure

**Weaknesses:**
- No mechanism for sharing constraint value insights
- Agents rely on individual Phase 1 experiences without group calibration
- Exact matching requirements prevent near-consensus solutions
- Limited discussion rounds for constraint value negotiation

**Evidence from Experiment Results:**
The Chinese-language experiment shows agents repeatedly stating preference for floor constraints but never specifying concrete constraint amounts during discussion, only mentioning the need to "discuss specific amounts."

## Root Causes Analysis

### 1. **Constraint Value Learning Gap**

**Issue**: The system teaches agents to apply constraint principles but doesn't establish shared understanding of appropriate constraint ranges.

**Impact**: Each agent develops personal constraint value intuitions that don't align with others.

### 2. **Discussion Framework Limitations**

**Issue**: Phase 2 discussion prompts focus on principle selection rather than constraint value negotiation.

**Impact**: Agents spend discussion time reaffirming principle preference rather than calibrating constraint values.

### 3. **Validation Rigidity**

**Issue**: All-or-nothing consensus requirements prevent recognition of substantial agreement.

**Impact**: Groups that agree on principle and approximately on constraint amounts are classified as "failed consensus."

### 4. **Memory Continuity Misalignment**

**Issue**: While memory continues across phases, there's no systematic extraction of constraint value insights from Phase 1 for Phase 2 application.

**Impact**: Agents don't effectively leverage their Phase 1 learning for Phase 2 coordination.

## Evidence from System Architecture

### Parser Agent Constraint Handling (`utility_agent.py:274-293`)

The system has sophisticated regex patterns for constraint detection but lacks value normalization:

```python
def _compile_principle_patterns(self) -> Dict[str, re.Pattern]:
    """Compile regex patterns for principle detection."""
    return {
        'maximizing_average_floor_constraint': re.compile(
            r'(?:maximizing?.*?average.*?floor|average.*?floor.*?constraint|floor.*?constraint|option\s*[(\[]?c[)\]]?)', 
            re.IGNORECASE
        ),
        # ...
    }
```

**Analysis**: The system can identify constraint principles but doesn't standardize constraint values or provide guidance on reasonable ranges.

### Distribution Generator Context (`distribution_generator.py:90-100`)

The constraint application logic shows how different constraint values lead to different outcomes:

```python
@staticmethod
def _apply_maximizing_average_floor_constraint(
    distributions: List[IncomeDistribution], 
    floor_constraint: int
) -> Tuple[IncomeDistribution, str]:
    """Apply maximizing average with floor constraint."""
    # Filter distributions that meet floor constraint
    valid_distributions = [d for d in distributions if d.low >= floor_constraint]
    
    if not valid_distributions:
        # No distribution meets constraint, choose one with highest floor
```

**Analysis**: Small differences in constraint values can lead to significantly different distribution selections, making exact consensus both critical and difficult to achieve.

## Recommendations

### 1. **Implement Constraint Value Anchoring**

**Solution**: Provide agents with constraint value references based on distribution data.

**Implementation**: 
- Add distribution-aware constraint suggestions
- Include constraint value ranges in Phase 1 prompts
- Show constraint value outcomes clearly in counterfactual analysis

### 2. **Develop Constraint Value Negotiation Framework**

**Solution**: Modify Phase 2 discussion to focus on constraint value convergence.

**Implementation**:
- Add constraint value proposal and counter-proposal mechanisms
- Enable agents to share their Phase 1 constraint value experiences
- Implement constraint value averaging or median-finding processes

### 3. **Relax Consensus Requirements**

**Solution**: Allow consensus with "close enough" constraint values.

**Implementation**:
- Define constraint value tolerance ranges (e.g., within 10%)
- Implement tiered consensus levels (exact vs approximate)
- Use median constraint values when principle consensus exists

### 4. **Enhance Memory-Guided Constraint Learning**

**Solution**: Systematically extract and share constraint value insights across agents.

**Implementation**:
- Add structured constraint value memory sections
- Implement constraint value experience sharing in Phase 2
- Create constraint value recommendation systems based on Phase 1 outcomes

### 5. **Add Constraint Value Discussion Rounds**

**Solution**: Dedicate specific discussion rounds to constraint value negotiation.

**Implementation**:
- Separate principle selection from constraint value specification
- Add constraint value proposal and refinement cycles
- Enable iterative constraint value convergence

## Conclusion

The constraint consensus problem is **primarily a system design issue rather than an agent intelligence limitation**. The agents correctly identify the optimal principle (maximizing average with floor constraint) but lack the coordination mechanisms needed to agree on specific constraint values.

The solution requires **architectural changes** to support:
1. Shared constraint value learning
2. Structured constraint value negotiation
3. Flexible consensus mechanisms
4. Enhanced memory utilization for constraint insights

These changes would preserve the experimental integrity while significantly improving consensus achievement rates by addressing the underlying coordination challenges rather than the agents' reasoning capabilities.

---

*Report generated through systematic analysis of the Frohlich Experiment codebase, including examination of agent behavior, prompt engineering, validation mechanisms, and memory management systems.*