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