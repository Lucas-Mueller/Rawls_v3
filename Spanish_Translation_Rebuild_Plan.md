# Spanish Translation Rebuild Plan

## Overview
This document outlines the comprehensive plan to rebuild Spanish translations from the ground up, using the updated English version as the source. The current Spanish translation appears outdated compared to the significantly expanded English prompts.

## Current State Analysis

### English Source (english_prompts.json)
- **Total entries**: ~122 translation keys
- **Structure**: 
  - `common` section: principle_names, income_classes, certainty_levels
  - `prompts` section: comprehensive experimental prompts, utility functions, system messages
- **Recent updates**: Substantial expansion with new features like:
  - Enhanced voting mechanisms
  - Complex discussion prompts  
  - Detailed utility agent instructions
  - Comprehensive error handling messages
  - Memory management prompts
  - Validation and parsing instructions

### Current Spanish Translation (spanish_prompts.json)
- **Status**: Outdated, missing many new entries
- **Inconsistencies**: Some terminology variations
- **Gaps**: Missing recent additions from English updates

## Translation Strategy

### 1. Consistency Framework
Create a **terminology dictionary** for consistent translation of key concepts:

#### Core Justice Principles (CRITICAL FOR CONSISTENCY)
- `maximizing_floor` → "Maximizar el ingreso mínimo"
- `maximizing_average` → "Maximizar el ingreso promedio" 
- `maximizing_average_floor_constraint` → "Maximizar el ingreso promedio con restricción de ingreso mínimo"
- `maximizing_average_range_constraint` → "Maximizar el ingreso promedio con restricción de rango"

#### Income Classes
- `high` → "Alta"
- `medium_high` → "Medio alto" 
- `medium` → "Medio"
- `medium_low` → "Medio bajo"
- `low` → "Bajo"

#### Certainty Levels
- `very_unsure` → "muy inseguro"
- `unsure` → "inseguro"
- `no_opinion` → "sin opinión"
- `sure` → "seguro"
- `very_sure` → "muy seguro"

#### Technical Terms
- `constraint` → "restricción"
- `floor constraint` → "restricción de ingreso mínimo"
- `range constraint` → "restricción de rango"
- `distribution` → "distribución"
- `principle` → "principio"
- `consensus` → "consenso"
- `voting` → "votación"
- `ballot` → "voto/papeleta"

### 2. Translation Process

#### Phase 1: DeepL Translation
For each English entry:
1. **Extract** the English text
2. **Translate** using DeepL MCP
3. **Document** the initial DeepL output
4. **Flag** any terminology that needs consistency checks

#### Phase 2: Evaluation and Refinement
For each DeepL translation:
1. **Check consistency** against terminology dictionary
2. **Evaluate context** - ensure translation fits experimental context
3. **Assess tone** - maintain formal but accessible academic tone
4. **Verify technical accuracy** - especially for experimental instructions

#### Phase 3: Contextual Optimization
1. **Long prompts**: Ensure coherent flow in Spanish
2. **Instructions**: Adapt to Spanish linguistic patterns while preserving precision
3. **Examples**: Modify examples to be natural in Spanish
4. **Cultural adaptation**: Adjust where needed for Spanish-speaking context

### 3. Quality Assurance

#### Consistency Checks
- [ ] All four justice principles translated identically across all contexts
- [ ] Income classes uniform throughout
- [ ] Certainty levels consistent
- [ ] Technical terms standardized

#### Functional Validation
- [ ] Experimental instructions clear and actionable
- [ ] Response format examples properly translated
- [ ] Error messages informative and helpful
- [ ] System prompts maintain experimental integrity

#### Linguistic Quality
- [ ] Natural Spanish phrasing
- [ ] Appropriate formality level
- [ ] Clear and unambiguous instructions
- [ ] Grammatically correct

## Implementation Plan

### Step 1: Preparation (15 minutes)
- [ ] Set up DeepL MCP access
- [ ] Create terminology tracking spreadsheet
- [ ] Backup current spanish_prompts.json

