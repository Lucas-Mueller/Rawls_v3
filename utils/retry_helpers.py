"""
Retry utilities with exponential backoff.

Provides utility functions for retry logic with proper exponential backoff
and logging. Fixes the backoff logging bug from the original implementation.
"""

import asyncio
from typing import Any, Awaitable, Callable, Optional, Protocol


class Logger(Protocol):
    """Protocol for logging functionality."""
    def log_info(self, message: str) -> None:
        """Log info message."""
        ...
    
    def log_warning(self, message: str) -> None:
        """Log warning message."""
        ...


async def execute_with_exponential_backoff(
    operation: Callable[[], Awaitable[Any]],
    max_retries: int,
    base_delay: float = 1.0,
    backoff_factor: float = 1.5,
    operation_name: str = "operation",
    logger: Optional[Logger] = None
) -> Any:
    """
    Execute an async operation with exponential backoff retry logic.
    
    Args:
        operation: Async callable to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        backoff_factor: Factor to multiply delay by each retry
        operation_name: Name of operation for logging
        logger: Optional logger for retry information
        
    Returns:
        Result of the operation if successful
        
    Raises:
        Exception: The last exception from the operation if all retries fail
    """
    last_exception = None
    backoff_delay = base_delay
    
    for attempt in range(max_retries):
        try:
            # Add exponential backoff for retries (fixed logging bug)
            if attempt > 0:
                # LOG BEFORE sleeping to show the actual delay being used
                if logger:
                    logger.log_info(f"Waiting {backoff_delay:.1f}s before retry")
                await asyncio.sleep(backoff_delay)
                # THEN multiply for next iteration
                backoff_delay *= backoff_factor
            
            if logger:
                logger.log_info(f"Executing {operation_name} (attempt {attempt + 1}/{max_retries})")
            
            # Execute the operation
            return await operation()
            
        except Exception as e:
            last_exception = e
            if logger:
                logger.log_warning(f"{operation_name} attempt {attempt + 1} failed: {str(e)}")
            
            # If this was the last attempt, re-raise the exception
            if attempt == max_retries - 1:
                raise last_exception
    
    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError(f"All {max_retries} attempts failed for {operation_name}")


def calculate_backoff_delay(attempt: int, base_delay: float, factor: float) -> float:
    """
    Calculate exponential backoff delay for a given attempt.
    
    Args:
        attempt: Attempt number (0-based)
        base_delay: Initial delay in seconds
        factor: Exponential backoff factor
        
    Returns:
        Delay in seconds for this attempt
    """
    return base_delay * (factor ** attempt)


async def execute_with_timeout_and_retry(
    operation: Callable[[], Awaitable[Any]],
    timeout_seconds: float,
    max_retries: int,
    base_delay: float = 1.0,
    backoff_factor: float = 1.5,
    operation_name: str = "operation",
    logger: Optional[Logger] = None
) -> Any:
    """
    Execute an async operation with both timeout and retry logic.
    
    Combines timeout handling with exponential backoff retry for robust operation execution.
    
    Args:
        operation: Async callable to execute
        timeout_seconds: Timeout in seconds for each attempt
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds for retries
        backoff_factor: Factor to multiply delay by each retry
        operation_name: Name of operation for logging
        logger: Optional logger for operation information
        
    Returns:
        Result of the operation if successful
        
    Raises:
        asyncio.TimeoutError: If all attempts timeout
        Exception: The last exception from the operation if all retries fail
    """
    async def timeout_wrapper():
        """Wrapper to add timeout to the operation."""
        try:
            return await asyncio.wait_for(operation(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            if logger:
                logger.log_warning(f"Timeout for {operation_name} after {timeout_seconds}s")
            raise
    
    return await execute_with_exponential_backoff(
        operation=timeout_wrapper,
        max_retries=max_retries,
        base_delay=base_delay,
        backoff_factor=backoff_factor,
        operation_name=operation_name,
        logger=logger
    )