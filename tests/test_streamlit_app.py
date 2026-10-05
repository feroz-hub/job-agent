"""Small presentation smoke checks with isolated synthetic local inputs."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from components import sidebar
from src.job_matching.models import CandidateProfile
from src.job_matching.profile import load_profile
import src.job_matching.profile as profile_module
from src.job_matching.resume import save_resume_upload


class StreamlitTests(unittest.TestCase):
    def test_pages_missing_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(sidebar, "ROOT", root), patch.object(profile_module, "PROFILE_PATH", root / "profile.yaml"), patch.dict(os.environ, {"GEMINI_API_KEY": "", "GEMINI_MODEL": ""}):
                for file in [ROOT / "app/Home.py", *sorted((ROOT / "app/pages").glob("*.py"))]:
                    with self.subTest(page=file.name):
                        app = AppTest.from_file(str(ROOT / "app/Home.py")).run(timeout=15)
                        if file.name != "Home.py":
                            app.switch_page("pages/" + file.name).run(timeout=15)
                        self.assertEqual(len(app.exception), 0)
                        if file.name == "3_AI_Matches.py":
                            self.assertTrue(app.button[0].disabled)
                            self.assertGreaterEqual(len(app.warning), 4)

    def test_profile_form_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "profile.yaml"
            # Route the form's service call to a temporary personal file only.
            from src.job_matching.profile import save_profile
            with patch.object(sidebar, "ROOT", root), patch.object(profile_module, "PROFILE_PATH", path), patch.object(profile_module, "save_profile", side_effect=lambda value: save_profile(value, path)):
                app = AppTest.from_file(str(ROOT / "app/pages/4_Profile.py")).run()
                app.text_input[0].set_value("Test Candidate")
                app.text_input[1].set_value("Test Engineer")
                app.number_input[0].set_value(4.0)
                app.button[0].click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(app.success)
                self.assertEqual(load_profile(path).name, "Test Candidate")

    def test_settings_resume_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            save_resume_upload(b"Synthetic test resume", "test.txt", root / "resume")
            with patch.object(sidebar, "ROOT", root):
                app = AppTest.from_file(str(ROOT / "app/pages/5_Settings.py")).run()
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(app.success)
                self.assertEqual(app.text[-1].value, "Synthetic test resume")
