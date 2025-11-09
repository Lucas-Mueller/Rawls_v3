Error Handling & Recovery
==========================

The Frohlich Experiment implements a comprehensive error handling and recovery system that ensures experimental reliability, data integrity, and graceful degradation. This documentation covers error categorization, retry mechanisms, recovery strategies, and monitoring capabilities.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

The error handling system provides standardized error management across all experiment components:

.. code-block:: text

   Error Handling Architecture
   ├── Error Categorization
   │   ├── Configuration Errors
   │   ├── Agent Communication Errors
   │   ├── Memory Management Errors
   │   ├── Validation Errors
   │   ├── System Errors
   │   └── Experiment Logic Errors
   │
   ├── Severity Levels
   │   ├── Recoverable (retry/continue)
   │   ├── Degraded (reduced functionality)
   │   └── Fatal (abort experiment)
   │
   ├── Recovery Mechanisms
   │   ├── Automatic Retry with Backoff
   │   ├── Graceful Degradation
   │   ├── Alternative Pathways
   │   └── Data Preservation
   │
   └── Monitoring & Reporting
       ├── Error Statistics
       ├── Performance Metrics
       └── Recovery Analytics

Error Categories
----------------

The system categorizes errors for appropriate handling strategies:

**Configuration Errors**
   - Invalid YAML syntax or structure
   - Missing required fields
   - Type validation failures
   - Incompatible parameter combinations

**Agent Communication Errors**
   - API rate limiting
   - Network connectivity issues
   - Model unavailability
   - Timeout exceeded
   - Invalid API responses

**Memory Management Errors**
   - Memory limit exceeded
   - Memory corruption detected
   - Compression failures
   - Memory validation errors

**Validation Errors**
   - Response format validation failures
   - Constraint specification errors
   - Statement length requirements not met
   - Data integrity violations

**System Errors**
   - Infrastructure failures
   - Resource exhaustion
   - File system errors
   - Database connectivity issues

**Experiment Logic Errors**
   - Invalid state transitions
   - Consensus algorithm failures
   - Phase sequencing errors
   - Agent coordination failures

Error Severity Levels
---------------------

Errors are classified by severity to determine appropriate response:

**Recoverable Errors**
   - Can be resolved through retry mechanisms
   - Experiment can continue normally after recovery
   - Examples: temporary API timeouts, network glitches

**Degraded Errors**
   - Cannot be fully resolved but experiment can continue
   - May result in reduced functionality or data quality
   - Examples: memory compression failures, partial data loss

**Fatal Errors**
   - Experiment cannot continue safely
   - Require immediate abortion and cleanup
   - Examples: configuration corruption, critical data loss

Automatic Retry Mechanisms
---------------------------

The system implements intelligent retry logic with exponential backoff:

.. code-block:: python

   from utils.error_handling import handle_with_retry

   @handle_with_retry(
       max_attempts=3,
       backoff_factor=2.0,
       recoverable_categories=[ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR]
   )
   async def unreliable_operation():
       # Operation that may fail
       pass

**Retry Configuration:**

.. code-block:: yaml

   # Retry settings in Phase 2 configuration
   phase2_settings:
     max_statement_retries: 3              # Maximum retry attempts
     retry_backoff_factor: 1.5             # Exponential backoff multiplier
     max_memory_retries: 5                 # Memory operation retries

**Retry Behavior:**

- Exponential backoff prevents API rate limit violations
- Jitter added to prevent thundering herd problems
- Maximum retry limits prevent infinite loops
- Different retry strategies for different error categories

Graceful Degradation
--------------------

The system continues operation with reduced functionality when full recovery is impossible:

**Memory Degradation:**
- Automatic compression when limits are approached
- Intelligent truncation preserving most important content
- Fallback to simplified memory structures
- Continued operation with reduced context

**Communication Degradation:**
- Fallback to alternative model providers
- Simplified prompts when complex generation fails
- Reduced reasoning complexity
- Continued operation with basic functionality

