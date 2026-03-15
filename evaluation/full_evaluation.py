import time

import pandas as pd

from agents.baseline_agent import run_baseline
from agents.multi_agent import run_multi_agent
from agents.single_agent import run_single_agent
from evaluation.evaluator import run_evaluator
from evaluation.models.eval_record import EvalRecord

# ── Column rename map (internal name → Excel header) ─────────
_COL_NAMES = {
    "question_id": "Question ID", "question": "Question", "complexity": "Difficulty",
    "category": "Category", "expected": "Expected Answer",
    "bl_answer": "Baseline Answer", "bl_time": "Baseline Time (s)",
    "bl_score": "Baseline Score /3", "bl_reasoning": "Baseline Eval Reasoning",
    "bl_hallucination": "Baseline Hallucination", "bl_issues": "Baseline Issues",
    "sa_answer": "SA Answer", "sa_tools": "SA Tools Used", "sa_tool_count": "SA Tool Count",
    "sa_iters": "SA Iterations", "sa_time": "SA Time (s)",
    "sa_score": "SA Score /3", "sa_reasoning": "SA Eval Reasoning",
    "sa_hallucination": "SA Hallucination", "sa_issues": "SA Issues",
    "ma_answer": "MA Answer", "ma_tools": "MA Tools Used", "ma_tool_count": "MA Tool Count",
    "ma_time": "MA Time (s)", "ma_confidence": "MA Avg Confidence",
    "ma_critic_issues": "MA Critic Issue Count", "ma_agents": "MA Agents Activated",
    "ma_architecture": "MA Architecture",
    "ma_score": "MA Score /3", "ma_reasoning": "MA Eval Reasoning",
    "ma_hallucination": "MA Hallucination", "ma_issues": "MA Issues",
}


def _save_excel(records: list, path: str):
    df = pd.DataFrame([r.__dict__ for r in records]).rename(columns=_COL_NAMES)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # ── Sheet 1: full results ──────────────────────────────
        df.to_excel(writer, index=False, sheet_name="Results")

        # ── Sheet 2: summary by architecture × difficulty ──────
        rows = []
        for arch, sc, tc, hc in [
            ("Baseline", "Baseline Score /3", "Baseline Time (s)", "Baseline Hallucination"),
            ("Single Agent", "SA Score /3", "SA Time (s)", "SA Hallucination"),
            ("Multi Agent", "MA Score /3", "MA Time (s)", "MA Hallucination"),
        ]:
            for tier in ["easy", "medium", "hard", "all"]:
                subset = df if tier == "all" else df[df["Difficulty"] == tier]
                valid = subset[subset[sc] >= 0]
                avg_s = valid[sc].mean() if len(valid) else 0
                rows.append({
                    "Architecture": arch,
                    "Difficulty": tier,
                    "Questions Scored": len(valid),
                    "Avg Score /3": round(avg_s, 2),
                    "Accuracy %": round(avg_s / 3 * 100, 1),
                    "Avg Time (s)": round(df[tc].mean(), 1),
                    "Hallucinations": (df[hc] == "True").sum(),
                })
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="Summary")

