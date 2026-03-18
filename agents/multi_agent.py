import json
import time

from openai import RateLimitError

from agents.models.agent_result import AgentResult
from agents.specialist_agent import run_specialist_agent
from agents.tool_schemas import (
    SCHEMA_MOVERS,
    SCHEMA_NEWS,
    SCHEMA_OVERVIEW,
    SCHEMA_PRICE,
    SCHEMA_SQL,
    SCHEMA_STATUS,
    SCHEMA_TICKERS,
)
from config import ACTIVE_MODEL, get_client


class Orchestrator:
    def __init__(self, active_model=ACTIVE_MODEL):
        self.prompt = """
            You are the Orchestrator in a multi-agent stock analysis system.

            You are called repeatedly during execution. On each call, you receive:
            - the user's original question
            - conversation or replanning guidance
            - the current plan summary
            - executed step history
            - accumulated specialist result summaries

            Your job is to:
            1. Maintain or revise the current step-by-step plan.
            2. Decide whether more specialist work is still needed.
            3. If more work is needed, return exactly one next specialist instruction.

            Available specialists and their actual capabilities:

            - market_specialist
            Can do:
            - find tickers by sector or industry
            - get stock price performance over 1mo, 3mo, 6mo, ytd, or 1y
            - compare returns across tickers
            - identify top gainers, losers, and most active stocks
            - check whether markets are open or closed
            Cannot do:
            - retrieve P/E ratio, EPS, market cap, or 52-week high/low
            - retrieve news sentiment

            - fundamental_specialist
            Can do:
            - retrieve company overview data such as P/E ratio, EPS, market cap, 52-week high, and 52-week low
            - query the local stock database for filtering by sector, industry, market_cap, or exchange
            - identify companies and tickers from the local database
            Cannot do:
            - retrieve current or live stock price
            - calculate return or momentum from price history
            - retrieve news sentiment

            - news_specialist
            Can do:
            - retrieve recent news headlines and sentiment for a ticker
            - use the local database to identify relevant tickers before checking sentiment
            Cannot do:
            - retrieve price performance or current stock price
            - retrieve P/E ratio, EPS, market cap, or 52-week high/low

            Routing rules:
            - Questions about price performance, return ranking, gainers/losers, or market status -> market_specialist
            - Questions about P/E, EPS, market cap, 52-week high, or 52-week low -> fundamental_specialist
            - Questions about headlines, catalysts, or sentiment -> news_specialist
            - If a question spans multiple data types, call multiple specialists
            - Do not ask a specialist to do work outside its tool access

            Decomposition rules:
            - You may call the same specialist more than once if the task is easier or more reliable when broken into stages
            - If the task has multiple constraints, break it into clear subproblems
            - If multiple calls are made to the same specialist, make the instructions sequential and purposeful rather than repetitive

            Rules:
            - Choose the minimum number of specialist calls needed
            - The same specialist may appear multiple times across repeated calls if needed
            - Emit at most one executable specialist step per call
            - Do not duplicate work unless a later step depends on the earlier step
            - If earlier validated results are still useful, keep them and build on them instead of restarting
            - If a prior step failed or was incomplete, revise the next step accordingly
            - Each instruction must be specific, concise, and executable with that specialist's tools
            - Do not explicitly instruct a specialist to retrieve all stocks from the database or dataset
            - State the goal, constraints, and desired output, and let the specialist decide how much data to retrieve
            - Prefer minimal, targeted instructions over broad data-retrieval instructions
            - Return status = "done" only when no additional specialist steps are needed before synthesis
            - Do not answer the user directly
            - If the user is only greeting, making small talk, or asking something that does not require stock-analysis tools, return status = "done" with next_step = null
            - Do not ask follow-up questions

            Instruction independence rule:
            - Every specialist instruction must be self-contained.
            - Do not refer to hidden prior outputs using phrases like "those companies", "the earlier result" unless those exact tickers or companies are explicitly included in the instruction.
            - A specialist can only act on the information written in its own task plus its own tools.
            - If a later step depends on an earlier step, the earlier result must first be obtained and then explicitly passed into a new instruction.
        """
        self.active_model = active_model

    def run(
        self,
        question: str,
        conv_hist: str = "",
        current_plan: str = "",
        execution_history: list | None = None,
        specialist_results: list | None = None,
    ):
        cxt = json.dumps(
            {
                "question": question,
                "conversation_history": conv_hist,
                "current_plan": current_plan,
                "executed_step_history": execution_history or [],
                "specialist_results_summary": specialist_results or [],
            }
        )
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": cxt},
        ]
        response_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "orchestrator_result",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "plan": {"type": "string"},
                        "status": {"type": "string", "enum": ["continue", "done"]},
                        "next_step": {
                            "anyOf": [
                                {"type": "null"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "agent_name": {
                                            "type": "string",
                                            "enum": [
                                                "market_specialist",
                                                "fundamental_specialist",
                                                "news_specialist",
                                            ],
                                        },
                                        "instruction": {"type": "string"},
                                    },
                                    "required": ["agent_name", "instruction"],
                                    "additionalProperties": False,
                                },
                            ]
                        },
                    },
                    "required": ["plan", "status", "next_step"],
                    "additionalProperties": False,
                },
            },
        }

        params = {
            "model": self.active_model,
            "messages": messages,
            "response_format": response_schema,
            "temperature": 0,
        }
        client = get_client()
        try:
            response = client.chat.completions.create(**params)
        except RateLimitError:
            print("Rate limit hit, waiting and retrying...")
            time.sleep(2)
            response = client.chat.completions.create(**params)
        output = response.choices[0].message.content
        results = json.loads((output or "").strip())

        return AgentResult(
            agent_name="Orchestrator",
            answer=results["plan"],
            raw_data={
                "status": results["status"],
                "next_step": results["next_step"],
            },
        )


