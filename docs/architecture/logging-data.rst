Logging and Data Output
=======================

The Frohlich Experiment system provides comprehensive logging and data output capabilities designed for both real-time monitoring and post-experiment analysis. This section details all logging mechanisms, data formats, and analysis tools.

Logging Architecture
--------------------

Multi-Layer Logging System
~~~~~~~~~~~~~~~~~~~~~~~~~~

The system implements a sophisticated logging architecture with multiple complementary systems:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                   Logging Architecture                      │
   ├─────────────────────────────────────────────────────────────┤
   │  1. Agent-Centric Logger    │  Complete agent interactions │
   │  2. OpenAI Tracing          │  Platform-level debugging    │
   │  3. System Logging          │  Infrastructure monitoring   │
   │  4. Error Statistics        │  Failure tracking & recovery │
   │  5. Performance Metrics     │  Timing & resource usage     │
   └─────────────────────────────────────────────────────────────┘

**Key Design Principles:**
- **Agent-Centric**: Focus on agent behaviors and interactions
- **Structured Data**: JSON-formatted for machine processing  
- **Human Readable**: Clear formatting for manual inspection
- **Multi-Level**: From detailed traces to high-level summaries
- **Error Recovery**: Comprehensive error categorization and tracking

Agent-Centric Logging
~~~~~~~~~~~~~~~~~~~~~

The core logging system tracks all agent inputs, outputs, and state changes:

.. code-block:: python

   # Agent-centric logger structure
   class AgentCentricLogger:
       """Comprehensive logging of agent behaviors and interactions."""
       
       def log_agent_input(self, agent_name: str, input_data: dict):
           """Log input to agent (prompts, context, etc.)"""
           
       def log_agent_output(self, agent_name: str, output_data: dict):  
           """Log output from agent (responses, decisions, etc.)"""
           
       def log_agent_memory_update(self, agent_name: str, memory_data: dict):
           """Log agent memory changes"""
           
       def log_phase_transition(self, phase: str, participants: list):
           """Log phase changes and participant states"""

**Logged Data Categories:**

.. code-block:: json

   {
     "agent_logs": {
       "Agent_1": [
         {
           "timestamp": "2025-08-19T10:51:30Z",
           "type": "input",
           "phase": "phase1",
           "principle": "maximizing_floor", 
           "input_data": { /* Complete input context */ },
           "session_id": "uuid-string"
         },
         {
           "timestamp": "2025-08-19T10:51:45Z",
           "type": "output",
           "phase": "phase1",
           "principle": "maximizing_floor",
           "output_data": { /* Agent response data */ },
           "processing_time_ms": 15234
         }
       ]
     }
   }

Experiment Results Structure
----------------------------

Complete JSON Output
~~~~~~~~~~~~~~~~~~~

Each experiment generates a comprehensive JSON file with this structure:

.. code-block:: json

   {
     "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
     "configuration": {
       "language": "english",
       "agents": [ /* Complete agent configurations */ ],
       "phase2_rounds": 10,
       "original_values_mode": { /* Mode configuration */ }
     },
     "execution_metadata": {
       "start_time": "2025-08-19T10:51:30Z",
       "end_time": "2025-08-19T10:55:45Z",
       "duration_seconds": 255,
       "total_api_calls": 47,
       "total_tokens_used": 15234,
       "language": "english",
       "system_version": "1.0.0",
       "model_providers_used": ["openai", "openrouter"]
     },
     "phase1_results": [ /* Individual agent responses */ ],
     "phase2_results": { /* Group discussion and consensus */ },
     "error_statistics": { /* Comprehensive error tracking */ },
     "agent_logs": { /* Complete agent interaction logs */ },
     "trace_links": { /* OpenAI platform debugging links */ },
     "analysis_metadata": { /* Computed metrics and summaries */ }
   }

Phase 1 Results Format
~~~~~~~~~~~~~~~~~~~~~

Individual agent familiarization data:

.. code-block:: json

   {
     "phase1_results": [
       {
         "agent_name": "Agent_1",
         "agent_personality": "Analytical and methodical...",
         "responses": {
           "maximizing_floor": {
             "chosen_principle": "a",
             "confidence_level": "high",
             "reasoning": "Detailed reasoning text...",
             "constraint_amount": null,
             "response_time_seconds": 12.5,
             "memory_state_summary": "Current memory contents...",
             "validation_passed": true
           },
           "maximizing_average": {
             /* Similar structure for each principle */
           }
         },
         "principle_rankings": {
           "first_choice": "a",
           "second_choice": "c", 
           "third_choice": "b",
           "fourth_choice": "d",
           "ranking_confidence": "medium"
         },
         "memory_evolution": [
           {
             "after_principle": "maximizing_floor",
             "memory_length": 1234,
             "key_concepts_learned": ["floor income", "worst-off protection"]
           }
         ]
       }
     ]
   }

