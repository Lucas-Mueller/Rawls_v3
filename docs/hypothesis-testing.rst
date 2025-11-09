Hypothesis Testing Framework
============================

The Frohlich Experiment includes a comprehensive hypothesis testing framework that enables systematic investigation of research questions through controlled experimental variations. This framework supports batch execution, statistical analysis, and visualization of experimental results across multiple conditions.

.. contents:: Table of Contents
   :local:
   :depth: 2

Framework Overview
------------------

The hypothesis testing framework is organized around specific research questions (hypotheses) with dedicated experimental conditions, configurations, and analysis tools.

.. code-block:: text

   hypothesis_testing/
   ├── hypothesis_1/          # Cultural Communication Styles
   │   ├── configs/          # 33 experimental configurations
   │   ├── results/          # Experimental results (JSON)
   │   ├── terminal_outputs/ # Execution logs
   │   └── transcripts/      # Agent conversation transcripts
   ├── hypothesis_2/         # American vs Chinese Cultural Values
   │   ├── configs/          # Cultural variation configurations
   │   ├── results/          # Cross-cultural experiment results
   │   ├── terminal_outputs/ # Execution logs
   │   └── transcripts/      # Multilingual conversation transcripts
   ├── hypothesis_3/         # Income Inequality Variations
   │   ├── configs/          # Inequality manipulation configs
   │   ├── results/          # Inequality impact results
   │   ├── terminal_outputs/ # Execution logs
   │   └── transcripts/      # Economic scenario transcripts
   ├── hypothesis_6/         # Advanced Experimental Conditions
   │   ├── configs/          # Complex experimental designs
   │   ├── results/          # Advanced condition results
   │   ├── terminal_outputs/ # Execution logs
   │   └── transcripts/      # Complex scenario transcripts
   ├── reproducibility_proof/ # Experimental Reproducibility Tests
   └── utils_hypothesis_testing/ # Shared Analysis Utilities

Research Hypotheses
-------------------

Hypothesis 1: Cultural Communication Styles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Research Question:** How do different communication styles affect consensus building in distributive justice scenarios?

**Experimental Design:**
- 33 different experimental conditions
- Variations in agent communication patterns
- Analysis of consensus formation dynamics

**Key Findings:**
- Communication style impacts consensus time
- Some styles lead to more equitable outcomes
- Cultural communication patterns emerge in AI agents

Hypothesis 2: American vs Chinese Cultural Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Research Question:** Do AI agents trained on American vs Chinese cultural contexts exhibit different patterns in distributive justice decisions?

**Experimental Design:**
- American cultural conditioning
- Chinese cultural conditioning
- Cross-cultural comparison analysis

**Key Findings:**
- Cultural conditioning affects fairness perceptions
- Different cultural frameworks lead to different justice principles
- AI agents can learn cultural value systems

Hypothesis 3: Income Inequality Variations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Research Question:** How do different levels of income inequality affect AI agent decisions about distributive justice?

**Experimental Design:**
- Low inequality scenarios
- Medium inequality scenarios
- High inequality scenarios
- Manipulator agents for experimental control

**Key Findings:**
- Inequality levels influence fairness judgments
- Higher inequality leads to more varied justice principles
- AI agents respond to economic context

Hypothesis 6: Advanced Experimental Conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Research Question:** Complex interactions between multiple experimental variables in distributive justice scenarios.

**Experimental Design:**
- Multi-factor experimental designs
- Interaction effects analysis
- Advanced statistical modeling

**Key Findings:**
- Complex variable interactions identified
- Non-linear effects in justice decision making
- Robust statistical patterns across conditions

Batch Execution Utilities
-------------------------

The framework includes powerful batch execution utilities for running multiple experiments efficiently.

