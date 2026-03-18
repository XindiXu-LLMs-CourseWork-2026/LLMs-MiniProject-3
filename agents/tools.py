import sqlite3
import warnings
import requests
from config import ALPHAVANTAGE_API_KEY, AV_BASE, DB_PATH


def get_price_performance(tickers: list, period: str = "1y"):
    import yfinance as yf

    results = {}
    TICKER_ALIASES = {
        "FI": "FISV",
    }
    INACTIVE_TICKERS = {
        "JNPR": {
            "reason": "Ticker delisted after acquisition by HPE on 2025-07-02",
            "replacement_ticker": "HPE",
        },
        "ANSS": {
            "reason": "Ticker delisted after acquisition by SNPS on 2025-07-17",
            "replacement_ticker": "SNPS",
        },
        "DAY": {
            "reason": "Ticker delisted after acquisition by Thoma Bravo on 2026-02-04",
            "replacement_ticker": None,
        },
    }

    def normalize_ticker(ticker: str) -> str:
        return TICKER_ALIASES.get(ticker.upper(), ticker.upper())
        
    for ticker in tickers:
        inactive_meta = INACTIVE_TICKERS.get(ticker.upper())
        if inactive_meta:
            results[ticker] = {
                "error": inactive_meta["reason"],
                "replacement_ticker": inactive_meta["replacement_ticker"],
            }
            continue

        try:
            yf_ticker = normalize_ticker(ticker)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                data = yf.download(yf_ticker, period=period, progress=False, auto_adjust=True)

            if data.empty:
                results[ticker] = {"error": "No data"}
                continue

            close_prices = data["Close"]
            start = float(close_prices.iloc[0].item())
            end = float(close_prices.iloc[-1].item())

            results[ticker] = {
                "start_price": round(start,2),
                "end_price": round(end,2),
                "pct_change": round((end-start)/start*100,2),
                "period":period
            }

        except Exception as e:

            results[ticker] = {"error":str(e)}

    return results


def get_market_status():

    return requests.get(
        f"{AV_BASE}/query?function=MARKET_STATUS&apikey={ALPHAVANTAGE_API_KEY}"
    ).json()


def get_top_gainers_losers():

    return requests.get(
        f"{AV_BASE}/query?function=TOP_GAINERS_LOSERS&apikey={ALPHAVANTAGE_API_KEY}"
    ).json()


def get_news_sentiment(ticker: str, limit: int = 5):

    data = requests.get(
        f"{AV_BASE}/query?function=NEWS_SENTIMENT"
        f"&tickers={ticker}&limit={limit}&apikey={ALPHAVANTAGE_API_KEY}"
    ).json()

    return {
        "ticker": ticker,
        "articles": [
            {
                "title":a.get("title"),
                "source":a.get("source"),
                "sentiment":a.get("overall_sentiment_label"),
                "score":a.get("overall_sentiment_score")
            }
            for a in data.get("feed",[])[:limit]
        ]
    }


def query_local_db(sql: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return {
        "columns": columns,
        "rows": rows
    }


def get_company_overview(ticker: str):

    data = requests.get(
        f"{AV_BASE}/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
    ).json()

    if not data.get("Name"):
        return {"error":f"No overview data for {ticker}"}

    return {
        "ticker":data.get("Symbol"),
        "name":data.get("Name"),
        "sector":data.get("Sector"),
        "pe_ratio":data.get("PERatio"),
        "eps":data.get("EPS"),
        "market_cap":data.get("MarketCapitalization"),
        "52w_high":data.get("52WeekHigh"),
        "52w_low":data.get("52WeekLow")
    }


def get_tickers_by_sector(sector: str):
    sql_sector = """
                 SELECT ticker, company, sector, industry
                 FROM stocks
                 WHERE LOWER(sector) LIKE Lower(?) \
                 """
    sql_industry = """
                   SELECT ticker, company, sector, industry
                   FROM stocks
                   WHERE LOWER(industry) LIKE Lower(?) \
                   """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(sql_sector, [f"%{sector}%"])
            rows = cursor.fetchall()
            if not rows:
                cursor = conn.execute(sql_industry, [f"%{sector}%"])
                rows = cursor.fetchall()
        return {
            "sector": rows[0][2] if rows else sector,
            "stocks": [
                {"ticker": row[0], "company": row[1], "industry": row[3]}
                for row in rows
            ]
        }
    except Exception as e:
        return {"error": str(e)}
