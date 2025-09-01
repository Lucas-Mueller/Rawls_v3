CRITICAL ISSUE CONFIRMED: "Compromise Forgetting" Problem

  The investigation has revealed a severe issue with the memory optimization that could be undermining experimental validity. Here's the comprehensive analysis:

  ---
  🔍 Root Cause Analysis

  The Problem Chain:

  1. Discussion Phase: Agents negotiate and reach compromise (e.g., "$18,000 floor constraint")
  2. Context Switch: System switches from "discussion" to "voting" context detection
  3. Memory Summarization: Different summarization logic strips out compromise details
  4. Voting Phase: Agents receive heavily summarized memory without compromise information
  5. Result: Agents vote inconsistently with their previous agreements

  Evidence from Testing:

  Full Memory Contains:
  - compromise: 5 mentions
  - $18,000: 6 mentions
  - consensus: 2 mentions
  - agreed: 3 mentions
  - floor constraint: 5 mentions

  Voting Context Summary Contains:
  - compromise: 0 mentions ❌
  - $18,000: 0 mentions ❌
  - consensus: 0 mentions ❌
  - agreed: 0 mentions ❌
  - floor constraint: 0 mentions ❌

  ---
  🎯 Specific Technical Issues

  1. Context Detection Problems:

  # Context detection logic (participant_agent.py:187)
  if any(keyword in role_description.lower() for keyword in ["vote", "ballot", "consensus"]):
      return "voting"  # ← Triggers voting context summarization

  2. Voting Summarization is Too Narrow:

  def _create_voting_summary(full_memory, insights, max_lines):
      # Only extracts: Phase 1 earnings, best principle, voting info, generic insights
      # ❌ MISSING: Group agreements, compromise details, consensus amounts

  3. Key Information Loss Points:

  - $18,000 compromise amount → Not extracted by voting patterns
  - Group consensus statements → Not prioritized in voting context
  - "Everyone agreed on..." → Lost in generic insight extraction
  - Specific principle+constraint combinations → Not preserved in voting format

  ---
  🔧 Immediate Fix Recommendations

  Option 1: Enhanced Voting Context Summarization (Recommended)

  Update _create_voting_summary() to preserve compromise details:

  def _create_voting_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
      lines = []

      # 1. Extract compromise/consensus information FIRST
      compromise_info = _extract_compromise_details(full_memory)
      if compromise_info:
          lines.append(f"Group consensus: {compromise_info}")

      # 2. Phase 1 performance (existing)
      earnings_match = re.search(r"total.*?earnings?.*?\$?([\d,]+\.?\d*)", full_memory, re.IGNORECASE)
      if earnings_match:
          lines.append(f"Phase 1: Earned ${earnings_match.group(1)} total.")

      # 3. Specific agreed amounts/principles
      agreed_amount = _extract_agreed_amount(full_memory)
      if agreed_amount:
          lines.append(f"Agreed amount: {agreed_amount}")

      return " ".join(lines[:max_lines])

  def _extract_compromise_details(memory: str) -> Optional[str]:
      """Extract compromise/consensus statements."""
      patterns = [
          r"(?:consensus|agreed|compromise).*?(?:\$?[\d,]+|principle \d+|floor constraint)",
          r"everyone.*?(?:agreed|support|accept).*?(?:\$?[\d,]+|principle \d+)",
          r"(?:group|all).*?(?:consensus|agreement).*?(?:\$?[\d,]+|principle \d+)"
      ]
      # Implementation details...

  Option 2: Use Discussion Context During Voting

  Modify context detection to preserve discussion context during voting:

  def _detect_memory_context_type(context, role_description):
      # Keep discussion context until final results
      if context.phase == ExperimentPhase.PHASE_2:
          if "final results" not in role_description.lower():
              return "discussion"  # Always use discussion context in Phase 2
      # Other logic...

  Option 3: Configuration Override for Critical Voting

  Add option to use full memory during voting:

  memory_optimization:
    use_full_memory_during_voting: true  # Override summarization for voting
    voting_memory_priority: "consensus"  # Prioritize group agreements

  ---
  ⚡ Immediate Action Items

  High Priority (Fix Immediately):

  1. Implement enhanced voting context summarization with compromise extraction
  2. Add compromise/consensus-specific regex patterns
  3. Test with real experiment data to validate fix
  4. Add configuration option to disable optimization during voting if needed

  Medium Priority:

  1. Improve context detection logic to better identify voting vs discussion
  2. Add validation tests for compromise retention across context switches
  3. Implement memory content validation to ensure critical info preservation

  Testing Needed:

  1. Run experiment with current system → Document "forgetting" instances
  2. Apply fixes → Re-run same scenario
  3. Compare agent consistency before/after voting context switch
  4. Measure compromise retention rates across different scenarios

  ---
  💥 Impact Assessment

  Experimental Validity Risk: HIGH 🔴
  - Agents may vote against previously agreed compromises
  - Results may not reflect genuine consensus-building
  - Phase 2 outcomes could be artificially inconsistent

  Fix Complexity: MEDIUM 🟡
  - Requires enhanced pattern matching for compromise extraction
  - Need to balance summarization efficiency with information preservation
  - Should maintain backward compatibility

  This issue likely explains why you're seeing agents "forget" their compromise agreements during voting! The memory optimization, while improving performance, inadvertently strips out the most critical information needed for consistent voting behavior.