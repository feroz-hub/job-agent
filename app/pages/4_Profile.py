from components.sidebar import setup, show_error, ROOT
setup("Profile")
from dataclasses import asdict
import streamlit as st
from src.job_matching.profile import load_profile, save_profile, PROFILE_PATH
from src.job_matching.models import CandidateProfile, PROFILE_LISTS

values = {}
try:
    if PROFILE_PATH.exists():
        values = asdict(load_profile())
except Exception as exc:
    show_error(exc)
st.caption("Enter only your actual skills and experience. This personal file is ignored by Git.")
with st.form("profile"):
    data = {}
    for field in ("name", "current_role", "current_location"):
        data[field] = st.text_input(field.replace("_", " ").title(), values.get(field, ""))
    data["years_of_experience"] = st.number_input("Years of experience", min_value=0.0, value=float(values.get("years_of_experience", 0)), step=0.5)
    for field in PROFILE_LISTS:
        text = st.text_area(field.replace("_", " ").title() + " (one per line)", "\n".join(values.get(field, [])))
        data[field] = [line.strip() for line in text.splitlines() if line.strip()]
    for field in ("work_experience_summary", "education", "notice_period", "current_ctc", "expected_ctc"):
        data[field] = st.text_area(field.replace("_", " ").title(), values.get(field, ""))
    data["willing_to_relocate"] = st.checkbox("Willing to relocate", values.get("willing_to_relocate", False))
    submitted = st.form_submit_button("Save Profile")
if submitted:
    try:
        save_profile(CandidateProfile(**data))
        (ROOT / "data/scored_jobs.csv").unlink(missing_ok=True)
        st.success("Saved personal profile.yaml. Reprocess jobs if experience or preferred locations changed.")
    except Exception as exc:
        show_error(exc)
