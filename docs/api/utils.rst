Utility Modules
===============

The utility modules provide essential supporting functionality for the Frohlich Experiment system, including memory management, error handling, logging, multi-language support, and experimental orchestration. This comprehensive guide covers all utility components with practical examples and integration patterns.

.. contents:: Table of Contents
   :local:
   :depth: 2

Utility Architecture Overview
-----------------------------

The utility modules form the supporting infrastructure that enables the core experimental functionality.

.. mermaid::

   graph TB
       subgraph "Memory Management"
           MM[Memory Manager]
           MC[Memory Compression]
           MV[Memory Validation]
       end
       
       subgraph "Error Handling"
           EH[Error Handler]
           RC[Retry Controller]
           ES[Error Statistics]
       end
       
       subgraph "Logging System"
           ACL[Agent-Centric Logger]
           EL[Event Logger]
           TL[Trace Logger]
       end
       
       subgraph "Multi-Language Support"
           LM[Language Manager]
           PT[Prompt Templates]
           TR[Translation Registry]
       end
       
       subgraph "Model Integration"
           MP[Model Provider]
           AP[API Manager]
           LP[LiteLLM Provider]
       end
       
       subgraph "Experiment Orchestration"
           ER[Experiment Runner]
           CG[Config Generator]
           BR[Batch Runner]
       end
       
       MM --> MC
       MM --> MV
       EH --> RC
       EH --> ES
       ACL --> EL
       ACL --> TL
       LM --> PT
       LM --> TR
       MP --> AP
       MP --> LP
       ER --> CG
       ER --> BR

Memory Manager
--------------

The memory manager handles agent memory allocation, compression, and optimization throughout experiments.

.. automodule:: utils.memory_manager
   :members:
   :undoc-members:
   :show-inheritance:

Core Memory Management
~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Usage

      .. code-block:: python

         from utils.memory_manager import MemoryManager, MemoryConfiguration

         # Create memory manager for an agent
         memory_config = MemoryConfiguration(
             character_limit=50000,
             guidance_style="structured",  # or "narrative"
             compression_threshold=0.9,  # Compress at 90% capacity
             min_retained_ratio=0.7  # Retain 70% after compression
         )
         
         memory_manager = MemoryManager(memory_config)
         
         # Add memory entries
         memory_manager.add_memory_entry(
             step_type="principle_application",
             input_data="Justice principle evaluation task",
             output_data="Selected maximizing floor principle",
             reasoning="This principle best protects vulnerable populations"
         )
         
         # Get current memory state
         current_memory = memory_manager.get_formatted_memory()
         usage_stats = memory_manager.get_usage_statistics()
         
         print(f"Memory usage: {usage_stats['current_characters']}/{usage_stats['character_limit']}")
         print(f"Usage percentage: {usage_stats['usage_percentage']:.1f}%")

   .. tab:: Advanced Memory Management

      .. code-block:: python

         # Create memory manager with custom compression strategy
         class CustomMemoryManager(MemoryManager):
             """Memory manager with domain-specific compression."""
             
             def compress_memory_intelligent(self) -> str:
                 """Compress memory while preserving key justice reasoning."""
                 
                 entries = self.memory_entries
                 
                 # Preserve critical entries
                 critical_entries = [
                     entry for entry in entries 
                     if entry.step_type in ["principle_choice", "final_vote", "consensus"]
                 ]
                 
                 # Summarize less critical entries
                 summarizable_entries = [
                     entry for entry in entries
                     if entry not in critical_entries
                 ]
                 
                 # Create compressed summary
                 summary = self.create_intelligent_summary(summarizable_entries)
                 
                 # Combine critical entries with summary
                 compressed = self.format_compressed_memory(critical_entries, summary)
                 
                 return compressed
         
         # Use custom memory manager
         custom_manager = CustomMemoryManager(memory_config)

   .. tab:: Memory Analytics

      .. code-block:: python

         # Analyze memory patterns across agents
         def analyze_agent_memory_patterns(agents: List[Agent]) -> Dict:
             """Analyze memory usage patterns across agents."""
             
             analysis = {
                 'total_memory_used': 0,
                 'average_memory_per_agent': 0,
                 'memory_efficiency': {},
                 'compression_statistics': {},
                 'content_analysis': {}
             }
             
             for agent in agents:
                 memory_stats = agent.memory_manager.get_usage_statistics()
                 
                 # Track memory usage
                 analysis['total_memory_used'] += memory_stats['current_characters']
                 
                 # Analyze memory efficiency
                 efficiency_ratio = memory_stats['unique_content_ratio']
                 analysis['memory_efficiency'][agent.name] = efficiency_ratio
                 
                 # Track compression events
                 compression_stats = agent.memory_manager.get_compression_history()
                 analysis['compression_statistics'][agent.name] = compression_stats
                 
                 # Content type analysis
                 content_breakdown = agent.memory_manager.analyze_content_types()
                 analysis['content_analysis'][agent.name] = content_breakdown
             
             analysis['average_memory_per_agent'] = analysis['total_memory_used'] / len(agents)
             
             return analysis

