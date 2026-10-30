"""Turn the facts dict into a short written summary, with a safe fallback."""
import json
import logging
import os
import re

from anthropic import Anthropic

log = logging.getLogger(__name__)
MODEL = os.getenv("SUMMARY_MODEL", "claude-haiku-5-5")

SYSTEM = """You write a short daily portfolio note for an internal operations audience.
Rules:
- Use ONLY the figures in the JSON provided, copied exactly as written.
- Never calculate, estimate, round or invent a number.
- No investment advice and no predictions.
- If there are reconciliation or data quality issues, say so plainly.
- Plain text, three short paragraphs: performance, notable positions, data quality.
- Maximum 120 words."""

NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def numbers_grounded(text: str, facts: dict) -> bool:
    """True if every number in the text is also a number in the facts."""
    allowed = set(NUMBER.findall(json.dumps(facts, ensure_ascii=False)))
    return all(n in allowed for n in NUMBER.findall(text))


def fallback_summary(f: dict) -> str:
    lines = [f"Portfolio value on {f['date']}: {f['market_value']} across {f['positions_held']} positions."]
    if f["day_pnl"] is not None:
        change = f"Day P&L: {f['day_pnl']}"
        if f["day_pnl_pct"]:
            change += f" ({f['day_pnl_pct']} of prior-day value)"
        lines.append(f"{change}. Total P&L: {f['total_pnl']}.")
    if f["top_gainers"]:
        lines.append("Top gainers: " + ", ".join(f"{m['ticker']} ({m['pnl']})" for m in f["top_gainers"]) + ".")
    if f["top_losers"]:
        lines.append("Top losers: " + ", ".join(f"{m['ticker']} ({m['pnl']})" for m in f["top_losers"]) + ".")
    recon = ", ".join(f"{k}: {v}" for k, v in f["recon_by_status"].items()) or "none"
    dq = ", ".join(f"{k}: {v}" for k, v in f["dq_issues_by_check"].items()) or "none"
    lines.append(f"Reconciliation, latest run: {recon}.")
    lines.append(f"Data quality issues, latest run: {dq}.")
    lines.append(f"Stale prices on held positions: {f['stale_prices']}.")
    return "\n".join(lines)


def narrate(facts: dict) -> tuple[str, str]:
    """Return (text, source) where source is 'llm' or 'fallback'."""
    try:
        client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        msg = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(facts, indent=2, ensure_ascii=False)}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        if not text:
            raise ValueError("empty response")
        if not numbers_grounded(text, facts):
            raise ValueError("response contained numbers not in the facts")
        return text, "llm"
    except Exception as exc:
        log.warning("LLM summary failed (%s); using fallback", exc)
        return fallback_summary(facts), "fallback"