import json
import time

from agents.specialist_agent import run_specialist_agent
from agents.models.agent_result import AgentResult
from agents.tools.tool_schemas import SCHEMA_TICKERS, SCHEMA_PRICE, SCHEMA_STATUS, SCHEMA_MOVERS, SCHEMA_OVERVIEW, \
    SCHEMA_SQL, SCHEMA_NEWS
from config import ACTIVE_MODEL, client


class Orchestrator:
    def __init__(self, active_model):
        self.prompt = """
            You are the Orchestrator in a multi-agent stock analysis system.

            Your job is to:
            1. Write a detailed plan for answering the user's question.
            2. Decide which specialists are needed.
            3. Give each selected specialist one concrete instruction based on what that specialist can actually do.

            Available specialists and their real capabilities:

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
            - identify companies/tickers from the local database
            Cannot do:
            - retrieve current or live stock price
            - calculate return or momentum from market price history
            - retrieve news sentiment

            - news_specialist
            Can do:
            - retrieve recent news headlines and sentiment for a ticker
            - use the local database to identify relevant tickers before checking sentiment
            Cannot do:
            - retrieve price performance or current stock price
            - retrieve P/E ratio, EPS, market cap, or 52-week high/low

            Routing rules:
            - Questions about P/E, EPS, market cap, 52-week high, or 52-week low -> fundamental_specialist
            - Questions about price performance, return ranking, gainers/losers, or market status -> market_specialist
            - Questions about headlines, catalysts, or sentiment -> news_specialist
            - If a question spans multiple data types, call multiple specialists
            - If a tool already provides the requested metric directly, ask for that metric directly rather than asking the specialist to derive it manually

            Important examples:
            - If the user asks for P/E ratio, send it to fundamental_specialist and ask it to retrieve the returned pe_ratio directly
            - Do not ask fundamental_specialist for current market price
            - If the user asks for current or recent stock movement, send it to market_specialist
            - If the user asks for both return and P/E ratio, use both market_specialist and fundamental_specialist
            - If the user asks for sentiment plus returns, use both news_specialist and market_specialist

            Rules:
            - Choose the minimum number of specialists needed
            - Do not duplicate work across specialists
            - Each instruction must be specific, concise, and executable with that specialist's tools
            - Do not answer the user directly
            - If the user is only greeting, making small talk, or asking something that does not require stock-analysis tools, return an empty specialists_to_call list
            - Do not ask follow-up questions
        """
        self.active_model = active_model

    def run(self, question: str, conv_hist: str = ""):
        cxt = (
            f"question:\n{question}\n\n"
            f"conversation history:\n{conv_hist}"
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
                        "specialists_to_call": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "agent_name": {"type": "string",
                                                   "enum": ["market_specialist", "fundamental_specialist",
                                                            "news_specialist"]},
                                    "instruction": {"type": "string"},
                                },
                                "required": ["agent_name", "instruction"],
                                "additionalProperties": False,
                            }
                        },
                    },
                    "required": ["plan", "specialists_to_call"],
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
        response = client.chat.completions.create(**params)
        output = response.choices[0].message.content
        results = json.loads((output or "").strip())

        return AgentResult(
            agent_name="Orchestrator",
            answer=results["plan"],
            raw_data={"specialist_to_call": results["specialists_to_call"]},
        )


class Specialist:
    def __init__(self, name, schema, active_model=ACTIVE_MODEL):
        self.name = name
        self.prompt = """ """
        self.schema = schema
        self.active_model=active_model

    def run(self, task: str, cxt: str = ""):
        task += cxt
        specialist_results = run_specialist_agent(
            agent_name=self.name,
            system_prompt=self.prompt,
            task=task,
            tool_schemas=self.schema,
            max_iters=5,
            verbose=True,
            active_model=self.active_model
        )

        return specialist_results


