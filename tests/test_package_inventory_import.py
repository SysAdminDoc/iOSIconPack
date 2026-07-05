from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PackageInventoryImportTest(unittest.TestCase):
    def test_imports_adb_text_without_network_and_preserves_unicode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory_path = Path(tmp) / "inventory.txt"
            inventory_path.write_text(
                "\n".join(
                    [
                        "package:com.example.cafe",
                        "application-label:'Café Notes'",
                        "userId=10 work-profile",
                        "ComponentInfo{com.example.cafe/com.example.MainActivity}",
                        "package:com.android.chrome",
                        "application-label:'Chrome'",
                        "ComponentInfo{com.android.chrome/com.google.android.apps.chrome.Main}",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "icontool.py"),
                    "package-inventory-import",
                    "--input",
                    str(inventory_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["network"])
        self.assertEqual(payload["emitted_records"], 1)

        record = payload["records"][0]
        self.assertEqual(record["app_name"], "Café Notes")
        self.assertEqual(record["package"], "com.example.cafe")
        self.assertEqual(record["status"], "ready-to-map")
        self.assertTrue(record["work_profile_ambiguous"])
        self.assertIn("ComponentInfo{com.example.cafe/com.example.MainActivity}", record["candidate_appfilter_item"])
        self.assertNotIn("com.android.chrome", result.stdout)


if __name__ == "__main__":
    unittest.main()
