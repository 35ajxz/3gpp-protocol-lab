from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_logic_campaign import main as run_logic_campaign_main  # noqa: E402


class LogicCampaignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run_logic_campaign_main()

    def test_summary_exists(self):
        summary_path = ROOT / "outputs" / "logic" / "summary.json"
        self.assertTrue(summary_path.exists())
        summary = json.loads(summary_path.read_text())
        self.assertEqual(summary["case_count"], 14)
        self.assertGreater(summary["finding_count"], 0)

    def test_expected_finding_types(self):
        summary = json.loads((ROOT / "outputs" / "logic" / "summary.json").read_text())
        finding_types = summary["finding_types"]
        self.assertIn("negative_acceptance", finding_types)
        self.assertIn("state_divergence", finding_types)

    def test_cross_procedure_swap_generates_findings(self):
        findings = json.loads((ROOT / "outputs" / "logic" / "findings.json").read_text())
        cross_swap = [item for item in findings if item["perturbation"] == "cross_procedure_response_swap"]
        self.assertTrue(cross_swap)


if __name__ == "__main__":
    unittest.main()
