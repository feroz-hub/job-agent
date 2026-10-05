"""Stable first-occurrence deduplication of normalized jobs."""
import pandas as pd


def duplicate_mask(jobs: pd.DataFrame) -> pd.Series:
    seen = set()
    duplicates = []
    for _, row in jobs.iterrows():
        url = row["_url_key"]
        composite = tuple(row[f"_normalized_{name}"] for name in ("title", "company", "location"))
        # Incomplete fallback identity cannot confidently establish duplication.
        key = ("url", url) if url else (("fields", *composite) if all(composite) else None)
        duplicates.append(key is not None and key in seen)
        if key is not None:
            seen.add(key)
    return pd.Series(duplicates, index=jobs.index, dtype=bool)
