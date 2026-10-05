"""Normalize, deduplicate, and explain every processing decision."""
import pandas as pd

from .deduplicator import duplicate_mask
from .filters import rejection_reason
from .models import FilterConfig, ProcessingResult
from .normalizer import normalize_jobs

REASONS = ("duplicate", "rejected_unrelated_title", "rejected_location", "rejected_experience", "accepted")


def process_jobs(raw: pd.DataFrame, config: FilterConfig | None = None) -> ProcessingResult:
    config = config if config is not None else FilterConfig()
    jobs = normalize_jobs(raw)
    duplicates = duplicate_mask(jobs)
    reasons = ["duplicate" if duplicates.loc[index] else rejection_reason(row, config)
               for index, row in jobs.iterrows()]
    # Internal matching columns never leak into the exported job schema.
    public = jobs.drop(columns=[name for name in jobs if name.startswith("_normalized_") or name == "_url_key"])
    decisions = public.copy()
    decisions["processing_reason"] = pd.Series(reasons, index=jobs.index, dtype=str)
    counts = {"raw": len(raw), **{reason: reasons.count(reason) for reason in REASONS}}
    accepted = public.loc[decisions["processing_reason"] == "accepted"].reset_index(drop=True)
    return ProcessingResult(accepted, decisions, counts)