class Critic:
    def __init__(self, active_model=ACTIVE_MODEL):
        self.prompt = """
            You are a critic reviewing another specialist agent's output.
            Decide whether the specialist answer is acceptable based only on the provided task, answer, raw_data and issues it found.
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
            "temperature": 0
        }
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

            You will receive a JSON input containing:
            - the user's original question
            - the orchestrator's plan
            - a list of validated specialist results

            The specialist results have already passed critic review, but they still may be incomplete, partially relevant, or mutually contradictory.

            Your job is to decide whether the validated results are sufficient to answer the user's question.

            Output rules:
            - Always return structured JSON only.
            - Return exactly these fields:
            - confidence
            - answer
            - reasoning

            Interpret confidence as a binary sufficiency flag:
            - confidence = 1 means the validated results are sufficient to answer the user's question
            - confidence = 0 means the validated results are not sufficient to answer the user's question

            Meaning of answer:
            - If confidence = 1, answer must be the final user-facing answer
            - If confidence = 0, answer must first state what's the current specialist results are and then provide suggestions for the orchestrator describing what additional information or specialist work is needed

            Meaning of reasoning:
            - Explain why the validated results are sufficient or insufficient
            - Include any important missing information, unresolved conflicts, or gaps in evidence

            Decision rules:
            - Set confidence = 1 only if the validated results are enough to answer the user's question directly and responsibly
            - Set confidence = 0 if key required evidence is missing, if the results do not actually answer the question, or if contradictions prevent a reliable answer
            - Contradictions should only cause failure if they materially affect the conclusion
            - If the available evidence is only partial and not enough for a reliable final answer, set confidence = 0
            - Do not invent facts, numbers, or claims not present in the input
            - Use only the validated specialist results as evidence
            - Do not mention internal roles such as orchestrator, specialist, critic, or synthesizer in the final user-facing answer

            If confidence = 1:
            - combine the validated results into one clear, concise, coherent final answer

            If confidence = 0:
            - do not try to fully answer the user's question
            - use answer to tell the orchestrator exactly how the plan should be refined
            - be specific about what additional evidence, tool usage, or specialist routing is needed
        """
        self.active_model = active_model

    def run(self, question: str, plan, valid_results: dict):
        verified_results = json.dumps({
            "question": question,
            "orchestrator_plan": plan,
            "valid_results": valid_results,
        })
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
                        "reasoning": {"type": "string"}
                    },
                    "required": ["confidence", "answer", "reasoning"],
                    "additionalProperties": False
                }
            }
        }

        params = {
            "model": self.active_model,
            "messages": messages,
            "response_format": response_schema,
            "temperature": 0,
        }
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
        - If the task involves selecting companies from a sector, exchange, or market-cap bucket, use the database tools first
        - When comparing companies, present the exact values clearly
        - If a metric is missing or a tool fails, say so explicitly
        - Keep the final answer concise and analytical
        - Do not answer beyond the assigned task
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
        - If the task refers to a sector or group of companies, use the database tool only to identify relevant tickers
        - Summarize the most relevant headlines and sentiment clearly
        - If sentiment is mixed, say that explicitly
        - If there are too many possible tickers, prioritize the ones named in the task
        - If data is missing or a tool fails, say so clearly
        - Keep the answer concise and directly tied to the assigned task
        - Do not answer beyond the assigned task
        """,
}

def run_multi_agent(question, conv_hist = ""):
    t0 = time.perf_counter()

    MARKET_TOOLS      = [SCHEMA_TICKERS, SCHEMA_PRICE, SCHEMA_STATUS, SCHEMA_MOVERS]
    FUNDAMENTAL_TOOLS = [SCHEMA_OVERVIEW, SCHEMA_SQL, SCHEMA_TICKERS]
    SENTIMENT_TOOLS   = [SCHEMA_NEWS, SCHEMA_SQL]

    orchestrator = Orchestrator()
    market_specialist = Specialist("market_specialist", schema=MARKET_TOOLS)
    fundamental_specialist = Specialist("fundamental_specialist", schema=FUNDAMENTAL_TOOLS)
    news_specialist = Specialist("news_specialist", schema=SENTIMENT_TOOLS)
    critic = Critic()
    synthesizer = Synthsizer()

    SPECIALISTS = {
        "market_specialist": market_specialist,
        "fundamental_specialist": fundamental_specialist,
        "news_specialist": news_specialist,
    }
    SPECIALISTS_ANSWER = {}
    SPECIALISTS_RESULTS = []

    reply_is_ready = False
    max_attempts = 5
    
    retry = 0
    while not reply_is_ready and retry < 5:
        orchestrator_results = orchestrator.run(question=question, conv_hist=conv_hist)
        plan = orchestrator_results.answer
        display(Markdown(plan))

        for specialist_called  in orchestrator_results.raw_data["specialist_to_call"]:
            sp = specialist_called["agent_name"]
            task = specialist_called["instruction"]
            display(Markdown(task))
            SPECIALISTS[sp].prompt = SPECIALIST_PROMPTS[sp]
            task_success = False
            task_attempt = 1
            cxt = ""

            while not task_success and task_attempt <= max_attempts:
                task_attempt += 1
                sp_results = SPECIALISTS[sp].run(task=task, cxt=cxt)
                critic_results = critic.run(task=task, specalist_results=sp_results)

                if not critic_results.answer:
                    cxt = f"\n\nYour last answer failed!\n\nlast answer:{sp_results.answer}\n\nfailure reason: {critic_results.reasoning}"
                    task_success = False
                else:
                    task_success = True
            
            if task_attempt > max_attempts:
                print(f"{sp} has reached it maximum attempts")
                SPECIALISTS_ANSWER[sp] = "Specialist failed in retrieving relevant infomation."
            else:
                print(f"{sp} has passed critic's evaluation")
                SPECIALISTS_ANSWER[sp] = sp_results.answer
            SPECIALISTS_RESULTS.append(sp_results)
    
        synthesizer_results = synthesizer.run(question=question, plan=plan, valid_results=SPECIALISTS_ANSWER)
        if synthesizer_results.confidence == 1.0:
            reply_is_ready = True
            print("reply is ready")
        else:
            retry += 1
            reply_is_ready = False
            conv_hist += f"\n\nSpecalist results insufficient in answering user's question. Here's the reason:\n\n{synthesizer_results.reasoning}\n\nand replanning suggestions:\n\n{synthesizer_results.answer}"
            print("specialist results insufficent in answering user's question, returning to orchestrator replanning")


    if retry < 5:
        wall_time = round(time.perf_counter() - t0, 3)
        return {
            "final_answer": synthesizer_results.answer,
            "agent_results": SPECIALISTS_RESULTS,
            "elapsed_sec": wall_time,
            "architecture": "orchestrator-critic"
        }
    else:
        wall_time = round(time.perf_counter() - t0, 3)
        return {
            "final_answer": "Sorry, I am not being able to answer your question now.",
            "agent_results": SPECIALISTS_RESULTS,
            "elapsed_sec": wall_time,
            "architecture": "orchestrator-critic"
        }
