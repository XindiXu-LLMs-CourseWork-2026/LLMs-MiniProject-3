from agents.models.agent_result import AgentResult
from agents.specialist_agent import run_specialist_agent


def run_baseline(question: str, verbose: bool = True) -> AgentResult:
    # Implement a single LLM call with no tools.
    # Use run_specialist_agent() with an empty tool_schemas list — or make the call directly.
    # Return an AgentResult with agent_name="Baseline" and tools_called=[].
    ### YOUR CODE HERE
    system_prompt = (
        "You are a finance assistant. "
        "Answer clearly and concisely. No follow-ups."
        "If you are unsure or data may be outdated, say so explicitly."
    )
    return run_specialist_agent(
        agent_name="Baseline Agent",
        system_prompt=system_prompt,
        task=question,
        tool_schemas=[],
        max_iters=1,
        verbose=verbose
    )