### Step 2: Common Section Translation (30 minutes)
- [ ] Translate `principle_names` (ensuring perfect consistency)
- [ ] Translate `income_classes`
- [ ] Translate `certainty_levels`
- [ ] Verify consistency with existing good translations

### Step 3: Core Experimental Prompts (60 minutes)
Priority order:
1. **experiment_explanation** - Foundation prompt
2. **phase1_round0_initial_ranking** - Initial ranking instructions
3. **phase1_rounds1_4_principle_application** - Core application prompts
4. **phase1_round5_final_ranking** - Final ranking
5. **phase2_discussion_prompt_simple** - Group discussion (simple mode)
6. **phase2_discussion_prompt_complex** - Group discussion (complex mode)

### Step 4: Utility Agent Prompts (45 minutes)
- [ ] All `utility_*` prompts for parsing and validation
- [ ] Ensure technical precision for AI agent instructions
- [ ] Maintain parsing format requirements

### Step 5: System Messages and Formatting (30 minutes)
- [ ] Error messages (`system_error_messages_*`)
- [ ] Success messages (`system_success_messages_*`)
- [ ] Status messages (`system_status_messages_*`)
- [ ] Format strings (`format_*`)

### Step 6: Memory and Context Prompts (30 minutes)
- [ ] Memory management prompts (`memory_*`)
- [ ] Context formatting prompts (`context_*`)
- [ ] Validation messages (`validation_*`)

### Step 7: Phase-Specific Prompts (30 minutes)
- [ ] Remaining `phase1_*` prompts
- [ ] Remaining `phase2_*` prompts
- [ ] Distribution and table formatting prompts

### Step 8: Final Validation (30 minutes)
- [ ] Complete consistency check
- [ ] Compare entry count with English version
- [ ] Test key prompt translations for naturalness
- [ ] Final JSON validation

## Key Translation Challenges

### 1. Justice Principle Consistency
**Critical**: The four justice principles must be translated identically everywhere they appear. Any variation could confuse experimental participants.

### 2. Technical Precision
Utility agent prompts require exact technical language to ensure AI parsing works correctly.

### 3. Experimental Instructions
Must be clear and actionable while maintaining the experimental validity.

### 4. Response Format Examples
Need to adapt examples to Spanish while preserving the required format structure.

### 5. Cultural Context
Adapt monetary examples and cultural references appropriately for Spanish-speaking participants.

## Success Metrics

### Quantitative
- [ ] 100% of English entries translated
- [ ] 0 inconsistencies in core terminology
- [ ] JSON validates successfully
- [ ] Character count similar to English (±20%)

### Qualitative  
- [ ] Natural Spanish phrasing throughout
- [ ] Experimental integrity maintained
- [ ] Instructions clear to Spanish speakers
- [ ] Technical prompts precise and functional

## Risk Mitigation

### Terminology Drift
**Risk**: Inconsistent translation of key terms across entries
**Mitigation**: Maintain live terminology dictionary, frequent consistency checks

### Technical Prompt Errors
**Risk**: Utility agent prompts lose technical precision
**Mitigation**: Careful review of all parsing/validation prompts

### Context Loss
**Risk**: Long prompts lose coherence in translation
**Mitigation**: Review entire prompt context, not just individual sentences

### JSON Structure Issues
**Risk**: Translation process breaks JSON structure
**Mitigation**: Regular JSON validation during process

## Timeline Estimate
**Total estimated time**: 4.5 hours
- Preparation: 15 minutes
- Translation phases: 3.5 hours  
- Final validation: 30 minutes
- Buffer for revisions: 30 minutes

## Post-Implementation
1. **Testing**: Test key prompts with Spanish speakers
2. **Documentation**: Update any documentation referencing translations
3. **Backup**: Archive old Spanish version for reference
4. **Monitoring**: Track any issues in Spanish experiment runs

---

**Note**: This plan prioritizes consistency and experimental integrity while ensuring natural Spanish language flow. The four justice principles are the absolute critical consistency requirement - any variation could invalidate experimental results.