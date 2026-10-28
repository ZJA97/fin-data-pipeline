import pandas as pd
from src.reconcile import reconcile, check_duplicates, check_stale, check_missing_days

CFG = {
    "reconciliation": {"default_tolerance_pct": 0.5, "warn_tolerance_pct": 0.1, "overrides": {}},
    "dq": {"stale_run_days": 3, "max_age_business_days": 3, "min_coverage_for_expected_day": 0.5},
}


def prices(rows):
    df = pd.DataFrame(rows, columns=["ticker", "price_date", "close"])
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


def test_reconcile_statuses():
    a = prices([("AAA", "2026-01-05", 100), ("AAA", "2026-01-06", 100), ("AAA", "2026-01-07", 100)])
    b = prices([("AAA", "2026-01-05", 100.01), ("AAA", "2026-01-06", 102), ("AAA", "2026-01-08", 100)])
    r = reconcile(a, b, CFG).set_index("price_date")["status"]
    assert r["2026-01-05"] == "MATCH"
    assert r["2026-01-06"] == "BREAK"
    assert r["2026-01-07"] == "MISSING_IN_B"
    assert r["2026-01-08"] == "MISSING_IN_A"


def test_duplicates_found():
    df = prices([("AAA", "2026-01-05", 1), ("AAA", "2026-01-05", 1)])
    assert len(check_duplicates(df, "s", CFG)) == 1


def test_stale_run_found():
    df = prices([("AAA", f"2026-01-0{d}", c) for d, c in zip([5, 6, 7, 8], [10, 10, 10, 11])])
    runs = [f for f in check_stale(df, "s", CFG) if f["check"] == "STALE_RUN"]
    assert len(runs) == 1


def test_missing_day_found():
    rows = [("A", d, 1) for d in ["2026-01-05", "2026-01-06", "2026-01-07"]]
    rows += [("C", d, 1) for d in ["2026-01-05", "2026-01-06", "2026-01-07"]]
    rows += [("B", "2026-01-05", 1), ("B", "2026-01-07", 1)]  # B misses the 6th
    found = check_missing_days(prices(rows), "s", CFG)
    assert [(f["ticker"], str(f["price_date"].date())) for f in found] == [("B", "2026-01-06")]