from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PNG_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable-xxxhdpi"
PROVENANCE_JSON = REPO_ROOT / "app" / "src" / "main" / "assets" / "icon_provenance.json"


class IconProvenanceTest(unittest.TestCase):
    def test_manifest_matches_shipped_pngs(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "fetch_icons.py"), "--provenance-check"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(PROVENANCE_JSON.read_text(encoding="utf-8"))
        pngs = {
            path.stem
            for path in PNG_DIR.glob("*.png")
            if path.stem.startswith(("ios", "tp_"))
        }
        self.assertEqual(set(manifest["entries"]), pngs)
        self.assertEqual(manifest["entry_count"], len(pngs))


if __name__ == "__main__":
    unittest.main()
