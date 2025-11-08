Development Setup
=================

This guide provides detailed instructions for setting up a development environment for the Frohlich Experiment project.

Prerequisites
-------------

System Requirements
~~~~~~~~~~~~~~~~~~~

- **Python 3.11 or higher**
- **Git** for version control
- **Virtual environment support** (venv, conda, or similar)
- **Text editor or IDE** (VS Code, PyCharm, vim, etc.)

**Recommended Development Environment:**
- VS Code with Python extension
- Terminal with bash/zsh support
- At least 8GB RAM for running experiments
- OpenAI and/or OpenRouter API keys for testing

Initial Setup
-------------

Repository Setup
~~~~~~~~~~~~~~~~

1. **Fork the Repository** (for contributors):
   
   Visit https://github.com/Lucas-Mueller/Rawls_v3 and click "Fork"

2. **Clone Your Fork**:

   .. code-block:: bash

      git clone https://github.com/your-username/Rawls_v3.git
      cd Rawls_v3

3. **Add Upstream Remote**:

   .. code-block:: bash

      git remote add upstream https://github.com/Lucas-Mueller/Rawls_v3.git
      git remote -v  # Verify remotes

Environment Setup
~~~~~~~~~~~~~~~~~

4. **Create Virtual Environment**:

   .. code-block:: bash

      # Using venv (recommended)
      python -m venv .venv
      
      # Activate virtual environment
      source .venv/bin/activate  # macOS/Linux
      .venv\Scripts\activate     # Windows

5. **Upgrade pip**:

   .. code-block:: bash

      pip install --upgrade pip

6. **Install Dependencies**:

   .. code-block:: bash

      pip install -r requirements.txt

API Keys Configuration
~~~~~~~~~~~~~~~~~~~~~~

7. **Set Up API Keys** (choose one method):

   **Option A: Environment Variables**

   .. code-block:: bash

      export OPENAI_API_KEY="your-openai-key"
      export OPENROUTER_API_KEY="your-openrouter-key"

   **Option B: .env File**

   .. code-block:: bash

      # Create .env file in project root
      echo "OPENAI_API_KEY=your-openai-key" >> .env
      echo "OPENROUTER_API_KEY=your-openrouter-key" >> .env

   **Option C: Shell Configuration**

   .. code-block:: bash

      # Add to ~/.bashrc or ~/.zshrc
      echo 'export OPENAI_API_KEY="your-openai-key"' >> ~/.bashrc
      echo 'export OPENROUTER_API_KEY="your-openrouter-key"' >> ~/.bashrc

Verification
~~~~~~~~~~~~

8. **Verify Installation**:

   .. code-block:: bash

      # Run the preset suite
      pytest --mode=ci
      
      # Expected output (truncated):
      # ============================= test session starts ==============================
      # collected 420 items
      #
      # tests/unit/test_*.py ............
      # tests/component/test_*.py sssssss
      # ...
      # ========================= 410 passed, 10 skipped in 900.00s ====================

9. **Test Basic Functionality**:

   .. code-block:: bash

      # Quick system test (optional - uses API calls)
      python main.py config/default_config.yaml

Development Tools
-----------------

Recommended IDE Setup
~~~~~~~~~~~~~~~~~~~~~

**VS Code Configuration:**

.. code-block:: json

   // .vscode/settings.json
   {
       "python.defaultInterpreterPath": "./.venv/bin/python",
       "python.testing.pytestEnabled": false,
       "python.testing.unittestEnabled": true,
       "python.testing.unittestArgs": [
           "-v",
           "-s",
           "./tests",
           "-p",
           "test_*.py"
       ],
       "python.linting.enabled": true,
       "python.linting.flake8Enabled": true,
       "python.formatting.provider": "black",
       "editor.formatOnSave": true,
       "files.exclude": {
           "**/__pycache__": true,
           "**/.pytest_cache": true,
           ".venv": true
       }
   }

**PyCharm Configuration:**
- Set Python interpreter to `.venv/bin/python`
- Enable pytest or unittest for testing
- Configure code style to follow PEP 8
- Set up version control integration

Code Quality Tools
~~~~~~~~~~~~~~~~~~

**Install Development Tools** (optional):

.. code-block:: bash

   # Code formatting
   pip install black isort

   # Linting
   pip install flake8 pylint

   # Type checking
   pip install mypy

**Usage Examples:**

.. code-block:: bash

   # Format code
   black your_file.py
   
   # Sort imports
   isort your_file.py
   
   # Lint code
   flake8 your_file.py
   
   # Type checking
   mypy your_file.py

Git Configuration
~~~~~~~~~~~~~~~~~

**Configure Git** (first time setup):

.. code-block:: bash

   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"

**Pre-commit Hooks** (if available):

.. code-block:: bash

   # Install pre-commit if hooks are configured
   pip install pre-commit
   pre-commit install

Development Workflow
--------------------

Daily Development
~~~~~~~~~~~~~~~~~~

1. **Sync with Upstream**:

   .. code-block:: bash

      git fetch upstream
      git checkout main
      git merge upstream/main

2. **Create Feature Branch**:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

3. **Make Changes and Test**:

   .. code-block:: bash

      # Edit code
      # Run tests frequently
      pytest --mode=dev
     
      # Test specific modules
      python -m unittest tests.unit.test_your_module -v

4. **Commit Changes**:

   .. code-block:: bash

      git add .
      git commit -m "Add feature: brief description of changes"

5. **Push and Create PR**:

   .. code-block:: bash

      git push origin feature/your-feature-name
      # Create PR via GitHub interface

Running Tests
~~~~~~~~~~~~~

**Fast Feedback Suite (default)**:

