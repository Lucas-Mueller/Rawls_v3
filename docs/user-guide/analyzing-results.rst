Analyzing Results
=================

This comprehensive guide shows you how to interpret, analyze, and visualize results from Frohlich Experiments, from basic output understanding to advanced statistical analysis.

Understanding Output Files
---------------------------

Result File Structure
~~~~~~~~~~~~~~~~~~~~~

Each experiment generates a timestamped JSON file using an **agent-centric logging structure**:

.. code-block:: json

   {
     "general_information": {
       "experiment_id": "uuid-string",
       "consensus_reached": true,
       "consensus_principle": "maximizing_floor",
       "consensus_floor_amount": 15000,
       "rounds_conducted_phase_2": 5,
       "max_rounds_phase_2": 10,
       "public_conversation_phase_2": "Complete discussion transcript...",
       "seed_used": 42,
       "config_file": "config.yaml",
       "income_class_probabilities": {
         "high": 0.05,
         "medium_high": 0.1,
         "medium": 0.5,
         "medium_low": 0.25,
         "low": 0.1
       }
     },
     "agents": {
       "Agent_1": {
         "name": "Agent_1",
         "model": "gpt-4o-mini",
         "temperature": 0.0,
         "personality": "Analytical thinker",
         "phase_1": {
           "initial_ranking": [
             {"principle": "maximizing_floor", "rank": 1, "reasoning": "..."},
             {"principle": "maximizing_average", "rank": 2, "reasoning": "..."},
             {"principle": "floor_constraint", "rank": 3, "reasoning": "..."},
             {"principle": "range_constraint", "rank": 4, "reasoning": "..."}
           ],
           "detailed_explanation": "Complete explanation of ranking...",
           "ranking_2": [/* Second ranking after demonstrations */],
           "demonstrations": [/* Examples seen by agent */],
           "ranking_3": [/* Final ranking before Phase 2 */]
         },
         "phase_2": {
           "rounds": [
             {
               "round_number": 1,
               "statement": "Agent's statement in discussion...",
               "memory_before_turn": "Agent's memory state..."
             }
           ],
           "post_group_discussion": {
             "final_ranking": [/* Final ranking after discussion */],
             "final_thoughts": "Agent's final reflections..."
           }
         }
       }
       /* Additional agents... */
     },
     "voting_history": {
       "voting_rounds": [
         {
           "round": 1,
           "votes": {"maximizing_floor": 3, "maximizing_average": 1},
           "consensus_reached": false
         }
       ]
     }
   }

Key Metrics Overview
~~~~~~~~~~~~~~~~~~~~

**Execution Metrics:**
- Total experiment duration
- API call counts and costs
- Error rates and recovery statistics
- Memory usage patterns

**Phase 1 Metrics:**
- Individual agent principle preferences
- Reasoning complexity and depth
- Constraint specification patterns
- Learning progression indicators

**Phase 2 Metrics:**
- Group consensus achievement
- Discussion dynamics and participation
- Principle switching patterns
- Final payoff distributions

Basic Analysis Tasks
--------------------

Loading and Parsing Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import json
   import pandas as pd
   from pathlib import Path
   from datetime import datetime

   def load_experiment_results(filepath):
       """Load and parse experiment results JSON."""
       with open(filepath, 'r') as f:
           results = json.load(f)
       return results

   def extract_basic_metrics(results):
       """Extract key metrics for quick analysis."""
       general_info = results['general_information']
       agents = results['agents']

       metrics = {
           'experiment_id': general_info['experiment_id'],
           'consensus_reached': general_info['consensus_reached'],
           'final_principle': general_info.get('consensus_principle'),
           'floor_amount': general_info.get('consensus_floor_amount'),
           'total_rounds': general_info['rounds_conducted_phase_2'],
           'max_rounds': general_info['max_rounds_phase_2'],
           'participant_count': len(agents),
           'seed_used': general_info.get('seed_used'),
           'config_file': general_info.get('config_file')
       }
       return metrics

   # Usage example
   results = load_experiment_results("experiment_results_20250819_105130.json")
   metrics = extract_basic_metrics(results)
   print(f"Consensus: {metrics['consensus_reached']}, Principle: {metrics['final_principle']}")

Phase 1 Analysis
~~~~~~~~~~~~~~~~

Analyze individual agent behavior during familiarization:

