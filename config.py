import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_KEY")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "test")

# Database
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "stocks.db")

# Alpha Vantage base URL:
# - local mock server by default
# - real API when ALPHAVANTAGE_BASE_URL is explicitly set to https://www.alphavantage.co
AV_BASE = os.getenv("ALPHAVANTAGE_BASE_URL", "http://127.0.0.1:2345")

# OpenAI
MODEL_SMALL = "gpt-4o-mini"
MODEL_LARGE = "gpt-4o"
ACTIVE_MODEL = MODEL_SMALL


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)
