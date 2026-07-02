from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CoverageGapCommandTest(unittest.TestCase):
    def test_scores_requests_and_public_sources_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            issues_path = tmp_path / "issues.json"
            source_path = tmp_path / "sample_appfilter.xml"

            issues_path.write_text(
                json.dumps(
                    [
                        {
                            "number": 7,
                            "title": "[Icon] Example Notes",
                            "html_url": "https://github.com/SysAdminDoc/iOSIconPack/issues/7",
                            "labels": [{"name": "icon-request"}],
                            "body": "\n".join(
                                [
                                    "### App name",
                                    "Example Notes",
                                    "",
                                    "### Package name",
                                    "com.example.uncovered",
                                    "",
                                    "### ComponentInfo (optional)",
                                    "",
                                    "### Play Store URL",
                                    "https://play.google.com/store/apps/details?id=com.example.uncovered",
                                ]
                            ),
                        }
                    ]
                ),
                encoding="utf-8",
            )
            source_path.write_text(
                "\n".join(
                    [
                        '<?xml version="1.0" encoding="utf-8"?>',
                        "<resources>",
                        '  <item component="ComponentInfo{com.example.uncovered/com.example.MainActivity}" drawable="notes" />',
                        '  <item component="ComponentInfo{com.android.chrome/com.google.android.apps.chrome.Main}" drawable="chrome" />',
                        "</resources>",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "icontool.py"),
                    "coverage-gap",
                    "--input",
                    str(issues_path),
                    "--no-public-sources",
                    "--source",
                    f"SamplePack={source_path}",
                    "--top",
                    "5",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("com.example.uncovered", result.stdout)
        self.assertIn("requests #7", result.stdout)
        self.assertIn("SamplePack x1", result.stdout)
        self.assertIn("existing drawable: ios18_notes", result.stdout)
        self.assertNotIn("  2. score", result.stdout)


if __name__ == "__main__":
    unittest.main()