Runner Module (``utils_hypothesis_testing/runner.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Core Functions:**

.. code-block:: python

   from utils_hypothesis_testing.runner import (
       run_single_experiment,
       run_batch_experiments,
       generate_experiment_configs
   )

**Single Experiment Execution:**

.. code-block:: python

   async def run_single_experiment():
       \"\"\"Run a single hypothesis test experiment.\"\"\"

       # Load configuration
       config = ExperimentConfiguration.from_yaml(
           "hypothesis_2/configs/american_condition_1.yaml"
       )

       # Execute experiment
       results = await run_experiment_from_config(config)

       # Save results
       with open("results/experiment_output.json", 'w') as f:
           json.dump(results, f, indent=2, default=str)

       return results

**Batch Experiment Execution:**

.. code-block:: python

   async def run_hypothesis_batch():
       \"\"\"Run multiple experiments for hypothesis testing.\"\"\"

       # Define experiment configurations
       config_files = [
           "hypothesis_2/configs/american_condition_1.yaml",
           "hypothesis_2/configs/american_condition_2.yaml",
           "hypothesis_2/configs/chinese_condition_1.yaml",
           "hypothesis_2/configs/chinese_condition_2.yaml"
       ]

       # Execute batch
       results = await run_experiments_parallel_async(
           config_files=config_files,
           max_parallel=3,
           output_dir="hypothesis_2/results/",
           verbose=True
       )

       return results

**Configuration Generation:**

.. code-block:: python

   def generate_hypothesis_configs():
       \"\"\"Generate multiple configurations for hypothesis testing.\"\"\"

       from utils.experiment_runner import generate_random_config

       # Generate configs for cultural comparison
       configs = []
       for culture in ["american", "chinese"]:
           for condition in range(1, 6):
               config = generate_random_config(
                   num_agents=3,
                   num_rounds=20,
                   language="english" if culture == "american" else "mandarin",
                   personality=get_cultural_personality(culture),
                   seed=f"{culture}_{condition}"
               )
               configs.append(config)

       return configs

Statistical Analysis Tools
--------------------------

Statistics Module (``utils_hypothesis_testing/statistics.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Core Statistical Functions:**

.. code-block:: python

   from utils_hypothesis_testing.statistics import (
       calculate_consensus_rates,
       analyze_decision_patterns,
       compare_cultural_differences,
       perform_statistical_tests
   )

**Consensus Rate Analysis:**

.. code-block:: python

   def analyze_consensus_rates(results_list):
       \"\"\"Analyze consensus rates across experimental conditions.\"\"\"

       # Calculate consensus statistics
       consensus_stats = calculate_consensus_rates(results_list)

       print(f"Overall consensus rate: {consensus_stats['overall_rate']:.1%}")
       print(f"Average rounds to consensus: {consensus_stats['avg_rounds']:.1f}")

       # By experimental condition
       for condition, stats in consensus_stats['by_condition'].items():
           print(f"{condition}: {stats['rate']:.1%} consensus")

       return consensus_stats

**Decision Pattern Analysis:**

.. code-block:: python

   def analyze_justice_principles(results_list):
       \"\"\"Analyze which justice principles are chosen under different conditions.\"\"\"

       # Analyze principle selection patterns
       principle_stats = analyze_decision_patterns(results_list)

       # Most common principles
       for principle, stats in principle_stats['principle_distribution'].items():
           print(f"{principle}: {stats['count']} times ({stats['percentage']:.1%})")

       # Principle choice by experimental condition
       for condition, principles in principle_stats['by_condition'].items():
           print(f"{condition} most common: {principles[0]['principle']}")

       return principle_stats

**Cultural Comparison Analysis:**

.. code-block:: python

   def compare_cultural_results(american_results, chinese_results):
       \"\"\"Compare results between American and Chinese cultural conditions.\"\"\"

       # Statistical comparison
       comparison = compare_cultural_differences(
           american_results, chinese_results
       )

       # Significance tests
       print("Cultural Differences Analysis:")
       print(f"Consensus rate difference: {comparison['consensus_diff']:.1%}")
       print(f"Statistical significance: p = {comparison['p_value']:.3f}")

       # Principle preference differences
       for principle in comparison['principle_differences']:
           print(f"{principle['name']}: {principle['difference']:.1%} difference")

       return comparison

Visualization Tools
-------------------

Style Module (``utils_hypothesis_testing/style.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**University of Bayreuth Color Scheme:**

.. code-block:: python

   from utils_hypothesis_testing.style import (
       BAYREUTH_COLORS, setup_publication_style
   )

   # University of Bayreuth color palette
   colors = {
       'green': '#009260',      # Bayreuth Green
       'dark_gray': '#48535A',  # Dark Gray
       'medium_gray': '#7F8990', # Medium Gray
       'light_gray': '#EBEBE4'   # Light Gray
   }

   # Setup publication-quality plotting style
   plt.style.use(setup_publication_style())

**Consistent Plot Formatting:**

.. code-block:: python

   def create_consensus_plot(results_data):
       \"\"\"Create publication-quality consensus rate plot.\"\"\"

       fig, ax = plt.subplots(figsize=(10, 6))

       # Apply Bayreuth styling
       setup_publication_style()

       # Create bar plot
       conditions = list(results_data.keys())
       rates = [data['consensus_rate'] for data in results_data.values()]

       bars = ax.bar(conditions, rates,
                    color=BAYREUTH_COLORS['green'],
                    alpha=0.8)

       # Formatting
       ax.set_ylabel('Consensus Rate (%)', fontsize=12)
       ax.set_xlabel('Experimental Condition', fontsize=12)
       ax.set_title('Consensus Rates by Experimental Condition',
                   fontsize=14, fontweight='bold')

       # Add value labels on bars
       for bar, rate in zip(bars, rates):
           height = bar.get_height()
           ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                  f'{rate:.1%}', ha='center', va='bottom', fontsize=10)

       plt.tight_layout()
       return fig

Visualizations Module (``utils_hypothesis_testing/visualizations.py``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Hypothesis-Specific Visualizations:**

.. code-block:: python

   from utils_hypothesis_testing.visualizations import (
       create_cultural_comparison_plot,
       create_inequality_impact_plot,
       create_consensus_timeline,
       create_decision_heatmap
   )

**Cultural Comparison Visualization:**

.. code-block:: python

   def visualize_cultural_differences(results_a, results_b):
       \"\"\"Create visualization comparing American vs Chinese results.\"\"\"

       fig = create_cultural_comparison_plot(
           american_results=results_a,
           chinese_results=results_b,
           metric='consensus_rate',
           title='Cultural Differences in Consensus Building'
       )

       plt.savefig('cultural_consensus_comparison.png', dpi=300, bbox_inches='tight')
       plt.show()

       return fig

**Inequality Impact Analysis:**

.. code-block:: python

   def analyze_inequality_effects(results_by_inequality):
       \"\"\"Analyze how income inequality affects justice decisions.\"\"\"

       fig = create_inequality_impact_plot(
           low_inequality_results=results_by_inequality['low'],
           medium_inequality_results=results_by_inequality['medium'],
           high_inequality_results=results_by_inequality['high'],
           decision_metric='justice_principle'
       )

       plt.savefig('inequality_justice_decisions.png', dpi=300, bbox_inches='tight')
       plt.show()

       return fig

**Consensus Timeline Visualization:**

.. code-block:: python

   def show_consensus_evolution(experiment_results):
       \"\"\"Show how consensus evolves over discussion rounds.\"\"\"

       fig = create_consensus_timeline(
           results=experiment_results,
           show_individual_experiments=True,
           highlight_key_transitions=True
       )

       plt.savefig('consensus_evolution.png', dpi=300, bbox_inches='tight')
       plt.show()

       return fig

**Decision Pattern Heatmap:**

.. code-block:: python

   def create_decision_heatmap(experiment_matrix):
       \"\"\"Create heatmap showing decision patterns across conditions.\"\"\"

       fig = create_decision_heatmap(
           decision_matrix=experiment_matrix,
           conditions=['Condition_A', 'Condition_B', 'Condition_C'],
           principles=['Maximize_Floor', 'Maximize_Average', 'Maximize_Average_Floor'],
           title='Decision Patterns Across Experimental Conditions'
       )

       plt.savefig('decision_patterns_heatmap.png', dpi=300, bbox_inches='tight')
       plt.show()

       return fig

Data Management and Analysis
----------------------------

Results Processing
~~~~~~~~~~~~~~~~~~

**Batch Results Analysis:**

.. code-block:: python

   def process_hypothesis_results(hypothesis_dir):
       \"\"\"Process and analyze results from a hypothesis testing directory.\"\"\"

       import json
       from pathlib import Path

       results_dir = Path(hypothesis_dir) / "results"
       all_results = []

       # Load all result files
       for result_file in results_dir.glob("*.json"):
           with open(result_file, 'r') as f:
               result = json.load(f)
               all_results.append(result)

       # Perform comprehensive analysis
       analysis = {
           'total_experiments': len(all_results),
           'consensus_analysis': calculate_consensus_rates(all_results),
           'decision_patterns': analyze_decision_patterns(all_results),
           'performance_metrics': calculate_performance_metrics(all_results)
       }

       return analysis

**Cross-Hypothesis Comparisons:**

.. code-block:: python

   def compare_hypotheses(hypothesis_results):
       \"\"\"Compare results across different hypotheses.\"\"\"

       comparisons = {}

       for hypothesis_name, results in hypothesis_results.items():
           comparisons[hypothesis_name] = {
               'consensus_rate': results['consensus_analysis']['overall_rate'],
               'avg_rounds': results['consensus_analysis']['avg_rounds'],
               'principle_distribution': results['decision_patterns']['principle_distribution']
           }

       # Create comparison visualizations
       create_hypothesis_comparison_plot(comparisons)

       return comparisons

Reproducibility and Validation
------------------------------

Reproducibility Testing
~~~~~~~~~~~~~~~~~~~~~~~

**Reproducibility Verification:**

.. code-block:: python

   def verify_experiment_reproducibility(config_file, num_runs=3):
       \"\"\"Verify that experiments produce consistent results with same seed.\"\"\"

       results = []

       for run in range(num_runs):
           # Load config
           config = ExperimentConfiguration.from_yaml(config_file)

           # Ensure seed is set for reproducibility
           if config.seed is None:
               config.seed = 42  # Default reproducibility seed

           # Run experiment
           result = await run_experiment_from_config(config)
           results.append(result)

       # Check reproducibility
       consensus_rates = [r['phase2_results']['consensus_reached'] for r in results]
       chosen_principles = [r['phase2_results']['chosen_principle'] for r in results]

       reproducibility_check = {
           'all_consensus_agree': len(set(consensus_rates)) == 1,
           'all_principles_agree': len(set(chosen_principles)) == 1,
           'consistent_outcomes': all_consensus_agree and all_principles_agree,
           'num_runs': num_runs
       }

       return reproducibility_check

**Statistical Validation:**

.. code-block:: python

   def validate_hypothesis_findings(results, statistical_tests=True):
       \"\"\"Validate hypothesis findings with statistical rigor.\"\"\"

       validation = {
           'sample_size': len(results),
           'effect_sizes': calculate_effect_sizes(results),
           'statistical_significance': {},
           'confidence_intervals': {}
       }

       if statistical_tests:
           # Perform statistical tests
           validation['statistical_significance'] = perform_statistical_tests(results)
           validation['confidence_intervals'] = calculate_confidence_intervals(results)

       # Generate validation report
       create_validation_report(validation)

       return validation

Best Practices
--------------

Hypothesis Testing Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. Hypothesis Formulation:**

.. code-block:: python

   def formulate_research_hypothesis():
       \"\"\"Clearly define research questions and predictions.\"\"\"

       hypothesis = {
           'research_question': 'How does cultural context affect AI justice decisions?',
           'null_hypothesis': 'Cultural context has no effect on AI justice decisions',
           'alternative_hypothesis': 'Different cultural contexts lead to different justice decisions',
           'experimental_design': 'Compare American vs Chinese cultural conditioning',
           'expected_effect_size': 'medium',
           'required_sample_size': 50
       }

       return hypothesis

**2. Experimental Design:**

.. code-block:: python

   def design_experiments(hypothesis):
       \"\"\"Design controlled experiments to test the hypothesis.\"\"\"

       design = {
           'independent_variables': ['cultural_context', 'income_inequality'],
           'dependent_variables': ['justice_principle_choice', 'consensus_time'],
           'control_variables': ['agent_model', 'discussion_length', 'language'],
           'experimental_conditions': generate_conditions(hypothesis),
           'randomization': True,
           'blinding': 'double_blind_where_possible'
       }

       return design

**3. Data Collection:**

.. code-block:: python

   async def collect_experimental_data(design):
       \"\"\"Systematically collect data according to experimental design.\"\"\"

       all_results = []

       for condition in design['experimental_conditions']:
           # Generate configurations for this condition
           configs = generate_configs_for_condition(condition)

           # Run experiments
           results = await run_experiments_parallel_async(
               config_files=configs,
               max_parallel=5,
               output_dir=f"results/{condition['name']}/"
           )

           all_results.extend(results)

       return all_results

**4. Analysis and Interpretation:**

.. code-block:: python

   def analyze_and_interpret(results, hypothesis):
       \"\"\"Analyze results and interpret findings in context of hypothesis.\"\"\"

       # Statistical analysis
       stats = perform_statistical_analysis(results)

       # Effect size calculation
       effects = calculate_effect_sizes(results, hypothesis)

       # Visualization
       create_analysis_visualizations(results, hypothesis)

       # Interpretation
       interpretation = interpret_findings(stats, effects, hypothesis)

       return {
           'statistics': stats,
           'effects': effects,
           'interpretation': interpretation,
           'recommendations': generate_recommendations(interpretation)
       }

**5. Reporting and Documentation:**

.. code-block:: python

   def create_research_report(analysis, hypothesis):
       \"\"\"Create comprehensive research report.\"\"\"

       report = {
           'hypothesis': hypothesis,
           'methodology': document_methodology(),
           'results': analysis['statistics'],
           'interpretation': analysis['interpretation'],
           'limitations': identify_limitations(),
           'future_work': suggest_future_research(),
           'figures': generate_publication_figures(),
           'supplementary_materials': create_supplementary_data()
       }

       # Generate report formats
       generate_pdf_report(report)
       generate_interactive_dashboard(report)

       return report

Quality Assurance
-----------------

**Data Integrity Checks:**

.. code-block:: python

   def validate_experimental_data(results):
       \"\"\"Validate the integrity of experimental data.\"\"\"

       validation_checks = {
           'complete_results': check_all_experiments_completed(results),
           'data_consistency': check_data_consistency(results),
           'statistical_assumptions': check_statistical_assumptions(results),
           'reproducibility': verify_reproducibility(results)
       }

       # Report any issues
       issues = [check for check, passed in validation_checks.items() if not passed]

       if issues:
           print(f"Data validation issues found: {issues}")
           return False

       print("All data validation checks passed")
       return True

**Replication Standards:**

.. code-block:: python

   def ensure_replication_standards(experiment_config):
       \"\"\"Ensure experiment meets replication standards.\"\"\"

       standards_check = {
           'random_seed_documented': experiment_config.seed is not None,
           'sample_size_adequate': len(experiment_config.agents) >= 3,
           'conditions_clearly_defined': validate_condition_definitions(experiment_config),
           'data_preservation': check_data_preservation_setup(),
           'analysis_transparent': validate_analysis_transparency()
       }

       return standards_check

Integration with Main Framework
-------------------------------

**Seamless Integration:**

.. code-block:: python

   def run_hypothesis_test(hypothesis_name, conditions):
       \"\"\"Run a complete hypothesis test using the main framework.\"\"\"

       # Setup
       setup_experiment_environment()

       # Generate configurations
       configs = generate_hypothesis_configs(hypothesis_name, conditions)

       # Run experiments using main framework
       results = run_experiments_parallel(configs)

       # Analyze using hypothesis utilities
       analysis = analyze_hypothesis_results(results, hypothesis_name)

       # Generate report
       report = create_hypothesis_report(analysis, hypothesis_name)

       return report

**Cross-Hypothesis Meta-Analysis:**

.. code-block:: python

   def perform_meta_analysis(all_hypotheses_results):
       \"\"\"Perform meta-analysis across all hypotheses.\"\"\"

       meta_analysis = {
           'overall_effects': calculate_overall_effects(all_hypotheses_results),
           'consistency_across_hypotheses': check_consistency(all_hypotheses_results),
           'moderator_analysis': analyze_moderators(all_hypotheses_results),
           'publication_bias_check': check_publication_bias(all_hypotheses_results)
       }

       # Generate meta-analysis report
       create_meta_analysis_report(meta_analysis)

       return meta_analysis

This comprehensive hypothesis testing framework enables rigorous, reproducible research into AI behavior in distributive justice scenarios, with full support for statistical analysis, visualization, and publication-quality reporting.

See Also
--------

- :doc:`user-guide/running-experiments` - Learn how to run hypothesis experiments
- :doc:`user-guide/designing-experiments` - Design custom hypothesis configurations
- :doc:`user-guide/analyzing-results` - Analyze hypothesis testing results
- :doc:`contributing/testing` - Testing framework for hypothesis validation
- :doc:`cultural-adaptation` - Multilingual support for cross-cultural hypotheses
- :doc:`error-handling` - Error handling in hypothesis testing scenarios