Phase 2 Results Format
~~~~~~~~~~~~~~~~~~~~~

Group discussion and consensus data:

.. code-block:: json

   {
     "phase2_results": {
       "discussion_rounds": [
         {
           "round_number": 1,
           "income_distribution": {
             "high": 100, "medium_high": 80, 
             "medium": 60, "medium_low": 40, "low": 20
           },
           "agent_turns": [
             {
               "agent_name": "Agent_1",
               "speaking_order": 2,
               "message": "I believe we should focus on maximizing floor income...",
               "message_length": 156,
               "mentions_other_agents": ["Agent_2"],
               "principles_referenced": ["maximizing_floor"],
               "response_time_seconds": 8.3
             }
           ],
           "round_summary": {
             "dominant_themes": ["floor income protection", "efficiency concerns"],
             "consensus_indicators": ["agreement on minimum standards"],
             "disagreement_points": ["constraint specification"]
           }
         }
       ],
       "voting_results": {
         "consensus_reached": true,
         "chosen_principle": "c",
         "constraint_amount": 25,
         "rounds_to_consensus": 7,
         "final_vote_counts": {"a": 0, "b": 0, "c": 3, "d": 0},
         "voting_history": [
           {"round": 1, "votes": {"a": 1, "b": 1, "c": 1, "d": 0}},
           {"round": 2, "votes": {"a": 1, "b": 0, "c": 2, "d": 0}}
         ]
       },
       "payoff_results": {
         "Agent_1": {"income_class": "medium", "income_amount": 60, "payoff": 60},
         "Agent_2": {"income_class": "low", "income_amount": 25, "payoff": 25},
         "Agent_3": {"income_class": "high", "income_amount": 100, "payoff": 100}
       },
       "discussion_analytics": {
         "total_messages": 42,
         "average_message_length": 127.5,
         "participation_distribution": {"Agent_1": 14, "Agent_2": 15, "Agent_3": 13},
         "principle_mention_frequency": {"a": 8, "b": 12, "c": 18, "d": 4},
         "consensus_progression_score": 0.85
       }
     }
   }

Error Tracking and Statistics
-----------------------------

Comprehensive Error Categorization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All errors are categorized and tracked for analysis:

.. code-block:: json

   {
     "error_statistics": {
       "total_errors": 3,
       "errors_by_category": {
         "memory_errors": 1,
         "validation_errors": 2,
         "communication_errors": 0,
         "system_errors": 0,
         "experiment_logic_errors": 0
       },
       "errors_by_severity": {
         "low": 2,
         "medium": 1,
         "high": 0,
         "critical": 0
       },
       "recovery_statistics": {
         "successful_retries": 3,
         "failed_retries": 0,
         "total_retry_attempts": 8
       },
       "error_details": [
         {
           "timestamp": "2025-08-19T10:52:15Z",
           "category": "memory_errors", 
           "severity": "medium",
           "agent": "Agent_2",
           "description": "Memory limit exceeded",
           "recovery_action": "Memory cleanup successful",
           "retry_count": 2,
           "resolved": true
         }
       ]
     }
   }

Error Recovery Mechanisms
~~~~~~~~~~~~~~~~~~~~~~~~

The system implements sophisticated error recovery:

**Memory Errors:**
- Automatic memory cleanup and retry
- Configurable retry limits (default: 5 attempts)
- Exponential backoff between retries
- Graceful degradation if recovery fails

**API Errors:**
- Rate limit handling with backoff
- Model unavailability fallbacks
- Network timeout recovery
- Cost limit protections

**Validation Errors:**
- Response format correction attempts
- Constraint specification validation
- Multi-language parsing error handling
- Clear error messages for debugging

Real-Time Monitoring
--------------------

Console Output
~~~~~~~~~~~~~

Real-time experiment progress tracking:

.. code-block:: text

   Starting Frohlich Experiment...
   ═══════════════════════════════════════════════
   Experiment ID: 550e8400-e29b-41d4-a716-446655440000
   Language: English
   Participants: 3 agents
   Configuration: default_config.yaml
   
   Initializing Agents...
   ✅ Agent_1 (gpt-4.1-mini) initialized [2.3s]
   ✅ Agent_2 (google/gemini-2.5-flash) initialized [1.8s]  
   ✅ Agent_3 (gpt-4.1-mini) initialized [2.1s]
   
   Phase 1: Individual Familiarization (Parallel)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Agent_1: Principle A ✅ | Principle B ✅ | Principle C ✅ | Principle D ✅
   Agent_2: Principle A ✅ | Principle B ✅ | Principle C ✅ | Principle D ✅
   Agent_3: Principle A ✅ | Principle B ✅ | Principle C ✅ | Principle D ✅
   Phase 1 completed in 45.6s
   
   Phase 2: Group Discussion (Sequential)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Round 1: Agent_2 → Agent_1 → Agent_3 [Discussion: 23.4s]
   Round 2: Agent_3 → Agent_2 → Agent_1 [Discussion: 19.8s]
   Round 3: Agent_1 → Agent_3 → Agent_2 [Discussion: 21.2s]
   ...
   Round 7: Consensus reached on Principle C (constraint: 25)
   Phase 2 completed in 142.8s
   
   Experiment Summary:
   ═══════════════════════════════════════════════
   Duration: 4m 15s
   Consensus: ✅ Principle C (Maximizing average with floor constraint)
   Payoffs: Agent_1: $60 | Agent_2: $25 | Agent_3: $100
   Errors: 3 (all recovered)
   Results: experiment_results_20250819_105130.json
   Trace: https://platform.openai.com/traces/exp-550e8400-e29b

