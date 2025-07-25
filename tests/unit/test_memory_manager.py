"""
Unit tests for memory management utilities.
"""
import unittest
from utils.memory_manager import MemoryManager
from models import ExperimentPhase


class TestMemoryManager(unittest.TestCase):
    """Test cases for the MemoryManager class."""
    
    def test_update_memory_within_limits(self):
        """Test memory update when within size limits."""
        current_memory = "Initial memory content."
        new_info = "New information to add."
        max_length = 1000
        
        updated_memory = MemoryManager.update_memory(current_memory, new_info, max_length)
        
        # Should contain both old and new content
        self.assertIn("Initial memory content", updated_memory)
        self.assertIn("New information to add", updated_memory)
        self.assertLessEqual(len(updated_memory), max_length)
    
    def test_update_memory_with_truncation(self):
        """Test memory update when truncation is needed."""
        # Create memory that will exceed limits
        current_memory = "A" * 800  # 800 characters
        new_info = "B" * 300       # 300 characters 
        max_length = 500           # Total would be 1100, limit is 500
        
        updated_memory = MemoryManager.update_memory(current_memory, new_info, max_length)
        
        # Should be within limits
        self.assertLessEqual(len(updated_memory), max_length)
        
        # Should contain recent information
        self.assertIn("B", updated_memory)  # New info should be preserved
    
    def test_format_memory_prompt_phase1(self):
        """Test memory formatting for Phase 1."""
        memory = "Test memory content"
        
        formatted = MemoryManager.format_memory_prompt(memory, ExperimentPhase.PHASE_1)
        
        self.assertIn("Phase 1", formatted)
        self.assertIn("Individual Learning", formatted)
        self.assertIn("Test memory content", formatted)
    
    def test_format_memory_prompt_phase2(self):
        """Test memory formatting for Phase 2."""
        memory = "Test memory content"
        
        formatted = MemoryManager.format_memory_prompt(memory, ExperimentPhase.PHASE_2)
        
        self.assertIn("Phase 1 + Phase 2", formatted)
        self.assertIn("Group Discussion", formatted)
        self.assertIn("Test memory content", formatted)
    
    def test_format_memory_prompt_empty(self):
        """Test memory formatting with empty memory."""
        memory = ""
        
        formatted = MemoryManager.format_memory_prompt(memory, ExperimentPhase.PHASE_1)
        
        self.assertIn("No previous memories", formatted)
    
    def test_add_memory_entry(self):
        """Test structured memory entry addition."""
        current_memory = "Existing content"
        
        updated_memory = MemoryManager.add_memory_entry(
            current_memory, "RANKING", "Completed initial ranking", 1
        )
        
        self.assertIn("Existing content", updated_memory)
        self.assertIn("[RANKING (Round 1)]", updated_memory)
        self.assertIn("Completed initial ranking", updated_memory)
    
    def test_add_memory_entry_no_round(self):
        """Test memory entry addition without round number."""
        current_memory = "Existing content"
        
        updated_memory = MemoryManager.add_memory_entry(
            current_memory, "TRANSITION", "Moving to Phase 2"
        )
        
        self.assertIn("[TRANSITION]", updated_memory)
        self.assertIn("Moving to Phase 2", updated_memory)
        self.assertNotIn("Round", updated_memory)
    
    def test_extract_key_learnings(self):
        """Test key learning extraction."""
        memory = """
        I learned that maximizing floor is important.
        I discovered that average income can be misleading.
        I earned $2.50 in round 1.
        Other random content here.
        I realized that constraints matter.
        More content without key indicators.
        """
        
        key_learnings = MemoryManager.extract_key_learnings(memory)
        
        # Should extract lines with learning indicators
        self.assertTrue(any("learned that" in learning.lower() for learning in key_learnings))
        self.assertTrue(any("discovered that" in learning.lower() for learning in key_learnings))
        self.assertTrue(any("earned $" in learning.lower() for learning in key_learnings))
        self.assertTrue(any("realized that" in learning.lower() for learning in key_learnings))
        
        # Should not exceed maximum
        self.assertLessEqual(len(key_learnings), 10)
    
    def test_create_phase_transition_summary(self):
        """Test phase transition summary creation."""
        phase1_memory = """
        I learned that maximizing floor helps the poorest.
        I earned $3.20 total in Phase 1.
        I chose principle (a) maximizing floor in round 2.
        Other content here.
        """
        
        summary = MemoryManager.create_phase_transition_summary(phase1_memory)
        
        self.assertIn("PHASE 1 SUMMARY", summary)
        self.assertIn("TRANSITIONING TO PHASE 2", summary)
        self.assertIn("Key experiences", summary)
        
        # Should include extracted learnings
        self.assertTrue(any("learned that" in line for line in summary.split('\n')))


if __name__ == '__main__':
    unittest.main()