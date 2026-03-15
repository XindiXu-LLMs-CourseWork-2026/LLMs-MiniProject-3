import os
import sqlite3
import pandas as pd

from config import DB_PATH


def create_local_database(csv_path="sp500_companies.csv"):

    if not os.path.exists(csv_path):
        raise FileNotFoundError("sp500 csv not found")

    df = pd.read_csv(csv_path)

    df.columns = df.columns.str.strip().str.lower()

    df = df.rename(columns={
        "symbol":"ticker",
        "shortname":"company",
        "sector":"sector",
        "industry":"industry",
        "exchange":"exchange",
        "marketcap":"market_cap_raw"
    })

    def cap_bucket(v):
        try:
            v = float(v)
            if v >= 10_000_000_000:
                return "Large"
            elif v >= 2_000_000_000:
                return "Mid"
            else:
                return "Small"
        except:
            return "Unknown"

    df["market_cap"] = df["market_cap_raw"].apply(cap_bucket)

    df = (
        df.dropna(subset=["ticker","company"])
        .drop_duplicates(subset=["ticker"])
        [["ticker","company","sector","industry","market_cap","exchange"]]
    )

    conn = sqlite3.connect(DB_PATH)

    df.to_sql("stocks", conn, if_exists="replace", index=False)

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ticker ON stocks(ticker)")

    conn.commit()

    conn.close()

    print("✅ Database initialized")


if __name__ == "__main__":
    create_local_database()
