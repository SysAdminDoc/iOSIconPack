from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_icontool():
    spec = importlib.util.spec_from_file_location(
        "icontool_under_test",
        REPO_ROOT / "scripts" / "icontool.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/icontool.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DependencyAuditHelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icontool = load_icontool()

    def test_latest_stable_filters_prereleases(self) -> None:
        latest = self.icontool._latest_stable_version(
            ["8.12.0", "9.0.0-alpha01", "8.13.0", "9.0.0-rc01"]
        )

        self.assertEqual(latest, "8.13.0")

    def test_osv_vuln_ids_extracts_ids(self) -> None:
        ids = self.icontool._osv_vuln_ids(
            {"vulns": [{"id": "GHSA-test-1"}, {"id": "CVE-2099-0001"}, {}]}
        )

        self.assertEqual(ids, ["GHSA-test-1", "CVE-2099-0001"])


if __name__ == "__main__":
    unittest.main()
