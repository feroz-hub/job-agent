"""Readable scored-job details."""
import streamlit as st
from src.workflow import list_items
from src.job_processing.normalizer import clean_text, url_key


def render_job_card(row: dict) -> None:
    with st.container(border=True):
        st.subheader(clean_text(row.get("title")))
        st.caption(clean_text(row.get("company")))
        st.write(f"Match Score: {row.get('match_score', 0)}% · {clean_text(row.get('recommendation')).replace('_', ' ').upper()}")
        st.caption(f"Confidence: {clean_text(row.get('match_confidence'))}")
        for column, field in zip(st.columns(4), ("role_match_score", "skills_match_score", "experience_match_score", "location_match_score")):
            column.metric(field.replace("_match_score", "").title(), row.get(field, 0))
        with st.expander("Evidence, gaps and suggestions"):
            for field, label in (("matched_skills", "Matched Skills"), ("missing_required_skills", "Missing Required"),
                                 ("nice_to_have_gaps", "Nice-to-have Gaps"), ("candidate_strengths", "Strengths"),
                                 ("risks", "Risks"), ("resume_tailoring_suggestions", "Resume Suggestions")):
                st.markdown(f"**{label}**")
                items = list_items(row.get(field))
                for item in items:
                    st.text(f"• {item}")
                if not items:
                    st.caption("None reported")
            st.markdown("**Why this matches**")
            st.text(clean_text(row.get("reasoning_summary")))
        url = clean_text(row.get("job_url"))
        if url_key(url):
            st.link_button("Open Job", url)
