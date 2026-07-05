from __future__ import annotations

import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
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


class PseudoLocaleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icontool = load_icontool()

    def test_pseudo_locale_preserves_placeholders_and_writes_temp_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = root / "strings.xml"
            docs = root / "index.html"
            output = root / "out"
            values.write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="launcher_apply_unavailable">Could not open %1$s. Install the launcher.</string>
    <string name="privacy_policy_link" translatable="false">https://example.com/privacy</string>
</resources>
""",
                encoding="utf-8",
            )
            docs.write_text(
                """<!doctype html>
<html><body><button>Apply Icons</button><script>const label = "Apply Icons";</script></body></html>
""",
                encoding="utf-8",
            )

            audit = self.icontool._pseudo_locale_audit(
                source_paths=[values],
                docs_paths=(docs,),
                output_dir=output,
            )

            self.assertEqual(audit["errors"], [])
            self.assertEqual(audit["android_value_count"], 2)
            expanded = ET.parse(output / "values-en-rXA" / "strings.xml").getroot()
            text = expanded.find("string").text
            self.assertIn("%1$s", text)
            self.assertNotIn("https://example.com/privacy", text)
            pseudo_doc = (output / "docs-en-rXA" / "index.html").read_text(encoding="utf-8")
            self.assertIn('const label = "Apply Icons";', pseudo_doc)
            self.assertIn("[!!", pseudo_doc)

    def test_pseudo_locale_reports_clipping_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = root / "home_setup.xml"
            docs = root / "index.html"
            values.write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="quick_apply_custom_text">Apply this complete icon pack immediately from this long button label</string>
</resources>
""",
                encoding="utf-8",
            )
            docs.write_text("<html><body>Gallery</body></html>", encoding="utf-8")

            audit = self.icontool._pseudo_locale_audit(
                source_paths=[values],
                docs_paths=(docs,),
                output_dir=root / "out",
            )

            warnings = audit["warnings"]
            self.assertTrue(warnings)
            self.assertEqual(warnings[0]["name"], "quick_apply_custom_text")


if __name__ == "__main__":
    unittest.main()
