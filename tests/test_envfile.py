import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper.envfile import (  # noqa: E402
    clean_username,
    ensure_env,
    list_usernames,
    remove_account,
    set_setting,
    unset_setting,
    upsert_account,
    validate,
)

AUTH = "a" * 40
CT0 = "b1" * 80


class EnvFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = Path(self.tmp.name) / ".env"
        ensure_env(self.env, ROOT / ".env.example")  # the committed example, never the real .env

    def tearDown(self):
        self.tmp.cleanup()

    def text(self):
        return self.env.read_text(encoding="utf-8")

    def assert_private(self, path: Path) -> None:
        """POSIX: only the owner may read/write (0o600). Windows has no Unix
        permission bits (it reports 0o666); there the file lives in the user's
        own folder, so only check that our chmod didn't leave it read-only."""
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        else:
            self.assertTrue(os.access(path, os.W_OK))

    def test_created_from_example_private(self):
        self.assertIn("TW_ROTATE_EVERY=40", self.text())
        self.assert_private(self.env)
        self.assertEqual(list_usernames(self.env), [])  # placeholder doesn't count

    def test_fills_placeholder_slot(self):
        self.assertEqual(upsert_account(self.env, "alice", AUTH, CT0), "added")
        t = self.text()
        self.assertIn("TW_ACCOUNT_1_USERNAME=alice", t)
        self.assertIn(f'TW_ACCOUNT_1_COOKIES="auth_token={AUTH}; ct0={CT0}"', t)
        self.assertNotIn("your_twitter_username", t)
        self.assertIn("# Rotation / pacing", t)  # other content preserved

    def test_second_goes_to_empty_slot_then_append(self):
        upsert_account(self.env, "alice", AUTH, CT0)
        upsert_account(self.env, "bob", AUTH, CT0)
        upsert_account(self.env, "carol", AUTH, CT0, proxy="http://h:1")
        t = self.text()
        self.assertIn("TW_ACCOUNT_2_USERNAME=bob", t)
        self.assertIn("TW_ACCOUNT_3_USERNAME=carol", t)
        self.assertIn("TW_ACCOUNT_3_PROXY=http://h:1", t)
        self.assertEqual(list_usernames(self.env), ["alice", "bob", "carol"])
        self.assert_private(self.env)  # still private after rewrites

    def test_update_existing_keeps_proxy(self):
        upsert_account(self.env, "alice", AUTH, CT0, proxy="http://p:1")
        self.assertEqual(upsert_account(self.env, "ALICE", "c" * 40, CT0), "updated")
        t = self.text()
        self.assertIn("auth_token=" + "c" * 40, t)
        self.assertNotIn("auth_token=" + AUTH, t)
        self.assertIn("TW_ACCOUNT_1_PROXY=http://p:1", t)
        self.assertEqual(t.count("TW_ACCOUNT_1_USERNAME="), 1)

    def test_remove_renumbers(self):
        for name in ("alice", "bob", "carol"):
            upsert_account(self.env, name, AUTH, CT0)
        self.assertTrue(remove_account(self.env, "alice"))
        t = self.text()
        self.assertIn("TW_ACCOUNT_1_USERNAME=bob", t)
        self.assertIn("TW_ACCOUNT_2_USERNAME=carol", t)
        self.assertNotRegex(t, r"(?m)^TW_ACCOUNT_3_")
        self.assertNotIn("alice", t)
        self.assertFalse(remove_account(self.env, "nobody"))

    def test_missing_example(self):
        env = Path(self.tmp.name) / "other.env"
        ensure_env(env, Path(self.tmp.name) / "missing.example")
        upsert_account(env, "alice", AUTH, CT0)
        self.assertTrue(env.read_text().startswith("TW_ACCOUNT_1_USERNAME=alice"))


class SettingTests(unittest.TestCase):
    """OUTPUT_DIR and friends, always on a temporary copy of .env.example."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = Path(self.tmp.name) / ".env"
        ensure_env(self.env, ROOT / ".env.example")

    def tearDown(self):
        self.tmp.cleanup()

    def text(self):
        return self.env.read_text(encoding="utf-8")

    def test_set_new_then_replace(self):
        set_setting(self.env, "OUTPUT_DIR", "/tmp/one")
        set_setting(self.env, "OUTPUT_DIR", "/tmp/two")
        t = self.text()
        self.assertEqual(t.count("\nOUTPUT_DIR="), 1)
        self.assertIn("OUTPUT_DIR=/tmp/two", t)
        self.assertIn("# OUTPUT_DIR=", t)  # the commented example line is left alone
        self.assertIn("TW_ROTATE_EVERY=40", t)

    def test_value_with_spaces_is_quoted(self):
        set_setting(self.env, "OUTPUT_DIR", "/home/me/My Documents/out")
        self.assertIn('OUTPUT_DIR="/home/me/My Documents/out"', self.text())

    def test_unset(self):
        set_setting(self.env, "OUTPUT_DIR", "/tmp/x")
        self.assertTrue(unset_setting(self.env, "OUTPUT_DIR"))
        self.assertNotIn("\nOUTPUT_DIR=", self.text())
        self.assertFalse(unset_setting(self.env, "OUTPUT_DIR"))

    def test_account_keys_and_bad_values_refused(self):
        with self.assertRaises(ValueError):
            set_setting(self.env, "TW_ACCOUNT_1_COOKIES", "x")
        with self.assertRaises(ValueError):
            set_setting(self.env, "output_dir", "x")
        with self.assertRaises(ValueError):
            set_setting(self.env, "OUTPUT_DIR", "a\nTW_ACCOUNT_9_USERNAME=evil")


class ValidateTests(unittest.TestCase):
    def test_clean_username(self):
        self.assertEqual(clean_username("@alice"), "alice")
        self.assertEqual(clean_username("https://x.com/alice/status/1"), "alice")

    def test_valid(self):
        self.assertEqual(validate("@alice_1", AUTH, CT0), "alice_1")

    def test_invalid(self):
        for args in (("al ice", AUTH, CT0), ("alice", "xyz", CT0), ("alice", AUTH, "short"),
                     ("alice", AUTH + ";", CT0), ("alice", AUTH, CT0, "http://a b")):
            with self.assertRaises(ValueError):
                validate(*args)


if __name__ == "__main__":
    unittest.main()
