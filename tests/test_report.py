import unittest

from oss_update_watch.report import render_markdown


class ReportTests(unittest.TestCase):
    def test_update_report_shows_acknowledged_and_current_values(self):
        report = {
            "generated_at": "2026-09-09T00:00:00+00:00",
            "summary": {
                "update_available": 1,
                "unbaselined": 0,
                "error": 0,
                "up_to_date": 0,
                "local_updates": 1,
                "upstream_changes": 1,
            },
            "items": [
                {
                    "repo": "owner/repo",
                    "status": "update_available",
                    "priority": "high",
                    "usages": [{"project": "tool", "relation": "direct"}],
                    "acknowledged": {"mode": "release", "value": "v1.0.0"},
                    "current": {"mode": "release", "value": "v2.0.0"},
                    "local": {"status": "behind", "update_available": True, "usages": []},
                }
            ],
        }

        markdown = render_markdown(report)

        self.assertIn("| Baseline | Current upstream |", markdown)
        self.assertIn("| BEHIND | CHANGED | owner/repo | v1.0.0 | v2.0.0 |", markdown)


if __name__ == "__main__":
    unittest.main()
