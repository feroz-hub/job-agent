"""Processing configuration and explainable results."""
from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class FilterConfig:
    target_keywords: tuple[str, ...] = (
        ".net", "dotnet", "dot net", "c#", "asp.net", "asp.net core",
        "backend developer", "software engineer", "software developer",
        "full stack", "full-stack", "fullstack", "web api",
    )
    excluded_title_keywords: tuple[str, ...] = (
        "java", "php", "android", "ios", "sap", "mainframe", "sales",
        "marketing", "recruiter", "data entry",
    )
    preferred_locations: tuple[str, ...] = ("Chennai", "Remote")
    candidate_experience_years: float = 4


@dataclass
class ProcessingResult:
    accepted: pd.DataFrame
    decisions: pd.DataFrame
    counts: dict[str, int] = field(default_factory=dict)
