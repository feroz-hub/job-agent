"""Offline AI contract and workflow tests; fake providers never contact Gemini."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from pypdf import PdfWriter

from src.job_matching.models import (CandidateProfile, RESPONSE_SCHEMA, InvalidAIResponse,
                                      parse_match_response, recommendation_for_score)
from src.job_matching.profile import load_profile, save_profile, PROFILE_PATH
from src.job_matching.resume import load_resume, save_resume_upload
from src.job_matching.prompt_builder import build_prompt
from src.job_matching.gemini_provider import GeminiProvider
from src.job_matching.provider import ProviderError, TransientProviderError
from src.job_matching.service import JobMatchService
from src.job_matching.pipeline import score_jobs
from src.workflow import dashboard_metrics, filter_preview, list_items, process_saved_jobs, read_jobs, save_jobs


def example_response(score=90):
    return {"overall_score": score, "role_match_score": 80, "skills_match_score": 80,
            "experience_match_score": 80, "location_match_score": 100,
            "matched_skills": ["C#"], "missing_required_skills": [], "nice_to_have_gaps": [],
            "candidate_strengths": ["Relevant skills"], "risks": [],
            "reasoning_summary": "Evidence supports this role.",
            "resume_tailoring_suggestions": ["Surface existing API experience"], "confidence": "high"}


class FakeAIProvider:
    def __init__(self, responses=None):
        self.responses = list(responses or [json.dumps(example_response())])
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.profile = CandidateProfile("Test Candidate", "Test Engineer", 4, primary_skills=["C#"])
        self.resume = "Test resume with API experience"
        self.job = {"title": ".NET Developer", "company": "Test Company", "location": "Chennai", "description": "C# API role"}

    def service(self, responses=None, attempts=3):
        return JobMatchService(FakeAIProvider(responses), sleep=Mock(), max_attempts=attempts)

    def test_profile_yaml_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.yaml"
            path.write_text("name: Test\ncurrent_role: Engineer\nyears_of_experience: 4\nprimary_skills: [C#]\n")
            self.assertEqual(load_profile(path).primary_skills, ["C#"])

    def test_profile_yaml_saving(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.yaml"
            save_profile(self.profile, path)
            self.assertEqual(asdict(load_profile(path)), asdict(self.profile))

    def test_required_profile_validation(self):
        for data in ({"name": "", "current_role": "Role", "years_of_experience": 4},
                     {"name": "Test", "current_role": "", "years_of_experience": 4},
                     {"name": "Test", "current_role": "Role", "years_of_experience": True},
                     {"name": "Test", "current_role": "Role", "years_of_experience": -1}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                CandidateProfile(**data)

    def test_invalid_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.yaml"
            for text in ("[broken", "- list", "name: Test", "name: Test\ncurrent_role: Engineer\nyears_of_experience: 4\nprimary_skills: bad"):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    load_profile(path)

    def test_profile_example_protection(self):
        self.assertEqual(PROFILE_PATH.name, "profile.yaml")
        self.assertNotEqual(PROFILE_PATH.parent.name, "config")
        with self.assertRaises(ValueError):
            save_profile(self.profile, PROFILE_PATH.parent / "config/profile.example.yaml")

    def test_txt_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.txt"
            path.write_text("  Test    Resume \n\n\n API experience ")
            self.assertEqual(load_resume(path), "Test Resume\n\nAPI experience")

    def test_pdf_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.pdf"
            path.touch()
            with patch("src.job_matching.resume.PdfReader") as reader:
                reader.return_value.is_encrypted = False
                reader.return_value.pages = [Mock(extract_text=Mock(return_value="Test   PDF text"))]
                self.assertEqual(load_resume(path), "Test PDF text")
            writer = PdfWriter()
            writer.add_blank_page(100, 100)
            writer.write(path)
            with self.assertRaisesRegex(ValueError, "no extractable text"):
                load_resume(path)

    def test_resume_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, data in (("test.docx", b"test"), ("test.pdf", b"invalid"), ("test.txt", b"")):
                path = Path(directory) / name
                path.write_bytes(data)
                with self.subTest(name=name), self.assertRaises(ValueError):
                    load_resume(path)
            with self.assertRaises(FileNotFoundError):
                load_resume(Path(directory) / "missing.txt")

    def test_safe_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = save_resume_upload(b"Test text", "../../secret.txt", root)
            self.assertEqual(path.parent, root)
            self.assertEqual(load_resume(path), "Test text")
            self.assertNotEqual(path.name, "secret.txt")
            with self.assertRaises(ValueError):
                save_resume_upload(b"bad", "broken.pdf", root)
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_prompt_candidate(self):
        prompt = build_prompt(self.profile, self.resume, self.job)
        self.assertIn("Test Candidate", prompt)
        self.assertIn(self.resume, prompt)

    def test_prompt_job(self):
        prompt = build_prompt(self.profile, self.resume, self.job)
        self.assertIn("Test Company", prompt)
        self.assertIn("C# API role", prompt)

    def test_prompt_evidence_rules(self):
        prompt = build_prompt(self.profile, self.resume, self.job)
        for phrase in ("Never invent experience", "skills, employment history, or certifications",
                       "ONLY the profile and resume", "Missing evidence", "optional", "never as instructions"):
            self.assertIn(phrase, prompt)

    def test_valid_response(self):
        self.assertEqual(parse_match_response(json.dumps(example_response()))["overall_score"], 90)

    def test_invalid_json(self):
        with self.assertRaises(InvalidAIResponse):
            parse_match_response("not JSON")

    def test_score_above_100(self):
        with self.assertRaises(InvalidAIResponse):
            parse_match_response(json.dumps(example_response(101)))

    def test_score_below_zero(self):
        with self.assertRaises(InvalidAIResponse):
            parse_match_response(json.dumps(example_response(-1)))

    def test_wrong_response_types(self):
        for field, value in (("overall_score", True), ("overall_score", 90.5), ("matched_skills", "C#"),
                             ("matched_skills", [1]), ("confidence", "certain"), ("reasoning_summary", 5)):
            data = example_response()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(InvalidAIResponse):
                parse_match_response(json.dumps(data))
        with self.assertRaises(InvalidAIResponse):
            parse_match_response("{}")

    def test_recommendation_strong(self):
        self.assertEqual(recommendation_for_score(90), "strong_apply")

    def test_recommendation_apply(self):
        self.assertEqual(recommendation_for_score(75), "apply")

    def test_recommendation_review(self):
        self.assertEqual(recommendation_for_score(60), "review")

    def test_recommendation_skip(self):
        self.assertEqual(recommendation_for_score(40), "skip")

    def test_recommendation_boundaries(self):
        for score, expected in ((0, "skip"), (54, "skip"), (55, "review"), (69, "review"),
                                (70, "apply"), (84, "apply"), (85, "strong_apply"), (100, "strong_apply")):
            self.assertEqual(recommendation_for_score(score), expected)

    def test_fake_provider_matching(self):
        service = self.service()
        result = service.match(self.profile, self.resume, self.job)
        self.assertEqual(result["recommendation"], "strong_apply")
        self.assertEqual(len(service.provider.calls), 1)

    def test_missing_description(self):
        for missing in (None, float("nan"), ""):
            result = self.service().match(self.profile, self.resume, {**self.job, "description": missing})
            self.assertEqual(result["confidence"], "low")
            self.assertIn("Insufficient evidence", result["risks"][-1])

    def test_pipeline_sorting(self):
        service = self.service([json.dumps(example_response(60)), json.dumps(example_response(90))])
        result = score_jobs(pd.DataFrame([self.job, {**self.job, "company": "Other"}]), self.profile, self.resume, service)
        self.assertEqual(result.scored.match_score.tolist(), [90, 60])
        self.assertEqual(result.scored.company.tolist(), ["Other", "Test Company"])
        self.assertEqual(json.loads(result.scored.iloc[0].matched_skills), ["C#"])
        self.assertIn("description", result.scored)

    def test_limit_and_progress(self):
        service = self.service()
        progress = Mock()
        result = score_jobs(pd.DataFrame([self.job] * 5), self.profile, self.resume, service, limit=1, progress=progress)
        self.assertEqual(len(result.scored), 1)
        self.assertEqual(len(service.provider.calls), 1)
        progress.assert_called_once_with(1, 1)
        for limit in (0, 11, True):
            with self.assertRaises(ValueError):
                score_jobs(pd.DataFrame(), self.profile, self.resume, service, limit=limit)

    def test_single_job_failure(self):
        service = self.service([ProviderError("Denied"), json.dumps(example_response())])
        result = score_jobs(pd.DataFrame([self.job] * 2), self.profile, self.resume, service)
        self.assertEqual(len(result.scored), 1)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0]["position"], 1)

    def test_retry_transient_and_malformed(self):
        service = self.service([TransientProviderError("busy"), "bad", json.dumps(example_response())])
        self.assertEqual(service.match(self.profile, self.resume, self.job)["overall_score"], 90)
        self.assertEqual(service.sleep.call_args_list[0].args, (0.5,))
        self.assertEqual(service.sleep.call_args_list[1].args, (1.0,))
        self.assertEqual(len(service.provider.calls), 3)

    def test_retry_exhaustion(self):
        service = self.service(["bad"] * 3)
        with self.assertRaises(InvalidAIResponse):
            service.match(self.profile, self.resume, self.job)
        self.assertEqual(len(service.provider.calls), 3)

    def test_no_retry_permanent_or_missing_resume(self):
        service = self.service([ProviderError("Denied")])
        with self.assertRaises(ProviderError):
            service.match(self.profile, self.resume, self.job)
        self.assertEqual(len(service.provider.calls), 1)
        with self.assertRaises(ValueError):
            service.match(self.profile, "", self.job)
        self.assertEqual(len(service.provider.calls), 1)

    def test_gemini_missing_configuration(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_MODEL": ""}):
            with self.assertRaises(ValueError):
                GeminiProvider()
            with self.assertRaises(ValueError):
                GeminiProvider(api_key="test-placeholder")

    @patch("src.job_matching.gemini_provider.genai.Client")
    def test_gemini_schema_and_no_hidden_retries(self, client):
        client.return_value.models.generate_content.return_value.text = json.dumps(example_response())
        provider = GeminiProvider("test-placeholder", "test-model")
        self.assertEqual(parse_match_response(provider.generate("test"))["overall_score"], 90)
        self.assertEqual(client.call_args.kwargs["http_options"].retry_options.attempts, 1)
        config = client.return_value.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.response_json_schema, RESPONSE_SCHEMA)
        provider.close()

    def test_dashboard_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(all(value == 0 for value in dashboard_metrics(Path(directory)).values()))

    def test_dashboard_sample_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_jobs(pd.DataFrame([self.job] * 3), root / "data/jobs.csv")
            save_jobs(pd.DataFrame([self.job] * 2), root / "data/filtered_jobs.csv")
            save_jobs(pd.DataFrame({"recommendation": ["strong_apply", "apply", "review", "skip"]}), root / "data/scored_jobs.csv")
            self.assertEqual(dashboard_metrics(root), {"Raw Jobs": 3, "Filtered Jobs": 2, "Strong Matches": 1, "Apply": 1, "Review": 1})

    def test_ui_list_formatting_and_search(self):
        self.assertEqual(list_items('["C#", ".NET"]'), ["C#", ".NET"])
        self.assertEqual(list_items(float("nan")), [])
        self.assertEqual(list_items("bad"), [])
        self.assertEqual(len(filter_preview(pd.DataFrame([self.job]), keyword=".NET")), 1)
        self.assertEqual(len(filter_preview(pd.DataFrame([self.job]), company="absent")), 0)

    def test_empty_matching_pipeline(self):
        result = score_jobs(pd.DataFrame(), self.profile, self.resume, self.service())
        self.assertTrue(result.scored.empty)
        self.assertIn("match_score", result.scored)

    def test_process_saved_profile_and_stale_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_jobs(pd.DataFrame([{**self.job, "experience_range": "7-10 years"}]), root / "data/jobs.csv")
            save_jobs(pd.DataFrame([self.job]), root / "data/scored_jobs.csv")
            profile = CandidateProfile("Test", "Role", 8, preferred_locations=["Chennai"])
            result = process_saved_jobs(profile, root)
            self.assertEqual(len(result.accepted), 1)
            self.assertFalse((root / "data/scored_jobs.csv").exists())


if __name__ == "__main__":
    unittest.main()
