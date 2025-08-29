"""
Base test class for Frohlich Experiment tests with tracing disabled.

This module provides a base test class that ensures tracing is completely
disabled for all test operations to prevent unwanted trace generation.
"""

import unittest
import os
import asyncio


class TracingDisabledTestCase(unittest.TestCase):
    """Base test case that ensures tracing is completely disabled."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level tracing disable."""
        # Set environment variables to disable tracing
        os.environ['OPENAI_AGENTS_DISABLE_TRACING'] = '1'
        os.environ['OPENAI_DISABLE_TRACING'] = 'true'
        
        # Also disable programmatically
        try:
            from agents import set_tracing_disabled
            set_tracing_disabled(True)
        except ImportError:
            # If agents module not available, just continue
            pass
    
    def setUp(self):
        """Set up each test with tracing disabled."""
        # Ensure tracing is disabled for each test
        try:
            from agents import set_tracing_disabled
            set_tracing_disabled(True)
        except ImportError:
            # If agents module not available, just continue
            pass


class AsyncTracingDisabledTestCase(TracingDisabledTestCase):
    """Base async test case that ensures tracing is completely disabled."""
    
    def setUp(self):
        """Set up each async test with tracing disabled."""
        super().setUp()
        
        # Create event loop for async tests if needed
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up async test resources."""
        # Clean up any remaining async tasks
        try:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass