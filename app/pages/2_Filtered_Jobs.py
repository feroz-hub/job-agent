from components.sidebar import setup, show_error, ROOT
setup("Filtered Jobs")
import streamlit as st
from src.workflow import read_jobs, filter_preview

try:
    jobs = read_jobs(ROOT / "data/filtered_jobs.csv")
    if jobs.empty:
        st.info("No accepted jobs available. Discover and process jobs first.")
    else:
        left, middle, right = st.columns(3)
        keyword = left.text_input("Keyword")
        company = middle.text_input("Company")
        location = right.text_input("Location")
        jobs = filter_preview(jobs, keyword, company, location)
        columns = [name for name in ("title", "company", "location", "experience_range", "date_posted", "job_url") if name in jobs]
        st.dataframe(jobs[columns], hide_index=True, width="stretch")
except Exception as exc:
    show_error(exc)
st.page_link("pages/3_AI_Matches.py", label="Score Jobs with AI → AI Matches")
