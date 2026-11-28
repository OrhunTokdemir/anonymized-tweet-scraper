"""First-run responsible-use notice: the text, the local "read" record per version, and the app screen."""

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import guidelines  # noqa: E402


class GuidelinesTextTests(unittest.TestCase):
    def test_file_has_version_and_both_languages(self):
        version, text = guidelines.load_guidelines(ROOT / guidelines.GUIDELINES_FILE)
        self.assertGreaterEqual(version, 1)
        self.assertNotIn("guidelines-version", text)  # the marker isn't shown to users
        self.assertIn("## English", text)
        self.assertIn("## Türkçe", text)
        self.assertIn("not legal advice", text)
        self.assertIn("hukuki tavsiye değildir", text)
        self.assertIn("pseudonymized, not anonymous", text)
        self.assertIn("does not modify or add conditions to the MIT License", text)

    def test_no_binding_language(self):
        _, text = guidelines.load_guidelines(ROOT / guidelines.GUIDELINES_FILE)
        lower = text.lower()
        for phrase in ("you accept", "do not accept", "you must", "you may not", "limited to",
                       "commercial", "kabul ediyorsunuz", "kabul etmiyorsanız"):
            self.assertNotIn(phrase, lower)

    def test_missing_version_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "t.md")
            p.write_text("# no version\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                guidelines.load_guidelines(p)


class ReadRecordTests(unittest.TestCase):
    def test_round_trip_and_new_version(self):
        with tempfile.TemporaryDirectory() as d:
            app_dir = Path(d) / "app"  # created on first dismissal
            self.assertFalse(guidelines.is_read(app_dir, 1))
            guidelines.record_read(app_dir, 1)
            self.assertTrue(guidelines.is_read(app_dir, 1))
            self.assertFalse(guidelines.is_read(app_dir, 2))  # changed text -> shown again
            self.assertEqual(guidelines.read_info(app_dir)[0], 1)

    def test_garbage_file_counts_as_not_read(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, guidelines.READ_FILE).write_text("version=abc\n", encoding="utf-8")
            self.assertFalse(guidelines.is_read(Path(d), 1))


class GuidelinesScreenTests(unittest.TestCase):
    """Drive the real app headless, with APP_DIR pointed at a temporary folder."""

    def run_app(self, steps):
        from scraper import tui

        async def go():
            app = tui.ScraperApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                await steps(app, pilot)
                await pilot.pause()
                return app

        with tempfile.TemporaryDirectory() as d, mock.patch.object(tui, "APP_DIR", Path(d)):
            app = asyncio.run(go())
            return app, guidelines.is_read(Path(d), app.guidelines_version)

    def test_notice_shown_then_dismissed_and_recorded(self):
        async def steps(app, pilot):
            tui = tui_mod()
            self.assertIsInstance(app.screen, tui.GuidelinesScreen)
            app.action_start()  # ctrl+s behind the notice must not start a run or stack screens
            await pilot.pause()
            self.assertFalse(app.busy)
            self.assertEqual(sum(isinstance(s, tui.GuidelinesScreen) for s in app.screen_stack), 1)
            await pilot.click("#guidelines-ok")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, tui.GuidelinesScreen)

        app, read = self.run_app(steps)
        self.assertTrue(read)
        self.assertTrue(app.guidelines_read)

    def test_escape_also_dismisses(self):
        async def steps(app, pilot):
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, tui_mod().GuidelinesScreen)

        app, read = self.run_app(steps)
        self.assertTrue(read)


def tui_mod():
    from scraper import tui
    return tui


if __name__ == "__main__":
    unittest.main()
