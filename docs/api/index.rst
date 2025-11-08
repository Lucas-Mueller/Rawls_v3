API Reference
=============

This section provides detailed documentation for all public classes, functions, and modules in the Frohlich Experiment system.

.. toctree::
   :maxdepth: 2

   core
   agents  
   models
   utils

Overview
--------

The Frohlich Experiment API is organized into four main modules:

Core Modules
~~~~~~~~~~~~

- :doc:`core` - Experiment orchestration and phase management
- :doc:`agents` - Participant and utility agent implementations  
- :doc:`models` - Data structures and configuration classes
- :doc:`utils` - Supporting utilities and helper functions

Usage Pattern
~~~~~~~~~~~~~

The typical API usage pattern follows this structure:

.. code-block:: python

   from config.models import ExperimentConfiguration
   from core.experiment_manager import FrohlichExperimentManager
   
   # Load configuration
   config = ExperimentConfiguration.from_yaml("config.yaml")
   
   # Initialize and run experiment  
   manager = FrohlichExperimentManager(config)
   results = await manager.run_complete_experiment()
   
   # Access results
   print(f"Consensus reached: {results.phase2_results.consensus_reached}")

Auto-Generated Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All API documentation is automatically generated from docstrings in the source code using Sphinx's autodoc extension. This ensures the documentation stays synchronized with the codebase.