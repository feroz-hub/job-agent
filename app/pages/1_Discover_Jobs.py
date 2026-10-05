from components.sidebar import setup, show_error, ROOT
setup("Discover Jobs")

import streamlit as st
from components.metrics import render_metrics
from src.job_discovery.models import JobSearchConfig
from src.job_discovery.service import discover_jobs, save_jobs_csv
from src.job_matching.profile import load_profile, PROFILE_PATH
from src.workflow import read_jobs, process_saved_jobs

with st.form("discovery"):
    term = st.text_input("Search term", ".NET Developer")
    location = st.text_input("Location", "Chennai")
    sites = st.multiselect("Job portals", ["naukri", "indeed", "linkedin", "glassdoor", "zip_recruiter", "google", "bdjobs"], default=["naukri"])
    count = st.number_input("Results wanted", 1, 100, 10)
    days = st.number_input("Days old", 1, 30, 7)
    submitted = st.form_submit_button("Discover Jobs")
if submitted:
    if not term.strip() or not location.strip() or not sites:
        st.error("Enter a search term, location and at least one portal.")
    else:
        try:
            with st.spinner("Discovering jobs…"):
                jobs = discover_jobs(JobSearchConfig(term.strip(), location.strip(), tuple(sites), int(count), int(days) * 24))
                save_jobs_csv(jobs)
                for filename in ("filtered_jobs.csv", "scored_jobs.csv"):
                    (ROOT / "data" / filename).unlink(missing_ok=True)
            st.success(f"Found {len(jobs)} jobs")
            if jobs.empty:
                st.warning("No jobs returned. Portal/network failures may also produce an empty result; check logs.")
        except Exception as exc:
            show_error(exc)
if st.button("Process / Filter Jobs"):
    try:
        profile = load_profile() if PROFILE_PATH.exists() else None
        with st.spinner("Processing jobs…"):
            result = process_saved_jobs(profile)
        labels = {"raw": "Raw", "duplicate": "Duplicates",
                  "rejected_unrelated_title": "Title Rejected", "rejected_location": "Location Rejected",
                  "rejected_experience": "Experience Rejected", "accepted": "Accepted"}
        render_metrics({labels[key]: value for key, value in result.counts.items()})
        st.dataframe(result.accepted, hide_index=True, width="stretch")
        st.success("Saved data/filtered_jobs.csv")
    except Exception as exc:
        show_error(exc)
try:
    jobs = read_jobs(ROOT / "data/jobs.csv")
    if jobs.empty:
        st.info("No raw jobs available. Run discovery above.")
    else:
        st.subheader("Raw jobs")
        st.dataframe(jobs, hide_index=True, width="stretch")
except Exception as exc:
    show_error(exc)
