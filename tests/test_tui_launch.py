"""Starting without a terminal (e.g. double-click): reopen in a terminal instead of spinning on stdin."""

import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper import tui  # noqa: E402


def which_only(*present):
    return lambda name: f"/usr/bin/{name}" if name in present else None


class TerminalCommandTests(unittest.TestCase):
    PROG = ["/opt/app/anonymized-tweet-scraper"]

    def test_prefers_terminal_env(self):
        cmd = tui._terminal_command(which_only("foot", "xterm"), {"TERMINAL": "foot"}, self.PROG)
        self.assertEqual(cmd, ["foot", "-e", *self.PROG])

    def test_ignores_missing_terminal_env(self):
        cmd = tui._terminal_command(which_only("xterm"), {"TERMINAL": "nope"}, self.PROG)
        self.assertEqual(cmd, ["/usr/bin/xterm", "-e", *self.PROG])

    def test_list_order_and_args(self):
        cmd = tui._terminal_command(which_only("gnome-terminal", "xterm"), {}, self.PROG)
        self.assertEqual(cmd, ["/usr/bin/gnome-terminal", "--", *self.PROG])

    def test_none_found(self):
        self.assertIsNone(tui._terminal_command(which_only(), {}, self.PROG, "linux"))

    def test_windows_uses_windows_terminal(self):
        with mock.patch("os.getcwd", return_value=r"C:\work;dir"):
            cmd = tui._terminal_command(which_only("wt.exe"), {}, [r"C:\a;b\app.exe"], "win32")
        self.assertEqual(cmd, ["/usr/bin/wt.exe", "-d", r"C:\work\;dir", r"C:\a\;b\app.exe"])

    def test_windows_without_wt(self):
        self.assertIsNone(tui._terminal_command(which_only("xterm"), {}, self.PROG, "win32"))


class MainWithoutTerminalTests(unittest.TestCase):
    """Linux behaviour (runs on every CI platform: sys.platform is patched)."""

    def setUp(self):
        patches = [
            mock.patch("sys.platform", "linux"),
            mock.patch.object(tui, "_has_terminal", return_value=False),
            mock.patch.object(tui, "ScraperApp"),
            mock.patch.object(tui, "ensure_app_dir"),
            mock.patch("subprocess.Popen"),
            mock.patch("subprocess.run"),
            mock.patch.dict(os.environ, {}, clear=False),
        ]
        mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        _, _, self.app, _, self.popen, self.run, _ = mocks
        os.environ.pop(tui.RELAUNCH_ENV, None)
        os.environ.pop("TERMINAL", None)

    def test_relaunches_in_terminal(self):
        with mock.patch("shutil.which", which_only("xterm")):
            self.assertEqual(tui.main([]), 0)
        self.app.assert_not_called()
        cmd = self.popen.call_args.args[0]
        self.assertEqual(cmd[:2], ["/usr/bin/xterm", "-e"])
        self.assertEqual(cmd[2:], tui._own_command())
        self.assertEqual(self.popen.call_args.kwargs["env"][tui.RELAUNCH_ENV], "1")

    def test_no_terminal_found_exits(self):
        with mock.patch("shutil.which", which_only("notify-send")), \
                mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(tui.main([]), 1)
        self.app.assert_not_called()
        self.popen.assert_not_called()
        self.assertIn("terminal app", err.getvalue())
        self.run.assert_called_once()  # desktop notification

    def test_no_second_relaunch(self):
        os.environ[tui.RELAUNCH_ENV] = "1"
        with mock.patch("shutil.which", which_only("xterm")), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(tui.main([]), 1)
        self.popen.assert_not_called()
        self.app.assert_not_called()

    def test_version_works_without_terminal(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(tui.main(["--version"]), 0)
        self.assertIn(tui.__version__, out.getvalue())
        self.popen.assert_not_called()


class WindowsLaunchTests(unittest.TestCase):
    def setUp(self):
        patches = [
            mock.patch("sys.platform", "win32"),
            mock.patch.dict(os.environ, {}, clear=False),
            mock.patch("subprocess.Popen"),
            mock.patch.object(tui, "_report_no_terminal"),
        ]
        mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        self.popen = mocks[2]
        for k in (tui.RELAUNCH_ENV, "WT_SESSION"):
            os.environ.pop(k, None)

    def should(self, count, wt=True, tty=True, frozen=True):
        with mock.patch.object(tui, "_has_terminal", return_value=tty), \
                mock.patch.object(tui, "_console_process_count", return_value=count), \
                mock.patch("shutil.which", which_only("wt.exe") if wt else which_only()), \
                mock.patch.object(sys, "frozen", frozen, create=True):
            return tui._should_relaunch()

    def test_double_click_into_old_console_relaunches(self):
        self.assertTrue(self.should(2))
        self.assertTrue(self.should(1, frozen=False))

    def test_started_from_a_shell_runs_in_place(self):
        self.assertFalse(self.should(3))
        self.assertFalse(self.should(2, frozen=False))

    def test_already_in_windows_terminal(self):
        os.environ["WT_SESSION"] = "x"
        self.assertFalse(self.should(2))

    def test_no_windows_terminal_installed(self):
        self.assertFalse(self.should(2, wt=False))

    def test_no_console_always_relaunches(self):
        self.assertTrue(self.should(0, wt=False, tty=False))

    def test_console_check_failure_runs_in_place(self):
        with mock.patch.object(tui, "_has_terminal", return_value=True), \
                mock.patch.object(tui, "_console_process_count", side_effect=OSError):
            self.assertFalse(tui._should_relaunch())

    def test_relaunch_with_windows_terminal(self):
        flags = {"CREATE_NO_WINDOW": 0x08000000, "CREATE_NEW_PROCESS_GROUP": 0x200}
        with mock.patch("shutil.which", which_only("wt.exe")), \
                mock.patch.multiple("subprocess", create=True, **flags):
            self.assertEqual(tui._relaunch_in_terminal(), 0)
        cmd = self.popen.call_args.args[0]
        self.assertEqual(cmd[:2], ["/usr/bin/wt.exe", "-d"])
        self.assertEqual(self.popen.call_args.kwargs["creationflags"], 0x08000200)
        self.assertEqual(self.popen.call_args.kwargs["env"][tui.RELAUNCH_ENV], "1")

    def test_relaunch_without_wt_opens_new_console(self):
        with mock.patch("shutil.which", which_only()), \
                mock.patch("subprocess.CREATE_NEW_CONSOLE", 0x10, create=True):
            self.assertEqual(tui._relaunch_in_terminal(), 0)
        self.assertEqual(self.popen.call_args.args[0], tui._own_command())
        self.assertEqual(self.popen.call_args.kwargs["creationflags"], 0x10)

    def test_frozen_relaunch_resets_pyinstaller_env(self):
        with mock.patch("shutil.which", which_only()), \
                mock.patch("subprocess.CREATE_NEW_CONSOLE", 0x10, create=True), \
                mock.patch.object(sys, "frozen", True, create=True):
            tui._relaunch_in_terminal()
        self.assertEqual(self.popen.call_args.kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")

    def test_no_second_relaunch(self):
        os.environ[tui.RELAUNCH_ENV] = "1"
        self.assertEqual(tui._relaunch_in_terminal(), 1)
        self.popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
