"""Provider calls, response validation, retries and deterministic decisions."""
import logging
import time
from collections.abc import Callable
from src.job_processing.normalizer import clean_text
from .models import CandidateProfile, InvalidAIResponse, parse_match_response, recommendation_for_score
from .prompt_builder import build_prompt
from .provider import AIProvider, TransientProviderError

logger = logging.getLogger(__name__)


class JobMatchService:
    def __init__(self, provider: AIProvider, sleep: Callable[[float], None] = time.sleep,
                 max_attempts: int = 3):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3")
        self.provider, self.sleep, self.max_attempts = provider, sleep, max_attempts

    def match(self, profile: CandidateProfile, resume: str, job: dict) -> dict:
        if not resume.strip():
            raise ValueError("Resume text is required")
        prompt = build_prompt(profile, resume, job)
        for attempt in range(self.max_attempts):
            try:
                result = parse_match_response(self.provider.generate(prompt))
                if not clean_text(job.get("description")):
                    result["confidence"] = "low"
                    result["risks"].append("Insufficient evidence: job description is missing.")
                    result["reasoning_summary"] += " Limited assessment: no job description available."
                result["recommendation"] = recommendation_for_score(result["overall_score"])
                return result
            except (TransientProviderError, InvalidAIResponse) as exc:
                logger.warning("Matching attempt %s failed: %s", attempt + 1, type(exc).__name__)
                if attempt + 1 == self.max_attempts:
                    raise
                self.sleep(0.5 * 2 ** attempt)
        raise RuntimeError("Matching did not complete")
