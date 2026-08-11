import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import SceneSettingsUpdate  # noqa: E402


class SceneSettingsUpdateTests(unittest.TestCase):
    def test_video_layer_defaults_are_full_canvas_and_visible(self):
        config = SceneSettingsUpdate()

        self.assertEqual(config.video_x, 50)
        self.assertEqual(config.video_y, 50)
        self.assertEqual(config.video_width, 100)
        self.assertEqual(config.video_height, 100)
        self.assertEqual(config.video_rotation, 0)
        self.assertEqual(config.video_fit, "contain")
        self.assertTrue(config.video_visible)
        self.assertTrue(config.avatar_visible)
        self.assertTrue(config.caption_visible)

    def test_video_transform_bounds_are_validated(self):
        invalid_values = (
            {"video_x": -1},
            {"video_y": 101},
            {"video_width": 0},
            {"video_height": 301},
            {"video_rotation": -181},
            {"video_rotation": 181},
        )

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    SceneSettingsUpdate(**values)


if __name__ == "__main__":
    unittest.main()
