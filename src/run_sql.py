"""Run every .sql file in sql/<layer>/ in filename order, with timings."""
import re
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = "data/pipeline.db"


def main() -> None:
    layer = sys.argv[1]  # e.g. "cleaned"
    files = sorted((Path("sql") / layer).glob("*.sql"))
    if not files:
        sys.exit(f"No .sql files found in sql/{layer}/")

    created = []
    with sqlite3.connect(DB_PATH) as conn:
        for f in files:
            text = f.read_text(encoding="utf-8")
            start = time.time()
            conn.executescript(text)
            print(f"Running {f.name:28} {time.time() - start:6.1f}s")
            created += re.findall(r"CREATE TABLE (\w+)", text)

        print("\nRow counts:")
        for table in created:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n}")


if __name__ == "__main__":
    main()