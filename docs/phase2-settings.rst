Phase 2 Settings Configuration
==============================

The Phase 2 Settings provide fine-grained control over Phase 2 experimental behavior, including timeouts, validation rules, memory management, and consensus mechanisms. This documentation covers all configuration options and their impact on experiment execution.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

Phase 2 Settings are configured through the ``phase2_settings`` field in the main experiment configuration. These settings control the sophisticated services-first architecture that manages group discussion, voting, and consensus building.

.. code-block:: yaml

   # Basic Phase 2 configuration
   phase2_settings:
     # Statement validation
     min_statement_length: 10
     max_statement_retries: 3

     # Timeouts
     statement_timeout_seconds: 600
     confirmation_timeout_seconds: 600

     # Memory management
     memory_compression_threshold: 0.9
     public_history_max_length: 50000

If not specified, default Phase2Settings are used automatically.

Statement Validation
--------------------

Control validation rules for agent statements during discussion:

.. code-block:: yaml

   phase2_settings:
     # Minimum statement lengths
     min_statement_length: 10              # Minimum characters for statements
     min_statement_length_cjk: 5           # Shorter for CJK languages (Chinese, Japanese, Korean)

     # Retry behavior
     max_statement_retries: 3              # Maximum retry attempts (1-10)
     retry_backoff_factor: 1.5             # Exponential backoff multiplier (1.0-3.0)

**Validation Rules:**

- Statements must meet minimum length requirements
- CJK languages have adjusted length requirements due to character density
- Failed statements trigger automatic retries with exponential backoff
- Invalid statements are quarantined from public discussion history

Timeout Configuration
---------------------

Configure timeouts for different Phase 2 operations:

.. code-block:: yaml

   phase2_settings:
     # Response timeouts (seconds)
     statement_timeout_seconds: 600        # Agent statement responses (10-600)
     confirmation_timeout_seconds: 600     # Voting confirmation responses (10-600)
     ballot_timeout_seconds: 600          # Secret ballot responses (10-600)

     # Specialized timeouts
     reasoning_timeout_seconds: 600       # Internal reasoning calls (10-600)
     constraint_correction_timeout_seconds: 600  # Constraint correction (10-600)

**Timeout Behavior:**

- Operations automatically fail after timeout
- Timeouts trigger retry mechanisms where applicable
- Failed operations are logged with timeout reasons
- System continues with available responses when possible

Reasoning System
-----------------

Control the two-step reasoning system (internal reasoning + public statement):

.. code-block:: yaml

   phase2_settings:
     # Reasoning configuration
     reasoning_enabled: true               # Enable two-step reasoning
     reasoning_max_retries: 2              # Maximum reasoning retries (1-5)

**Reasoning Process:**

1. **Internal Reasoning**: Agent thinks through response privately
2. **Public Statement**: Agent provides final, polished response
3. **Retry Logic**: Automatic retries on reasoning failures
4. **Fallback**: Direct public statement if reasoning fails

Memory Management
-----------------

Configure memory compression and validation:

.. code-block:: yaml

   phase2_settings:
     # Memory compression
     memory_compression_threshold: 0.9     # Compression trigger (0.5-0.95)
     memory_validation_strict: true        # Strict memory integrity checks

     # Public history management
     public_history_max_length: 50000      # Maximum history length (characters)
     quarantine_failed_responses: true     # Isolate failed responses

**Memory Management:**

- Automatic compression when approaching limits
- Intelligent truncation preserving most important content
- Failed responses can be quarantined from shared history
- Strict validation ensures memory integrity

Consensus Configuration
-----------------------

Control consensus building and constraint handling:

.. code-block:: yaml

   phase2_settings:
     # Consensus tolerance
     constraint_tolerance: 0                # Tolerance for constraint matching (0 = exact)

     # Agent requirements
     min_agents_for_experiment: 2           # Minimum agents required (≥2)

**Consensus Rules:**

- Zero tolerance requires exact constraint matching
- Higher tolerance allows small differences in amount specifications
- Minimum agent validation prevents invalid small-group experiments

Constraint Correction
---------------------

Configure automatic constraint correction for Principles 3 and 4:

.. code-block:: yaml

   phase2_settings:
     # Constraint correction
     constraint_correction_enabled: true    # Enable automatic correction
     max_constraint_correction_attempts: 2  # Maximum correction attempts (1-5)

**Constraint Correction Process:**

1. Agent proposes principle with constraint
2. System validates constraint specification
3. Automatic correction attempts if invalid
4. Multiple correction rounds allowed
5. Fallback to agent clarification if correction fails

Two-Stage Voting
-----------------

Configure the structured voting system:

.. code-block:: yaml

   phase2_settings:
     # Two-stage voting
     two_stage_voting_enabled: true         # Enable structured voting
     two_stage_max_retries: 3               # Maximum voting retries (1-10)

**Two-Stage Voting Process:**

1. **Stage 1**: Principle selection (numerical input 1-4)
2. **Stage 2**: Constraint specification (for Principles 3 & 4)
3. **Validation**: Automatic validation with fallback parsing
4. **Retry Logic**: Automatic retries on parsing failures

Advanced Configuration Examples
-------------------------------

**High-Performance Configuration:**

.. code-block:: yaml

   phase2_settings:
     # Optimized for speed
     statement_timeout_seconds: 300         # Faster timeouts
     max_statement_retries: 1               # Minimal retries
     reasoning_enabled: false               # Skip internal reasoning
     memory_compression_threshold: 0.8      # Earlier compression
     public_history_max_length: 25000       # Smaller history

