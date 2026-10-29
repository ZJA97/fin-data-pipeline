# Scope: Automated Financial Data Pipeline

## Goal
An automated, tested pipeline that ingests daily market data for 25 securities from two
independent sources, reconciles and validates it, models it into a GBP portfolio ledger
and valuation, and publishes analysis-ready tables, a dashboard and a daily summary,
running on a schedule with no manual steps.

## Universe
25 securities and 4 FX pairs (see the README for tickers):
- 7 UK equities, 10 US equities, 7 ETFs (24 tradable securities)
- 1 index (^FTSE), kept as a benchmark and not traded
- FX pairs: GBPUSD, EURUSD, EURGBP, USDJPY

## In scope
- Daily OHLCV price and FX ingestion from yfinance, with Tiingo as a second source
  for US securities
- A synthetic, deliberately messy trade ledger, so the cleaning layer has real work to do
- SQLite storage with raw -> cleaned -> analytics layers, built in SQL
- Daily positions, market value and P&L in GBP, using average-cost accounting,
  pence/pound normalisation and historical FX
- Reconciliation of the two price sources with configurable tolerances and a
  "breaks" table
- Data-quality checks: nulls, duplicates, stale prices, missing days, long gaps
- Scheduled runs on GitHub Actions: weekday schedule, retries on failure, email alerts
  when checks fail, results written back to the repo
- Power BI dashboard: portfolio value, returns, currency and sector exposure,
  volatility and drawdown, and a reconciliation breaks page
- An LLM-written daily summary emailed out
- pytest tests, a README with an architecture diagram, and a limitations and
  next steps section

## Out of scope (for now)
- Intraday or tick data
- Real trading data: all trades are synthetic, and results demonstrate the mechanics,
  not investment performance
- Trading signals, backtesting, or investment advice
- Paid data feeds
- Cloud infrastructure (stretch goal only)

## Phases
| Phase | What you build | Status |
|---|---|---|
| 0. Setup | GitHub repo, folder structure, 25 securities, one-page scope | Done |
| 1. Ingestion | Python scripts pulling prices and FX into raw tables, with logging and error handling | Done |
| 2. Ledger and valuation | Synthetic trade generator, SQL transformations (raw -> cleaned -> analytics), daily positions, market value and P&L in GBP | Done |
| 3. Reconciliation and data quality | Price comparison across both sources, tolerance rules, a "breaks" table, checks for nulls, duplicates, stale prices and missing days | Done |
| 4. Automation | GitHub Actions runs the pipeline every weekday, retries on failure, emails an alert when checks fail, writes data back to the repo | Done |
| 5. Dashboard | Power BI with portfolio value, returns, currency and sector exposure, volatility and drawdown, and a reconciliation breaks page | Not started |
| 6. AI summary and polish | LLM-written daily summary emailed out, pytest tests, README with architecture diagram, "limitations and next steps" section | Not started |

## Success criteria
- One command (`python run_pipeline.py`) rebuilds the full dataset from scratch
- Pipeline runs daily without intervention
- Data-quality checks fail loudly, not silently
- A new reader can understand the project from the README in under 5 minutes

## Stack
Python, pandas, SQLite, SQL, pytest, GitHub Actions, yfinance and Tiingo APIs, Power BI