BENCHMARK_QUESTIONS = [
    # ── EASY ──────────────────────────────────────────────────────────────
    {"id":"Q01","complexity":"easy","category":"sector_lookup",
     "question":"List all semiconductor companies in the database.",
     "expected":"Should return company names and tickers for semiconductor stocks from the local DB. "
                "Tickers include NVDA, AMD, INTC, QCOM, AVGO, TXN, ADI, MU and others."},
    {"id":"Q02","complexity":"easy","category":"market_status",
     "question":"Are the US stock markets open right now?",
     "expected":"Should return the current open/closed status for NYSE and NASDAQ "
                "with their trading hours."},
    {"id":"Q03","complexity":"easy","category":"fundamentals",
     "question":"What is the P/E ratio of Apple (AAPL)?",
     "expected":"Should return AAPL P/E ratio as a single numeric value fetched from Alpha Vantage."},
    {"id":"Q04","complexity":"easy","category":"sentiment",
     "question":"What is the latest news sentiment for Microsoft (MSFT)?",
     "expected":"Should return 3–5 recent MSFT headlines with Bullish/Bearish/Neutral labels and scores."},
    {"id":"Q05","complexity":"easy","category":"price",
     "question":"What is NVIDIA's stock price performance over the last month?",
     "expected":"Should return NVDA start price, end price, and % change for the 1-month period."},

    # ── MEDIUM ─────────────────────────────────────────────────────────────
    {"id":"Q06","complexity":"medium","category":"price_comparison",
     "question":"Compare the 1-year price performance of AAPL, MSFT, and GOOGL. Which grew the most?",
     "expected":"Should fetch 1y performance for all 3 tickers, return % change for each, "
                "and identify the highest performer."},
    {"id":"Q07","complexity":"medium","category":"fundamentals",
     "question":"Compare the P/E ratios of AAPL, MSFT, and NVDA. Which looks most expensive?",
     "expected":"Should return P/E ratios for all 3 tickers and identify which has the highest P/E."},
    {"id":"Q08","complexity":"medium","category":"sector_price",
     "question":"Which energy stocks in the database had the best 6-month performance?",
     "expected":"Should query the DB for energy sector tickers, fetch 6-month price performance "
                "for each, and return them ranked by % change."},
    {"id":"Q09","complexity":"medium","category":"sentiment",
     "question":"What is the news sentiment for Tesla (TSLA) and how has its stock moved this month?",
     "expected":"Should return TSLA news sentiment (label + score) AND 1-month price % change "
                "from two separate tool calls."},
    {"id":"Q10","complexity":"medium","category":"fundamentals",
     "question":"What are the 52-week high and low for JPMorgan (JPM) and Goldman Sachs (GS)?",
     "expected":"Should return 52-week high and low for both JPM and GS fetched from Alpha Vantage."},

    # ── HARD ───────────────────────────────────────────────────────────────
    {"id":"Q11","complexity":"hard","category":"multi_condition",
     "question":"Which tech stocks dropped this month but grew this year? Return the top 3.",
     "expected":"Should get tech tickers from DB, fetch both 1-month and year-to-date performance, "
                "filter for negative 1-month AND positive YTD, return top 3 by yearly growth with "
                "exact percentages. Results must satisfy both conditions simultaneously."},
    {"id":"Q12","complexity":"hard","category":"multi_condition",
     "question":"Which large-cap technology stocks on NASDAQ have grown more than 20% this year?",
     "expected":"Should query DB for large-cap NASDAQ tech stocks, fetch YTD performance, "
                "filter for >20% growth, and return matching tickers with exact % change."},
    {"id":"Q13","complexity":"hard","category":"cross_domain",
     "question":"For the top 3 semiconductor stocks by 1-year return, what are their P/E ratios "
                "and current news sentiment?",
     "expected":"Should find semiconductor tickers in DB, rank by 1-year return to find top 3, "
                "then fetch P/E ratio AND news sentiment for each — requiring three separate "
                "data domains (price, fundamentals, sentiment)."},
    {"id":"Q14","complexity":"hard","category":"cross_domain",
     "question":"Compare the market cap, P/E ratio, and 1-year stock performance of JPM, GS, and BAC.",
     "expected":"Should return market cap, P/E, and 1-year % change for all 3 tickers, "
                "combining Alpha Vantage fundamentals and yfinance price data."},
    {"id":"Q15","complexity":"hard","category":"multi_condition",
     "question":"Which finance sector stocks are trading closer to their 52-week low than their "
                "52-week high? Return the news sentiment for each.",
     "expected":"Should get finance sector tickers from DB, fetch 52-week high and low for each, "
                "compute proximity to the low, then fetch news sentiment for qualifying stocks."},
]

