# Phase 1 Step 1.3 Analysis: Agent Knowledge and Class Assignment

## Executive Summary

This report analyzes how agents are informed about consequences and class assignments in Phase 1 Step 1.3 of the Frohlich Experiment. **Critical Finding**: The current implementation has a significant gap from the intended experimental design - agents are NOT told what they would have received under alternative principles, despite this being explicitly required in the master plan.

## Key Questions Addressed

1. **Are agents informed of the consequences of their principle choice?** 
   - **Partially Yes** - Agents are told they will be randomly assigned to a class and earn money based on their income
   - **No** - Agents are NOT told about counterfactual outcomes under alternative principles

2. **Is class assignment randomly generated after they make their choice?**
   - **Yes** - Class assignment happens AFTER principle selection using `random.choice()`

3. **Are agents told what they would have received under alternative principles?**
   - **No** - This is a major implementation gap from the master plan requirements

## Detailed Analysis

### Step 1.3 Implementation Flow

**Location**: `core/phase1_manager.py:93-119`

For each of the 4 rounds in Step 1.3:

1. **Distribution Generation** (lines 98-101)
   - New set of 4 income distributions generated with random multipliers
   - Uses `DistributionGenerator.generate_dynamic_distribution()`
   - Multiplier range configurable via `config.distribution_range_phase1`

2. **Agent Decision** (lines 103-105)
   - Agent presented with distributions in table format
   - Must choose one of four justice principles (a-d)
   - Principles c/d require constraint amount specification

3. **Information Provided to Agents** (lines 362-384)
   ```
   Your chosen principle will determine which distribution is selected. 
   You'll then be randomly assigned to an income class and earn $1 for every $10,000 of income.
   ```

4. **Class Assignment** (line 228)
   - Executed via `DistributionGenerator.calculate_payoff(chosen_distribution)`
   - **Timing**: Happens AFTER principle selection
   - **Method**: Completely random using `random.choice()` across 5 income classes

### Class Assignment Implementation

**Location**: `core/distribution_generator.py:130-142`

```python
def calculate_payoff(distribution: IncomeDistribution) -> Tuple[IncomeClass, float]:
    """Randomly assign participant to income class and calculate payoff."""
    # Randomly assign to one of the five income classes
    income_classes = list(IncomeClass)
    assigned_class = random.choice(income_classes)
    
    # Get income for assigned class
    income = distribution.get_income_by_class(assigned_class)
    
    # Calculate payoff: $1 for every $10,000 of income
    payoff = income / 10000.0
    
    return assigned_class, payoff
```

**Key Properties**:
- **Random**: Uses `random.choice()` - no bias or manipulation
- **Post-Decision**: Occurs after agent makes principle choice
- **Independent**: Each round gets new random assignment
- **Equal Probability**: All 5 income classes have equal selection chance

### Critical Implementation Gap: Missing Counterfactual Information

#### What the Master Plan Requires
The master plan explicitly states:
> "Agents are explicitly told what they _would have received_ under competing distributions each time they receive a payoff."

#### What the Implementation Actually Does

**Alternative Earnings ARE Calculated** (`core/distribution_generator.py:145-154`):
```python
def calculate_alternative_earnings(distributions: List[IncomeDistribution]) -> dict:
    """Calculate what participant would have earned under each distribution."""
    alternative_earnings = {}
    
    for i, dist in enumerate(distributions):
        # For each distribution, randomly assign class and calculate earnings
        assigned_class, earnings = DistributionGenerator.calculate_payoff(dist)
        alternative_earnings[f"distribution_{i+1}"] = earnings
    
    return alternative_earnings
```

**But Alternative Earnings Are NOT Shared with Agents**:

The memory update only includes (`core/phase1_manager.py:244-248`):
```python
round_content = f"""Prompt: {application_prompt}
Your Response: {text_response}
Your Choice: {parsed_choice.dict() if hasattr(parsed_choice, 'dict') else str(parsed_choice)}
Outcome: Chose {parsed_choice.principle.value}, assigned to {assigned_class.value} class, earned ${earnings:.2f}. Total earnings now ${context.bank_balance + earnings:.2f}."""
```

**Missing Information**:
- What they would have earned under the other 3 distributions
- What their income would have been in different income classes  
- Any counterfactual outcomes from alternative principle choices

### Agent Memory Updates

After each round, agents receive and store in memory:
- The round's prompt and their response
- Their principle choice and any constraints
- Their assigned class and actual earnings
- Their cumulative earnings total

**What's Missing**: Counterfactual information about alternative outcomes.

## Implications of the Implementation Gap

### Experimental Validity Impact
1. **Learning Mechanism**: Agents cannot learn from counterfactual outcomes as intended
2. **Preference Formation**: Missing feedback could affect how agents develop preferences
3. **Decision-Making Realism**: Reduces ecological validity of the decision process
4. **Comparative Analysis**: Agents can't compare actual vs. potential outcomes

### Behavioral Consequences
- Agents may develop different strategies without counterfactual learning
- Risk assessment abilities limited by incomplete outcome information
- Preference stability may differ from intended experimental design
- Group dynamics in Phase 2 may be affected by Phase 1 learning gaps

## Recommendations

1. **Immediate Fix**: Modify the memory update system to include alternative earnings information
2. **Testing**: Verify that counterfactual information affects agent decision-making as expected
3. **Documentation**: Update implementation to match master plan requirements
4. **Validation**: Compare results with and without counterfactual information to assess impact

## Technical Implementation Files

- **`core/phase1_manager.py`**: Main Phase 1 orchestration and memory updates
- **`core/distribution_generator.py`**: Distribution generation and payoff calculations  
- **`models/experiment_types.py`**: Data structures including `ApplicationResult`
- **`experiment_agents/participant_agent.py`**: Agent implementation and memory management

## Conclusion

The current implementation correctly handles the timing and randomization of class assignments (occurring post-decision with true randomness), but fails to provide agents with critical counterfactual information about alternative outcomes. This represents a significant deviation from the intended experimental design that could substantially impact the validity and interpretability of results.