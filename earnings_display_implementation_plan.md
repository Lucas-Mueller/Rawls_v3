# Comprehensive Earnings Display Implementation Plan

## Problem Analysis

**Core Issues Identified:**

1. **Missing Phase 1 Decision Landscape Context**: During Phase 1 demonstration rounds, agents don't see the complete mapping of how each principle and constraint combination would select distributions and affect their earnings
2. **Missing Phase 2 Actual Earnings Prominence**: After Phase 2 group discussion, agents see counterfactual alternatives but their own actual earnings under the group's chosen principle lack clear distinction
3. **Incomplete Learning Integration**: No connection between Phase 1 learning experiences and Phase 2 group decision outcomes
4. **Missing Comprehensive Display**: Current system only shows basic earnings without the detailed constraint-to-distribution mapping that agents need for informed decision-making

**Impact**: Agents cannot fully understand the implications of different principles during learning (Phase 1) or properly evaluate their collective decision-making process (Phase 2), limiting the educational and research value of the experiment.

## Current System Analysis

### Existing Architecture Strengths
- **Services-first architecture**: `CounterfactualsServic11e` handles all results display
- **Template-based results**: Uses localized templates through `phase2_results_delivery_prompt`
- **Translation infrastructure**: Multi-language support already in place
- **Memory integration**: Results are properly integrated with agent memory

### Root Cause Assessment

**Issue 1: Missing Phase 1 Decision Context**
- **Location**: Phase 1 demonstration rounds (4 rounds of principle application)
- **Problem**: Agents don't see comprehensive constraint mapping during learning phase
- **Current pattern**: Shows only basic earnings without detailed principle-to-distribution explanations

**Issue 2: Missing Phase 2 Decision Context** 
- **Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`
- **Problem**: Results don't show the principle-to-distribution mapping table that agents need to understand their group decision
- **Current pattern**: Shows only final earnings without showing which distribution each principle selected

**Issue 3: No Integration Between Phases**
- **Location**: Both Phase 1 and Phase 2 results displays
- **Problem**: No connection showing how Phase 2 group decision relates to Phase 1 learning experiences
- **Impact**: Agents cannot evaluate whether their collective decision aligned with their individual learning

## Implementation Strategy

### Phase 1: Add Phase 1 Demonstration Round Display (120 minutes)

**Target**: Create comprehensive earnings display for each Phase 1 demonstration round showing detailed constraint mapping and learning outcomes

**Changes Required:**

1. **Create new service method** for Phase 1 comprehensive display in `CounterfactualsService`:

```python
def deliver_phase1_comprehensive_results(self, 
                                       distributions: List[IncomeDistribution], 
                                       chosen_principle: PrincipleChoice,
                                       assigned_class: IncomeClass,
                                       round_number: int,
                                       participant_lang_manager) -> str:
    """Deliver comprehensive Phase 1 results showing full decision landscape for learning."""
    
    # Generate comprehensive constraint mappings
    mappings = self._generate_comprehensive_constraint_mappings(distributions, assigned_class)
    
    # Build distribution table
    distributions_table = self._build_distributions_display_table(distributions, participant_lang_manager)
    
    # Build principle selection mapping with current choice highlighted
    principle_mapping = self._build_principle_selection_mapping(mappings, chosen_principle, participant_lang_manager)
    
    # Calculate actual earnings for chosen principle
    actual_earnings = self._calculate_actual_earnings(distributions, chosen_principle, assigned_class)
    
    # Format comprehensive results
    results_template = participant_lang_manager.get("phase1_results.comprehensive_display_template")
    
    comprehensive_results = results_template.format(
        round_number=round_number,
        distributions_table=distributions_table,
        principle_mapping=principle_mapping,
        class_assignment=assigned_class.value,
        chosen_principle_name=self._format_principle_name(chosen_principle, participant_lang_manager),
        actual_earnings_display=actual_earnings,
        alternative_earnings_breakdown=self._format_alternative_earnings(mappings, chosen_principle, participant_lang_manager)
    )
    
    return comprehensive_results
