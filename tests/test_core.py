import json
import random
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qiangjing.config import ConfigStore, PetConfig
from qiangjing.geometry import CORNERS, QUARTER_TURNS, corner_position, quarter_turns
from qiangjing.logic import describe_status, format_seconds, next_corner, screen_menu_label
from qiangjing.paths import SPRITE


class GeometryTest(unittest.TestCase):
    def test_window_sits_flush_in_each_corner(self):
        area = (0, 0, 1920, 1080)
        width, height = 320, 300
        self.assertEqual(corner_position("tl", area, width, height), (0, 0))
        self.assertEqual(corner_position("tr", area, width, height), (1920 - 320, 0))
        self.assertEqual(corner_position("bl", area, width, height), (0, 1080 - 300))
        self.assertEqual(
            corner_position("br", area, width, height),
            (1920 - 320, 1080 - 300),
        )

    def test_flush_on_offset_screen(self):
        area = (40, 80, 1000, 700)
        width, height = 200, 150
        self.assertEqual(corner_position("tl", area, width, height), (40, 80))
        self.assertEqual(corner_position("tr", area, width, height), (40 + 1000 - 200, 80))
        self.assertEqual(corner_position("bl", area, width, height), (40, 80 + 700 - 150))
        self.assertEqual(
            corner_position("br", area, width, height),
            (40 + 1000 - 200, 80 + 700 - 150),
        )
        for corner in CORNERS:
            x, y = corner_position(corner, area, width, height)
            self.assertGreaterEqual(x, area[0])
            self.assertGreaterEqual(y, area[1])
            self.assertLessEqual(x + width, area[0] + area[2])
            self.assertLessEqual(y + height, area[1] + area[3])

    def test_quarter_turns_pin_the_right_angle(self):
        self.assertEqual(QUARTER_TURNS, {"tl": 1, "tr": 2, "bl": 0, "br": 3})
        for corner, turns in QUARTER_TURNS.items():
            self.assertEqual(quarter_turns(corner), turns)

    def test_unknown_corner_rejected(self):
        with self.assertRaises(ValueError):
            corner_position("middle", (0, 0, 100, 100), 10, 10)
        with self.assertRaises(ValueError):
            quarter_turns("middle")


class LogicTest(unittest.TestCase):
    def test_next_corner_always_changes_and_can_reach_each(self):
        rng = random.Random(1)
        seen = {corner: set() for corner in CORNERS}
        for _ in range(80):
            for corner in CORNERS:
                nxt = next_corner(corner, rng)
                self.assertNotEqual(nxt, corner)
                self.assertIn(nxt, CORNERS)
                seen[corner].add(nxt)
        for corner in CORNERS:
            self.assertEqual(seen[corner], set(CORNERS) - {corner})

    def test_format_seconds(self):
        self.assertEqual(format_seconds(8), "8 秒")
        self.assertEqual(format_seconds(60), "1 分钟")
        self.assertEqual(format_seconds(61), "1 分 1 秒")
        self.assertEqual(format_seconds(90), "1 分 30 秒")

    def test_screen_menu_label(self):
        self.assertEqual(screen_menu_label(r"\\.\DISPLAY1", is_primary=True, index=0), "主屏幕")
        self.assertEqual(screen_menu_label(r"\\.\DISPLAY2", is_primary=False, index=1), "屏幕 2")
        self.assertEqual(
            screen_menu_label("BenQ EW3270U", is_primary=False, index=1),
            "BenQ EW3270U",
        )

    def test_status_copy(self):
        self.assertEqual(
            describe_status("tl", paused=True, phase="idle", remaining_ms=5000)[0],
            "左上角 · 已暂停",
        )
        self.assertEqual(
            describe_status("br", paused=False, phase="moving", remaining_ms=5000)[0],
            "右下角 · 正在出现",
        )
        self.assertEqual(
            describe_status("tr", paused=False, phase="idle", remaining_ms=10000),
            ("右上角 · 10 秒后换角", "green"),
        )
        self.assertEqual(
            describe_status("bl", paused=False, phase="idle", remaining_ms=90000)[0],
            "左下角 · 1 分 30 秒后换角",
        )
        self.assertEqual(
            describe_status("tl", paused=False, phase="idle", remaining_ms=0)[0],
            "左上角 · 马上换角",
        )
        self.assertEqual(
            describe_status("tl", paused=True, phase="idle", remaining_ms=1000)[1],
            "amber",
        )