class Specialist:
    def __init__(self, name, schema, active_model=ACTIVE_MODEL):
        self.name = name
        self.prompt = """ """
        self.schema = schema
        self.active_model = active_model

    def run(self, task: str, cxt: str = ""):
        task += cxt
        specialist_results = run_specialist_agent(
            agent_name=self.name,
            system_prompt=self.prompt,
            task=task,
            tool_schemas=self.schema,
            max_iters=10,
            verbose=True,
            active_model=self.active_model,
        )

        return specialist_results


class Critic:
    def __init__(self, active_model=ACTIVE_MODEL):
        self.prompt = """
            You are a critic reviewing another specialist agent's output.
            Decide whether the specialist answer is acceptable based only on the provided task, answer, raw_data, and issues it found.

            Core evaluation rule:
            - Use only the provided evidence.
            - Do not guess, infer missing values, or invent conflicts.
            - If the answer is a ranking, comparison, top-k result, filter result, or any numerically constrained claim, explicitly compare the relevant values from the evidence before judging.
            - Read the raw_data carefully and base your judgment only on values that are actually present there.
            - Never mark an answer wrong unless you can point to a specific contradiction with the provided evidence.
            - If the evidence is insufficient to prove the answer wrong, prefer explaining that the evidence is insufficient rather than inventing a contradiction.
            - A valid negative finding should pass: if the task asks for stocks that satisfy some criteria and the evidence shows that no retrieved stocks satisfy those criteria, then an answer that clearly says no stocks matched should be judged acceptable.
            - If the specialist correctly identifies that no stock matches the task criteria, pass the answer and explain which checked evidence supports that negative finding so the orchestrator can reuse it.

            Consistency check before finalizing:
            1. Identify the exact values or records relevant to the task.
            2. If ranking is required, sort them mentally by the provided numbers before judging.
            3. Check that your reasoning matches those values exactly.
            4. If your reasoning would contradict the evidence, revise the judgment before responding.
            5. If the task is a filter/search and every relevant candidate fails the required condition, treat "no matches found" as a valid result rather than a failure.

            Return JSON with:
            - judgement: 1 if the answer is acceptable, 0 otherwise
            - reasoning: brief explanation why the specialist agent answer is pass or fail
            - confidence: Set confidence as a number from 0 to 1 representing how certain you are that your judgment is correct.
                Use higher confidence when the evidence in raw_data clearly supports your judgment.
                Use lower confidence when the evidence is incomplete, ambiguous, contradictory, or hard to verify.
                Do not use confidence to express whether the answer is good or bad; use it only to express certainty in your evaluation.

            Be strict. Do not invent evidence not present in the input. Do not follow-up.
        """
        self.active_model = active_model

    def run(self, task, specalist_results: AgentResult):
        specialist_response = {
            "task": task,
            "specialist": specalist_results.agent_name,
            "answer": specalist_results.answer,
            "raw_data": specalist_results.raw_data,
            "issues_found": specalist_results.issues_found,
        }
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": json.dumps(specialist_response)},
        ]
        response_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "critic_result",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "judgement": {"type": "number"},
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["judgement", "reasoning", "confidence"],
                    "additionalProperties": False,
                },
            },
        }

        params = {
            "model": self.active_model,
            "messages": messages,
            "response_format": response_schema,
            "temperature": 0,
        }
        client = get_client()
        try:
            response = client.chat.completions.create(**params)
        except RateLimitError:
            print("Rate limit hit, waiting and retrying...")
            time.sleep(2)
            response = client.chat.completions.create(**params)
        output = response.choices[0].message.content
        results = json.loads((output or "").strip())

        return AgentResult(
            agent_name="Critic",
            answer=(int(results["judgement"]) == 1),
            confidence=results["confidence"],
            reasoning=results["reasoning"],
        )


