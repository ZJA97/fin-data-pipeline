"""Append this run's results to the CSVs committed under data/exports/."""
import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd

DB_PATH = os.environ.get("PIPELINE_DB", "data/pipeline.db")
OUT_DIR = "data/exports"


def scalar(conn, sql):
    try:
        return conn.execute(sql).fetchone()[0] or 0
    except sqlite3.OperationalError:  # table missing: nothing was saved this run
        return 0


def append_csv(path, new):
    if os.path.exists(path):
        new = pd.concat([pd.read_csv(path), new], ignore_index=True)
    new.drop_duplicates().to_csv(path, index=False)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        for table in ("recon_breaks", "dq_results"):
            try:
                df = pd.read_sql(f"SELECT * FROM {table}", conn)
            except Exception:  # table doesn't exist when nothing was found
                continue
            append_csv(f"{OUT_DIR}/{table}.csv", df)
            print(f"{table}: {len(df)} rows exported")

        summary = pd.DataFrame([{
            "run_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "raw_prices_rows": scalar(conn, "SELECT COUNT(*) FROM raw_prices"),
            "raw_fx_rows": scalar(conn, "SELECT COUNT(*) FROM raw_fx"),
            "recon_exceptions": scalar(conn, "SELECT COUNT(*) FROM recon_breaks"),
            "dq_findings": scalar(conn, "SELECT COUNT(*) FROM dq_results"),
        }])
    append_csv(f"{OUT_DIR}/run_log.csv", summary)


if __name__ == "__main__":
    main()