**Memory Optimization Strategies**

.. code-block:: python

   # Different memory optimization approaches
   optimization_strategies = {
       "conservative": MemoryConfiguration(
           character_limit=75000,
           compression_threshold=0.85,
           min_retained_ratio=0.80,
           guidance_style="narrative"
       ),
       
       "balanced": MemoryConfiguration(
           character_limit=50000,
           compression_threshold=0.90,
           min_retained_ratio=0.70,
           guidance_style="structured"
       ),
       
       "aggressive": MemoryConfiguration(
           character_limit=30000,
           compression_threshold=0.95,
           min_retained_ratio=0.60,
           guidance_style="bullet_points"
       )
   }

Memory Validation and Recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from utils.memory_manager import MemoryValidationError
   
   # Memory validation and recovery
   def validate_and_recover_memory(memory_manager: MemoryManager) -> bool:
       """Validate memory state and attempt recovery if needed."""
       
       try:
           # Validate memory integrity
           validation_result = memory_manager.validate_memory_integrity()
           
           if not validation_result.is_valid:
               print(f"Memory validation failed: {validation_result.error_message}")
               
               # Attempt automatic recovery
               recovery_success = memory_manager.attempt_memory_recovery()
               
               if recovery_success:
                   print("Memory recovery successful")
                   return True
               else:
                   print("Memory recovery failed, manual intervention required")
                   return False
           
           return True
           
       except MemoryValidationError as e:
           print(f"Critical memory error: {e}")
           return False

Error Handling
--------------

Comprehensive error handling system with automatic retry mechanisms and statistical tracking.

.. automodule:: utils.error_handling
   :members:
   :undoc-members:
   :show-inheritance:

