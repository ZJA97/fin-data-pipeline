import sqlite3
import sys

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

with sqlite3.connect("data/pipeline.db") as conn:
    print(pd.read_sql(sys.argv[1], conn).to_string(index=False))