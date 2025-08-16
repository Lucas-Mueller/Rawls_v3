"""
Generate clean, simplified architectural diagrams for the MAAI Frohlich Experiment system.

This script creates much cleaner, more readable diagrams using Mermaid syntax,
focusing on high-level architecture and key flows rather than implementation details.
"""

import os
import subprocess
from pathlib import Path

def create_mermaid_diagram(diagram_content, filename, title):
    """Create a Mermaid diagram and convert it to PNG."""
    
    # Create the mermaid file
    mermaid_file = f"documentation/{filename}.mmd"
    png_file = f"documentation/{filename}.png"
    
    with open(mermaid_file, 'w') as f:
        f.write(diagram_content)
    
    try:
        # Try to convert using mermaid CLI with high resolution settings
        result = subprocess.run([
            'mmdc', 
            '-i', mermaid_file, 
            '-o', png_file,
            '--width', '2400',  # High width for better resolution
            '--height', '1600', # High height for better resolution
            '--scale', '2',     # 2x scale for crisp text
            '--backgroundColor', 'white'
        ], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Generated {png_file} (High Resolution)")
        else:
            print(f"❌ Failed to generate {png_file}")
            print(f"Error: {result.stderr}")
            print(f"💡 Mermaid code saved to {mermaid_file} - you can use online tools to render it")
    except FileNotFoundError:
        print(f"💡 Mermaid CLI not found. Mermaid code saved to {mermaid_file}")
        print(f"   You can render it at: https://mermaid.live/")

def create_overall_system_architecture():
    """Create a clean overall system architecture diagram with left-to-right process flow."""
    
    diagram = """
graph LR
    subgraph "1. Configuration"
        Config[YAML Configuration]
        Models[Pydantic Models]
    end
    
    subgraph "2. Experiment Setup"
        ExpMgr[Experiment Manager]
        Init[Initialize Agents<br/>& Bank Accounts]
    end
    
    subgraph "3. Phase 1 Execution"
        Phase1[Phase 1 Manager]
        P1Process[Individual Learning<br/>4 Application Rounds]
        Distributions[Distribution Generator]
    end
    
    subgraph "4. Phase 2 Execution"  
        Phase2[Phase 2 Manager]
        P2Process[Group Discussion<br/>& Consensus]
        Consensus[Consensus Detection]
    end
    
    subgraph "5. AI Agent Layer"
        Participants[Participant Agents<br/>5 Agents]
        Utility[Utility Agents<br/>Parser & Validator]
        LLMs[Language Models<br/>OpenAI, Anthropic, Google]
    end
    
    subgraph "6. Core Systems"
        Memory[Memory Management]
        Bank[Bank Account System]
    end
    
    subgraph "7. Data & Results"
        Logger[Agent-Centric Logger]
        Storage[Experimental Data]
        Export[Analysis Export]
    end
    
    %% Process Flow Connections (Left to Right)
    Config --> ExpMgr
    Models --> ExpMgr
    ExpMgr --> Init
    Init --> Phase1
    
    Phase1 --> P1Process
    P1Process --> Phase2
    Phase2 --> P2Process
    P2Process --> Logger
    
    %% Supporting System Connections
    Phase1 --> Distributions
    Phase2 --> Consensus
    
    P1Process --> Participants
    P2Process --> Participants
    Participants --> Utility
    Participants --> LLMs
    
    Participants --> Memory
    Participants --> Bank
    
    %% Data Flow
    Participants --> Logger
    Logger --> Storage
    Storage --> Export
    
    %% Styling
    classDef configClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef setupClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef phase1Class fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef phase2Class fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef agentClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef coreClass fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef dataClass fill:#fafafa,stroke:#424242,stroke-width:2px
    
    class Config,Models configClass
    class ExpMgr,Init setupClass
    class Phase1,P1Process,Distributions phase1Class
    class Phase2,P2Process,Consensus phase2Class
    class Participants,Utility,LLMs agentClass
    class Memory,Bank coreClass
    class Logger,Storage,Export dataClass
"""
    
    create_mermaid_diagram(diagram, "clean_01_overall_architecture", "MAAI System Architecture - Process Flow")

def create_experimental_flow():
    """Create a clean experimental flow diagram."""
    
    diagram = """
graph TD
    Start([Experiment Start]) --> Init[Initialize Agents & Accounts]
    
    Init --> P1Start[Phase 1: Individual Learning]
    
    subgraph "Phase 1 Process"
        P1Start --> InitRank[Initial Principle Ranking]
        InitRank --> Learn[Learn Principle Applications]
        Learn --> Apply[Apply Principles<br/>4 Rounds with Earnings]
        Apply --> FinalRank[Final Principle Ranking]
    end
    
    FinalRank --> P2Start[Phase 2: Group Discussion]
    
    subgraph "Phase 2 Process"
        P2Start --> Discuss[Group Discussion<br/>Multiple Rounds]
        Discuss --> VoteCheck{Vote Proposed?}
        VoteCheck -->|No| Discuss
        VoteCheck -->|Yes| Vote[Secret Ballot Vote]
        Vote --> Consensus{Consensus<br/>Reached?}
        Consensus -->|No| CheckRounds{Max Rounds<br/>Reached?}
        CheckRounds -->|No| Discuss
        CheckRounds -->|Yes| Random[Random Payoff]
        Consensus -->|Yes| Apply2[Apply Agreed Principle]
    end
    
    Random --> Final[Final Rankings & Results]
    Apply2 --> Final
    Final --> End([Experiment Complete])
    
    %% Styling
    classDef startEnd fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    classDef phase1 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef phase2 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class Start,End startEnd
    class InitRank,Learn,Apply,FinalRank phase1
    class Discuss,Vote,Apply2,Random phase2
    class VoteCheck,Consensus,CheckRounds decision
"""
    
    create_mermaid_diagram(diagram, "clean_02_experimental_flow", "Experimental Process Flow")

def create_agent_architecture():
    """Create a clean agent architecture diagram."""
    
    diagram = """
graph LR
    subgraph "Agent Core"
        Agent[Participant Agent]
        Memory[Agent Memory<br/>50,000 chars]
        Bank[Bank Account<br/>Earnings Tracker]
    end
    
    subgraph "Processing Pipeline"
        Prompt[Experimental<br/>Prompt]
        LLM[Language Model<br/>Provider]
        Response[Agent Response]
        Parse[Utility Agent<br/>Parser]
        Validate[Response<br/>Validator]
    end
    
    subgraph "Economic System"
        Distribution[Income<br/>Distribution]
        Assignment[Class<br/>Assignment]
        Earnings[Earnings<br/>Calculation]
        Update[Balance<br/>Update]
    end
    
    %% Flow
    Prompt --> Agent
    Agent --> Memory
    Agent --> LLM
    LLM --> Response
    Response --> Parse
    Parse --> Validate
    
    Validate --> Distribution
    Distribution --> Assignment
    Assignment --> Earnings
    Earnings --> Bank
    Bank --> Update
    Update --> Memory
    
    %% Feedback loop
    Memory -.-> Agent
    
    %% Styling
    classDef agentCore fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef processing fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef economic fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class Agent,Memory,Bank agentCore
    class Prompt,LLM,Response,Parse,Validate processing
    class Distribution,Assignment,Earnings,Update economic
"""
    
    create_mermaid_diagram(diagram, "clean_03_agent_architecture", "Agent Architecture")

def create_data_flow():
    """Create a clean data flow diagram."""
    
    diagram = """
graph TB
    subgraph "Data Sources"
        Agents[Agent Interactions]
        System[System Events]
        Errors[Error Events]
    end
    
    subgraph "Collection & Processing"
        Logger[Agent-Centric<br/>Logger]
        Processor[Data Processor]
        Validator[Data Validator]
    end
    
    subgraph "Storage"
        ExperimentDB[(Experimental<br/>Data)]
        ConfigDB[(Configuration<br/>Archive)]
        TraceDB[(Trace Data)]
    end
    
    subgraph "Analysis & Export"
        JSON[JSON Export]
        CSV[CSV Export]
        Stats[Statistical<br/>Analysis]
    end
    
    %% Flow
    Agents --> Logger
    System --> Logger
    Errors --> Logger
    
    Logger --> Processor
    Processor --> Validator
    
    Validator --> ExperimentDB
    Validator --> ConfigDB
    Validator --> TraceDB
    
    ExperimentDB --> JSON
    ExperimentDB --> CSV
    ExperimentDB --> Stats
    
    %% Styling
    classDef source fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef export fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class Agents,System,Errors source
    class Logger,Processor,Validator process
    class ExperimentDB,ConfigDB,TraceDB storage
    class JSON,CSV,Stats export
"""
    
    create_mermaid_diagram(diagram, "clean_04_data_flow", "Data Flow Architecture")

def create_bank_account_system():
    """Create a clean bank account system diagram."""
    
    diagram = """
graph TD
    Start[Agent Initialization<br/>Balance: $0.00] --> P1[Phase 1 Earnings]
    
    subgraph "Phase 1 Earnings Cycle"
        P1 --> Choose[Choose Justice<br/>Principle]
        Choose --> Apply[Apply Principle<br/>to Distribution]
        Apply --> Assign[Random Class<br/>Assignment]
        Assign --> Earn[Calculate Earnings<br/>$1 per $10,000 income]
        Earn --> Update1[Update Bank<br/>Balance]
        Update1 --> Memory1[Update Agent<br/>Memory]
        Memory1 --> NextRound{Next Round?}
        NextRound -->|Yes<br/>Round 2,3,4| Choose
        NextRound -->|No| P1Complete[Phase 1 Complete<br/>Total Earnings]
    end
    
    P1Complete --> P2[Phase 2 Discussion]
    
    subgraph "Phase 2 Economic Stakes"
        P2 --> Discuss[Group Discussion<br/>with P1 Earnings Context]
        Discuss --> Outcome{Group Outcome}
        Outcome -->|Consensus| GroupPay[Apply Agreed<br/>Principle]
        Outcome -->|No Consensus| RandomPay[Random<br/>Assignment]
        GroupPay --> P2Earn[Phase 2<br/>Earnings]
        RandomPay --> P2Earn
        P2Earn --> Final[Final Total<br/>Earnings]
    end
    
    Final --> Analysis[Economic Behavior<br/>Analysis]
    
    %% Economic feedback
    Memory1 -.->|Influences<br/>Future Decisions| Choose
    P1Complete -.->|Stakes Context| Discuss
    
    %% Styling
    classDef start fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    classDef phase1 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef phase2 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef economic fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef decision fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class Start start
    class Choose,Apply,Assign,Earn,Update1,Memory1 phase1
    class Discuss,GroupPay,RandomPay,P2Earn phase2
    class P1Complete,Final,Analysis economic
    class NextRound,Outcome decision
"""
    
    create_mermaid_diagram(diagram, "clean_05_bank_account_system", "Bank Account & Economic System")

def create_consensus_mechanism():
    """Create a clean consensus mechanism diagram."""
    
    diagram = """
graph TD
    Start[Group Discussion<br/>Begins] --> Round[Discussion Round]
    
    subgraph "Discussion Process"
        Round --> Speak[Random Speaking<br/>Order]
        Speak --> Statement[Agent Makes<br/>Statement]
        Statement --> Check[Check for<br/>Vote Proposal]
        Check --> AllSpoke{All Agents<br/>Spoken?}
        AllSpoke -->|No| Speak
        AllSpoke -->|Yes| VoteProp{Vote<br/>Proposed?}
    end
    
    VoteProp -->|No| NextRound{Max Rounds<br/>Reached?}
    NextRound -->|No| Round
    NextRound -->|Yes| NoConsensus[No Consensus<br/>Random Payoff]
    
    VoteProp -->|Yes| VoteAgree[Check Vote<br/>Agreement]
    VoteAgree --> Unanimous{All Agree<br/>to Vote?}
    Unanimous -->|No| Round
    
    Unanimous -->|Yes| SecretVote[Secret Ballot<br/>Voting]
    SecretVote --> CountVotes[Count & Validate<br/>Votes]
    CountVotes --> Consensus{Consensus<br/>Reached?}
    
    Consensus -->|No| Round
    Consensus -->|Yes| Success[Consensus Success<br/>Apply Principle]
    
    NoConsensus --> End[Experiment<br/>Continues]
    Success --> End
    
    %% Styling
    classDef start fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef outcome fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class Start,End start
    class Round,Speak,Statement,Check,VoteAgree,SecretVote,CountVotes process
    class AllSpoke,VoteProp,NextRound,Unanimous,Consensus decision
    class NoConsensus,Success outcome
"""
    
    create_mermaid_diagram(diagram, "clean_06_consensus_mechanism", "Consensus Detection Mechanism")

def install_mermaid_cli():
    """Provide instructions for installing Mermaid CLI."""
    print("\n" + "="*60)
    print("📋 MERMAID CLI INSTALLATION INSTRUCTIONS")
    print("="*60)
    print("\nTo generate PNG files from Mermaid diagrams, install the Mermaid CLI:")
    print("\n1. Install Node.js (if not already installed):")
    print("   - Download from: https://nodejs.org/")
    print("\n2. Install Mermaid CLI globally:")
    print("   npm install -g @mermaid-js/mermaid-cli")
    print("\n3. Re-run this script to generate PNG files")
    print("\nAlternatively, you can:")
    print("- Use the .mmd files with online tools like https://mermaid.live/")
    print("- Integrate with documentation tools that support Mermaid")
    print("- Use VS Code with Mermaid extensions")
    print("\n" + "="*60)

def main():
    """Generate all clean architectural diagrams."""
    
    print("🎨 Generating clean MAAI Frohlich Experiment architectural diagrams...")
    print("   Using Mermaid for cleaner, more readable diagrams")
    
    # Create output directory if it doesn't exist
    os.makedirs("documentation", exist_ok=True)
    
    print("\n📊 Creating diagrams...")
    create_overall_system_architecture()
    create_experimental_flow()
    create_agent_architecture()
    create_data_flow()
    create_bank_account_system()
    create_consensus_mechanism()
    
    print("\n✅ All Mermaid diagram files created!")
    print("\n📁 Generated files:")
    
    mermaid_files = [
        "clean_01_overall_architecture.mmd",
        "clean_02_experimental_flow.mmd", 
        "clean_03_agent_architecture.mmd",
        "clean_04_data_flow.mmd",
        "clean_05_bank_account_system.mmd",
        "clean_06_consensus_mechanism.mmd"
    ]
    
    for file in mermaid_files:
        file_path = f"documentation/{file}"
        if os.path.exists(file_path):
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} (failed to create)")
    
    # Check if Mermaid CLI is available
    try:
        result = subprocess.run(['mmdc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"\n🎉 Mermaid CLI found! PNG files generated successfully.")
        else:
            install_mermaid_cli()
    except FileNotFoundError:
        install_mermaid_cli()

if __name__ == "__main__":
    main()