class Synthsizer:
    def __init__(self, active_model=ACTIVE_MODEL):
        self.prompt = """
            You are the Synthesizer in a multi-agent stock analysis system.

            You will receive:
            - the user's original question
            - the orchestrator's plan
            - a list of executed specialist results with status

            Your job is to decide whether the available specialist results are sufficient to answer the user's question.

            Important distinction:
            1. If the evidence is incomplete, identity-inconsistent, mismatched, or insufficiently grounded, then the result is not sufficient and replanning is needed.
            2. If the evidence is valid, internally consistent, and sufficient to evaluate the user's condition, but the condition yields no matching result, then this is still sufficient and should be answered directly as a valid negative finding.

            Output rules:
            - Return structured JSON only.
            - Return exactly these fields:
            - confidence
            - answer
            - reasoning

            Interpret confidence as a binary sufficiency flag:
            - confidence = 1 means the specialist results are sufficient to answer the user's question
            - confidence = 0 means the specialist results are not sufficient and the orchestrator should refine the plan

            Field meanings:
            - If confidence = 1, answer must be the final user-facing answer
            - If confidence = 0, answer must be a replanning instruction for the orchestrator
            - reasoning must explain why the evidence is sufficient or insufficient

            Decision rules:
            - Set confidence = 1 if the specialist results are enough to answer the user's question directly and responsibly, even if the answer is that no matching fact, stock, or condition exists
            - Set confidence = 0 only when key evidence is missing, the results are not actually responsive to the question, or identity/conflict issues prevent a reliable conclusion
            - Contradictory but still interpretable evidence does not automatically require replanning; use replanning only when the contradiction blocks a trustworthy answer
            - When results are only partially sufficient, preserve any reliable intermediate findings, distinguish reusable evidence from missing evidence, and avoid recommending repeated work that already produced valid results
            - Use passed specialist results as evidence and treat failed specialist steps as missing or incomplete evidence
            - Do not invent facts, numbers, or claims not present in the input
            - Use only the provided specialist results as evidence
            - Do not mention internal roles such as orchestrator, specialist, critic, or synthesizer in the final user-facing answer

            If confidence = 1:
            - provide a direct, honest answer
            - if no matching stocks or facts exist, say so clearly

            If confidence = 0:
            - explain exactly what is wrong with the evidence
            - tell the orchestrator what needs to be rechecked, clarified, or recomputed

            If confidence = 0:
            - do not try to answer the user's question
            - use answer to tell the orchestrator exactly how the plan should be refined
            - be specific about what additional evidence, tool usage, or specialist routing is needed
            - include any specialist results that are still useful and should be reused
            - identify which partial findings are reliable, which are incomplete, and which should be ignored
            - when possible, suggest the next specialist call using the useful partial evidence already gathered
        """
        self.active_model = active_model

    def run(self, question: str, plan, valid_results: list):
        verified_results = json.dumps(
            {
                "question": question,
                "orchestrator_plan": plan,
                "valid_results": valid_results,
            }
        )
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": verified_results},
        ]
        response_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "synthesizer_result",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "confidence": {"type": "number"},
                        "answer": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["confidence", "answer", "reasoning"],
                    "additionalProperties": False,
                },
            },
        }

        params = {
            "model": self.active_model,
            "messages": messages,
            "response_format": response_schema,
            "temperature": 0,
        }
        client = get_client()
        try:
            response = client.chat.completions.create(**params)
        except RateLimitError:
            print("Rate limit hit, waiting and retrying...")
            time.sleep(2)
            response = client.chat.completions.create(**params)
        output = response.choices[0].message.content
        results = json.loads((output or "").strip())

        return AgentResult(
            agent_name="Synthesizer",
            answer=results["answer"],
            confidence=float(results["confidence"]),
            reasoning=results["reasoning"],
        )


