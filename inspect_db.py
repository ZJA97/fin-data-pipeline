import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])

for name, sql in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print(sql, "\n")

conn.close()