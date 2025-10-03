note to codex: Dont delete
note to claude: Dont delete


Done
Fix testing or leave it as is --> Done
Implement GEMINI API natively --> Done 
Fix Phase counter --> Done
Reasoing parameter not funcitnla? --> Done
Memory Update Phae 1 emphasis payoff --> Done
More emphasis on the recent activity simialray to phase 1 demonstration rounds --> Done
Probabilites need to be explained --> Done 
Example amount in voting call remove --> Done
Phase 2 description --> probabilites are different stakes are much higher --> Already there (Reasoning Call)
Memory update before voting decisions  --> Done 
Discussion hisortry bold in memory update call --> Done
Round counter in post disucssion phase 2 is wrong --> Don
Memory Update Call in phase 2; phase wrong, round wrong --> Done
Ollama integration --> Done
post discussion phase 2, distribution communication to agent  --> Done
Issue: Reasoning Prompt content, not header, in instruct prompt bold ???  (statement call) --> Target: Reasoning content not bold  --> Done, I guess...
1. Issue: Discussion History content, not header, in instruct prompt bold ??? (statement call) --> Target: Discussion History content not bold --> Done
Wrong > in floor range --> Done
Principle description end of phase 2 wehn no concsensus wasreached --> Done


WIP
These denominators in instruct prompt  "Phase 1 – Initial ranking." 




Check if problem still there
Investigate why so many runs failed --> Probably fixed --> Test needed



Backlog

voting round message in ballot is false "Voting Decision Point - Round 1 of 10" 





Prepare Repo for Release 
--> Documentation
--> Test Suite



Nice to have
Legacy Code 
Testing Suite Update
GUI 
LOG  Each Agent what the did, 
Memory via OpenAI Memory

Quo vadis?
2. **Free-Text System** (alternative approach):
   ```
   Format: "My ballot choice is maximizing average with floor constraint with a floor constraint of $15,000"
   ```



“Return your complete updated memory incorporating insights from the recent activity. 
Your memory is given to you in every interaction and gives you your knowledge on yourself and the experiment. Strucutre your memory as it fits you best. You are given your previous memory and recent activity of the experiment. Return the complete memory. 

Your Previous Memory:
{current_memory}

You are participating in an experiment studying principles of justice and income distribution.

The experiment has two main phases:

PHASE 1: You will individually learn about and apply four different principles of justice to income distributions. You will be asked to rank these principles by preference and apply them to specific scenarios. Your choices will affect your earnings.

PHASE 2: You will join a group discussion to reach consensus on which principle of justice the group should adopt. The group’s chosen principle will then be applied to determine everyone’s final earnings.

Throughout the experiment, engage thoughtfully with the principles and other participants.

Recent Activity:
{round_content}

RETURN: Your complete updated memory (not incremental changes or prefixes like ‘Memory update:’)”