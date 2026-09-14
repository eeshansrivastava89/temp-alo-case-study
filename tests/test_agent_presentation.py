from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent import _finalize_submission


class AgentPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = [
            {
                "tool": "rank_performance",
                "evidence_index": 0,
                "metric": "ga_conversion_rate",
                "metric_label": "GA Conversion Rate",
                "metric_format": "percent",
                "dimension": "channel",
                "direction": "top",
                "ranking_basis": "value",
                "period": {"start": "2026-06-22", "end": "2026-06-28"},
                "comparison": {"type": "ly", "label": "Provided LY comparator"},
                "results": [],
            }
        ]

    def test_submission_links_finding_to_valid_evidence(self) -> None:
        submission = {
            "headline": "Affiliates leads GA Conversion Rate.",
            "findings": [
                {
                    "statement": "GA Conversion Rate increased :green[**+0.46 pp**].",
                    "exhibit": {"evidence_index": 0, "visual": "bar"},
                }
            ],
            "action": "Validate the channel mix before reallocating spend.",
        }
        response = _finalize_submission(submission, self.evidence, [], "test-model")
        self.assertEqual(response.presentation, submission)
        self.assertIn(":green[**+0.46 pp**]", response.text)

    def test_submission_rejects_visual_not_supported_by_evidence(self) -> None:
        submission = {
            "headline": "Affiliates leads GA Conversion Rate.",
            "findings": [
                {
                    "statement": "Affiliates leads.",
                    "exhibit": {"evidence_index": 0, "visual": "line"},
                }
            ],
            "action": "Validate the result.",
        }
        with self.assertRaises(RuntimeError):
            _finalize_submission(submission, self.evidence, [], "test-model")


if __name__ == "__main__":
    unittest.main()
