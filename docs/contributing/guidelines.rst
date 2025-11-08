Contribution Guidelines
=======================

Welcome to the Frohlich Experiment project! We're excited to have you contribute to this research into AI ethics and distributive justice. This guide will help you make meaningful contributions to the project.

Getting Started
---------------

Before Contributing
~~~~~~~~~~~~~~~~~~~

1. **Read the Documentation**: Familiarize yourself with the project by reading the :doc:`../getting-started/introduction` and :doc:`../architecture/system-overview`.

2. **Understand the Research Goals**: This project explores how AI agents reason about distributive justice and fairness. Contributions should align with these research objectives.

3. **Review Existing Issues**: Check the `GitHub Issues <https://github.com/Lucas-Mueller/Rawls_v3/issues>`_ for existing bugs, feature requests, or research questions.

4. **Join Discussions**: Participate in discussions about the project's direction and research priorities.

Types of Contributions
~~~~~~~~~~~~~~~~~~~~~~

**Code Contributions:**
- Bug fixes and improvements
- New experimental features
- Performance optimizations
- Test coverage improvements
- Documentation enhancements

**Research Contributions:**
- Novel experimental configurations
- Analysis methodologies and tools
- Theoretical insights and interpretations
- Cross-cultural or multi-language extensions
- Validation studies and replications

**Documentation Contributions:**
- Tutorial improvements
- Example code and configurations
- API documentation enhancements
- Research methodology documentation
- Troubleshooting guides

Development Workflow
--------------------

Setting Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Fork and Clone the Repository**:

   .. code-block:: bash

      git clone https://github.com/your-username/Rawls_v3.git
      cd Rawls_v3

2. **Create Development Environment**:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate  # On macOS/Linux
      # .venv\Scripts\activate   # On Windows

3. **Install Development Dependencies**:

   .. code-block:: bash

      pip install -r requirements.txt
      pip install -r requirements-dev.txt  # If available

4. **Verify Installation**:

   .. code-block:: bash

      pytest --mode=ci

5. **Set Up Pre-commit Hooks** (if configured):

   .. code-block:: bash

      pre-commit install

Branch Management
~~~~~~~~~~~~~~~~

**Branch Naming Conventions:**

.. code-block:: text

   feature/short-description     # New features
   bugfix/issue-description     # Bug fixes  
   research/experiment-name     # Research contributions
   docs/section-name           # Documentation updates
   refactor/component-name     # Code refactoring

**Example Branch Names:**

.. code-block:: bash

   git checkout -b feature/multi-language-validation
   git checkout -b bugfix/memory-limit-error
   git checkout -b research/personality-temperature-interaction
   git checkout -b docs/api-reference-improvements

Development Standards
--------------------

Code Quality
~~~~~~~~~~~

**Python Code Standards:**
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and reasonably sized
- Use meaningful variable and function names

**Example of Good Code Style:**

.. code-block:: python

   from typing import List, Dict, Optional
   from pydantic import BaseModel

   def analyze_agent_consensus(
       agent_responses: List[Dict[str, str]], 
       threshold: float = 0.8
   ) -> Optional[str]:
       """Analyze agent responses to determine consensus.
       
       Args:
           agent_responses: List of agent response dictionaries
           threshold: Minimum agreement threshold for consensus (0.0-1.0)
           
       Returns:
           Consensus principle if achieved, None otherwise
           
       Raises:
           ValueError: If threshold is not between 0.0 and 1.0
       """
       if not 0.0 <= threshold <= 1.0:
           raise ValueError(f"Threshold must be 0.0-1.0, got {threshold}")
       
       principle_counts = {}
       for response in agent_responses:
           principle = response.get("chosen_principle")
           if principle:
               principle_counts[principle] = principle_counts.get(principle, 0) + 1
       
       if not principle_counts:
           return None
           
       total_responses = len(agent_responses)
       max_count = max(principle_counts.values())
       
       if max_count / total_responses >= threshold:
           return max(principle_counts.keys(), key=lambda k: principle_counts[k])
       
       return None

Testing Requirements
~~~~~~~~~~~~~~~~~~~

**All code changes must include tests:**

