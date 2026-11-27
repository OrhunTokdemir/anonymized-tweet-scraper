"""Where a built program keeps its files (source / portable / standard)."""

import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import __version__, paths  # noqa: E402

HOME = Path("/home/ayse")


class ModeTests(unittest.TestCase):
    def test_source_when_not_frozen(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "portable").touch()  # ignored when not frozen
            self.assertEqual(paths.detect_mode(False, Path(d)), "source")

    def test_portable_marker(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(paths.detect_mode(True, Path(d)), "standard")
            (Path(d) / "portable").touch()
            self.assertEqual(paths.detect_mode(True, Path(d)), "portable")

    def test_portable_keeps_everything_in_its_folder(self):
        with tempfile.TemporaryDirectory() as d:
            exe_dir = Path(d)
            (exe_dir / "portable").touch()
            mode, app_dir, out = paths.resolve(True, exe_dir, "linux", {}, HOME)
            self.assertEqual((mode, app_dir, out), ("portable", exe_dir, exe_dir / "data"))

    def test_standard_linux(self):
        with tempfile.TemporaryDirectory() as d:
            mode, app_dir, out = paths.resolve(True, Path(d), "linux", {"XDG_CONFIG_HOME": d}, HOME)
        self.assertEqual(mode, "standard")
        self.assertEqual(app_dir, HOME / ".local/share/anonymized-tweet-scraper")
        self.assertEqual(out, HOME / "Documents" / "anonymized-posts")

    def test_standard_linux_reads_user_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "user-dirs.dirs").write_text(
                '# comment\nXDG_DESKTOP_DIR="$HOME/Masaüstü"\nXDG_DOCUMENTS_DIR="$HOME/Belgeler"\n',
                encoding="utf-8")
            _, _, out = paths.resolve(True, Path(d), "linux", {"XDG_CONFIG_HOME": d}, HOME)
        self.assertEqual(out, HOME / "Belgeler" / "anonymized-posts")


class LocationTests(unittest.TestCase):
    def test_xdg_data_home(self):
        self.assertEqual(paths.user_data_dir("linux", {"XDG_DATA_HOME": "/data/x"}, HOME),
                         Path("/data/x/anonymized-tweet-scraper"))
        # relative values are invalid per the XDG spec and ignored
        self.assertEqual(paths.user_data_dir("linux", {"XDG_DATA_HOME": "rel"}, HOME),
                         HOME / ".local/share/anonymized-tweet-scraper")

    def test_windows_appdata(self):
        self.assertEqual(paths.user_data_dir("win32", {"APPDATA": "C:/Users/ayse/AppData/Roaming"}, HOME),
                         Path("C:/Users/ayse/AppData/Roaming/anonymized-tweet-scraper"))
        self.assertEqual(paths.user_data_dir("win32", {}, HOME),
                         HOME / "AppData" / "Roaming" / "anonymized-tweet-scraper")

    def test_user_dirs_parsing(self):
        self.assertEqual(paths.xdg_documents_dir('XDG_DOCUMENTS_DIR="$HOME/Belgeler"', HOME), HOME / "Belgeler")
        self.assertEqual(paths.xdg_documents_dir('XDG_DOCUMENTS_DIR="/srv/docs"', HOME), Path("/srv/docs"))
        self.assertIsNone(paths.xdg_documents_dir('XDG_DOCUMENTS_DIR="$HOME/"', HOME))  # = "not set"
        self.assertIsNone(paths.xdg_documents_dir("", HOME))
        self.assertIsNone(paths.xdg_documents_dir(None, HOME))

    def test_output_dir_setting_wins(self):
        self.assertEqual(paths.output_dir(""), paths.DEFAULT_OUTPUT_DIR)
        absolute = Path(tempfile.gettempdir()) / "out"  # absolute on every OS
        self.assertEqual(paths.output_dir(str(absolute)), absolute)
        self.assertEqual(paths.output_dir("rel"), paths.APP_DIR / "rel")


class CliTests(unittest.TestCase):
    def run_main(self, *args):
        from scraper.tui import main

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_version(self):
        self.assertEqual(self.run_main("--version"), (0, f"anonymized-tweet-scraper {__version__}\n", ""))

    def test_paths(self):
        code, out, _ = self.run_main("--paths")
        self.assertEqual(code, 0)
        self.assertEqual([line.split(":")[0] for line in out.splitlines()],
                         ["Mode", "Settings & accounts", "CSV output", "Terms of use"])

    def test_terms_flag(self):
        code, out, _ = self.run_main("--terms")
        self.assertEqual(code, 0)
        self.assertIn("## Türkçe", out)

    def test_unknown_flag(self):
        code, out, err = self.run_main("--scrape-everything")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("Usage:", err)

    def test_version_matches_citation(self):
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertEqual(re.search(r"^version:\s*(\S+)", cff, re.M).group(1), __version__)


if __name__ == "__main__":
    unittest.main()
