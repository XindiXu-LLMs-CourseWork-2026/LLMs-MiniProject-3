import os

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv(override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_KEY")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "test")

# database
DB_PATH = "./db/stocks.db"

# Mock ALPHAVANTAGE
os.environ["ALPHAVANTAGE_BASE_URL"] = "http://127.0.0.1:2345"
AV_BASE = os.getenv("ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co")

# OpenAI

MODEL_SMALL = "gpt-4o-mini"
MODEL_LARGE = "gpt-4o"
ACTIVE_MODEL = MODEL_SMALL
client = OpenAI(api_key=OPENAI_API_KEY)