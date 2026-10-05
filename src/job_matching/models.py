"""Profile and strict response validation."""
from dataclasses import dataclass, field
import json
import math


@dataclass
class CandidateProfile:
    name: str
    current_role: str
    years_of_experience: float
    current_location: str = ""
    preferred_locations: list[str] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)
    primary_skills: list[str] = field(default_factory=list)
    secondary_skills: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    cloud_tools: list[str] = field(default_factory=list)
    ai_skills: list[str] = field(default_factory=list)
    work_experience_summary: str = ""
    projects: list[str] = field(default_factory=list)
    education: str = ""
    notice_period: str = ""
    current_ctc: str = ""
    expected_ctc: str = ""
    willing_to_relocate: bool = False

    def __post_init__(self) -> None:
        for name in ("name", "current_role"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"Profile {name} is required")
        years = self.years_of_experience
        if type(years) not in (int, float) or not math.isfinite(years) or years < 0:
            raise ValueError("Profile years_of_experience must be a nonnegative number")
        for name, value in vars(self).items():
            if name == "years_of_experience":
                continue
            if name == "willing_to_relocate":
                if type(value) is not bool:
                    raise ValueError(f"Profile {name} must be boolean")
            elif name in PROFILE_LISTS:
                if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                    raise ValueError(f"Profile {name} must be a list of strings")
            elif not isinstance(value, str):
                raise ValueError(f"Profile {name} must be text")


PROFILE_LISTS = ("preferred_locations", "target_roles", "primary_skills", "secondary_skills",
                 "frameworks", "databases", "cloud_tools", "ai_skills", "projects")
SCORE_FIELDS = ("overall_score", "role_match_score", "skills_match_score",
                "experience_match_score", "location_match_score")
LIST_FIELDS = ("matched_skills", "missing_required_skills", "nice_to_have_gaps",
               "candidate_strengths", "risks", "resume_tailoring_suggestions")
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        **{name: {"type": "integer", "minimum": 0, "maximum": 100} for name in SCORE_FIELDS},
        **{name: {"type": "array", "items": {"type": "string"}} for name in LIST_FIELDS},
        "reasoning_summary": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [*SCORE_FIELDS, *LIST_FIELDS, "reasoning_summary", "confidence"],
    "additionalProperties": False,
}


class InvalidAIResponse(ValueError):
    """Untrusted provider output did not satisfy the contract."""


def validate_score(score: int) -> None:
    if type(score) is not int or not 0 <= score <= 100:
        raise InvalidAIResponse("Scores must be integers from 0 to 100")


def recommendation_for_score(score: int) -> str:
    validate_score(score)
    return "strong_apply" if score >= 85 else "apply" if score >= 70 else "review" if score >= 55 else "skip"


def parse_match_response(text: str) -> dict:
    try:
        result = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise InvalidAIResponse("Provider returned invalid JSON") from exc
    if not isinstance(result, dict) or set(result) != set(RESPONSE_SCHEMA["required"]):
        raise InvalidAIResponse("Response fields do not match the scoring schema")
    for name in SCORE_FIELDS:
        validate_score(result[name])
    for name in LIST_FIELDS:
        if not isinstance(result[name], list) or any(not isinstance(item, str) for item in result[name]):
            raise InvalidAIResponse(f"{name} must be an array of strings")
    if not isinstance(result["reasoning_summary"], str) or not result["reasoning_summary"].strip():
        raise InvalidAIResponse("reasoning_summary must be nonempty text")
    if result["confidence"] not in ("high", "medium", "low"):
        raise InvalidAIResponse("Invalid confidence")
    return result
