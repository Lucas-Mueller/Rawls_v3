Experiment Flow
===============

This page outlines the sequence of operations executed when you run ``python main.py`` so contributors can map code modules to stages.

High-Level Timeline
-------------------

1. **Bootstrap**
   - ``main.py`` loads the requested YAML configuration and environment variables.
   - ``ExperimentConfiguration.from_yaml`` validates top-level keys and agent definitions.
   - ``create_process_logger`` initialises console output according to the config's logging section.

2. **Language & Manager Setup**
   - ``create_language_manager`` instantiates the translation layer and sets the configured language.
   - ``FrohlichExperimentManager`` is created with the config, language manager, and config path for later reporting.

3. **Initialisation (``async_init``)**
   - Participant agents are created via ``experiment_agents.participant_agent`` with dynamic temperature detection.
   - The utility agent is initialised for response parsing and validation.
   - Phase managers (Phase 1 / Phase 2) receive shared dependencies such as the error handler, seed manager, and language manager.

4. **Seed & Trace**
   - ``SeedManager`` derives or sets the experiment seed; the value is reported in the console and logged.
   - An OpenAI trace span is opened (unless tracing is disabled) and the trace ID is captured for later display.

5. **Phase 1 – Familiarisation**
   - Runs in parallel using ``asyncio.gather`` inside ``Phase1Manager``.
   - Each agent ranks principles, reviews explanations, and applies principles across four rounds.
   - Memory updates funnel through ``utils.memory_manager.MemoryManager`` and the utility agent validates structured outputs.

6. **Phase 2 – Discussion & Voting**
   - Executed sequentially by ``Phase2Manager`` to preserve conversation order.
   - Services for speaking order, discussion prompts, voting, counterfactuals, and memory updates are initialised on demand.
   - The manager coordinates discussion rounds, optional votes, payoff computation, and final memory consolidation.

7. **Results Assembly**
   - ``ExperimentResults`` aggregates Phase 1 and Phase 2 records.
   - ``AgentCentricLogger`` captures per-agent journeys, voting history, and general experiment metadata.

8. **Persistence & Reporting**
   - ``FrohlichExperimentManager.save_results`` writes the agent-centric log to ``experiment_results_<timestamp>.json``.
   - Console output lists the file location and, when applicable, the OpenAI trace URL.

Cross-Referencing Modules
-------------------------

===========================  ==========================================
Stage                        Primary Modules / Files
===========================  ==========================================
Bootstrap                    ``main.py``
Configuration Validation     ``config/models.py``
Agent Construction           ``experiment_agents/participant_agent.py``
Phase 1 Execution            ``core/phase1_manager.py``
Phase 2 Execution            ``core/phase2_manager.py`` + ``core/services``
Seed Management              ``utils/seed_manager.py``
Memory Helpers               ``utils/memory_manager.py``
Logging                      ``utils/logging/agent_centric_logger.py``
Summary Generation           ``utils/logging/result_summary.py``
===========================  ==========================================

Tips for Contributors
---------------------

- To instrument a new metric, decide whether it belongs in the detailed agent log or the summary and update the respective helper.
- Keep stage-specific prompts or logic inside the relevant phase manager or service to maintain separation of concerns.
- When adding new configuration flags, update both ``config/models.py`` and ``docs/configuration.md`` so the validation and documentation stay aligned.
