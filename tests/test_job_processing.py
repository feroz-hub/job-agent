"""Offline deterministic processing tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.job_processing.cli import main
from src.job_processing.deduplicator import duplicate_mask
from src.job_processing.filters import parse_experience
from src.job_processing.models import FilterConfig
from src.job_processing.normalizer import normalize_jobs
from src.job_processing.pipeline import process_jobs


def job(**overrides):
    return {"title": ".NET Developer", "company": "Example", "location": "Chennai",
            "description": "", "job_url": "", **overrides}


class ProcessingTests(unittest.TestCase):
    def reason(self, **fields):
        return process_jobs(pd.DataFrame([job(**fields)])).decisions.iloc[0].processing_reason

    def test_normalization(self):
        raw = pd.DataFrame([job(title="  Senior   .NET Developer ", company=" ACME  Ltd ")])
        normalized = normalize_jobs(raw)
        self.assertEqual(normalized.iloc[0].title, "Senior .NET Developer")
        self.assertEqual(normalized.iloc[0]._normalized_title, "senior .net developer")
        self.assertEqual(normalized.iloc[0].company, "ACME Ltd")
        self.assertEqual(raw.iloc[0].title, "  Senior   .NET Developer ")

    def test_missing_values(self):
        raw = pd.DataFrame([job(title=None, company=float("nan"), location=pd.NA, description="  ")])
        normalized = normalize_jobs(raw)
        for field in ("title", "company", "location", "description", "job_url"):
            self.assertEqual(normalized.iloc[0][field], "")

    def test_url_duplicates(self):
        jobs = normalize_jobs(pd.DataFrame([
            job(job_url="https://EXAMPLE.com/jobs/1#details"),
            job(title="Different title", job_url="https://example.com/jobs/1"),
            job(job_url="https://example.com/jobs/2"),
        ]))
        self.assertEqual(duplicate_mask(jobs).tolist(), [False, True, False])

    def test_fallback_duplicates(self):
        jobs = normalize_jobs(pd.DataFrame([job(), job(title=" .net  developer ", company="example"), job(company="Other")]))
        self.assertEqual(duplicate_mask(jobs).tolist(), [False, True, False])

    def test_distinct_urls_preserved(self):
        jobs = normalize_jobs(pd.DataFrame([job(job_url="https://example.com/1"), job(job_url="https://example.com/2")]))
        self.assertFalse(duplicate_mask(jobs).any())

    def test_incomplete_identity_preserved(self):
        self.assertFalse(duplicate_mask(normalize_jobs(pd.DataFrame([job(company=None), job(company=None)]))).any())

    def test_target_titles(self):
        for title in (".NET Developer", "Senior Dot Net Developer", "C# Developer", "ASP.NET Core Developer", "Software Engineer (.NET)", ".NET Full Stack Developer"):
            with self.subTest(title=title):
                self.assertEqual(self.reason(title=title), "accepted")

    def test_unrelated_title(self):
        self.assertEqual(self.reason(title="Java Developer"), "rejected_unrelated_title")
        self.assertEqual(self.reason(title="Java Software Engineer"), "rejected_unrelated_title")

    def test_description_exclusion_not_applied(self):
        self.assertEqual(self.reason(description="Java is optional"), "accepted")

    def test_keyword_boundaries(self):
        self.assertEqual(self.reason(title="Software Engineer", description=""), "accepted")
        self.assertEqual(self.reason(title="Biosystems .NET Developer"), "accepted")

    def test_chennai(self):
        self.assertEqual(self.reason(location="Chennai (Perungudi), Bengaluru, India"), "accepted")

    def test_remote(self):
        self.assertEqual(self.reason(location="Remote"), "accepted")
        self.assertEqual(self.reason(location="Bengaluru", is_remote=True), "accepted")

    def test_other_location(self):
        self.assertEqual(self.reason(location="Mumbai, India"), "rejected_location")

    def test_unknown_location(self):
        self.assertEqual(self.reason(location=None), "accepted")

    def test_experience_ranges(self):
        for value in ("3-5 years", "3 to 6 years", "2-4 Yrs", "4+ years", "minimum 3 years"):
            with self.subTest(value=value):
                self.assertEqual(self.reason(experience_range=value), "accepted")
        for value in ("7-10 years", "1-3 years", "5 years experience"):
            with self.subTest(value=value):
                self.assertEqual(self.reason(experience_range=value), "rejected_experience")

    def test_unknown_experience(self):
        for value in (None, "competitive", "5-3 years", "3-5 years or 7-10 years"):
            with self.subTest(value=value):
                self.assertIsNone(parse_experience(value))
                self.assertEqual(self.reason(experience_range=value), "accepted")
        self.assertEqual(self.reason(description="Worked on a project for 7-10 years"), "accepted")

    def test_explicit_description_experience(self):
        self.assertEqual(self.reason(description="Experience required: 7-10 years"), "rejected_experience")
        self.assertEqual(self.reason(description="Experience: 3-5 years"), "accepted")
        self.assertEqual(self.reason(description="Experience: 7-10 years. Experience: 3-5 years"), "accepted")

    def test_configuration(self):
        config = FilterConfig(target_keywords=("python",), excluded_title_keywords=(),
                              preferred_locations=("Mumbai",), candidate_experience_years=8)
        result = process_jobs(pd.DataFrame([job(title="Python Developer", location="Mumbai", experience_range="7-10 years")]), config)
        self.assertEqual(result.counts["accepted"], 1)

    def test_pipeline_counts(self):
        rows = [job(), job(), job(title="Java Developer"), job(company="Else", location="Mumbai"),
                job(company="Senior", experience_range="7-10 years"), job(company="Remote", location="Remote")]
        result = process_jobs(pd.DataFrame(rows))
        self.assertEqual(result.counts, {"raw": 6, "duplicate": 1, "rejected_unrelated_title": 1,
                                       "rejected_location": 1, "rejected_experience": 1, "accepted": 2})
        self.assertEqual(len(result.decisions), 6)
        self.assertFalse(any(name.startswith("_") for name in result.accepted.columns))
        self.assertEqual(result.accepted.company.tolist(), ["Example", "Remote"])

    def test_empty_pipeline(self):
        result = process_jobs(pd.DataFrame())
        self.assertTrue(result.accepted.empty)
        self.assertEqual(sum(result.counts.values()), 0)

    def test_cli_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            pd.DataFrame([job(), job(title="Java Developer")]).to_csv(root / "data/jobs.csv", index=False)
            with patch("src.job_processing.cli.ROOT", root), patch("builtins.print"):
                self.assertEqual(main(), 0)
            output = pd.read_csv(root / "data/filtered_jobs.csv")
            self.assertEqual(output.title.tolist(), [".NET Developer"])
            self.assertNotIn("processing_reason", output.columns)


if __name__ == "__main__":
    unittest.main()
