Services-First Architecture
===========================

The Frohlich Experiment implements a services-first architecture for Phase 2 operations, where specialized services handle specific responsibilities rather than a monolithic manager class. This design provides clean separation of concerns, improved testability, and maintainability.

.. contents:: Table of Contents
   :local:
   :depth: 2

Architecture Overview
---------------------

.. mermaid::

   graph TB
       subgraph "Phase2Manager (Orchestrator)"
           P2M[Phase2Manager]
       end

       subgraph "Specialized Services"
           SO[SpeakingOrderService]
           DS[DiscussionService]
           VS[VotingService]
           MS[MemoryService]
           CFS[CounterfactualsService]
           MPS[ManipulatorService]
           PFS[PreferenceAggregationService]
       end

       subgraph "Core Components"
           AG[Agents]
           UM[Utility Agent]
           LM[Language Manager]
           EM[Error Handler]
           SL[Seed Manager]
           TL[Transcript Logger]
       end

       P2M --> SO
       P2M --> DS
       P2M --> VS
       P2M --> MS
       P2M --> CFS
       P2M --> MPS
       P2M --> PFS

       SO --> AG
       DS --> AG
       VS --> AG
       MS --> AG
       CFS --> AG
       MPS --> AG
       PFS --> AG

       AG --> UM
       AG --> LM
       AG --> EM
       AG --> SL
       AG --> TL

The Phase2Manager acts as an orchestrator that delegates specific responsibilities to specialized services, ensuring clean separation of concerns and maintainability.

Core Services
-------------

SpeakingOrderService
~~~~~~~~~~~~~~~~~~~~

**Location**: ``core/services/speaking_order_service.py``

**Purpose**: Manages speaking turn orders with finisher restrictions and randomization strategies.

**Key Responsibilities**:
- Determine speaking order for discussion rounds
- Apply finisher restrictions (agents who have finished cannot speak again)
- Support different ordering strategies (random, fixed, conversational)
- Track speaking history and ensure fair participation

**Key Methods**:
- ``determine_speaking_order(agents, previous_speakers, strategy)`` → List of speaking agents
- ``apply_finisher_restrictions(agents, finished_agents)`` → Filtered agent list
- ``get_next_speaker(available_agents, strategy)`` → Next agent to speak

**Configuration**:
- ``randomize_speaking_order``: Enable/disable randomization
- ``speaking_order_strategy``: Strategy selection ("random", "fixed", "conversational")

DiscussionService
~~~~~~~~~~~~~~~~~

**Location**: ``core/services/discussion_service.py``

**Purpose**: Handles discussion prompts, statement validation, and history management.

**Key Responsibilities**:
- Generate discussion prompts for each round
- Validate agent statements for appropriateness
- Manage discussion history length and truncation
- Format group composition information
- Handle multilingual discussion prompts

**Key Methods**:
- ``build_discussion_prompt(round_num, speaking_agent, history)`` → Discussion prompt
- ``validate_statement(statement, language_manager)`` → Validation result
- ``manage_discussion_history_length(history, max_length)`` → Truncated history
- ``format_group_composition(agents)`` → Group description

**Configuration**:
- ``public_history_max_length``: Maximum discussion history length (characters)
- ``discussion_validation_enabled``: Enable/disable statement validation
- ``include_internal_reasoning``: Include agent reasoning in history

VotingService
~~~~~~~~~~~~~

**Location**: ``core/services/voting_service.py``

**Purpose**: Manages vote initiation, confirmation phases, and ballot coordination.

**Key Responsibilities**:
- Initiate voting when agents signal readiness
- Coordinate voting confirmation phase (all agents must agree)
- Manage secret ballot voting with numerical validation
- Handle consensus validation and timeout management
- Support two-stage voting (principle selection + constraint specification)

**Key Methods**:
- ``initiate_voting(discussion_state)`` → Voting initiation result
- ``coordinate_voting_confirmation(agents, timeout)`` → Confirmation result
- ``coordinate_secret_ballot(agents, voting_config)`` → Ballot results
- ``validate_consensus(votes, required_consensus)`` → Consensus check

