# Automated Financial Data Pipeline

An automated pipeline that ingests daily market data for 25 securities, validates it, and models it into analysis-ready tables.

See [docs/SCOPE.md](docs/SCOPE.md) for the full scope and phases.

## Security universe

| Group | Tickers |
|---|---|
| UK equities (10) | SHEL.L, AZN.L, HSBA.L, ULVR.L, BP.L, GSK.L, RIO.L, LSEG.L, BARC.L, DGE.L |
| US equities (10) | AAPL, MSFT, NVDA, GOOGL, AMZN, JPM, JNJ, XOM, KO, V |
| ETFs (5) | VUSA.L (S&P 500), VWRL.L (global equities), ISF.L (FTSE 100), IGLT.L (UK gilts), SGLN.L (gold) |

All 25 tickers resolved and were validated in Phase 1.

## Status

- [x] Phase 0: Setup
- [x] Phase 1: Ingest, store, validate
- [ ] Phase 2: Automation
- [ ] Phase 3: Modelling
- [ ] Phase 4: Presentation

## Phase 1: Ingestion

Python scripts that pull prices and FX into raw SQLite tables, with logging and error handling.

- **Config-driven:** every ticker and FX pair lives in [`config/tickers.yaml`](config/tickers.yaml), not in code. Add or remove a line and re-run.
- **Fetch:** `yfinance` pulls daily bars for 25 securities and 4 FX pairs into the tables `raw_prices` and `raw_fx`.
- **Validated at ingestion:** rows with missing, non-numeric or non-positive prices (open, high, low, close, adj_close) are rejected before insert and logged with a count. Everything else is stored as received.
- **Incremental:** each run only loads days newer than what is already stored, and only completed trading days.
- **Resilient:** each symbol is retried with backoff, and one failing ticker is logged without stopping the rest.
- **Logged:** console output plus a rotating log file at `logs/pipeline.log`.

### Data quality checks

These run after ingestion, as a second safeguard over what is stored.

| Check | Fails when |
|---|---|
| `ticker_resolved` | a configured ticker returned no rows |
| `no_duplicates` | a (ticker, date) pair appears more than once |
| `no_long_gaps` | consecutive dates for a ticker are more than `max_gap_days` apart |
| `positive_prices` | any price is zero or negative, or `close` is missing |

The run exits with code `1` if any ingestion step or check fails, so a scheduler can alert on it later.

### Run it (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m pipeline.run     # ingest, then run the checks
python -m pytest           # 2 tests: the checks, and ingestion validation
```

### Example output

Output of a re-run after the fix below. Ticker lines are abridged.

```text
13:48:52 INFO    === Ingestion ===
13:48:53 INFO    AAPL: no new rows since 2026-10-23
13:48:53 INFO    MSFT: no new rows since 2026-10-23
13:48:53 INFO    GOOGL: no new rows since 2026-10-23
13:48:53 INFO    AMZN: no new rows since 2026-10-23
13:48:53 INFO    NVDA: no new rows since 2026-10-23
13:48:53 INFO    JPM: no new rows since 2026-10-23
13:48:53 INFO    XOM: no new rows since 2026-10-23
13:48:54 INFO    JNJ: no new rows since 2026-10-23
13:48:54 INFO    PG: no new rows since 2026-10-23
13:48:54 INFO    KO: no new rows since 2026-10-23
13:48:54 INFO    HSBA.L: no new rows since 2026-10-23
13:48:54 INFO    BP.L: no new rows since 2026-10-23
13:48:54 INFO    SHEL.L: no new rows since 2026-10-23
13:48:54 INFO    AZN.L: no new rows since 2026-10-23
13:48:54 INFO    ULVR.L: no new rows since 2026-10-23
13:48:54 INFO    LLOY.L: no new rows since 2026-10-23
13:48:55 INFO    BARC.L: no new rows since 2026-10-23
13:48:55 INFO    SPY: no new rows since 2026-10-23
13:48:55 INFO    QQQ: no new rows since 2026-10-23
13:48:55 INFO    VTI: no new rows since 2026-10-23
13:48:55 INFO    VWRL.L: no new rows since 2026-10-22
13:48:55 INFO    ISF.L: no new rows since 2026-10-23
13:48:55 INFO    AGG: no new rows since 2026-10-23
13:48:55 INFO    GLD: no new rows since 2026-10-23
13:48:55 INFO    ^FTSE: no new rows since 2026-10-23
13:48:55 INFO    raw_prices: 25 symbols, 0 new rows, 0 failed
13:48:55 INFO    GBPUSD=X: no new rows since 2026-10-23
13:48:55 INFO    EURUSD=X: no new rows since 2026-10-23
13:48:55 INFO    EURGBP=X: no new rows since 2026-10-23
13:48:56 INFO    USDJPY=X: no new rows since 2026-10-23
13:48:56 INFO    raw_fx: 4 symbols, 0 new rows, 0 failed
13:48:56 INFO    === Data quality checks ===
13:48:56 INFO    raw_prices PASS ticker_resolved  25/25 tickers have data
13:48:56 INFO    raw_prices PASS no_duplicates    no duplicate ticker/date rows
13:48:56 INFO    raw_prices PASS no_long_gaps     no gaps longer than 7 days
13:48:56 INFO    raw_prices PASS positive_prices  all prices positive
13:48:56 INFO    raw_fx PASS ticker_resolved  4/4 tickers have data
13:48:56 INFO    raw_fx PASS no_duplicates    no duplicate ticker/date rows
13:48:56 INFO    raw_fx PASS no_long_gaps     no gaps longer than 7 days
13:48:56 INFO    raw_fx PASS positive_prices  all prices positive
13:48:56 INFO    Finished: all good
```

### Data quality incident and fix

On the first full run, ingestion reported no failures, but the `positive_prices` check failed. One `VWRL.L` row dated 2026-10-23 had open, high, low and volume, but no `close` or `adj_close`. Querying Yahoo Finance directly for that date returned no price data, so the missing values were left unfilled rather than estimated.

**Cause:** ingestion inserted whatever came back without validating prices. Because loads start after the latest stored date, a bad row that was already stored would never be refetched.

**Fix:**
- `pipeline/ingest.py` now rejects rows with missing, non-numeric or non-positive prices before insert, and logs how many were rejected per symbol.
- `tests/test_ingest.py` is a regression test using simulated data and in-memory SQLite (no network). It checks that a bad row is rejected and a good row is stored.
- The single bad row was deleted after confirming that exactly one row matched, so the next run can try to fetch that date again.
- After the fix, all 8 checks (4 per table) passed.

**Known limitation:** the checks confirm that stored data is valid, not that it is up to date. At the time of writing, `VWRL.L` ended at 2026-10-22 because Yahoo had not returned a valid bar for the 23rd. A freshness check would catch this and is not yet implemented.

### Project layout

```text
config/tickers.yaml         instruments and settings
pipeline/config.py          config loader
pipeline/logging_setup.py   logging setup
pipeline/db.py              SQLite schema and helpers
pipeline/ingest.py          fetch, retry, validate, load
pipeline/checks.py          data quality checks
pipeline/run.py             entry point
tests/test_checks.py        test for the checks
tests/test_ingest.py        regression test for ingestion validation
```