Error Management Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Error Handling

      .. code-block:: python

         from utils.error_handling import (
             ErrorHandler, ErrorCategory, handle_with_retry,
             ExperimentError, AgentError, SystemError
         )
         
         # Create error handler with configuration
         error_handler = ErrorHandler(
             max_retries=3,
             base_delay=1.0,
             max_delay=30.0,
             exponential_base=2.0,
             jitter=True
         )
         
         # Handle errors with automatic retry
         @handle_with_retry(
             max_attempts=3,
             error_categories=[ErrorCategory.COMMUNICATION_ERROR, ErrorCategory.MEMORY_ERROR],
             backoff_factor=2.0
         )
         async def robust_agent_interaction(agent, task_data):
             """Agent interaction with automatic error handling."""
             
             try:
                 response = await agent.process_task(task_data)
                 return response
                 
             except AgentError as e:
                 # Log specific agent error
                 error_handler.log_error(e, ErrorCategory.AGENT_ERROR)
                 raise
                 
             except SystemError as e:
                 # Log system-level error
                 error_handler.log_error(e, ErrorCategory.SYSTEM_ERROR)
                 raise

   .. tab:: Advanced Error Recovery

      .. code-block:: python

         from utils.error_handling import ErrorRecoveryStrategy
         
         class ExperimentErrorRecovery:
             """Specialized error recovery for experiments."""
             
             def __init__(self):
                 self.recovery_strategies = {
                     ErrorCategory.MEMORY_ERROR: self.handle_memory_error,
                     ErrorCategory.VALIDATION_ERROR: self.handle_validation_error,
                     ErrorCategory.COMMUNICATION_ERROR: self.handle_communication_error,
                     ErrorCategory.AGENT_ERROR: self.handle_agent_error
                 }
             
             async def handle_memory_error(self, error, context):
                 """Handle agent memory limit exceeded."""
                 
                 agent = context.get('agent')
                 if agent:
                     # Attempt memory compression
                     compression_success = await agent.compress_memory()
                     
                     if compression_success:
                         return ErrorRecoveryStrategy.RETRY
                     else:
                         # Reduce memory limit as fallback
                         agent.reduce_memory_limit(0.8)
                         return ErrorRecoveryStrategy.RETRY_WITH_MODIFICATION
                 
                 return ErrorRecoveryStrategy.FAIL
             
             async def handle_validation_error(self, error, context):
                 """Handle response validation failures."""
                 
                 # Provide additional guidance to agent
                 agent = context.get('agent')
                 task_data = context.get('task_data', {})
                 
                 if agent and task_data:
                     # Add validation guidance
                     task_data['additional_guidance'] = self.get_validation_guidance(error)
                     return ErrorRecoveryStrategy.RETRY_WITH_MODIFICATION
                 
                 return ErrorRecoveryStrategy.FAIL
             
             async def handle_communication_error(self, error, context):
                 """Handle API communication failures."""
                 
                 # Check if it's a rate limit error
                 if "rate_limit" in str(error).lower():
                     delay = self.calculate_rate_limit_delay(error)
                     await asyncio.sleep(delay)
                     return ErrorRecoveryStrategy.RETRY
                 
                 # Check if it's a temporary network issue
                 if error.is_temporary():
                     return ErrorRecoveryStrategy.RETRY
                 
                 return ErrorRecoveryStrategy.FAIL

   .. tab:: Error Analytics

      .. code-block:: python

         # Comprehensive error analysis
         def analyze_experiment_errors(error_handler: ErrorHandler) -> Dict:
             """Analyze error patterns and provide insights."""
             
             error_stats = error_handler.get_error_statistics()
             
             analysis = {
                 'error_summary': {
                     'total_errors': error_stats.total_errors,
                     'unique_error_types': len(error_stats.errors_by_category),
                     'recovery_rate': error_stats.recovery_success_rate,
                     'average_retries': error_stats.average_retry_count
                 },
                 'category_analysis': {},
                 'temporal_patterns': {},
                 'agent_error_patterns': {},
                 'recommendations': []
             }
             
             # Analyze by category
             for category, count in error_stats.errors_by_category.items():
                 if count > 0:
                     analysis['category_analysis'][category] = {
                         'count': count,
                         'percentage': (count / error_stats.total_errors) * 100,
                         'typical_recovery_time': error_handler.get_average_recovery_time(category),
                         'success_rate': error_handler.get_category_success_rate(category)
                     }
             
             # Generate recommendations
             if error_stats.errors_by_category.get(ErrorCategory.MEMORY_ERROR, 0) > 5:
                 analysis['recommendations'].append(
                     "Consider reducing agent memory limits or improving compression"
                 )
             
             if error_stats.errors_by_category.get(ErrorCategory.COMMUNICATION_ERROR, 0) > 3:
                 analysis['recommendations'].append(
                     "Review API rate limiting and network connectivity"
                 )
             
             return analysis

**Error Statistics and Reporting**

.. code-block:: python

   # Generate comprehensive error report
   def generate_error_report(experiment_results: List[Dict]) -> str:
       """Generate detailed error report across multiple experiments."""
       
       report = []
       total_experiments = len(experiment_results)
       total_errors = sum(
           sum(result.get('error_statistics', {}).values()) 
           for result in experiment_results
       )
       
       report.append(f"Error Analysis Report")
       report.append(f"{'='*50}")
       report.append(f"Total Experiments: {total_experiments}")
       report.append(f"Total Errors: {total_errors}")
       report.append(f"Average Errors per Experiment: {total_errors/total_experiments:.2f}")
       report.append("")
       
       # Category breakdown
       category_totals = {}
       for result in experiment_results:
           error_stats = result.get('error_statistics', {})
           for category, count in error_stats.items():
               category_totals[category] = category_totals.get(category, 0) + count
       
       report.append("Error Categories:")
       for category, count in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
           percentage = (count / total_errors) * 100 if total_errors > 0 else 0
           report.append(f"  {category}: {count} ({percentage:.1f}%)")
       
       return "\n".join(report)

Agent-Centric Logger
--------------------

Comprehensive logging system organized around individual agent activities and system events.

.. automodule:: utils.logging.agent_centric_logger
   :members:
   :undoc-members:
   :show-inheritance:

Experiment Summary Utilities
----------------------------

Structured helpers for generating machine-readable experiment summaries.

.. automodule:: utils.logging.result_summary
   :members:
   :undoc-members:
   :show-inheritance:

Logging Architecture
~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Agent Logging

