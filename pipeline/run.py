"""Entry point:  python -m pipeline.run"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

import pandas as pd

from .checks import run_all_checks
from .config import DEFAULT_CONFIG, load_config
from .db import get_connection, init_db
from .ingest import ingest_symbols
from .logging_setup import setup_logging

log = logging.getLogger("pipeline")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest prices and FX into raw tables, then run checks.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to the YAML config")
    args = parser.parse_args(argv)

    setup_logging()
    try:
        cfg = load_config(args.config)
    except (OSError, ValueError) as exc:
        log.error("Could not load config: %s", exc)
        return 2

    targets = [("raw_prices", cfg.tickers), ("raw_fx", cfg.fx_pairs)]
    conn = get_connection(cfg.database_path)
    ok = True

    try:
        init_db(conn)
        end = date.today()  # exclusive: today's bar is still forming

        log.info("=== Ingestion ===")
        for table, symbols in targets:
            results = ingest_symbols(conn, table, symbols, cfg.start_date, end)
            failed = [r for r in results if r.error]
            total = sum(r.rows for r in results)
            log.info("%s: %d symbols, %d new rows, %d failed", table, len(symbols), total, len(failed))
            ok &= not failed

        log.info("=== Data quality checks ===")
        for table, symbols in targets:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            for check in run_all_checks(df, symbols, cfg.max_gap_days):
                level = logging.INFO if check.passed else logging.ERROR
                log.log(level, "%s %-4s %-16s %s", table, "PASS" if check.passed else "FAIL", check.name, check.detail)
                ok &= check.passed
    finally:
        conn.close()

    log.info("Finished: %s", "all good" if ok else "completed with problems - see log above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