.. code-block:: python

   def analyze_phase1_responses(results):
       """Analyze Phase 1 individual responses."""
       phase1_data = []

       for agent_name, agent_data in results['agents'].items():
           phase1 = agent_data['phase_1']

           # Extract initial ranking
           for rank_item in phase1['initial_ranking']:
               phase1_data.append({
                   'agent': agent_name,
                   'principle': rank_item['principle'],
                   'rank': rank_item['rank'],
                   'reasoning_length': len(rank_item.get('reasoning', ''))
               })

           # Add ranking progression data
           if phase1.get('ranking_2'):
               for i, principle in enumerate(phase1['ranking_2']):
                   phase1_data.append({
                       'agent': agent_name,
                       'principle': principle,
                       'stage': 'ranking_2',
                       'rank': i + 1
                   })

           if phase1.get('ranking_3'):
               for i, principle in enumerate(phase1['ranking_3']):
                   phase1_data.append({
                       'agent': agent_name,
                       'principle': principle,
                       'stage': 'ranking_3',
                       'rank': i + 1
                   })

       return pd.DataFrame(phase1_data)

   # Analyze principle preferences
   def phase1_preference_analysis(df):
       """Analyze principle preferences in Phase 1."""
       # Preference distribution by rank
       rank_dist = df[df['rank'] == 1].groupby('principle').size()

       # Reasoning complexity
       reasoning_stats = df.groupby(['agent', 'principle'])['reasoning_length'].mean()

       return {
           'top_preferences': rank_dist.to_dict(),
           'reasoning_complexity': reasoning_stats.to_dict()
       }

Phase 2 Analysis
~~~~~~~~~~~~~~~~

Analyze group discussion dynamics:

.. code-block:: python

   def analyze_phase2_discussion(results):
       """Analyze Phase 2 group discussion patterns."""
       discussion_data = []

       for agent_name, agent_data in results['agents'].items():
           phase2 = agent_data['phase_2']

           for round_data in phase2.get('rounds', []):
               discussion_data.append({
                   'agent': agent_name,
                   'round': round_data['round_number'],
                   'statement': round_data['statement'],
                   'statement_length': len(round_data['statement']),
                   'memory_length': len(round_data.get('memory_before_turn', ''))
               })

       return pd.DataFrame(discussion_data)

   def analyze_discussion_patterns(df):
       """Analyze patterns in discussion data."""
       patterns = {}

       # Message length statistics
       patterns['avg_message_length'] = df['statement_length'].mean()
       patterns['total_messages'] = len(df)

       # Participation by round
       patterns['messages_per_round'] = df.groupby('round').size()

       # Agent participation distribution
       patterns['agent_participation'] = df.groupby('agent').size()

       return patterns

Consensus Analysis
~~~~~~~~~~~~~~~~~

Analyze how consensus is achieved:

.. code-block:: python

   def analyze_consensus_formation(results):
       """Analyze how consensus forms over discussion rounds."""
       general_info = results['general_information']
       voting_history = results.get('voting_history', {})

       consensus_metrics = {
           'consensus_achieved': general_info['consensus_reached'],
           'final_principle': general_info.get('consensus_principle'),
           'final_floor_amount': general_info.get('consensus_floor_amount'),
           'rounds_conducted': general_info['rounds_conducted_phase_2'],
           'max_rounds': general_info['max_rounds_phase_2']
       }

       # Analyze voting history if available
       if voting_history.get('voting_rounds'):
           voting_rounds = voting_history['voting_rounds']
           consensus_metrics['voting_rounds_count'] = len(voting_rounds)

           # Find when consensus was reached
           for round_data in voting_rounds:
               if round_data.get('consensus_reached'):
                   consensus_metrics['consensus_round'] = round_data['round']
                   break

       return consensus_metrics

   def analyze_principle_evolution(results):
       """Analyze how agent preferences evolve from Phase 1 to Phase 2."""
       evolution_data = []

       for agent_name, agent_data in results['agents'].items():
           phase1_final = None
           if agent_data['phase_1'].get('ranking_3'):
               phase1_final = agent_data['phase_1']['ranking_3'][0]  # Top preference
           elif agent_data['phase_1'].get('ranking_2'):
               phase1_final = agent_data['phase_1']['ranking_2'][0]
           else:
               phase1_final = agent_data['phase_1']['initial_ranking'][0]['principle']

           phase2_final = None
           if agent_data['phase_2'].get('post_group_discussion', {}).get('final_ranking'):
               phase2_final = agent_data['phase_2']['post_group_discussion']['final_ranking'][0]

           evolution_data.append({
               'agent': agent_name,
               'phase1_preference': phase1_final,
               'phase2_preference': phase2_final,
               'principle_switch': phase1_final != phase2_final if phase2_final else None
           })

       return pd.DataFrame(evolution_data)

