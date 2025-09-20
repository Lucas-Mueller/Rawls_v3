# Frohlich Experiment Target Architecture

## 1. Design Philosophy – What I Would Do Differently
### 1.1 Domain-First Modelling
- Treat justice principles, distributions, and voting mechanics as pure domain modules with no IO or SDK dependencies.
- Encode business rules as deterministic functions and state machines, letting application services orchestrate them; this keeps prompts and agents replaceable.

### 1.2 Configuration as Contracts
- Version configuration files, validate them at startup, and generate migration guides automatically.
- Split settings into explicit namespaces (`experiment`, `phases`, `memory`, `logging`, `observability`, `agents`) to avoid monolithic models.

### 1.3 Pipeline Declaration Over Imperative Flows
- Describe experiment phases declaratively (YAML/JSON) so the runtime reads a “stage plan” rather than hard-coded loops.
- Allow new phases (e.g., surveys, debriefs) without editing orchestration code—just add stage definitions and handler classes.

### 1.4 Interface-Oriented Agents
- Define an `AgentGateway` protocol capturing required behaviours (`generate_statement`, `update_memory`, `cast_vote`).
- Provide concrete adapters for OpenAI Agents, replay logs, scripted mocks, and future providers; swap implementations via DI.

### 1.5 Observability by Design
- Emit structured events (`phase_started`, `agent_step`, `vote_called`) into a central event bus with consistent schemas.
- Generate human-readable logs and markdown reports from the same event stream, eliminating duplicated logging pathways.

### 1.6 Testability & Determinism
- Mock agent gateways in unit tests, use scenario fixtures for domain logic, and introduce contract tests that run on deterministically seeded transcripts.
- Reserve live LLM tests for scheduled builds; day-to-day CI should succeed offline.

### 1.7 Packaging & Deployment Discipline
- Package the project with `pyproject.toml`, publish CLI entry points (`frohlich run`, `frohlich test`), and provide Docker/uv environments.
- Document environment parity expectations, reproducible seeds, and caching of translation assets.

## 2. Target Architecture Overview

```
┌──────────────────────────────────────────┐
│              Interface Layer             │
│  - CLI (Typer)                           │
│  - Future REST/gRPC adapters             │
└───────────────▲──────────────────────────┘
                │ orchestrates use-cases
┌───────────────┴──────────────────────────┐
│            Application Layer             │
│  - ExperimentService                     │
│  - PhasePipelineEngine                   │
│  - StageHandlers (Phase1, Phase2, …)     │
└───────────────▲───────────┬─────────────┘
                │ invokes   │ depends on
┌───────────────┴──────┐ ┌──┴────────────────────────┐
│      Domain Layer     │ │      Infrastructure        │
│  - Principles module  │ │  - AgentGateway impls      │
│  - Voting FSM         │ │  - Persistence adapters    │
│  - Memory logic       │ │  - LanguageProvider impls  │
│  - Result DTOs        │ │  - Logging/Event sinks     │
└───────────────┬───────┘ └───────────────────────────┘
                │ pure data/logic
┌───────────────▼──────────────────────────┐
│          Cross-Cutting Concerns          │
│  - Config Registry & Validation          │
│  - Observability Event Bus               │
│  - Dependency Injection Container        │
└──────────────────────────────────────────┘
```

## 3. Component Responsibilities
### 3.1 Interface Layer (`frohlich.cli`, `frohlich.http`)
- Parse CLI arguments, load config, bootstrap DI container, and call `ExperimentService.run_experiment`.
- Future APIs expose experiment lifecycle endpoints for dashboards or automation.

### 3.2 Application Layer (`frohlich.app`)
- **ExperimentService**: Validates configs, builds the phase pipeline, coordinates persistence, and emits top-level events.
- **PhasePipelineEngine**: Executes ordered `Stage` definitions (phase1_familiarization, phase2_discussion, etc.) with lifecycle hooks (`before_stage`, `after_stage`, failure policies).
- **StageHandlers**: Each stage encapsulates workflow logic; they request domain operations and talk to infrastructure interfaces (agents, logging).
- **ScenarioRegistry**: Maps configuration stage names to handler classes so new stages plug in declaratively.

### 3.3 Domain Layer (`frohlich.domain`)
- **Principles**: Defines value objects for justice principles, calculators for distributions, and ranking utilities.
- **Voting**: Finite-state machine covering proposal, confirmation, ballots, and consensus resolution; returns events describing transitions.
- **Memory**: Stateless functions producing memory update prompts and summarizations given participant context.
- **DTOs & Aggregates**: `PhaseResults`, `ExperimentResults`, `AgentTranscript`, kept framework-agnostic and serializable.