```

2. **Add new method** in `CounterfactualsService` to generate comprehensive constraint mappings:
```python
def _generate_comprehensive_constraint_mappings(self, distributions: List[IncomeDistribution], assigned_class: IncomeClass) -> dict:
    """Generate detailed mapping of every constraint value to distribution and agent's earnings."""
    from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
    
    mappings = {
        'floor_constraints': [],
        'range_constraints': [],
        'non_constraint_principles': []
    }
    
    # Test floor constraints at each distribution's low income level
    floor_amounts = sorted(set(dist.low for dist in distributions))
    for floor_constraint in floor_amounts:
        try:
            choice = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=floor_constraint,
                certainty=CertaintyLevel.SURE
            )
            chosen_distribution, chosen_index = DistributionGenerator.apply_principle_to_distributions(
                distributions, choice
            )
            
            # Calculate agent's earnings in their assigned class
            agent_income = chosen_distribution.get_income_by_class(assigned_class)
            agent_earnings = agent_income / 10000.0
            
            mappings['floor_constraints'].append({
                'constraint_value': floor_constraint,
                'display_name': f"Floor constraint ≤ ${floor_constraint:,}",
                'selected_distribution': f"Distribution {chosen_index + 1}",
                'agent_income': agent_income,
                'agent_earnings': agent_earnings
            })
        except Exception as e:
            continue
    
    # Test range constraints at each distribution's range level
    range_amounts = sorted(set(dist.high - dist.low for dist in distributions))
    for range_constraint in range_amounts:
        try:
            choice = PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                constraint_amount=range_constraint,
                certainty=CertaintyLevel.SURE
            )
            chosen_distribution, chosen_index = DistributionGenerator.apply_principle_to_distributions(
                distributions, choice
            )
            
            # Calculate agent's earnings in their assigned class
            agent_income = chosen_distribution.get_income_by_class(assigned_class)
            agent_earnings = agent_income / 10000.0
            
            mappings['range_constraints'].append({
                'constraint_value': range_constraint,
                'display_name': f"Range constraint ≤ ${range_constraint:,}",
                'selected_distribution': f"Distribution {chosen_index + 1}",
                'agent_income': agent_income,
                'agent_earnings': agent_earnings
            })
        except Exception as e:
            continue
    
    # Test non-constraint principles
    non_constraint_principles = [
        (JusticePrinciple.MAXIMIZING_FLOOR, "Maximizing the floor"),
        (JusticePrinciple.MAXIMIZING_AVERAGE, "Maximizing average")
    ]
    
    for principle, display_name in non_constraint_principles:
        try:
            choice = PrincipleChoice(
                principle=principle,
                certainty=CertaintyLevel.SURE
            )
            chosen_distribution, chosen_index = DistributionGenerator.apply_principle_to_distributions(
                distributions, choice
            )
            
            # Calculate agent's earnings in their assigned class
            agent_income = chosen_distribution.get_income_by_class(assigned_class)
            agent_earnings = agent_income / 10000.0
            
            mappings['non_constraint_principles'].append({
                'display_name': display_name,
                'selected_distribution': f"Distribution {chosen_index + 1}",
                'agent_income': agent_income,
                'agent_earnings': agent_earnings
            })
        except Exception as e:
            continue
    
    return mappings
