import sqlite3
from types import SimpleNamespace

import pytest

from src.summary import narrate as narrate_mod
from src.summary.facts import build_facts


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE portfolio_daily (date TEXT, market_value_gbp REAL,
            total_pnl_gbp REAL, daily_pnl_gbp REAL, positions_held INTEGER);
        CREATE TABLE daily_valuation (ticker TEXT, date TEXT, quantity REAL,
            is_stale INTEGER, total_pnl_gbp REAL);
        CREATE TABLE recon_breaks (run_ts TEXT, ticker TEXT, status TEXT);
        CREATE TABLE dq_results (run_ts TEXT, source TEXT, "check" TEXT,
            ticker TEXT, price_date TEXT, detail TEXT);

        INSERT INTO portfolio_daily VALUES
            ('2026-10-29', 2000, 100, 10, 2),
            ('2026-10-30', 2050, 150, 50, 2);
        INSERT INTO daily_valuation VALUES
            ('AAA', '2026-10-29', 10, 0, 60), ('BBB', '2026-10-29', 5, 0, 40),
            ('AAA', '2026-10-30', 10, 0, 120), ('BBB', '2026-10-30', 5, 1, 30);
        INSERT INTO recon_breaks VALUES
            ('2026-10-28', 'AAA', 'BREAK'),
            ('2026-10-29', 'AAA', 'WARN'), ('2026-10-29', 'BBB', 'WARN'),
            ('2026-10-29', 'BBB', 'BREAK');
        INSERT INTO dq_results VALUES
            ('2026-10-29', 'source_a', 'MISSING_DAY', 'BBB', '2026-10-27', 'x');
    """)
    return c


def fake_client(text, stop_reason="end_turn"):
    reply = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=None,
    )
    return lambda: SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kw: reply)
    )

def test_truncated_response_triggers_fallback(conn, monkeypatch):
    monkeypatch.setattr(
        narrate_mod, "Anthropic", fake_client("Value is £2,050 (-0", "max_tokens")
    )
    text, source = narrate_mod.narrate(build_facts(conn))
    assert source == "fallback"


def test_facts_values(conn):
    f = build_facts(conn)
    assert f["date"] == "2026-10-30"
    assert f["market_value"] == "£2,050"
    assert f["day_pnl"] == "£50"
    assert f["day_pnl_pct"] == "+2.50%"
    assert f["top_gainers"][0] == {"ticker": "AAA", "pnl": "£60"}
    assert f["top_losers"][0] == {"ticker": "BBB", "pnl": "-£10"}
    assert f["stale_prices"] == 1
    assert f["recon_by_status"] == {"WARN": 2, "BREAK": 1}  # latest run only
    assert f["dq_issues_by_check"] == {"MISSING_DAY": 1}


def test_grounding_rejects_invented_number(conn):
    f = build_facts(conn)
    assert narrate_mod.numbers_grounded("Value was £2,050 on 2026-10-30.", f)
    assert not narrate_mod.numbers_grounded("Value was £9,999 today.", f)


def test_llm_text_used_when_grounded(conn, monkeypatch):
    monkeypatch.setattr(narrate_mod, "Anthropic", fake_client("Value is £2,050."))
    text, source = narrate_mod.narrate(build_facts(conn))
    assert source == "llm"


def test_invented_number_triggers_fallback(conn, monkeypatch):
    monkeypatch.setattr(narrate_mod, "Anthropic", fake_client("Value is £9,999."))
    text, source = narrate_mod.narrate(build_facts(conn))
    assert source == "fallback"
    assert "£2,050" in text


def test_falls_back_when_api_fails(conn, monkeypatch):
    def boom():
        raise RuntimeError("API down")
    monkeypatch.setattr(narrate_mod, "Anthropic", boom)
    text, source = narrate_mod.narrate(build_facts(conn))
    assert source == "fallback"