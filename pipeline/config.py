"""Load the ticker/FX configuration from YAML."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "tickers.yaml"


@dataclass(frozen=True)
class Config:
    start_date: str
    max_gap_days: int
    database_path: Path
    tickers: list[str]
    fx_pairs: list[str]


def _dedupe(items: list[str]) -> list[str]:
    """Remove duplicates but keep the original order."""
    return list(dict.fromkeys(str(i).strip() for i in items))


def load_config(path: Path | str = DEFAULT_CONFIG) -> Config:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    missing = [k for k in ("start_date", "tickers", "fx_pairs") if k not in raw]
    if missing:
        raise ValueError(f"Config {path} is missing required keys: {', '.join(missing)}")

    db_path = Path(raw.get("database_path", "data/pipeline.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    return Config(
        start_date=str(raw["start_date"]),
        max_gap_days=int(raw.get("max_gap_days", 7)),
        database_path=db_path,
        tickers=_dedupe(raw["tickers"]),
        fx_pairs=_dedupe(raw["fx_pairs"]),
    )