Advanced Analysis Techniques
----------------------------

Statistical Analysis
~~~~~~~~~~~~~~~~~~~

Perform statistical tests on experimental data:

.. code-block:: python

   import scipy.stats as stats
   from scipy.stats import chi2_contingency, mannwhitneyu
   import numpy as np

   def statistical_analysis_suite(results_list):
       """Comprehensive statistical analysis of multiple experiments."""

       # Combine results from multiple experiments
       combined_metrics = [extract_basic_metrics(r) for r in results_list]
       df = pd.DataFrame(combined_metrics)

       analyses = {}

       # Consensus rate analysis
       consensus_rate = df['consensus_reached'].mean()
       consensus_ci = stats.binom.interval(0.95, len(df), consensus_rate)

       analyses['consensus'] = {
           'rate': consensus_rate,
           'confidence_interval': consensus_ci,
           'sample_size': len(df)
       }

       # Principle preference distribution
       principle_counts = df['final_principle'].value_counts()
       if len(principle_counts) > 1:
           chi2_stat, p_value = chi2_contingency([principle_counts.values, [len(df)/4]*4])
           uniform_distribution = p_value > 0.05
       else:
           chi2_stat, p_value, uniform_distribution = None, None, None

       analyses['principle_distribution'] = {
           'counts': principle_counts.to_dict(),
           'chi2_test': {'statistic': chi2_stat, 'p_value': p_value} if chi2_stat else None,
           'uniform_distribution': uniform_distribution
       }

       # Duration analysis (if available)
       if 'duration' in df.columns:
           duration_stats = {
               'mean': df['duration'].mean(),
               'median': df['duration'].median(),
               'std': df['duration'].std(),
               'range': (df['duration'].min(), df['duration'].max())
           }
           analyses['duration'] = duration_stats

       return analyses

Comparative Analysis
~~~~~~~~~~~~~~~~~~~

Compare different experimental conditions:

.. code-block:: python

   def compare_experimental_conditions(condition_a_results, condition_b_results, condition_names=["A", "B"]):
       """Compare two experimental conditions."""

       # Extract metrics for both conditions
       metrics_a = [extract_basic_metrics(r) for r in condition_a_results]
       metrics_b = [extract_basic_metrics(r) for r in condition_b_results]

       df_a = pd.DataFrame(metrics_a)
       df_b = pd.DataFrame(metrics_b)

       comparison = {}

       # Consensus rate comparison
       consensus_a = df_a['consensus_reached'].mean()
       consensus_b = df_b['consensus_reached'].mean()

       comparison['consensus_rates'] = {
           condition_names[0]: consensus_a,
           condition_names[1]: consensus_b,
           'difference': consensus_b - consensus_a
       }

       # Principle preference comparison
       principles_a = df_a['final_principle'].value_counts(normalize=True)
       principles_b = df_b['final_principle'].value_counts(normalize=True)

       comparison['principle_preferences'] = {
           condition_names[0]: principles_a.to_dict(),
           condition_names[1]: principles_b.to_dict()
       }

       # Rounds to consensus comparison
       rounds_a = df_a['total_rounds'].mean()
       rounds_b = df_b['total_rounds'].mean()

       comparison['discussion_length'] = {
           condition_names[0]: rounds_a,
           condition_names[1]: rounds_b,
           'difference': rounds_b - rounds_a
       }

       return comparison

Visualization Techniques
------------------------

Basic Visualizations
~~~~~~~~~~~~~~~~~~~

Create standard plots for experiment analysis:

