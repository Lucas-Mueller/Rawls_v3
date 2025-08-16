# Deep Dive: Rawls Execution Flow

This document provides a highly detailed, step-by-step walkthrough of the entire experiment execution process, from the initial command to the final output. It is designed to be read alongside the `execution_flow_diagram.mmd` file, which visually represents this flow.

## Phase 0: Setup & Initialization

This phase is concerned with loading the application, validating its configuration, and preparing all necessary components for the experiment.

1.  **Execution Begins (`main.py`)**: A user executes `python main.py` in the terminal. The Python interpreter starts the `main()` function within the `main.py` script. The first step inside is to set up a basic logging configuration to ensure status messages are printed to the console.

2.  **Configuration Loading**: The script identifies the path to the configuration file, defaulting to `config/default_config.yaml`.

3.  **Pydantic Validation**: The script calls the class method `ExperimentConfiguration.from_yaml(config_path)`. This is a critical validation gateway. Pydantic reads the YAML file and rigorously checks its contents against the schema defined in `config/models.py`. It validates data types (e.g., `phase2_rounds` is an integer), constraints (e.g., `temperature` is between 0 and 2), list requirements (e.g., there are at least 2 agents), and custom rules (e.g., all agent names are unique). If any part of the configuration is invalid, the program terminates immediately with a detailed error. Otherwise, it returns a trusted, type-safe `config` object.

4.  **Manager Instantiation**: An instance of the primary orchestrator, `FrohlichExperimentManager`, is created. The validated `config` object is passed to its constructor. The manager now has all the parameters for the experiment and assigns itself a unique `experiment_id`.

5.  **Asynchronous Initialization (`async_init`)**: The `run_complete_experiment` method is called, which in turn calls `async_init`. This method creates the actual agent objects (`ParticipantAgent`, `UtilityAgent`) and the phase managers (`Phase1Manager`, `Phase2Manager`), providing them with the agents they need to manage.

## Phase 1: Deliberation (Veil of Ignorance)

With all components initialized, the experiment begins. The goal of this phase is for agents to agree on a principle of justice without knowing their future socioeconomic status.

6.  **Delegate to `Phase1Manager`**: The `ExperimentManager` calls `phase1_manager.run_phase1()`.

7.  **The Deliberation Loop**: The `Phase1Manager` orchestrates a multi-round discussion:
    *   **Prompting**: It sends an initial prompt to all `ParticipantAgent`s, explaining the "Veil of Ignorance" and asking them to argue for a principle of justice.
    *   **Agent Reasoning (LLM Call)**: Each agent combines this prompt with its unique personality and sends the request to the configured LLM API (e.g., Gemini).
    *   **Argument Collection**: The manager collects the text-based arguments from all agents.
    *   **Information Sharing**: The manager compiles the arguments and broadcasts them to all agents in the next round, asking them to consider their peers' arguments and potentially offer rebuttals.
    *   **Consensus Check**: In parallel, the `UtilityAgent` (a specialized LLM call) analyzes the discussion transcript to detect if a consensus is forming around a specific principle.
    *   **Repeat**: This loop continues until the `UtilityAgent` reports a consensus or a maximum number of rounds is reached.

8.  **Phase 1 Conclusion**: The `Phase1Manager` concludes its execution and returns the results, most importantly the **agreed-upon principle**, back to the `ExperimentManager`.

## Phase 2: Application & Evaluation

The goal of this phase is to apply the chosen principle to a concrete distribution of resources and measure the agents' satisfaction now that they are aware of their own self-interest.

9.  **Delegate to `Phase2Manager`**: The `ExperimentManager` calls `phase2_manager.run_phase2()`, passing in the chosen principle from Phase 1.

10. **The Veil is Lifted**: The `Phase2Manager` "lifts the veil" by assigning each `ParticipantAgent` a specific socioeconomic status (e.g., "high", "medium", "low" income) based on the probabilities in the configuration file.

11. **The Voting Loop**:
    *   **Distribution Proposal**: The manager calculates a specific distribution of wealth based on the rules of the agreed-upon principle.
    *   **Voting Prompt**: It presents this distribution to all agents, informs each of their personal status within it, and asks them to vote "yes" or "no" on the outcome.
    *   **Agent Voting (LLM Call)**: Each agent, now aware of its self-interest, uses its LLM to formulate a justification for its vote.
    *   **Vote Collection**: The manager collects the votes and justifications. This loop may repeat for several rounds to allow for negotiations or re-distributions.

12. **Phase 2 Conclusion**: The phase ends after a set number of rounds. The `Phase2Manager` returns the detailed results, including the final payoffs for each agent and the history of their votes, to the `ExperimentManager`.

## Phase 4: Logging & Shutdown

13. **Compile Final Results**: The `ExperimentManager` collects the results from both phases and aggregates them into a single, comprehensive `ExperimentResults` object.

14. **Save to File**: The manager calls `agent_logger.save_to_file()`. The `AgentCentricLogger`, which has been accumulating data throughout the process, serializes the final `ExperimentResults` object into a JSON string. This string is written to a timestamped file (e.g., `experiment_results_20250816_103000.json`). This file is the definitive, machine-readable record of the experiment.

15. **Output Summary & Exit**: The manager calls `get_experiment_summary()` to generate a human-readable summary, which it prints to the console. The `main.py` script then finishes, and the program exits.
