"""Clean display values and retain separate case-insensitive matching values."""
import re
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

TEXT_FIELDS = ("title", "company", "location", "description", "job_url")


def clean_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def url_key(value) -> str:
    """Use only HTTP(S) URLs; preserve path/query identity and remove fragments."""
    value = clean_text(value)
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            return ""
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                           parts.query, ""))
    except ValueError:
        return ""


def normalize_jobs(raw: pd.DataFrame) -> pd.DataFrame:
    jobs = raw.copy().reset_index(drop=True)
    for column in TEXT_FIELDS:
        if column not in jobs:
            jobs[column] = ""
        jobs[column] = jobs[column].map(clean_text)
        jobs[f"_normalized_{column}"] = jobs[column].str.casefold()
    jobs["_url_key"] = jobs["job_url"].map(url_key)
    return jobs