.. code-block:: python

   from utils.logging.agent_centric_logger import (
             AgentCentricLogger, LogEvent, LogLevel
         )
         
         # Create logger for specific agent
         logger = AgentCentricLogger(
             agent_name="Alice",
             experiment_id="exp_20250822_001",
             log_level=LogLevel.INFO,
             include_timestamps=True,
             include_context=True
         )
         
         # Log agent activities
         logger.log_principle_application(
             principle="maximizing_floor",
             distribution_choice=3,
             reasoning="Protects most vulnerable populations",
             confidence_level="high",
             response_time=23.4
         )
         
         logger.log_discussion_turn(
             round_number=5,
             internal_reasoning="Need to address Bob's concerns about efficiency",
             public_statement="I understand the efficiency concerns, but we must balance that with fairness",
             addresses_agents=["Bob"],
             proposes_vote=False
         )
         
         logger.log_voting_action(
             round_number=8,
             chosen_principle="maximizing_average_with_floor",
             constraint_amount=15000,
             changed_preference=True,
             reasoning="Compromise addresses both efficiency and fairness"
         )

   .. tab:: Advanced Logging Features

      .. code-block:: python

         # Custom logging with structured data
         logger.log_custom_event(
             event_type="memory_optimization",
             severity=LogLevel.INFO,
             data={
                 "memory_before": 48750,
                 "memory_after": 42300,
                 "compression_ratio": 0.87,
                 "compression_time": 2.1,
                 "retained_entries": 156,
                 "discarded_entries": 23
             },
             message="Successfully compressed agent memory"
         )
         
         # Log performance metrics
         logger.log_performance_metric(
             metric_name="response_generation_time",
             value=18.7,
             unit="seconds",
             context={
                 "phase": "phase2",
                 "round": 7,
                 "task_complexity": "high"
             }
         )
         
         # Log error with recovery
         logger.log_error_with_recovery(
             error_type="validation_error",
             original_error="Response missing constraint specification",
             recovery_action="Provided additional guidance and retried",
             recovery_success=True,
             retry_count=2
         )

   .. tab:: Log Analysis and Queries

      .. code-block:: python

         # Query and analyze agent logs
         def analyze_agent_performance(logger: AgentCentricLogger) -> Dict:
             """Analyze agent performance from logs."""
             
             logs = logger.get_all_logs()
             
             analysis = {
                 'total_events': len(logs),
                 'event_breakdown': {},
                 'performance_metrics': {},
                 'error_analysis': {},
                 'decision_patterns': {},
                 'interaction_patterns': {}
             }
             
             # Event breakdown
             for log_entry in logs:
                 event_type = log_entry.event_type
                 analysis['event_breakdown'][event_type] = \
                     analysis['event_breakdown'].get(event_type, 0) + 1
             
             # Performance analysis
             response_times = [
                 log.data.get('response_time', 0)
                 for log in logs
                 if log.data.get('response_time')
             ]
             
             if response_times:
                 analysis['performance_metrics'] = {
                     'average_response_time': sum(response_times) / len(response_times),
                     'min_response_time': min(response_times),
                     'max_response_time': max(response_times),
                     'total_responses': len(response_times)
                 }
             
             # Decision pattern analysis
             principle_choices = [
                 log.data.get('principle')
                 for log in logs
                 if log.event_type == 'principle_application'
             ]
             
             if principle_choices:
                 from collections import Counter
                 analysis['decision_patterns']['principle_preferences'] = \
                     Counter(principle_choices)
             
             return analysis

**Multi-Agent Logging Coordination**

.. code-block:: python

   # Coordinate logging across multiple agents
   class ExperimentLogger:
       """Centralized logging coordinator for multi-agent experiments."""
       
       def __init__(self, experiment_id: str):
           self.experiment_id = experiment_id
           self.agent_loggers = {}
           self.central_log = []
       
       def get_agent_logger(self, agent_name: str) -> AgentCentricLogger:
           """Get or create logger for specific agent."""
           
           if agent_name not in self.agent_loggers:
               self.agent_loggers[agent_name] = AgentCentricLogger(
                   agent_name=agent_name,
                   experiment_id=self.experiment_id
               )
           
           return self.agent_loggers[agent_name]
       
       def log_experiment_event(self, event_type: str, data: Dict, message: str):
           """Log experiment-level events."""
           
           event = {
               'timestamp': datetime.now().isoformat(),
               'event_type': event_type,
               'data': data,
               'message': message
           }
           
           self.central_log.append(event)
       
       def generate_unified_timeline(self) -> List[Dict]:
           """Generate unified timeline of all experiment events."""
           
           all_events = []
           
           # Add agent events
           for agent_name, logger in self.agent_loggers.items():
               for log_entry in logger.get_all_logs():
                   all_events.append({
                       'timestamp': log_entry.timestamp,
                       'source': f'agent_{agent_name}',
                       'event_type': log_entry.event_type,
                       'data': log_entry.data,
                       'message': log_entry.message
                   })
           
           # Add experiment events
           for event in self.central_log:
               all_events.append({
                   'timestamp': event['timestamp'],
                   'source': 'experiment_system',
                   'event_type': event['event_type'],
                   'data': event['data'],
                   'message': event['message']
               })
           
           # Sort by timestamp
           all_events.sort(key=lambda x: x['timestamp'])
           
           return all_events