class ConfigTest(unittest.TestCase):
    def test_roundtrip_and_clamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            store = ConfigStore(path)
            saved = store.save(PetConfig(interval_sec=9999, size=10, peek=5, paused=True))
            self.assertEqual(saved.interval_sec, 300)
            self.assertEqual(saved.size, 160)
            self.assertEqual(saved.peek, 1.0)
            self.assertTrue(saved.paused)
            self.assertEqual(saved.screen_name, "")
            loaded = store.load()
            self.assertEqual(loaded, saved)

    def test_screen_name_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            store = ConfigStore(path)
            saved = store.save(PetConfig(screen_name="BenQ EW3270U"))
            self.assertEqual(store.load().screen_name, "BenQ EW3270U")
            self.assertEqual(saved.screen_name, "BenQ EW3270U")

    def test_partial_and_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"interval_sec": 4}), encoding="utf-8")
            loaded = ConfigStore(path).load()
            self.assertEqual(loaded.interval_sec, 4)
            self.assertEqual(loaded.size, PetConfig().size)
            path.write_text("{", encoding="utf-8")
            self.assertEqual(ConfigStore(path).load(), PetConfig())

    def test_string_pause_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"paused": "false"}), encoding="utf-8")
            self.assertFalse(ConfigStore(path).load().paused)


class RotationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_clockwise_quarters_keep_the_bottom_left_pixel(self):
        from PySide6.QtGui import QColor, QImage, QPixmap

        from qiangjing.pet import rotate_quarters

        width, height = 5, 7
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        image.setPixelColor(0, height - 1, QColor(255, 0, 0, 255))
        image.setPixelColor(0, 0, QColor(0, 255, 0, 255))
        image.setPixelColor(width - 1, 0, QColor(0, 0, 255, 255))
        image.setPixelColor(width - 1, height - 1, QColor(255, 255, 0, 255))
        source = QPixmap.fromImage(image)

        still = rotate_quarters(source, 0)
        self.assertEqual(still.size(), source.size())
        self.assertEqual(still.toImage().pixelColor(0, height - 1), QColor(255, 0, 0, 255))

        turned = {
            1: (height, width, 0, 0),
            2: (width, height, width - 1, 0),
            3: (height, width, height - 1, width - 1),
        }
        for turns, (out_w, out_h, x, y) in turned.items():
            result = rotate_quarters(source, turns).toImage()
            self.assertEqual((result.width(), result.height()), (out_w, out_h), turns)
            self.assertEqual(result.pixelColor(x, y), QColor(255, 0, 0, 255), turns)
            self.assertEqual(result.pixelColor(x, y).alpha(), 255, turns)

    def test_scaled_screen_keeps_every_edge_flush(self):
        from PySide6.QtGui import QColor, QImage, QPixmap

        from qiangjing.pet import rotate_quarters

        width, height = 8, 6
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(10, 20, 30, 255))
        source = QPixmap.fromImage(image)
        source.setDevicePixelRatio(2)
        for turns, out_w, out_h in ((1, height, width), (2, width, height), (3, height, width)):
            result = rotate_quarters(source, turns)
            self.assertEqual(result.devicePixelRatio(), 2, turns)
            out = result.toImage()
            self.assertEqual((out.width(), out.height()), (out_w, out_h), turns)
            for x in range(out.width()):
                self.assertEqual(out.pixelColor(x, 0).alpha(), 255, turns)
                self.assertEqual(out.pixelColor(x, out.height() - 1).alpha(), 255, turns)
            for y in range(out.height()):
                self.assertEqual(out.pixelColor(0, y).alpha(), 255, turns)
                self.assertEqual(out.pixelColor(out.width() - 1, y).alpha(), 255, turns)

    def test_sprite_right_angle_is_solid(self):
        from PySide6.QtGui import QImage

        image = QImage(str(SPRITE))
        self.assertFalse(image.isNull())
        height = image.height()
        self.assertEqual(image.pixelColor(0, height - 1).alpha(), 255)
        self.assertEqual(image.pixelColor(0, height - 2).alpha(), 255)
        self.assertEqual(image.pixelColor(1, height - 1).alpha(), 255)


class SpriteTest(unittest.TestCase):
    def test_sprite_is_hd_and_transparent(self):
        data = SPRITE.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", data[16:24])
        self.assertGreaterEqual(width, 1400)
        self.assertGreaterEqual(height, 1400)
        self.assertEqual(data[24], 8)  # bit depth
        self.assertEqual(data[25], 6)  # RGBA
        self.assertGreater(SPRITE.stat().st_size, 500_000)


if __name__ == "__main__":
    unittest.main()
