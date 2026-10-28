# Scope: Automated Financial Data Pipeline

## Goal
An automated, tested pipeline that ingests daily market data for 25 securities,
validates and models it in a local warehouse, and publishes analysis-ready tables
and a simple dashboard, running on a schedule with no manual steps.

## Universe
25 securities: 10 UK equities, 10 US equities, 5 ETFs (see README for tickers).

## In scope
- Daily OHLCV price ingestion from a free source (yfinance to start)
- Data-quality checks: missing days, duplicates, outliers, stale prices,
  currency/pence normalisation
- Storage in DuckDB (or SQLite) with raw -> clean -> analytics layers
- Derived metrics: daily returns, rolling volatility, moving averages, drawdown
- Scheduled runs via GitHub Actions
- Unit tests and a short data dictionary
- Dashboard or report of the outputs

## Out of scope (for now)
- Intraday or tick data
- Trading signals, backtesting, or investment advice
- Paid data feeds
- Cloud infrastructure (stretch goal only)

## Phases
- [x] 0. Setup: repo, universe, scope (this page)
- [x] 1. First win: ingest + store + validate
- [x] 2. Automation: scheduled runs, logging, failure alerts
- [x] 3. Modelling: derived metrics and analytics layer
- [ ] 4. Presentation: dashboard, README with architecture diagram, write-up

## Success criteria
- One command rebuilds the full dataset from scratch
- Pipeline runs daily without intervention
- Data-quality checks fail loudly, not silently
- A new reader can understand the project from the README in under 5 minutes

## Stack
Python, pandas, DuckDB/SQLite, pytest, GitHub Actions