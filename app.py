import os
import tempfile

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from load_data import load_csv_to_sqlite
from query_engine import generate_sql, run_sql, get_schema
from insights import generate_insight

DB_PATH = "business.db"
TABLE = "data"

st.set_page_config(page_title="AI Business Analyst Assistant", page_icon="📊", layout="wide")

# ---------- Session state ----------
defaults = {
    "history": [],           # list of {"question": ..., "sql": ...}
    "current_sql": "",
    "current_question": "",
    "result_df": None,
    "insight": None,
    "db_ready": os.path.exists(DB_PATH),
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- Sidebar: dataset upload + history ----------
with st.sidebar:
    st.header("Dataset")
    uploaded_file = st.file_uploader("Upload a CSV", type=["csv"])
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        try:
            load_csv_to_sqlite(tmp_path, db_path=DB_PATH, table=TABLE)
            st.session_state.db_ready = True
            st.session_state.result_df = None
            st.session_state.insight = None
            st.success("Dataset loaded.")
        except Exception as e:
            st.error(f"Couldn't load file: {e}")
        finally:
            os.remove(tmp_path)

    st.divider()
    st.header("History")
    if st.session_state.history:
        for i, item in enumerate(reversed(st.session_state.history)):
            if st.button(item["question"], key=f"hist_{i}", use_container_width=True):
                st.session_state.current_question = item["question"]
                st.session_state.current_sql = item["sql"]
                st.session_state.result_df = None
                st.session_state.insight = None
    else:
        st.caption("No questions asked yet.")

# ---------- Main ----------
st.title("AI Business Analyst Assistant")
st.caption("Ask a plain-English business question about your data.")

if not st.session_state.db_ready:
    st.info("Upload a CSV in the sidebar to get started, or run `python load_data.py yourfile.csv` first.")
    st.stop()

# Dataset overview
with st.expander("Dataset overview", expanded=False):
    schema = get_schema(DB_PATH, TABLE)
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Columns**")
        st.table(pd.DataFrame(schema, columns=["Column", "Type"]))
    with col2:
        row_count = run_sql(f"SELECT COUNT(*) AS n FROM {TABLE}", DB_PATH)["n"][0]
        st.metric("Total rows", f"{row_count:,}")
        st.write("**Sample rows**")
        st.dataframe(run_sql(f"SELECT * FROM {TABLE} LIMIT 5", DB_PATH), use_container_width=True)

# Question input
question = st.text_input(
    "Ask a question",
    value=st.session_state.current_question,
    placeholder="Why did revenue drop in March?",
)

if st.button("Generate SQL") and question:
    with st.spinner("Generating SQL..."):
        try:
            st.session_state.current_sql = generate_sql(question, DB_PATH, TABLE)
            st.session_state.current_question = question
            st.session_state.result_df = None
            st.session_state.insight = None
        except Exception as e:
            st.error(f"Couldn't generate a query: {e}")

# Editable SQL + run
if st.session_state.current_sql:
    st.subheader("Generated SQL")
    st.caption("Review or edit before running \u2014 the AI's query isn't executed blindly.")
    edited_sql = st.text_area("SQL", value=st.session_state.current_sql, height=100, label_visibility="collapsed")
    st.session_state.current_sql = edited_sql

    if st.button("Run query"):
        with st.spinner("Running query..."):
            try:
                st.session_state.result_df = run_sql(edited_sql, DB_PATH)
                st.session_state.insight = None
                st.session_state.history.append({
                    "question": st.session_state.current_question,
                    "sql": edited_sql,
                })
            except Exception as e:
                st.error(f"Query failed: {e}")

# Results, chart, export
if st.session_state.result_df is not None:
    result_df = st.session_state.result_df

    st.subheader("Result")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        "Download result as CSV",
        result_df.to_csv(index=False).encode("utf-8"),
        "result.csv",
        "text/csv",
    )

    if result_df.shape[1] == 2 and len(result_df) > 1:
        col_x, col_y = result_df.columns
        if pd.api.types.is_numeric_dtype(result_df[col_y]):
            is_date_like = False
            try:
                pd.to_datetime(result_df[col_x])
                is_date_like = True
            except Exception:
                pass

            fig, ax = plt.subplots()
            if is_date_like:
                sorted_df = result_df.sort_values(col_x)
                ax.plot(pd.to_datetime(sorted_df[col_x]), sorted_df[col_y], marker="o")
            else:
                ax.bar(result_df[col_x].astype(str), result_df[col_y])
                plt.xticks(rotation=45, ha="right")
            ax.set_xlabel(col_x)
            ax.set_ylabel(col_y)
            st.pyplot(fig)

    if st.button("Generate AI Insight"):
        with st.spinner("Generating insight... (retrying automatically if the model is busy)"):
            try:
                st.session_state.insight = generate_insight(
                    st.session_state.current_question, st.session_state.current_sql, result_df
                )
            except Exception as e:
                st.warning(f"Insight generation failed: {e}")

if st.session_state.insight:
    st.subheader("AI Insight")
    st.write(st.session_state.insight.replace("$", "\\$"))
