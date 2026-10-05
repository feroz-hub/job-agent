"""Offline tests: no real job-board requests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.job_discovery.cli import main
from src.job_discovery.models import JobSearchConfig
from src.job_discovery.service import discover_jobs, save_jobs_csv


class JobDiscoveryTests(unittest.TestCase):
    def test_defaults(self):
        config = JobSearchConfig()
        self.assertEqual(config.search_term, ".NET Developer")
        self.assertEqual(config.location, "Chennai")
        self.assertEqual(config.sites, ("naukri",))
        self.assertEqual(config.results_wanted, 10)
        self.assertEqual(config.hours_old, 168)

    @patch("src.job_discovery.service.scrape_jobs")
    def test_service_arguments_and_dataframe(self, scrape):
        config = JobSearchConfig("Python Developer", "Mumbai", ("naukri",), 5, 24)
        expected = pd.DataFrame({"title": ["Python Developer"]})
        scrape.return_value = expected
        actual = discover_jobs(config)
        scrape.assert_called_once_with(
            site_name=["naukri"], search_term="Python Developer", location="Mumbai",
            results_wanted=5, hours_old=24, verbose=2,
        )
        self.assertIs(actual, expected)
        self.assertIsInstance(actual, pd.DataFrame)

    @patch("src.job_discovery.service.scrape_jobs", return_value=pd.DataFrame())
    def test_empty_results(self, scrape):
        self.assertTrue(discover_jobs(JobSearchConfig()).empty)

    @patch("src.job_discovery.service.scrape_jobs", side_effect=RuntimeError("network failure"))
    def test_service_propagates_failure(self, scrape):
        with self.assertLogs("src.job_discovery.service", level="ERROR"):
            with self.assertRaisesRegex(RuntimeError, "network failure"):
                discover_jobs(JobSearchConfig())

    def test_csv_export(self):
        jobs = pd.DataFrame({"title": [".NET Developer"], "company": ["Example"]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data" / "jobs.csv"
            save_jobs_csv(jobs, path)
            pd.testing.assert_frame_equal(pd.read_csv(path), jobs)
            save_jobs_csv(jobs.iloc[:0], path)
            self.assertEqual(list(pd.read_csv(path).columns), ["title", "company"])
            self.assertTrue(pd.read_csv(path).empty)

    @patch("builtins.print")
    @patch("src.job_discovery.cli.save_jobs_csv")
    @patch("src.job_discovery.cli.discover_jobs")
    def test_cli_missing_columns_and_empty_results(self, discover, save, output):
        for jobs in (pd.DataFrame({"title": ["Developer"]}), pd.DataFrame()):
            with self.subTest(columns=list(jobs.columns)):
                discover.return_value = jobs
                self.assertEqual(main(), 0)
                self.assertIs(save.call_args.args[0], jobs)

    @patch("builtins.print")
    @patch("src.job_discovery.cli.save_jobs_csv")
    @patch("src.job_discovery.cli.discover_jobs", side_effect=RuntimeError("blocked"))
    def test_cli_failure_does_not_export(self, discover, save, output):
        with self.assertLogs("src.job_discovery.cli", level="ERROR"):
            self.assertEqual(main(), 1)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
