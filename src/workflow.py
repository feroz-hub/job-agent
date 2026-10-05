"""Filesystem workflow helpers shared by presentation and automation."""
from pathlib import Path
import json
import pandas as pd
from .job_processing.models import FilterConfig
from .job_processing.pipeline import process_jobs
from .job_matching.models import CandidateProfile

ROOT = Path(__file__).resolve().parents[1]


def read_jobs(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def save_jobs(jobs: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs.to_csv(path, index=False)


def process_saved_jobs(profile: CandidateProfile | None = None, root: Path = ROOT):
    source = root / "data/jobs.csv"
    if not source.is_file():
        raise FileNotFoundError("Discover jobs first: data/jobs.csv is missing")
    config = FilterConfig() if profile is None else FilterConfig(
        preferred_locations=tuple(profile.preferred_locations),
        candidate_experience_years=profile.years_of_experience)
    result = process_jobs(read_jobs(source), config)
    save_jobs(result.accepted, root / "data/filtered_jobs.csv")
    # Changed upstream jobs invalidate scored output; never show stale matches.
    (root / "data/scored_jobs.csv").unlink(missing_ok=True)
    return result


def dashboard_metrics(root: Path = ROOT) -> dict[str, int]:
    raw = read_jobs(root / "data/jobs.csv")
    filtered = read_jobs(root / "data/filtered_jobs.csv")
    scored = read_jobs(root / "data/scored_jobs.csv")
    recommendations = scored.get("recommendation", pd.Series(dtype=str))
    return {"Raw Jobs": len(raw), "Filtered Jobs": len(filtered),
            "Strong Matches": int((recommendations == "strong_apply").sum()),
            "Apply": int((recommendations == "apply").sum()),
            "Review": int((recommendations == "review").sum())}


def list_items(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
    except ValueError:
        return []
    return parsed if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed) else []


def filter_preview(jobs: pd.DataFrame, keyword: str = "", company: str = "", location: str = "") -> pd.DataFrame:
    result = jobs.copy()
    for column, value in (("company", company), ("location", location)):
        if value and column in result:
            result = result[result[column].fillna("").str.contains(value, case=False, regex=False)]
    if keyword:
        mask = pd.Series(False, index=result.index)
        for column in ("title", "company", "description"):
            if column in result:
                mask |= result[column].fillna("").str.contains(keyword, case=False, regex=False)
        result = result[mask]
    return result
