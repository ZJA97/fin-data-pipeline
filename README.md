# Automated Financial Data Pipeline

An automated pipeline that ingests daily market data for 25 securities, validates it, and models it into analysis-ready tables.

See [docs/SCOPE.md](docs/SCOPE.md) for the full scope and phases.

## Security universe

| Group | Tickers |
|---|---|
| UK equities (10) | SHEL.L, AZN.L, HSBA.L, ULVR.L, BP.L, GSK.L, RIO.L, LSEG.L, BARC.L, DGE.L |
| US equities (10) | AAPL, MSFT, NVDA, GOOGL, AMZN, JPM, JNJ, XOM, KO, V |
| ETFs (5) | VUSA.L (S&P 500), VWRL.L (global equities), ISF.L (FTSE 100), IGLT.L (UK gilts), SGLN.L (gold) |

Tickers are provisional until validated in Phase 1.

## Status

- [x] Phase 0: Setup
- [ ] Phase 1: Ingest, store, validate
- [ ] Phase 2: Automation
- [ ] Phase 3: Modelling
- [ ] Phase 4: Presentation