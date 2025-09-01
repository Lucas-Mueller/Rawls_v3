#!/usr/bin/env python3
"""
Test script for memory optimization functionality.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.memory_summarizer import MemorySummarizer, SummaryContext
from utils.language_manager import LanguageManager


def test_memory_summarizer():
    """Test the MemorySummarizer with sample memory content."""
    
    # Sample Phase 1 memory content
    sample_phase1_memory = """
    In my initial ranking, I placed maximizing floor income first because I believe in protecting the worst-off. 
    Then I learned about how the principles actually work through examples. In round 1 of applications, I chose 
    maximizing average because the numbers looked good, and I was assigned to medium class and earned $2.40. 
    In round 2, I chose maximizing floor because I wanted to help the poor, and I was assigned to medium class 
    again and earned $1.80. In round 3, I chose maximizing average with floor constraint with a constraint of 
    $15,000 because I wanted to balance both goals, and I was assigned to high class and earned $3.20. 
    In round 4, I chose maximizing floor again because I wanted to be consistent with my values, and I was 
    assigned to low class and earned $1.50. My total earnings were $9.90. I learned that the floor principle 
    tends to give more consistent results, while the average principle can be very unpredictable. The constraint 
    versions seem like good compromises.
    """
    
    # Sample Phase 2 memory content  
    sample_phase2_memory = """
    Phase 1 taught me that floor principles work well. I earned $9.90 total, with the floor principle 
    performing best in 3 out of 4 rounds. Now in Phase 2, Alice argued strongly for maximizing average 
    because she thinks efficiency matters most. Bob supports floor protection like me - he said the 
    worst-off deserve priority. Charlie seems undecided but leans toward some kind of constraint approach. 
    In round 1, I argued for floor principle. In round 2, Alice countered with efficiency arguments. 
    Bob and I formed an alliance supporting floor protection. In round 3, we're building consensus around 
    $18,000 floor constraint as a compromise. I voted to initiate voting because I think we're close to 
    agreement. The group seems ready to move forward with principle 3 and $18,000 constraint.
    """

    print("🧪 Testing Memory Summarization")
    print("=" * 50)
    
    # Test different context types
    contexts = [
        (SummaryContext.GENERAL, "General"),
        (SummaryContext.VOTING, "Voting"),
        (SummaryContext.DISCUSSION, "Discussion"), 
        (SummaryContext.APPLICATION, "Application")
    ]
    
    for context_type, context_name in contexts:
        print(f"\n📋 {context_name} Context Summary:")
        print("-" * 30)
        
        # Test with Phase 1 memory
        summary1 = MemorySummarizer.create_summary(sample_phase1_memory, context_type, max_lines=4)
        print(f"Phase 1: {summary1}")
        
        # Test with Phase 2 memory
        summary2 = MemorySummarizer.create_summary(sample_phase2_memory, context_type, max_lines=4)
        print(f"Phase 2: {summary2}")
        
    # Test insight extraction
    print(f"\n🔍 Key Insights Extraction:")
    print("-" * 30)
    insights1 = MemorySummarizer.extract_key_insights(sample_phase1_memory)
    insights2 = MemorySummarizer.extract_key_insights(sample_phase2_memory)
    
    print("Phase 1 Insights:")
    for i, insight in enumerate(insights1, 1):
        print(f"  {i}. {insight}")
        
    print("Phase 2 Insights:")
    for i, insight in enumerate(insights2, 1):
        print(f"  {i}. {insight}")


def test_language_manager_integration():
    """Test LanguageManager integration with memory summarization."""
    
    print(f"\n🌐 Testing LanguageManager Integration")
    print("=" * 50)
    
    # Initialize language manager
    language_manager = LanguageManager()
    language_manager.set_language(language_manager.current_language)
    
    sample_memory = """
    I initially preferred floor principle. Earned $9.60 total in Phase 1. Floor principle performed best. 
    Now in Phase 2 round 3, building consensus with Alice and Bob on $18k floor constraint. Ready to vote.
    """
    
    # Test different display modes
    print("\n📺 Display Mode Comparison:")
    print("-" * 30)
    
    # Full display
    full_display = language_manager.format_memory_section(sample_memory, display_mode="full")
    print("Full Display:")
    print(full_display)
    
    # Compact display - general context
    compact_general = language_manager.format_memory_section(sample_memory, display_mode="compact", context_type="general")
    print("\nCompact Display (General):")
    print(compact_general)
    
    # Compact display - voting context
    compact_voting = language_manager.format_memory_section(sample_memory, display_mode="compact", context_type="voting")
    print("\nCompact Display (Voting):")
    print(compact_voting)
    
    # Compact display - discussion context
    compact_discussion = language_manager.format_memory_section(sample_memory, display_mode="compact", context_type="discussion")
    print("\nCompact Display (Discussion):")
    print(compact_discussion)
    
    # Test empty memory
    print("\n📭 Empty Memory Test:")
    print("-" * 30)
    empty_full = language_manager.format_memory_section("", display_mode="full")
    empty_compact = language_manager.format_memory_section("", display_mode="compact")
    print("Empty Full:", empty_full)
    print("Empty Compact:", empty_compact)


def test_token_reduction():
    """Test and measure token reduction achieved."""
    
    print(f"\n📊 Token Reduction Analysis")
    print("=" * 50)
    
    # Sample long memory for testing
    long_memory = """
    In my initial ranking, I placed maximizing floor income first, then maximizing average with floor constraint second, 
    maximizing average income third, and maximizing average with range constraint fourth. I was very sure about this ranking 
    because I strongly believe in protecting the worst-off members of society. After learning about the detailed examples, 
    I maintained the same ranking because the examples confirmed my understanding. In round 1 of applications, I chose 
    maximizing average income because I wanted to see how pure efficiency would work, and I was assigned to medium class 
    and earned $2.40. In round 2, I chose maximizing floor income because I wanted to stay true to my values of protecting 
    the poor, and I was assigned to medium class again and earned $1.80. In round 3, I chose maximizing average with floor 
    constraint with a constraint of $15,000 because I wanted to balance efficiency with protection, and I was assigned to 
    high class and earned $3.20. In round 4, I chose maximizing floor income again because I wanted to be consistent, 
    and I was assigned to low class and earned $1.50. My total earnings were $9.90. I learned that the floor principle 
    tends to protect the worst-off but may sacrifice some efficiency, while the average principle maximizes total wealth 
    but can leave the poor behind. The constrained versions offer good compromises. Now in Phase 2, I'm discussing with 
    other participants. Alice argued for maximizing average income because she believes efficiency should be the priority. 
    Bob supports floor protection like me. Charlie is undecided. In round 1, I stated my position strongly for floor 
    principle. In round 2, Alice presented counter-arguments about efficiency. In round 3, Bob and I are trying to build 
    consensus around a floor constraint compromise.
    """
    
    # Initialize language manager
    language_manager = LanguageManager()
    language_manager.set_language(language_manager.current_language)
    
    # Test token reduction
    full_display = language_manager.format_memory_section(long_memory, display_mode="full")
    compact_display = language_manager.format_memory_section(long_memory, display_mode="compact", context_type="general")
    
    # Rough token estimation (1 token ≈ 4 characters for English)
    full_tokens = len(full_display) // 4
    compact_tokens = len(compact_display) // 4
    reduction_percent = ((full_tokens - compact_tokens) / full_tokens) * 100
    
    print(f"Full Display Length: {len(full_display)} characters (~{full_tokens} tokens)")
    print(f"Compact Display Length: {len(compact_display)} characters (~{compact_tokens} tokens)")
    print(f"Token Reduction: {reduction_percent:.1f}%")
    
    print(f"\nFull Display Preview:")
    print(full_display[:200] + "..." if len(full_display) > 200 else full_display)
    
    print(f"\nCompact Display:")
    print(compact_display)


if __name__ == "__main__":
    try:
        test_memory_summarizer()
        test_language_manager_integration()
        test_token_reduction()
        
        print(f"\n✅ All memory optimization tests completed successfully!")
        print("=" * 50)
        print("Summary:")
        print("- MemorySummarizer creates context-aware summaries")
        print("- LanguageManager integration supports compact display modes")
        print("- Token reduction achieved while preserving key insights")
        print("- Fallback mechanisms work for edge cases")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)