**Configuration**:
- ``voting_timeout_seconds``: Timeout for voting operations
- ``voting_retry_attempts``: Number of retry attempts for failures
- ``two_stage_voting_enabled``: Enable two-stage voting system

MemoryService
~~~~~~~~~~~~~

**Location**: ``core/services/memory_service.py``

**Purpose**: Provides unified memory management with guidance styles and content truncation.

**Key Responsibilities**:
- Update agent memory for discussion events
- Update agent memory for voting events
- Update agent memory for results events
- Apply guidance styles (narrative vs structured)
- Handle content truncation and intelligent preservation
- Route between simple and complex memory update strategies

**Key Methods**:
- ``update_discussion_memory(agent, prompt, context)`` → Memory update result
- ``update_voting_memory(agent, voting_results)`` → Memory update result
- ``update_results_memory(agent, final_results)`` → Memory update result
- ``truncate_content(content, max_length)`` → Truncated content

**Configuration**:
- ``memory_guidance_style``: "narrative" or "structured"
- ``memory_character_limit``: Per-agent memory limit
- ``selective_memory_updates``: Enable selective updates
- ``memory_update_threshold``: Update sensitivity level

CounterfactualsService
~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``core/services/counterfactuals_service.py``

**Purpose**: Handles payoff calculations, counterfactual analysis, and results formatting.

**Key Responsibilities**:
- Calculate payoffs for all justice principles under all income distributions
- Generate counterfactual analysis (what if different principle chosen)
- Format detailed results with transparency options
- Collect and organize final rankings from agents
- Provide insights into best/worst alternative outcomes

**Key Methods**:
- ``calculate_payoffs(distribution, principles)`` → Payoff calculations
- ``format_detailed_results(results, transparency_config)`` → Formatted results
- ``collect_final_rankings(agents, results)`` → Agent rankings
- ``generate_counterfactual_analysis(actual_results)`` → Counterfactual insights

**Configuration**:
- ``include_counterfactuals``: Enable counterfactual analysis
- ``transparency_detail_level``: "basic", "enhanced", or "full"
- ``include_class_assignment``: Show income class assignments
- ``include_insights``: Provide best/worst alternative insights

ManipulatorService (Hypothesis 3)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``core/services/manipulator_service.py``

**Purpose**: Handles experimental manipulations for hypothesis testing scenarios.

**Key Responsibilities**:
- Inject disruptive or manipulative agents into discussions
- Control intervention timing and content
- Track manipulation effects on consensus building
- Provide manipulation analytics and reporting

**Key Methods**:
- ``should_intervene(round_num, discussion_state)`` → Intervention decision
- ``generate_manipulation_prompt(manipulator_config)`` → Manipulation prompt
- ``track_manipulation_effects(before_state, after_state)`` → Effect analysis

**Configuration**:
- ``manipulator.enabled``: Enable/disable manipulation
- ``manipulator.type``: Manipulation strategy ("disruptive", "persuasive", etc.)
- ``manipulator.intervention_round``: When to intervene

PreferenceAggregationService
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Location**: ``core/services/preference_aggregation_service.py``

**Purpose**: Handles vote aggregation and preference analysis across agents.

**Key Responsibilities**:
- Aggregate voting preferences from multiple agents
- Handle tie-breaking mechanisms
- Detect consensus patterns and voting coalitions
- Provide preference analysis and visualization data

**Key Methods**:
- ``aggregate_preferences(votes, aggregation_method)`` → Aggregated result
- ``detect_consensus(votes, threshold)`` → Consensus analysis
- ``break_ties(tied_options, tie_breaker)`` → Tie resolution

Service Integration Patterns
-----------------------------

Protocol-Based Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All services follow protocol-based dependency injection for clean testing and maintainability:

.. code-block:: python

   from typing import Protocol

   class SpeakingOrderProtocol(Protocol):
       def determine_speaking_order(self, agents, previous_speakers, strategy) -> List:
           ...

   class DiscussionService:
       def __init__(self, speaking_order_service: SpeakingOrderProtocol):
           self.speaking_order = speaking_order_service