Language Manager
----------------

Multi-language support system for conducting experiments in English, Spanish, and Mandarin.

.. automodule:: utils.language_manager
   :members:
   :undoc-members:
   :show-inheritance:

Multi-Language Experiment Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Language Management

      .. code-block:: python

         from utils.language_manager import (
             get_language_manager, SupportedLanguage,
             LanguageManager, TranslationError
         )
         
         # Create language manager for Spanish experiment
         spanish_manager = get_language_manager(SupportedLanguage.SPANISH)
         
         # Get translated prompts
         principle_prompt = spanish_manager.get_prompt(
             "phase1_principle_application",
             context={
                 "principle_name": "maximizing_floor",
                 "agent_name": "María",
                 "distribution_count": 4
             }
         )
         
         # Translate justice principle names
         principles_spanish = {
             "maximizing_floor": spanish_manager.translate_principle_name("maximizing_floor"),
             "maximizing_average": spanish_manager.translate_principle_name("maximizing_average"),
             "maximizing_average_with_floor": spanish_manager.translate_principle_name("maximizing_average_with_floor"),
             "maximizing_average_with_range": spanish_manager.translate_principle_name("maximizing_average_with_range")
         }
         
         print("Spanish Principles:")
         for eng, esp in principles_spanish.items():
             print(f"  {eng} → {esp}")

   .. tab:: Advanced Language Features

      .. code-block:: python

         # Multi-language experiment configuration
         def create_multilingual_experiment_configs():
             """Create experiment configurations for all supported languages."""
             
             configs = {}
             
             for language in [SupportedLanguage.ENGLISH, SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN]:
                 language_manager = get_language_manager(language)
                 
                 # Get language-specific agent personalities
                 personalities = language_manager.get_cultural_personalities()
                 
                 config = ExperimentConfiguration(
                     language=language.value,
                     agents=[
                         AgentConfiguration(
                             name=language_manager.get_agent_name(i),
                             personality=personalities[i % len(personalities)],
                             model=language_manager.get_optimal_model(),
                             temperature=0.3
                         )
                         for i in range(3)
                     ],
                     phase2_rounds=language_manager.get_optimal_rounds()
                 )
                 
                 configs[language.value] = config
             
             return configs

   .. tab:: Custom Translation Management

      .. code-block:: python

         # Custom translation management for specialized terms
         class CustomLanguageManager(LanguageManager):
             """Extended language manager with domain-specific translations."""
             
             def __init__(self, language: SupportedLanguage):
                 super().__init__(language)
                 self.custom_translations = self.load_custom_translations()
             
             def load_custom_translations(self) -> Dict[str, str]:
                 """Load domain-specific justice theory translations."""
                 
                 if self.language == SupportedLanguage.SPANISH:
                     return {
                         "veil_of_ignorance": "velo de ignorancia",
                         "distributive_justice": "justicia distributiva",
                         "income_inequality": "desigualdad de ingresos",
                         "social_welfare": "bienestar social",
                         "economic_efficiency": "eficiencia económica"
                     }
                 elif self.language == SupportedLanguage.MANDARIN:
                     return {
                         "veil_of_ignorance": "无知之幕",
                         "distributive_justice": "分配正义",
                         "income_inequality": "收入不平等",
                         "social_welfare": "社会福利",
                         "economic_efficiency": "经济效率"
                     }
                 else:
                     return {}
             
             def translate_concept(self, concept: str) -> str:
                 """Translate specialized justice concepts."""
                 
                 return self.custom_translations.get(
                     concept,
                     super().translate_concept(concept)
                 )

**Language-Specific Validation**

.. code-block:: python

   # Validate responses in different languages
   def validate_multilingual_response(response: str, language: SupportedLanguage) -> bool:
       """Validate agent responses according to language-specific patterns."""
       
       language_manager = get_language_manager(language)
       
       # Check for required phrases
       required_phrases = language_manager.get_required_response_phrases()
       
       for phrase_type, phrases in required_phrases.items():
           if not any(phrase.lower() in response.lower() for phrase in phrases):
               return False
       
       # Validate cultural appropriateness
       if not language_manager.validate_cultural_appropriateness(response):
           return False
       
       # Check language-specific formatting
       if not language_manager.validate_response_format(response):
           return False
       
       return True

