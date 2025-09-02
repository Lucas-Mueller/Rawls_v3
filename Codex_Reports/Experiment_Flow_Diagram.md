How# Experiment Flow Diagrams

Below are sequence and component-level diagrams illustrating the end-to-end experiment flow, the agent calls, and the content elements passed on each call.

```mermaid
sequenceDiagram
    autonumber
    participant Orchestrator as Phase1/2 Manager
    participant LM as LanguageManager
    participant PA as ParticipantAgent (LLM)
    participant MS as MemoryService
    participant SMM as SelectiveMemoryManager
    participant MM as MemoryManager
    participant UA as UtilityAgent
    participant DS as DiscussionService
    participant VS as VotingService
    participant GDS as GroupDiscussionState

    Note over Orchestrator,PA: Instruction (format_context_info)
    Note over Orchestrator,PA: Name, Role, Bank, Phase, Round, Memory, Personality, Phase Instructions, Language Instruction, (Optional) Experiment Explanation

    rect rgb(240,250,255)
    Note over Orchestrator,PA: Phase 1 — per round
    Orchestrator->>PA: Runner.run(prompt, context)
    Orchestrator->>MM: prompt_agent_for_memory_update(agent, context, round_content, style)
    MM->>PA: update_memory(memory_update_prompt, bank_balance)
    alt Memory > 115% limit
        MM->>UA: compress with prompts.memory_compression_prompt
        UA-->>MM: compressed_memory
    end
    MM-->>Orchestrator: updated_memory
    end

    rect rgb(255,248,240)
    Note over Orchestrator,MS: Phase 2 init — carry Phase 1 memory
    Orchestrator->>MS: validate_and_sanitize_memory(final_memory_state, limit)
    MS-->>Orchestrator: validated_memory (set on ParticipantContext)
    end

    rect rgb(245,255,245)
    Note over Orchestrator,PA: Phase 2 — discussion round N
    Orchestrator->>DS: build_discussion_prompt(GDS.public_history, names, N, max)
    DS-->>Orchestrator: discussion_prompt
    Orchestrator->>PA: Runner.run(discussion_prompt, context)
    PA-->>Orchestrator: statement (and reasoning)
    Orchestrator->>MS: update_discussion_memory(statement, reasoning, round=N)
    MS->>SMM: update_memory_selective(content, event=DISCUSSION_STATEMENT)
    SMM->>MM: prompt_agent_for_memory_update(...)
    MM-->>SMM: updated_memory
    SMM-->>MS: updated_memory
    MS-->>Orchestrator: updated_memory (persist to context)
    end

    rect rgb(255,245,250)
    Note over Orchestrator,PA: Phase 2 — possible voting
    Orchestrator->>VS: prompt_for_vote_initiation(agent_recent_statement)
    VS->>PA: Runner.run(vote_initiation_prompt, context)
    PA-->>VS: yes/no
    VS-->>Orchestrator: wants_vote
    Orchestrator->>MS: update_vote_initiation_decision_memory(wants_vote)
    MS->>SMM: update_memory_selective(event=VOTE_INITIATION_RESPONSE)
    SMM-->>MS: appended_memory
    Note right of MS: If memory > 90% limit after append → compress via MemoryManager

    alt All confirm
        Orchestrator->>VS: conduct_secret_ballot(two-stage)
        VS->>PA: stage prompts (principle, amount)
        PA-->>VS: selections
        Orchestrator->>MS: update_ballot_selection_memory / update_amount_specification_memory
        MS->>SMM: update_memory_selective(event=BALLOT_SELECTION/AMOUNT_SPECIFICATION)
        SMM-->>MS: appended_memory (with post-append compression check)
    end
    end

    rect rgb(250,250,240)
    Note over Orchestrator,MS: Finalization (consensus or end)
    Orchestrator->>MS: update_final_results_memory(result_content, earnings, consensus)
    MS->>SMM: update_memory_selective(event=FINAL_RESULTS)
    SMM->>MM: prompt_agent_for_memory_update(...)
    MM-->>SMM: updated_memory
    SMM-->>MS: updated_memory
    MS-->>Orchestrator: updated_memory
    end
```

```mermaid
flowchart LR
    subgraph Phase1
      P1M[Phase1Manager]
      MM[MemoryManager]
      UA[UtilityAgent]
      PA[ParticipantAgent]
      LM[LanguageManager]
      P1M -->|Runner.run + Instructions| PA
      P1M -->|round_content| MM
      MM -->|memory_update_prompt (prompts.memory_*)| PA
      MM -->|compress if needed| UA
      LM -. provides .-> MM
      LM -. provides .-> P1M
    end

    subgraph Phase2
      P2M[Phase2Manager]
      MS[MemoryService]
      SMM[SelectiveMemoryManager]
      DS[DiscussionService]
      VS[VotingService]
      GDS[GroupDiscussionState]
      P2M -->|init| MS
      MS -->|validate carryover| P2M
      P2M --> DS -->|discussion_prompt| P2M -->|Runner.run + Instructions| PA
      P2M -->|statement,reasoning| MS --> SMM --> MM --> PA
      VS -->|prompts| PA --> VS
      P2M -->|vote mem updates| MS --> SMM
      MS -->|post-append check| MM
    end

    PA --- LM
```

Notes
- Instructions always include: Name, Role, Bank Balance, Phase, Round, Memory (full display), Personality, Phase Instructions, Language Instruction, optional Experiment Explanation.
- Memory updates: complex events → full LLM update via MemoryManager; simple events → append, then post-append compression if near limit.
- Discussion history is embedded in discussion prompts (not in the global instruction block) via `DiscussionService.build_discussion_prompt`.