**Validation Degradation:**
- Relaxed validation rules for edge cases
- Partial validation when full validation fails
- Warning generation instead of failure
- Continued operation with quality monitoring

Error Recovery Strategies
-------------------------

**Agent Communication Recovery:**

.. code-block:: python

   # Automatic model fallback
   async def communicate_with_fallback(agent, prompt):
       primary_models = ["gpt-4.1-mini", "gpt-4-turbo"]
       fallback_models = ["gemini-2.5-flash", "claude-3-haiku"]

       for model in primary_models + fallback_models:
           try:
               response = await agent.run_with_model(prompt, model)
               return response
           except Exception as e:
               logger.warning(f"Model {model} failed: {e}")
               continue

       raise ExperimentError("All models failed", category=AGENT_COMMUNICATION_ERROR)

**Memory Recovery:**

.. code-block:: python

   # Memory limit recovery
   async def recover_memory_limit(agent, content):
       # Attempt compression first
       compressed = compress_memory_content(content)
       if validate_memory_size(compressed):
           return compressed

       # Fallback to intelligent truncation
       truncated = truncate_memory_intelligently(content)
       if validate_memory_size(truncated):
           return truncated

       # Final fallback: clear oldest content
       emergency_clear = clear_oldest_memories(content)
       return emergency_clear

**State Recovery:**

.. code-block:: python

   # Experiment state recovery
   async def recover_experiment_state(failed_state):
       # Attempt to reconstruct from logs
       reconstructed = reconstruct_from_logs(failed_state)

       # Validate reconstructed state
       if validate_experiment_state(reconstructed):
           return reconstructed

       # Fallback to checkpoint restart
       checkpoint = load_last_checkpoint()
       return resume_from_checkpoint(checkpoint)

Error Monitoring & Statistics
------------------------------

The system provides comprehensive error tracking and analysis:

**Error Statistics Collection:**

.. code-block:: python

   # Access error statistics from results
   results = await run_experiment(config)

   error_stats = results.get('error_statistics', {})
   total_errors = sum(error_stats.values())

   print(f"Total recoverable errors: {total_errors}")
   for error_type, count in error_stats.items():
       percentage = (count / total_errors) * 100
       print(f"{error_type}: {count} ({percentage:.1f}%)")

**Error Categories Tracked:**

- Memory limit exceeded events
- API timeout occurrences
- Validation failure rates
- Network connectivity issues
- Model availability problems
- Configuration validation errors

Performance Impact Monitoring
-----------------------------

Error handling has measurable performance implications:

**Retry Performance:**
- Each retry attempt adds latency
- Exponential backoff reduces API load
- Smart retry logic minimizes total delay

**Degradation Performance:**
- Graceful degradation maintains basic functionality
- Performance monitoring tracks degradation impact
- Automatic recovery attempts minimize downtime

**Recovery Performance:**
- Recovery operations are optimized for speed
- Parallel recovery attempts where possible
- Caching prevents repeated recovery operations

Configuration Examples
----------------------

**Robust Experiment Configuration:**

.. code-block:: yaml

   # Error-resilient configuration
   phase2_settings:
     # Generous timeouts for reliability
     statement_timeout_seconds: 900
     confirmation_timeout_seconds: 900
     ballot_timeout_seconds: 900

     # Extensive retry capabilities
     max_statement_retries: 5
     max_memory_retries: 10
     retry_backoff_factor: 2.0

     # Memory resilience
     memory_compression_threshold: 0.8
     memory_validation_strict: true
     public_history_max_length: 100000

   # Intelligent retry system
   enable_intelligent_retries: true
   max_participant_retries: 3
   retry_feedback_detail: "detailed"

**High-Performance Configuration:**

.. code-block:: yaml

   # Speed-optimized configuration
   phase2_settings:
     # Aggressive timeouts
     statement_timeout_seconds: 300
     confirmation_timeout_seconds: 300

     # Minimal retries for speed
     max_statement_retries: 1
     max_memory_retries: 2

     # Memory optimization
     memory_compression_threshold: 0.9
     public_history_max_length: 25000

   # Disable complex error recovery
   enable_intelligent_retries: false
   max_participant_retries: 0

