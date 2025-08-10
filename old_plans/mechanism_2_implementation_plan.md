# Mechanism 2: Constraint Discovery Support Implementation Plan

## Overview

This document outlines the implementation plan for Mechanism 2, which provides constraint discovery support to help agents coordinate on specific constraint values during Phase 2 group discussion. This mechanism maintains the current system architecture while adding negotiation scaffolding and Phase 1 insights sharing.

## Core Concept

**Problem**: Agents agree on principles but fail to coordinate on specific constraint amounts during group discussion due to lack of shared reference points and structured negotiation tools.

**Solution**: Leave Phase 1 unchanged. Enhance Phase 2 with Phase 1 insights sharing and negotiation scaffolding without changing the fundamental experimental structure.

## Implementation Components

### 1. Phase 2 Enhancements

#### 1.1 Phase 1 Constraint Insights Extraction

**File**: `core/phase2_manager.py`
**New Method**: `_extract_phase1_constraint_insights()`

**Purpose**: Extract constraint values used by each participant in Phase 1 for group context.

**Implementation**:
```python
def _extract_phase1_constraint_insights(self, phase1_results: List[Phase1Results]) -> Dict[str, List[int]]:
    """Extract constraint values used by participants in Phase 1."""
    insights = {
        'floor_constraints': [],
        'range_constraints': [],
        'participant_preferences': {}
    }
    
    for result in phase1_results:
        participant_constraints = []
        for app_result in result.application_results:
            if app_result.principle_choice.constraint_amount:
                participant_constraints.append({
                    'principle': app_result.principle_choice.principle,
                    'amount': app_result.principle_choice.constraint_amount,
                    'earnings': app_result.earnings
                })
        
        insights['participant_preferences'][result.participant_name] = participant_constraints
    
    return insights
```

#### 1.2 Constraint-Aware Discussion Prompts

**File**: `core/phase2_manager.py`
**Method**: `_build_discussion_prompt()`

**Enhancement**: Include Phase 1 constraint insights and negotiation guidance.

**Implementation**:
```python
def _build_discussion_prompt_with_constraint_support(
    self, 
    discussion_state: GroupDiscussionState, 
    round_num: int,
    constraint_insights: Dict[str, Any]
) -> str:
    """Enhanced discussion prompt with constraint negotiation support."""
    
    language_manager = get_language_manager()
    
    # Format constraint insights for display
    constraint_context = language_manager.format_constraint_insights(constraint_insights)
    
    return f"""
{language_manager.get("prompts.phase2_discussion_header", round_num=round_num)}

{language_manager.get("prompts.phase2_discussion_history_label")}
{discussion_state.public_history or language_manager.get("prompts.no_previous_discussion")}

{constraint_context}

{language_manager.get("prompts.phase2_constraint_negotiation_guidance")}

{language_manager.get("prompts.phase2_discussion_instructions")}
"""
```

#### 1.3 Constraint Value Convergence Support

**File**: `core/phase2_manager.py`
**New Method**: `_provide_constraint_convergence_support()`

**Purpose**: Help agents converge on constraint values by showing proposal summaries and suggesting compromises.

### 2. Language Support Implementation

#### 2.1 English Prompts Enhancement

**File**: `translations/english_prompts.json`

**New Prompts to Add**:

```json
{
  "prompts": {
    "phase1_constraint_guidance_header": "CONSTRAINT GUIDANCE:",
    "phase1_floor_constraint_guidance": "For floor constraints: Current distributions have minimum incomes from ${min_floor:,} to ${max_floor:,}\n- Consider: What minimum income ensures basic needs?\n- Typical range: ${suggested_min:,} to ${suggested_max:,}",
    "phase1_range_constraint_guidance": "For range constraints: Current distributions have income gaps from ${min_range:,} to ${max_range:,}\n- Consider: What income gap promotes fairness while maintaining incentives?\n- Typical range: ${suggested_min:,} to ${suggested_max:,}",
    
    "phase2_constraint_insights_header": "PHASE 1 CONSTRAINT INSIGHTS:",
    "phase2_constraint_insights_summary": "Constraint values used in Phase 1:\n{participant_summary}\nMost effective constraints: {effective_constraints}",
    "phase2_constraint_negotiation_guidance": "For constraint principles, consider:\n- What constraint values did you find effective in Phase 1?\n- What values did others use successfully?\n- Can you propose a specific amount or support another's proposal?\n- Can you suggest a compromise (e.g., average of proposals)?",
    
    "phase2_constraint_proposal_template": "To propose a constraint: 'I suggest a {constraint_type} constraint of ${amount:,} because {reasoning}'",
    "phase2_constraint_support_template": "To support a proposal: 'I support {participant}'s proposal of ${amount:,} because {reasoning}'",
    "phase2_constraint_compromise_template": "To suggest compromise: 'I propose we average the suggestions: ${average_amount:,}'"
  }
}
```

