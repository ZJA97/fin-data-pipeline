"""Console + rotating file logging."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import ROOT


def setup_logging(log_dir: Path | None = None) -> None:
    log_dir = log_dir or ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:  # already configured (e.g. called twice)
        return
    root.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S"))

    file_handler = RotatingFileHandler(
        log_dir / "pipeline.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )

    root.addHandler(console)
    root.addHandler(file_handler)

    # yfinance logs its own (noisy) errors for empty results, e.g. on weekends.
    # We log our own clearer warning/error per symbol instead.
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
