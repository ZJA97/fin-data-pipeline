"""Phase 3: price reconciliation across two sources + data quality checks."""
import sqlite3
import sys
import os
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import yaml

DB_PATH = os.environ.get("PIPELINE_DB", "data/pipeline.db")
CONFIG_PATH = "config/reconciliation.yaml"

# Only these two queries should need editing to match your tables.
SQL_A = "SELECT ticker, date AS price_date, adj_close AS close FROM raw_prices WHERE source = 'yfinance'"
SQL_B = "SELECT ticker, date AS price_date, adj_close AS close FROM raw_prices WHERE source = 'tiingo'"

def load_config(path=CONFIG_PATH):
    with open(path) as f:
        return yaml.safe_load(f)


def load_prices(conn, sql):
    df = pd.read_sql(sql, conn)
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


# ---------- reconciliation ----------

def reconcile(a, b, cfg):
    rc = cfg["reconciliation"]
    key = ["ticker", "price_date"]
    m = a.drop_duplicates(key, keep="last").merge(
        b.drop_duplicates(key, keep="last"),
        on=key, how="outer", suffixes=("_a", "_b"), indicator=True,
    )
    m["abs_diff"] = (m["close_a"] - m["close_b"]).abs()
    m["pct_diff"] = m["abs_diff"] / m["close_b"].abs() * 100
    m["tolerance_pct"] = m["ticker"].map(rc.get("overrides", {})).fillna(rc["default_tolerance_pct"])
    m["warn_pct"] = np.minimum(rc["warn_tolerance_pct"], m["tolerance_pct"])

    # order matters: first matching condition wins
    m["status"] = np.select(
        [
            m["_merge"] == "left_only",
            m["_merge"] == "right_only",
            m["close_a"].isna() | m["close_b"].isna(),
            m["pct_diff"] > m["tolerance_pct"],
            m["pct_diff"] > m["warn_pct"],
        ],
        ["MISSING_IN_B", "MISSING_IN_A", "NULL_PRICE", "BREAK", "WARN"],
        default="MATCH",
    )
    return m.drop(columns="_merge")


# ---------- data quality checks ----------

def _f(source, check, ticker, price_date, detail):
    return {"source": source, "check": check, "ticker": ticker,
            "price_date": price_date, "detail": detail}


def check_nulls(df, source, cfg):
    bad = df[df[["ticker", "price_date", "close"]].isna().any(axis=1)]
    return [_f(source, "NULL_VALUE", r.ticker, r.price_date, "null in ticker/date/close")
            for r in bad.itertuples()]


def check_duplicates(df, source, cfg):
    dups = df[df.duplicated(["ticker", "price_date"], keep=False)]
    return [_f(source, "DUPLICATE", t, d, f"{len(g)} rows for same ticker+date")
            for (t, d), g in dups.groupby(["ticker", "price_date"])]


def check_stale(df, source, cfg):
    dq, out = cfg["dq"], []
    clean = df.dropna(subset=["close", "price_date"]).sort_values("price_date")
    for tkr, g in clean.groupby("ticker"):
        # a "run" is a streak of identical closes
        run_id = (g["close"] != g["close"].shift()).cumsum()
        runs = g.groupby(run_id).agg(start=("price_date", "min"), n=("close", "size"))
        for r in runs[runs["n"] >= dq["stale_run_days"]].itertuples():
            out.append(_f(source, "STALE_RUN", tkr, r.start, f"{r.n} identical closes in a row"))
        last = g["price_date"].max()
        age = int(np.busday_count(last.date(), date.today()))
        if age > dq["max_age_business_days"]:
            out.append(_f(source, "STALE_LATEST", tkr, last, f"latest price is {age} business days old"))
    return out


MARKET_OVERRIDES = {"^FTSE": "L"}


def market_of(ticker):
    if ticker in MARKET_OVERRIDES:
        return MARKET_OVERRIDES[ticker]
    # "AZN.L" -> "L", "SAP.DE" -> "DE", anything without a suffix -> "US"
    return ticker.rsplit(".", 1)[1] if "." in ticker else "US"


def check_missing_days(df, source, cfg):
    min_cov = cfg["dq"]["min_coverage_for_expected_day"]
    d = df.dropna(subset=["price_date", "close"]).copy()
    d["market"] = d["ticker"].map(market_of)
    out = []
    for market, md in d.groupby("market"):
        counts = md.groupby("price_date")["ticker"].nunique()
        expected = counts[counts >= min_cov * md["ticker"].nunique()].index
        for tkr, g in md.groupby("ticker"):
            exp = expected[(expected >= g["price_date"].min()) & (expected <= g["price_date"].max())]
            for day in exp.difference(pd.DatetimeIndex(g["price_date"])):
                out.append(_f(source, "MISSING_DAY", tkr, day, f"no price on a {market} trading day"))
    return out


CHECKS = [check_nulls, check_duplicates, check_stale, check_missing_days]


def run_dq(df, source, cfg):
    rows = []
    for check in CHECKS:
        rows += check(df, source, cfg)
    return pd.DataFrame(rows, columns=["source", "check", "ticker", "price_date", "detail"])


# ---------- persistence + entry point ----------

def save(conn, df, table, run_ts):
    if df.empty:
        return
    out = df.copy()
    out.insert(0, "run_ts", run_ts)
    out["price_date"] = pd.to_datetime(out["price_date"]).dt.strftime("%Y-%m-%d")
    out.to_sql(table, conn, if_exists="append", index=False)


def main():
    cfg = load_config()
    run_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        a, b = load_prices(conn, SQL_A), load_prices(conn, SQL_B)

        common = set(a["ticker"]) & set(b["ticker"])
        excluded = sorted((set(a["ticker"]) | set(b["ticker"])) - common)
        if excluded:
            print("Not covered by both sources, excluded from reconciliation:", ", ".join(excluded))
        recon = reconcile(a[a["ticker"].isin(common)], b[b["ticker"].isin(common)], cfg)

        breaks = recon[recon["status"] != "MATCH"]
        dq = pd.concat([run_dq(a, "source_a", cfg), run_dq(b, "source_b", cfg)], ignore_index=True)

        save(conn, breaks, "recon_breaks", run_ts)
        save(conn, dq, "dq_results", run_ts)

    print("Reconciliation:\n", recon["status"].value_counts().to_string(), "\n")
    print("Data quality findings:\n",
          dq.groupby(["source", "check"]).size().to_string() if not dq.empty else "none")
    sys.exit(1 if (breaks["status"] == "BREAK").any() else 0)


if __name__ == "__main__":
    main()