```

### Phase 2: Add Phase 2 Group Decision Display (90 minutes)

**Target**: Create comprehensive Phase 2 results display showing group decision outcomes with Phase 1 learning integration

**Changes Required:**

1. **Enhance existing `deliver_results_and_update_memory`** in `CounterfactualsService`:

```python
def deliver_phase2_comprehensive_results(self,
                                       phase2_distributions: List[IncomeDistribution],
                                       group_consensus: PrincipleChoice,
                                       assigned_class: IncomeClass,
                                       participant_lang_manager) -> str:
    """Deliver comprehensive Phase 2 results showing group decision outcomes."""
    
    # Generate Phase 2 constraint mappings
    phase2_mappings = self._generate_comprehensive_constraint_mappings(phase2_distributions, assigned_class)
    
    # Calculate Phase 2 actual earnings
    phase2_actual_earnings = self._calculate_actual_earnings(phase2_distributions, group_consensus, assigned_class)
    
    # Format comprehensive Phase 2 results
    results_template = participant_lang_manager.get("phase2_results.comprehensive_display_template")
    
    comprehensive_results = results_template.format(
        group_consensus_display=self._format_group_consensus(group_consensus, participant_lang_manager),
        phase2_distributions_table=self._build_distributions_display_table(phase2_distributions, participant_lang_manager),
        phase2_principle_mapping=self._build_principle_selection_mapping(phase2_mappings, group_consensus, participant_lang_manager),
        actual_earnings_prominent=self._format_prominent_actual_earnings(phase2_actual_earnings, group_consensus, assigned_class, participant_lang_manager),
        alternative_earnings_breakdown=self._format_alternative_earnings(phase2_mappings, group_consensus, participant_lang_manager)
    )
    
    return comprehensive_results
```

### Phase 3: Add Comprehensive Translation Keys (60 minutes)

**Target**: Add detailed translation support for both phases

1. **Add comprehensive translation keys** for Phase 1 and Phase 2 displays:

**English** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`):
```json
"phase1_results": {
  "comprehensive_display_template": "=== PHASE 1 DEMONSTRATION ROUND {round_number} RESULTS ===\n\n{distributions_table}\n\n{principle_mapping}\n\n{actual_earnings_display}\n\n{alternative_earnings_breakdown}",
  "demonstration_round_header": "PHASE 1 DEMONSTRATION ROUND {round_number} RESULTS",
  "learning_objective": "This round shows how different principles would affect your earnings with these distributions.",
  "your_assigned_principle": "Your assigned principle for this round:",
  "what_you_learned": "What you learned this round:"
},
"phase2_results": {
  "comprehensive_display_template": "=== PHASE 2 GROUP DECISION RESULTS ===\n\n{group_consensus_display}\n\n{phase2_distributions_table}\n\n{phase2_principle_mapping}\n\n{actual_earnings_prominent}\n\n{alternative_earnings_breakdown}",
  "group_decision_header": "PHASE 2 GROUP DECISION RESULTS",
  "group_consensus_achieved": "Group consensus achieved:",
  "your_groups_choice_marker": "← YOUR GROUP'S CHOICE",
  "final_earnings_header": "YOUR FINAL EXPERIMENT EARNINGS"
},
"results": {
  "distributions_and_mapping_header": "EXPERIMENT DISTRIBUTIONS AND SELECTION MAPPING",
  "income_class_header": "Income Class",
  "distribution_selection_header": "Distribution Selection by Principle:",
  "your_actual_earnings_header": "YOUR ACTUAL EARNINGS",
  "you_are_assigned_to": "You are assigned to {class_name} class.",
  "group_choice_detail": "Group choice: {principle_name} → {distribution}",
  "your_earnings_detail": "Your earnings: ${income:,} → ${earnings:.2f}",
  "alternative_earnings_header": "ALTERNATIVE EARNINGS ANALYSIS",
  "alternative_earnings_note": "What you would have earned under different choices:",
  "floor_constraint_options": "Floor Constraint Options:",
  "range_constraint_options": "Range Constraint Options:",
  "non_constraint_principles": "Non-Constraint Principles:",
  "maximizing_floor": "Maximizing the floor",
  "maximizing_average": "Maximizing average"
}
```

