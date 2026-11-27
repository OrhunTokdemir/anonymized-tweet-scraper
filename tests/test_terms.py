"""First-run terms of use: the text, local acceptance per version, and the app screen."""

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import terms  # noqa: E402


class TermsTextTests(unittest.TestCase):
    def test_file_has_version_and_both_languages(self):
        version, text = terms.load_terms(ROOT / terms.TERMS_FILE)
        self.assertGreaterEqual(version, 1)
        self.assertNotIn("terms-version", text)  # the marker isn't shown to users
        self.assertIn("## English", text)
        self.assertIn("## Türkçe", text)
        self.assertIn("not legal advice", text)
        self.assertIn("hukuki tavsiye değildir", text)
        self.assertIn("pseudonymized, not anonymous", text)

    def test_missing_version_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "t.md")
            p.write_text("# no version\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                terms.load_terms(p)


class AcceptanceTests(unittest.TestCase):
    def test_round_trip_and_new_version(self):
        with tempfile.TemporaryDirectory() as d:
            app_dir = Path(d) / "app"  # created on first acceptance
            self.assertFalse(terms.is_accepted(app_dir, 1))
            terms.record_acceptance(app_dir, 1)
            self.assertTrue(terms.is_accepted(app_dir, 1))
            self.assertFalse(terms.is_accepted(app_dir, 2))  # changed terms -> ask again
            self.assertEqual(terms.accepted_info(app_dir)[0], 1)

    def test_garbage_file_counts_as_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, terms.ACCEPT_FILE).write_text("version=abc\n", encoding="utf-8")
            self.assertFalse(terms.is_accepted(Path(d), 1))


class TermsScreenTests(unittest.TestCase):
    """Drive the real app headless, with APP_DIR pointed at a temporary folder."""

    def run_app(self, steps):
        from scraper import tui

        async def go(app_dir):
            app = tui.ScraperApp()
            async with app.run_test() as pilot:
                await pilot.pause()
                await steps(app, pilot)
                await pilot.pause()
                return app

        with tempfile.TemporaryDirectory() as d, mock.patch.object(tui, "APP_DIR", Path(d)):
            app = asyncio.run(go(Path(d)))
            return app, terms.is_accepted(Path(d), app.terms_version)

    def test_screen_shown_and_quit_records_nothing(self):
        async def steps(app, pilot):
            self.assertIsInstance(app.screen, tui_mod().TermsScreen)
            await pilot.click("#terms-quit")

        app, accepted = self.run_app(steps)
        self.assertFalse(accepted)
        self.assertFalse(app.terms_ok)

    def test_accept_needs_checkbox_then_records(self):
        async def steps(app, pilot):
            screen = app.screen
            self.assertTrue(screen.query_one("#terms-accept").disabled)
            app.action_start()  # ctrl+s behind the modal must not start a run or stack screens
            await pilot.pause()
            self.assertFalse(app.busy)
            self.assertEqual(sum(isinstance(s, tui_mod().TermsScreen) for s in app.screen_stack), 1)
            screen.query_one("#terms-check").value = True
            await pilot.pause()
            self.assertFalse(screen.query_one("#terms-accept").disabled)
            await pilot.click("#terms-accept")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, tui_mod().TermsScreen)

        app, accepted = self.run_app(steps)
        self.assertTrue(accepted)
        self.assertTrue(app.terms_ok)


def tui_mod():
    from scraper import tui
    return tui


if __name__ == "__main__":
    unittest.main()
