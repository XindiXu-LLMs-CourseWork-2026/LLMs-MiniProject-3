import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


REQUIRED_KEYS = {"score", "max_score", "reasoning", "hallucination_detected", "key_issues"}