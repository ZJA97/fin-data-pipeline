import argparse
import logging
import sqlite3
from pathlib import Path

from src.summary.facts import build_facts
from src.summary.narrate import narrate

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/pipeline.db")
    parser.add_argument("--out", default="summary.txt")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    text, source = narrate(build_facts(conn))
    body = f"{text}\n\n(Summary source: {source})\n"
    Path(args.out).write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()