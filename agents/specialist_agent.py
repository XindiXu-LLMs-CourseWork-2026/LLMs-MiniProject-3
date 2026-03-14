import json

from agents.models.agent_result import AgentResult
from agents.tools.tool_schemas import ALL_TOOL_FUNCTIONS
from config import ACTIVE_MODEL, client


def run_specialist_agent(
        agent_name: str,
        system_prompt: str,
        task: str,
        tool_schemas: list,
        max_iters: int = 8,
        verbose: bool = True,
        active_model=ACTIVE_MODEL
) -> AgentResult:
    """
    Core agentic loop used by every agent in this project.

    How it works:
      1. Sends system_prompt + task to the LLM
      2. If the LLM requests a tool call → looks up the function in ALL_TOOL_FUNCTIONS,
         executes it, appends the result to the message history, loops back to step 1
      3. When the LLM produces a response with no tool calls → returns an AgentResult

    Parameters
    ----------
    agent_name    : display name for logging
    system_prompt : the agent's persona, rules, and focus area
    task          : the specific question or sub-task for this agent
    tool_schemas  : list of schema dicts this agent is allowed to use
                    (pass [] for no tools — used by baseline)
    max_iters     : hard cap on iterations to prevent infinite loops
    verbose       : print each tool call as it happens
    """
    ### YOUR CODE HERE ###
    tools_called = []
    raw_data = {}
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]

    for i in range(max_iters):
        params = {
            "model": active_model,
            "messages": messages,
            "temperature": 0,
        }

        if tool_schemas:
            params["tools"] = tool_schemas
            params["tool_choice"] = "auto"

        response = client.chat.completions.create(**params)
        output = response.choices[0].message
        has_tool_call = output.tool_calls or []

        if not has_tool_call:
            answer = (output.content or "").strip()
            return AgentResult(
                agent_name=agent_name,
                answer=answer or "No answer generated",
                tools_called=tools_called,
                raw_data=raw_data
            )

        messages.append(output.model_dump(exclude_none=True))
        for tc in has_tool_call:
            name = tc.function.name
            arguments = tc.function.arguments or "{}"
            try:
                args = json.loads(arguments)
            except Exception:
                args = {}

            if verbose:
                print(f"{agent_name} is calling tool: {name}")

            func = ALL_TOOL_FUNCTIONS.get(name)
            if func:
                f_output = func(**args)
            else:
                f_output = {"Error": f"Function: {name} is not avaliable"}

            tools_called.append(name)
            raw_data.setdefault(name, []).append(f_output)
            results = json.dumps(f_output)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(results),
                }
            )

    return AgentResult(
        agent_name=agent_name,
        answer=f"Maximum iteration {max_iters} reached",
        tools_called=tools_called,
        raw_data=raw_data,
        issues_found=["maximum iteration reached"]
    )
