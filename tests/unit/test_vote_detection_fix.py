"""Test the vote detection fix without needing API keys."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.language_manager import get_language_manager


def test_vote_detection_prompt():
    """Test that the vote detection prompt is now properly configured."""
    # Get language manager
    lang_manager = get_language_manager()
    
    # Test statements that should trigger vote detection
    test_statements = [
        "I propose we vote on maximizing the average income with a floor constraint of $12,000.",
        "Since we have reached agreement, I propose that we vote.",
        "I am ready to call for a vote.",
        "Let's vote on this principle now.",
        "Should we proceed with a vote?"
    ]
    
    for statement in test_statements:
        # Get the prompt that would be sent to the utility agent
        prompt = lang_manager.get_vote_detection_prompt(statement)
        
        # Assert that the prompt is generated successfully
        assert prompt is not None, f"Prompt should be generated for statement: {statement}"
        assert isinstance(prompt, str), "Prompt should be a string"
        assert len(prompt) > 0, "Prompt should not be empty"
        
        # Check that the prompt contains the key instructions
        assert "VOTE_PROPOSAL:" in prompt, f"Prompt should contain 'VOTE_PROPOSAL:' format instruction"
        assert "NO_VOTE" in prompt, f"Prompt should contain 'NO_VOTE' format instruction"


def test_vote_detection_method_exists():
    """Test that vote detection method exists and is callable."""
    lang_manager = get_language_manager()
    
    # Assert that the method exists
    assert hasattr(lang_manager, 'get_vote_detection_prompt'), \
        "Language manager should have get_vote_detection_prompt method"
    
    # Assert that the method is callable
    assert callable(getattr(lang_manager, 'get_vote_detection_prompt')), \
        "get_vote_detection_prompt should be callable"