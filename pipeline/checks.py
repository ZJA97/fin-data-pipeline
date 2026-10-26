"""Data-quality checks for the raw tables.

Each check takes a DataFrame (the contents of a raw table) and returns a CheckResult,
so the checks can be unit-tested without a database or network connection.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _examples(items: list[str], limit: int = 5) -> str:
    shown = ", ".join(items[:limit])
    return shown + (f" (+{len(items) - limit} more)" if len(items) > limit else "")


def check_tickers_resolved(df: pd.DataFrame, expected: list[str]) -> CheckResult:
    """Every ticker in the config returned at least one row."""
    found = set(df["ticker"]) if not df.empty else set()
    missing = sorted(set(expected) - found)
    if missing:
        return CheckResult("ticker_resolved", False, f"no data for: {_examples(missing)}")
    return CheckResult("ticker_resolved", True, f"{len(expected)}/{len(expected)} tickers have data")


def check_no_duplicates(df: pd.DataFrame) -> CheckResult:
    """No (ticker, date) appears more than once."""
    dupes = df[df.duplicated(["ticker", "date"], keep="first")]
    if not dupes.empty:
        labels = [f"{r.ticker} {r.date}" for r in dupes.itertuples()]
        return CheckResult("no_duplicates", False, f"{len(dupes)} duplicate rows: {_examples(labels)}")
    return CheckResult("no_duplicates", True, "no duplicate ticker/date rows")


def check_no_long_gaps(df: pd.DataFrame, max_gap_days: int) -> CheckResult:
    """No ticker has a gap between consecutive dates longer than max_gap_days (calendar days)."""
    if df.empty:
        return CheckResult("no_long_gaps", True, "no data to check")
    d = df[["ticker", "date"]].copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["ticker", "date"])
    d["gap_days"] = d.groupby("ticker")["date"].diff().dt.days
    bad = d[d["gap_days"] > max_gap_days]
    if not bad.empty:
        labels = [
            f"{r.ticker} {int(r.gap_days)}d gap ending {r.date.date()}" for r in bad.itertuples()
        ]
        return CheckResult("no_long_gaps", False, f"{len(bad)} gaps > {max_gap_days} days: {_examples(labels)}")
    return CheckResult("no_long_gaps", True, f"no gaps longer than {max_gap_days} days")


def check_positive_prices(df: pd.DataFrame) -> CheckResult:
    """All price columns are > 0, and close is never missing."""
    if df.empty:
        return CheckResult("positive_prices", True, "no data to check")
    non_positive = (df[PRICE_COLUMNS] <= 0).any(axis=1)
    missing_close = df["close"].isna()
    bad = df[non_positive | missing_close]
    if not bad.empty:
        labels = [f"{r.ticker} {r.date}" for r in bad.itertuples()]
        return CheckResult("positive_prices", False, f"{len(bad)} rows with non-positive/missing prices: {_examples(labels)}")
    return CheckResult("positive_prices", True, "all prices positive")


def run_all_checks(df: pd.DataFrame, expected_tickers: list[str], max_gap_days: int) -> list[CheckResult]:
    return [
        check_tickers_resolved(df, expected_tickers),
        check_no_duplicates(df),
        check_no_long_gaps(df, max_gap_days),
        check_positive_prices(df),
    ]
