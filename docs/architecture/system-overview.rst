System Overview
===============

The Frohlich Experiment implements a sophisticated multi-agent architecture designed for researching distributive justice through AI agent interactions. This section provides a comprehensive overview of the system's components, data flow, and key design decisions.

High-Level Architecture
-----------------------

.. code-block:: text

                    ┌─────────────────────────┐
                    │   Experiment Manager    │
                    │   - Orchestration       │
                    │   - Tracing             │
                    │   - Error Handling      │
                    └──────────┬──────────────┘
                               │
                    ┌──────────┴──────────────┐
                    │                         │
          ┌─────────▼────────┐     ┌─────────▼────────┐
          │   Phase 1 Mgr    │     │   Phase 2 Mgr    │
          │   - Parallel     │     │   - Sequential    │
          │   - Individual   │     │   - Group Disc.   │
          └─────────┬────────┘     └─────────┬────────┘
                    │                        │
          ┌─────────▼────────┐     ┌─────────▼────────┐
          │  Participant     │     │  Services Layer  │
          │  Agents (3+)     │     │  - Discussion     │
          │  - Memory Mgmt   │     │  - Voting         │
          │  - Model Config  │     │  - Memory         │
          └─────────┬────────┘     │  - Counterfactuals│
                    │              └─────────┬────────┘
                    └────────┬───────────────┘
                             │
                   ┌─────────▼────────┐
                   │  Utility Agent   │
                   │  - Validation    │
                   │  - Parsing       │
                   │  - Logging       │
                   └──────────────────┘

Core Components
---------------

ExperimentManager
~~~~~~~~~~~~~~~~~

The central orchestrator that coordinates the complete experimental flow:

**Responsibilities:**
- Initialize all agent components asynchronously
- Manage experiment lifecycle and tracing
- Handle error recovery and reporting
- Generate comprehensive results and logging

**Key Features:**
- OpenAI SDK integration for professional tracing
- Configurable error handling with retry mechanisms
- Structured post-run outputs (agent log + summary)
- Agent-centric logging system

Phase Managers
~~~~~~~~~~~~~~

**Phase1Manager**
   - **Execution Model**: Parallel processing for efficiency
   - **Purpose**: Individual agent familiarization with justice principles
   - **Process**: Each agent independently works through 4 justice principles across multiple distribution scenarios
   - **Memory**: Agents build and maintain personal knowledge throughout the phase

**Phase2Manager**
   - **Execution Model**: Sequential processing to capture interaction dynamics
   - **Architecture**: Services-first design with specialized service components
   - **Purpose**: Group discussion and consensus building through orchestrated services
   - **Services**: Discussion, Voting, Memory, Counterfactuals, Speaking Order, and Manipulator services
   - **Process**: Structured discussion with random speaking order, voting mechanisms, and payoff calculations
   - **Consensus**: Multi-round voting with tie-breaking mechanisms

Agent Architecture
------------------

Participant Agents
~~~~~~~~~~~~~~~~~~

Each participant agent is a sophisticated autonomous entity with:

**Core Capabilities:**
- **Reasoning**: Configurable reasoning modes for different complexity levels
- **Memory Management**: Self-directed memory creation and maintenance (default 50,000 characters)
- **Model Flexibility**: Support for OpenAI and OpenRouter model providers
- **Temperature Control**: Dynamic temperature adjustment with retry mechanisms
- **Multi-language**: Full experimental support for English, Spanish, and Mandarin

**Configuration Options:**

.. code-block:: yaml

   agents:
     - name: "Alice"
       personality: "Analytical and methodical. Values fairness and systematic approaches."
       model: "gpt-4.1-mini"
       temperature: 0.0
       memory_character_limit: 50000
       reasoning_enabled: true

**Memory System:**
- **Agent-Controlled**: Agents decide what to remember and how to structure memory
- **Persistent**: Memory carries across both experimental phases
- **Error Handling**: 5 retry attempts if memory exceeds limits
- **Complete Freedom**: No restrictions on memory content or format

Utility Agent
~~~~~~~~~~~~~

Specialized agent for system operations:

- **Response Parsing**: Validates and extracts structured data from participant responses
- **Constraint Validation**: Ensures justice principle constraints are properly specified
- **Multi-language Support**: Processes responses in participant's chosen language
- **Error Detection**: Identifies and reports formatting or logical errors

Data Flow Architecture
----------------------

Configuration → Initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **YAML Configuration Loading**: Pydantic models ensure type safety and validation
2. **Agent Creation**: Asynchronous initialization with model provider detection
3. **Memory System Setup**: Agent-managed memory initialization
4. **Tracing Configuration**: OpenAI SDK trace initialization

Phase 1: Individual Learning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Parallel Execution**: All agents work simultaneously for efficiency
2. **Principle Application**: Agents apply each justice principle to distribution scenarios
3. **Memory Updates**: Agents update their memory after each principle application
4. **Response Validation**: Utility agent validates and logs all responses

