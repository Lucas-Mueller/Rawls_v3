# Ranking Extraction Issue Investigation Report

**Date**: August 10, 2025  
**Investigator**: Claude Code  
**Issue Description**: Agent rankings are not being properly extracted from agent responses during experiment execution, particularly evident in Jupyter notebook experiment runs.

## Executive Summary

A critical issue has been identified in the ranking extraction and logging system. Agents are consistently reporting that their stated rankings differ from what the system has recorded and logged in the experiment results. The agents' memory entries contain explicit "Discrepancy Notes" indicating that the system recorded different rankings and certainty levels than what they actually stated in their detailed responses.

## Issue Details

### Primary Symptoms

1. **Ranking Mismatch**: Agents report that their stated rankings do not match what appears in the `ranking_result` structures in the JSON logs
2. **Certainty Level Errors**: Agents report stating they were "sure" or "very sure" while the system records "unsure"
3. **Consistent Pattern**: This appears to affect multiple ranking steps (initial ranking, post-explanation ranking, final ranking)
4. **Agent Awareness**: The agents themselves are explicitly noting these discrepancies in their memory updates

### Evidence from Investigation

#### Example from `hypothesis_2_&_4/config_01_results_20250810_094637.json`:

**Agent's Self-Reported Ranking (from memory)**:
```
1. **Maximizing the average income with a floor constraint:** My top choice
2. **Maximizing the floor income:** A close second
3. **Maximizing the average income with a range constraint:** A less preferred option
4. **Maximizing the average income:** My last choice
Certainty: I was "sure" about my reasoning and this ranking
```

**System-Recorded Ranking**:
```json
"ranking_result": {
  "rankings": [
    {"principle": "maximizing_floor", "rank": 1},
    {"principle": "maximizing_average", "rank": 2},
    {"principle": "maximizing_average_floor_constraint", "rank": 3},
    {"principle": "maximizing_average_range_constraint", "rank": 4}
  ],
  "certainty": "unsure"
}
```

**Agent's Explicit Complaint**:
> "Discrepancy Note: The system recorded my ranking and certainty incorrectly. It logged my #1 as 'Maximizing the floor income' and my certainty as 'unsure'. I will stick to my written reasoning, as it reflects my actual beliefs."

## Technical Analysis

### System Flow Investigation

1. **Agent Response Generation**: Agents provide detailed text responses with their rankings
2. **Utility Agent Parsing**: The `UtilityAgent.parse_principle_ranking_enhanced()` method processes the text response
3. **Parsing Prompt**: Uses `utility_parse_principle_ranking` template from language manager
4. **Result Storage**: Parsed rankings are stored as `PrincipleRankingResult` objects
5. **Logging**: Results are logged via `AgentCentricLogger.log_initial_ranking()`

### Key Files Involved

- **`experiment_agents/utility_agent.py`**: Contains parsing logic (`parse_principle_ranking_enhanced()`)
- **`utils/language_manager.py`**: Contains parsing prompt templates
- **`models/logging_types.py`**: Defines `PrincipleRankingResult.from_principle_ranking()`
- **`core/phase1_manager.py`**: Orchestrates ranking collection and parsing
- **`utils/agent_centric_logger.py`**: Handles result logging

### Parsing Prompt Analysis

The utility agent uses this prompt template:
```
Parse the following participant response to extract their complete ranking of justice principles:

Response: "{response}"

Extract a complete ranking of all 4 principles from best (rank 1) to worst (rank 4).
Also extract the overall certainty level for the entire ranking.

Return the parsed data as a dictionary with:
- rankings: list of {{principle, rank}} objects (no individual certainty levels)
- certainty: overall certainty level for the entire ranking
```

### Root Cause Analysis

The issue appears to stem from one or more of the following:

1. **Utility Agent Parsing Failure**: The parsing agent may be misinterpreting the natural language rankings provided by participant agents
2. **Pattern Matching Issues**: The enhanced parsing with regex patterns may be incorrectly identifying principles
3. **Fallback Logic Problems**: The fallback parsing may be activating and providing default/incorrect rankings
4. **Agent Model Inconsistency**: Different models (like `google/gemini-2.5-pro` used in the problematic config) may provide responses in formats that the parsing logic struggles with

## Impact Assessment

### Experiment Integrity
- **High**: Agent decisions and group dynamics in Phase 2 may be based on incorrect ranking data
- **High**: Agents are explicitly noting these discrepancies, indicating awareness of system failures
- **High**: Final consensus formation may be compromised if agents' true preferences are misrepresented

### Data Validity
- **Critical**: Experiment results showing agent preferences may be completely inaccurate
- **Critical**: Any analysis based on ranking data will be fundamentally flawed
- **High**: Agent behavior modeling becomes unreliable when based on incorrect preference data

### System Trust
- **High**: Agents are developing distrust of the system ("The data the system is showing us is totally unreliable")
- **Medium**: This may affect agent behavior and experiment authenticity

## Specific Observations

### Pattern Consistency
- The issue appears in multiple ranking phases (initial, post-explanation, final)
- Multiple agents in the same experiment report similar discrepancies
- The issue persists across different models (Google Gemini 2.5 Pro in the observed case)

### Agent Sophistication
- Agents are sophisticated enough to notice and explicitly document these discrepancies
- Agents maintain their true preferences in memory despite system errors
- Agents attempt to correct the record during group discussions

## Recommendations

### Immediate Actions Needed
1. **Suspend Experiments**: Until this issue is resolved, experiment results should be considered unreliable
2. **Debug Utility Agent**: Add extensive logging to the utility agent parsing process to trace exactly what's happening
3. **Validate Parsing Prompts**: Test the parsing prompts with various agent response formats
4. **Model-Specific Testing**: Test with different LLM models to identify if certain models produce responses that consistently fail parsing

### Medium-Term Fixes
1. **Enhanced Validation**: Add validation that compares agent responses with parsed results
2. **Agent Confirmation**: Consider implementing a confirmation step where agents validate their parsed rankings
3. **Improved Error Detection**: Add automated detection of parsing failures and discrepancies
4. **Fallback Prevention**: Review and improve the fallback parsing logic to avoid defaults

### Long-Term Solutions
1. **Structured Output**: Consider moving to more structured output formats that are less prone to parsing errors
2. **Multi-Step Parsing**: Implement multi-step parsing with validation at each step
3. **Agent Feedback Loop**: Implement feedback mechanisms where agents can correct parsing errors

## Conclusion

This is a critical system integrity issue that fundamentally undermines the reliability of the Frohlich Experiment. The agents' own testimony provides clear evidence that the ranking extraction system is consistently failing to capture their true preferences. This issue must be resolved before any further experiments are conducted, as the current data cannot be considered valid for research purposes.

The fact that agents are explicitly documenting these discrepancies in their memory indicates both the severity of the problem and the sophistication of the AI agents in detecting system failures. This presents both a challenge (the system is broken) and an opportunity (the agents can help us debug and improve the system).

## Next Steps

1. **Immediate investigation** of the utility agent parsing logic
2. **Comprehensive testing** with various response formats and models
3. **Implementation of validation mechanisms** to prevent this issue in future experiments
4. **Revalidation** of existing experiment data once the issue is resolved