def run_full_evaluation(output_xlsx: str = "results.xlsx", delay_sec: float = 3.0, active_model="gpt-4o"):
    """
    Run all 15 questions through baseline, single agent, and multi agent.
    Score each answer. Write results to Excel after every question.
    """
    records = []
    total = len(BENCHMARK_QUESTIONS)
    print(f"\n{'=' * 62}")
    print(f"  FULL EVALUATION  |  {total} questions × 3 architectures")
    print(f"  Model: {active_model}  |  Output: {output_xlsx}")
    print(f"{'=' * 62}\n")
    bq = BENCHMARK_QUESTIONS
    for i, q in enumerate(bq, 1):
        print(f"[{i:02d}/{total}] {q['id']} ({q['complexity']:6s}) {q['question'][:52]}...")
        rec = EvalRecord(question_id=q["id"], question=q["question"],
                         complexity=q["complexity"], category=q["category"],
                         expected=q["expected"])

        # ── Baseline ───────────────────────────────────────────
        print("         baseline  ...", end=" ", flush=True)
        try:
            t0 = time.time()
            bl = run_baseline(q["question"], verbose=False)
            rec.bl_answer = bl.answer.replace("\n", " ")
            rec.bl_time = round(time.time() - t0, 2)
            ev = run_evaluator(q["question"], q["expected"], bl.answer)
            rec.bl_score = ev.get("score", -1)
            rec.bl_reasoning = ev.get("reasoning", "")
            rec.bl_hallucination = str(ev.get("hallucination_detected", False))
            rec.bl_issues = " | ".join(ev.get("key_issues", []))
            print(f"✅  {rec.bl_time:5.1f}s  score {rec.bl_score}/3")
        except Exception as e:
            print(f"❌  {e}")

        # ── Single Agent ───────────────────────────────────────
        print("         single    ...", end=" ", flush=True)
        try:
            t0 = time.time()
            sa = run_single_agent(q["question"], verbose=False)
            rec.sa_answer = sa.answer.replace("\n", " ")
            rec.sa_tools = ", ".join(sa.tools_called)
            rec.sa_tool_count = len(sa.tools_called)
            rec.sa_iters = len(sa.tools_called) + 1  # approx
            rec.sa_time = round(time.time() - t0, 2)
            ev = run_evaluator(q["question"], q["expected"], sa.answer)
            rec.sa_score = ev.get("score", -1)
            rec.sa_reasoning = ev.get("reasoning", "")
            rec.sa_hallucination = str(ev.get("hallucination_detected", False))
            rec.sa_issues = " | ".join(ev.get("key_issues", []))
            print(f"✅  {rec.sa_time:5.1f}s  score {rec.sa_score}/3"
                  f"  tools [{rec.sa_tools or 'none'}]")
        except Exception as e:
            print(f"❌  {e}")

        # ── Multi Agent ────────────────────────────────────────
        print("         multi     ...", end=" ", flush=True)
        try:
            t0 = time.time()
            ma = run_multi_agent(q["question"])
            # print(f"ma: {ma}")
            res = ma.get("agent_results", [])
            # print(f"res: {res}")
            all_tools = [t for r in res for t in r.tools_called]
            all_issues = [iss for r in res for iss in r.issues_found]
            avg_conf = sum(r.confidence for r in res) / len(res) if res else 0.0
            rec.ma_answer = ma["final_answer"].replace("\n", " ")
            rec.ma_tools = ", ".join(dict.fromkeys(all_tools))
            rec.ma_tool_count = len(all_tools)
            rec.ma_time = round(time.time() - t0, 2)
            rec.ma_confidence = f"{avg_conf:.0%}"
            rec.ma_critic_issues = len(all_issues)
            rec.ma_agents = ", ".join(r.agent_name for r in res)
            rec.ma_architecture = ma.get("architecture", "")
            ev = run_evaluator(q["question"], q["expected"], ma["final_answer"])
            rec.ma_score = ev.get("score", -1)
            rec.ma_reasoning = ev.get("reasoning", "")
            rec.ma_hallucination = str(ev.get("hallucination_detected", False))
            rec.ma_issues = " | ".join(ev.get("key_issues", []))
            print(f"✅  {rec.ma_time:5.1f}s  score {rec.ma_score}/3"
                  f"  conf {rec.ma_confidence}  issues {rec.ma_critic_issues}")
        except Exception as e:
            print(f"❌  {e}")

        records.append(rec)
        _save_excel(records, output_xlsx)  # save progress after every question

        if i < total:
            print(f"         ⏳ waiting {delay_sec}s ...\n")
            time.sleep(delay_sec)

    # ── Print summary table ────────────────────────────────────
    print(f"\n{'=' * 62}  RESULTS")
    print(f"{'Architecture':<18} {'Easy':>8} {'Medium':>8} {'Hard':>8} {'Overall':>8}")
    print("─" * 52)
    for arch, sk in [("Baseline", "bl_score"), ("Single Agent", "sa_score"), ("Multi Agent", "ma_score")]:
        def pct(tier):
            s = [getattr(r, sk) for r in records
                 if getattr(r, sk) >= 0 and (tier == "all" or r.complexity == tier)]
            return f"{sum(s) / len(s) / 3 * 100:.0f}%" if s else "—"

        print(f"{arch:<18} {pct('easy'):>8} {pct('medium'):>8} {pct('hard'):>8} {pct('all'):>8}")

    print(f"\n✅ Saved → {output_xlsx}")
    return output_xlsx
