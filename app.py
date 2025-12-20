import io
import json
import os
import urllib.parse
import pandas as pd
from dotenv import load_dotenv

from azure.storage.blob import ContainerClient
from sqlalchemy import create_engine

from dash import Dash, dash_table, dcc, html
from dash.dependencies import Input, Output, State

import plotly.graph_objects as go
import plotly.express as px

# =========================
# LOAD ENV
# =========================
load_dotenv()

BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "kalshdata")
BLOB_SAS_URL = os.getenv("BLOB_SAS_URL")
RAW_FOLDER = os.getenv("RAW_FOLDER", "raw/")
JSON_FOLDER = os.getenv("JSON_FOLDER", "raw_json/")
MAX_FILES = int(os.getenv("MAX_FILES", 50))

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DB = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASS = os.getenv("SQL_PASSWORD")
SQL_TABLE = os.getenv("SQL_TABLE", "KalshiMarketData")

if not BLOB_SAS_URL:
    raise ValueError("BLOB_SAS_URL missing in .env")

# =========================
# BLOB CLIENT
# =========================
container = ContainerClient.from_container_url(BLOB_SAS_URL)

def list_recent_blobs(prefix, max_files=MAX_FILES):
    blobs = sorted(
        container.list_blobs(name_starts_with=prefix),
        key=lambda b: b.last_modified,
        reverse=True
    )
    return blobs[:max_files]

# =========================
# LOAD PARQUET DATA
# =========================
parquet_blobs = [b for b in list_recent_blobs(RAW_FOLDER) if b.name.endswith(".parquet")]

dfs = []
for blob in parquet_blobs:
    try:
        raw = container.get_blob_client(blob.name).download_blob().readall()
        dfs.append(pd.read_parquet(io.BytesIO(raw)))
    except Exception as e:
        print(f"Skipped {blob.name}: {e}")

if not dfs:
    raise Exception("No Parquet files found")

market_df = pd.concat(dfs, ignore_index=True)

# =========================
# EVENT CATEGORY FALLBACK
# =========================
if "event_category" not in market_df.columns:
    json_blobs = [b for b in list_recent_blobs(JSON_FOLDER) if b.name.endswith(".json")]
    mapping = {}
    for blob in json_blobs:
        data = json.loads(container.get_blob_client(blob.name).download_blob().readall())
        for m in data:
            if m.get("event_ticker") and m.get("category"):
                mapping[m["event_ticker"]] = m["category"]
    market_df["event_category"] = market_df["event_ticker"].map(mapping).fillna("Unknown")

# =========================
# CLEAN NUMERIC COLUMNS
# =========================
market_df["volume"] = pd.to_numeric(market_df.get("volume", 0), errors="coerce").fillna(0)
market_df["open_interest"] = pd.to_numeric(market_df.get("open_interest", 0), errors="coerce").fillna(0)

# =========================
# 1️⃣ DAILY VOLUME
# =========================
vol_df = market_df.groupby("event_category")["volume"].sum().reset_index()
vol_df.columns = ["Category", "Volume"]
vol_df["Pct_of_Total"] = (vol_df["Volume"] / vol_df["Volume"].sum()).round(3)

fig_volume = px.bar(vol_df, x="Category", y="Volume", title="Daily Volume by Category")

# =========================
# 2️⃣ OPEN INTEREST
# =========================
oi_df = market_df.groupby("event_category")["open_interest"].sum().reset_index()
oi_df.columns = ["Category", "Open_Interest"]
oi_df["Pct_of_Total"] = (oi_df["Open_Interest"] / oi_df["Open_Interest"].sum()).round(3)

fig_oi = px.bar(oi_df, x="Category", y="Open_Interest", title="Open Interest by Category")

# =========================
# 3️⃣ TRADES PER DAY
# =========================
market_df["open_time"] = pd.to_datetime(market_df.get("open_time"), errors="coerce")
market_df["date"] = market_df["open_time"].dt.date

trades_df = market_df.groupby("date").size().reset_index(name="trades")
trades_df["30_MA"] = trades_df["trades"].rolling(30, min_periods=1).mean()

fig_trades = go.Figure()
fig_trades.add_bar(x=trades_df["date"], y=trades_df["trades"], name="Trades")
fig_trades.add_scatter(x=trades_df["date"], y=trades_df["30_MA"], name="30-Day MA")

