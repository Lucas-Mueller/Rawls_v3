"""
Voting tools for participant agents in the Frohlich Experiment.
"""
from agents import function_tool
from models import ParticipantContext, ExperimentPhase


def _is_phase2_group_discussion(ctx, agent) -> bool:
    """
    Check if we're currently in Phase 2 group discussion (not final ranking).
    
    Args:
        ctx: Current run context
        agent: Current agent instance
        
    Returns:
        bool: True if in Phase 2 group discussion, False otherwise
    """
    if not ctx or not hasattr(ctx, 'context') or not ctx.context:
        return False
    
    context = ctx.context
    return (context.phase == ExperimentPhase.PHASE_2 and 
            context.role_description != "FinalRanking")


@function_tool(is_enabled=_is_phase2_group_discussion)
async def propose_vote() -> dict:
    """
    Propose that the group proceeds to a formal vote on justice principles.
    
    This will initiate a confirmation phase where all participants must agree
    to proceed with voting. If all participants agree, a secret ballot will be conducted.
    Only use this when you believe the group is ready to make a final decision.
    
    Returns:
        dict: Action result indicating the vote proposal was submitted
    """
    return {
        "action": "propose_vote", 
        "success": True,
        "message": "Vote proposal submitted. Confirmation phase will begin."
    }