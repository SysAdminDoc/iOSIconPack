from __future__ import annotations

import importlib.util
import tempfile
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
            ["8.12.0", "9.0.0-alpha01", "8.13.0", "9.0.0-rc01", "9.7.0-milestone-2"]
        )

        self.assertEqual(latest, "8.13.0")

    def test_osv_vuln_ids_extracts_ids(self) -> None:
        ids = self.icontool._osv_vuln_ids(
            {"vulns": [{"id": "GHSA-test-1"}, {"id": "CVE-2099-0001"}, {}]}
        )

        self.assertEqual(ids, ["GHSA-test-1", "CVE-2099-0001"])

    def test_gradle_wrapper_version_parses_distribution_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            properties = Path(tmp) / "gradle-wrapper.properties"
            properties.write_text(
                "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.13-bin.zip\n",
                encoding="utf-8",
            )

            version = self.icontool._gradle_wrapper_version(properties)

        self.assertEqual(version, "8.13")

    def test_toolchain_apply_updates_mutates_only_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            versions = workspace / self.icontool.VERSIONS_KT.relative_to(REPO_ROOT)
            requirements = workspace / self.icontool.REQUIREMENTS_TXT.relative_to(REPO_ROOT)
            wrapper = workspace / self.icontool.GRADLE_WRAPPER_PROPERTIES.relative_to(REPO_ROOT)
            versions.parent.mkdir(parents=True)
            requirements.parent.mkdir(parents=True, exist_ok=True)
            wrapper.parent.mkdir(parents=True)
            versions.write_text(
                'object Versions {\n'
                '    const val gradle = "8.12.0"\n'
                '    const val kotlin = "2.2.21"\n'
                '    const val ksp = "2.3.4"\n'
                '    const val blueprint = "2.5.1"\n'
                '}\n',
                encoding="utf-8",
            )
            requirements.write_text("Pillow>=10.0.0\n", encoding="utf-8")
            wrapper.write_text(
                "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.13-bin.zip\n",
                encoding="utf-8",
            )

            errors = self.icontool._toolchain_apply_updates(
                workspace,
                [
                    {"id": "agp", "name": "Android Gradle Plugin", "latest": "8.13.0"},
                    {"id": "pillow", "name": "Pillow", "latest": "12.0.0"},
                    {"id": "gradle-wrapper", "name": "Gradle wrapper", "latest": "9.2.1"},
                ],
            )

            self.assertEqual(errors, [])
            self.assertIn('const val gradle = "8.13.0"', versions.read_text(encoding="utf-8"))
            self.assertEqual(requirements.read_text(encoding="utf-8"), "Pillow>=12.0.0\n")
            self.assertIn("gradle-9.2.1-bin.zip", wrapper.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
