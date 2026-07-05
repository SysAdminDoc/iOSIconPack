from __future__ import annotations

import importlib.util
import json
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


class IconQualityAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icontool = load_icontool()

    def _write_icon_fixture(self, root: Path, name: str, raw_size: int = 1024) -> None:
        Image, _, _ = self.icontool._preview_pillow_modules()
        png_dir = root / "drawable-xxxhdpi"
        vector_dir = root / "drawable"
        raw_dir = root / "icons_raw"
        png_dir.mkdir(exist_ok=True)
        vector_dir.mkdir(exist_ok=True)
        raw_dir.mkdir(exist_ok=True)

        Image.new("RGBA", (192, 192), (0, 122, 255, 255)).save(png_dir / f"{name}.png")
        Image.new("RGBA", (raw_size, raw_size), (0, 122, 255, 255)).save(raw_dir / f"{name}_{raw_size}.png")
        for path in (
            vector_dir / f"{name}_mono.xml",
            vector_dir / f"{name}_themed.xml",
            vector_dir / f"glyph_{name}.xml",
        ):
            path.write_text('<vector xmlns:android="http://schemas.android.com/apk/res/android" />\n', encoding="utf-8")

    def _write_provenance(self, root: Path, names: list[str], raw_size: int = 1024) -> Path:
        entries = {
            name: {
                "raw_artifact": f"icons_raw/{name}_{raw_size}.png",
            }
            for name in names
        }
        path = root / "icon_provenance.json"
        path.write_text(json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8")
        return path

    def test_low_resolution_source_is_ranked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_icon_fixture(root, "ios18_test", raw_size=256)
            provenance = self._write_provenance(root, ["ios18_test"], raw_size=256)

            findings = self.icontool._quality_findings(
                drawable_dir=root / "drawable-xxxhdpi",
                vector_dir=root / "drawable",
                provenance_path=provenance,
                repo_root=root,
                weak_contrast_ratio=0,
                low_alpha_coverage=0,
                corner_opaque_px=999,
                squircle_leak_ratio=1,
            )

        reasons = "\n".join(reason for finding in findings for reason in finding.reasons)
        self.assertIn("low-resolution source 256x256px below 512px", reasons)

    def test_complete_era_set_has_no_variant_gap(self) -> None:
        names = [self.icontool._quality_drawable_for_era(era, "test") for era in self.icontool.ICON_QUALITY_ERAS]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in names:
                self._write_icon_fixture(root, name)
            provenance = self._write_provenance(root, names)

            findings = self.icontool._quality_findings(
                drawable_dir=root / "drawable-xxxhdpi",
                vector_dir=root / "drawable",
                provenance_path=provenance,
                repo_root=root,
                weak_contrast_ratio=0,
                low_alpha_coverage=0,
                corner_opaque_px=999,
                squircle_leak_ratio=1,
            )

        reasons = "\n".join(reason for finding in findings for reason in finding.reasons)
        self.assertNotIn("variant gap", reasons)


if __name__ == "__main__":
    unittest.main()
