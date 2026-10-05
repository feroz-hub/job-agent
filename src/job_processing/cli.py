"""Offline CSV processing: python -m src.job_processing.cli."""
import logging
from pathlib import Path

import pandas as pd

from .pipeline import process_jobs

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        source = ROOT / "data" / "jobs.csv"
        try:
            raw = pd.read_csv(source)
        except pd.errors.EmptyDataError:
            raw = pd.DataFrame()
        result = process_jobs(raw)
        labels = {"raw": "Raw jobs", "duplicate": "Duplicates removed",
                  "rejected_unrelated_title": "Title rejected", "rejected_location": "Location rejected",
                  "rejected_experience": "Experience rejected", "accepted": "Accepted jobs"}
        for key, label in labels.items():
            print(f"{label + ':':24} {result.counts[key]}")
        columns = [name for name in ("title", "company", "location", "experience_range", "job_url") if name in result.accepted]
        if result.accepted.empty:
            print("No accepted jobs.")
        else:
            print(result.accepted[columns].head(10).to_string(index=False))
        destination = ROOT / "data" / "filtered_jobs.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        result.accepted.to_csv(destination, index=False)
        logging.getLogger(__name__).info("CSV saved: %s", destination)
    except Exception:
        logging.getLogger(__name__).exception("Job processing failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
