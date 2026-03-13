from config import REQUIRED_KEYS
import json

class Evaluator:
    def __init__(self, openai_client):
        self.openai_client = openai_client

    def run_evaluator(self, question: str, expected_answer: str, agent_answer: str) -> dict:
        """
        Score one agent answer against the expected answer description.

        Returns dict with keys:
            score, max_score, reasoning, hallucination_detected, key_issues

        On JSON parse failure, return:
            {"score":0,"max_score":3,"reasoning":"evaluator parse error",
             "hallucination_detected":False,"key_issues":["evaluator failed to parse"]}
        """

        prompt = f"""
        You are an evaluator (LLM-as-judge). Score an agent's answer against an expected answer description.

        Question:
        {question}

        Expected Answer Description:
        {expected_answer}

        Agent Answer:
        {agent_answer}

        ### Scoring Rubric
        3 — Fully correct:    all required data present, numbers accurate, conditions met
        2 — Partially correct: key data present but incomplete, gaps, or minor inaccuracies
        1 — Mostly wrong:     attempted but wrong numbers, missed required conditions,
                              or claims that appear fabricated
        0 — Complete failure: refused to answer, said data unavailable without trying tools,
                              or answer has no relevance to the question

        ### Hallucination Detection Rules
        - Flag specific numbers (prices, P/E ratios, % changes) with no tool data to support them
        - Flag stock tickers that don't exist or aren't relevant
        - Flag definitive claims about "current" data without having called a live data tool

        ### Required Output Format
        Return only a valid JSON object, strictly JSON syntax:

        {{
            "score"                 : int,        # 0, 1, 2, or 3
            "max_score"             : 3,
            "reasoning"             : str,        # one sentence explaining the score
            "hallucination_detected": bool,       # True if the answer contains invented facts
            "key_issues"            : list[str],  # specific problems found; empty list if none
        }}
        Do NOT include markdown, comments, or extra text.
        """


        messages=[{"role": "user", "content": prompt}]
        response = self.openai_client.get_ai_response(messages, 0)
        answer_text = response.choices[0].message.content

        try:
            # Attempt to parse as Python dict
            print(f"answer_text: {answer_text}")
            result = json.loads(answer_text)
            print(f"result: {result}")
            # Validate keys exist
            if not isinstance(result, dict) or not REQUIRED_KEYS.issubset(result.keys()):
                raise ValueError("Missing keys")
            return result
        except json.JSONDecodeError:
            return {
                "score": 0,
                "max_score": 3,
                "reasoning": "evaluator parse error",
                "hallucination_detected": False,
                "key_issues": ["evaluator failed to parse"]
            }