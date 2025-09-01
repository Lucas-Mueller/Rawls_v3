#!/usr/bin/env python3
"""
Test script to investigate the "compromise forgetting" issue during voting phase.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.memory_summarizer import MemorySummarizer, SummaryContext
from utils.language_manager import LanguageManager


def test_compromise_forgetting_issue():
    """Test how compromise information is preserved/lost in memory summarization."""
    print("🔍 Testing Compromise Forgetting Issue")
    print("=" * 60)
    
    # Simulate a realistic memory after discussion with compromise
    realistic_memory_with_compromise = """
    In my initial ranking, I placed maximizing floor income first because I believe in protecting the worst-off. 
    After Phase 1, I learned that floor principle earned me $9.60 total across four rounds, performing best in 3 out of 4 rounds.

    Phase 2 Discussion:
    Round 1: I argued for floor principle to protect the most vulnerable members of society. Alice disagreed, 
    saying efficiency should be the priority through maximizing average income.
    
    Round 2: Bob proposed a compromise: "What if we use maximizing average with floor constraint at $18,000? 
    This gives us efficiency while protecting the poor." I responded: "That sounds reasonable - $18,000 
    floor constraint could work as a compromise between pure efficiency and protection."
    
    Round 3: Alice stated: "I can accept the $18,000 floor constraint compromise. It's not my first choice 
    but I see the value in protecting the worst-off while still encouraging efficiency." Charlie agreed: 
    "Yes, $18,000 floor constraint seems like a good middle ground that everyone can support."
    
    Round 4: I confirmed our group consensus: "So we're all agreeing on maximizing average with floor 
    constraint at $18,000? This protects people from extreme poverty while still incentivizing overall 
    productivity." Everyone agreed this was our compromise position.
    
    We reached strong consensus on principle 3 (maximizing average with floor constraint) with $18,000 
    as the floor amount. This represents a compromise between my preference for pure floor protection 
    and Alice's preference for pure efficiency maximization.
    """
    
    # Initialize language manager
    language_manager = LanguageManager()
    language_manager.set_language(language_manager.current_language)
    
    print("📝 Full Memory Content (What agent actually remembers):")
    print("-" * 50)
    print(realistic_memory_with_compromise[:500] + "...\n")
    
    print("🗣️ Discussion Context Summary (What agent sees during discussion):")
    print("-" * 50)
    discussion_summary = MemorySummarizer.create_summary(
        realistic_memory_with_compromise, 
        SummaryContext.DISCUSSION, 
        max_lines=4
    )
    print(discussion_summary)
    print()
    
    print("🗳️ Voting Context Summary (What agent sees during voting):")
    print("-" * 50)
    voting_summary = MemorySummarizer.create_summary(
        realistic_memory_with_compromise, 
        SummaryContext.VOTING, 
        max_lines=4
    )
    print(voting_summary)
    print()
    
    # Show formatted memory displays
    print("🖥️ Formatted Memory Display Comparison:")
    print("-" * 50)
    
    print("During Discussion (compact mode, discussion context):")
    discussion_display = language_manager.format_memory_section(
        realistic_memory_with_compromise, 
        display_mode="compact", 
        context_type="discussion"
    )
    print(discussion_display)
    print()
    
    print("During Voting (compact mode, voting context):")
    voting_display = language_manager.format_memory_section(
        realistic_memory_with_compromise, 
        display_mode="compact", 
        context_type="voting"
    )
    print(voting_display)
    print()
    
    # Analyze what's lost
    print("🔍 Analysis of Information Loss:")
    print("-" * 50)
    
    compromise_keywords = [
        "compromise", "consensus", "$18,000", "agreed", "everyone", 
        "middle ground", "reasonable", "accept", "floor constraint"
    ]
    
    print("Compromise indicators in full memory:")
    for keyword in compromise_keywords:
        count = realistic_memory_with_compromise.lower().count(keyword.lower())
        print(f"  '{keyword}': {count} mentions")
    
    print(f"\nCompromise indicators in discussion summary:")
    for keyword in compromise_keywords:
        count = discussion_summary.lower().count(keyword.lower())
        print(f"  '{keyword}': {count} mentions")
        
    print(f"\nCompromise indicators in voting summary:")
    for keyword in compromise_keywords:
        count = voting_summary.lower().count(keyword.lower())
        print(f"  '{keyword}': {count} mentions")
    
    # Test insight extraction
    print(f"\n🎯 Key Insights Extraction:")
    print("-" * 50)
    insights = MemorySummarizer.extract_key_insights(realistic_memory_with_compromise)
    print("Extracted insights:")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. {insight}")
    
    # Check if compromise details are preserved
    compromise_preserved_in_voting = any(
        keyword in voting_summary.lower() 
        for keyword in ["18000", "$18,000", "consensus", "compromise", "agreed"]
    )
    
    compromise_preserved_in_discussion = any(
        keyword in discussion_summary.lower() 
        for keyword in ["18000", "$18,000", "consensus", "compromise", "agreed"]
    )
    
    print(f"\n🚨 Issue Analysis:")
    print("-" * 50)
    print(f"Compromise details preserved in discussion context: {compromise_preserved_in_discussion}")
    print(f"Compromise details preserved in voting context: {compromise_preserved_in_voting}")
    
    if not compromise_preserved_in_voting:
        print("\n❌ PROBLEM IDENTIFIED:")
        print("   Voting context summary loses critical compromise information!")
        print("   Agents may 'forget' the specific agreed-upon details during voting.")
    
    if compromise_preserved_in_voting and compromise_preserved_in_discussion:
        print("\n✅ No issue detected in this test case")
        
    return compromise_preserved_in_voting


def test_voting_vs_discussion_context_detection():
    """Test how context is detected during different phases."""
    print(f"\n🔧 Testing Context Detection Logic")
    print("=" * 60)
    
    from experiment_agents.participant_agent import _detect_memory_context_type
    from models.experiment_types import ParticipantContext, ExperimentPhase
    from unittest.mock import MagicMock
    
    # Create mock context
    context = MagicMock()
    context.phase = ExperimentPhase.PHASE_2
    context.round_number = 3
    
    # Test different role descriptions
    test_cases = [
        ("Regular discussion", "Phase 2 Group Discussion"),
        ("Vote initiation", "Phase 2 - Vote Initiation"),
        ("Voting confirmation", "Phase 2 - Voting Confirmation"),
        ("Secret ballot", "Phase 2 - Secret ballot selection"),
        ("Ballot voting", "Phase 2 - ballot"),
        ("Consensus checking", "Phase 2 - checking consensus"),
    ]
    
    print("Role Description → Detected Context Type:")
    for description, role_description in test_cases:
        detected_type = _detect_memory_context_type(context, role_description)
        print(f"  {description:20} → {detected_type}")
    
    # Check if ballot context is detected correctly
    ballot_context_detected = _detect_memory_context_type(context, "ballot")
    print(f"\nBallot context detection: {ballot_context_detected}")


def test_memory_extraction_methods():
    """Test the specific memory extraction methods used in voting summaries."""
    print(f"\n🔬 Testing Memory Extraction Methods")
    print("=" * 60)
    
    test_memory = """
    Phase 1: I earned $9.60 total. Floor principle performed best.
    
    Round 2: Bob proposed $18,000 floor constraint as compromise. I agreed this was reasonable.
    Round 3: Alice accepted the $18,000 compromise. Charlie supported it too.  
    Round 4: We reached consensus on principle 3 with $18,000 floor constraint.
    
    Group consensus: Everyone agreed on maximizing average with $18,000 floor constraint.
    Current position: Support the agreed compromise of $18,000 floor constraint.
    """
    
    # Test voting-specific extraction methods
    best_principle = MemorySummarizer._extract_best_principle(test_memory)
    voting_status = MemorySummarizer._extract_voting_status(test_memory)
    group_dynamics = MemorySummarizer._extract_group_dynamics(test_memory)
    current_preference = MemorySummarizer._extract_current_preference(test_memory)
    
    print("Extraction Results:")
    print(f"  Best principle: {best_principle}")
    print(f"  Voting status: {voting_status}")  
    print(f"  Group dynamics: {group_dynamics}")
    print(f"  Current preference: {current_preference}")
    
    # Check if $18,000 compromise is captured
    compromise_captured = any([
        voting_status and "18" in str(voting_status),
        group_dynamics and "18" in str(group_dynamics), 
        current_preference and "18" in str(current_preference)
    ])
    
    print(f"\nCompromise amount ($18,000) captured: {compromise_captured}")
    

def run_all_tests():
    """Run comprehensive test suite for compromise forgetting issue."""
    print("🧪 Compromise Forgetting Issue Investigation")
    print("=" * 70)
    
    try:
        # Main test
        compromise_preserved = test_compromise_forgetting_issue()
        
        # Additional tests
        test_voting_vs_discussion_context_detection()
        test_memory_extraction_methods()
        
        print(f"\n📊 Summary:")
        print("=" * 70)
        
        if not compromise_preserved:
            print("❌ CRITICAL ISSUE CONFIRMED:")
            print("   Agents lose compromise details during voting phase")
            print("   Root cause: Voting context summarization drops group consensus info")
            print("   Impact: Agents may vote inconsistently with previous agreements")
            
            print(f"\n🔧 Recommended Fixes:")
            print("   1. Enhance voting context summarization to preserve group agreements")
            print("   2. Add specific compromise/consensus extraction patterns")  
            print("   3. Consider using 'discussion' context during voting for better retention")
            print("   4. Add configuration option to show full memory during voting")
            
        else:
            print("✅ No critical issues detected in this test scenario")
            print("   Compromise information appears to be preserved")
            
        print(f"\n🎯 Next Steps:")
        print("   → Test with real experiment data to confirm issue")
        print("   → Implement enhanced voting context summarization")
        print("   → Add compromise-specific memory patterns")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()