from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def playwright_chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).exists()
    except Exception:
        return False


class DocsVisualSmokeTest(unittest.TestCase):
    def test_docs_visual_smoke_command(self) -> None:
        if not playwright_chromium_available():
            self.skipTest("Playwright Chromium is not installed")

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "icontool.py"),
                "docs-visual-smoke",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("docs/index.html dark desktop", result.stdout)
        self.assertIn("docs/requests.html light mobile", result.stdout)
        self.assertIn("docs visual smoke: OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
