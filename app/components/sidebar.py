"""Common page setup and local configuration."""
import sys
from pathlib import Path
import logging

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv


def setup(title: str) -> None:
    load_dotenv(ROOT / ".env", override=False)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    st.set_page_config(page_title=f"{title} · Job Agent", page_icon="💼", layout="wide")
    st.sidebar.title("Job Agent")
    st.sidebar.caption("AI-assisted job discovery and matching")
    st.sidebar.info("Configure profile → Add resume → Discover → Filter → Score")
    st.title(title)


def show_error(exc: Exception) -> None:
    # Provider adapter sanitizes its errors. Never show an SDK traceback or secret.
    logging.getLogger(__name__).warning("UI operation failed: %s", type(exc).__name__)
    if isinstance(exc, (ValueError, FileNotFoundError)):
        st.error(str(exc))
    else:
        st.error("Operation failed. Check your input, connectivity and provider configuration, then retry.")