Model Provider
--------------

Unified interface for multiple AI model providers including OpenAI and OpenRouter integration.

.. automodule:: utils.model_provider
   :members:
   :undoc-members:
   :show-inheritance:

Multi-Provider Support
~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Provider Usage

      .. code-block:: python

         from utils.model_provider import (
             ModelProvider, get_model_provider,
             OpenAIProvider, OpenRouterProvider
         )
         
         # Auto-detect provider based on model name
         openai_provider = get_model_provider("gpt-4.1-mini")
         openrouter_provider = get_model_provider("gemini-2.5-flash")
         claude_provider = get_model_provider("anthropic/claude-3-5-sonnet")
         
         # Use providers for agent interactions
         async def create_agent_with_provider(agent_config):
             """Create agent with appropriate model provider."""
             
             provider = get_model_provider(agent_config.model)
             
             # Configure provider settings
             provider.configure(
                 temperature=agent_config.temperature,
                 max_tokens=2000,
                 timeout=30.0
             )
             
             # Create agent with provider
             agent = Agent(
                 config=agent_config,
                 model_provider=provider
             )
             
             return agent

   .. tab:: Advanced Provider Configuration

      .. code-block:: python

         # Custom provider configuration for different use cases
         provider_configs = {
             "fast_openai": {
                 "model": "gpt-4.1-mini",
                 "temperature": 0.0,
                 "max_tokens": 1500,
                 "timeout": 15.0,
                 "retry_config": {
                     "max_retries": 3,
                     "backoff_factor": 1.5
                 }
             },
             
             "creative_claude": {
                 "model": "anthropic/claude-3-5-sonnet",
                 "temperature": 0.7,
                 "max_tokens": 3000,
                 "timeout": 45.0,
                 "retry_config": {
                     "max_retries": 2,
                     "backoff_factor": 2.0
                 }
             },
             
             "efficient_gemini": {
                 "model": "gemini-2.5-flash",
                 "temperature": 0.2,
                 "max_tokens": 2000,
                 "timeout": 20.0,
                 "retry_config": {
                     "max_retries": 5,
                     "backoff_factor": 1.2
                 }
             }
         }
         
         # Create providers with custom configs
         def create_optimized_providers():
             providers = {}
             
             for name, config in provider_configs.items():
                 provider = get_model_provider(config["model"])
                 provider.configure(**config)
                 providers[name] = provider
             
             return providers

   .. tab:: Provider Performance Monitoring

      .. code-block:: python

         # Monitor provider performance and costs
         class ProviderMonitor:
             """Monitor model provider performance and usage."""
             
             def __init__(self):
                 self.provider_stats = {}
                 self.cost_tracking = {}
             
             async def track_request(self, provider: ModelProvider, request_data: Dict) -> Dict:
                 """Track a provider request and response."""
                 
                 start_time = time.time()
                 
                 try:
                     response = await provider.generate_response(request_data)
                     end_time = time.time()
                     
                     # Track success metrics
                     self.record_success(
                         provider=provider,
                         response_time=end_time - start_time,
                         tokens_used=response.get('usage', {}).get('total_tokens', 0),
                         cost=self.calculate_cost(provider, response)
                     )
                     
                     return response
                     
                 except Exception as e:
                     end_time = time.time()
                     
                     # Track failure metrics
                     self.record_failure(
                         provider=provider,
                         error=e,
                         response_time=end_time - start_time
                     )
                     
                     raise
             
             def get_provider_summary(self) -> Dict:
                 """Get comprehensive provider performance summary."""
                 
                 summary = {}
                 
                 for provider_name, stats in self.provider_stats.items():
                     summary[provider_name] = {
                         'total_requests': stats['success_count'] + stats['failure_count'],
                         'success_rate': stats['success_count'] / (stats['success_count'] + stats['failure_count']),
                         'average_response_time': stats['total_response_time'] / stats['success_count'] if stats['success_count'] > 0 else 0,
                         'total_cost': self.cost_tracking.get(provider_name, 0),
                         'average_tokens_per_request': stats['total_tokens'] / stats['success_count'] if stats['success_count'] > 0 else 0
                     }
                 
                 return summary

**Provider Load Balancing**