Phase 2: Group Dynamics
~~~~~~~~~~~~~~~~~~~~~~~

1. **Sequential Discussion**: Agents participate in random-order discussion
2. **Voting Mechanisms**: Structured voting on preferred justice principles
3. **Consensus Building**: Multi-round process with tie-breaking
4. **Payoff Calculation**: Final income distribution based on chosen principle

Results Generation
~~~~~~~~~~~~~~~~~~

1. **Agent Log**: Complete transcript of agent interactions saved to ``experiment_results_<timestamp>.json``
2. **Trace Links**: OpenAI platform URLs emitted in the console when tracing is enabled
3. **Console Output**: Human-readable progress updates and warnings

Technology Stack
----------------

Core Framework
~~~~~~~~~~~~~~

- **OpenAI Agents SDK**: Professional multi-agent framework with built-in tracing
- **LiteLLM Integration**: Support for multiple model providers beyond OpenAI
- **Asyncio**: Efficient asynchronous processing for Phase 1 parallelization

Data & Configuration
~~~~~~~~~~~~~~~~~~~~

- **Pydantic**: Type-safe data models and configuration validation
- **PyYAML**: Human-readable configuration files
- **JSON**: Results serialization and storage

Testing & Quality
~~~~~~~~~~~~~~~~~

- **Unittest**: Comprehensive unit test coverage
- **Integration Tests**: End-to-end experiment validation
- **Error Simulation**: Failure scenario testing and recovery validation

Design Principles
-----------------

Modularity
~~~~~~~~~~

- **Service-Oriented Architecture**: Clear separation of concerns
- **Plugin-Style Agents**: Easy to extend with new agent types
- **Configuration-Driven**: All parameters externally configurable

Reliability
~~~~~~~~~~~

- **Error Categorization**: Standardized error types (Memory, Validation, Communication, System, Experiment Logic)
- **Automatic Recovery**: Configurable retry mechanisms with exponential backoff
- **Graceful Degradation**: System continues despite partial failures

Performance
~~~~~~~~~~~

- **Parallel Phase 1**: Simultaneous agent processing for efficiency
- **Memory Management**: Configurable limits with automatic validation
- **Lazy Loading**: Components initialized only when needed

Scalability
~~~~~~~~~~~

- **Multi-Model Support**: Mix different AI model providers in single experiments
- **Language Flexibility**: Full support for multiple human languages
- **Batch Processing**: Utilities for running multiple experiments in parallel

Memory Management Architecture
------------------------------

The Frohlich Experiment implements a sophisticated memory system that enables agents to maintain context and learn throughout experiments.

.. code-block:: text

   Memory Management Architecture
   ├── Agent-Level Memory
   │   ├── Persistent Storage: 50,000 char default limit
   │   ├── Self-Managed Content: Agents decide what to remember
   │   ├── Cross-Phase Continuity: Memory carries from Phase 1 to Phase 2
   │   └── Intelligent Truncation: Preserves most relevant content
   │
   ├── Update Strategies
   │   ├── Simple Events: Direct addition (quick votes, basic responses)
   │   ├── Complex Events: Narrative/structured formatting (discussions, reasoning)
   │   ├── Selective Updates: Skip trivial events to reduce API calls
   │   └── Batch Processing: Group multiple simple events together
   │
   ├── Guidance Styles
   │   ├── Narrative: Conversational, story-like memory entries
   │   ├── Structured: Bullet-point, factual memory entries
   │   └── Configurable: Per-experiment style selection
   │
   └── Validation & Recovery
       ├── Length Limits: Automatic enforcement with retry
       ├── Content Integrity: Validation of memory structure
       └── Error Recovery: Fallback mechanisms for memory failures

**Key Memory Components:**

- **MemoryManager**: Central coordinator for all memory operations
- **MemoryService**: Phase 2 memory orchestration through services
- **Agent Memory**: Individual agent persistent storage
- **Memory Validation**: Ensures memory integrity and limits

**Memory Flow During Experiment:**

1. **Phase 1**: Agents build foundational knowledge through principle applications
2. **Phase 2**: Memory guides discussion participation and voting decisions
3. **Post-Experiment**: Memory analysis reveals agent learning patterns

This architecture provides robust memory management while maintaining performance and reliability.

This architecture provides a robust foundation for researching AI ethics, distributive justice, and multi-agent cooperation while maintaining the flexibility to support diverse research questions and experimental designs.

See Also
--------

- :doc:`services-architecture` - Detailed documentation of the Phase 2 services-first architecture
- :doc:`configuration` - Configuration system and available options
- :doc:`experiment-flow` - Detailed experiment execution flow
- :doc:`../user-guide/running-experiments` - How to run experiments with this architecture
