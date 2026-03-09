from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_pipeline import main as run_pipeline_main  # noqa: E402


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run_pipeline_main()

    def test_expected_slice_count(self):
        slice_files = list((ROOT / "corpus" / "slices").glob("*.md"))
        self.assertEqual(len(slice_files), 3)

    def test_reports_pass(self):
        report_files = list((ROOT / "outputs" / "reports").glob("*.json"))
        self.assertTrue(report_files)
        for report_file in report_files:
            report = json.loads(report_file.read_text())
            self.assertTrue(report["pass"], msg=report_file.name)

    def test_property_reports_pass(self):
        property_files = list((ROOT / "outputs" / "properties").glob("*.json"))
        self.assertTrue(property_files)
        for property_file in property_files:
            report = json.loads(property_file.read_text())
            self.assertTrue(report["pass"], msg=property_file.name)

    def test_resume_seed_generation(self):
        seed_file = ROOT / "outputs" / "seeds" / "5.3.13-rrc-connection-resume.json"
        data = json.loads(seed_file.read_text())
        self.assertGreaterEqual(len(data["seeds"]), 2)
        resume_boundary = [
            seed
            for seed in data["seeds"]
            if seed["message"] == "RRCResume" and seed["mutation_class"] == "boundary"
        ]
        self.assertTrue(resume_boundary)

    def test_retrieval_prefers_resume(self):
        retrieval_file = ROOT / "outputs" / "retrieval" / "last_query.json"
        payload = json.loads(retrieval_file.read_text())
        self.assertTrue(payload["results"])
        self.assertEqual(payload["results"][0]["slice"], "5.3.13-rrc-connection-resume.md")


if __name__ == "__main__":
    unittest.main()
