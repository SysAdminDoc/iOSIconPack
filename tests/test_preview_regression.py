from __future__ import annotations

import copy
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


class PreviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icontool = load_icontool()

    def test_manifest_renders_all_preview_masks(self) -> None:
        Image, _, ImageDraw = self.icontool._preview_pillow_modules()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ios18_test.png"
            image = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((18, 18, 174, 174), radius=40, fill=(0, 122, 255, 255))
            image.save(path)

            manifest = self.icontool._preview_regression_manifest(Path(tmp))

        self.assertEqual(manifest["entry_count"], 1)
        entry = manifest["entries"]["ios18_test"]
        self.assertEqual(set(entry["renders"]), set(self.icontool.PREVIEW_MASKS))
        self.assertEqual(entry["alpha_bounds"], [18, 18, 175, 175])

    def test_diff_reports_source_and_mask_changes(self) -> None:
        base_renders = {mask: "same" for mask in self.icontool.PREVIEW_MASKS}
        expected = {
            "schema": self.icontool.PREVIEW_SCHEMA_VERSION,
            "icon_size": self.icontool.PREVIEW_ICON_SIZE,
            "masks": list(self.icontool.PREVIEW_MASKS),
            "entries": {
                "ios18_test": {
                    "source_sha256": "old",
                    "alpha_bounds": [0, 0, 192, 192],
                    "renders": base_renders,
                }
            },
        }
        actual = copy.deepcopy(expected)
        actual["entries"]["ios18_test"]["source_sha256"] = "new"
        actual["entries"]["ios18_test"]["renders"]["circle"] = "changed"

        diff = self.icontool._preview_manifest_diff(expected, actual)

        self.assertTrue(self.icontool._preview_has_diff(diff))
        self.assertEqual(diff["changed"][0]["drawable"], "ios18_test")
        self.assertEqual(diff["changed"][0]["fields"], ["source_sha256", "render:circle"])


if __name__ == "__main__":
    unittest.main()
