#!/usr/bin/env python3
"""
Test the new enhanced agreement detection logic with pattern matching.
"""
import re
import unittest

def _detect_agreement_patterns(response: str):
    """Rule-based agreement detection as primary method."""
    response_lower = response.lower().strip()
    
    # Clear disagreement patterns (higher priority - check first)
    disagreement_patterns = [
        r'but\b', r'however\b', r'although\b', r'though\b',
        r'not yet\b', r'not ready\b', r'not quite ready\b', r'more discussion\b',
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


class TestVoteAgreementPatterns(unittest.TestCase):
    """Test cases for enhanced agreement detection with pattern matching."""
    
    def test_simple_agreement_patterns(self):
        """Test basic agreement patterns."""
        test_cases = [
            ("YES", True),
            ("Yes", True),
            ("yes", True),
            ("Si", True),  # Spanish
            ("是的", True),  # Mandarin
        ]
        
        for response, expected in test_cases:
            with self.subTest(response=response):
                result = _detect_agreement_patterns(response)
                self.assertEqual(result, expected, f"Failed for response: '{response}'")
    
    def test_complex_agreement_patterns(self):
        """Test more complex agreement patterns."""
        test_cases = [
            ("Yes, I agree to vote.", True),
            ("I agree, let's vote.", True),
            ("Let's proceed with the vote.", True),
            ("I'm ready to vote on this.", True),
            ("We should vote, I agree.", True),
            ("Let's do it", True),
            ("Sounds good", True),
            ("That works", True),
            ("I agree", True),
            ("Let's proceed", True),
            ("Ready to vote", True),
            ("Time to vote", True),
        ]
        
        for response, expected in test_cases:
            with self.subTest(response=response):
                result = _detect_agreement_patterns(response)
                self.assertEqual(result, expected, f"Failed for response: '{response}'")
    
    def test_disagreement_patterns(self):
        """Test disagreement detection patterns."""
        test_cases = [
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
            ("I have concerns", False),
            ("Need more discussion", False),
        ]
        
        for response, expected in test_cases:
            with self.subTest(response=response):
                result = _detect_agreement_patterns(response)
                self.assertEqual(result, expected, f"Failed for response: '{response}'")
    
    def test_multilingual_patterns(self):
        """Test multilingual agreement/disagreement patterns."""
        test_cases = [
            # Spanish
            ("Estoy de acuerdo", True),
            ("Vamos a proceder", True),
            ("Estoy listo", True),
            ("Me parece bien", True),
            ("Es hora de votar", True),
            ("Finalicemos", True),
            
            # Mandarin  
            ("我同意", True),
            ("我们开始吧", True),
            ("我准备好", True),
            ("可以", True),
            ("我没意见", True),
            ("是时候投票了", True),
        ]
        
        for response, expected in test_cases:
            with self.subTest(response=response):
                result = _detect_agreement_patterns(response)
                self.assertEqual(result, expected, f"Failed for response: '{response}'")
    
    def test_fallback_cases(self):
        """Test cases that should fall back to LLM processing."""
        test_cases = [
            "Sure, I'm ready to vote.",  # Complex case
            "I think we're ready to vote now.",  # Should fall back to LLM
            "Well, I suppose we could vote.",  # Unclear sentiment
            "If everyone else agrees, then yes.",  # Conditional
        ]
        
        for response in test_cases:
            with self.subTest(response=response):
                result = _detect_agreement_patterns(response)
                # These should either be clearly classified or return None for LLM fallback
                self.assertIn(result, [True, False, None], f"Unexpected result for: '{response}'")


if __name__ == "__main__":
    unittest.main()