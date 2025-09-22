Installation
============

System Requirements
-------------------

* **Python**: 3.11 or higher
* **Operating System**: macOS, Linux, or Windows
* **Memory**: 4GB RAM minimum, 8GB recommended
* **API Keys**: 
  
  - OpenAI API key (required for OpenAI models)
  - OpenRouter API key (optional, for alternative model providers)

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

.env File (Alternative)
~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.env`` file in the project root:

.. code-block:: bash

   OPENAI_API_KEY=your-openai-key-here
   OPENROUTER_API_KEY=your-openrouter-key-here

.. note::
   API key handling follows the same pattern as ``Open_Router_Test.py`` - keys are retrieved using ``os.getenv()`` without strict validation. The system will work with whatever keys are available.

Verification
------------

Test your installation by running the test suite:

.. code-block:: bash

   python run_tests.py            # full suite
   python run_tests.py unit       # unit tests only
   python run_tests.py regression # deterministic regression checks

Each invocation prints the import smoke test followed by the selected suites.

Quick Test Run
--------------

Verify everything works with a basic experiment:

.. code-block:: bash

   python main.py

This will run the default experiment configuration and should complete successfully if your installation is correct.

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
