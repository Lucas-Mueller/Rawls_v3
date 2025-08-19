# Ghost Agent Technical Assessment

## Investigation Validation

The original investigation is **correct**. This is a data contamination issue, not an agent negotiation tactic.

## Root Cause Analysis

**Problem**: The `GroupDiscussionState.public_history` string field accumulates conversation logs without validation of participant names against the configured agent list.

**Location**: `models/experiment_types.py:149`
```python
self.public_history += f"\n{participant_name}: {statement}"
```

**Contamination Vector**: If a `GroupDiscussionState` object persists between experiments or agent memory contains contaminated conversation history, Agent 4 statements can leak into a 3-agent experiment.

## The Critical Fix

Add participant validation in `GroupDiscussionState.add_statement()`:

```python
def add_statement(self, participant_name: str, statement: str, valid_participants: List[str] = None):
    """Add statement to public history with participant validation."""
    if valid_participants and participant_name not in valid_participants:
        raise ValueError(f"Invalid participant '{participant_name}' not in configured agents: {valid_participants}")
    
    statement_obj = DiscussionStatement(
        participant_name=participant_name,
        statement=statement,
        round_number=self.round_number
    )
    self.statements.append(statement_obj)
    self.public_history += f"\n{participant_name}: {statement}"
```

## Conclusion

This single validation check would have prevented the ghost agent incident by rejecting any statements from unconfigured participants. The investigation correctly identified the system failure and provided accurate recommendations.