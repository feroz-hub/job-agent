from components.sidebar import setup, show_error, ROOT
setup("AI Matches")
import os
import streamlit as st
from components.job_card import render_job_card
from src.job_matching.profile import load_profile, PROFILE_PATH
from src.job_matching.resume import load_resume
from src.job_matching.gemini_provider import GeminiProvider
from src.job_matching.service import JobMatchService
from src.job_matching.pipeline import score_jobs
from src.workflow import read_jobs, save_jobs

resumes = sorted((ROOT / "resume").glob("*")) if (ROOT / "resume").exists() else []
resumes = [path for path in resumes if path.is_file() and path.suffix.lower() in (".pdf", ".txt")]
missing = []
if not PROFILE_PATH.is_file():
    missing.append("Save profile.yaml on the Profile page.")
if not resumes:
    missing.append("Upload a PDF/TXT resume on Settings.")
if not os.getenv("GEMINI_API_KEY", "").strip():
    missing.append("Set GEMINI_API_KEY in .env and restart Streamlit.")
if not os.getenv("GEMINI_MODEL", "").strip():
    missing.append("Set GEMINI_MODEL in .env and restart Streamlit.")
if not (ROOT / "data/filtered_jobs.csv").is_file():
    missing.append("Discover and process jobs to create data/filtered_jobs.csv.")
for message in missing:
    st.warning(message)
resume_path = st.selectbox("Resume", resumes, format_func=lambda path: path.name) if resumes else None
limit = st.number_input("Number of jobs to score", 1, 10, 3)
st.info("Run AI Matching triggers paid/quota-limited API calls and sends your profile, selected resume text and job details to Gemini. Up to 3 attempts per selected job.")
if st.button("Run AI Matching", disabled=bool(missing)):
    provider = None
    try:
        profile = load_profile()
        resume = load_resume(resume_path)
        jobs = read_jobs(ROOT / "data/filtered_jobs.csv")
        if jobs.empty:
            st.info("There are no filtered jobs to score.")
        else:
            provider = GeminiProvider()
            progress = st.progress(0)
            status = st.empty()
            def update(current: int, total: int) -> None:
                status.write(f"Scoring {current} of {total}…")
                progress.progress((current - 1) / total)
            result = score_jobs(jobs, profile, resume, JobMatchService(provider), int(limit), update)
            progress.progress(1.0)
            status.write("Matching finished")
            for failure in result.failures:
                st.warning(f"Job {failure['position']} could not be scored: {failure['error']}")
            save_jobs(result.scored, ROOT / "data/scored_jobs.csv")
            st.success(f"Saved {len(result.scored)} scored jobs")
    except Exception as exc:
        show_error(exc)
    finally:
        if provider:
            provider.close()
try:
    scored = read_jobs(ROOT / "data/scored_jobs.csv")
    if scored.empty:
        st.info("No AI matches available yet.")
    else:
        for row in scored.sort_values("match_score", ascending=False).to_dict("records"):
            render_job_card(row)
except Exception as exc:
    show_error(exc)