**Spanish** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`):
```json
"phase1_results": {
  "comprehensive_display_template": "=== RESULTADOS DE LA RONDA DE DEMOSTRACIÓN {round_number} DE LA FASE 1 ===\n\n{distributions_table}\n\n{principle_mapping}\n\n{actual_earnings_display}\n\n{alternative_earnings_breakdown}",
  "demonstration_round_header": "RESULTADOS DE LA RONDA DE DEMOSTRACIÓN {round_number} DE LA FASE 1",
  "learning_objective": "Esta ronda muestra cómo diferentes principios afectarían sus ganancias con estas distribuciones.",
  "your_assigned_principle": "Su principio asignado para esta ronda:",
  "what_you_learned": "Lo que aprendió en esta ronda:"
},
"phase2_results": {
  "comprehensive_display_template": "=== RESULTADOS DE LA DECISIÓN GRUPAL DE LA FASE 2 ===\n\n{group_consensus_display}\n\n{phase2_distributions_table}\n\n{phase2_principle_mapping}\n\n{actual_earnings_prominent}\n\n{alternative_earnings_breakdown}",
  "group_decision_header": "RESULTADOS DE LA DECISIÓN GRUPAL DE LA FASE 2",
  "group_consensus_achieved": "Consenso grupal alcanzado:",
  "your_groups_choice_marker": "← ELECCIÓN DE SU GRUPO",
  "final_earnings_header": "SUS GANANCIAS FINALES DEL EXPERIMENTO"
},
"results": {
  "distributions_and_mapping_header": "DISTRIBUCIONES DEL EXPERIMENTO Y MAPEO DE SELECCIÓN",
  "income_class_header": "Clase de Ingresos",
  "distribution_selection_header": "Selección de Distribución por Principio:",
  "your_actual_earnings_header": "SUS GANANCIAS REALES",
  "you_are_assigned_to": "Está asignado a la clase {class_name}.",
  "group_choice_detail": "Elección del grupo: {principle_name} → {distribution}",
  "your_earnings_detail": "Sus ganancias: ${income:,} → ${earnings:.2f}",
  "alternative_earnings_header": "ANÁLISIS DE GANANCIAS ALTERNATIVAS",
  "alternative_earnings_note": "Lo que habría ganado bajo diferentes opciones:",
  "floor_constraint_options": "Opciones de Restricción de Piso:",
  "range_constraint_options": "Opciones de Restricción de Rango:",
  "non_constraint_principles": "Principios Sin Restricción:",
  "maximizing_floor": "Maximizando el piso",
  "maximizing_average": "Maximizando el promedio"
}
```

**Mandarin** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`):
```json
"phase1_results": {
  "comprehensive_display_template": "=== 第1阶段演示轮次{round_number}结果 ===\n\n{distributions_table}\n\n{principle_mapping}\n\n{actual_earnings_display}\n\n{alternative_earnings_breakdown}",
  "demonstration_round_header": "第1阶段演示轮次{round_number}结果",
  "learning_objective": "此轮次显示不同原则如何影响您在这些分配下的收入。",
  "your_assigned_principle": "您在此轮次的分配原则:",
  "what_you_learned": "您在此轮次学到的内容:"
},
"phase2_results": {
  "comprehensive_display_template": "=== 第2阶段小组决策结果 ===\n\n{group_consensus_display}\n\n{phase2_distributions_table}\n\n{phase2_principle_mapping}\n\n{actual_earnings_prominent}\n\n{alternative_earnings_breakdown}",
  "group_decision_header": "第2阶段小组决策结果",
  "group_consensus_achieved": "达成小组共识:",
  "your_groups_choice_marker": "← 您小组的选择",
  "final_earnings_header": "您的最终实验收入"
},
"results": {
  "distributions_and_mapping_header": "实验分配和选择映射",
  "income_class_header": "收入阶层",
  "distribution_selection_header": "按原则选择分配:",
  "your_actual_earnings_header": "您的实际收入",
  "you_are_assigned_to": "您被分配到{class_name}阶层。",
  "group_choice_detail": "小组选择: {principle_name} → {distribution}",
  "your_earnings_detail": "您的收入: ${income:,} → ${earnings:.2f}",
  "alternative_earnings_header": "替代收入分析",
  "alternative_earnings_note": "在不同选择下您可能获得的收入:",
  "floor_constraint_options": "底线约束选项:",
  "range_constraint_options": "范围约束选项:",
  "non_constraint_principles": "无约束原则:",
  "maximizing_floor": "最大化底线",
  "maximizing_average": "最大化平均值"
}
```

