from components.sidebar import setup, show_error, ROOT
setup("Resume / Settings")
import os
import streamlit as st
from src.job_matching.resume import load_resume, save_resume_upload

st.subheader("Gemini configuration")
st.write("Gemini API Key: Configured ✅" if os.getenv("GEMINI_API_KEY", "").strip() else "Gemini API Key: Missing ❌")
st.text("Gemini model: " + (os.getenv("GEMINI_MODEL", "").strip() or "Not configured"))
st.caption("Set GEMINI_API_KEY and GEMINI_MODEL in .env, then restart Streamlit. Keys are never displayed.")
st.subheader("Resume")
upload = st.file_uploader("Upload PDF or TXT (maximum 10 MB)", type=["pdf", "txt"], max_upload_size=10)
if st.button("Save Resume", disabled=upload is None):
    try:
        path = save_resume_upload(upload.getvalue(), upload.name, ROOT / "resume")
        (ROOT / "data/scored_jobs.csv").unlink(missing_ok=True)
        st.success(f"Resume loaded: {path.name}")
    except Exception as exc:
        show_error(exc)
paths = sorted((ROOT / "resume").glob("*")) if (ROOT / "resume").exists() else []
paths = [path for path in paths if path.is_file() and path.suffix.lower() in (".pdf", ".txt")]
if paths:
    selected = st.selectbox("Saved resume", paths, format_func=lambda path: path.name)
    try:
        text = load_resume(selected)
        st.success(f"Resume loaded: {selected.name}")
        with st.expander("Extracted text preview"):
            st.text(text[:3000])
    except Exception as exc:
        show_error(exc)
else:
    st.info("Upload a resume or place a PDF/TXT file under resume/.")