Service Lifecycle
~~~~~~~~~~~~~~~~~

Services are instantiated once per experiment and reused throughout Phase 2:

.. code-block:: python

   # In Phase2Manager.__init__
   self.speaking_order_service = SpeakingOrderService()
   self.discussion_service = DiscussionService(
       speaking_order_service=self.speaking_order_service
   )
   self.voting_service = VotingService()
   self.memory_service = MemoryService()
   self.counterfactuals_service = CounterfactualsService()

Error Handling and Recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each service includes comprehensive error handling:

.. code-block:: python

   # Service-level error handling
   try:
       result = await self.voting_service.coordinate_secret_ballot(agents, config)
   except VotingTimeoutError:
       # Handle timeout with retry or fallback
       result = await self._handle_voting_timeout(agents, config)
   except ConsensusFailureError:
       # Continue discussion if consensus not reached
       await self._continue_discussion()

Configuration Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

Services access configuration through the Phase2Manager:

.. code-block:: python

   # Phase2Settings integration
   phase2_config = experiment_config.phase2_settings or Phase2Settings()

   # Pass relevant config to services
   discussion_service = DiscussionService(
       max_history_length=phase2_config.public_history_max_length,
       validation_enabled=phase2_config.statement_validation_enabled
   )

Testing Strategy
----------------

Services-First Testing
~~~~~~~~~~~~~~~~~~~~~~

The services architecture enables focused unit testing:

.. code-block:: python

   # Test services in isolation
   async def test_voting_service():
       service = VotingService()
       mock_agents = create_mock_agents()

       result = await service.coordinate_secret_ballot(mock_agents, config)
       assert result.consensus_reached == True

Protocol-Based Mocking
~~~~~~~~~~~~~~~~~~~~~~~

Protocol interfaces enable easy mocking:

.. code-block:: python

   class MockSpeakingOrderService:
       def determine_speaking_order(self, agents, previous_speakers, strategy):
           return agents  # Simple mock implementation

   # Use in tests
   service = DiscussionService(speaking_order_service=MockSpeakingOrderService())

Migration Benefits
------------------

The services-first architecture provides several benefits:

**Maintainability**
- Single responsibility per service
- Clear interfaces and contracts
- Easy to modify individual behaviors

**Testability**
- Services can be tested in isolation
- Protocol-based dependency injection
- Focused unit test coverage

**Scalability**
- Easy to add new services
- Services can be optimized independently
- Clean separation enables parallel development

**Reliability**
- Comprehensive error handling per service
- Graceful degradation on service failures
- Independent retry mechanisms

Integration with Phase2Manager
------------------------------

The Phase2Manager orchestrates service interactions:

.. code-block:: python

   async def run_phase2(self):
       # Initialize services
       services = self._initialize_services()

       # Main discussion loop
       while not consensus_reached and round_num < max_rounds:
           # 1. Determine speaking order
           speakers = await services.speaking_order.determine_speaking_order(...)

           # 2. Conduct discussion round
           discussion_result = await services.discussion.conduct_round(...)

           # 3. Update memories
           await services.memory.update_discussion_memory(...)

           # 4. Check for voting initiation
           if await services.voting.should_initiate_voting(...):
               # Run voting process
               voting_result = await services.voting.coordinate_voting(...)
               consensus_reached = voting_result.consensus_reached

       # Generate final results
       final_results = await services.counterfactuals.format_detailed_results(...)

This architecture ensures clean separation of concerns while maintaining cohesive Phase 2 execution.

See Also
--------

- :doc:`../user-guide/running-experiments` - Learn how to configure and run experiments
- :doc:`../user-guide/custom-agents` - Create custom agents that work with services
- :doc:`../api/core` - API reference for core components
- :doc:`system-overview` - High-level system architecture
- :doc:`configuration` - Configuration system documentation
- :doc:`../phase2-settings` - Phase 2 behavior configuration