2. **Modify results display logic** in `CounterfactualsService.deliver_results_and_update_memory()`:

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`

**Enhancement approach**:
- Add actual earnings section with prominent header before alternative earnings
- Use clear headers and formatting to distinguish sections
- Maintain existing template structure while adding prominence

**Specific change**: Modify the results template formatting to include:
```python
# Add after consensus_info building, before alternative earnings display:
actual_earnings_header = participant_lang_manager.get("results.your_actual_earnings_header")
actual_earnings_detail = participant_lang_manager.get("results.your_actual_earnings_detail").format(
    earnings=final_earnings,
    principle_name=chosen_principle_name
)

alternative_header = participant_lang_manager.get("results.alternative_earnings_header") 
alternative_note = participant_lang_manager.get("results.alternative_earnings_note")
```

### Phase 3: Integration and Validation (30 minutes)

**Target**: Ensure changes work correctly across languages and scenarios

**Validation Steps:**
1. Test constraint logic produces reasonable values for different distributions
2. Verify actual vs alternative earnings display clearly in all languages
3. Check memory integration maintains existing behavior
4. Validate both consensus and non-consensus scenarios

## Expected Outcome

**Before Fix:**
```
Group consensus: YES (Agreed: Maximizing Average with Floor Constraint with $13,000)

Alternative earnings analysis:
- Under Maximizing Floor Income: $15,000 ($1.50) 
- Under Maximizing Average Income: $24,000 ($2.40)
- Under Floor Constraint: $20,000 ($2.00)
- Under Range Constraint: $18,000 ($1.80)
```

**Phase 1 Example (After Fix):**
```
=== PHASE 1 DEMONSTRATION ROUND 2 RESULTS ===

EXPERIMENT DISTRIBUTIONS AND SELECTION MAPPING

| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |
|--------------|---------|---------|---------|---------|
| High         | $28,400 | $24,800 | $27,500 | $18,600 |
| Medium high  | $23,900 | $19,500 | $21,300 | $17,700 |
| Medium       | $21,300 | $17,700 | $18,600 | $16,800 |
| Medium low   | $11,500 | $15,100 | $14,200 | $14,200 |
| Low          | $10,600 | $11,500 | $12,400 | $13,300 |

PRINCIPLE OUTCOMES FOR MEDIUM CLASS:
- Maximizing the floor → Distribution 4 → $16,800 → $1.68
- Maximizing average → Distribution 1 → $21,300 → $2.13
- Floor constraint ≤ $10,600 → Distribution 1 → $21,300 → $2.13
- Floor constraint ≤ $11,500 → Distribution 2 → $17,700 → $1.77 ← YOUR ASSIGNED PRINCIPLE
- Floor constraint ≤ $12,400 → Distribution 3 → $18,600 → $1.86
- Floor constraint ≤ $13,300 → Distribution 4 → $16,800 → $1.68
- Range constraint ≤ $17,700 → Distribution 1 → $21,300 → $2.13
- Range constraint ≤ $15,000 → Distribution 3 → $18,600 → $1.86
- Range constraint ≤ $13,300 → Distribution 2 → $17,700 → $1.77

```

**Phase 2 Example (After Fix):**
```
=== PHASE 2 GROUP DECISION RESULTS ===

Group consensus achieved: Maximizing Average with Floor Constraint ≤ $13,000

EXPERIMENT DISTRIBUTIONS AND SELECTION MAPPING

| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |
|--------------|---------|---------|---------|---------|
| High         | $32,000 | $28,000 | $31,000 | $21,000 |
| Medium high  | $27,000 | $22,000 | $24,000 | $20,000 |
| Medium       | $24,000 | $20,000 | $21,000 | $19,000 |
| Medium low   | $13,000 | $17,000 | $16,000 | $16,000 |
| Low          | $12,000 | $13,000 | $14,000 | $15,000 |

