#!/usr/bin/env python3
"""
Test the new enhanced agreement detection logic with pattern matching.
"""
import re

def _detect_agreement_patterns(response: str):
    """Rule-based agreement detection as primary method."""
    response_lower = response.lower().strip()
    
    # Clear disagreement patterns (higher priority - check first)
    disagreement_patterns = [
        r'but\b', r'however\b', r'although\b', r'though\b',
        r'not yet\b', r'not ready\b', r'more discussion\b',
        r'think about\b', r'maybe\b', r'perhaps\b',
        r'^no$', r'^no\b', r'need more\b', r'have concerns\b',
        r'not sure\b', r'hold on\b', r'wait\b', r'let me think\b'
    ]
    
    # Check disagreement first (higher priority)
    if any(re.search(pattern, response_lower) for pattern in disagreement_patterns):
        return False
    
    # Clear agreement patterns
    agreement_patterns = [
        r'^yes$', r'^si$', r'^oui$', r'^是的$',  # Simple yes in multiple languages
        r'^yes[,.]', r'^yes\b',  # Yes with punctuation or word boundary
        r'i agree\b', r'estoy de acuerdo\b', r'我同意\b',  # I agree
        r"let\'s proceed\b", r"let\'s do it\b", r"let\'s vote\b",  # Let's proceed/do it/vote
        r"vamos a proceder\b", r"vamos a hacerlo\b", r"vamos a votar\b",  # Spanish equivalents
        r"我们开始吧\b", r"我们投票吧\b",  # Mandarin equivalents
        r"i\'m ready\b", r"we\'re ready\b", r"ready to vote\b",  # Ready statements
        r"estoy listo\b", r"estamos listos\b", r"listos para votar\b",  # Spanish ready
        r"我准备好\b", r"我们准备好\b",  # Mandarin ready
        r"sounds good\b", r"that works\b", r"fine with me\b",  # Positive acknowledgment
        r"me parece bien\b", r"可以\b", r"我没意见\b",  # Other language positive
        r"time to vote\b", r"es hora de votar\b", r"是时候投票了\b",  # Time to vote
        r"let\'s finalize\b", r"finalicemos\b", r"让我们最后敲定\b"  # Finalize
    ]
    
    # Check agreement
    if any(re.search(pattern, response_lower) for pattern in agreement_patterns):
        return True
        
    return None  # Unclear, use LLM fallback

def test_enhanced_agreement_detection():
    """Test the new enhanced agreement detection with pattern matching."""
    
    # Test responses that should now be detected correctly
    test_responses = [
        # Should be detected as AGREEMENT
        ("YES", True),
        ("Yes", True),
        ("yes", True),
        ("Yes, I agree to vote.", True),
        ("I agree, let's vote.", True),
        ("Sure, I'm ready to vote.", True),  # Note: This might still go to LLM fallback
        ("I think we're ready to vote now.", None),  # Should go to LLM fallback (improved)
        ("Let's proceed with the vote.", True),  # Should now be caught by pattern matching
        ("I'm ready to vote on this.", True),  # Should now be caught by pattern matching
        ("We should vote, I agree.", True),
        ("Let's do it", True),
        ("Sounds good", True),
        ("That works", True),
        
        # Should be detected as DISAGREEMENT
        ("Yes, but I think we should discuss more first.", False),
        ("Yes, however I have some concerns.", False),
        ("NO", False),
        ("No", False),
        ("I think we need more discussion.", False),
        ("Not yet, let's talk more.", False),
        ("I'm not quite ready to vote.", False),
        ("Maybe we should discuss this further.", False),
        ("Hold on", False),
        ("Let me think", False),
        
        # Multilingual tests
        ("Sí", True),
        ("Estoy de acuerdo", True),
        ("Vamos a proceder", True),
        ("我同意", True),
        ("我们开始吧", True),
    ]
    
    print("=== Testing Enhanced Agreement Detection with Pattern Matching ===\n")
    
    for response, expected in test_responses:
        result = _detect_agreement_patterns(response)
        
        if result is None:
            status = "→ LLM Fallback (should be improved with new prompt)"
        elif result == expected:
            status = "✅ CORRECT"
        else:
            status = "❌ INCORRECT"
        
        print(f"Response: '{response}'")
        print(f"  Expected: {expected}")
        print(f"  Pattern Result: {result}")  
        print(f"  Status: {status}")
        print("-" * 60)

if __name__ == "__main__":
    test_enhanced_agreement_detection()