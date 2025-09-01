# Internationalization Plan for Phase 2 Manager and Models

## Executive Summary

This document outlines a comprehensive plan to address hardcoded English text throughout the Frohlich Experiment codebase, focusing on Phase 2 Manager and related components. The current system has extensive hardcoded English strings that prevent true multilingual operation, requiring systematic replacement with translation keys and dynamic localization.

## Current State Analysis

### Translation System Infrastructure
- **Language Manager**: Well-established system in `utils/language_manager.py`
- **Translation Files**: JSON-based translations for English, Spanish, and Mandarin
- **Dynamic Loading**: Translation keys accessible via dot notation (`language_manager.get()`)

### Problem Scope
The analysis identified **27 distinct locations** with hardcoded English text across:
- **Phase 2 Manager** (`core/phase2_manager.py`): 23 instances
- **Experiment Types** (`models/experiment_types.py`): 4 instances

## Hardcoded Text Categories

### 1. User-Facing Messages (High Priority)
- **Vote prompts retry hints**: "Please respond with exactly 1 (to vote now) or 0..."
- **Discussion retry messages**: "Please ensure your response contains a clear statement..."
- **Group composition descriptions**: "The current group consists of..."
- **Internal reasoning sections**: "Based on your internal reasoning above..."

### 2. Public History Tags and Messages (High Priority)
- **Voting status tags**: `[VOTING INITIATED]`, `[VOTING CONFIRMATION]`, `[VOTING RESULT]`, `[VOTING ERROR]`
- **Vote result summaries**: "Vote conducted - Consensus: Yes/No (Agreed on: ...)"
- **Truncation markers**: "...earlier discussion truncated..."
- **System notifications**: All agents receive English status updates

### 3. Results and Analysis Display (Medium Priority)
- **Results headers**: "PHASE 2 FINAL RESULTS", "COUNTERFACTUAL ANALYSIS"
- **Table headers**: "Justice Principle | Income | Earnings"
- **Status labels**: "Consensus Status:", "Key Insights:"
- **Income class displays**: "VERY HIGH/HIGH/MEDIUM/LOW/VERY LOW"

### 4. System Logic Text (Medium Priority)
- **Error handling**: Hardcoded fallback messages in voting systems
- **Memory update prompts**: Mixed English/localized content
- **Configuration-specific text**: Dynamic sentence construction

## Implementation Strategy

### Phase 1: Translation Key Expansion (Weeks 1-2)

#### 1.1 Add Missing Translation Keys
Add comprehensive translation keys to all language files:

```json
"system_messages": {
  "voting": {
    "initiated_tag": "[VOTING INITIATED]",
    "confirmation_tag": "[VOTING CONFIRMATION]", 
    "result_tag": "[VOTING RESULT]",
    "error_tag": "[VOTING ERROR]",
    "initiated_message": "{name} has initiated formal voting",
    "confirmation_success": "All participants agreed to proceed with voting",
    "confirmation_failed": "Confirmation failed - continuing discussion",
    "process_failed": "Two-stage voting process failed"
  },
  "discussion": {
    "truncation_marker": "...earlier discussion truncated...",
    "group_composition": "The current group consists of {participants}",
    "retry_hint": "Please ensure your response contains a clear statement about your position on the justice principles"
  }
}
```

#### 1.2 Results and Display Translations
```json
"results": {
  "phase2_header": "PHASE 2 FINAL RESULTS",
  "counterfactual_header": "COUNTERFACTUAL ANALYSIS - What you would have earned under each principle:",
  "table_headers": {
    "principle": "Justice Principle",
    "income": "Income", 
    "earnings": "Earnings"
  },
  "consensus_status": "Consensus Status:",
  "key_insights": "Key Insights:",
  "income_classes": {
    "very_high": "VERY HIGH",
    "high": "HIGH", 
    "medium": "MEDIUM",
    "low": "LOW",
    "very_low": "VERY LOW"
  }
}
```

#### 1.3 Voting System Messages
```json
"voting_prompts": {
  "retry_instruction": "⚠️ Please respond with exactly 1 (to vote now) or 0 (to continue discussion)",
  "internal_reasoning_section": "=== YOUR INTERNAL REASONING ===",
  "reasoning_prompt": "Based on your internal reasoning above, what is your statement to the group?"
}
```

### Phase 2: Code Refactoring (Weeks 3-4)

#### 2.1 Phase2Manager Refactoring
Replace hardcoded strings with translation calls:

**Before:**
```python
discussion_state.public_history += f"\n[VOTING INITIATED] {initiator.name} has initiated formal voting."
```

**After:**
```python
tag = self.language_manager.get("system_messages.voting.initiated_tag")
message = self.language_manager.get("system_messages.voting.initiated_message", name=initiator.name)
discussion_state.public_history += f"\n{tag} {message}"
```

#### 2.2 Results Generation Refactoring
**Before:**
```python
result_content = f"""PHASE 2 FINAL RESULTS

Consensus Status: {consensus_status}
```

**After:**
```python
header = self.language_manager.get("results.phase2_header")
status_label = self.language_manager.get("results.consensus_status")
result_content = f"""{header}

{status_label} {consensus_status}
```

#### 2.3 Dynamic Text Generation
Create helper methods for complex string construction:

