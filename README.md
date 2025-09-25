# Frohlich Experiment: An AI Agent Experimentation Framework

This repository contains the source code for the "Frohlich Experiment," a Python-based framework for conducting experiments with AI agents. The project is designed to simulate scenarios involving multiple agents to study their behavior and interactions in a controlled environment.

## Overview

The Frohlich Experiment framework is inspired by the work of economist Norman Frohlich and his experiments on distributive justice. The framework allows researchers to create and run experiments where AI agents, acting as participants, make decisions based on different principles of justice.

The core of the project is the `FrohlichExperimentManager`, which orchestrates the execution of experiments. These experiments are divided into two phases:

*   **Phase 1:** Individual agents are familiarized with the principles of justice.
*   **Phase 2:** Agents engage in a group discussion to reach a consensus on a principle of justice.

The framework is highly configurable, with experiment parameters defined in YAML files. This allows researchers to easily modify experiment conditions and test different scenarios.

## Getting Started

To get started with the Frohlich Experiment framework, please refer to the `CLAUDE.md` file for comprehensive project overview, key components, and detailed instructions on how to run experiments and tests.

## **Intelligent Test Acceleration System**

The framework includes an intelligent test acceleration system that provides ultra-fast feedback for development while maintaining comprehensive validation for releases:

```bash
# ULTRA-FAST DEVELOPMENT WORKFLOWS

# Ultra-fast mode: Unit tests only (~7 seconds, 0 API calls)
python run_tests.py --mode ultra_fast

# Development mode: Unit + component tests (~5 minutes, minimal API calls)
python run_tests.py --mode dev

# CI/CD mode: Comprehensive validation (~15 minutes, moderate API calls)
python run_tests.py --mode ci

# Full mode: Complete validation (~30-45 minutes, all API calls)
python run_tests.py --mode full

# Get help with all available options
python run_tests.py --help
```

### **Performance Improvements Achieved**
- **Ultra-fast mode**: 99.3% improvement (7.6s vs 90-120 minutes)
- **Development workflow**: 95% improvement (5min vs 90-120 minutes)
- **CI/CD pipeline**: 85% improvement (15min vs 90-120 minutes)

### **Legacy Test Execution (Still Supported)**
```bash
python run_tests.py unit component   # fast feedback (unit + component)
python run_tests.py integration      # heavier multilingual flows
python run_tests.py contracts        # snapshot/golden checks
RUN_LIVE_TESTS=0 python run_tests.py integration  # force-skip live suites
```

Set `OPENAI_API_KEY` in your environment (or `.env`) to enable live component/integration runs; without it, the runner skips suites that require LLM access and explains how to re-enable them.

For detailed information about the test acceleration system, see `docs/TEST_ACCELERATION_GUIDE.md`.
