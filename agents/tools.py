import sqlite3
import requests
import yfinance as yf
import pandas as pd
from config import ALPHAVANTAGE_API_KEY, AV_BASE, DB_PATH


def get_price_performance(tickers: list, period: str = "1y"):

    results = {}
    TICKER_ALIASES = {
        "FI": "FISV",
    }
    def normalize_ticker(ticker: str) -> str:
        return TICKER_ALIASES.get(ticker.upper(), ticker.upper())
        
    for ticker in tickers:

        try:
            yf_ticker = normalize_ticker(ticker)
            data = yf.download(yf_ticker, period=period, progress=False, auto_adjust=True)

            if data.empty:
                results[ticker] = {"error": "No data"}
                continue

            start = float(data["Close"].iloc[0])
            end = float(data["Close"].iloc[-1])

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

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(sql, conn)

    conn.close()

    return {
        "columns": list(df.columns),
        "rows": df.to_dict(orient="records")
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
            df = pd.read_sql_query(sql_sector, conn, params=[f"%{sector}%"])
            if df.empty:
                df = pd.read_sql_query(sql_industry, conn, params=[f"%{sector}%"])
        return {
            "sector": df["sector"].iloc[0],
            "stocks": df[["ticker", "company", "industry"]].to_dict(orient="records")
        }
    except Exception as e:
        return {"error": str(e)}