#### 2.2 Spanish Translation

**File**: `translations/spanish_prompts.json`

**New Prompts**:

```json
{
  "prompts": {
    "phase1_constraint_guidance_header": "GUÍA DE RESTRICCIONES:",
    "phase1_floor_constraint_guidance": "Para restricciones de piso: Las distribuciones actuales tienen ingresos mínimos de ${min_floor:,} a ${max_floor:,}\n- Considera: ¿Qué ingreso mínimo asegura las necesidades básicas?\n- Rango típico: ${suggested_min:,} a ${suggested_max:,}",
    "phase1_range_constraint_guidance": "Para restricciones de rango: Las distribuciones actuales tienen brechas de ingresos de ${min_range:,} a ${max_range:,}\n- Considera: ¿Qué brecha de ingresos promueve la equidad manteniendo incentivos?\n- Rango típico: ${suggested_min:,} a ${suggested_max:,}",
    
    "phase2_constraint_insights_header": "PERSPECTIVAS DE RESTRICCIONES DE FASE 1:",
    "phase2_constraint_insights_summary": "Valores de restricción usados en Fase 1:\n{participant_summary}\nRestricciones más efectivas: {effective_constraints}",
    "phase2_constraint_negotiation_guidance": "Para principios con restricciones, considera:\n- ¿Qué valores de restricción encontraste efectivos en Fase 1?\n- ¿Qué valores usaron otros exitosamente?\n- ¿Puedes proponer una cantidad específica o apoyar la propuesta de otro?\n- ¿Puedes sugerir un compromiso (ej. promedio de propuestas)?",
    
    "phase2_constraint_proposal_template": "Para proponer una restricción: 'Sugiero una restricción de {constraint_type} de ${amount:,} porque {reasoning}'",
    "phase2_constraint_support_template": "Para apoyar una propuesta: 'Apoyo la propuesta de {participant} de ${amount:,} porque {reasoning}'",
    "phase2_constraint_compromise_template": "Para sugerir compromiso: 'Propongo que promediemos las sugerencias: ${average_amount:,}'"
  }
}
```

#### 2.3 Mandarin Translation

**File**: `translations/mandarin_prompts.json`

**New Prompts**:

```json
{
  "prompts": {
    "phase1_constraint_guidance_header": "约束条件指导：",
    "phase1_floor_constraint_guidance": "对于底线约束：当前分配的最低收入从${min_floor:,}到${max_floor:,}\n- 考虑：什么最低收入能确保基本需求？\n- 典型范围：${suggested_min:,}到${suggested_max:,}",
    "phase1_range_constraint_guidance": "对于范围约束：当前分配的收入差距从${min_range:,}到${max_range:,}\n- 考虑：什么收入差距既促进公平又维持激励？\n- 典型范围：${suggested_min:,}到${suggested_max:,}",
    
    "phase2_constraint_insights_header": "第一阶段约束条件经验：",
    "phase2_constraint_insights_summary": "第一阶段使用的约束值：\n{participant_summary}\n最有效的约束条件：{effective_constraints}",
    "phase2_constraint_negotiation_guidance": "对于约束原则，请考虑：\n- 你在第一阶段发现哪些约束值有效？\n- 其他人成功使用了什么值？\n- 你能提出具体金额或支持他人的提议吗？\n- 你能建议妥协方案（例如提议的平均值）吗？",
    
    "phase2_constraint_proposal_template": "提议约束条件：'我建议{constraint_type}约束为${amount:,}，因为{reasoning}'",
    "phase2_constraint_support_template": "支持提议：'我支持{participant}的${amount:,}提议，因为{reasoning}'",
    "phase2_constraint_compromise_template": "建议妥协：'我建议我们取各建议的平均值：${average_amount:,}'"
  }
}
```

### 3. Language Manager Enhancements

#### 3.1 New Language Manager Methods

**File**: `utils/language_manager.py`

**New Methods to Add**:

