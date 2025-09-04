"""
Unit tests for agent-managed memory system.
"""
import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from utils.memory_manager import MemoryManager
from utils.error_handling import MemoryError, ExperimentError


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
        self.mock_context.memory_character_limit = 1000
    
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
        
        # Create mock language manager that properly formats templates
        mock_language_manager = Mock()
        mock_language_manager.get.side_effect = lambda key, **kwargs: \
            "Test prompt with {current_memory} and {round_content}. Return your complete updated memory.".format(**kwargs)
        
        prompt = MemoryManager._create_memory_update_prompt(
            current_memory, round_content, "narrative", mock_language_manager
        )
        
        self.assertIn("Previous memory content", prompt)
        self.assertIn("New round information", prompt)
        self.assertIn("Return your complete updated memory", prompt)
    
    def test_create_memory_update_prompt_empty_memory(self):
        """Test memory update prompt creation with empty memory."""
        current_memory = ""
        round_content = "New round information"
        
        # Create mock language manager
        mock_language_manager = Mock()
        mock_language_manager.get.side_effect = lambda key, **kwargs: {
            "prompts.memory_narrative_update_prompt": "Test prompt with {current_memory} and {round_content}. Return your complete updated memory.",
            "prompts.memory_empty_memory_placeholder": "(Empty)"
        }.get(key, key).format(**kwargs)
        
        prompt = MemoryManager._create_memory_update_prompt(
            current_memory, round_content, "narrative", mock_language_manager
        )
        
        self.assertIn("(Empty)", prompt)
        self.assertIn("New round information", prompt)
        self.assertIn("Return your complete updated memory", prompt)
    
    def test_prompt_agent_for_memory_update_success(self):
        """Test successful agent memory update."""
        async def run_test():
            # Setup
            self.mock_agent.update_memory.return_value = "Updated memory content"
            round_content = "Test round content"
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            # Execute
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content,
                language_manager=mock_language_manager
            )
            
            # Verify
            self.assertEqual(result, "Updated memory content")
            self.mock_agent.update_memory.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_prompt_agent_for_memory_update_length_exceeded_then_compression(self):
        """Test memory update with length exceeded gets compressed."""
        async def run_test():
            # Setup - return memory that exceeds 15% tolerance and gets compressed
            self.mock_agent.update_memory.return_value = "A" * 1500  # Too long (exceeds 15% tolerance)
            round_content = "Test round content"
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            # Execute
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content,
                language_manager=mock_language_manager
            )
            
            # Verify - should be compressed since no utility agent provided
            self.assertIn("[Memory compressed due to length limit]", result)
            self.assertEqual(self.mock_agent.update_memory.call_count, 1)
        
        asyncio.run(run_test())
    
    def test_prompt_agent_for_memory_update_with_tolerance_compression(self):
        """Test memory update with tolerance exceeded gets compressed automatically."""
        async def run_test():
            # Setup - return memory that's too long (exceeds 15% tolerance)
            self.mock_agent.update_memory.return_value = "A" * 1500
            round_content = "Test round content"
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            # Execute - should not raise MemoryError but return compressed result
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content, max_retries=3,
                language_manager=mock_language_manager
            )
            
            # Should be compressed instead of failing
            self.assertIn("[Memory compressed due to length limit]", result)
            self.assertEqual(self.mock_agent.update_memory.call_count, 1)
        
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
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            # Execute
            result = await MemoryManager.prompt_agent_for_memory_update(
                self.mock_agent, self.mock_context, round_content,
                language_manager=mock_language_manager
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
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            # Execute & Verify
            with self.assertRaises(MemoryError):
                await MemoryManager.prompt_agent_for_memory_update(
                    self.mock_agent, self.mock_context, round_content, max_retries=2,
                    language_manager=mock_language_manager
                )
            
            # Should have tried max_retries times
            self.assertEqual(self.mock_agent.update_memory.call_count, 2)
        
        asyncio.run(run_test())
    
    def test_memory_error_creation(self):
        """Test MemoryError creation."""
        from utils.error_handling import ErrorSeverity
        error = MemoryError("Memory too long", ErrorSeverity.RECOVERABLE, {"length": 1500, "limit": 1000})
        
        self.assertIn("Memory too long", str(error))
        self.assertEqual(error.severity, ErrorSeverity.RECOVERABLE)
        self.assertEqual(error.context["length"], 1500)
        self.assertEqual(error.context["limit"], 1000)


class TestMemoryManagerTemplateSelection(unittest.TestCase):
    """Test cases for template selection logic in MemoryManager."""
    
    def setUp(self):
        """Set up test fixtures for template selection tests."""
        self.current_memory = "Previous memory content"
        self.round_content = "New round information"
        self.mock_language_manager = Mock()
        
        # Setup default template responses
        self.mock_language_manager.get.side_effect = self._mock_language_manager_get
    
    def _mock_language_manager_get(self, key, **kwargs):
        """Mock language manager get method with realistic template responses."""
        templates = {
            # Standard templates
            "prompts.memory_narrative_update_prompt": "Narrative template with Recent Activity:\n{current_memory}\n\nRecent Activity:\n{round_content}",
            "prompts.memory_memory_update_prompt": "Structured template with Recent Activity:\n{current_memory}\n\nRecent Activity:\n{round_content}",
            
            # No recent activity templates
            "prompts.memory_narrative_update_prompt_no_recent_activity": "Narrative template with Your Recent Reasoning:\n{current_memory}\n\nYour Recent Reasoning and Statement:\n{round_content}",
            "prompts.memory_memory_update_prompt_no_recent_activity": "Structured template with Your Recent Reasoning:\n{current_memory}\n\nYour Recent Reasoning and Statement:\n{round_content}",
            
            # Empty memory placeholder
            "prompts.memory_empty_memory_placeholder": "(Empty)"
        }
        
        template = templates.get(key)
        if template is None:
            raise KeyError(f"Template key '{key}' not found")
        
        # Format template with provided kwargs
        return template.format(**kwargs)
    
    def test_discussion_interaction_types_use_no_recent_activity_templates(self):
        """Test that discussion interaction types use _no_recent_activity templates."""
        discussion_types = ["internal_reasoning", "statement"]
        
        for interaction_type in discussion_types:
            with self.subTest(interaction_type=interaction_type):
                # Test narrative style
                prompt = MemoryManager._create_memory_update_prompt(
                    self.current_memory, self.round_content, "narrative", 
                    self.mock_language_manager, interaction_type
                )
                
                self.assertIn("Your Recent Reasoning and Statement:", prompt)
                self.assertNotIn("Recent Activity:", prompt)
                self.assertIn(self.current_memory, prompt)
                self.assertIn(self.round_content, prompt)
    
    def test_discussion_interaction_types_structured_style(self):
        """Test that discussion interaction types work with structured guidance style."""
        discussion_types = ["internal_reasoning", "statement"]
        
        for interaction_type in discussion_types:
            with self.subTest(interaction_type=interaction_type):
                # Test structured style
                prompt = MemoryManager._create_memory_update_prompt(
                    self.current_memory, self.round_content, "structured", 
                    self.mock_language_manager, interaction_type
                )
                
                self.assertIn("Your Recent Reasoning and Statement:", prompt)
                self.assertNotIn("Recent Activity:", prompt)
                self.assertIn(self.current_memory, prompt)
                self.assertIn(self.round_content, prompt)
    
    def test_non_discussion_interaction_types_use_standard_templates(self):
        """Test that non-discussion interaction types use standard templates."""
        non_discussion_types = ["vote_prompt", "vote_confirmation", "ballot", "other_type"]
        
        for interaction_type in non_discussion_types:
            with self.subTest(interaction_type=interaction_type):
                # Test narrative style
                prompt = MemoryManager._create_memory_update_prompt(
                    self.current_memory, self.round_content, "narrative", 
                    self.mock_language_manager, interaction_type
                )
                
                self.assertIn("Recent Activity:", prompt)
                self.assertNotIn("Your Recent Reasoning and Statement:", prompt)
                self.assertIn(self.current_memory, prompt)
                self.assertIn(self.round_content, prompt)
    
    def test_none_interaction_type_uses_standard_templates(self):
        """Test that None interaction_type uses standard templates."""
        # Test with None interaction_type
        prompt = MemoryManager._create_memory_update_prompt(
            self.current_memory, self.round_content, "narrative", 
            self.mock_language_manager, None
        )
        
        self.assertIn("Recent Activity:", prompt)
        self.assertNotIn("Your Recent Reasoning and Statement:", prompt)
        self.assertIn(self.current_memory, prompt)
        self.assertIn(self.round_content, prompt)
    
    def test_fallback_when_no_recent_activity_template_missing(self):
        """Test graceful fallback when _no_recent_activity templates are missing."""
        # Mock language manager to raise KeyError for no_recent_activity templates
        def mock_get_with_missing_template(key, **kwargs):
            if "_no_recent_activity" in key:
                raise KeyError(f"Template key '{key}' not found")
            return self._mock_language_manager_get(key, **kwargs)
        
        self.mock_language_manager.get.side_effect = mock_get_with_missing_template
        
        # Test with discussion interaction type - should fallback to standard template
        prompt = MemoryManager._create_memory_update_prompt(
            self.current_memory, self.round_content, "narrative", 
            self.mock_language_manager, "statement"
        )
        
        # Should use standard template as fallback
        self.assertIn("Recent Activity:", prompt)
        self.assertNotIn("Your Recent Reasoning and Statement:", prompt)
        self.assertIn(self.current_memory, prompt)
        self.assertIn(self.round_content, prompt)
    
    def test_fallback_handles_attribute_error(self):
        """Test that fallback handles AttributeError gracefully."""
        # Mock language manager to raise AttributeError for no_recent_activity templates
        def mock_get_with_attribute_error(key, **kwargs):
            if "_no_recent_activity" in key:
                raise AttributeError("'NoneType' object has no attribute 'get'")
            return self._mock_language_manager_get(key, **kwargs)
        
        self.mock_language_manager.get.side_effect = mock_get_with_attribute_error
        
        # Test with discussion interaction type - should fallback to standard template
        prompt = MemoryManager._create_memory_update_prompt(
            self.current_memory, self.round_content, "structured", 
            self.mock_language_manager, "internal_reasoning"
        )
        
        # Should use standard template as fallback
        self.assertIn("Recent Activity:", prompt)
        self.assertNotIn("Your Recent Reasoning and Statement:", prompt)
    
    def test_empty_memory_handling_with_discussion_types(self):
        """Test empty memory handling with discussion interaction types."""
        empty_memory = ""
        
        prompt = MemoryManager._create_memory_update_prompt(
            empty_memory, self.round_content, "narrative", 
            self.mock_language_manager, "statement"
        )
        
        self.assertIn("(Empty)", prompt)
        self.assertIn("Your Recent Reasoning and Statement:", prompt)
        self.assertIn(self.round_content, prompt)
    
    def test_template_selection_preserves_guidance_styles(self):
        """Test that template selection preserves different guidance styles."""
        guidance_styles = ["narrative", "structured"]
        interaction_type = "internal_reasoning"
        
        for style in guidance_styles:
            with self.subTest(style=style):
                prompt = MemoryManager._create_memory_update_prompt(
                    self.current_memory, self.round_content, style, 
                    self.mock_language_manager, interaction_type
                )
                
                # Both styles should use the no_recent_activity variant for discussion types
                self.assertIn("Your Recent Reasoning and Statement:", prompt)
                self.assertNotIn("Recent Activity:", prompt)
    
    def test_template_content_validation_all_languages(self):
        """Test that required templates exist in all language files."""
        language_files = [
            "/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json",
            "/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json",
            "/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json"
        ]
        
        required_templates = [
            "prompts.memory_narrative_update_prompt",
            "prompts.memory_narrative_update_prompt_no_recent_activity",
            "prompts.memory_memory_update_prompt",
            "prompts.memory_memory_update_prompt_no_recent_activity"
        ]
        
        for language_file in language_files:
            with self.subTest(language_file=language_file):
                with open(language_file, 'r', encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                    
                    # Check that all required templates exist
                    prompts_section = data.get("prompts", {})
                    for template_key in required_templates:
                        template_name = template_key.replace("prompts.", "")
                        self.assertIn(template_name, prompts_section, 
                                    f"Template '{template_name}' missing in {language_file}")
    
    def test_error_handling_doesnt_break_memory_flow(self):
        """Test that template selection errors don't break memory update flow."""
        # Mock language manager to fail completely
        failing_language_manager = Mock()
        failing_language_manager.get.side_effect = Exception("Complete failure")
        
        # Should raise the exception since we can't provide any fallback
        with self.assertRaises(Exception):
            MemoryManager._create_memory_update_prompt(
                self.current_memory, self.round_content, "narrative",
                failing_language_manager, "statement"
            )


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
            mock_context.memory_character_limit = 100
            mock_context.bank_balance = 50.0
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Test prompt template"
            
            # Run memory update
            result = await MemoryManager.prompt_agent_for_memory_update(
                mock_agent, mock_context, "New content",
                language_manager=mock_language_manager
            )
            
            # Verify
            self.assertEqual(result, "Short memory")
            mock_agent.update_memory.assert_called_once()
        
        # Run the async test
        self.loop.run_until_complete(run_test())
    
    def test_interaction_type_parameter_passing(self):
        """Test that interaction_type parameter is properly passed to template selection."""
        async def run_test():
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "TestAgent"
            mock_agent.config = Mock()
            mock_agent.config.memory_character_limit = 1000
            mock_agent.update_memory = AsyncMock(return_value="Updated memory")
            
            # Create mock context
            mock_context = Mock()
            mock_context.memory = "Previous memory"
            mock_context.memory_character_limit = 1000
            mock_context.bank_balance = 100.0
            
            # Create mock language manager with template selection
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            # Patch the _create_memory_update_prompt method to verify it's called correctly
            with patch.object(MemoryManager, '_create_memory_update_prompt', return_value="Mocked prompt") as mock_create_prompt:
                # Test with discussion interaction type
                await MemoryManager.prompt_agent_for_memory_update(
                    mock_agent, mock_context, "Round content", 
                    language_manager=mock_language_manager,
                    interaction_type="statement"
                )
                
                # Verify that _create_memory_update_prompt was called with the interaction_type
                mock_create_prompt.assert_called_once_with(
                    "Previous memory", 
                    "Round content", 
                    "narrative",  # default guidance style
                    mock_language_manager,
                    "statement"  # interaction_type should be passed through
                )
        
        # Run the async test
        self.loop.run_until_complete(run_test())
    
    def test_interaction_type_parameter_with_different_guidance_styles(self):
        """Test interaction_type works with different memory guidance styles."""
        async def run_test():
            # Create mock agent
            mock_agent = Mock()
            mock_agent.name = "TestAgent"
            mock_agent.config = Mock()
            mock_agent.config.memory_character_limit = 1000
            mock_agent.update_memory = AsyncMock(return_value="Updated memory")
            
            # Create mock context
            mock_context = Mock()
            mock_context.memory = "Previous memory"
            mock_context.memory_character_limit = 1000
            mock_context.bank_balance = 100.0
            
            # Create mock language manager
            mock_language_manager = Mock()
            mock_language_manager.get.return_value = "Mock prompt template"
            
            guidance_styles = ["narrative", "structured"]
            interaction_types = ["internal_reasoning", "statement", "vote_prompt", None]
            
            for guidance_style in guidance_styles:
                for interaction_type in interaction_types:
                    with self.subTest(guidance_style=guidance_style, interaction_type=interaction_type):
                        # Reset mock
                        mock_agent.update_memory.reset_mock()
                        
                        # Patch the _create_memory_update_prompt method to verify parameters
                        with patch.object(MemoryManager, '_create_memory_update_prompt', return_value="Mocked prompt") as mock_create_prompt:
                            await MemoryManager.prompt_agent_for_memory_update(
                                mock_agent, mock_context, "Round content",
                                memory_guidance_style=guidance_style,
                                language_manager=mock_language_manager,
                                interaction_type=interaction_type
                            )
                            
                            # Verify parameters passed to template selection
                            mock_create_prompt.assert_called_once_with(
                                "Previous memory", 
                                "Round content", 
                                guidance_style,
                                mock_language_manager,
                                interaction_type
                            )
        
        # Run the async test
        self.loop.run_until_complete(run_test())


if __name__ == '__main__':
    unittest.main()