SPECIALIST_PROMPTS = {
    "market_specialist": """
        You are market_specialist in a multi-agent stock analysis system.

        Your job is to answer only market- and price-related sub-tasks using the tools you have been given.

        Focus on:
        - price performance
        - momentum and trend
        - relative price comparisons
        - market open/closed status
        - top gainers, losers, and active stocks

        Avaliable tools:
        - get_tickers_by_sector:
        Use when the user asks about a sector/industry (e.g., energy, semiconductor, finance, tech stocks in DB). Returns all stocks in a sector or industry from the local database.
        - get_price_performance:
        Use for return comparisons over periods. Returns % price change for tickers over a period ('1mo','3mo','6mo','ytd','1y').
        - get_market_status:
        Use when asked whether markets/exchanges are open.
        - get_top_gainers_losers:
        Use for today’s top gainers/losers/most active.

        Rules:
        - Use only tool evidence, not guesses
        - Do not make claims about fundamentals, valuation, earnings, or news unless they are explicitly present in the provided tool output
        - If the task involves a sector or industry, first identify the relevant tickers before comparing price performance
        - If ranking is requested, ensure the ranking is based on the returned numbers
        - If data is missing or a tool fails, say so clearly
        - Keep the final answer concise and evidence-based
        - Include exact figures when available
        - Do not answer beyond the assigned task

        When you are ready to give the final answer, return:
        - answer: the best direct answer to the assigned task
        - confidence: a number from 0 to 1 showing how confident you are that your answer is correct and sufficiently supported by the available tool results
        - reasoning: a brief explanation of why the answer is supported, including any important limitations or missing evidence

        Set confidence higher when the tool results directly support the answer.
        Set confidence lower when data is missing, ambiguous, incomplete, or partially conflicting.
        Do not invent facts that are not present in tool outputs.
        """,
    "fundamental_specialist": """
        You are fundamental_specialist in a multi-agent stock analysis system.

        Your job is to answer only fundamentals- and company-overview-related sub-tasks using the tools you have been given.

        Focus on:
        - P/E ratio
        - EPS
        - market cap
        - 52-week high and low
        - company-level comparisons
        - sector and exchange filtering through the local database

        Avaliable tools:
        - get_tickers_by_sector:
        Use when the user asks about a sector/industry (e.g., energy, semiconductor, finance, tech stocks in DB). Returns all stocks in a sector or industry from the local database.
        - query_local_db:
        Use for custom filtering/counting in stocks.db. Fields include ticker, company, sector, industry, market_cap (Large/Mid/Small), exchange. Make sure to use A valid SQL SELECT statement as input.
        - get_company_overview:
        Use for company fundamentals (P/E, EPS, market cap, 52-week high/low).

        Rules:
        - Use only tool evidence, not guesses
        - Do not make claims about recent price moves or news sentiment unless explicitly given in the task input
        - Before the main task, only if the exact sector or industry label is uncertain, only use SQL patterns like:
          SELECT DISTINCT sector, industry FROM stocks WHERE LOWER(sector) LIKE '%keyword%' OR LOWER(industry) LIKE '%keyword%' ORDER BY sector, industry;
          and then determine the correct sector ot industry name to call
        - If the task involves selecting companies from a sector, exchange, or market-cap bucket, use the database tools first
        - When comparing companies, present the exact values clearly
        - If a metric is missing or a tool fails, say so explicitly
        - Keep the final answer concise and analytical
        - Do not answer beyond the assigned task

        When you are ready to give the final answer, return:
        - answer: the best direct answer to the assigned task
        - confidence: a number from 0 to 1 showing how confident you are that your answer is correct and sufficiently supported by the available tool results
        - reasoning: a brief explanation of why the answer is supported, including any important limitations or missing evidence

        Set confidence higher when the tool results directly support the answer.
        Set confidence lower when data is missing, ambiguous, incomplete, or partially conflicting.
        Do not invent facts that are not present in tool outputs.
        """,
    "news_specialist": """
        You are news_specialist in a multi-agent stock analysis system.

        Your job is to answer only news- and sentiment-related sub-tasks using the tools you have been given.

        Focus on:
        - recent headlines
        - sentiment labels
        - sentiment scores
        - company-specific or sector-related news context

        Tools avaliable:
        - query_local_db:
        Use for custom filtering/counting in stocks.db. Fields include ticker, company, sector, industry, market_cap (Large/Mid/Small), exchange. Make sure to use A valid SQL SELECT statement as input.
        - get_news_sentiment:
        Use for sentiment/headlines for specific tickers.

        Rules:
        - Use only tool evidence, not guesses
        - Do not make claims about valuation, earnings, or price performance unless explicitly present in the provided data
        - Before the main task, only if the exact sector or industry label is uncertain, only use SQL patterns like:
          SELECT DISTINCT sector, industry FROM stocks WHERE LOWER(sector) LIKE '%keyword%' OR LOWER(industry) LIKE '%keyword%' ORDER BY sector, industry;
          and then determine the correct sector ot industry name to call
        - If the task involves selecting companies from a sector, exchange, or market-cap bucket, use the database tools first
        - If the task refers to a sector or group of companies, use the database tool only to identify relevant tickers
        - Summarize the most relevant headlines and sentiment clearly
        - If sentiment is mixed, say that explicitly
        - If there are too many possible tickers, prioritize the ones named in the task
        - If data is missing or a tool fails, say so clearly
        - Keep the answer concise and directly tied to the assigned task
        - Do not answer beyond the assigned task

        When you are ready to give the final answer, return:
        - answer: the best direct answer to the assigned task
        - confidence: a number from 0 to 1 showing how confident you are that your answer is correct and sufficiently supported by the available tool results
        - reasoning: a brief explanation of why the answer is supported, including any important limitations or missing evidence

        Set confidence higher when the tool results directly support the answer.
        Set confidence lower when data is missing, ambiguous, incomplete, or partially conflicting.
        Do not invent facts that are not present in tool outputs.
        """,
}


