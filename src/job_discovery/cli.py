"""Run with python -m src.job_discovery.cli."""

import logging

from .models import JobSearchConfig
from .service import discover_jobs, save_jobs_csv

DISPLAY_COLUMNS = ("site", "title", "company", "location", "date_posted", "job_url")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config = JobSearchConfig()
    print(
        f"Search term: {config.search_term}\nLocation: {config.location}\n"
        f"Portals: {', '.join(config.sites)}\nResults wanted: {config.results_wanted}\n"
        f"Posted within: {config.hours_old} hours (7 days)",
        flush=True,
    )
    try:
        jobs = discover_jobs(config)
        print(f"Jobs found: {len(jobs)}", flush=True)
        if jobs.empty:
            print("No jobs returned. Check the logs for possible portal/network errors.")
        else:
            columns = [column for column in DISPLAY_COLUMNS if column in jobs.columns]
            if columns:
                print(jobs[columns].to_string(index=False))
            else:
                print("No standard display columns available in the response.")
        save_jobs_csv(jobs)
    except Exception:
        logging.getLogger(__name__).exception("Job discovery or CSV export failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
