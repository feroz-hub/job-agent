"""Personal YAML persistence; example configuration is never overwritten."""
from dataclasses import asdict
from pathlib import Path
import yaml
from .models import CandidateProfile

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "profile.yaml"


def load_profile(path: str | Path = PROFILE_PATH) -> CandidateProfile:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError("Invalid profile YAML") from exc
    if not isinstance(data, dict):
        raise ValueError("Profile YAML must contain a mapping")
    try:
        return CandidateProfile(**data)
    except TypeError as exc:
        raise ValueError("Profile fields are missing or unsupported") from exc


def save_profile(profile: CandidateProfile, path: str | Path = PROFILE_PATH) -> None:
    path = Path(path)
    if path.resolve() == (ROOT / "config/profile.example.yaml").resolve() or path.name.endswith(".example.yaml"):
        raise ValueError("Save personal data to profile.yaml, not the example")
    CandidateProfile(**asdict(profile))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(asdict(profile), sort_keys=False, allow_unicode=True), encoding="utf-8")
