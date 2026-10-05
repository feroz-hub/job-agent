"""Bounded scoring, stable ranking and explainable per-job failures."""
from dataclasses import dataclass
from collections.abc import Callable
import json
import logging
import pandas as pd
from .models import CandidateProfile, LIST_FIELDS
from .provider import ProviderError
from .models import InvalidAIResponse
from .service import JobMatchService

logger = logging.getLogger(__name__)
OUTPUT_FIELDS = ("match_score", "recommendation", "role_match_score", "skills_match_score",
                 "experience_match_score", "location_match_score", *LIST_FIELDS,
                 "reasoning_summary", "match_confidence")


@dataclass
class ScoringResult:
    scored: pd.DataFrame
    failures: list[dict]


def score_jobs(jobs: pd.DataFrame, profile: CandidateProfile, resume: str,
               service: JobMatchService, limit: int = 3,
               progress: Callable[[int, int], None] | None = None) -> ScoringResult:
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Scoring limit must be between 1 and 10")
    if not resume.strip():
        raise ValueError("Resume text is required")
    rows, failures = [], []
    selected = jobs.head(limit)
    for position, (_, row) in enumerate(selected.iterrows(), 1):
        if progress:
            progress(position, len(selected))
        try:
            match = service.match(profile, resume, row.to_dict())
        except (ProviderError, InvalidAIResponse) as exc:
            logger.warning("Job %s could not be scored: %s", position, type(exc).__name__)
            failures.append({"position": position, "title": str(row.get("title", "")),
                             "error": str(exc)})
            continue
        match["match_score"] = match.pop("overall_score")
        match["match_confidence"] = match.pop("confidence")
        for name in LIST_FIELDS:
            match[name] = json.dumps(match[name], ensure_ascii=False)
        rows.append({**row.to_dict(), **match})
    columns = list(dict.fromkeys([*jobs.columns, *OUTPUT_FIELDS]))
    scored = pd.DataFrame(rows, columns=columns).sort_values("match_score", ascending=False, kind="stable").reset_index(drop=True)
    return ScoringResult(scored, failures)
