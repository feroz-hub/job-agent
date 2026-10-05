"""Configuration for a job search."""

from dataclasses import dataclass


@dataclass(frozen=True)
class JobSearchConfig:
    """Search criteria passed to the discovery service."""

    search_term: str = ".NET Developer"
    location: str = "Chennai"
    sites: tuple[str, ...] = ("naukri",)
    results_wanted: int = 10
    hours_old: int = 168