.. code-block:: python

   # Implement load balancing across providers
   class LoadBalancedProvider:
       """Load balancer for multiple model providers."""
       
       def __init__(self, providers: List[ModelProvider]):
           self.providers = providers
           self.current_loads = {provider.name: 0 for provider in providers}
           self.failure_counts = {provider.name: 0 for provider in providers}
       
       async def get_response(self, request_data: Dict) -> Dict:
           """Get response using load balancing strategy."""
           
           # Select provider with lowest current load
           available_providers = [
               p for p in self.providers 
               if self.failure_counts[p.name] < 3  # Skip failing providers
           ]
           
           if not available_providers:
               # Reset failure counts if all providers are failing
               self.failure_counts = {provider.name: 0 for provider in self.providers}
               available_providers = self.providers
           
           selected_provider = min(
               available_providers,
               key=lambda p: self.current_loads[p.name]
           )
           
           # Track load
           self.current_loads[selected_provider.name] += 1
           
           try:
               response = await selected_provider.generate_response(request_data)
               
               # Reset failure count on success
               self.failure_counts[selected_provider.name] = 0
               
               return response
               
           except Exception as e:
               # Track failure
               self.failure_counts[selected_provider.name] += 1
               raise
               
           finally:
               # Reduce load
               self.current_loads[selected_provider.name] -= 1

Experiment Runner
-----------------

Utilities for running experiments, generating configurations, and managing batch processes.

.. automodule:: utils.experiment_runner
   :members:
   :undoc-members:
   :show-inheritance:

Experiment Orchestration
~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Single Experiment Execution

      .. code-block:: python

         from utils.experiment_runner import (
             run_experiment_from_config, generate_random_config,
             ExperimentRunner, ExperimentResult
         )
         
         # Generate and run single experiment
         async def run_single_experiment():
             """Run a single experiment with random configuration."""
             
             # Generate random configuration
             config = generate_random_config(
                 num_agents=3,
                 num_rounds=15,
                 language="English"
             )
             
             # Run experiment
             results = await run_experiment_from_config(config)
             
             # Save results
             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
             output_file = f"experiment_results_{timestamp}.json"
             
             with open(output_file, 'w') as f:
                 json.dump(results, f, indent=2, default=str)
             
             print(f"Experiment completed. Results saved to {output_file}")
             
             return results

   .. tab:: Batch Experiment Execution

      .. code-block:: python

         from utils.experiment_runner import run_experiments_parallel
         
         # Run multiple experiments in parallel
         def run_batch_experiments():
             """Run multiple experiments for statistical analysis."""
             
             # Generate multiple configurations
             configs = []
             for i in range(10):
                 config = generate_random_config(
                     num_agents=3,
                     num_rounds=random.randint(10, 20),
                     language=random.choice(["English", "Spanish", "Mandarin"]),
                     seed=i  # Different seed for each experiment
                 )
                 configs.append(config)
             
             # Convert configs to temporary files\n             import tempfile\n             import yaml\n             import os\n             config_files = []\n             \n             for config in configs:\n                 with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:\n                     yaml.dump(config, f)\n                     config_files.append(f.name)\n             \n             # Run experiments in parallel
             results = run_experiments_parallel(
                 config_files,
                 max_parallel=3,  # Limit concurrent experiments
                 output_dir=\"batch_results\",
                 verbose=True
             )
             
             # Analyze batch results
             batch_analysis = analyze_batch_results(results)
             
             return results, batch_analysis
         
         def print_progress(completed: int, total: int, current_experiment: str):
             """Progress callback for batch execution."""
             percentage = (completed / total) * 100
             print(f"Progress: {completed}/{total} ({percentage:.1f}%) - Running: {current_experiment}")

   .. tab:: Configuration Generation

      .. code-block:: python

         # Advanced configuration generation
         def generate_experimental_conditions():
             """Generate configurations for different experimental conditions."""
             
             conditions = {
                 "baseline": {
                     "num_agents": 3,
                     "phase2_rounds": 10,
                     "temperature": 0.3,
                     "original_values_mode": {"enabled": False}
                 },
                 
                 "high_variance": {
                     "num_agents": 5,
                     "phase2_rounds": 15,
                     "temperature": 0.6,
                     "original_values_mode": {"enabled": False}
                 },
                 
                 "original_values": {
                     "num_agents": 3,
                     "phase2_rounds": 10,
                     "temperature": 0.3,
                     "original_values_mode": {"enabled": True, "situation": "sample"}
                 },
                 
                 "multilingual": {
                     "languages": ["English", "Spanish", "Mandarin"],
                     "num_agents": 3,
                     "phase2_rounds": 12,
                     "temperature": 0.3
                 }
             }
             
             configs = []
             
             for condition_name, params in conditions.items():
                 if "languages" in params:
                     # Generate config for each language
                     for language in params["languages"]:
                         config = generate_random_config(
                             num_agents=params["num_agents"],
                             num_rounds=params["phase2_rounds"],
                             language=language
                         )
                         config.condition_name = f"{condition_name}_{language}"
                         configs.append(config)
                 else:
                     # Generate single config
                     config = generate_random_config(
                         num_agents=params["num_agents"],
                         num_rounds=params["phase2_rounds"]
                     )
                     
                     # Apply condition-specific parameters
                     for key, value in params.items():
                         if key not in ["num_agents", "phase2_rounds"]:
                             setattr(config, key, value)
                     
                     config.condition_name = condition_name
                     configs.append(config)
             
             return configs

