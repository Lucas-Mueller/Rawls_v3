"""
Unit tests for retry_helpers utility functions.

Tests exponential backoff retry logic with proper logging order.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, call
from utils.retry_helpers import (
    execute_with_exponential_backoff,
    calculate_backoff_delay,
    execute_with_timeout_and_retry
)


class TestRetryHelpers:
    """Test retry utility functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logger = Mock()
        self.logger.log_info = Mock()
        self.logger.log_warning = Mock()
    
    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test successful operation that doesn't need retry."""
        operation = AsyncMock(return_value="success")
        
        result = await execute_with_exponential_backoff(
            operation=operation,
            max_retries=3,
            logger=self.logger
        )
        
        assert result == "success"
        operation.assert_called_once()
        self.logger.log_info.assert_called_once_with("Executing operation (attempt 1/3)")
    
    @pytest.mark.asyncio
    async def test_successful_operation_after_retries(self):
        """Test operation that succeeds after failures."""
        # Fail twice, then succeed
        operation = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        
        result = await execute_with_exponential_backoff(
            operation=operation,
            max_retries=3,
            base_delay=0.1,  # Small delay for test speed
            logger=self.logger
        )
        
        assert result == "success"
        assert operation.call_count == 3
        
        # Check logging calls
        info_calls = self.logger.log_info.call_args_list
        warning_calls = self.logger.log_warning.call_args_list
        
        # Should log each attempt
        assert len(info_calls) == 5  # 3 attempts + 2 wait messages
        assert "Executing operation (attempt 1/3)" in str(info_calls[0])
        assert "Waiting 0.1s before retry" in str(info_calls[1])
        assert "Executing operation (attempt 2/3)" in str(info_calls[2])
        assert "Waiting 0.2s before retry" in str(info_calls[3])  # 0.1 * 1.5
        assert "Executing operation (attempt 3/3)" in str(info_calls[4])
        
        # Should log failures
        assert len(warning_calls) == 2
        assert "operation attempt 1 failed: fail1" in str(warning_calls[0])
        assert "operation attempt 2 failed: fail2" in str(warning_calls[1])
    
    @pytest.mark.asyncio
    async def test_all_retries_fail(self):
        """Test operation that fails all retry attempts."""
        operation = AsyncMock(side_effect=Exception("persistent failure"))
        
        with pytest.raises(Exception, match="persistent failure"):
            await execute_with_exponential_backoff(
                operation=operation,
                max_retries=2,
                base_delay=0.1,
                logger=self.logger
            )
        
        assert operation.call_count == 2
        
        # Should log all attempts and failures
        info_calls = self.logger.log_info.call_args_list
        warning_calls = self.logger.log_warning.call_args_list
        
        assert len(info_calls) == 3  # 2 attempts + 1 wait message
        assert len(warning_calls) == 2  # 2 failures
    
    @pytest.mark.asyncio
    async def test_backoff_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        # Simulate timing to verify proper delay calculation
        operation = AsyncMock(side_effect=[Exception("fail"), "success"])
        start_time = asyncio.get_event_loop().time()
        
        await execute_with_exponential_backoff(
            operation=operation,
            max_retries=2,
            base_delay=0.1,
            backoff_factor=2.0,
            logger=self.logger
        )
        
        end_time = asyncio.get_event_loop().time()
        
        # Should have waited at least 0.1 seconds for backoff
        assert end_time - start_time >= 0.1
        
        # Check that correct delay was logged
        info_calls = self.logger.log_info.call_args_list
        assert "Waiting 0.1s before retry" in str(info_calls[1])
    
    def test_calculate_backoff_delay_function(self):
        """Test standalone backoff delay calculation function."""
        assert calculate_backoff_delay(0, 1.0, 1.5) == 1.0
        assert calculate_backoff_delay(1, 1.0, 1.5) == 1.5
        assert calculate_backoff_delay(2, 1.0, 1.5) == 2.25
        assert calculate_backoff_delay(3, 2.0, 2.0) == 16.0  # 2.0 * 2^3
    
    @pytest.mark.asyncio
    async def test_operation_without_logger(self):
        """Test retry operation without logger."""
        operation = AsyncMock(side_effect=[Exception("fail"), "success"])
        
        result = await execute_with_exponential_backoff(
            operation=operation,
            max_retries=2,
            base_delay=0.01  # Very small delay for test speed
        )
        
        assert result == "success"
        assert operation.call_count == 2
    
    @pytest.mark.asyncio
    async def test_custom_operation_name(self):
        """Test operation with custom name for logging."""
        operation = AsyncMock(return_value="success")
        
        await execute_with_exponential_backoff(
            operation=operation,
            max_retries=1,
            operation_name="test_operation",
            logger=self.logger
        )
        
        self.logger.log_info.assert_called_with("Executing test_operation (attempt 1/1)")
    
    @pytest.mark.asyncio
    async def test_timeout_and_retry_success(self):
        """Test timeout and retry wrapper with successful operation."""
        operation = AsyncMock(return_value="success")
        
        result = await execute_with_timeout_and_retry(
            operation=operation,
            timeout_seconds=1.0,
            max_retries=2,
            logger=self.logger
        )
        
        assert result == "success"
        operation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_timeout_and_retry_with_timeout(self):
        """Test timeout and retry wrapper with timeout."""
        # Create operation that takes too long
        async def slow_operation():
            await asyncio.sleep(0.2)  # Sleep longer than timeout
            return "success"
        
        with pytest.raises(asyncio.TimeoutError):
            await execute_with_timeout_and_retry(
                operation=slow_operation,
                timeout_seconds=0.1,  # Short timeout
                max_retries=2,
                base_delay=0.01,
                logger=self.logger
            )
        
        # Should log timeout warnings
        warning_calls = self.logger.log_warning.call_args_list
        timeout_warnings = [call for call in warning_calls if "Timeout" in str(call)]
        assert len(timeout_warnings) >= 1
    
    @pytest.mark.asyncio
    async def test_timeout_and_retry_success_after_timeout(self):
        """Test timeout and retry wrapper that succeeds after initial timeout."""
        call_count = 0
        
        async def intermittent_slow_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call times out
                await asyncio.sleep(0.2)
                return "too slow"
            else:
                # Second call succeeds quickly
                return "success"
        
        result = await execute_with_timeout_and_retry(
            operation=intermittent_slow_operation,
            timeout_seconds=0.1,
            max_retries=2,
            base_delay=0.01,
            logger=self.logger
        )
        
        assert result == "success"
        assert call_count == 2


