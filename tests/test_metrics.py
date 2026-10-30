import pandas as pd
import pytest

from src.dashboard.build_metrics import compute_metrics


def test_purchases_are_not_counted_as_returns():
    pf = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=3),
        "market_value_gbp": [100.0, 160.0, 144.0],  # day 2 includes a 50 purchase
        "total_pnl_gbp": [0.0, 10.0, -6.0],
        "daily_pnl_gbp": [0.0, 10.0, -16.0],
    })
    df = compute_metrics(pf)
    assert df["daily_return"].iloc[1] == pytest.approx(0.10)
    assert df["daily_return"].iloc[2] == pytest.approx(-0.10)
    assert df["drawdown"].min() == pytest.approx(-0.10)