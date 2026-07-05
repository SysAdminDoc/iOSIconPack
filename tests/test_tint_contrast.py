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


class TintContrastTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icontool = load_icontool()

    def _write_fixture(self, root: Path, name: str = "ios18_test") -> tuple[Path, Path]:
        drawable_dir = root / "drawable"
        values_dir = root / "values"
        drawable_dir.mkdir()
        values_dir.mkdir()
        (values_dir / "colors.xml").write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="era_tint_ios18">#0A84FF</color>
    <color name="ios18_themed_icon_background">@color/era_tint_ios18</color>
</resources>
""",
            encoding="utf-8",
        )
        (drawable_dir / f"{name}_mono.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="192dp"
    android:height="192dp"
    android:viewportWidth="192"
    android:viewportHeight="192">
    <path android:fillColor="#FFFFFFFF" android:pathData="M48,48 H144 V144 H48 Z" />
</vector>
""",
            encoding="utf-8",
        )
        (drawable_dir / f"{name}_themed.xml").write_text(
            f"""<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ios18_themed_icon_background" />
    <foreground android:drawable="@drawable/{name}" />
    <monochrome android:drawable="@drawable/{name}_mono" />
</adaptive-icon>
""",
            encoding="utf-8",
        )
        return drawable_dir, values_dir

    def test_tint_audit_accepts_valid_monochrome_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drawable_dir, values_dir = self._write_fixture(Path(tmp))

            audit = self.icontool._tint_contrast_audit(
                drawable_dir,
                values_dir,
                simulations=(("light-test", "light", "test", "#000000", "#FFFFFF"),),
            )

        self.assertEqual(audit["entry_count"], 1)
        self.assertEqual(audit["findings"], [])
        self.assertEqual(audit["entries"]["ios18_test"]["wrapper"]["background_color"], "#FF0A84FF")

    def test_tint_audit_reports_low_wallpaper_palette_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drawable_dir, values_dir = self._write_fixture(Path(tmp))

            audit = self.icontool._tint_contrast_audit(
                drawable_dir,
                values_dir,
                simulations=(("low-test", "dark", "gray", "#777777", "#787878"),),
            )

        self.assertEqual(len(audit["findings"]), 1)
        finding = audit["findings"][0]
        self.assertEqual(finding["drawable"], "ios18_test")
        self.assertIn("low-test tint contrast", "\n".join(finding["reasons"]))

    def test_tint_audit_reports_broken_monochrome_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drawable_dir, values_dir = self._write_fixture(Path(tmp), "ios18_bad")
            themed = drawable_dir / "ios18_bad_themed.xml"
            themed.write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ios18_themed_icon_background" />
    <foreground android:drawable="@drawable/ios18_bad" />
    <monochrome android:drawable="@drawable/ios18_other_mono" />
</adaptive-icon>
""",
                encoding="utf-8",
            )

            audit = self.icontool._tint_contrast_audit(
                drawable_dir,
                values_dir,
                simulations=(("light-test", "light", "test", "#000000", "#FFFFFF"),),
            )

        reasons = "\n".join(audit["findings"][0]["reasons"])
        self.assertIn("expected @drawable/ios18_bad_mono", reasons)


if __name__ == "__main__":
    unittest.main()