class TestRetryHelpersEdgeCases:
    """Test edge cases for retry helpers."""
    
    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Test behavior with zero retries (should fail immediately)."""
        operation = AsyncMock(side_effect=Exception("immediate fail"))
        
        with pytest.raises(Exception, match="immediate fail"):
            await execute_with_exponential_backoff(
                operation=operation,
                max_retries=1,  # Only one attempt, no retries
                logger=Mock()
            )
        
        operation.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_very_large_backoff_factor(self):
        """Test with very large backoff factor."""
        operation = AsyncMock(side_effect=[Exception("fail"), "success"])
        logger = Mock()
        
        result = await execute_with_exponential_backoff(
            operation=operation,
            max_retries=2,
            base_delay=0.01,
            backoff_factor=10.0,
            logger=logger
        )
        
        assert result == "success"
        # Should log the large delay
        info_calls = logger.log_info.call_args_list
        assert "Waiting 0.0s before retry" in str(info_calls[1])  # 0.01 formatted as 0.0
    
    def test_calculate_backoff_delay_with_zero_factor(self):
        """Test backoff calculation with edge case factors."""
        # Factor of 1.0 should result in constant delay
        assert calculate_backoff_delay(0, 5.0, 1.0) == 5.0
        assert calculate_backoff_delay(3, 5.0, 1.0) == 5.0
        
        # Factor of 0 should result in zero delay for non-zero attempts  
        assert calculate_backoff_delay(0, 5.0, 0.0) == 5.0
        assert calculate_backoff_delay(1, 5.0, 0.0) == 0.0