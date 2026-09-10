"""
Turns a raw SQL result into a plain-English business insight, citing the
actual numbers rather than making generic statements.
"""

import os
import time
from google import genai
from google.genai import errors as genai_errors
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.6-flash"


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


def generate_insight(question, sql, result_df):
    # Cap the preview so we don't send huge result sets into the prompt
    preview = result_df.head(20).to_string(index=False)

    prompt = f"""A business user asked: "{question}"

This SQL query was run:
{sql}

Result:
{preview}

Write a 2-4 sentence business insight explaining this result.
- Cite specific numbers from the result.
- If a category, region, or customer stands out, name it directly.
- No generic filler like "this shows an interesting trend."
"""
    return _generate_with_retry(prompt)