**High-Quality Configuration:**

.. code-block:: yaml

   phase2_settings:
     # Optimized for quality
     statement_timeout_seconds: 900         # More time for responses
     max_statement_retries: 5               # More retry attempts
     reasoning_enabled: true                # Full reasoning process
     memory_validation_strict: true         # Strict memory checks
     constraint_tolerance: 100              # Flexible constraint matching

**Research-Grade Configuration:**

.. code-block:: yaml

   phase2_settings:
     # Optimized for research validity
     min_statement_length: 20               # Require detailed responses
     reasoning_enabled: true                # Full cognitive process
     memory_validation_strict: true         # Ensure data integrity
     quarantine_failed_responses: true      # Clean data collection
     two_stage_voting_enabled: true         # Structured voting process

Default Settings
----------------

If no Phase 2 settings are specified, the system uses these defaults:

.. code-block:: yaml

   phase2_settings:
     # Validation
     min_statement_length: 10
     min_statement_length_cjk: 5
     max_statement_retries: 3

     # Timeouts
     statement_timeout_seconds: 600
     confirmation_timeout_seconds: 600
     ballot_timeout_seconds: 600
     reasoning_timeout_seconds: 600

     # Memory
     memory_compression_threshold: 0.9
     memory_validation_strict: true
     public_history_max_length: 50000
     quarantine_failed_responses: true

     # Consensus
     constraint_tolerance: 0
     min_agents_for_experiment: 2

     # Reasoning
     reasoning_enabled: true
     reasoning_max_retries: 2

     # Constraint Correction
     constraint_correction_enabled: true
     constraint_correction_timeout_seconds: 600
     max_constraint_correction_attempts: 2

     # Two-Stage Voting
     two_stage_voting_enabled: true
     two_stage_max_retries: 3

     # Retry Settings
     max_memory_retries: 5
     retry_backoff_factor: 1.5

Configuration Validation
-------------------------

The Phase2Settings model includes comprehensive validation:

.. code-block:: python

   from config.phase2_settings import Phase2Settings

   # Valid configuration
   settings = Phase2Settings(
       min_statement_length=15,
       statement_timeout_seconds=300,
       reasoning_enabled=True
   )

   # Invalid configurations will raise ValidationError
   # - Timeouts outside 10-600 second range
   # - Retry counts outside allowed ranges
   # - Invalid compression thresholds

**Validation Rules:**

- All timeouts must be between 10-600 seconds
- Retry counts have specific min/max limits
- Memory thresholds must be between 0.5-0.95
- Minimum agent count cannot be less than 2

Integration with Main Configuration
-----------------------------------

Phase 2 settings integrate seamlessly with the main experiment configuration:

.. code-block:: yaml

   # Complete experiment configuration
   language: "english"

   agents:
     - name: "Alice"
       personality: "Analytical researcher"
       model: "gpt-4.1-mini"

   # Phase 2 specific settings
   phase2_settings:
     reasoning_enabled: true
     memory_compression_threshold: 0.85
     public_history_max_length: 75000

   # Other experiment settings...
   phase2_rounds: 10
   memory_guidance_style: "structured"

**Integration Benefits:**

- Settings are automatically passed to Phase 2 services
- Validation occurs at configuration load time
- Settings override defaults only where specified
- Clean separation between general and Phase 2 specific settings

Performance Impact
------------------

Different settings have varying performance implications:

**Performance-Optimized Settings:**
- Shorter timeouts reduce waiting time
- Disabled reasoning reduces API calls
- Lower retry counts speed up failures
- Smaller history limits reduce memory usage

**Quality-Optimized Settings:**
- Longer timeouts allow better responses
- Enabled reasoning provides deeper analysis
- Higher retry counts improve success rates
- Larger history preserves conversation context

**Research-Optimized Settings:**
- Strict validation ensures data integrity
- Comprehensive logging captures all details
- Quarantined responses maintain clean datasets
- Full reasoning process captures cognitive steps

Monitoring and Debugging
-------------------------

Phase 2 settings affect logging and debugging output:

.. code-block:: python

   # Enable detailed Phase 2 logging
   import logging
   logging.getLogger('core.phase2_manager').setLevel(logging.DEBUG)
   logging.getLogger('core.services').setLevel(logging.DEBUG)

   # Monitor timeout events
   # Monitor retry attempts
   # Monitor memory compression
   # Monitor constraint corrections

**Debug Information:**

- Timeout events with duration tracking
- Retry attempts with failure reasons
- Memory compression operations
- Constraint correction attempts
- Voting process validation steps

Best Practices
--------------

**Development Settings:**
- Use shorter timeouts for faster iteration
- Enable relaxed validation for experimentation
- Reduce history limits to speed up testing

**Production Settings:**
- Use standard timeouts for quality responses
- Enable full validation and error handling
- Configure appropriate history limits for experiment size

**Research Settings:**
- Enable comprehensive logging and validation
- Use structured reasoning for cognitive analysis
- Configure strict consensus requirements
- Enable full transcript logging

This Phase 2 settings system provides researchers with complete control over the sophisticated experimental procedures while maintaining system reliability and performance.

See Also
--------

- :doc:`architecture/services-architecture` - How Phase 2 settings control services
- :doc:`user-guide/running-experiments` - Using Phase 2 settings in experiments
- :doc:`user-guide/designing-experiments` - Configuring Phase 2 settings
- :doc:`error-handling` - Error handling affected by Phase 2 settings
- :doc:`architecture/system-overview` - System architecture overview