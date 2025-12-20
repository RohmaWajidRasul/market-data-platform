KALSHI MARKET DATA PIPELINE & ANALYTICS DASHBOARD
================================================

End-to-end data engineering and analytics system that ingests live Kalshi market data,
stores it in Azure Blob Storage and Azure SQL Database, and visualizes insights through
an interactive Dash dashboard.

This project demonstrates cloud-native data ingestion, transformation, storage,
and analytics using Python, Azure Functions, Azure SQL, and Plotly Dash.

------------------------------------------------
ARCHITECTURE OVERVIEW
------------------------------------------------

Kalshi API
   ↓
Azure Function (Timer Trigger, Python)
   ↓
Azure Blob Storage
   - Raw Parquet files
   - Raw JSON files
   - Master Parquet (historical)
   ↓
Azure SQL Database
   - Structured relational storage
   ↓
Dash Analytics Dashboard
   - Category insights
   - Volume & open interest
   - Time-series trends
   - SQL query explorer

------------------------------------------------
FEATURES
------------------------------------------------

• Automated market data ingestion every 5 minutes  
• Parallel API enrichment for event categories  
• Efficient Parquet-based storage  
• Historical master dataset with deduplication  
• Azure SQL relational persistence  
• Interactive analytics dashboard  
• Secure configuration using environment variables  

------------------------------------------------
REPOSITORY STRUCTURE
------------------------------------------------

.
├── function_app.py        # Azure Function (Timer Trigger)
├── dashboard.py           # Dash analytics application
├── requirements.txt       # Python dependencies
├── README.txt             # Project documentation
├── local.settings.json    # Azure Functions local config (not committed)
└── .env                   # Dashboard environment variables (not committed)

------------------------------------------------
TECH STACK
------------------------------------------------

• Python 3.9+
• Azure Functions (Timer Trigger)
• Azure Blob Storage
• Azure SQL Database
• Pandas / PyArrow
• SQLAlchemy + pyodbc
• Plotly Dash
• Microsoft ODBC Driver 17 for SQL Server

------------------------------------------------
AZURE SQL TABLE SCHEMA
------------------------------------------------

CREATE TABLE KalshiMarketData (
    can_close_early INT,
    category NVARCHAR(255),
    close_time DATETIME2,
    created_time DATETIME2,
    early_close_condition NVARCHAR(MAX),
    event_ticker NVARCHAR(255),
    expected_expiration_time DATETIME2,
    expiration_time DATETIME2,
    expiration_value NVARCHAR(255),
    last_price FLOAT,
    last_price_dollars NVARCHAR(50),
    latest_expiration_time DATETIME2,
    liquidity FLOAT,
    liquidity_dollars NVARCHAR(50),
    market_type NVARCHAR(50),
    no_ask INT,
    no_ask_dollars NVARCHAR(50),
    no_bid INT,
    no_bid_dollars NVARCHAR(50),
    no_sub_title NVARCHAR(MAX),
    notional_value FLOAT,
    notional_value_dollars NVARCHAR(50),
    open_interest INT,
    open_time DATETIME2,
    previous_price FLOAT,
    previous_price_dollars NVARCHAR(50),
    previous_yes_ask FLOAT,
    previous_yes_ask_dollars NVARCHAR(50),
    previous_yes_bid FLOAT,
    previous_yes_bid_dollars NVARCHAR(50),
    price_level_structure NVARCHAR(MAX),
    price_ranges NVARCHAR(50),
    response_price_units NVARCHAR(50),
    result NVARCHAR(MAX),
    risk_limit_cents INT,
    rules_primary NVARCHAR(MAX),
    rules_secondary NVARCHAR(MAX),
    settlement_timer_seconds INT,
    status NVARCHAR(50),
    subtitle NVARCHAR(MAX),
    tick_size FLOAT,
    ticker NVARCHAR(255),
    title NVARCHAR(MAX),
    volume INT,
    volume_24h INT,
    yes_ask FLOAT,
    yes_ask_dollars NVARCHAR(50),
    yes_bid FLOAT,
    yes_bid_dollars NVARCHAR(50),
    yes_sub_title NVARCHAR(MAX),
    strike_type NVARCHAR(50),
    [custom_strike.Individual] NVARCHAR(MAX),
    [custom_strike.Leader] NVARCHAR(MAX),
    [custom_strike.Person] NVARCHAR(MAX),
    [custom_strike.Company] NVARCHAR(MAX),
    cap_strike NVARCHAR(50),
    [custom_strike.Actor] NVARCHAR(MAX),
    floor_strike NVARCHAR(50),
    [custom_strike.Artist] NVARCHAR(MAX),
    [custom_strike.Song] NVARCHAR(MAX),
    [custom_strike.Country] NVARCHAR(MAX),
    [custom_strike.Chart] NVARCHAR(MAX),
    [custom_strike.Geography] NVARCHAR(MAX),
    [custom_strike.Candidate] NVARCHAR(MAX),
    [custom_strike.Party] NVARCHAR(MAX),
    [custom_strike.House Winner] NVARCHAR(MAX),
    [custom_strike.President Winner] NVARCHAR(MAX),
    [custom_strike.Senate Winner] NVARCHAR(MAX),
    [custom_strike.Pres candidate] NVARCHAR(MAX),
    [custom_strike.State] NVARCHAR(MAX),
    event_title NVARCHAR(MAX),
    event_category NVARCHAR(255),
    fetched_utc DATETIME2
);

------------------------------------------------
HOW TO RUN – AZURE FUNCTION (LOCAL)
------------------------------------------------

1. Install prerequisites:
   • Python 3.9+
   • Azure Functions Core Tools
   • Microsoft ODBC Driver 17 for SQL Server

2. Create and activate virtual environment:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. Install dependencies:
   pip install -r requirements.txt

4. Configure local.settings.json:
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "...",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "BLOB_SAS_URL": "...",
       "SQL_SERVER": "...",
       "SQL_DATABASE": "...",
       "SQL_USER": "...",
       "SQL_PASSWORD": "...",
       "SQL_TABLE": "KalshiMarketData"
     }
   }

5. Start Azure Function:
   func start

The function will automatically trigger every 5 minutes.

------------------------------------------------
HOW TO RUN – DASH DASHBOARD
------------------------------------------------

1. Create `.env` file in project root:
   BLOB_SAS_URL=...
   SQL_SERVER=...
   SQL_DATABASE=...
   SQL_USER=...
   SQL_PASSWORD=...
   SQL_TABLE=KalshiMarketData

2. Run dashboard:
   python dashboard.py

3. Open browser:
   http://127.0.0.1:8050

------------------------------------------------
DASHBOARD FEATURES
------------------------------------------------

• Daily volume by category  
• Open interest distribution  
• Trades over time with moving average  
• Monthly transaction analysis  
• SQL Explorer for live database queries  

------------------------------------------------
SECURITY NOTES
------------------------------------------------

• Secrets are loaded via environment variables
• `.env` and `local.settings.json` should not be committed
• SQL access uses encrypted connections

------------------------------------------------
AUTHOR
------------------------------------------------

Rohma Wajid Rasul

------------------------------------------------
END OF FILE
------------------------------------------------
