Analyzing Results
=================

This comprehensive guide shows you how to interpret, analyze, and visualize results from Frohlich Experiments, from basic output understanding to advanced statistical analysis.

Understanding Output Files
---------------------------

Result File Structure
~~~~~~~~~~~~~~~~~~~~~

Each experiment generates a timestamped JSON file with this structure:

.. code-block:: json

   {
     "experiment_id": "uuid-string",
     "configuration": { /* Complete experiment config */ },
     "execution_metadata": {
       "start_time": "2025-08-19T10:51:30Z",
       "end_time": "2025-08-19T10:55:45Z", 
       "duration_seconds": 255,
       "total_api_calls": 47,
       "language": "english"
     },
     "phase1_results": [ /* Individual agent responses */ ],
     "phase2_results": {
       "discussion_rounds": [ /* Group discussion transcript */ ],
       "voting_results": { /* Consensus outcomes */ },
       "payoff_results": { /* Final income calculations */ }
     },
     "error_statistics": { /* Error handling metrics */ },
     "agent_logs": { /* Complete agent interaction logs */ },
     "trace_links": { /* OpenAI platform debugging links */ }
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
       metrics = {
           'experiment_id': results['experiment_id'],
           'duration': results['execution_metadata']['duration_seconds'],
           'consensus_reached': results['phase2_results']['voting_results']['consensus_reached'],
           'final_principle': results['phase2_results']['voting_results'].get('chosen_principle'),
           'total_rounds': len(results['phase2_results']['discussion_rounds']),
           'participant_count': len(results['configuration']['agents']),
           'language': results['execution_metadata']['language']
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
       
       for agent_responses in results['phase1_results']:
           agent_name = agent_responses['agent_name']
           
           for principle, response in agent_responses['responses'].items():
               phase1_data.append({
                   'agent': agent_name,
                   'principle': principle,
                   'chosen_principle': response['chosen_principle'],
                   'confidence': response['confidence_level'],
                   'reasoning_length': len(response.get('reasoning', '')),
                   'constraint_specified': bool(response.get('constraint_amount'))
               })
       
       return pd.DataFrame(phase1_data)

   # Analyze principle preferences
   def phase1_preference_analysis(df):
       """Analyze principle preferences in Phase 1."""
       # Preference distribution
       preference_dist = df.groupby(['agent', 'chosen_principle']).size().unstack(fill_value=0)
       
       # Confidence patterns
       confidence_by_principle = df.groupby('chosen_principle')['confidence'].value_counts()
       
       # Reasoning complexity
       reasoning_stats = df.groupby(['agent', 'chosen_principle'])['reasoning_length'].mean()
       
       return {
           'preferences': preference_dist,
           'confidence_patterns': confidence_by_principle,
           'reasoning_complexity': reasoning_stats
       }

Phase 2 Analysis
~~~~~~~~~~~~~~~~

Analyze group discussion dynamics:

.. code-block:: python

   def analyze_phase2_discussion(results):
       """Analyze Phase 2 group discussion patterns."""
       discussion_data = []
       
       for round_num, round_data in enumerate(results['phase2_results']['discussion_rounds']):
           for turn in round_data['agent_turns']:
               discussion_data.append({
                   'round': round_num + 1,
                   'agent': turn['agent_name'],
                   'speaking_order': turn.get('speaking_order', 0),
                   'message_length': len(turn['message']),
                   'mentions_other_agents': count_agent_mentions(turn['message'], results),
                   'principle_mentioned': extract_principle_mentions(turn['message'])
               })
       
       return pd.DataFrame(discussion_data)

   def count_agent_mentions(message, results):
       """Count how often other agents are mentioned."""
       agent_names = [agent['name'] for agent in results['configuration']['agents']]
       mentions = sum(1 for name in agent_names if name.lower() in message.lower())
       return mentions

   def extract_principle_mentions(message):
       """Extract which principles are mentioned in message."""
       principles = ['maximizing floor', 'maximizing average', 'floor constraint', 'range constraint']
       mentioned = [p for p in principles if p in message.lower()]
       return mentioned

Consensus Analysis
~~~~~~~~~~~~~~~~~

Analyze how consensus is achieved:

.. code-block:: python

   def analyze_consensus_formation(results):
       """Analyze how consensus forms over discussion rounds."""
       voting_data = results['phase2_results']['voting_results']
       
       consensus_metrics = {
           'consensus_achieved': voting_data['consensus_reached'],
           'rounds_to_consensus': voting_data.get('rounds_to_consensus', 0),
           'final_principle': voting_data.get('chosen_principle'),
           'vote_distribution': voting_data.get('final_vote_counts', {}),
           'principle_switches': count_principle_switches(results),
           'unanimous_consensus': is_unanimous_consensus(voting_data)
       }
       
       return consensus_metrics

   def count_principle_switches(results):
       """Count how many agents switched principles during discussion."""
       # Compare Phase 1 preferences with final Phase 2 choices
       phase1_prefs = extract_phase1_final_preferences(results)
       phase2_choice = results['phase2_results']['voting_results'].get('chosen_principle')
       
       switches = sum(1 for pref in phase1_prefs.values() if pref != phase2_choice)
       return switches

   def is_unanimous_consensus(voting_data):
       """Check if consensus was unanimous."""
       if not voting_data.get('final_vote_counts'):
           return False
       
       vote_counts = voting_data['final_vote_counts']
       return len([count for count in vote_counts.values() if count > 0]) == 1

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
       chi2_stat, p_value = chi2_contingency([principle_counts.values, [len(df)/4]*4])
       
       analyses['principle_distribution'] = {
           'counts': principle_counts.to_dict(),
           'chi2_test': {'statistic': chi2_stat, 'p_value': p_value},
           'uniform_distribution': p_value > 0.05
       }
       
       # Duration analysis
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

   def compare_conditions(condition_a_results, condition_b_results, condition_names=["A", "B"]):
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
       
       # Duration comparison
       duration_comparison = mannwhitneyu(df_a['duration'], df_b['duration'], alternative='two-sided')
       
       comparison['duration_test'] = {
           'condition_a_median': df_a['duration'].median(),
           'condition_b_median': df_b['duration'].median(),
           'mann_whitney_u': duration_comparison.statistic,
           'p_value': duration_comparison.pvalue,
           'significant_difference': duration_comparison.pvalue < 0.05
       }
       
       # Principle preference comparison
       principles_a = df_a['final_principle'].value_counts(normalize=True)
       principles_b = df_b['final_principle'].value_counts(normalize=True)
       
       comparison['principle_preferences'] = {
           condition_names[0]: principles_a.to_dict(),
           condition_names[1]: principles_b.to_dict()
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
   
   def create_standard_plots(results_list, save_dir="plots/"):
       """Create standard visualization suite."""
       
       # Prepare data
       metrics_list = [extract_basic_metrics(r) for r in results_list]
       df = pd.DataFrame(metrics_list)
       
       # Set up plotting style
       plt.style.use('seaborn-v0_8')
       fig, axes = plt.subplots(2, 2, figsize=(15, 12))
       
       # 1. Consensus Rate
       consensus_counts = df['consensus_reached'].value_counts()
       axes[0,0].pie(consensus_counts.values, labels=['No Consensus', 'Consensus'], autopct='%1.1f%%')
       axes[0,0].set_title('Consensus Achievement Rate')
       
       # 2. Principle Distribution
       principle_counts = df['final_principle'].value_counts()
       axes[0,1].bar(range(len(principle_counts)), principle_counts.values)
       axes[0,1].set_xticks(range(len(principle_counts)))
       axes[0,1].set_xticklabels(principle_counts.index, rotation=45)
       axes[0,1].set_title('Final Principle Distribution')
       axes[0,1].set_ylabel('Frequency')
       
       # 3. Duration Distribution
       axes[1,0].hist(df['duration'], bins=20, alpha=0.7)
       axes[1,0].set_title('Experiment Duration Distribution')
       axes[1,0].set_xlabel('Duration (seconds)')
       axes[1,0].set_ylabel('Frequency')
       
       # 4. Rounds vs Consensus
       consensus_df = df[df['consensus_reached'] == True]
       no_consensus_df = df[df['consensus_reached'] == False]
       
       axes[1,1].scatter(consensus_df['total_rounds'], consensus_df['duration'], 
                        alpha=0.6, label='Consensus', color='green')
       axes[1,1].scatter(no_consensus_df['total_rounds'], no_consensus_df['duration'], 
                        alpha=0.6, label='No Consensus', color='red')
       axes[1,1].set_title('Discussion Rounds vs Duration')
       axes[1,1].set_xlabel('Total Rounds')
       axes[1,1].set_ylabel('Duration (seconds)')
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

   def create_interactive_dashboard(results_list):
       """Create interactive dashboard for experiment analysis."""
       
       # Prepare data
       all_data = []
       for i, results in enumerate(results_list):
           metrics = extract_basic_metrics(results)
           metrics['experiment_num'] = i + 1
           
           # Add Phase 1 data
           phase1_df = analyze_phase1_responses(results)
           metrics['phase1_preference_diversity'] = len(phase1_df['chosen_principle'].unique())
           
           # Add Phase 2 data
           phase2_df = analyze_phase2_discussion(results)
           metrics['avg_message_length'] = phase2_df['message_length'].mean()
           metrics['total_messages'] = len(phase2_df)
           
           all_data.append(metrics)
       
       df = pd.DataFrame(all_data)
       
       # Create subplots
       fig = make_subplots(
           rows=2, cols=2,
           subplot_titles=('Consensus vs Duration', 'Principle Preferences', 
                          'Message Activity', 'Experiment Timeline'),
           specs=[[{"secondary_y": False}, {"type": "bar"}],
                  [{"secondary_y": True}, {"type": "scatter"}]]
       )
       
       # 1. Consensus vs Duration (scatter)
       consensus_color = df['consensus_reached'].map({True: 'green', False: 'red'})
       fig.add_trace(
           go.Scatter(x=df['duration'], y=df['total_rounds'],
                     mode='markers',
                     marker=dict(color=consensus_color, size=10),
                     text=df['final_principle'],
                     hovertemplate="Duration: %{x}s<br>Rounds: %{y}<br>Principle: %{text}",
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
       
       # 3. Message Activity (dual axis)
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
       
       # 4. Timeline view
       fig.add_trace(
           go.Scatter(x=df['experiment_num'], y=df['duration'],
                     mode='lines+markers',
                     marker=dict(size=df['participant_count']*5),
                     name="Duration Timeline"),
           row=2, col=2
       )
       
       # Update layout
       fig.update_layout(height=800, showlegend=True, 
                        title_text="Frohlich Experiment Analysis Dashboard")
       
       fig.show()
       
       return fig

Time Series Analysis
~~~~~~~~~~~~~~~~~~~

Analyze experiments conducted over time:

.. code-block:: python

   def time_series_analysis(results_list):
       """Analyze trends in experiment results over time."""
       
       time_data = []
       for results in results_list:
           metrics = extract_basic_metrics(results)
           # Extract timestamp from results
           timestamp = results['execution_metadata']['start_time']
           metrics['timestamp'] = pd.to_datetime(timestamp)
           time_data.append(metrics)
       
       df = pd.DataFrame(time_data).sort_values('timestamp')
       
       # Calculate rolling averages
       df['consensus_rate_rolling'] = df['consensus_reached'].rolling(window=5, min_periods=1).mean()
       df['duration_rolling'] = df['duration'].rolling(window=5, min_periods=1).mean()
       
       # Create time series plot
       fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
       
       # Consensus rate over time
       ax1.plot(df['timestamp'], df['consensus_rate_rolling'], 'b-', linewidth=2, label='Rolling Average')
       ax1.scatter(df['timestamp'], df['consensus_reached'], alpha=0.5, color='blue')
       ax1.set_ylabel('Consensus Rate')
       ax1.set_title('Experiment Performance Over Time')
       ax1.legend()
       ax1.grid(True, alpha=0.3)
       
       # Duration over time
       ax2.plot(df['timestamp'], df['duration_rolling'], 'r-', linewidth=2, label='Rolling Average')
       ax2.scatter(df['timestamp'], df['duration'], alpha=0.5, color='red')
       ax2.set_ylabel('Duration (seconds)')
       ax2.set_xlabel('Time')
       ax2.legend()
       ax2.grid(True, alpha=0.3)
       
       plt.tight_layout()
       plt.xticks(rotation=45)
       plt.show()
       
       return df

Advanced Research Analysis
--------------------------

Agent Behavior Modeling
~~~~~~~~~~~~~~~~~~~~~~

Model individual agent decision patterns:

.. code-block:: python

   from sklearn.cluster import KMeans
   from sklearn.preprocessing import StandardScaler

   def agent_behavior_clustering(results_list):
       """Cluster agents based on behavior patterns."""
       
       # Extract agent features across all experiments
       agent_features = []
       for results in results_list:
           phase1_df = analyze_phase1_responses(results)
           
           for agent in phase1_df['agent'].unique():
               agent_data = phase1_df[phase1_df['agent'] == agent]
               
               features = {
                   'agent_name': agent,
                   'experiment_id': results['experiment_id'],
                   'avg_confidence': agent_data['confidence'].map({'low': 1, 'medium': 2, 'high': 3}).mean(),
                   'reasoning_complexity': agent_data['reasoning_length'].mean(),
                   'principle_consistency': calculate_principle_consistency(agent_data),
                   'constraint_usage': agent_data['constraint_specified'].mean()
               }
               agent_features.append(features)
       
       df = pd.DataFrame(agent_features)
       
       # Prepare features for clustering
       feature_cols = ['avg_confidence', 'reasoning_complexity', 'principle_consistency', 'constraint_usage']
       X = df[feature_cols].fillna(0)
       
       # Standardize features
       scaler = StandardScaler()
       X_scaled = scaler.fit_transform(X)
       
       # Perform clustering
       kmeans = KMeans(n_clusters=3, random_state=42)
       df['cluster'] = kmeans.fit_predict(X_scaled)
       
       # Analyze clusters
       cluster_analysis = df.groupby('cluster')[feature_cols].mean()
       
       return df, cluster_analysis

   def calculate_principle_consistency(agent_data):
       """Calculate how consistent an agent is in principle choice."""
       if len(agent_data) <= 1:
           return 1.0
       
       most_common_principle = agent_data['chosen_principle'].mode().iloc[0]
       consistency = (agent_data['chosen_principle'] == most_common_principle).mean()
       return consistency

Network Analysis
~~~~~~~~~~~~~~~

Analyze agent interaction patterns in group discussions:

.. code-block:: python

   import networkx as nx

   def create_interaction_network(results):
       """Create network graph of agent interactions."""
       
       # Initialize network
       G = nx.Graph()
       
       # Add nodes (agents)
       agent_names = [agent['name'] for agent in results['configuration']['agents']]
       G.add_nodes_from(agent_names)
       
       # Analyze Phase 2 discussions for interactions
       for round_data in results['phase2_results']['discussion_rounds']:
           previous_speaker = None
           
           for turn in round_data['agent_turns']:
               current_speaker = turn['agent_name']
               
               # Add edge for direct response (speaking after someone)
               if previous_speaker and previous_speaker != current_speaker:
                   if G.has_edge(previous_speaker, current_speaker):
                       G[previous_speaker][current_speaker]['weight'] += 1
                   else:
                       G.add_edge(previous_speaker, current_speaker, weight=1)
               
               # Add edges for explicit mentions
               for other_agent in agent_names:
                   if other_agent != current_speaker and other_agent.lower() in turn['message'].lower():
                       if G.has_edge(current_speaker, other_agent):
                           G[current_speaker][other_agent]['mentions'] = G[current_speaker][other_agent].get('mentions', 0) + 1
                       else:
                           G.add_edge(current_speaker, other_agent, mentions=1)
               
               previous_speaker = current_speaker
       
       return G

   def analyze_network_properties(G):
       """Analyze network properties and centrality measures."""
       
       analysis = {
           'nodes': G.number_of_nodes(),
           'edges': G.number_of_edges(),
           'density': nx.density(G),
           'clustering': nx.average_clustering(G),
           'centrality': {
               'degree': nx.degree_centrality(G),
               'betweenness': nx.betweenness_centrality(G),
               'closeness': nx.closeness_centrality(G),
               'eigenvector': nx.eigenvector_centrality(G)
           }
       }
       
       return analysis

Report Generation
-----------------

Automated Analysis Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate comprehensive analysis reports:

.. code-block:: python

   def generate_experiment_report(results_list, output_file="experiment_report.html"):
       """Generate comprehensive HTML report."""
       
       from jinja2 import Template
       
       # Perform all analyses
       basic_stats = statistical_analysis_suite(results_list)
       phase1_summary = summarize_phase1_across_experiments(results_list)
       phase2_summary = summarize_phase2_across_experiments(results_list)
       
       # Create visualizations
       overview_plots = create_standard_plots(results_list, save_dir="report_plots/")
       
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
               <strong>Consensus Rate:</strong> {{ consensus_rate }}%<br>
               <strong>Average Duration:</strong> {{ avg_duration }} seconds<br>
               <strong>Most Common Principle:</strong> {{ most_common_principle }}
           </div>
           
           <h2>Statistical Analysis</h2>
           <h3>Consensus Analysis</h3>
           <p>Consensus Rate: {{ basic_stats.consensus.rate * 100 }}%</p>
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
           {{ phase1_summary }}
           
           <h3>Phase 2 Summary</h3>
           {{ phase2_summary }}
           
           <div class="chart">
               <img src="report_plots/experiment_overview.png" alt="Experiment Overview">
           </div>
       </body>
       </html>
       '''
       
       # Prepare template data
       template_data = {
           'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           'total_experiments': len(results_list),
           'consensus_rate': round(basic_stats['consensus']['rate'] * 100, 1),
           'avg_duration': round(basic_stats['duration']['mean'], 1),
           'most_common_principle': max(basic_stats['principle_distribution']['counts'].keys(),
                                       key=lambda k: basic_stats['principle_distribution']['counts'][k]),
           'basic_stats': basic_stats,
           'principle_distribution': basic_stats['principle_distribution']['counts'],
           'phase1_summary': phase1_summary,
           'phase2_summary': phase2_summary
       }
       
       # Render template
       template = Template(template_str)
       html_content = template.render(**template_data)
       
       # Save report
       with open(output_file, 'w') as f:
           f.write(html_content)
       
       print(f"Report generated: {output_file}")

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
           experiment_id = results.get('experiment_id', f'experiment_{i}')
           
           # Check for incomplete experiments
           if not results.get('phase2_results'):
               quality_issues.append(f"{experiment_id}: Missing Phase 2 results")
           
           # Check for high error rates
           error_stats = results.get('error_statistics', {})
           total_errors = sum(error_stats.values()) if error_stats else 0
           if total_errors > 10:
               quality_issues.append(f"{experiment_id}: High error count ({total_errors})")
           
           # Check for consensus data quality
           if results.get('phase2_results', {}).get('voting_results', {}).get('consensus_reached') is None:
               quality_issues.append(f"{experiment_id}: Missing consensus data")
       
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

   # Use efficient data structures
   import numpy as np
   from concurrent.futures import ProcessPoolExecutor

   def parallel_analysis(results_list, analysis_function, n_workers=4):
       """Run analysis in parallel for large datasets."""
       
       with ProcessPoolExecutor(max_workers=n_workers) as executor:
           futures = [executor.submit(analysis_function, results) 
                     for results in results_list]
           
           results = [future.result() for future in futures]
       
       return results

For comprehensive analysis examples and advanced techniques, see the ``analysis_examples/`` directory and refer to :doc:`designing-experiments` for systematic experimental design that supports robust analysis.