**Research-Grade Configuration:**

.. code-block:: yaml

   # Data integrity focused
   phase2_settings:
     # Extended timeouts for quality
     statement_timeout_seconds: 1200
     reasoning_timeout_seconds: 900

     # Comprehensive validation
     memory_validation_strict: true
     quarantine_failed_responses: true

     # Full error tracking
     max_statement_retries: 5

   # Enhanced error reporting
   logging:
     verbosity_level: "detailed"

   transcript_logging:
     enabled: true
     include_memory_updates: true
     include_agent_responses: true

Best Practices
--------------

**Error Prevention:**
- Use validated configurations to prevent setup errors
- Monitor API rate limits to avoid throttling
- Implement proper resource limits to prevent exhaustion
- Test configurations with small experiments first

**Error Recovery:**
- Enable appropriate retry mechanisms for your use case
- Configure graceful degradation for production systems
- Monitor error rates and adjust timeouts accordingly
- Implement comprehensive logging for debugging

**Performance Optimization:**
- Balance reliability with performance requirements
- Use shorter timeouts for development, longer for production
- Monitor error statistics to identify systemic issues
- Implement caching to reduce API call frequency

**Monitoring & Alerting:**
- Set up alerts for high error rates
- Monitor recovery success rates
- Track performance impact of error handling
- Maintain error logs for post-mortem analysis

Troubleshooting Common Issues
------------------------------

**High Memory Error Rates:**

.. code-block:: python

   # Diagnose memory issues
   def diagnose_memory_errors(results):
       memory_errors = results.get('error_statistics', {}).get('memory', 0)
       total_operations = results.get('total_operations', 1)

       error_rate = memory_errors / total_operations
       if error_rate > 0.1:  # 10% error rate
           print("High memory error rate detected")
           print("Consider increasing memory limits or enabling compression")
           return True
       return False

**API Timeout Issues:**

.. code-block:: python

   # Analyze timeout patterns
   def analyze_timeout_patterns(results):
       timeouts = results.get('timeout_events', [])

       # Group by operation type
       timeout_by_operation = {}
       for timeout in timeouts:
           operation = timeout.get('operation')
           timeout_by_operation[operation] = timeout_by_operation.get(operation, 0) + 1

       # Identify problematic operations
       for operation, count in timeout_by_operation.items():
           if count > 5:  # More than 5 timeouts per operation type
               print(f"High timeout rate for {operation}: {count} timeouts")
               print("Consider increasing timeout values or optimizing prompts")

**Validation Failure Analysis:**

.. code-block:: python

   # Analyze validation failures
   def analyze_validation_failures(results):
       validation_errors = results.get('validation_errors', [])

       # Categorize by failure type
       failures_by_type = {}
       for error in validation_errors:
           failure_type = error.get('type')
           failures_by_type[failure_type] = failures_by_type.get(failure_type, 0) + 1

       # Report most common failures
       for failure_type, count in sorted(failures_by_type.items(), key=lambda x: x[1], reverse=True):
           print(f"{failure_type}: {count} failures")
           if failure_type == "statement_too_short":
               print("Consider reducing min_statement_length or improving prompts")
           elif failure_type == "constraint_invalid":
               print("Consider enabling constraint_correction_enabled")

This comprehensive error handling system ensures the Frohlich Experiment maintains reliability and data integrity even under adverse conditions, while providing detailed monitoring and recovery capabilities for research and production use cases.

See Also
--------

- :doc:`user-guide/running-experiments` - Error handling in experiment execution
- :doc:`phase2-settings` - Phase 2 configuration affecting error handling
- :doc:`architecture/system-overview` - System reliability architecture
- :doc:`contributing/testing` - Testing error scenarios
- :doc:`user-guide/analyzing-results` - Analyzing error statistics in results