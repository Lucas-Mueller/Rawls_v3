# Frohlich Experiment: An AI Agent Experimentation Framework

This repository contains the source code for the "Frohlich Experiment," a Python-based framework for conducting experiments with AI agents. The project is designed to simulate scenarios involving multiple agents to study their behavior and interactions in a controlled environment.

## Overview

The Frohlich Experiment framework is inspired by the work of economist Norman Frohlich and his experiments on distributive justice. The framework allows researchers to create and run experiments where AI agents, acting as participants, make decisions based on different principles of justice.

The core of the project is the `FrohlichExperimentManager`, which orchestrates the execution of experiments. These experiments are divided into two phases:

*   **Phase 1:** Individual agents are familiarized with the principles of justice.
*   **Phase 2:** Agents engage in a group discussion to reach a consensus on a principle of justice.

The framework is highly configurable, with experiment parameters defined in YAML files. This allows researchers to easily modify experiment conditions and test different scenarios.

## Getting Started

To get started with the Frohlich Experiment framework, please refer to the `GEMINI.md` file for a detailed project overview, key components, and instructions on how to run experiments and tests. The bundled `run_tests.py` script now supports layered selections and live toggles:

```
python run_tests.py unit component   # fast feedback (unit + component)
python run_tests.py integration      # heavier multilingual flows
python run_tests.py contracts        # snapshot/golden checks
RUN_LIVE_TESTS=0 python run_tests.py integration  # force-skip live suites
```

Set `OPENAI_API_KEY` in your environment (or `.env`) to enable live component/integration runs; without it, the runner skips suites that require LLM access and explains how to re-enable them.
