import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "validate_visual_accessibility.py"
SPEC = importlib.util.spec_from_file_location("validate_visual_accessibility", SCRIPT_PATH)
visual_validation = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = visual_validation
SPEC.loader.exec_module(visual_validation)


class VisualAccessibilityTests(unittest.TestCase):
    def test_capture_matrix_covers_themes_and_resolutions(self):
        combinations = {
            (capture["theme"], capture["size"]) for capture in visual_validation.CAPTURES
        }

        for size in ((390, 844), (768, 1024), (1600, 1000)):
            self.assertIn(("solar", size), combinations)
            self.assertIn(("lunar", size), combinations)

    def test_identical_images_have_no_visual_difference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            current = Path(temp_dir) / "current.png"
            baseline = Path(temp_dir) / "baseline.png"
            difference = Path(temp_dir) / "difference.png"
            Image.new("RGB", (20, 20), "#ffffff").save(current)
            Image.new("RGB", (20, 20), "#ffffff").save(baseline)

            result = visual_validation.compare_images(current, baseline, difference)

        self.assertTrue(result["passed"])
        self.assertEqual(result["difference_percent"], 0)
        self.assertFalse(difference.exists())

    def test_relevant_visual_change_generates_diff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            current = Path(temp_dir) / "current.png"
            baseline = Path(temp_dir) / "baseline.png"
            difference = Path(temp_dir) / "difference.png"
            Image.new("RGB", (20, 20), "#000000").save(current)
            Image.new("RGB", (20, 20), "#ffffff").save(baseline)

            result = visual_validation.compare_images(current, baseline, difference)

            self.assertFalse(result["passed"])
            self.assertEqual(result["difference_percent"], 100)
            self.assertTrue(difference.exists())

    def test_single_pixel_rasterization_shift_is_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            current = Path(temp_dir) / "current.png"
            baseline = Path(temp_dir) / "baseline.png"
            difference = Path(temp_dir) / "difference.png"
            baseline_image = Image.new("RGB", (40, 40), "#ffffff")
            for position in range(8, 32):
                baseline_image.putpixel((position, 20), (0, 0, 0))
            baseline_image.save(baseline)
            shifted_image = Image.new("RGB", (40, 40), "#ffffff")
            for position in range(8, 32):
                shifted_image.putpixel((position, 21), (0, 0, 0))
            shifted_image.save(current)

            result = visual_validation.compare_images(
                current,
                baseline,
                difference,
            )

        self.assertTrue(result["passed"])
        self.assertLessEqual(result["difference_percent"], 0.35)
        self.assertFalse(difference.exists())

    def test_fixture_exposes_required_accessibility_contracts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "report.html"
            visual_validation.render_fixture(fixture, 10)
            document = fixture.read_text(encoding="utf-8")

        self.assertIn('lang="pt-BR"', document)
        self.assertIn('role="status" aria-live="polite"', document)
        self.assertIn('scope="col"', document)
        self.assertIn('aria-labelledby="incident-dialog-title"', document)
        self.assertIn('aria-label="Buscar em todos os incidentes"', document)

    def test_capture_forces_isolated_section_layout_before_screenshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "report.html"
            visual_validation.render_fixture(fixture, 40)
            visual_validation.inject_capture_state(
                fixture,
                theme="lunar",
                section=".table-wrap",
                modal=None,
            )
            document = fixture.read_text(encoding="utf-8")

        self.assertIn("void isolated.getBoundingClientRect()", document)
        self.assertIn('dataset.visualReady = "true"', document)


if __name__ == "__main__":
    unittest.main()
