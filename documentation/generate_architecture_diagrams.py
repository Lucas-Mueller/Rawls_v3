"""
Generate comprehensive architectural diagrams for the MAAI Frohlich Experiment system.

This script creates multiple architectural diagrams showing different aspects of the system:
1. Overall system architecture
2. Agent interaction flow
3. Phase 1 process flow
4. Phase 2 process flow
5. Data flow and logging architecture
6. Error handling and validation systems

Uses the diagrams library to create professional architectural diagrams.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.framework import React
from diagrams.programming.language import Python
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.monitoring import Prometheus
from diagrams.generic.blank import Blank
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.generic.network import Firewall, Router
from diagrams.generic.os import Ubuntu
from diagrams.generic.storage import Storage
import os

# Use available logging components
from diagrams.onprem.logging import Fluentbit as Fluentd  # Use Fluentbit instead of Fluentd

# Create a simple Custom class for model providers
class Custom:
    def __init__(self, name, icon=""):
        self._name = name
    
    def __new__(cls, name, icon=""):
        # Return a Rack component with the custom name
        return Rack(name)

def create_overall_architecture():
    """Create the overall system architecture diagram."""
    
    with Diagram("MAAI Frohlich Experiment - Overall System Architecture", 
                 filename="documentation/01_overall_architecture", 
                 show=False, 
                 direction="TB"):
        
        with Cluster("Configuration Layer"):
            config_yaml = Storage("YAML Configs")
            pydantic_models = Python("Pydantic Models")
            config_validation = Firewall("Config Validation")
            
        with Cluster("Experiment Management Layer"):
            exp_manager = Rack("Experiment Manager")
            phase1_mgr = Ubuntu("Phase 1 Manager")
            phase2_mgr = Ubuntu("Phase 2 Manager")
            
        with Cluster("Agent Layer"):
            with Cluster("Participant Agents"):
                participant1 = React("Agent 1")
                participant2 = React("Agent 2")
                participant3 = React("Agent 3")
                participant4 = React("Agent 4")
                participant5 = React("Agent 5")
                
            with Cluster("Utility Agents"):
                parser = Python("Parser Agent")
                validator = Python("Validator Agent")
                
        with Cluster("Core Systems"):
            memory_mgr = Redis("Memory Manager")
            bank_system = SQL("Bank Account System")
            distribution_gen = Python("Distribution Generator")
            consensus_detector = Python("Consensus Detector")
            
        with Cluster("Model Provider Layer"):
            openai = Custom("OpenAI", "")
            openrouter = Custom("OpenRouter", "")
            anthropic = Custom("Anthropic", "")
            google = Custom("Google", "")
            
        with Cluster("Data & Logging Layer"):
            agent_logger = Fluentd("Agent-Centric Logger")
            data_storage = Storage("Experimental Data")
            monitoring = Prometheus("Error Monitoring")
            
        # Connections
        config_yaml >> pydantic_models >> config_validation
        config_validation >> exp_manager
        
        exp_manager >> phase1_mgr
        exp_manager >> phase2_mgr
        
        phase1_mgr >> participant1
        phase1_mgr >> participant2
        phase1_mgr >> participant3
        phase1_mgr >> participant4
        phase1_mgr >> participant5
        
        phase2_mgr >> participant1
        phase2_mgr >> participant2
        phase2_mgr >> participant3
        phase2_mgr >> participant4
        phase2_mgr >> participant5
        
        participant1 >> parser
        participant2 >> parser
        participant3 >> parser
        participant4 >> parser
        participant5 >> parser
        
        participant1 >> validator
        participant2 >> validator
        participant3 >> validator
        participant4 >> validator
        participant5 >> validator
        
        participant1 >> memory_mgr
        participant2 >> memory_mgr
        participant3 >> memory_mgr
        participant4 >> memory_mgr
        participant5 >> memory_mgr
        
        participant1 >> bank_system
        participant2 >> bank_system
        participant3 >> bank_system
        participant4 >> bank_system
        participant5 >> bank_system
        
        phase1_mgr >> distribution_gen
        phase2_mgr >> consensus_detector
        
        participant1 >> openai
        participant2 >> openrouter
        participant3 >> anthropic
        participant4 >> google
        participant5 >> openai
        
        exp_manager >> agent_logger
        phase1_mgr >> agent_logger
        phase2_mgr >> agent_logger
        agent_logger >> data_storage
        
        exp_manager >> monitoring
        phase1_mgr >> monitoring
        phase2_mgr >> monitoring

def create_agent_interaction_flow():
    """Create the agent interaction flow diagram."""
    
    with Diagram("MAAI Frohlich Experiment - Agent Interaction Flow", 
                 filename="documentation/02_agent_interaction_flow", 
                 show=False, 
                 direction="LR"):
        
        with Cluster("Participant Agent"):
            agent_core = React("Agent Core")
            agent_memory = Redis("Agent Memory")
            agent_bank = SQL("Bank Account")
            
        with Cluster("Utility Processing"):
            response_parser = Python("Response Parser")
            validator = Firewall("Validator")
            retry_logic = Router("Retry Logic")
            
        with Cluster("Model Providers"):
            llm_provider = Custom("LLM Provider", "")
            
        with Cluster("Experiment Context"):
            context_mgr = Ubuntu("Context Manager")
            prompt_engine = Python("Prompt Engine")
            
        with Cluster("Results Processing"):
            earnings_calc = Python("Earnings Calculator")
            memory_updater = Redis("Memory Updater")
            
        # Flow connections
        context_mgr >> prompt_engine
        prompt_engine >> agent_core
        agent_core >> llm_provider
        llm_provider >> agent_core
        agent_core >> response_parser
        response_parser >> validator
        validator >> retry_logic
        retry_logic >> agent_core  # Retry loop
        validator >> earnings_calc
        earnings_calc >> agent_bank
        validator >> memory_updater
        memory_updater >> agent_memory

def create_phase1_process_flow():
    """Create the Phase 1 process flow diagram."""
    
    with Diagram("MAAI Frohlich Experiment - Phase 1 Process Flow", 
                 filename="documentation/03_phase1_process_flow", 
                 show=False, 
                 direction="TB"):
        
        start = Blank("Start Phase 1")
        
        with Cluster("1.1 Initial Ranking"):
            initial_prompt = Python("Initial Ranking Prompt")
            initial_response = React("Agent Response")
            initial_parse = Python("Parse Ranking")
            
        with Cluster("1.2 Detailed Explanation"):
            explanation_prompt = Python("Explanation Prompt")
            explanation_response = React("Agent Learning")
            
        with Cluster("1.2b Post-Explanation Ranking"):
            post_exp_prompt = Python("Post-Explanation Prompt")
            post_exp_response = React("Agent Response")
            post_exp_parse = Python("Parse Ranking")
            
        with Cluster("1.3 Principle Application (x4 rounds)"):
            with Cluster("Each Round"):
                distribution_gen = Python("Generate Distribution")
                application_prompt = Python("Application Prompt")
                principle_choice = React("Agent Choice")
                principle_parse = Python("Parse Choice")
                principle_apply = Python("Apply Principle")
                income_assignment = Router("Assign Income Class")
                earnings_calc = SQL("Calculate Earnings")
                memory_update = Redis("Update Memory")
                
        with Cluster("1.4 Final Ranking"):
            final_prompt = Python("Final Ranking Prompt")
            final_response = React("Agent Response")
            final_parse = Python("Parse Ranking")
            
        end = Blank("Phase 1 Complete")
        
        # Flow connections
        start >> initial_prompt >> initial_response >> initial_parse
        initial_parse >> explanation_prompt >> explanation_response
        explanation_response >> post_exp_prompt >> post_exp_response >> post_exp_parse
        
        post_exp_parse >> distribution_gen
        distribution_gen >> application_prompt >> principle_choice >> principle_parse
        principle_parse >> principle_apply >> income_assignment >> earnings_calc
        earnings_calc >> memory_update
        
        memory_update >> Edge(label="Next Round (4x)") >> distribution_gen
        memory_update >> final_prompt >> final_response >> final_parse >> end

def create_phase2_process_flow():
    """Create the Phase 2 process flow diagram."""
    
    with Diagram("MAAI Frohlich Experiment - Phase 2 Process Flow", 
                 filename="documentation/04_phase2_process_flow", 
                 show=False, 
                 direction="TB"):
        
        start = Blank("Start Phase 2")
        
        with Cluster("Initialize Group Discussion"):
            context_transfer = Redis("Transfer Phase 1 Memory")
            group_setup = Ubuntu("Setup Group Context")
            
        with Cluster("Discussion Rounds (Max N rounds)"):
            with Cluster("Each Round"):
                speaking_order = Router("Generate Speaking Order")
                
                with Cluster("For Each Agent"):
                    discussion_prompt = Python("Discussion Prompt")
                    agent_statement = React("Agent Statement")
                    statement_validation = Firewall("Validate Statement")
                    vote_detection = Python("Detect Vote Proposal")
                    
                consensus_check = Python("Check Consensus Readiness")
                
        with Cluster("Voting Process"):
            vote_agreement = Python("Check Vote Agreement")
            secret_ballot = Firewall("Secret Ballot Voting")
            vote_validation = Python("Validate Votes")
            consensus_detection = Python("Detect Consensus")
            
        with Cluster("Outcome Determination"):
            consensus_branch = Router("Consensus Reached?")
            apply_principle = Python("Apply Agreed Principle")
            random_assignment = Python("Random Assignment")
            payoff_calculation = SQL("Calculate Payoffs")
            
        with Cluster("Final Assessment"):
            final_rankings = Python("Collect Final Rankings")
            experiment_complete = Blank("Experiment Complete")
            
        # Flow connections
        start >> context_transfer >> group_setup
        group_setup >> speaking_order
        speaking_order >> discussion_prompt >> agent_statement >> statement_validation
        statement_validation >> vote_detection
        vote_detection >> consensus_check
        
        consensus_check >> Edge(label="Continue Discussion") >> speaking_order
        consensus_check >> vote_agreement
        
        vote_agreement >> secret_ballot >> vote_validation >> consensus_detection
        consensus_detection >> consensus_branch
        
        consensus_branch >> Edge(label="Yes") >> apply_principle >> payoff_calculation
        consensus_branch >> Edge(label="No") >> random_assignment >> payoff_calculation
        
        payoff_calculation >> final_rankings >> experiment_complete

def create_data_flow_architecture():
    """Create the data flow and logging architecture diagram."""
    
    with Diagram("MAAI Frohlich Experiment - Data Flow & Logging Architecture", 
                 filename="documentation/05_data_flow_architecture", 
                 show=False, 
                 direction="LR"):
        
        with Cluster("Data Sources"):
            agent_interactions = React("Agent Interactions")
            system_events = Ubuntu("System Events")
            error_events = Firewall("Error Events")
            
        with Cluster("Data Collection Layer"):
            agent_logger = Fluentd("Agent-Centric Logger")
            memory_tracker = Redis("Memory State Tracker")
            earnings_tracker = SQL("Earnings Tracker")
            interaction_logger = Python("Interaction Logger")
            
        with Cluster("Data Processing"):
            data_validator = Firewall("Data Validator")
            data_enricher = Python("Data Enricher")
            temporal_sequencer = Router("Temporal Sequencer")
            
        with Cluster("Data Storage"):
            experimental_data = Storage("Experimental Data")
            configuration_archive = Storage("Configuration Archive")
            trace_data = Storage("Trace Data")
            
        with Cluster("Analysis & Export"):
            json_exporter = Python("JSON Exporter")
            csv_exporter = Python("CSV Exporter")
            statistical_interface = Python("Statistical Interface")
            
        # Flow connections
        agent_interactions >> agent_logger
        system_events >> agent_logger
        error_events >> agent_logger
        
        agent_interactions >> memory_tracker
        agent_interactions >> earnings_tracker
        agent_interactions >> interaction_logger
        
        agent_logger >> data_validator
        memory_tracker >> data_validator
        earnings_tracker >> data_validator
        interaction_logger >> data_validator
        
        data_validator >> data_enricher >> temporal_sequencer
        
        temporal_sequencer >> experimental_data
        temporal_sequencer >> configuration_archive
        temporal_sequencer >> trace_data
        
        experimental_data >> json_exporter
        experimental_data >> csv_exporter
        experimental_data >> statistical_interface
        
        configuration_archive >> json_exporter
        trace_data >> csv_exporter

def create_error_handling_architecture():
    """Create the error handling and validation systems diagram."""
    
    with Diagram("MAAI Frohlich Experiment - Error Handling & Validation Architecture", 
                 filename="documentation/06_error_handling_architecture", 
                 show=False, 
                 direction="TB"):
        
        with Cluster("Error Detection Layer"):
            communication_monitor = Prometheus("Communication Monitor")
            response_validator = Firewall("Response Validator")
            memory_monitor = Redis("Memory Monitor")
            consensus_validator = Python("Consensus Validator")
            
        with Cluster("Error Classification"):
            error_classifier = Router("Error Classifier")
            
            with Cluster("Error Categories"):
                comm_errors = Custom("Communication Errors", "")
                validation_errors = Custom("Validation Errors", "")
                memory_errors = Custom("Memory Errors", "")
                system_errors = Custom("System Errors", "")
                
        with Cluster("Error Handling Strategies"):
            retry_handler = Router("Retry Handler")
            fallback_handler = Ubuntu("Fallback Handler")
            graceful_degradation = Python("Graceful Degradation")
            error_logger = Fluentd("Error Logger")
            
        with Cluster("Recovery Mechanisms"):
            communication_recovery = Python("Communication Recovery")
            validation_recovery = Python("Validation Recovery")
            memory_recovery = Redis("Memory Recovery")
            experiment_continuation = Ubuntu("Experiment Continuation")
            
        with Cluster("Quality Assurance"):
            constraint_validation = Firewall("Constraint Validation")
            ranking_validation = Firewall("Ranking Validation")
            discussion_validation = Firewall("Discussion Validation")
            consensus_validation = Firewall("Consensus Validation")
            
        # Flow connections
        communication_monitor >> error_classifier
        response_validator >> error_classifier
        memory_monitor >> error_classifier
        consensus_validator >> error_classifier
        
        error_classifier >> comm_errors
        error_classifier >> validation_errors
        error_classifier >> memory_errors
        error_classifier >> system_errors
        
        comm_errors >> retry_handler
        validation_errors >> retry_handler
        memory_errors >> retry_handler
        system_errors >> retry_handler
        
        retry_handler >> fallback_handler >> graceful_degradation
        
        retry_handler >> error_logger
        fallback_handler >> error_logger
        graceful_degradation >> error_logger
        
        comm_errors >> communication_recovery
        validation_errors >> validation_recovery
        memory_errors >> memory_recovery
        
        communication_recovery >> experiment_continuation
        validation_recovery >> experiment_continuation
        memory_recovery >> experiment_continuation
        
        constraint_validation >> response_validator
        ranking_validation >> response_validator
        discussion_validation >> response_validator
        consensus_validation >> response_validator

def create_bank_account_system_diagram():
    """Create a detailed diagram of the bank account and economic incentive system."""
    
    with Diagram("MAAI Frohlich Experiment - Bank Account & Economic Incentive System", 
                 filename="documentation/07_bank_account_system", 
                 show=False, 
                 direction="TB"):
        
        with Cluster("Agent Initialization"):
            agent_creation = React("Agent Creation")
            bank_initialization = SQL("Initialize Bank Account ($0.00)")
            
        with Cluster("Phase 1 Earnings System"):
            with Cluster("Round Processing (x4)"):
                principle_application = Python("Principle Application")
                income_class_assignment = Router("Random Income Class Assignment")
                earnings_calculation = Python("Earnings = Income / 10,000")
                balance_update = SQL("Update Bank Balance")
                
            phase1_total = SQL("Phase 1 Total Earnings")
            
        with Cluster("Economic Feedback Loop"):
            memory_integration = Redis("Integrate Earnings into Memory")
            counterfactual_analysis = Python("Calculate Alternative Earnings")
            decision_influence = React("Influence Future Decisions")
            
        with Cluster("Phase 2 Economic Stakes"):
            group_context = Ubuntu("Group Economic Context")
            consensus_incentives = Python("Consensus-Based Payoffs")
            failure_random = Router("Random Assignment (No Consensus)")
            
        with Cluster("Final Economic Outcomes"):
            phase2_earnings = SQL("Phase 2 Earnings")
            total_earnings = SQL("Total Experiment Earnings")
            economic_analysis = Python("Economic Behavior Analysis")
            
        with Cluster("Economic Data Tracking"):
            earnings_logger = Fluentd("Earnings Logger")
            economic_metrics = Prometheus("Economic Metrics")
            payoff_history = Storage("Payoff History")
            
        # Flow connections
        agent_creation >> bank_initialization
        bank_initialization >> principle_application
        
        principle_application >> income_class_assignment >> earnings_calculation >> balance_update
        balance_update >> Edge(label="Round Complete") >> principle_application
        balance_update >> phase1_total
        
        earnings_calculation >> memory_integration >> decision_influence
        earnings_calculation >> counterfactual_analysis >> decision_influence
        
        phase1_total >> group_context
        group_context >> consensus_incentives
        group_context >> failure_random
        
        consensus_incentives >> phase2_earnings
        failure_random >> phase2_earnings
        
        phase1_total >> total_earnings
        phase2_earnings >> total_earnings
        total_earnings >> economic_analysis
        
        earnings_calculation >> earnings_logger
        phase2_earnings >> earnings_logger
        total_earnings >> earnings_logger
        
        earnings_logger >> economic_metrics >> payoff_history

def main():
    """Generate all architectural diagrams."""
    
    print("Generating MAAI Frohlich Experiment architectural diagrams...")
    
    # Create output directory if it doesn't exist
    os.makedirs("documentation", exist_ok=True)
    
    try:
        print("1. Creating overall system architecture diagram...")
        create_overall_architecture()
        
        print("2. Creating agent interaction flow diagram...")
        create_agent_interaction_flow()
        
        print("3. Creating Phase 1 process flow diagram...")
        create_phase1_process_flow()
        
        print("4. Creating Phase 2 process flow diagram...")
        create_phase2_process_flow()
        
        print("5. Creating data flow architecture diagram...")
        create_data_flow_architecture()
        
        print("6. Creating error handling architecture diagram...")
        create_error_handling_architecture()
        
        print("7. Creating bank account system diagram...")
        create_bank_account_system_diagram()
        
        print("\nAll diagrams generated successfully!")
        print("Output files:")
        print("- documentation/01_overall_architecture.png")
        print("- documentation/02_agent_interaction_flow.png")
        print("- documentation/03_phase1_process_flow.png")
        print("- documentation/04_phase2_process_flow.png")
        print("- documentation/05_data_flow_architecture.png")
        print("- documentation/06_error_handling_architecture.png")
        print("- documentation/07_bank_account_system.png")
        
    except ImportError as e:
        print(f"Error: Missing required library. Please install with: pip install diagrams")
        print(f"Specific error: {e}")
    except Exception as e:
        print(f"Error generating diagrams: {e}")

if __name__ == "__main__":
    main()