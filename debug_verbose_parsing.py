#!/usr/bin/env python3
"""
Debug script for the verbose format parsing issue.
"""
import sys
import os
from pathlib import Path
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('OPENAI_API_KEY', 'test-key')

sys.path.insert(0, str(Path(__file__).parent / 'experiment_agents'))
from utility_agent import UtilityAgent

verbose_response = """After careful consideration, my complete ranking is:

1. Maximizing the average income with a floor constraint: This principle offers the best balance between efficiency and equity by ensuring a safety net while still incentivizing productivity.

2. Maximizing the floor income: While this prioritizes the worst-off, it may limit overall economic growth but provides crucial protection.

3. Maximizing the average income with a range constraint: This approach caps inequality but feels less direct than a floor constraint.

4. Maximizing the average income: This pure efficiency approach risks creating severe inequality and leaving people behind.

My overall certainty level: sure

This ranking reflects my belief that we need both growth and protection."""

def debug_parsing():
    print("Debugging Verbose Format Parsing")
    print("=" * 50)
    
    utility_agent = UtilityAgent()
    
    # Test the ranking line regex
    ranking_pattern = utility_agent._ranking_patterns['ranking_line']
    print("Using ranking pattern:", ranking_pattern.pattern)
    
    matches = ranking_pattern.findall(verbose_response)
    print(f"\nRanking line matches found: {len(matches)}")
    for i, (rank_num, rank_text) in enumerate(matches):
        print(f"Match {i+1}: Rank {rank_num}")
        print(f"  Text: '{rank_text[:100]}...' (truncated)")
        print(f"  Full text: '{rank_text.strip()}'")
        
        # Test principle identification
        principle = utility_agent._identify_principle_in_text(rank_text.strip())
        print(f"  Identified principle: {principle}")
        print()
    
    # Test certainty detection
    print("Testing certainty detection:")
    for certainty_key, pattern in utility_agent._certainty_patterns.items():
        if pattern.search(verbose_response):
            print(f"  Found: {certainty_key}")
    
    # Test direct ranking extraction
    print("\nTesting direct extraction:")
    ranking_data = utility_agent._extract_ranking_direct(verbose_response)
    if ranking_data:
        print("Success! Found rankings:")
        for ranking in ranking_data['rankings']:
            print(f"  {ranking['rank']}. {ranking['principle']}")
        print(f"Certainty: {ranking_data['certainty']}")
    else:
        print("Direct extraction failed")

if __name__ == "__main__":
    debug_parsing()