**Experiment Result Analysis**

.. code-block:: python

   # Comprehensive result analysis
   def analyze_experiment_results(results: List[Dict]) -> Dict:
       """Analyze results from multiple experiments."""
       
       analysis = {
           'summary_statistics': {},
           'principle_preferences': {},
           'consensus_patterns': {},
           'performance_metrics': {},
           'error_analysis': {},
           'temporal_patterns': {}
       }
       
       # Summary statistics
       total_experiments = len(results)
       successful_experiments = len([r for r in results if r.get('success', False)])
       
       analysis['summary_statistics'] = {
           'total_experiments': total_experiments,
           'successful_experiments': successful_experiments,
           'success_rate': successful_experiments / total_experiments,
           'average_duration': sum(r.get('duration_seconds', 0) for r in results) / total_experiments
       }
       
       # Principle preference analysis
       principle_counts = {}
       for result in results:
           if result.get('success') and 'phase2_results' in result:
               final_principle = result['phase2_results'].get('voting_results', {}).get('chosen_principle')
               if final_principle:
                   principle_counts[final_principle] = principle_counts.get(final_principle, 0) + 1
       
       analysis['principle_preferences'] = principle_counts
       
       # Consensus analysis
       consensus_achieved = len([
           r for r in results 
           if r.get('phase2_results', {}).get('voting_results', {}).get('consensus_reached', False)
       ])
       
       analysis['consensus_patterns'] = {
           'consensus_rate': consensus_achieved / successful_experiments if successful_experiments > 0 else 0,
           'average_rounds_to_consensus': calculate_average_consensus_rounds(results)
       }
       
       return analysis

Performance Optimization
------------------------

Performance monitoring and optimization utilities for the experimental system.

.. code-block:: python

   # Performance monitoring utilities
   class PerformanceMonitor:
       """Monitor and optimize experiment performance."""
       
       def __init__(self):
           self.metrics = {}
           self.optimization_suggestions = []
       
       def track_experiment_performance(self, experiment_results: Dict):
           """Track performance metrics from experiment results."""
           
           duration = experiment_results.get('duration_seconds', 0)
           phase1_duration = experiment_results.get('phase1_duration_seconds', 0)
           phase2_duration = experiment_results.get('phase2_duration_seconds', 0)
           
           # Track timing metrics
           self.metrics['total_duration'] = duration
           self.metrics['phase1_efficiency'] = phase1_duration / duration if duration > 0 else 0
           self.metrics['phase2_efficiency'] = phase2_duration / duration if duration > 0 else 0
           
           # Track resource usage
           memory_stats = experiment_results.get('memory_statistics', {})
           api_stats = experiment_results.get('api_statistics', {})
           
           self.metrics['memory_efficiency'] = memory_stats.get('peak_usage', 0)
           self.metrics['api_efficiency'] = api_stats.get('total_calls', 0)
           
           # Generate optimization suggestions
           self.generate_optimization_suggestions()
       
       def generate_optimization_suggestions(self):
           """Generate performance optimization suggestions."""
           
           suggestions = []
           
           if self.metrics.get('total_duration', 0) > 600:  # More than 10 minutes
               suggestions.append("Consider reducing phase2_rounds or using faster models")
           
           if self.metrics.get('memory_efficiency', 0) > 100000000:  # More than 100MB
               suggestions.append("Consider reducing agent memory limits")
           
           if self.metrics.get('api_efficiency', 0) > 100:  # More than 100 API calls
               suggestions.append("Consider optimizing agent reasoning or using more efficient models")
           
           self.optimization_suggestions = suggestions

See Also
--------

- :doc:`core` - How core modules use these utility functions
- :doc:`agents` - Agent integration with utility modules  
- :doc:`models` - Data models used by utility functions
- :doc:`../user-guide/running-experiments` - Using experiment runner utilities
- :doc:`../architecture/system-overview` - How utilities fit into the overall architecture
