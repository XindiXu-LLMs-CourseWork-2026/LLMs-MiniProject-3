from agents.baseline_agent import run_baseline
from agents.multi_agent import run_multi_agent
from agents.single_agent import run_single_agent
from agents.tools import query_local_db, get_tickers_by_sector
from evaluation.evaluator import run_evaluator
from evaluation.full_evaluation import BENCHMARK_QUESTIONS


def calibration_tests():
    print("=== Calibration Test 1 — correct answer (expect score=3) ===")
    t1 = run_evaluator(
        question="What is the P/E ratio of Apple (AAPL)?",
        expected_answer="Should return AAPL P/E ratio as a single numeric value from Alpha Vantage.",
        agent_answer="The current P/E ratio of Apple Inc. (AAPL) is 33.45.",
    )
    print(f"  Score: {t1['score']}/3 | Hallucination: {t1['hallucination_detected']}")
    print(f"  Reasoning: {t1['reasoning']}")

    print("\n=== Calibration Test 2 — fabricated number (expect hallucination=True, score≤1) ===")
    t2 = run_evaluator(
        question="What is the P/E ratio of Apple (AAPL)?",
        expected_answer="Should return AAPL P/E ratio as a single numeric value from Alpha Vantage.",
        agent_answer="Apple's P/E ratio is approximately 28.5 based on current market conditions.",
    )
    print(f"  Score: {t2['score']}/3 | Hallucination: {t2['hallucination_detected']}")
    print(f"  Reasoning: {t2['reasoning']}")
    assert t2["hallucination_detected"] == True, "Should detect fabricated P/E as hallucination"

    print("\n=== Calibration Test 3 — refusal (expect score=0) ===")
    t3 = run_evaluator(
        question="What is the P/E ratio of Apple (AAPL)?",
        expected_answer="Should return AAPL P/E ratio as a single numeric value from Alpha Vantage.",
        agent_answer="I cannot retrieve real-time financial data. Please check Yahoo Finance.",
    )
    print(f"  Score: {t3['score']}/3 | Hallucination: {t3['hallucination_detected']}")
    print(f"  Reasoning: {t3['reasoning']}")
    assert t3["score"] == 0, "Refusal should score 0"

    print("\n✅ Evaluator calibration complete")


def sanity_check():
    # ── Sanity check — one question, all three architectures ──────
    print("=== Sanity check ===")
    q_test = BENCHMARK_QUESTIONS[7]  # Q03 — easy fundamentals
    print(f"Test question: {q_test['question']}\n")

    bl_t = run_baseline(q_test["question"], verbose=False)
    sa_t = run_single_agent(q_test["question"], verbose=False)
    ma_t = run_multi_agent(q_test["question"])

    print(f"Baseline     : {bl_t.answer[:120]}")
    print(f"Single Agent : {sa_t.answer[:120]}  |  tools: {sa_t.tools_called}")
    print(f"Multi Agent  : {ma_t['final_answer'][:120]}  |  arch: {ma_t['architecture']}")

    ev_bl = run_evaluator(q_test["question"], q_test["expected"], bl_t.answer)
    ev_sa = run_evaluator(q_test["question"], q_test["expected"], sa_t.answer)
    ev_ma = run_evaluator(q_test["question"], q_test["expected"], ma_t["final_answer"])
    print(f"\nScores — Baseline: {ev_bl['score']}/3  |  Single: {ev_sa['score']}/3  |  Multi: {ev_ma['score']}/3")


if __name__ == "__main__":
    # calibration_tests()
    # sanity_check()
    # sql = "select ticker, company from stocks limit 10"
#     sql = """SELECT ticker, company, industry
# FROM stocks
# WHERE LOWER(industry) LIKE
# LOWER('%semiconductor%')"""
#     # query_local_db(sql)
#     print(query_local_db(sql))
    print(get_tickers_by_sector('semiconductor'))