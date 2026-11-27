import json
import unittest
from pathlib import Path
from themes.engine import AVAILABLE_THEMES
from ui.hawk_emblem import resolve_logo_path

ROOT = Path(__file__).resolve().parent.parent


class TestHawkeye(unittest.TestCase):
    def test_all_six_master_themes_exist_and_valid(self):
        self.assertEqual(len(AVAILABLE_THEMES), 6)
        required_keys = {
            "bg_primary", "bg_secondary", "bg_surface", "bg_active",
            "border", "border_focus", "fg_primary", "fg_secondary",
            "fg_muted", "accent", "accent_fg", "terminal_bg",
            "terminal_fg", "cursor", "ansi",
        }
        for tid, _name in AVAILABLE_THEMES:
            path = ROOT / "themes" / f"{tid}.json"
            self.assertTrue(path.exists(), f"Missing theme file: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(required_keys.issubset(set(data["palette"].keys())))
            self.assertEqual(len(data["palette"]["ansi"]), 16)

    def test_logo_asset_exists(self):
        logo = resolve_logo_path()
        self.assertIsNotNone(logo)
        self.assertTrue(logo.exists())


if __name__ == "__main__":
    unittest.main()
