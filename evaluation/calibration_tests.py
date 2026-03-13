from client.openai_client import OpenAIClient
from evaluation.evaluator import Evaluator

openai_client = OpenAIClient()
evaluator = Evaluator(openai_client=openai_client)

print("=== Calibration Test 1 — correct answer (expect score=3) ===")
t1 = evaluator.run_evaluator(
    question        = "What is the P/E ratio of Apple (AAPL)?",
    expected_answer = "Should return AAPL P/E ratio as a single numeric value from Alpha Vantage.",
    agent_answer    = "The current P/E ratio of Apple Inc. (AAPL) is 33.45.",
)
print(f"  Score: {t1['score']}/3 | Hallucination: {t1['hallucination_detected']}")
print(f"  Reasoning: {t1['reasoning']}")

print("\n=== Calibration Test 2 — fabricated number (expect hallucination=True, score≤1) ===")
t2 = evaluator.run_evaluator(
    question        = "What is the P/E ratio of Apple (AAPL)?",
    expected_answer = "Should return AAPL P/E ratio as a single numeric value from Alpha Vantage.",
    agent_answer    = "Apple's P/E ratio is approximately 28.5 based on current market conditions.",
)
print(f"  Score: {t2['score']}/3 | Hallucination: {t2['hallucination_detected']}")
print(f"  Reasoning: {t2['reasoning']}")
assert t2["hallucination_detected"] == True, "Should detect fabricated P/E as hallucination"

print("\n=== Calibration Test 3 — refusal (expect score=0) ===")
t3 = evaluator.run_evaluator(
    question        = "What is the P/E ratio of Apple (AAPL)?",
    expected_answer = "Should return AAPL P/E ratio as a single numeric value from Alpha Vantage.",
    agent_answer    = "I cannot retrieve real-time financial data. Please check Yahoo Finance.",
)
print(f"  Score: {t3['score']}/3 | Hallucination: {t3['hallucination_detected']}")
print(f"  Reasoning: {t3['reasoning']}")
assert t3["score"] == 0, "Refusal should score 0"

print("\n✅ Evaluator calibration complete")