PRINCIPLE OUTCOMES FOR MEDIUM CLASS:
- Maximizing the floor → Distribution 4 → $19,000 → $1.90
- Maximizing average → Distribution 1 → $24,000 → $2.40
- Floor constraint ≤ $12,000 → Distribution 1 → $24,000 → $2.40
- Floor constraint ≤ $13,000 → Distribution 2 → $20,000 → $2.00 ← YOUR GROUP'S CHOICE
- Floor constraint ≤ $14,000 → Distribution 3 → $21,000 → $2.10  
- Floor constraint ≤ $15,000 → Distribution 4 → $19,000 → $1.90
- Range constraint ≤ $20,000 → Distribution 1 → $24,000 → $2.40
- Range constraint ≤ $17,000 → Distribution 3 → $21,000 → $2.10
- Range constraint ≤ $15,000 → Distribution 2 → $20,000 → $2.00
```

## Technical Benefits

1. **Complete Learning Journey**: Agents experience comprehensive education about principles through detailed Phase 1 demonstration displays (4 rounds)
2. **Full Decision Landscape**: Both phases show complete mapping of every constraint value to distribution selection and personal earnings  
3. **Enhanced Educational Value**: Agents understand principle implications during individual learning (Phase 1) and see comprehensive outcomes of collective decision-making (Phase 2)
4. **Clear Principle Understanding**: Detailed constraint-to-distribution mapping helps agents understand how different constraint amounts affect outcomes
5. **Maintained Architecture**: Works within existing services-first approach with focused enhancements to CounterfactualsService
6. **Multilingual Support**: Full comprehensive display across all supported languages for both experimental phases

## Risk Mitigation

**Low Risk Changes**: 
- Constraint calculation helper is isolated and testable
- Display changes work within existing template system
- Translation additions don't modify existing keys

**Fallback Protection**:
- Constraint helper includes fallback to 15000 for unexpected cases
- Existing error handling in CounterfactualsService remains unchanged

## Implementation Timeline

- **Phase 1 (Phase 1 Demonstration Round Display)**: 120 minutes
- **Phase 2 (Phase 2 Group Decision Display)**: 90 minutes  
- **Phase 3 (Comprehensive Translation Keys)**: 60 minutes
- **Phase 4 (Integration/Validation)**: 45 minutes

**Total Estimated Time**: 5 hours 15 minutes

**Note**: This approach covers both experimental phases with comprehensive principle outcome displays. The system must:
- Generate detailed constraint mappings for every Phase 1 demonstration round (4 rounds × detailed display)  
- Create comprehensive Phase 2 group decision results with full constraint analysis
- Support detailed multilingual display across both phases

## Files Modified

1. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py` - Add comprehensive Phase 1 and Phase 2 displays
2. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase1_manager.py` - Integrate comprehensive Phase 1 demonstration results display  
3. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py` - Integrate comprehensive Phase 2 results display
4. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json` - Add comprehensive Phase 1 and Phase 2 translation keys
5. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json` - Add comprehensive Phase 1 and Phase 2 translation keys  
6. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json` - Add comprehensive Phase 1 and Phase 2 translation keys

## Testing Requirements

1. **Phase 1 Display Tests**: Validate comprehensive demonstration round results show correct constraint mappings for all 4 rounds
2. **Phase 2 Display Tests**: Verify group decision results display correctly with full constraint analysis and prominent actual earnings
3. **Constraint Mapping Tests**: Validate that each constraint value correctly maps to expected distribution selection across both phases
4. **Earnings Calculation Tests**: Verify agent earnings are calculated correctly for each income class across all constraint scenarios in both phases
5. **Display Format Tests**: Check that comprehensive results display properly formats tables, headers, and earnings breakdown for both phases
6. **Language Tests**: Verify all three languages display the detailed constraint mappings correctly with proper formatting
7. **Edge Case Tests**: Test scenarios with unusual distribution patterns or constraint values
8. **End-to-End**: Run complete two-phase experiments with various agent configurations to validate comprehensive display experience

This plan provides agents with comprehensive principle outcome displays during Phase 1 demonstration rounds (4 times) and after Phase 2 group discussion. Agents see detailed constraint-to-distribution mappings and their personal earnings under all possible principle choices, enabling thorough understanding of the decision landscape in both experimental phases. The approach maintains the existing services-first architecture while significantly enhancing the clarity and educational value of the experiment.