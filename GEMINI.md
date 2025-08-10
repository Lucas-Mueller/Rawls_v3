# Rawls: An AI Agent Experimentation Framework

## Project Overview

This project, "Rawls," is a Python-based framework for conducting experiments with AI agents. It is designed to simulate scenarios involving multiple agents to study their behavior and interactions in a controlled environment. The framework is named after the philosopher John Rawls, and its name, combined with the "Veil of Ignorance" concept, suggests a focus on fairness, social welfare, and ethical considerations in AI systems.

The core of the project is an `ExperimentManager` that orchestrates the execution of experiments. These experiments are divided into two phases, each managed by a dedicated manager (`Phase1Manager` and `Phase2Manager`). The framework uses a configuration-driven approach, with experiment parameters defined in YAML files.

## Background

The project is inspired by John Rawls's "Veil of Ignorance" thought experiment. In this experiment, individuals are asked to choose principles of justice from behind a "veil of ignorance," where they do not know their own social status, class, or natural abilities. This is to ensure that the chosen principles are fair and just for all members of society.

This framework aims to apply this concept to the development of AI agents. By simulating a "Veil of Ignorance" scenario, the framework can be used to study how AI agents would behave and interact if they were designed to be fair and just.

## Key Components

- **`main.py`**: The entry point for running experiments. It loads the configuration, initializes the necessary components, and starts the experiment.
- **`config/`**: This directory contains the configuration for the experiments.
  - `default_config.yaml`: The default configuration file. It defines the experiment parameters, including the number of agents, the resources, and the principles to be used.
  - `models.py`: Defines the data models for the configuration files.
- **`core/`**: This directory contains the core logic of the framework.
  - `experiment_manager.py`: The main class that manages the execution of experiments.
  - `phase1_manager.py`: Manages the first phase of the experiment, where agents deliberate and choose a principle of justice.
  - `phase2_manager.py`: Manages the second phase of the experiment, where the chosen principle is applied and the results are evaluated.
  - `distribution_generator.py`: Generates the distribution of resources for the experiment.
- **`experiment_agents/`**: This directory contains the AI agents that participate in the experiments.
  - `participant_agent.py`: An agent that participates in the experiment, representing an individual in the "original position."
  - `utility_agent.py`: An agent that has a utility-related role in the experiment, likely to evaluate the outcomes of the chosen principles.
- **`models/`**: This directory contains the data models for the project.
  - `experiment_types.py`: Defines the different types of experiments that can be run.
  - `principle_types.py`: Defines the different types of principles that can be used in the experiments.
  - `response_types.py`: Defines the structure of the responses from the agents.
- **`utils/`**: This directory contains utility functions.
  - `logging_utils.py`: Provides logging functionality.
  - `memory_manager.py`: Manages memory usage.
- **`tests/`**: This directory contains the tests for the project.
  - `unit/`: Contains unit tests for the individual components of the framework.
  - `integration/`: Contains integration tests that test the interactions between the different components.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- The dependencies listed in `requirements.txt`

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/Rawls.git
    ```
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Project

To run the project, you need to have Python installed. You can then run the `main.py` script from the command line:

```bash
python main.py
```

This will run the experiment with the default configuration. You can also specify a custom configuration file using the `--config` argument:

```bash
python main.py --config /path/to/your/config.yaml
```

### Running Tests

To run the tests, you can use the `run_tests.py` script:

```bash
python run_tests.py [test_type]
```

The `test_type` argument can be one of the following:

- `unit`: Runs the unit tests.
- `integration`: Runs the integration tests.
- `all`: Runs all tests (default).

## How to Use the Codebase

This codebase provides a flexible framework for conducting experiments with AI agents. Here's how you can use it:

1.  **Define your experiment in a YAML file.** You can use the `default_config.yaml` file as a template. In this file, you can specify the number of agents, the resources, and the principles to be used in the experiment.
2.  **Implement your own AI agents.** You can create your own agents by inheriting from the `BaseAgent` class and implementing the `act()` method.
3.  **Run the experiment.** You can run the experiment by running the `main.py` script.
4.  **Analyze the results.** The results of the experiment will be saved to a file. You can then analyze the results to study the behavior of the agents and the effectiveness of the principles.

## Research Applications

This framework can be used to study a wide range of topics, including:

-   Fairness in AI systems
-   Social welfare in multi-agent systems
-   The emergence of cooperation and competition among AI agents
-   The impact of different ethical principles on the behavior of AI agents

By providing a flexible and extensible framework for conducting experiments with AI agents, this project can help to advance our understanding of these important topics.
