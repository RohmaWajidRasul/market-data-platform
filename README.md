# Kalshi Market Data Platform

An end-to-end data engineering and analytics platform for collecting Kalshi market data, storing it in Azure, and exploring it through an interactive Plotly Dash dashboard.

## Overview

The platform:

1. Fetches open markets from the Kalshi API.
2. Enriches markets with event categories.
3. Writes raw Parquet and JSON files to Azure Blob Storage.
4. Persists cleaned market data in Azure SQL Database.
5. Loads recent Parquet files into a Dash analytics dashboard.

## Architecture

```text
Kalshi API
    |
    v
Azure Function (timer trigger, every 30 minutes)
    |
    +--> Azure Blob Storage
    |      +-- Raw Parquet files
    |      +-- Raw JSON files
    |      +-- Retained master data
    |
    +--> Azure SQL Database
           |
           v
    Plotly Dash dashboard
```

## Features

- Automated market data ingestion with an Azure timer-triggered function
- Parallel event-category enrichment
- Parquet-based raw data storage
- Historical data retention and deduplication
- Azure SQL persistence
- Interactive volume, open-interest, and trend visualizations
- SQL query explorer
- Environment-variable-based configuration

## Repository structure

```text
.
├── app.py             # Plotly Dash analytics dashboard
├── function_app.py    # Azure Function and ingestion pipeline
├── host.json          # Azure Functions host configuration
├── requirements.txt   # Python dependencies
└── README.md          # Project documentation
```

## Technology stack

- Python 3.11
- Azure Functions
- Azure Blob Storage
- Azure SQL Database
- Pandas and PyArrow
- SQLAlchemy and pyodbc
- Plotly Dash
- Microsoft ODBC Driver 17 for SQL Server

## Prerequisites

- Python 3.11
- Azure Functions Core Tools
- Microsoft ODBC Driver 17 for SQL Server
- Access to:
  - The Kalshi API
  - An Azure Blob Storage container
  - An Azure SQL Database

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

### Azure Function

For local Azure Functions development, create `local.settings.json` in the project root. Do not commit this file.

```json
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
    "SQL_TABLE": "KalshiMarketData",
    "BLOB_CONTAINER_NAME": "kalshdata",
    "RAW_FOLDER": "raw/",
    "JSON_FOLDER": "raw_json/",
    "RETENTION_DAYS": "30"
  }
}
```

`BLOB_SAS_URL` should be a container SAS URL. The function runs on startup and then every 30 minutes.

### Dash dashboard

Create a `.env` file in the project root. Do not commit this file.

```dotenv
BLOB_SAS_URL=...
SQL_SERVER=...
SQL_DATABASE=...
SQL_USER=...
SQL_PASSWORD=...
SQL_TABLE=KalshiMarketData
BLOB_CONTAINER_NAME=kalshdata
RAW_FOLDER=raw/
JSON_FOLDER=raw_json/
MAX_FILES=50
```

## Running locally

### Start the ingestion function

From the project root:

```bash
func start
```

The timer function fetches open markets, writes the raw files to Blob Storage, and updates Azure SQL.

### Start the dashboard

```bash
python app.py
```

Then open [http://127.0.0.1:8050](http://127.0.0.1:8050).

The dashboard includes:

- Daily volume by category
- Open interest by category
- Trades over time with a 30-day moving average
- Monthly trades by category
- A SQL Explorer for sample and custom queries

Keep `.env` and `local.settings.json` out of version control. Store secrets in Azure Function application settings when deploying.

## Author

Rohma Wajid Rasul
