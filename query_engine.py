"""
Converts a plain-English business question into a SQL query, then runs it
safely against the local SQLite database.
"""

import os
import time
import sqlite3
import pandas as pd
from google import genai
from google.genai import errors as genai_errors
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.6-flash"  # free-tier via AI Studio as of writing; check ai.google.dev/gemini-api/docs/models if this changes


def _generate_with_retry(prompt, max_retries=3, base_delay=2):
    """Calls the model with retry + exponential backoff for transient errors (e.g. 503)."""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text
        except genai_errors.ServerError as e:
            if attempt == max_retries - 1:
                raise
            wait = base_delay * (2 ** attempt)
            time.sleep(wait)
    raise RuntimeError("Model call failed after retries.")


def get_schema(db_path="business.db", table="data"):
    """Returns a list of (column_name, column_type) tuples for the table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    conn.close()
    return [(col[1], col[2]) for col in columns]


def _clean_sql(raw_text):
    """Strips markdown code fences if the model wraps its answer in them."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip(";")


def generate_sql(question, db_path="business.db", table="data"):
    schema = get_schema(db_path, table)
    schema_str = "\n".join(f"- {name} ({dtype})" for name, dtype in schema)

    prompt = f"""You are a SQL expert working with a SQLite database.
Table name: {table}
Schema:
{schema_str}

Write ONE SQLite SELECT query that answers this question: {question}

Rules:
- Return ONLY the SQL query. No explanation, no markdown formatting.
- Only SELECT statements are allowed. Never write, update, insert, or delete data.
- Date columns are stored as text in 'YYYY-MM-DD' format. Use SQLite's
  strftime() or standard string comparisons on them directly — no format
  conversion is needed.
"""
    return _clean_sql(_generate_with_retry(prompt))


def run_sql(sql, db_path="business.db"):
    """Executes a SQL string. Only SELECT queries are permitted."""
    if not sql.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed for safety.")

    conn = sqlite3.connect(db_path)
    try:
        result_df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return result_df