.. code-block:: python

   import matplotlib.pyplot as plt
   import seaborn as sns

   def create_experiment_visualizations(results_list, save_dir="plots/"):
       """Create standard visualization suite."""

       # Prepare data
       metrics_list = [extract_basic_metrics(r) for r in results_list]
       df = pd.DataFrame(metrics_list)

       # Set up plotting style
       plt.style.use('seaborn-v0_8')
       fig, axes = plt.subplots(2, 2, figsize=(15, 12))

       # 1. Consensus Rate
       consensus_counts = df['consensus_reached'].value_counts()
       axes[0,0].pie(consensus_counts.values, labels=['No Consensus', 'Consensus'],
                     autopct='%1.1f%%', colors=['lightcoral', 'lightgreen'])
       axes[0,0].set_title('Consensus Achievement Rate')

       # 2. Principle Distribution
       principle_counts = df['final_principle'].value_counts()
       if len(principle_counts) > 0:
           axes[0,1].bar(range(len(principle_counts)), principle_counts.values)
           axes[0,1].set_xticks(range(len(principle_counts)))
           axes[0,1].set_xticklabels(principle_counts.index, rotation=45)
           axes[0,1].set_title('Final Principle Distribution')
           axes[0,1].set_ylabel('Frequency')

       # 3. Discussion Rounds Distribution
       axes[1,0].hist(df['total_rounds'], bins=20, alpha=0.7, color='skyblue')
       axes[1,0].set_title('Discussion Rounds Distribution')
       axes[1,0].set_xlabel('Rounds Conducted')
       axes[1,0].set_ylabel('Frequency')

       # 4. Agent Participation vs Consensus
       consensus_df = df[df['consensus_reached'] == True]
       no_consensus_df = df[df['consensus_reached'] == False]

       axes[1,1].scatter(consensus_df['participant_count'], consensus_df['total_rounds'],
                        alpha=0.6, label='Consensus', color='green')
       axes[1,1].scatter(no_consensus_df['participant_count'], no_consensus_df['total_rounds'],
                        alpha=0.6, label='No Consensus', color='red')
       axes[1,1].set_title('Agent Count vs Discussion Length')
       axes[1,1].set_xlabel('Number of Agents')
       axes[1,1].set_ylabel('Discussion Rounds')
       axes[1,1].legend()

       plt.tight_layout()
       plt.savefig(f"{save_dir}/experiment_overview.png", dpi=300, bbox_inches='tight')
       plt.show()

Interactive Visualizations
~~~~~~~~~~~~~~~~~~~~~~~~~

Create interactive plots using Plotly:

