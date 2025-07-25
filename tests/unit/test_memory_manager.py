"""
Unit tests for agent-managed memory system.
"""
import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from utils.memory_manager import MemoryManager, MemoryLengthExceededError, ExperimentAbortError


class TestMemoryManager(unittest.TestCase):
    """Test cases for the new agent-managed MemoryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_agent = Mock()
        self.mock_agent.name = "TestAgent"
        self.mock_agent.config = Mock()
        self.mock_agent.config.memory_character_limit = 1000
        self.mock_agent.update_memory = AsyncMock()
        
        self.mock_context = Mock()
        self.mock_context.memory = "Current memory content"
    
    def test_validate_memory_length_valid(self):
        """Test memory length validation with valid memory."""
        memory = "This is a short memory"
        limit = 1000
        
        is_valid, length = MemoryManager._validate_memory_length(memory, limit)
        
        self.assertTrue(is_valid)
        self.assertEqual(length, len(memory))
    
    def test_validate_memory_length_invalid(self):
        """Test memory length validation with memory exceeding limit."""
        memory = "A" * 1500  # 1500 characters
        limit = 1000
        
        is_valid, length = MemoryManager._validate_memory_length(memory, limit)
        
        self.assertFalse(is_valid)
        self.assertEqual(length, 1500)
    
    def test_create_memory_update_prompt(self):
        """Test memory update prompt creation."""
        current_memory = "Previous memory content"
        round_content = "New round information"
        
        prompt = MemoryManager._create_memory_update_prompt(current_memory, round_content)
        
        self.assertIn("Previous memory content", prompt)
        self.assertIn("New round information", prompt)
        self.assertIn("Update your memory", prompt)
    
    def test_create_memory_update_prompt_empty_memory(self):
        """Test memory update prompt creation with empty memory."""
        current_memory = ""
        round_content = "New round information"
        
        prompt = MemoryManager._create_memory_update_prompt(current_memory, round_content)
        
        self.assertIn("(Empty)", prompt)
        self.assertIn("New round information", prompt)
        self.assertIn("Update your memory", prompt)
    
    def test_prompt_agent_for_memory_update_success(self):
        """Test successful agent memory update."""
        async def run_test():
            # Setup
            self.mock_agent.update_memory.return_value = "Updated memory content"
            round_content = "Test round content"
            
            # Execute
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content
            )
            
            # Verify
            self.assertEqual(result, "Updated memory content")
            self.mock_agent.update_memory.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_prompt_agent_for_memory_update_length_exceeded_then_success(self):
        """Test memory update with initial length exceeded, then success."""
        async def run_test():
            # Setup - first call returns too long memory, second call succeeds
            self.mock_agent.update_memory.side_effect = [
                "A" * 1500,  # Too long
                "Updated memory content"  # Valid length
            ]
            round_content = "Test round content"
            
            # Execute
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content
            )
            
            # Verify
            self.assertEqual(result, "Updated memory content")
            self.assertEqual(self.mock_agent.update_memory.call_count, 2)
        
        asyncio.run(run_test())
    
    def test_prompt_agent_for_memory_update_max_retries_exceeded(self):
        """Test memory update failure after max retries."""
        async def run_test():
            # Setup - always return memory that's too long
            self.mock_agent.update_memory.return_value = "A" * 1500
            round_content = "Test round content"
            
            # Execute & Verify
            with self.assertRaises(ExperimentAbortError):
                await MemoryManager.prompt_agent_for_memory_update(
                    self.mock_agent, self.mock_context, round_content, max_retries=3
                )
            
            # Should have tried 3 times
            self.assertEqual(self.mock_agent.update_memory.call_count, 3)
        
        asyncio.run(run_test())
    
    def test_prompt_agent_for_memory_update_exception_then_success(self):
        """Test memory update with exception, then success."""
        async def run_test():
            # Setup - first call raises exception, second succeeds
            self.mock_agent.update_memory.side_effect = [
                Exception("Test error"),
                "Updated memory content"
            ]
            round_content = "Test round content"
            
            # Execute
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content
            )
            
            # Verify
            self.assertEqual(result, "Updated memory content")
            self.assertEqual(self.mock_agent.update_memory.call_count, 2)
        
        asyncio.run(run_test())
    
    def test_prompt_agent_for_memory_update_persistent_exception(self):
        """Test memory update with persistent exceptions."""
        async def run_test():
            # Setup - always raise exception
            self.mock_agent.update_memory.side_effect = Exception("Persistent error")
            round_content = "Test round content"
            
            # Execute & Verify
            with self.assertRaises(ExperimentAbortError):
                await MemoryManager.prompt_agent_for_memory_update(
                    self.mock_agent, self.mock_context, round_content, max_retries=2
                )
            
            # Should have tried max_retries times
            self.assertEqual(self.mock_agent.update_memory.call_count, 2)
        
        asyncio.run(run_test())
    
    def test_memory_length_exceeded_error(self):
        """Test MemoryLengthExceededError creation."""
        error = MemoryLengthExceededError(1500, 1000)
        
        self.assertEqual(error.attempted_length, 1500)
        self.assertEqual(error.limit, 1000)
        self.assertIn("1500", str(error))
        self.assertIn("1000", str(error))
        self.assertIn("reduce", str(error).lower())


class TestMemoryManagerIntegration(unittest.TestCase):
    """Integration tests for memory manager with real async behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.loop.close()
    
    def test_async_memory_update_flow(self):
        """Test complete async memory update flow."""
        async def run_test():
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "TestAgent"
            mock_agent.config = Mock()
            mock_agent.config.memory_character_limit = 100
            mock_agent.update_memory = AsyncMock(return_value="Short memory")
            
            # Create mock context
            mock_context = Mock()
            mock_context.memory = "Previous"
            
            # Run memory update
            result = await MemoryManager.prompt_agent_for_memory_update(
                mock_agent, mock_context, "New content"
            )
            
            # Verify
            self.assertEqual(result, "Short memory")
            mock_agent.update_memory.assert_called_once()
        
        # Run the async test
        self.loop.run_until_complete(run_test())


if __name__ == '__main__':
    unittest.main()