Performance Metrics
~~~~~~~~~~~~~~~~~~~

Detailed performance tracking:

.. code-block:: json

   {
     "performance_metrics": {
       "timing": {
         "total_experiment_duration": 255.6,
         "phase1_duration": 45.6,
         "phase2_duration": 142.8,
         "initialization_duration": 6.2,
         "finalization_duration": 1.0
       },
       "resource_usage": {
         "total_api_calls": 47,
         "total_tokens_used": 15234,
         "average_tokens_per_call": 324,
         "estimated_cost_usd": 2.45
       },
       "agent_performance": {
         "Agent_1": {
           "response_times": [12.5, 8.3, 9.1, 7.8],
           "average_response_time": 9.4,
           "memory_usage_final": 23456,
           "api_calls": 16
         }
       },
       "system_performance": {
         "memory_usage_peak_mb": 245,
         "cpu_usage_peak_percent": 15.3,
         "parallel_efficiency": 0.87
       }
     }
   }

OpenAI Platform Integration
---------------------------

Trace Link Generation
~~~~~~~~~~~~~~~~~~~~

Every experiment generates OpenAI trace links for detailed debugging:

.. code-block:: json

   {
     "trace_links": {
       "experiment_trace": "https://platform.openai.com/traces/exp-550e8400-e29b",
       "phase1_traces": {
         "Agent_1": "https://platform.openai.com/traces/agent1-phase1-abc123",
         "Agent_2": "https://platform.openai.com/traces/agent2-phase1-def456"
       },
       "phase2_traces": {
         "discussion": "https://platform.openai.com/traces/discussion-ghi789"
       }
     }
   }

**Trace Contents:**
- Complete conversation histories
- Token usage breakdowns
- Response timing information
- Model parameter details
- Error occurrences and recovery

Platform Navigation
~~~~~~~~~~~~~~~~~~~

**Accessing Traces:**

1. **From Results JSON**: Copy trace URL from ``trace_links`` section
2. **OpenAI Platform**: Visit https://platform.openai.com/traces  
3. **Experiment View**: Search by experiment ID or timestamp
4. **Agent-Specific**: Filter by agent name or phase

**Trace Analysis Features:**
- Conversation replay with timing
- Token cost analysis
- Performance bottleneck identification
- Error pattern analysis
- Model behavior comparison

Data Analysis Integration
-------------------------

Pandas Integration
~~~~~~~~~~~~~~~~~

Results are designed for easy analysis with pandas:

.. code-block:: python

   import json
   import pandas as pd

   def load_experiment_data(json_path):
       """Load experiment results into analysis-friendly format."""
       
       with open(json_path, 'r') as f:
           data = json.load(f)
       
       # Phase 1 analysis DataFrame
       phase1_rows = []
       for agent_result in data['phase1_results']:
           agent_name = agent_result['agent_name']
           for principle, response in agent_result['responses'].items():
               phase1_rows.append({
                   'agent': agent_name,
                   'principle': principle,
                   'chosen_principle': response['chosen_principle'],
                   'confidence': response['confidence_level'],
                   'response_time': response['response_time_seconds'],
                   'reasoning_length': len(response['reasoning'])
               })
       
       phase1_df = pd.DataFrame(phase1_rows)
       
       # Phase 2 analysis DataFrame  
       phase2_rows = []
       for round_num, round_data in enumerate(data['phase2_results']['discussion_rounds']):
           for turn in round_data['agent_turns']:
               phase2_rows.append({
                   'round': round_num + 1,
                   'agent': turn['agent_name'],
                   'speaking_order': turn['speaking_order'],
                   'message_length': turn['message_length'],
                   'response_time': turn['response_time_seconds']
               })
       
       phase2_df = pd.DataFrame(phase2_rows)
       
       return phase1_df, phase2_df, data

Time Series Analysis
~~~~~~~~~~~~~~~~~~~

Multi-experiment longitudinal analysis:

.. code-block:: python

   def create_experiment_timeline(experiment_files):
       """Create timeline analysis across multiple experiments."""
       
       timeline_data = []
       
       for file_path in experiment_files:
           with open(file_path, 'r') as f:
               data = json.load(f)
           
           timeline_data.append({
               'experiment_id': data['experiment_id'],
               'timestamp': data['execution_metadata']['start_time'],
               'duration': data['execution_metadata']['duration_seconds'],
               'consensus_reached': data['phase2_results']['voting_results']['consensus_reached'],
               'chosen_principle': data['phase2_results']['voting_results'].get('chosen_principle'),
               'total_errors': data['error_statistics']['total_errors'],
               'agent_count': len(data['configuration']['agents'])
           })
       
       df = pd.DataFrame(timeline_data)
       df['timestamp'] = pd.to_datetime(df['timestamp'])
       df = df.sort_values('timestamp')
       
       return df

Export and Integration
---------------------

CSV Export
~~~~~~~~~~

Convert results to CSV for external analysis:

.. code-block:: python

   def export_to_csv(json_path, output_dir="csv_exports/"):
       """Export experiment results to CSV files."""
       
       phase1_df, phase2_df, full_data = load_experiment_data(json_path)
       
       experiment_id = full_data['experiment_id'][:8]  # Short ID
       
       # Export phase data
       phase1_df.to_csv(f"{output_dir}/phase1_{experiment_id}.csv", index=False)
       phase2_df.to_csv(f"{output_dir}/phase2_{experiment_id}.csv", index=False)
       
       # Export summary metrics
       summary_data = {
           'experiment_id': full_data['experiment_id'],
           'consensus_reached': full_data['phase2_results']['voting_results']['consensus_reached'],
           'chosen_principle': full_data['phase2_results']['voting_results'].get('chosen_principle'),
           'duration_seconds': full_data['execution_metadata']['duration_seconds'],
           'total_errors': full_data['error_statistics']['total_errors']
       }
       
       summary_df = pd.DataFrame([summary_data])
       summary_df.to_csv(f"{output_dir}/summary_{experiment_id}.csv", index=False)

Database Integration
~~~~~~~~~~~~~~~~~~~

Store results in databases for large-scale analysis:

.. code-block:: python

   import sqlite3
   
   def create_experiment_database(db_path="experiments.db"):
       """Create SQLite database for experiment storage."""
       
       conn = sqlite3.connect(db_path)
       cursor = conn.cursor()
       
       # Experiments table
       cursor.execute('''
           CREATE TABLE IF NOT EXISTS experiments (
               experiment_id TEXT PRIMARY KEY,
               start_time TEXT,
               duration_seconds INTEGER,
               consensus_reached BOOLEAN,
               chosen_principle TEXT,
               total_errors INTEGER,
               agent_count INTEGER
           )
       ''')
       
       # Agent responses table
       cursor.execute('''
           CREATE TABLE IF NOT EXISTS agent_responses (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               experiment_id TEXT,
               agent_name TEXT,
               phase INTEGER,
               principle TEXT,
               chosen_principle TEXT,
               confidence TEXT,
               response_time REAL,
               FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id)
           )
       ''')
       
       conn.commit()
       conn.close()

Data Retention and Management
----------------------------

File Organization
~~~~~~~~~~~~~~~~

Recommended structure for experiment data management:

.. code-block:: text

   experiment_data/
   ├── raw_results/
   │   ├── 2025-08/
   │   │   ├── experiment_results_20250819_105130.json
   │   │   └── experiment_results_20250819_110245.json
   │   └── 2025-09/
   ├── processed/
   │   ├── csv_exports/
   │   ├── summary_reports/
   │   └── statistical_analyses/
   ├── archives/
   │   └── compressed_2024/
   └── backups/
       └── weekly_backups/

Automated Data Management
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def organize_experiment_files(source_dir=".", target_dir="experiment_data/"):
       """Automatically organize experiment result files."""
       
       import shutil
       from datetime import datetime
       from pathlib import Path
       
       source_path = Path(source_dir)
       target_path = Path(target_dir)
       
       # Find all experiment result files
       result_files = source_path.glob("experiment_results_*.json")
       
       for file_path in result_files:
           # Extract date from filename
           filename = file_path.name
           date_str = filename.split('_')[2]  # YYYYMMDD
           
           # Create date-based directory
           year_month = f"{date_str[:4]}-{date_str[4:6]}"
           dest_dir = target_path / "raw_results" / year_month
           dest_dir.mkdir(parents=True, exist_ok=True)
           
           # Move file
           dest_file = dest_dir / filename
           shutil.move(str(file_path), str(dest_file))
           
           print(f"Organized: {filename} → {dest_file}")

For detailed examples of data analysis workflows and visualization techniques, refer to :doc:`../user-guide/analyzing-results` and the analysis examples in the ``analysis_examples/`` directory.