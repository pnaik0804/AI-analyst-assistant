# AI Business Analyst Assistant

## Problem
Analysts spend hours answering repetitive business questions and building
one-off reports. This tool lets a business user upload a dataset and ask
a plain-English question (e.g. "Why did revenue drop in March?") and get
back a reviewable SQL query, the data, a chart, and a written explanation
of what likely caused the result.

## Approach
- Data is loaded into a local SQLite database so the app runs real SQL
  instead of just filtering a CSV in memory. Datasets can be loaded via
  CLI (`load_data.py`) or uploaded directly in the app's sidebar.
- An LLM (Google `gemini-3.6-flash`, used via the free-tier Gemini API) is given the table schema and asked to
  generate a single SELECT query for the user's question. Only SELECT
  statements are permitted to execute — no writes are ever allowed.
- The generated SQL is shown in an editable box before it runs — the
  AI's query is reviewed, not executed blindly.
- The query result is passed back to the model a second time, which writes
  a short, numbers-specific business explanation rather than a generic
  summary.
- If the result is a category + a number, a bar chart renders automatically;
  if the x-axis looks like a date, a line chart renders instead.
- Query history is clickable — selecting a past question reloads its SQL
  so it can be re-run instantly. Results can be exported as a CSV.
- Built with Streamlit for a fast, demoable UI.

## Datasets
Superstore dataset — 9,994 rows, orders spanning 2014–2017, 793 unique customers, total sales of $2,297,200.86.

## Results
"Tested on the Superstore dataset. Correctly answered 9/10 manually
verified questions about sales by region, category performance, and
month-over-month change. Average response time ~3-4 seconds per query."

## Limitations
- The model can occasionally generate an incorrect or overly broad SQL
  query — always spot-check unfamiliar results against the raw data.
- Only SELECT queries are allowed, so this can't yet handle multi-step
  questions that need several joins or intermediate calculations.
- Charting is basic (single category vs. single number) — more complex
  visual requests aren't auto-detected.
- Not deployed for real production use — API costs and rate limits aren't
  handled for concurrent users.

## How to Run It
1. Clone this repo and `cd` into it.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your Gemini API key (get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
4. Download a dataset (e.g. the
   [Kaggle Superstore dataset](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final))
   and save it as `superstore.csv` in this folder.
5. Load it into the database: `python load_data.py superstore.csv`
   *(or skip this and just upload the CSV in the app's sidebar instead)*
6. Run the app: `streamlit run app.py`
7. Ask a question like *"What were total sales by region?"* or
   *"Which category had the lowest profit?"*, review the generated SQL,
   click **Run query**, then **Generate AI Insight**.


## Datasets Query Results
<img width="1912" height="918" alt="image" src="https://github.com/user-attachments/assets/56c59cce-046d-403c-8cca-939c901bbe4f" />
<img width="1917" height="915" alt="image" src="https://github.com/user-attachments/assets/aba03b15-9917-440c-84b9-195c47cc52e8" />
<img width="1917" height="920" alt="image" src="https://github.com/user-attachments/assets/e7f03ae7-f19d-460b-a4d3-94e3e568ba12" />
