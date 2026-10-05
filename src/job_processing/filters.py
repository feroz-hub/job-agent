"""Title/location rules and conservative, isolated experience parsing."""
import re

from .models import FilterConfig
from .normalizer import clean_text

YEARS = r"(?:years?|yrs?)"


def contains_keyword(text: str, keyword: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(keyword.casefold()) + r"(?!\w)", text.casefold()))


def parse_experience(value) -> tuple[float, float | None] | None:
    """Parse an entire experience field; ambiguous or contradictory text is unknown."""
    text = clean_text(value).casefold().replace("–", "-").replace("—", "-")
    match = re.fullmatch(rf"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*{YEARS}", text)
    if match:
        low, high = map(float, match.groups())
        return (low, high) if low <= high else None
    match = re.fullmatch(rf"(?:minimum\s+|at least\s+)?(\d+(?:\.\d+)?)\s*(\+)?\s*{YEARS}(?:\s+(?:of\s+)?experience)?", text)
    if match:
        # A single stated number is treated as a minimum requirement.
        return float(match.group(1)), None
    return None


def experience_for_job(row) -> tuple[float, float | None] | None:
    structured = clean_text(row.get("experience_range"))
    if structured:
        return parse_experience(structured)
    # Only explicitly labelled overall experience in descriptions; arbitrary skill
    # tenure ranges could refer to a small part of the role and must not reject it.
    matches = re.findall(
        r"(?:^|[.;\n])\s*(?:required experience|experience required|experience)\s*:\s*([^.;\n]+)",
        row.get("description", ""), flags=re.I,
    )
    parsed = [parse_experience(value) for value in matches]
    return parsed[0] if len(parsed) == 1 else None


def rejection_reason(row, config: FilterConfig) -> str:
    title = row["_normalized_title"]
    if any(contains_keyword(title, word) for word in config.excluded_title_keywords):
        return "rejected_unrelated_title"
    if not any(contains_keyword(title, word) for word in config.target_keywords):
        return "rejected_unrelated_title"
    location = row["_normalized_location"]
    remote = clean_text(row.get("is_remote")).casefold() in ("true", "1", "1.0")
    matches_location = any(contains_keyword(location, place) for place in config.preferred_locations)
    matches_remote = remote and any(place.casefold() == "remote" for place in config.preferred_locations)
    if location and not matches_location and not matches_remote:
        return "rejected_location"
    experience = experience_for_job(row)
    if experience is not None:
        low, high = experience
        years = config.candidate_experience_years
        if years < low or (high is not None and years > high):
            return "rejected_experience"
    return "accepted"
