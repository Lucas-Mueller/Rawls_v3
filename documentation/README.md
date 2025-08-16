# MAAI Frohlich Experiment - Architecture Documentation

This directory contains comprehensive architectural diagrams and documentation for the Multi-Agent AI (MAAI) Frohlich Experiment system.

## Architecture Diagrams

We provide two types of architectural diagrams:

### 🎨 Clean, Simplified Diagrams (Recommended)

**For academic publications and high-level understanding**

**Prerequisites:** Mermaid CLI (optional for PNG generation)
```bash
npm install -g @mermaid-js/mermaid-cli
```

**Generate diagrams:**
```bash
python documentation/generate_clean_architecture_diagrams.py
```

**Files created:**
- `clean_01_overall_architecture.png` - High-level system overview
- `clean_02_experimental_flow.png` - Phase 1 & 2 process flow  
- `clean_03_agent_architecture.png` - Agent processing pipeline
- `clean_04_data_flow.png` - Data collection & analysis
- `clean_05_bank_account_system.png` - Economic incentive system
- `clean_06_consensus_mechanism.png` - Group consensus process

### 🔧 Detailed Implementation Diagrams

**For technical implementation and detailed system understanding**

**Prerequisites:** Diagrams library
```bash
pip install diagrams
```

**Generate diagrams:**
```bash
python documentation/generate_architecture_diagrams.py
```

## Clean Architectural Diagrams (Recommended for Academic Use)

The clean diagrams focus on conceptual understanding and are perfect for academic publications, presentations, and high-level system understanding.

### 1. Overall System Architecture (`clean_01_overall_architecture.png`)
**Purpose**: High-level view of the MAAI system with clear separation of concerns
- **Configuration Layer**: YAML configs and Pydantic models
- **Orchestration**: Experiment manager and phase managers  
- **Agents**: Participant and utility agents
- **Core Systems**: Memory, bank accounts, and distribution generation
- **Infrastructure**: Model providers and data systems

### 2. Experimental Flow (`clean_02_experimental_flow.png`)
**Purpose**: Clear sequential flow showing both experimental phases
- **Phase 1**: Individual learning with principle ranking and application rounds
- **Phase 2**: Group discussion, voting, and consensus building
- **Decision Points**: Vote proposals, consensus detection, round limits
- **Outcomes**: Consensus-based or random payoff assignment

### 3. Agent Architecture (`clean_03_agent_architecture.png`)  
**Purpose**: Core agent processing pipeline and economic integration
- **Agent Core**: Memory management and bank account integration
- **Processing**: Prompt → LLM → Response → Validation pipeline
- **Economic System**: Distribution application and earnings calculation
- **Feedback Loops**: Memory updates influencing future decisions

### 4. Data Flow (`clean_04_data_flow.png`)
**Purpose**: Data collection, processing, and analysis pipeline
- **Sources**: Agent interactions, system events, error events
- **Processing**: Logging, validation, and data structuring
- **Storage**: Experimental data, configurations, and traces
- **Export**: JSON, CSV, and statistical analysis formats

### 5. Bank Account System (`clean_05_bank_account_system.png`)
**Purpose**: Economic incentive mechanism throughout the experiment
- **Phase 1**: Earnings accumulation through principle applications
- **Economic Feedback**: Memory integration influencing future choices
- **Phase 2**: Group economic stakes and consensus incentives
- **Analysis**: Economic behavior pattern analysis

### 6. Consensus Mechanism (`clean_06_consensus_mechanism.png`)
**Purpose**: Group discussion and consensus detection process
- **Discussion Rounds**: Structured speaking order and statement collection
- **Vote Detection**: Proposal identification and agreement checking
- **Consensus Process**: Secret ballot voting and unanimity detection
- **Outcomes**: Successful consensus or fallback to random assignment

## Detailed Implementation Diagrams (For Technical Reference)

The detailed diagrams show implementation-level components and are useful for developers and technical implementers. These include all 7 original diagrams with comprehensive component details.

## Architectural Principles

The MAAI Frohlich Experiment system is built on several key architectural principles:

### 1. **Modular Design**
- Clear separation of concerns between configuration, orchestration, agents, and data layers
- Each component has well-defined responsibilities and interfaces
- Enables independent testing and development of system components

### 2. **Multi-Agent Architecture**
- Distinct participant agents and utility agents with specialized roles
- Support for heterogeneous agent configurations within single experiments
- Sophisticated inter-agent communication and coordination mechanisms

### 3. **Experimental Fidelity**
- Precise replication of original Frohlich & Oppenheimer experimental protocols
- Configurable modes for both historical replication and novel research conditions
- Comprehensive validation systems to ensure experimental integrity

### 4. **Robustness and Error Handling**
- Multi-layered error detection and recovery mechanisms
- Graceful degradation under failure conditions
- Comprehensive logging and monitoring for debugging and analysis

### 5. **Scalability and Performance**
- Parallel processing capabilities for Phase 1 individual interactions
- Efficient resource management and API optimization
- Support for large-scale experimental programs and batch execution

### 6. **Data Integrity and Reproducibility**
- Comprehensive data collection and validation systems
- Complete experimental trace capabilities for reproducibility
- Structured data formats for downstream statistical analysis

## System Components Detail

### Configuration Layer
- **YAML-based configuration**: Flexible experimental parameter specification
- **Pydantic models**: Type-safe configuration validation and data structures
- **Multi-language support**: Localized configurations for cross-cultural research

### Agent Management
- **Participant agents**: Primary experimental subjects with configurable personalities and capabilities
- **Utility agents**: Specialized parsing, validation, and consensus detection functions
- **Memory management**: Persistent, agent-managed memory systems with character limits
- **Bank account systems**: Economic incentive tracking with earnings accumulation

### Experimental Orchestration
- **Phase managers**: Specialized coordinators for Phase 1 and Phase 2 experimental flows
- **Distribution generation**: Dynamic and original values modes for income distribution scenarios
- **Consensus detection**: Multi-tiered consensus determination with exact and semantic matching

### Data and Logging
- **Agent-centric logging**: Comprehensive traces of all agent interactions and decisions
- **Economic tracking**: Detailed earnings, payoffs, and counterfactual analysis
- **Temporal analysis**: Time-series data for preference evolution and group dynamics studies
- **Export capabilities**: JSON, CSV, and statistical software integration

## Usage Notes

### Development and Testing
- Use the architectural diagrams to understand system component relationships
- Reference the error handling diagram when implementing new features
- Follow the data flow architecture for new logging and analysis requirements

### Research Applications
- The bank account system diagram is essential for understanding economic incentive mechanisms
- Phase flow diagrams provide detailed experimental protocol implementation
- Agent interaction diagrams help in designing agent behavior studies

### System Administration
- Overall architecture diagram provides deployment and infrastructure guidance
- Error handling architecture guides monitoring and alerting setup
- Data flow architecture informs backup and data retention policies

## Future Extensions

The modular architecture supports several potential extensions:

- **Strategic behavior analysis**: Game-theoretic capabilities can be added to the agent layer
- **Longitudinal studies**: Extended memory and session management for multi-session experiments
- **Cultural extensions**: Additional language and cultural adaptation modules
- **Advanced analytics**: Machine learning and advanced statistical analysis integration

For technical implementation details, see the main `EXPERIMENTAL_SYSTEM_TECHNICAL_ARCHITECTURE.md` document.