"""JobSpy integration and CSV export."""

import logging
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

from .models import JobSearchConfig

logger = logging.getLogger(__name__)
DEFAULT_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "jobs.csv"


def discover_jobs(config: JobSearchConfig) -> pd.DataFrame:
    """Search JobSpy; log and propagate any raised exception."""
    logger.info(
        "Starting job search: portals=%s search_term=%s location=%s "
        "results_wanted=%s hours_old=%s",
        config.sites, config.search_term, config.location,
        config.results_wanted, config.hours_old,
    )
    try:
        jobs = scrape_jobs(
            site_name=list(config.sites),
            search_term=config.search_term,
            location=config.location,
            results_wanted=config.results_wanted,
            hours_old=config.hours_old,
            verbose=2,
        )
    except Exception:
        logger.exception("Search failure")
        raise
    logger.info("Number of jobs returned: %s", len(jobs))
    return jobs


def save_jobs_csv(jobs: pd.DataFrame, path: Path = DEFAULT_CSV_PATH) -> None:
    """Export the returned results, including headers for an empty result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs.to_csv(path, index=False)
    logger.info("CSV saved: %s", path)
