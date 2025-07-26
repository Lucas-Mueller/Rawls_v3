# Phase 1.3 Payoff Feedback System Analysis

## Executive Summary

This report analyzes the current implementation of Phase 1.3 (Repeated Application of Principles) against the experimental requirements and identifies critical gaps in the payoff feedback system. The analysis reveals that while the core principle application logic is implemented, the essential feedback mechanism that informs agents of their social class assignment and counterfactual payoffs is incomplete.

## Experimental Requirements (from master_plan.md)

### Phase 1.3 Specification
- **4 rounds by default** ✅ IMPLEMENTED
- **Agent chooses justice principle** ✅ IMPLEMENTED  
- **Distribution applied based on chosen principle** ✅ IMPLEMENTED
- **Agent randomly assigned to social class** ✅ IMPLEMENTED
- **Agent receives corresponding payoff** ✅ IMPLEMENTED
- **CRITICAL: Agent made aware of assigned social class** ❌ MISSING
- **CRITICAL: Agent told alternative payoffs under each principle (same class)** ❌ MISSING

### Reference Implementation (chit_example.png)
The reference image shows the expected format:
```
This assigns you to the following income class: LOW (in Situation A)

For each principle of justice the following income would be received by each member of this income class. You will receive a payoff of $1 for each $10,000 of income.

Principle of Justice               Income    Payoff
Maximizing the floor              $13,000    $1.30
Maximizing the average             $6,000    $0.60
Maximizing the average with a 
floor constraint of $12,000       $12,000    $1.20
Maximizing the average with a
floor constraint of $10,000       $10,000    $1.00
Maximizing the average with a
range constraint of $25,000        $6,000    $0.60
Maximizing the average with a
range constraint of $15,000       $12,000    $1.20
```

## Current Implementation Analysis

### File: core/phase1_manager.py

#### What's Implemented Correctly
1. **Four rounds execution** (lines 129-174)
2. **Principle choice validation** (lines 275-287)
3. **Distribution application logic** (lines 289-292)
4. **Payoff calculation** (lines 294-295)
5. **Memory updates** (lines 163-172)

#### Critical Gaps Identified

##### 1. Missing Social Class Notification
**Location:** `_step_1_3_principle_application()` method (lines 252-336)

**Current:** Agent receives earnings but is NOT explicitly told their assigned income class.

**Required:** Agent must be clearly informed: "You were assigned to the [CLASS] income class"

**Impact:** Without knowing their social position, agents cannot properly learn from the counterfactual information.

##### 2. Incorrect Alternative Payoff Calculation
**Location:** Lines 297-306 in phase1_manager.py

**Current Implementation:**
```python
# Calculate alternative earnings by principle (not just distribution)
alternative_earnings_by_principle = DistributionGenerator.calculate_alternative_earnings_by_principle(
    distribution_set.distributions, 
    parsed_choice.constraint_amount if parsed_choice.constraint_amount else None
)
```

**Problem:** The `calculate_alternative_earnings_by_principle()` method in `distribution_generator.py` (lines 157-205) calculates what the agent would earn under different principles but with NEW random class assignments for each principle.

**Required:** Calculate what the agent would have earned under each principle if they had been assigned to the SAME income class.

##### 3. Incomplete Feedback Format
**Location:** Round content creation (lines 330-334)

**Current:** Shows alternative earnings but doesn't follow the experimental format.

**Required:** Must include explicit social class assignment and formatted counterfactual table as shown in chit_example.png.

### File: core/distribution_generator.py

#### Issue in calculate_alternative_earnings_by_principle()
**Location:** Lines 157-205

**Current Logic:**
```python
# Calculate what they would have earned with this principle
assigned_class, earnings = DistributionGenerator.calculate_payoff(chosen_distribution)
alternative_earnings[principle.value] = earnings
```

**Problem:** `calculate_payoff()` randomly assigns a NEW income class for each principle, which is incorrect.

**Required:** Use the SAME income class assignment across all principle alternatives.

## Required Implementation Changes

### 1. Modify ApplicationResult Model
**File:** models/experiment_types.py

**Add field:**
```python
class ApplicationResult(BaseModel):
    # ... existing fields ...
    assigned_income_class: IncomeClass  # ✅ Already exists
    alternative_earnings_same_class: Dict[str, float] = Field(
        default_factory=dict, 
        description="What participant would have earned under each principle with SAME class assignment"
    )
```

### 2. Fix calculate_alternative_earnings_by_principle()
**File:** core/distribution_generator.py

**Current method needs modification to accept a fixed income class:**
```python
@staticmethod
def calculate_alternative_earnings_by_principle_fixed_class(
    distributions: List[IncomeDistribution], 
    assigned_class: IncomeClass,
    constraint_amount: Optional[int] = None
) -> dict:
    """Calculate what participant would have earned under each principle with FIXED class assignment."""
    # Implementation needed
```

### 3. Update Phase 1 Manager Feedback
**File:** core/phase1_manager.py

**Modify `_step_1_3_principle_application()` to:**
1. Explicitly state assigned income class
2. Calculate same-class alternative payoffs
3. Format feedback as shown in chit_example.png

### 4. Enhanced Round Content Format
The round content should include:
```
ROUND {round_num} OUTCOME:

You chose: {principle} {constraint}
Assigned income class: {assigned_class}
Your earnings: ${earnings:.2f}

COUNTERFACTUAL ANALYSIS:
If you had been assigned to the same income class ({assigned_class}) under each principle:

Principle                           Income    Payoff
Maximizing the floor               $X,XXX    $X.XX
Maximizing the average             $X,XXX    $X.XX
Max average with floor constraint  $X,XXX    $X.XX
Max average with range constraint  $X,XXX    $X.XX
```

## Impact Assessment

### Learning Mechanism Compromise
Without proper counterfactual feedback, agents cannot:
1. **Understand their social position** - Critical for justice reasoning
2. **Learn from alternatives** - Cannot see how principle choice affects outcomes
3. **Develop informed preferences** - Cannot connect choices to consequences

### Experimental Validity
The current implementation may produce invalid results because:
1. **Incomplete information** - Agents lack crucial feedback for decision-making
2. **Random noise** - Alternative earnings with random classes don't show causal effects
3. **Learning bias** - Agents may develop incorrect associations

## Recommendations

### Priority 1: Critical Fixes
1. **Immediate:** Implement explicit social class notification
2. **Immediate:** Fix alternative earnings to use same income class
3. **High:** Update feedback format to match experimental specification

### Priority 2: Enhancement
1. **Medium:** Add validation to ensure all feedback elements are included
2. **Medium:** Create unit tests for payoff feedback system
3. **Low:** Consider logging counterfactual information for analysis

## Conclusion

The Phase 1.3 implementation has solid foundational logic but is missing critical components of the experimental design. The payoff feedback system must be enhanced to provide agents with complete information about their social class assignment and counterfactual outcomes under alternative principles. Without these changes, the experiment cannot achieve its intended learning objectives and may produce invalid results.

The fixes are straightforward but essential for experimental validity and should be implemented before any experimental runs.

---

**Generated:** 2025-07-26  
**Analyst:** Claude Code  
**Files Analyzed:** master_plan.md, core/phase1_manager.py, core/distribution_generator.py, models/experiment_types.py, chit_example.png