# =========================
# 4️⃣ MONTHLY TRADES
# =========================
market_df["month"] = market_df["open_time"].dt.to_period("M").dt.to_timestamp()
monthly_df = market_df.groupby(["month", "event_category"]).size().reset_index(name="Transactions")

fig_monthly = px.bar(
    monthly_df,
    x="month",
    y="Transactions",
    color="event_category",
    title="Monthly Trades per Category"
)

# =========================
# SQL ENGINE
# =========================
def create_sql_engine():
    driver = "ODBC Driver 17 for SQL Server"
    conn = f"""
    Driver={{{driver}}};
    Server=tcp:{SQL_SERVER},1433;
    Database={SQL_DB};
    Uid={SQL_USER};
    Pwd={SQL_PASS};
    Encrypt=yes;
    TrustServerCertificate=no;
    Connection Timeout=30;
    """
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(conn)}"
    )

# =========================
# SAMPLE SQL
# =========================
SAMPLE_SQL = {
    "Latest Rows": f"SELECT TOP 50 * FROM {SQL_TABLE} ORDER BY fetched_utc DESC",
    "Volume by Category": f"SELECT event_category, SUM(volume) vol FROM {SQL_TABLE} GROUP BY event_category",
    "Trades per Day": f"SELECT CAST(open_time AS DATE) d, COUNT(*) c FROM {SQL_TABLE} GROUP BY CAST(open_time AS DATE)"
}

# =========================
# DASH APP
# =========================
app = Dash(__name__)
app.title = "Kalshi Market Dashboard"

app.layout = html.Div([
    html.H1("Kalshi Market Dashboard"),

    dcc.Tabs([

        dcc.Tab(label="Daily Volume", children=[
            dash_table.DataTable(data=vol_df.to_dict("records"),
                                 columns=[{"name": i, "id": i} for i in vol_df.columns]),
            dcc.Graph(figure=fig_volume)
        ]),

        dcc.Tab(label="Open Interest", children=[
            dash_table.DataTable(data=oi_df.to_dict("records"),
                                 columns=[{"name": i, "id": i} for i in oi_df.columns]),
            dcc.Graph(figure=fig_oi)
        ]),

        dcc.Tab(label="Trades", children=[
            dash_table.DataTable(data=trades_df.to_dict("records"),
                                 columns=[{"name": i, "id": i} for i in trades_df.columns]),
            dcc.Graph(figure=fig_trades)
        ]),

        dcc.Tab(label="Monthly Trades", children=[
            dash_table.DataTable(data=monthly_df.to_dict("records"),
                                 columns=[{"name": i, "id": i} for i in monthly_df.columns]),
            dcc.Graph(figure=fig_monthly)
        ]),

        dcc.Tab(label="SQL Explorer", children=[
            dcc.Dropdown(
                id="sample-sql",
                options=[{"label": k, "value": v} for k, v in SAMPLE_SQL.items()],
                placeholder="Choose sample query"
            ),
            dcc.Textarea(id="sql-input", value=list(SAMPLE_SQL.values())[0],
                         style={"width": "100%", "height": 160}),
            html.Button("Run Query", id="run-sql"),
            html.Div(id="sql-status"),
            dcc.Graph(id="sql-graph"),
            html.Div(id="sql-table")
        ])
    ])
])

# =========================
# CALLBACKS
# =========================
@app.callback(Output("sql-input", "value"), Input("sample-sql", "value"))
def load_sample(q): return q

@app.callback(
    Output("sql-status", "children"),
    Output("sql-graph", "figure"),
    Output("sql-table", "children"),
    Input("run-sql", "n_clicks"),
    State("sql-input", "value"),
    prevent_initial_call=True
)
def run_sql(_, query):
    if not query.lower().strip().startswith("select"):
        return "Only SELECT allowed", {}, None

    engine = create_sql_engine()
    df = pd.read_sql(query, engine)

    table = dash_table.DataTable(
        data=df.head(100).to_dict("records"),
        columns=[{"name": i, "id": i} for i in df.columns],
        page_size=15
    )

    fig = {}
    if df.shape[1] >= 2:
        fig = px.bar(df, x=df.columns[0], y=df.columns[1])

    return f"{len(df)} rows", fig, table

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