```python
def _format_group_composition(self, participants: List[str]) -> str:
    """Format group composition message with proper localization."""
    participant_list = ", ".join(participants)
    return self.language_manager.get(
        "system_messages.discussion.group_composition", 
        participants=participant_list
    )

def _format_voting_tag_message(self, tag_key: str, message_key: str, **kwargs) -> str:
    """Format voting system messages with consistent tagging."""
    tag = self.language_manager.get(f"system_messages.voting.{tag_key}")
    message = self.language_manager.get(f"system_messages.voting.{message_key}", **kwargs)
    return f"{tag} {message}"
```

### Phase 3: Models Integration (Week 5)

#### 3.1 Experiment Types Refactoring
Update `models/experiment_types.py` vote result formatting:

**Before:**
```python
vote_summary = f"Vote conducted - Consensus: {'Yes' if vote_result.consensus_reached else 'No'}"
self.public_history += f"\n[VOTE RESULT] {vote_summary}"
```

**After:**
```python
def add_vote_result(self, vote_result: VoteResult, language_manager: LanguageManager):
    tag = language_manager.get("system_messages.voting.result_tag")
    consensus_text = language_manager.get("common.yes_no.yes" if vote_result.consensus_reached else "common.yes_no.no")
    vote_summary = language_manager.get("system_messages.voting.result_summary", consensus=consensus_text)
    if vote_result.consensus_reached and vote_result.agreed_principle:
        principle_name = language_manager.get_justice_principle_name(vote_result.agreed_principle.principle.value)
        vote_summary += language_manager.get("system_messages.voting.agreed_principle", principle=principle_name)
    self.public_history += f"\n{tag} {vote_summary}"
```

### Phase 4: Quality Assurance (Week 6)

#### 4.1 Translation Validation
- Implement automated validation for missing translation keys
- Add fallback handling for untranslated strings
- Create translation completeness reports

#### 4.2 Integration Testing
- Test all three languages (English, Spanish, Mandarin)
- Validate proper character encoding and display
- Ensure consistent terminology across all components

#### 4.3 Backward Compatibility
- Implement graceful degradation for missing translations
- Maintain system functionality during translation rollout
- Create migration path for existing experiments

## Implementation Details

### Translation Key Naming Convention
- **Hierarchical structure**: `category.subcategory.specific_key`
- **Consistent prefixes**: `system_messages.`, `results.`, `voting_prompts.`
- **Template support**: Use `{variable}` for dynamic content
- **Fallback handling**: English fallbacks for missing keys

### Code Integration Pattern
```python
# Standard pattern for all hardcoded text replacement
def _get_localized_message(self, key: str, **kwargs) -> str:
    """Get localized message with fallback handling."""
    try:
        return self.language_manager.get(key, **kwargs)
    except KeyError:
        self.logger.warning(f"Missing translation key: {key}")
        # Return English fallback or key name
        return f"[MISSING: {key}]"
```

### Memory Integration
Update memory management to use localized text:
```python
def _update_memory_with_localized_content(self, content_key: str, **kwargs):
    """Update agent memory with properly localized content."""
    localized_content = self.language_manager.get(content_key, **kwargs)
    # Update memory with localized content
```

## Risk Mitigation

### Technical Risks
1. **Translation Loading Performance**: Cache frequently used translations
2. **Character Encoding Issues**: Ensure UTF-8 handling throughout
3. **Template Formatting Errors**: Implement robust error handling

### Operational Risks
1. **Incomplete Translations**: Staged rollout with fallbacks
2. **Testing Coverage**: Comprehensive multilingual test suite
3. **Regression Issues**: Maintain English behavior during transition

## Success Metrics

### Functional Requirements
- **Zero hardcoded user-facing English text** in Phase 2 Manager
- **Consistent multilingual operation** across all supported languages
- **Proper localization** of all public history entries and system messages

### Quality Requirements
- **Translation coverage**: 100% of identified hardcoded text
- **Fallback reliability**: Graceful handling of missing translations
- **Performance impact**: <5% overhead from translation loading

## Timeline and Milestones

| Week | Milestone | Deliverables |
|------|-----------|-------------|
| 1-2 | Translation Expansion | Complete translation key additions |
| 3 | Core Refactoring | Phase2Manager hardcoded text removal |
| 4 | Integration Updates | Models and supporting component updates |
| 5 | System Integration | End-to-end multilingual functionality |
| 6 | Quality Assurance | Testing, validation, and documentation |

## Future Considerations

### Extensibility
- **New Language Support**: Framework for adding additional languages
- **Regional Variants**: Support for locale-specific variations
- **Cultural Adaptation**: Context-aware cultural considerations

### Maintenance
- **Translation Updates**: Workflow for maintaining translations
- **Key Management**: Systematic approach to translation key lifecycle
- **Quality Control**: Ongoing translation quality assurance

## Conclusion

This internationalization plan addresses all identified hardcoded English text while establishing a robust framework for multilingual operation. The systematic approach ensures complete coverage while maintaining system stability and performance. Implementation will result in true multilingual capability across the entire experiment framework.

The plan prioritizes user-facing text and system messages, ensuring that participants receive fully localized experiences regardless of their configured language setting. The modular approach allows for incremental implementation and testing, reducing deployment risk while maximizing translation coverage.