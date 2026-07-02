from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_style_prototypes():
    spec = importlib.util.spec_from_file_location(
        "style_prototypes_under_test",
        REPO_ROOT / "scripts" / "gen_style_prototypes.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load scripts/gen_style_prototypes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StylePrototypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_style_prototypes()

    def test_style_attrs_transform_open_paths_safely(self) -> None:
        path = {
            self.generator._android_attr("pathData"): "M24,96 L168,96",
            self.generator._android_attr("strokeColor"): "#FFFFFFFF",
            self.generator._android_attr("strokeWidth"): "11",
        }

        line = self.generator._style_path_attrs(path, "line")
        filled = self.generator._style_path_attrs(path, "filled")
        sharp = self.generator._style_path_attrs(path, "sharp")

        self.assertEqual(line[self.generator._android_attr("strokeWidth")], "8")
        self.assertEqual(filled[self.generator._android_attr("strokeWidth")], "11")
        self.assertEqual(sharp[self.generator._android_attr("strokeLineCap")], "butt")
        self.assertEqual(sharp[self.generator._android_attr("strokeLineJoin")], "miter")

    def test_build_manifest_writes_three_style_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            drawable_dir = root / "drawable"
            output_dir = root / "style-prototypes"
            drawable_dir.mkdir()
            (drawable_dir / "ios18_test_mono.xml").write_text(
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
                '    android:width="192dp"\n'
                '    android:height="192dp"\n'
                '    android:viewportWidth="192"\n'
                '    android:viewportHeight="192">\n'
                '    <path android:fillColor="#FFFFFFFF" android:pathData="M48,48 H144 V144 H48 Z" />\n'
                "</vector>\n",
                encoding="utf-8",
            )

            manifest = self.generator.build_manifest(
                drawable_dir=drawable_dir,
                output_dir=output_dir,
                write=True,
            )

            self.assertEqual(manifest["source_count"], 1)
            self.assertEqual(manifest["file_count"], 3)
            self.assertTrue((output_dir / "sharp" / "sharp_ios18_test.xml").exists())
            self.assertTrue((output_dir / "line" / "line_ios18_test.xml").exists())
            self.assertTrue((output_dir / "filled" / "filled_ios18_test.xml").exists())
            self.assertTrue((output_dir / "style_prototypes.json").exists())


if __name__ == "__main__":
    unittest.main()