def _append_context(existing: str, addition: str) -> str:
    if not addition:
        return existing
    if not existing:
        return addition
    return f"{existing}\n\n{addition}"


def _build_step_summary(
    step_index: int,
    agent_name: str,
    task: str,
    status: str,
    specialist_result: AgentResult,
    critic_reasoning: str,
    attempts: int,
):
    return {
        "step_index": step_index,
        "agent_name": agent_name,
        "task": task,
        "status": status,
        "answer": specialist_result.answer,
        "confidence": specialist_result.confidence,
        "tools_called": specialist_result.tools_called,
        "issues_found": specialist_result.issues_found,
        "critic_reasoning": critic_reasoning,
        "attempts": attempts,
    }


def _build_execution_record(step_summary: dict):
    return {
        "step_index": step_summary["step_index"],
        "agent_name": step_summary["agent_name"],
        "task": step_summary["task"],
        "status": step_summary["status"],
        "critic_reasoning": step_summary["critic_reasoning"],
        "attempts": step_summary["attempts"],
    }


def run_multi_agent(question, conv_hist="", active_model=ACTIVE_MODEL):
    t0 = time.perf_counter()

    market_tools = [SCHEMA_TICKERS, SCHEMA_PRICE, SCHEMA_STATUS, SCHEMA_MOVERS]
    fundamental_tools = [SCHEMA_OVERVIEW, SCHEMA_SQL, SCHEMA_TICKERS]
    sentiment_tools = [SCHEMA_NEWS, SCHEMA_SQL]

    orchestrator = Orchestrator(active_model)
    market_specialist = Specialist(
        "market_specialist",
        schema=market_tools,
        active_model=active_model,
    )
    fundamental_specialist = Specialist(
        "fundamental_specialist",
        schema=fundamental_tools,
        active_model=active_model,
    )
    news_specialist = Specialist(
        "news_specialist",
        schema=sentiment_tools,
        active_model=active_model,
    )
    critic = Critic(active_model)
    synthesizer = Synthsizer(active_model)

    specialists = {
        "market_specialist": market_specialist,
        "fundamental_specialist": fundamental_specialist,
        "news_specialist": news_specialist,
    }
    specialist_summaries = []
    specialist_results = []
    execution_history = []

    max_replans = 5
    max_specialist_attempts = 5
    max_plan_steps = 5
    orchestrator_context = conv_hist.strip()

    replan_round = 0
    while replan_round < max_replans:
        current_plan = ""
        latest_plan = ""
        step_counter = 0
        orchestrator_done = False

        while step_counter < max_plan_steps:
            orchestrator_results = orchestrator.run(
                question=question,
                conv_hist=orchestrator_context,
                current_plan=current_plan,
                execution_history=execution_history,
                specialist_results=specialist_summaries,
            )
            latest_plan = orchestrator_results.answer
            current_plan = latest_plan
            orchestration_state = orchestrator_results.raw_data
            status = orchestration_state["status"]
            next_step = orchestration_state["next_step"]

            print(f"current plan: {current_plan}")

            if status == "done":
                orchestrator_done = True
                break

            if not next_step:
                raise ValueError("Orchestrator returned continue without next_step")

            specialist_name = next_step["agent_name"]
            task = next_step["instruction"]
            print(f"task:{task}")

            specialists[specialist_name].prompt = SPECIALIST_PROMPTS[specialist_name]

            task_success = False
            task_attempt = 0
            feedback_context = ""
            critic_reasoning = ""
            sp_results = AgentResult(
                agent_name=specialist_name,
                answer="Specialist failed in retrieving relevant infomation.",
                confidence=0.0,
                issues_found=["specialist did not complete successfully"],
            )

            while not task_success and task_attempt < max_specialist_attempts:
                task_attempt += 1
                sp_results = specialists[specialist_name].run(
                    task=task,
                    cxt=feedback_context,
                )
                critic_results = critic.run(task=task, specalist_results=sp_results)
                critic_reasoning = critic_results.reasoning

                if critic_results.answer:
                    task_success = True
                else:
                    print(f"{specialist_name} has failed critic's evaluation")
                    feedback_context = (
                        "\n\nYour last answer failed!\n\n"
                        f"last answer:{sp_results.answer}\n\n"
                        f"failure reason: {critic_results.reasoning}"
                    )
                    print(feedback_context)

            if task_success:
                print(f"{specialist_name} has passed critic's evaluation")
                step_status = "passed"
            else:
                print(f"{specialist_name} has reached it maximum attempts")
                step_status = "failed"
                if not sp_results.answer:
                    sp_results.answer = "Specialist failed in retrieving relevant infomation."

            step_index = len(execution_history) + 1
            step_summary = _build_step_summary(
                step_index=step_index,
                agent_name=specialist_name,
                task=task,
                status=step_status,
                specialist_result=sp_results,
                critic_reasoning=critic_reasoning,
                attempts=task_attempt,
            )
            specialist_summaries.append(step_summary)
            execution_history.append(_build_execution_record(step_summary))
            specialist_results.append(sp_results)
            step_counter += 1

        if not orchestrator_done:
            orchestrator_context = _append_context(
                orchestrator_context,
                (
                    "The orchestrator did not finish the plan within the allowed "
                    f"step budget of {max_plan_steps}. Revise the plan to be more targeted."
                ),
            )
            replan_round += 1
            continue

        synthesizer_results = synthesizer.run(
            question=question,
            plan=latest_plan,
            valid_results=specialist_summaries,
        )
        if synthesizer_results.confidence == 1.0:
            print("reply is ready")
            wall_time = round(time.perf_counter() - t0, 3)
            return {
                "final_answer": synthesizer_results.answer,
                "agent_results": specialist_results,
                "elapsed_sec": wall_time,
                "architecture": "orchestrator-critic",
            }

        print("specialist results insufficent in answering user's question, returning to orchestrator replanning")
        orchestrator_context = _append_context(
            orchestrator_context,
            (
                "Synthesizer said the executed plan is insufficient.\n\n"
                f"Reason:\n{synthesizer_results.reasoning}\n\n"
                f"Replanning guidance:\n{synthesizer_results.answer}"
            ),
        )
        replan_round += 1

    wall_time = round(time.perf_counter() - t0, 3)
    return {
        "final_answer": "Sorry, I am not being able to answer your question now.",
        "agent_results": specialist_results,
        "elapsed_sec": wall_time,
        "architecture": "orchestrator-critic",
    }
