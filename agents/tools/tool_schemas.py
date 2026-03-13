from agents.tools.tools import get_tickers_by_sector, get_price_performance, get_company_overview, get_market_status, \
    get_top_gainers_losers, get_news_sentiment, query_local_db


def _s(name, desc, props, req):

    return {
        "type":"function",
        "function":{
            "name":name,
            "description":desc,
            "parameters":{
                "type":"object",
                "properties":props,
                "required":req
            }
        }
    }

SCHEMA_TICKERS = _s(
    "get_tickers_by_sector",
    "Return stocks in sector",
    {"sector":{"type":"string"}},
    ["sector"]
)

SCHEMA_PRICE = _s(
    "get_price_performance",
    "Return price performance",
    {"tickers":{"type":"array","items":{"type":"string"}}},
    ["tickers"]
)

SCHEMA_OVERVIEW = _s(
    "get_company_overview",
    "Company fundamentals",
    {"ticker":{"type":"string"}},
    ["ticker"]
)

SCHEMA_STATUS = _s(
    "get_market_status",
    "Market open/close",
    {},
    []
)

SCHEMA_MOVERS = _s(
    "get_top_gainers_losers",
    "Top movers",
    {},
    []
)

SCHEMA_NEWS = _s(
    "get_news_sentiment",
    "News sentiment",
    {"ticker":{"type":"string"}},
    ["ticker"]
)

SCHEMA_SQL = _s(
    "query_local_db",
    "Run SQL",
    {"sql":{"type":"string"}},
    ["sql"]
)

ALL_SCHEMAS = [
    SCHEMA_TICKERS,
    SCHEMA_PRICE,
    SCHEMA_OVERVIEW,
    SCHEMA_STATUS,
    SCHEMA_MOVERS,
    SCHEMA_NEWS,
    SCHEMA_SQL
]

ALL_TOOL_FUNCTIONS = {
    "get_tickers_by_sector": get_tickers_by_sector,
    "get_price_performance": get_price_performance,
    "get_company_overview": get_company_overview,
    "get_market_status": get_market_status,
    "get_top_gainers_losers": get_top_gainers_losers,
    "get_news_sentiment": get_news_sentiment,
    "query_local_db": query_local_db
}
