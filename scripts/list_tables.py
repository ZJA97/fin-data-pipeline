import sqlite3

conn = sqlite3.connect("data/pipeline.db")
for name, kind in conn.execute(
    "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({name})")]
    print(f"{kind:5} {name}: {', '.join(cols)}")