.. code-block:: python

   # tests/test_consensus_analysis.py
   import unittest
   from your_module import analyze_agent_consensus

   class TestConsensusAnalysis(unittest.TestCase):
       
       def test_consensus_achieved(self):
           """Test consensus detection with clear majority."""
           responses = [
               {"chosen_principle": "a"},
               {"chosen_principle": "a"}, 
               {"chosen_principle": "b"}
           ]
           result = analyze_agent_consensus(responses, threshold=0.6)
           self.assertEqual(result, "a")
       
       def test_no_consensus(self):
           """Test when no consensus threshold is met."""
           responses = [
               {"chosen_principle": "a"},
               {"chosen_principle": "b"},
               {"chosen_principle": "c"}
           ]
           result = analyze_agent_consensus(responses, threshold=0.8)
           self.assertIsNone(result)
       
       def test_invalid_threshold(self):
           """Test error handling for invalid threshold."""
           with self.assertRaises(ValueError):
               analyze_agent_consensus([], threshold=1.5)

**Testing Guidelines:**
- Write unit tests for individual functions
- Include integration tests for component interactions
- Test error conditions and edge cases
- Ensure tests are deterministic and repeatable
- Use descriptive test names that explain what's being tested

Documentation Standards
~~~~~~~~~~~~~~~~~~~~~~

**Docstring Format** (Google Style):

.. code-block:: python

   def process_experiment_results(
       results_path: str, 
       analysis_type: str = "consensus"
   ) -> Dict[str, Any]:
       """Process experiment results and generate analysis.
       
       This function loads experiment results from a JSON file and performs
       the specified type of analysis on the data.
       
       Args:
           results_path: Path to the experiment results JSON file
           analysis_type: Type of analysis to perform. Options are:
               - "consensus": Analyze consensus formation patterns
               - "individual": Analyze individual agent behaviors  
               - "temporal": Analyze changes over time
               
       Returns:
           Dictionary containing analysis results with keys:
               - "summary": High-level summary statistics
               - "details": Detailed analysis data
               - "metadata": Analysis configuration and timestamps
               
       Raises:
           FileNotFoundError: If results_path does not exist
           ValueError: If analysis_type is not supported
           JSONDecodeError: If results file is not valid JSON
           
       Example:
           >>> results = process_experiment_results(
           ...     "experiment_results_20250819_105130.json",
           ...     analysis_type="consensus"
           ... )
           >>> print(results["summary"]["consensus_rate"])
           0.85
       """

**README and Documentation Updates:**
- Update relevant documentation when adding features
- Include examples for new functionality  
- Update configuration documentation for new parameters
- Add troubleshooting information for complex features

Submission Process
-----------------

Pull Request Guidelines
~~~~~~~~~~~~~~~~~~~~~~

**Before Submitting:**

1. **Run All Tests**:

   .. code-block:: bash

      pytest --mode=ci

2. **Check Code Style**:

   .. code-block:: bash

      # If using linting tools
      flake8 your_changed_files.py
      black your_changed_files.py --check

3. **Update Documentation**:

   .. code-block:: bash

      cd docs
      make html  # Verify documentation builds

4. **Test Your Changes**:

   .. code-block:: bash

      # Run a quick experiment to verify functionality
      python main.py config/test_config.yaml

**Pull Request Template:**

