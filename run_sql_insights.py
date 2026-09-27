"""
run_sql_insights.py
--------------------
Parses sql/insights.sql into its individual statements (split on the
"-- N." numbered comment headers) and runs each one against the
SQLite database, printing the result as a small table. This is the
same execution path the Streamlit app's "SQL Insights" tab uses.

Run:
    python run_sql_insights.py
"""

import re
import sqlite3
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
DB_PATH = BASE / "db" / "fitbit.db"
SQL_PATH = BASE / "sql" / "insights.sql"


def load_queries():
    """Return a list of (title, sql) tuples parsed from insights.sql."""
    text = SQL_PATH.read_text()
    # Split on lines like "-- 3. Title text"
    parts = re.split(r"\n-- (\d+)\.\s*(.*?)\n", text)
    # parts = [preamble, num, title, sql, num, title, sql, ...]
    queries = []
    for i in range(1, len(parts), 3):
        num, title, sql = parts[i], parts[i + 1], parts[i + 2]
        # A title can wrap onto a following "--    ..." comment line; strip those.
        sql_clean = "\n".join(
            line for line in sql.splitlines() if not line.strip().startswith("--")
        ).strip().rstrip(";")
        queries.append((f"{num}. {title.strip()}", sql_clean))
    return queries


def main():
    conn = sqlite3.connect(DB_PATH)
    pd.set_option("display.max_rows", 20)
    pd.set_option("display.width", 120)

    for title, sql in load_queries():
        print("\n" + "=" * 70)
        print(title)
        print("=" * 70)
        df = pd.read_sql_query(sql, conn)
        print(df.to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()
