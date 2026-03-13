from config import REQUIRED_KEYS
import json
import re

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
        You are an LLM-based evaluator (LLM-as-judge). Your task is to score an agent's answer against an expected answer description.

        Rules:
        
        1. Scoring:
            - 3 — Fully correct:    all required data present, numbers accurate, conditions met
            - 2 — Partially correct: key data present but incomplete, gaps, or minor inaccuracies
            - 1 — Mostly wrong:     attempted but wrong numbers, missed required conditions, or claims that appear fabricated
            - 0 — Complete failure: refused to answer, said data unavailable without trying tools, or answer has no relevance to the question
        
        2. Hallucination Detection:

            The evaluator only sees the final text answer and cannot verify tool usage.
            
            Flag hallucination ONLY if the answer itself shows evidence of fabrication or speculation.
            
            Examples of hallucination signals:
            - The answer describes a number as an estimate, approximation, or guess
              (e.g., "approximately", "estimated", "based on market conditions").
            - The reasoning suggests the value was inferred rather than retrieved from data.
            - The answer contains an invalid or unrelated stock ticker.
            
            Do NOT flag hallucination if:
            - The answer simply states a specific numeric value.
            - The answer directly answers the question without speculative language.

        
        3. Output Format:
           Respond only with a valid JSON object, strictly following this structure:
           {{
                "score"                 : int,        # 0, 1, 2, or 3
                "max_score"             : 3,
                "reasoning"             : str,        # one sentence explaining the score
                "hallucination_detected": bool,       # True if the answer contains invented facts
                "key_issues"            : list[str],  # specific problems found; empty list if none
            }}
           Do not include any markdown, comments, or extra text.
        
        Now evaluate the following:
        
        Question:
        {question}
        
        Expected Answer Description:
        {expected_answer}
        
        Agent Answer:
        {agent_answer}

        """


        messages=[{"role": "user", "content": prompt}]
        response = self.openai_client.get_ai_response(messages, 0)
        answer_text = response.choices[0].message.content
        result = self.parse_json(answer_text)
        return result

    def parse_json(self, answer_text: str) -> dict:
        """
        Safely parse LLM output that may be wrapped in ```json ... ``` markdown
        """
        # remove ```json ... ``` 或 ``` ... ```
        answer_text = answer_text.strip()
        markdown_pattern = r"^```(?:json)?\s*(.*?)\s*```$"
        match = re.match(markdown_pattern, answer_text, re.DOTALL)
        if match:
            answer_text = match.group(1)

        try:
            result = json.loads(answer_text)
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
