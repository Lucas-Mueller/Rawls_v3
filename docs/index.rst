Frohlich Experiment Documentation
=================================

Welcome to the **Frohlich Experiment** - a multi-agent AI system implementing an experiment to simulate how AI agents interact with principles of justice and income distribution. This system is based on the OpenAI Agents SDK and implements a two-phase experimental design exploring how artificial agents navigate concepts from John Rawls' theory of justice.

.. note::
   The Frohlich Experiment is named after Norman Frohlich, a political scientist known for his empirical work on distributive justice and experimental testing of theories of social choice.

Quick Links
-----------

* :doc:`getting-started/installation` - Get up and running in minutes
* :doc:`user-guide/running-experiments` - Learn to conduct experiments
* :doc:`architecture/system-overview` - Understand the system design
* :doc:`api/index` - Explore the API reference

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   getting-started/introduction
   getting-started/installation
   getting-started/quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide & Tutorials
   :hidden:

   user-guide/running-experiments
   user-guide/designing-experiments
   user-guide/custom-agents
   user-guide/analyzing-results

.. toctree::
   :maxdepth: 2
   :caption: Hypothesis Testing
   :hidden:

   hypothesis-testing

.. toctree::
   :maxdepth: 2
   :caption: Architecture & Core Concepts
   :hidden:

   architecture/system-overview
   architecture/services-architecture
   cultural-adaptation
   phase2-settings
   error-handling
   architecture/veil-of-ignorance
   architecture/configuration
   architecture/experiment-flow
   architecture/logging-data

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:

   api/index
   api/core
   api/agents
   api/models
   api/utils

.. toctree::
   :maxdepth: 2
   :caption: Contributing
   :hidden:

   contributing/guidelines
   contributing/development-setup
   contributing/testing

Features
--------

* **Two-Phase Experiment Design**: Individual agent familiarization followed by group discussion
* **Multi-Agent Architecture**: Configurable participant agents with specialized utility agents
* **Justice Principles**: Implementation of four key distributive justice principles
* **Multi-Language Support**: Full experimental support for English, Spanish, and Mandarin
* **Agent-Managed Memory**: Agents create and manage their own memory throughout experiments
* **Comprehensive Tracing**: Built-in OpenAI SDK tracing for debugging and analysis
* **Structured Summaries**: Automatic JSON summaries to complement detailed agent logs
* **Configurable Parameters**: YAML-based configuration for all experimental settings
* **Error Recovery**: Robust error handling with automatic retry mechanisms

System Requirements
-------------------

* Python 3.11+
* OpenAI API key (for OpenAI models)
* OpenRouter API key (for alternative model providers, optional)

License
-------

This project is released under the MIT License. See the LICENSE file for details.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