.. code-block:: bash

   pytest --mode=dev

**Specific Test Categories**:

.. code-block:: bash

   # Unit-only logic
   pytest --mode=ultra_fast

   # Component + live multilingual flows
   pytest tests/component -m "component and live"
   pytest tests/integration -m "integration and live"

   # Contract/golden artefact checks
   pytest tests/snapshots/contracts

   # Enable live suites explicitly (override environment defaults)
   pytest --run-live --languages=en,es

   # Skip live suites even when credentials are present
   pytest tests/integration -m "integration and live" --no-run-live

Set ``OPENAI_API_KEY`` (and optionally ``OPENROUTER_API_KEY``) in your environment or ``.env`` file to enable live runs; without them the runner will automatically skip suites that call real LLMs and explain how to re-enable coverage.

**Individual Test Files**:

.. code-block:: bash

   # Specific test file
   python -m unittest tests.unit.test_memory_manager -v
   
   # Specific test method
   python -m unittest tests.unit.test_memory_manager.TestMemoryManager.test_memory_validation -v

**Testing with Different Configurations**:

.. code-block:: bash

   # Test with different models (requires API keys)
   python main.py config/spanish_config.yaml
   python main.py config/mixed_models_example.yaml

Documentation Development
-------------------------

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

**Install Documentation Dependencies** (if not already installed):

.. code-block:: bash

   pip install sphinx furo sphinx-rtd-theme

**Build Documentation Locally**:

.. code-block:: bash

   cd docs
   make html
   
   # View in browser
   open _build/html/index.html  # macOS
   xdg-open _build/html/index.html  # Linux
   start _build/html/index.html  # Windows

**Clean and Rebuild**:

.. code-block:: bash

   cd docs
   make clean
   make html

Writing Documentation
~~~~~~~~~~~~~~~~~~~~~

**Documentation Structure**:

.. code-block:: text

   docs/
   ├── getting-started/     # New user guides
   ├── user-guide/          # Detailed usage instructions
   ├── architecture/        # System design and concepts
   ├── api/                 # Auto-generated API docs
   └── contributing/        # Development and contribution guides

**Adding New Documentation**:

1. Create new `.rst` files in appropriate directories
2. Add references to `index.rst` toctrees
3. Build and verify documentation
4. Include in pull requests

Debugging and Troubleshooting
-----------------------------

Common Development Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Import Errors**:

.. code-block:: text

   ModuleNotFoundError: No module named 'experiment_agents'
   
   Solution: Ensure you're in the project root and virtual environment is activated

**API Key Issues**:

.. code-block:: text

   Error: API key not configured
   
   Solution: Set environment variables or check .env file

**Test Failures**:

.. code-block:: text

   Tests failing due to API rate limits
   
   Solution: Pause live suites by exporting ``NEW_ENV_PLACEHOLDER`` or rerun once the limit resets. The runner reports which language/layer was skipped so you can resume coverage later.

Debugging Tools
~~~~~~~~~~~~~~~

**Python Debugger**:

.. code-block:: python

   # Add to code for debugging
   import pdb; pdb.set_trace()

**Logging Configuration**:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)

**VS Code Debugging**:

.. code-block:: json

   // .vscode/launch.json
   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "Run Experiment",
               "type": "python",
               "request": "launch",
               "program": "main.py",
               "args": ["config/default_config.yaml"],
               "console": "integratedTerminal"
           },
           {
               "name": "Run Tests",
               "type": "python",
               "request": "launch",
               "module": "pytest",
               "args": ["--mode=dev"],
               "console": "integratedTerminal"
           }
       ]
   }

Performance Optimization
-----------------------

Development Performance
~~~~~~~~~~~~~~~~~~~~~~

**Faster Testing**:

.. code-block:: bash

   # Run subset of tests during development
   pytest tests/unit -v
   
   # Skip slow integration tests
   pytest --mode=ultra_fast

**Memory Usage**:

.. code-block:: yaml

   # Use smaller memory limits during development
   agents:
     - memory_character_limit: 10000  # Reduced from 50000

**Reduced Experiment Times**:

.. code-block:: yaml

   # Shorter experiments for testing
   phase2_rounds: 2  # Reduced from 10

Docker Development
------------------

Container-Based Development
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Dockerfile for Development**:

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["pytest", "--mode=ci"]

**Docker Compose for Development**:

.. code-block:: yaml

   # docker-compose.dev.yml
   version: '3.8'
   services:
     frohlich-dev:
       build: .
       volumes:
         - .:/app
         - /app/.venv  # Exclude venv from mount
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
         - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
       command: pytest --mode=ci

**Running in Docker**:

.. code-block:: bash

   # Build development container
   docker-compose -f docker-compose.dev.yml build
   
   # Run tests in container
   docker-compose -f docker-compose.dev.yml run frohlich-dev
   
   # Interactive development
   docker-compose -f docker-compose.dev.yml run frohlich-dev bash

Next Steps
----------

After Setup
~~~~~~~~~~~

1. **Explore the Codebase**: Start with :doc:`../architecture/system-overview`
2. **Run Example Experiments**: Try different configurations in `config/`
3. **Read Research Documentation**: Understand the philosophical background
4. **Join Discussions**: Participate in GitHub discussions about research directions
5. **Identify Contribution Areas**: Look at open issues or propose new research questions

**Getting Help:**
- Check :doc:`../getting-started/quickstart` for basic usage
- Review :doc:`testing` for testing procedures
- Open GitHub discussions for questions
- Read existing issues for known problems and solutions

You're now ready to contribute to the Frohlich Experiment project! Whether you're interested in code improvements, research contributions, or documentation enhancements, your work will help advance our understanding of AI ethics and distributive justice.
