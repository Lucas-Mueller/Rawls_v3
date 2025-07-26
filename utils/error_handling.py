"""
Standardized error handling framework for the Frohlich Experiment.
Provides consistent error categorization, retry logic, and recovery mechanisms.
"""
import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps


class ExperimentErrorCategory(Enum):
    """Categorize errors by type and functionality."""
    CONFIGURATION_ERROR = "configuration"      # Config/validation issues
    AGENT_COMMUNICATION_ERROR = "agent_comm"   # Agent interaction failures  
    MEMORY_ERROR = "memory"                    # Memory management issues
    VALIDATION_ERROR = "validation"           # Data validation failures
    SYSTEM_ERROR = "system"                   # Infrastructure/API failures
    EXPERIMENT_LOGIC_ERROR = "exp_logic"      # Experimental flow issues


class ErrorSeverity(Enum):
    """Error severity levels determining handling strategy."""
    RECOVERABLE = "recoverable"    # Can retry/continue
    DEGRADED = "degraded"         # Can continue with reduced functionality
    FATAL = "fatal"               # Must abort experiment


class ExperimentError(Exception):
    """Base exception for all experiment-related errors."""
    
    def __init__(
        self, 
        message: str, 
        category: ExperimentErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        operation: Optional[str] = None
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        self.operation = operation
        self.timestamp = datetime.now()
        self.attempt_count = 0


class ConfigurationError(ExperimentError):
    """Configuration and validation errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            message, 
            ExperimentErrorCategory.CONFIGURATION_ERROR, 
            ErrorSeverity.FATAL, 
            context, 
            cause
        )


class AgentCommunicationError(ExperimentError):
    """Agent interaction and communication errors."""
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE, 
        context: Optional[Dict[str, Any]] = None, 
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message, 
            ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR, 
            severity, 
            context, 
            cause
        )


class MemoryError(ExperimentError):
    """Memory management errors."""
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE, 
        context: Optional[Dict[str, Any]] = None, 
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message, 
            ExperimentErrorCategory.MEMORY_ERROR, 
            severity, 
            context, 
            cause
        )


class ValidationError(ExperimentError):
    """Data validation errors."""
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE, 
        context: Optional[Dict[str, Any]] = None, 
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message, 
            ExperimentErrorCategory.VALIDATION_ERROR, 
            severity, 
            context, 
            cause
        )


class SystemError(ExperimentError):
    """Infrastructure and API errors."""
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.RECOVERABLE, 
        context: Optional[Dict[str, Any]] = None, 
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message, 
            ExperimentErrorCategory.SYSTEM_ERROR, 
            severity, 
            context, 
            cause
        )


class ExperimentLogicError(ExperimentError):
    """Experimental flow and logic errors."""
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.DEGRADED, 
        context: Optional[Dict[str, Any]] = None, 
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message, 
            ExperimentErrorCategory.EXPERIMENT_LOGIC_ERROR, 
            severity, 
            context, 
            cause
        )


class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(self, max_retries: int, backoff: float, exponential: bool = False):
        self.max_retries = max_retries
        self.backoff = backoff
        self.exponential = exponential


class ExperimentErrorHandler:
    """Centralized error handling and recovery coordination."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_history: List[ExperimentError] = []
        
        # Default retry configurations
        self.retry_config = {
            ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR: RetryConfig(3, 1.0, True),
            ExperimentErrorCategory.MEMORY_ERROR: RetryConfig(5, 0.5, False),
            ExperimentErrorCategory.VALIDATION_ERROR: RetryConfig(2, 0.0, False),
            ExperimentErrorCategory.SYSTEM_ERROR: RetryConfig(3, 2.0, True),
            ExperimentErrorCategory.EXPERIMENT_LOGIC_ERROR: RetryConfig(1, 0.0, False)
        }
    
    async def handle_error_async(
        self, 
        error: ExperimentError, 
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Handle error with appropriate retry logic and logging (async version)."""
        self.error_history.append(error)
        self._log_error(error)
        
        if error.severity == ErrorSeverity.FATAL:
            raise error
            
        if error.category in self.retry_config:
            return await self._retry_operation_async(error, operation, *args, **kwargs)
        else:
            raise error
    
    def handle_error_sync(
        self, 
        error: ExperimentError, 
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Handle error with appropriate retry logic and logging (sync version)."""
        self.error_history.append(error)
        self._log_error(error)
        
        if error.severity == ErrorSeverity.FATAL:
            raise error
            
        if error.category in self.retry_config:
            return self._retry_operation_sync(error, operation, *args, **kwargs)
        else:
            raise error
    
    async def _retry_operation_async(
        self, 
        error: ExperimentError, 
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Retry async operation with exponential backoff."""
        config = self.retry_config[error.category]
        
        for attempt in range(config.max_retries):
            try:
                if attempt > 0:
                    delay = config.backoff * (2 ** attempt if config.exponential else 1)
                    await asyncio.sleep(delay)
                
                error.attempt_count = attempt + 1
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Operation succeeded after {attempt + 1} attempts: {error.operation}"
                    )
                
                return result
                
            except Exception as e:
                if attempt == config.max_retries - 1:
                    # Final attempt failed
                    final_error = self._wrap_exception(
                        e, error.category, ErrorSeverity.FATAL, 
                        {"original_error": str(error), "retry_attempts": attempt + 1}
                    )
                    self._log_error(final_error)
                    raise final_error
                else:
                    # Log retry attempt
                    self.logger.warning(
                        f"Retry attempt {attempt + 1}/{config.max_retries} failed for {error.operation}: {str(e)}"
                    )
    
    def _retry_operation_sync(
        self, 
        error: ExperimentError, 
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Retry sync operation with exponential backoff."""
        config = self.retry_config[error.category]
        
        for attempt in range(config.max_retries):
            try:
                if attempt > 0:
                    delay = config.backoff * (2 ** attempt if config.exponential else 1)
                    time.sleep(delay)
                
                error.attempt_count = attempt + 1
                result = operation(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Operation succeeded after {attempt + 1} attempts: {error.operation}"
                    )
                
                return result
                
            except Exception as e:
                if attempt == config.max_retries - 1:
                    # Final attempt failed
                    final_error = self._wrap_exception(
                        e, error.category, ErrorSeverity.FATAL, 
                        {"original_error": str(error), "retry_attempts": attempt + 1}
                    )
                    self._log_error(final_error)
                    raise final_error
                else:
                    # Log retry attempt
                    self.logger.warning(
                        f"Retry attempt {attempt + 1}/{config.max_retries} failed for {error.operation}: {str(e)}"
                    )
    
    def _log_error(self, error: ExperimentError):
        """Standardized error logging."""
        log_context = {
            "error_category": error.category.value,
            "error_severity": error.severity.value,
            "error_context": error.context,
            "operation": error.operation,
            "attempt_count": error.attempt_count,
            "timestamp": error.timestamp.isoformat(),
            "cause": str(error.cause) if error.cause else None
        }
        
        if error.severity == ErrorSeverity.FATAL:
            self.logger.error(f"FATAL ERROR: {error}", extra=log_context)
        elif error.severity == ErrorSeverity.DEGRADED:
            self.logger.warning(f"DEGRADED ERROR: {error}", extra=log_context)
        else:
            self.logger.info(f"RECOVERABLE ERROR: {error}", extra=log_context)
    
    def _wrap_exception(
        self, 
        exception: Exception, 
        category: ExperimentErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None
    ) -> ExperimentError:
        """Wrap a generic exception into an ExperimentError."""
        
        # Try to map common exceptions to appropriate categories
        if isinstance(exception, (ValueError, TypeError)):
            category = ExperimentErrorCategory.VALIDATION_ERROR
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            category = ExperimentErrorCategory.SYSTEM_ERROR
        elif isinstance(exception, FileNotFoundError):
            category = ExperimentErrorCategory.CONFIGURATION_ERROR
        
        error_class_map = {
            ExperimentErrorCategory.CONFIGURATION_ERROR: ConfigurationError,
            ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR: AgentCommunicationError,
            ExperimentErrorCategory.MEMORY_ERROR: MemoryError,
            ExperimentErrorCategory.VALIDATION_ERROR: ValidationError,
            ExperimentErrorCategory.SYSTEM_ERROR: SystemError,
            ExperimentErrorCategory.EXPERIMENT_LOGIC_ERROR: ExperimentLogicError
        }
        
        error_class = error_class_map.get(category, ExperimentError)
        
        if error_class == ExperimentError:
            return ExperimentError(str(exception), category, severity, context, exception)
        else:
            return error_class(str(exception), severity, context, exception)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about errors encountered."""
        if not self.error_history:
            return {"total_errors": 0}
        
        stats = {
            "total_errors": len(self.error_history),
            "by_category": {},
            "by_severity": {},
            "recent_errors": []
        }
        
        for error in self.error_history:
            # Category stats
            category = error.category.value
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            
            # Severity stats
            severity = error.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
        
        # Recent errors (last 10)
        stats["recent_errors"] = [
            {
                "message": str(error),
                "category": error.category.value,
                "severity": error.severity.value,
                "timestamp": error.timestamp.isoformat()
            }
            for error in self.error_history[-10:]
        ]
        
        return stats
    
    def clear_error_history(self):
        """Clear error history (useful for testing)."""
        self.error_history.clear()


# Convenience decorators for error handling
def handle_experiment_errors(
    category: ExperimentErrorCategory = ExperimentErrorCategory.SYSTEM_ERROR,
    severity: ErrorSeverity = ErrorSeverity.RECOVERABLE,
    operation_name: Optional[str] = None
):
    """Decorator to automatically wrap functions with error handling."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = ExperimentErrorHandler()
            try:
                return await func(*args, **kwargs)
            except ExperimentError:
                raise  # Re-raise experiment errors as-is
            except Exception as e:
                error = error_handler._wrap_exception(
                    e, category, severity, 
                    {"function": func.__name__, "operation": operation_name or func.__name__}
                )
                error.operation = operation_name or func.__name__
                raise error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            error_handler = ExperimentErrorHandler()
            try:
                return func(*args, **kwargs)
            except ExperimentError:
                raise  # Re-raise experiment errors as-is
            except Exception as e:
                error = error_handler._wrap_exception(
                    e, category, severity, 
                    {"function": func.__name__, "operation": operation_name or func.__name__}
                )
                error.operation = operation_name or func.__name__
                raise error
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global error handler instance
_global_error_handler: Optional[ExperimentErrorHandler] = None


def get_global_error_handler() -> ExperimentErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ExperimentErrorHandler()
    return _global_error_handler


def set_global_error_handler(handler: ExperimentErrorHandler):
    """Set the global error handler instance."""
    global _global_error_handler
    _global_error_handler = handler