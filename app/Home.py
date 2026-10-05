from components.sidebar import setup, show_error, ROOT
setup("JOB AGENT")

import streamlit as st
from components.metrics import render_metrics
from src.workflow import dashboard_metrics, read_jobs

st.caption("AI-assisted job discovery and matching")
try:
    render_metrics(dashboard_metrics(ROOT))
    st.subheader("Recent top matches")
    scored = read_jobs(ROOT / "data/scored_jobs.csv")
    if scored.empty:
        st.info("No scored jobs yet. Complete the setup and run AI Matching.")
    else:
        columns = [name for name in ("title", "company", "match_score", "recommendation") if name in scored]
        st.dataframe(scored[columns].head(5), hide_index=True, width="stretch")
except Exception as exc:
    show_error(exc)
st.subheader("Your workflow")
st.markdown("1. Configure your profile\n2. Upload or select a PDF/TXT resume\n3. Discover jobs\n4. Filter jobs\n5. Score relevant jobs with Gemini")
st.caption("Scoring sends your profile, resume text and selected job details to Gemini. Discovery and filtering do not call AI.")