.. code-block:: python

   import plotly.graph_objects as go
   import plotly.express as px
   from plotly.subplots import make_subplots

   def create_interactive_analysis_dashboard(results_list):
       """Create interactive dashboard for experiment analysis."""

       # Prepare data
       all_data = []
       for i, results in enumerate(results_list):
           metrics = extract_basic_metrics(results)
           metrics['experiment_num'] = i + 1

           # Add Phase 1 diversity metric
           phase1_df = analyze_phase1_responses(results)
           metrics['phase1_preference_diversity'] = len(phase1_df['principle'].unique())

           # Add Phase 2 discussion metrics
           phase2_df = analyze_phase2_discussion(results)
           metrics['total_messages'] = len(phase2_df)
           metrics['avg_message_length'] = phase2_df['statement_length'].mean() if len(phase2_df) > 0 else 0

           all_data.append(metrics)

       df = pd.DataFrame(all_data)

       # Create subplots
       fig = make_subplots(
           rows=2, cols=2,
           subplot_titles=('Consensus vs Discussion Length', 'Principle Preferences',
                          'Discussion Activity', 'Experiment Overview'),
           specs=[[{\"secondary_y\": False}, {\"type\": \"bar\"}],
                  [{\"secondary_y\": True}, {\"type\": \"scatter\"}]]
       )

       # 1. Consensus vs Discussion Length (scatter)
       consensus_color = df['consensus_reached'].map({True: 'green', False: 'red'})
       fig.add_trace(
           go.Scatter(x=df['total_rounds'], y=df['phase1_preference_diversity'],
                     mode='markers',
                     marker=dict(color=consensus_color, size=10),
                     text=df['final_principle'],
                     hovertemplate="Rounds: %{x}<br>Diversity: %{y}<br>Principle: %{text}",
                     name="Experiments"),
           row=1, col=1
       )

       # 2. Principle Distribution (bar)
       principle_counts = df['final_principle'].value_counts()
       fig.add_trace(
           go.Bar(x=principle_counts.index, y=principle_counts.values,
                  name="Principle Count"),
           row=1, col=2
       )

       # 3. Discussion Activity (dual axis)
       fig.add_trace(
           go.Scatter(x=df['experiment_num'], y=df['total_messages'],
                     mode='lines+markers', name="Total Messages"),
           row=2, col=1
       )

       fig.add_trace(
           go.Scatter(x=df['experiment_num'], y=df['avg_message_length'],
                     mode='lines+markers', name="Avg Message Length",
                     yaxis="y2"),
           row=2, col=1, secondary_y=True
       )

       # 4. Experiment Overview
       fig.add_trace(
           go.Scatter(x=df['experiment_num'], y=df['participant_count'],
                     mode='lines+markers',
                     marker=dict(size=df['total_rounds']),
                     name="Agent Count vs Rounds"),
           row=2, col=2
       )

       # Update layout
       fig.update_layout(height=800, showlegend=True,
                        title_text="Frohlich Experiment Analysis Dashboard")

       fig.show()

       return fig

Advanced Research Analysis
--------------------------

Agent Behavior Modeling
~~~~~~~~~~~~~~~~~~~~~~

Model individual agent decision patterns:

.. code-block:: python

   from sklearn.cluster import KMeans
   from sklearn.preprocessing import StandardScaler

   def agent_behavior_clustering(results_list):
       """Cluster agents based on behavior patterns across experiments."""

       # Extract agent features across all experiments
       agent_features = []
       for results in results_list:
           general_info = results['general_information']

           for agent_name, agent_data in results['agents'].items():
               phase1 = agent_data['phase_1']
               phase2 = agent_data['phase_2']

               # Calculate behavior metrics
               initial_top_choice = phase1['initial_ranking'][0]['principle'] if phase1.get('initial_ranking') else None
               final_top_choice = None
               if phase2.get('post_group_discussion', {}).get('final_ranking'):
                   final_top_choice = phase2['post_group_discussion']['final_ranking'][0]

               features = {
                   'agent_name': agent_name,
                   'experiment_id': general_info['experiment_id'],
                   'initial_preference': initial_top_choice,
                   'final_preference': final_top_choice,
                   'principle_switch': initial_top_choice != final_top_choice if final_top_choice else False,
                   'rounds_participated': len(phase2.get('rounds', [])),
                   'avg_statement_length': sum(len(r.get('statement', ''))
                                             for r in phase2.get('rounds', [])) / max(len(phase2.get('rounds', [])), 1)
               }
               agent_features.append(features)

       df = pd.DataFrame(agent_features)

       # Prepare features for clustering (exclude non-numeric)
       feature_cols = ['principle_switch', 'rounds_participated', 'avg_statement_length']
       X = df[feature_cols].fillna(0)

       # Standardize features
       scaler = StandardScaler()
       X_scaled = scaler.fit_transform(X)

       # Perform clustering
       kmeans = KMeans(n_clusters=3, random_state=42)
       df['behavior_cluster'] = kmeans.fit_predict(X_scaled)

       # Analyze clusters
       cluster_analysis = df.groupby('behavior_cluster')[feature_cols].mean()

       return df, cluster_analysis

Report Generation
-----------------

Automated Analysis Reports
~~~~~~~~~~~~~~~~~~~~~~~~~

Generate comprehensive analysis reports:

.. code-block:: python

   def generate_experiment_report(results_list, output_file="experiment_report.html"):
       """Generate comprehensive HTML report."""

       from jinja2 import Template

       # Perform analyses
       basic_stats = statistical_analysis_suite(results_list)
       phase1_analysis = analyze_phase1_across_experiments(results_list)
       phase2_analysis = analyze_phase2_across_experiments(results_list)

       # HTML template
       template_str = '''
       <!DOCTYPE html>
       <html>
       <head>
           <title>Frohlich Experiment Analysis Report</title>
           <style>
               body { font-family: Arial, sans-serif; margin: 40px; }
               .metric { background: #f0f0f0; padding: 10px; margin: 10px 0; }
               .chart { text-align: center; margin: 20px 0; }
               table { border-collapse: collapse; width: 100%; }
               th, td { border: 1px solid #ddd; padding: 8px; }
               th { background-color: #f2f2f2; }
           </style>
       </head>
       <body>
           <h1>Frohlich Experiment Analysis Report</h1>
           <p>Generated on {{ timestamp }}</p>

           <h2>Executive Summary</h2>
           <div class="metric">
               <strong>Total Experiments:</strong> {{ total_experiments }}<br>
               <strong>Consensus Rate:</strong> {{ "%.1f"|format(consensus_rate) }}%<br>
               <strong>Average Rounds:</strong> {{ "%.1f"|format(avg_rounds) }} rounds<br>
               <strong>Most Common Principle:</strong> {{ most_common_principle }}
           </div>

           <h2>Statistical Analysis</h2>
           <h3>Consensus Analysis</h3>
           <p>Consensus Rate: {{ "%.1f"|format(basic_stats.consensus.rate * 100) }}%</p>
           <p>95% Confidence Interval: {{ basic_stats.consensus.confidence_interval }}</p>

           <h3>Principle Distribution</h3>
           <table>
               <tr><th>Principle</th><th>Frequency</th></tr>
               {% for principle, count in principle_distribution.items() %}
               <tr><td>{{ principle }}</td><td>{{ count }}</td></tr>
               {% endfor %}
           </table>

           <h2>Phase Analysis</h2>
           <h3>Phase 1 Summary</h3>
           <p>{{ phase1_summary }}</p>

           <h3>Phase 2 Summary</h3>
           <p>{{ phase2_summary }}</p>
       </body>
       </html>
       '''

       # Prepare template data
       template_data = {
           'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           'total_experiments': len(results_list),
           'consensus_rate': round(basic_stats['consensus']['rate'] * 100, 1),
           'avg_rounds': sum(extract_basic_metrics(r)['total_rounds'] for r in results_list) / len(results_list),
           'most_common_principle': max(basic_stats['principle_distribution']['counts'].keys(),
                                       key=lambda k: basic_stats['principle_distribution']['counts'][k]),
           'basic_stats': basic_stats,
           'principle_distribution': basic_stats['principle_distribution']['counts'],
           'phase1_summary': phase1_analysis,
           'phase2_summary': phase2_analysis
       }

       # Render template
       template = Template(template_str)
       html_content = template.render(**template_data)

       # Save report
       with open(output_file, 'w') as f:
           f.write(html_content)

       print(f"Report generated: {output_file}")

   def analyze_phase1_across_experiments(results_list):
       """Summarize Phase 1 patterns across experiments."""
       all_phase1_data = []
       for results in results_list:
           phase1_df = analyze_phase1_responses(results)
           all_phase1_data.append(phase1_df)

       if all_phase1_data:
           combined_df = pd.concat(all_phase1_data)
           top_preferences = combined_df[combined_df['rank'] == 1]['principle'].value_counts()
           return f"Most common initial preference: {top_preferences.index[0]} ({top_preferences.iloc[0]} times)"
       return "No Phase 1 data available"

   def analyze_phase2_across_experiments(results_list):
       """Summarize Phase 2 patterns across experiments."""
       consensus_count = sum(1 for r in results_list if r['general_information']['consensus_reached'])
       avg_rounds = sum(r['general_information']['rounds_conducted_phase_2'] for r in results_list) / len(results_list)

       return f"Consensus achieved in {consensus_count}/{len(results_list)} experiments. Average discussion rounds: {avg_rounds:.1f}"

Best Practices for Analysis
---------------------------

Data Quality Checks
~~~~~~~~~~~~~~~~~~

Always validate your data before analysis:

.. code-block:: python

   def validate_results_quality(results_list):
       """Validate experiment results for analysis quality."""

       quality_issues = []

       for i, results in enumerate(results_list):
           experiment_id = results.get('general_information', {}).get('experiment_id', f'experiment_{i}')

           # Check for required structure
           if 'general_information' not in results:
               quality_issues.append(f"{experiment_id}: Missing general_information")
               continue

           if 'agents' not in results:
               quality_issues.append(f"{experiment_id}: Missing agents data")
               continue

           general_info = results['general_information']

           # Check for consensus data
           if 'consensus_reached' not in general_info:
               quality_issues.append(f"{experiment_id}: Missing consensus data")

           # Check agent data completeness
           for agent_name, agent_data in results['agents'].items():
               if 'phase_1' not in agent_data:
                   quality_issues.append(f"{experiment_id}: Agent {agent_name} missing Phase 1 data")
               if 'phase_2' not in agent_data:
                   quality_issues.append(f"{experiment_id}: Agent {agent_name} missing Phase 2 data")

       return quality_issues

Reproducibility Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~

Ensure your analyses are reproducible:

1. **Version Control**: Track analysis code and configuration files
2. **Random Seeds**: Set random seeds for clustering and sampling
3. **Environment Documentation**: Document Python/package versions
4. **Data Provenance**: Maintain clear links between analyses and source experiments
5. **Parameter Documentation**: Record all analysis parameters and thresholds

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

For large-scale analysis:

.. code-block:: python

   from concurrent.futures import ProcessPoolExecutor

   def parallel_analysis(results_list, analysis_function, n_workers=4):
       """Run analysis in parallel for large datasets."""

       with ProcessPoolExecutor(max_workers=n_workers) as executor:
           futures = [executor.submit(analysis_function, results)
                     for results in results_list]

           results = [future.result() for future in futures]

       return results

For comprehensive analysis examples and advanced techniques, see the ``analysis_examples/`` directory and refer to :doc:`designing-experiments` for systematic experimental design that supports robust analysis.