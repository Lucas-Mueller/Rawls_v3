Installation
============

System Requirements
-------------------

* **Python**: 3.11 or higher
* **Operating System**: macOS, Linux, or Windows
* **Memory**: 4GB RAM minimum, 8GB recommended
* **API Keys / Local Endpoints**:

  - OpenAI API key (required for OpenAI models)
  - OpenRouter API key (optional, for 100+ alternative hosted models)
  - GEMINI_API_KEY (optional, for native Google Gemini models)
  - Running Ollama instance (optional, for local models via OpenAI-compatible API)

Environment Setup
-----------------

1. **Clone the Repository**

   .. code-block:: bash

      git clone https://github.com/Lucas-Mueller/Rawls_v3.git
      cd Rawls_v3

2. **Create Virtual Environment**

   .. code-block:: bash

      # Create and activate virtual environment
      python -m venv .venv
      source .venv/bin/activate  # On macOS/Linux
      # OR on Windows:
      .venv\Scripts\activate

3. **Install Dependencies**

   .. code-block:: bash

      pip install -r requirements.txt

Core Dependencies
~~~~~~~~~~~~~~~~~

The system relies on these core packages:

- ``openai-agents[litellm]`` - Multi-agent framework with model provider support
- ``python-dotenv`` - Environment variable management
- ``pydantic`` - Data validation and settings management
- ``PyYAML`` - Configuration file parsing

Analysis Dependencies
~~~~~~~~~~~~~~~~~~~~~

For data analysis and visualization:

- ``pandas`` - Data manipulation and analysis
- ``numpy`` - Numerical computing
- ``matplotlib`` - Basic plotting
- ``seaborn`` - Statistical visualization
- ``scipy`` - Scientific computing
- ``statsmodels`` - Statistical modeling
- ``plotly`` - Interactive visualization

API Key Configuration
---------------------

The system automatically retrieves API keys from your environment. You can set them up in several ways:

Environment Variables (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   export OPENAI_API_KEY="your-openai-key-here"
   export OPENROUTER_API_KEY="your-openrouter-key-here"
   export OLLAMA_BASE_URL="http://localhost:11434/v1"  # Optional, defaults to this value
   export OLLAMA_API_KEY="ollama"                      # Optional sentinel when needed

.env File (Alternative)
~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.env`` file in the project root:

.. code-block:: bash

   OPENAI_API_KEY=your-openai-key-here
   OPENROUTER_API_KEY=your-openrouter-key-here
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_API_KEY=ollama

.. note::
   API key handling follows the same pattern as ``Open_Router_Test.py`` - keys are retrieved using ``os.getenv()`` without strict validation. The system will work with whatever keys are available. For Ollama, ensure ``ollama serve`` is running locally and the desired model has been pulled (e.g., ``ollama pull llama3.2``).

Verification
------------

Test your installation by running the test suite:

.. code-block:: bash

   pytest --mode=dev                          # fast feedback across unit + component
   pytest --mode=ci -m "integration and live" # full multilingual flows with live LLMs
   pytest tests/snapshots                    # snapshot/golden checks
   pytest --mode=ci -m "integration and not live"  # force skip live suites

If ``OPENAI_API_KEY`` is not set, the runner automatically skips suites that require live LLM calls and prints guidance for re-enabling them. Each invocation prints the import smoke test followed by the selected suites.

Quick Test Run
--------------

Verify everything works with a basic experiment:

.. code-block:: bash

   python main.py

This will run the default experiment configuration and should complete successfully if your installation is correct.

To exercise a local Ollama model instead, start the daemon, pull the target model (for example ``ollama pull gemma3:1b``), and launch the provided sample configuration:

.. code-block:: bash

   python main.py config/sample_ollama_gemma3.yaml

Agents referencing ``model: "ollama/<model-name>"`` will automatically use the Ollama OpenAI-compatible endpoint.

Docker Setup (Optional)
------------------------

If you prefer containerized deployment:

.. code-block:: bash

   # Build the container
   docker build -t frohlich-experiment .
   
   # Run with environment variables
   docker run -e OPENAI_API_KEY=your-key frohlich-experiment

Troubleshooting
---------------

Import Errors
~~~~~~~~~~~~~

If you encounter import errors, ensure you're in the correct virtual environment:

.. code-block:: bash

   which python  # Should point to your .venv directory

API Key Issues
~~~~~~~~~~~~~~

- Verify your API keys are correctly set in your environment
- Check that your OpenAI/OpenRouter accounts have sufficient credits
- Ensure there are no extra spaces or quotes in your environment variables

Permission Errors
~~~~~~~~~~~~~~~~~

On some systems, you may need to install packages with user permissions:

.. code-block:: bash

   pip install --user -r requirements.txt

Next Steps
----------

With the system installed, head to the :doc:`quickstart` guide to run your first experiment!
