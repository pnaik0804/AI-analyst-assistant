"""
Loads a CSV file into a local SQLite database so the app can query it with real SQL.

Usage:
    python load_data.py path/to/your_data.csv
"""

import sqlite3
import sys
import pandas as pd


def load_csv_to_sqlite(csv_path, db_path="business.db", table="data"):
    # latin-1 handles the encoding of common Kaggle datasets like Superstore
    df = pd.read_csv(csv_path, encoding="latin-1")

    # Clean column names: spaces and special characters break SQL queries
    df.columns = [c.strip().replace(" ", "_").replace("-", "_") for c in df.columns]

    # Normalize likely date columns to ISO format (YYYY-MM-DD). SQLite's
    # date functions (strftime, date comparisons) only work reliably on
    # this format — source CSVs are often MM/DD/YYYY or other formats that
    # silently fail to match instead of erroring, which is worse.
    normalized_date_cols = []
    for col in df.columns:
        if df[col].dtype == object and "date" in col.lower():
            parsed = pd.to_datetime(df[col], errors="coerce")
            # Only convert if the column is mostly real dates, to avoid
            # corrupting a column that just happens to have "date" in its name
            if parsed.notna().mean() > 0.8:
                df[col] = parsed.dt.strftime("%Y-%m-%d")
                normalized_date_cols.append(col)

    conn = sqlite3.connect(db_path)
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()

    print(f"Loaded {len(df)} rows into '{db_path}' (table: '{table}')")
    print(f"Columns: {list(df.columns)}")
    if normalized_date_cols:
        print(f"Normalized to YYYY-MM-DD format: {normalized_date_cols}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "superstore.csv"
    load_csv_to_sqlite(csv_path)
