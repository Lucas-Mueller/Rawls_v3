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
pytest --mode=ultra_fast

# Development mode: Unit + component tests (~5 minutes, minimal API calls)
pytest --mode=dev

# CI/CD mode: Comprehensive validation (~15 minutes, moderate API calls)
pytest --mode=ci

# Full mode: Complete validation (~30-45 minutes, all API calls)
pytest --mode=full
```

### **Performance Improvements Achieved**
- **Ultra-fast mode**: 99.3% improvement (7.6s vs 90-120 minutes)
- **Development workflow**: 95% improvement (5min vs 90-120 minutes)
- **CI/CD pipeline**: 85% improvement (15min vs 90-120 minutes)

### **Targeted Test Execution**
```bash
pytest tests/unit/test_fast_*         # deterministic fast feedback
pytest tests/component -m "component and not live"  # offline component coverage
pytest tests/integration -m "integration and live"  # integration suite (requires API keys)
pytest tests/snapshots                # contract/golden checks (post-migration location)
pytest --run-live --languages=en,es   # live coverage limited to English and Spanish
pytest --skip-expensive               # skip tests marked as expensive regardless of mode
```

Set `OPENAI_API_KEY` in your environment (or `.env`) to enable live component/integration runs; without it, the runner skips suites that require LLM access and explains how to re-enable them.

For detailed information about the test acceleration system, see `docs/TEST_ACCELERATION_GUIDE.md`.

## Using Local Ollama Models

Ollama’s OpenAI-compatible endpoint is now supported via the `ollama/<model>` prefix. To try it out:

1. Ensure the daemon is running and pull the target model:
   ```bash
   ollama serve &
   ollama pull gemma3:1b
   ```
2. Optionally export overrides (defaults shown):
   ```bash
   export OLLAMA_BASE_URL="http://localhost:11434/v1"
   export OLLAMA_API_KEY="ollama"
   ```
3. Run the sample configuration:
   ```bash
   python main.py config/sample_ollama_gemma3.yaml
   ```

All agents configured with `model: "ollama/gemma3:1b"` will now route through the local endpoint using the standard Agents SDK pipeline (streaming, structured output, tracing, etc.).