### 3.4 Infrastructure Layer (`frohlich.infra`)
- **AgentGateway Implementations**: Concrete adapters for OpenAI Agents, offline scripted agents, and recorded transcripts.
- **LanguageProvider**: Loads translations, caches them, offers safe fallbacks; optionally supports remote translation services.
- **Persistence Adapters**: Writers/readers for JSON, parquet, or database storage; include repository interfaces for results/history.
- **Observability**: Event dispatcher to console, JSONL, OTLP exporter; structured logging formatters share schema.
- **Configuration Loader**: Validates YAML against versioned schema, applies migrations, instantiates typed config objects.

### 3.5 Cross-Cutting Concerns
- **Dependency Injection**: Provide a simple container (e.g., `punq` or handmade) that wires gateways, services, and configuration.
- **Event Bus**: A synchronous or async publisher that StageHandlers use to emit events; sinks subscribe to transform into logs, metrics, or reports.
- **Policy Engine**: Central place for retry/timeouts/backoff strategies shared across stage handlers and gateways.

## 4. Package Layout Proposal
| Package | Purpose |
| --- | --- |
| `frohlich.cli` | Typer/Click commands (`run`, `validate`, `report`). |
| `frohlich.app` | Application services, phase pipeline engine, scenario registry. |
| `frohlich.domain` | Pure domain logic for principles, voting FSM, memory calculations, DTOs. |
| `frohlich.infra.agents` | Agent gateway adapters, mocks, capability caches. |
| `frohlich.infra.localization` | Language/translation loading, formatting helpers. |
| `frohlich.infra.persistence` | Result repositories (JSON/SQL/parquet). |
| `frohlich.infra.observability` | Event bus, structured logging, tracing exporters. |
| `frohlich.config` | Schemas, migrations, environment resolution, config registry. |
| `frohlich.tests` | Test utilities, fixtures, contract tests. |

## 5. Experiment Stage Definition Example
```yaml
experiment:
  id: "baseline-justice"
  phases:
    - name: phase1_familiarization
      handler: familiarization_stage
      strategy:
        application_rounds: 4
        distribution_mode: original_values
    - name: phase2_discussion
      handler: deliberation_stage
      strategy:
        voting: two_stage_secret_ballot
        max_rounds: 10
    - name: debrief_survey
      handler: survey_stage
      optional: true
logging:
  level: info
  event_stream: jsonl
observability:
  exporters:
    - type: console
    - type: otlp
agents:
  provider: openai_agents
  participants:
    - id: "alice"  # references roster file
  utility:
    model: "gpt-4.1-mini"
```

The runtime reads this plan, resolves `handler` names through the ScenarioRegistry, and executes each stage with matching strategy parameters.

## 6. Data & Event Flow
1. **Config bootstrap** – Load YAML ➜ validate ➜ instantiate typed config objects ➜ seed PhasePipelineEngine.
2. **Stage execution** – For each stage, handler requests domain computations (e.g., `principles::rank`), then calls `AgentGateway` for language model interactions.
3. **Event emission** – Domain and application layers emit events (`AgentStatement`, `VoteInitiated`) onto the bus; observability sinks serialize them.
4. **Persistence** – After each stage, results aggregator assembles partial DTOs and writes snapshots; final results exported to configured repositories.
5. **Reporting** – Post-run commands consume event logs/DTOs to produce markdown, dashboards, or analytics.

## 7. Migration Strategy Outline
1. **Introduce Domain Module**: Extract principle and distribution logic into `frohlich.domain` while leaving existing orchestrators intact.
2. **Implement AgentGateway Interface**: Wrap current OpenAI interactions; update Phase managers to use the interface.
3. **Adopt Event Bus**: Replace direct logger calls with event emissions, initially forwarding to the existing loggers.
4. **Stage Pipeline Pilot**: Re-implement Phase 1 using `PhasePipelineEngine`; run in parallel with legacy flow behind feature flag.
5. **Config Migration**: Release schema v2 with migration CLI; update docs and default configs.
6. **Package & CLI**: Move modules into new package layout, add `pyproject.toml`, publish CLI adapters.
7. **Deprecate Legacy Managers**: Once stages cover all behaviours, retire `core/phase*_manager.py` in favour of StageHandlers.

## 8. Expected Benefits
- **Maintainability**: Clear boundaries reduce regression risk and enable team specialization.
- **Extensibility**: Adding new phases or agent providers becomes configuration + handler implementation rather than invasive refactors.
- **Testability**: Domain logic is pure, easily unit-tested; application layer can be simulated with mocked gateways.
- **Observability**: Single source of truth for experiment events supports dashboards, analytics, and replay.
- **Reproducibility**: Versioned configs and deterministic pipelines make experiments auditable and repeatable.

## 9. Next Steps for Adoption
1. Create RFC documenting proposed packages and naming conventions; gather team feedback.
2. Prototype `PhasePipelineEngine` with one stage to validate ergonomics.
3. Define event schemas and align stakeholders (analytics, research) on required telemetry.
4. Plan dual-run period where legacy and new pipelines produce comparable outputs to ensure parity.
5. Schedule incremental refactors aligned with roadmap priorities (config, observability, testing).
