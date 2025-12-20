import logging
import os
import io
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import azure.functions as func
import pandas as pd
import requests
from azure.storage.blob import ContainerClient, ContentSettings
from sqlalchemy import create_engine
from dotenv import load_dotenv

# =============================
# Load ENV (LOCAL ONLY)
# =============================
load_dotenv()

# =============================
# CONFIG
# =============================
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME")
BLOB_SAS_URL = os.getenv("BLOB_SAS_URL")
RAW_FOLDER = os.getenv("RAW_FOLDER", "raw/")
JSON_FOLDER = os.getenv("JSON_FOLDER", "raw_json/")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", 30))

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DB = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASS = os.getenv("SQL_PASSWORD")
SQL_TABLE = os.getenv("SQL_TABLE", "KalshiMarketData")

MAX_WORKERS = 8

if not BLOB_SAS_URL:
    raise ValueError("BLOB_SAS_URL missing in .env")

# =============================
# APP
# =============================
app = func.FunctionApp()

# =============================
# HELPERS
# =============================
def init_blob_client():
    return ContainerClient.from_container_url(BLOB_SAS_URL)

def upload_blob(container, path, data, content_type):
    container.get_blob_client(path).upload_blob(
        data, overwrite=True,
        content_settings=ContentSettings(content_type=content_type)
    )

def fetch_event_category(ticker):
    try:
        r = requests.get(
            f"https://api.elections.kalshi.com/trade-api/v2/events/{ticker}",
            timeout=8
        )
        r.raise_for_status()
        return ticker, r.json().get("event", {}).get("category", "Unknown")
    except Exception:
        return ticker, "Unknown"

def sanitize_for_sql(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # -----------------------------
    # 1) Replace empty strings with NULL
    # -----------------------------
    df = df.replace({"": None})

    # -----------------------------
    # 2) Force NUMERIC columns
    # -----------------------------
    numeric_cols = [
        "last_price","last_price_dollars",
        "no_bid","no_bid_dollars",
        "no_ask","no_ask_dollars",
        "yes_bid","yes_bid_dollars",
        "yes_ask","yes_ask_dollars",
        "volume","volume_24h",
        "open_interest",
        "notional_value","notional_value_dollars",
        "liquidity", "liquidity_dollars",
        "previous_price","previous_price_dollars",
        "previous_yes_ask","previous_yes_ask_dollars",
        "previous_yes_bid","previous_yes_bid_dollars",
        "risk_limit_cents","tick_size"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -----------------------------
    # 3) Force DATETIME columns (REMOVE TZ)
    # -----------------------------
    datetime_cols = [
        "close_time","created_time","expected_expiration_time",
        "expiration_time","latest_expiration_time",
        "open_time","fetched_utc"
    ]

    for col in datetime_cols:
        if col in df.columns:
            df[col] = (
                pd.to_datetime(df[col], errors="coerce", utc=True)
                .dt.tz_localize(None)
            )

    # -----------------------------
    # 4) Force BOOLEAN → INT (BIT safe)
    # -----------------------------
    bool_cols = ["can_close_early"]

    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    # -----------------------------
    # 5) Convert dict/list → JSON STRING
    # -----------------------------
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: json.dumps(x, default=str)
            if isinstance(x, (dict, list)) else x
        )

    # -----------------------------
    # 6) NaN → NULL (CRITICAL)
    # -----------------------------
    df = df.where(pd.notnull(df), None)

    return df

def create_sql_engine():
    driver = "ODBC Driver 17 for SQL Server"
    raw_conn = f"""
    Driver={{{driver}}};
    Server=tcp:{SQL_SERVER},1433;
    Database={SQL_DB};
    Uid={SQL_USER};
    Pwd={SQL_PASS};
    Encrypt=yes;
    TrustServerCertificate=no;
    Connection Timeout=30;
    """
    encoded = urllib.parse.quote_plus(raw_conn)
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={encoded}",
        fast_executemany=True
    )

# =============================
# TIMER FUNCTION
# =============================
@app.timer_trigger(
    schedule="0 */30 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False
)
def timer_trigger(myTimer: func.TimerRequest):

    logging.info("Kalshi fetch started")

    # -------- Fetch markets --------
    try:
        r = requests.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params={"status": "open", "limit": 500},
            timeout=30
        )
        r.raise_for_status()
        markets = r.json().get("markets", [])
    except Exception as e:
        logging.error(f"API fetch failed: {e}")
        return

    if not markets:
        logging.info("No markets returned")
        return

    df = pd.json_normalize(markets)

    # -------- Basic cleanup --------
    for col in ["ticker", "event_ticker", "status", "title"]:
        if col not in df.columns:
            df[col] = None

    df["fetched_utc"] = datetime.utcnow()

    # -------- Event categories --------
    event_tickers = df["event_ticker"].dropna().unique().tolist()
    categories = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch_event_category, t) for t in event_tickers]
        for f in as_completed(futures):
            t, c = f.result()
            categories[t] = c

    df["event_category"] = df["event_ticker"].map(categories).fillna("Unknown")

    # -------- Write Parquet + JSON --------
    ts = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    parquet_name = f"{RAW_FOLDER}markets_{ts}.parquet"
    json_name = f"{JSON_FOLDER}markets_{ts}.json"

    parquet_buf = io.BytesIO()
    df.to_parquet(parquet_buf, index=False, engine="pyarrow")

    container = init_blob_client()

    upload_blob(container, parquet_name, parquet_buf.getvalue(), "application/octet-stream")
    upload_blob(container, json_name, json.dumps(markets).encode(), "application/json")

    # -------- SQL INSERT --------
    try:
        engine = create_sql_engine()
        sql_df = sanitize_for_sql(df)
        sql_df.to_sql(SQL_TABLE, engine, if_exists="append", index=False)
        engine.dispose()
        logging.info(f"Inserted {len(sql_df)} rows into SQL")
    except Exception as e:
        logging.error(f"SQL load failed: {e}")

    logging.info("Kalshi fetch completed successfully")