```python
def get_constraint_guidance(self, distribution_context: Dict[str, Any]) -> str:
    """Generate localized constraint guidance based on distribution statistics."""
    
def format_constraint_insights(self, constraint_insights: Dict[str, Any]) -> str:
    """Format Phase 1 constraint insights for Phase 2 display."""
    
def get_constraint_negotiation_templates(self) -> Dict[str, str]:
    """Get templates for constraint proposal, support, and compromise."""
    
def format_constraint_proposals_summary(self, proposals: List[Dict]) -> str:
    """Format current constraint proposals for group visibility."""
```

### 4. Configuration Enhancements

#### 4.1 Experiment Configuration

**File**: `config/experiment_config.py`

**New Configuration Options**:

```python
@dataclass
class ConstraintSupportConfig:
    enabled: bool = True
    show_phase1_insights: bool = True
    provide_constraint_templates: bool = True
    highlight_effective_constraints: bool = True
    
@dataclass 
class ExperimentConfiguration:
    # ... existing fields
    constraint_support: ConstraintSupportConfig = field(default_factory=ConstraintSupportConfig)
```

#### 4.2 Configuration Files

**Files**: `config/english_config.yaml`, `config/spanish_config.yaml`, `config/mandarin_config.yaml`

**New Configuration Sections**:

```yaml
# Constraint Discovery Support Configuration
constraint_support:
  enabled: true
  show_phase1_insights: true
  provide_constraint_templates: true
  highlight_effective_constraints: true
```

### 5. Validation and Testing Enhancements

#### 5.1 Enhanced Utility Agent Capabilities

**File**: `experiment_agents/utility_agent.py`

**New Methods**:

```python
async def extract_constraint_proposals(self, statement: str) -> List[Dict[str, Any]]:
    """Extract constraint amount proposals from discussion statements."""
    
async def validate_constraint_reasonableness(self, constraint_amount: int, distribution_context: Dict) -> bool:
    """Validate if constraint amount is reasonable given distribution context."""
```

#### 5.2 Testing Framework

**New Test Files**:
- `tests/unit/test_constraint_support.py`
- `tests/integration/test_mechanism2_flow.py`

### 6. Implementation Phases

#### Phase 1: Foundation (Week 1)
1. Enhance language manager with new methods
2. Create multilingual prompt templates
3. Update configuration system

#### Phase 2: Phase 2 Enhancements (Week 2)
1. Add constraint insights extraction
2. Enhance discussion prompts with insights
3. Add constraint negotiation support
4. Test Phase 2 improvements

#### Phase 3: Integration and Testing (Week 3)
1. Full system integration testing
2. Multilingual testing with all three languages
3. Comparative testing against baseline
4. Performance and effectiveness validation

### 7. Success Metrics

#### Quantitative Metrics
1. **Consensus Achievement Rate**: Percentage of experiments reaching consensus
2. **Constraint Agreement Rate**: Percentage of groups agreeing on constraint amounts
3. **Discussion Quality**: Number of concrete constraint proposals per discussion
4. **Constraint Value Convergence**: Standard deviation of final constraint proposals

#### Qualitative Metrics
1. **Agent Engagement**: Quality of constraint-related reasoning in responses
2. **Negotiation Effectiveness**: Frequency of compromise proposals and counter-proposals
3. **Learning Transfer**: Evidence of Phase 1 constraint insights being used in Phase 2

### 8. Risk Mitigation

#### Technical Risks
- **Language Complexity**: Ensure accurate translations across all three languages
- **Performance Impact**: Monitor system performance with enhanced prompts
- **Backward Compatibility**: Maintain ability to run baseline experiments

#### Experimental Risks
- **Over-Guidance**: Risk of providing too much guidance that influences agent autonomy
- **Cultural Sensitivity**: Ensure constraint guidance is culturally appropriate across languages
- **Experimental Validity**: Maintain core experimental design integrity

### 9. Rollback Plan

If Mechanism 2 proves ineffective or problematic:

1. **Configuration Disable**: Set `constraint_support.enabled = false`
2. **Prompt Fallback**: Revert to original prompt templates
3. **Method Isolation**: New methods are additive and can be bypassed
4. **Data Preservation**: All original experimental data and behavior preserved

## Conclusion

This implementation plan provides a comprehensive approach to adding constraint discovery support while maintaining the experimental integrity and expanding language support. The phased approach allows for careful testing and validation at each step, with clear success metrics and risk mitigation strategies.

The key innovation is providing contextual anchoring and negotiation scaffolding without fundamentally changing the agent decision-making process, allowing for direct comparison with baseline results while significantly improving the tools available for constraint value coordination.