.. code-block:: text

   ## Description
   Brief description of what this PR does and why.
   
   ## Type of Change
   - [ ] Bug fix (non-breaking change that fixes an issue)
   - [ ] New feature (non-breaking change that adds functionality)
   - [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
   - [ ] Documentation update
   - [ ] Research contribution
   
   ## Testing
   - [ ] All existing tests pass
   - [ ] New tests added for new functionality  
   - [ ] Manual testing completed
   - [ ] Documentation updated
   
   ## Research Impact
   - [ ] This change affects experimental results
   - [ ] This change requires updating existing analyses
   - [ ] This change introduces new research possibilities
   
   ## Checklist
   - [ ] My code follows the project's style guidelines
   - [ ] I have performed a self-review of my code
   - [ ] I have commented my code, particularly in hard-to-understand areas
   - [ ] I have made corresponding changes to the documentation
   - [ ] My changes generate no new warnings
   - [ ] I have added tests that prove my fix is effective or that my feature works
   - [ ] New and existing unit tests pass locally with my changes

Review Process
~~~~~~~~~~~~~

**What Reviewers Look For:**

1. **Code Quality**: Clean, readable, well-documented code
2. **Testing**: Adequate test coverage and edge case handling
3. **Research Validity**: Changes that maintain or enhance research integrity
4. **Documentation**: Clear documentation for new features
5. **Compatibility**: Changes that don't break existing functionality

**Addressing Review Feedback:**

.. code-block:: bash

   # Make requested changes
   git add .
   git commit -m "Address review feedback: improve error handling"
   git push origin your-branch-name

**Merge Requirements:**
- At least one approval from a project maintainer
- All automated checks passing
- No merge conflicts with main branch
- Documentation updated appropriately

Research Contributions
---------------------

Experimental Contributions
~~~~~~~~~~~~~~~~~~~~~~~~~

**Novel Experiments:**
- New agent personality configurations
- Cross-cultural studies using multi-language support
- Innovative uses of the veil of ignorance concept
- Comparative studies with different model providers

**Analysis Contributions:**
- New statistical analysis methods
- Visualization techniques and dashboards  
- Machine learning approaches to pattern detection
- Network analysis of agent interactions

**Example Research Contribution Process:**

.. code-block:: bash

   # 1. Create research branch
   git checkout -b research/empathy-temperature-study
   
   # 2. Develop experimental configurations
   # Create config files in configs/research/empathy_study/
   
   # 3. Run experiments and collect data
   # Document methodology in research_notes/
   
   # 4. Develop analysis scripts
   # Add to analysis_scripts/empathy_temperature/
   
   # 5. Document findings
   # Update docs/research/ or create research paper
   
   # 6. Submit PR with complete research package

Data Contributions
~~~~~~~~~~~~~~~~~

**Experimental Data:**
- Well-documented experiment runs with novel configurations
- Replication studies validating previous results
- Cross-cultural comparison datasets
- Large-scale parameter sweep results

**Analysis Scripts:**
- Statistical analysis pipelines
- Visualization and plotting utilities
- Data processing and cleaning tools
- Reproducible analysis workflows

Documentation Contributions
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Tutorial Development:**
- Step-by-step guides for new users
- Advanced configuration examples
- Analysis methodology documentation
- Troubleshooting and FAQ sections

**Research Documentation:**
- Theoretical background explanations
- Methodology comparisons
- Best practices for experimental design
- Interpretation guidelines for results

Community Guidelines
-------------------

Communication Standards
~~~~~~~~~~~~~~~~~~~~~~~

**Be Respectful and Inclusive:**
- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Focus on constructive feedback and solutions
- Be patient with newcomers and questions

**Research Ethics:**
- Maintain high standards for research integrity
- Properly cite related work and inspirations
- Share methodologies transparently
- Acknowledge limitations and potential biases

**Issue Reporting:**
- Use clear, descriptive titles
- Provide steps to reproduce problems
- Include relevant configuration files and error messages
- Specify your environment (OS, Python version, etc.)

Getting Help
~~~~~~~~~~~

**Where to Ask Questions:**
- GitHub Discussions for general questions and research ideas
- Issues for bug reports and feature requests
- Pull Request comments for code-specific questions
- Documentation for methodology and usage questions

**What Information to Include:**
- Your environment setup (OS, Python version, dependencies)
- Relevant configuration files
- Complete error messages and stack traces
- Steps you've already tried
- What you expected to happen vs. what actually happened

Recognition
----------

Contributor Recognition
~~~~~~~~~~~~~~~~~~~~~~

**Contributors are recognized through:**
- GitHub contributor listings
- Documentation acknowledgments
- Research paper co-authorships (for significant research contributions)
- Conference presentation opportunities
- Project maintenance roles for ongoing contributors

**Research Credit:**
- Significant research contributions may qualify for co-authorship on papers
- Novel experimental methodologies will be properly credited
- Data contributions will be acknowledged in publications
- Analysis tools and visualizations will be attributed

License and Legal
----------------

**Code License:**
All code contributions are subject to the project's MIT License. By contributing code, you agree to license your contributions under the same terms.

**Research Data:**
Experimental data and results should be contributed under terms that allow academic use and reproduction while respecting any applicable privacy or ethical constraints.

**Attribution:**
Contributors retain credit for their contributions while granting the project rights to use, modify, and distribute the contributions as part of the larger research effort.

Thank you for contributing to the Frohlich Experiment! Your work helps advance our understanding of AI ethics and distributive justice. For questions about contributing, please check our documentation or open a discussion on GitHub.
