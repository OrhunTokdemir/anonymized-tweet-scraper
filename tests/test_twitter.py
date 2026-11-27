"""Account watch (ban handling) and the rate-limit log filter, with fakes (no network)."""

import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper import twitter  # noqa: E402
from scraper.models import Post  # noqa: E402
from scraper.tui import library_log_text  # noqa: E402
from scraper.twitter import AccountsExhausted, AccountWatch  # noqa: E402


class FakePool:
    def __init__(self, states):
        self.states = states  # list of {username: active} snapshots, one per call
        self.calls = 0

    async def accounts_info(self):
        snap = self.states[min(self.calls, len(self.states) - 1)]
        self.calls += 1
        return [{"username": u, "active": a, "total_req": 1, "error_msg": "" if a else "(64) suspended"}
                for u, a in snap.items()]


def fake_api(states, results=()):
    """`results`: one list of fake tweets per search call."""
    api = types.SimpleNamespace(pool=FakePool(states))
    batches = iter(results)

    async def search(q, limit, kv):
        for tw in next(batches, []):
            yield tw
    api.search = search
    return api


def run(coro):
    return asyncio.run(coro)


class AccountWatchTests(unittest.TestCase):
    def test_logs_deactivated_account_and_continues(self):
        log = []
        watch = AccountWatch(fake_api([{"a": True, "b": True}, {"a": True, "b": False}]), log.append)
        run(watch.check())
        run(watch.check())
        self.assertTrue(any("@b was deactivated" in m and "1 active" in m for m in log))

    def test_raises_when_no_account_is_left(self):
        watch = AccountWatch(fake_api([{"a": True}, {"a": False}]), lambda m: None)
        run(watch.check())
        with self.assertRaises(AccountsExhausted):
            run(watch.check())

    def test_periodic_summary(self):
        log = []
        watch = AccountWatch(fake_api([{"a": True, "b": True}]), log.append)
        for _ in range(AccountWatch.SUMMARY_EVERY):
            run(watch.check())
        self.assertTrue(any(m.startswith("[dim]Accounts: 2 active") for m in log))


class FetchSearchBanTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(twitter, "_to_post",
                                    lambda tw, q, m: Post("twitter", m, q, "t", str(tw.id)))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.settings = types.SimpleNamespace(rotate_every=2, delay_min=0, delay_max=0)

    def test_empty_chunk_with_all_accounts_banned_is_an_error_not_the_end(self):
        tweets = [types.SimpleNamespace(id=i) for i in (10, 9)]
        api = fake_api([{"a": True}, {"a": False}], results=[tweets, []])
        got = []
        with self.assertRaises(AccountsExhausted):
            run(twitter.fetch_search(api, "q", 10, "Latest", self.settings, lambda m: None, got.extend))
        self.assertEqual(len(got), 2)  # rows before the ban were emitted (saved)

    def test_empty_chunk_with_active_accounts_is_the_end(self):
        tweets = [types.SimpleNamespace(id=i) for i in (10, 9)]
        api = fake_api([{"a": True}], results=[tweets, []])
        n = run(twitter.fetch_search(api, "q", 10, "Latest", self.settings, lambda m: None, lambda b: None))
        self.assertEqual(n, 2)


REFUSED = {
    "data": {"search_by_raw_query": {"search_timeline": {"timeline": {"instructions": []}}}},
    "errors": [{"message": "InvalidArgument: ProductDisabled: Closed gate stopped execution of the "
                           "pipeline (LatestTabSrpDenySuspendedUsers)"}],
}
NORMAL = {"data": {"search_by_raw_query": {"search_timeline": {"timeline": {"instructions": [
    {"type": "TimelineAddEntries", "entries": [{"entryId": "tweet-1"}, {"entryId": "cursor-bottom"}]}]}}}}}


class SearchRefusalTests(unittest.TestCase):
    def test_suspended_gate_is_a_refusal(self):
        msg = twitter.search_refusal(REFUSED)
        self.assertIn("suspended or restricted", msg)
        self.assertIn("LatestTabSrpDenySuspendedUsers", msg)

    def test_normal_page_is_fine(self):
        self.assertIsNone(twitter.search_refusal(NORMAL))

    def test_other_error_with_empty_timeline_is_a_refusal(self):
        obj = {"data": {}, "errors": [{"message": "(-1) Internal server error"}]}
        self.assertEqual(twitter.search_refusal(obj), "X said: (-1) Internal server error")

    def test_warning_alongside_results_is_fine(self):
        self.assertIsNone(twitter.search_refusal({**NORMAL, "errors": [{"message": "minor"}]}))


class CheckAccountTests(unittest.TestCase):
    """The profile lookup alone used to give ✅ for accounts X won't let search."""

    def check(self, user, search_reply):
        class FakeAPI:
            def __init__(self, *a, **k):
                self.pool = types.SimpleNamespace(add_account=self._noop, accounts_info=self._info)

            async def _noop(self, *a, **k):
                pass

            async def _info(self):
                return [{"error_msg": ""}]

            async def user_by_login(self, login):
                return user

            async def _gql_item(self, op, kv, toggles=None):
                return types.SimpleNamespace(json=lambda: search_reply)

        acc = types.SimpleNamespace(username="tester", password="", email="", email_password="",
                                    proxy="", cookies="auth_token=a; ct0=b")
        settings = types.SimpleNamespace(accounts=[acc])
        with mock.patch.object(twitter, "API", FakeAPI):
            return run(twitter.check_account(settings, "tester", timeout=5))

    def test_lookup_ok_but_search_refused_is_not_ok(self):
        ok, msg = self.check(object(), REFUSED)
        self.assertFalse(ok)
        self.assertIn("refuses search", msg)

    def test_lookup_and_search_ok(self):
        self.assertEqual(self.check(object(), NORMAL), (True, "works"))

    def test_rejected_cookies(self):
        ok, msg = self.check(None, NORMAL)
        self.assertFalse(ok)
        self.assertIn("rejected the cookies", msg)


class EmptySearchHintTests(unittest.TestCase):
    def test_zero_results_logs_a_hint(self):
        log = []
        settings = types.SimpleNamespace(rotate_every=2, delay_min=0, delay_max=0)
        n = run(twitter.fetch_search(fake_api([{"a": True}], results=[[]]), "q", 10, "Latest",
                                     settings, log.append, lambda b: None))
        self.assertEqual(n, 0)
        self.assertTrue(any("refusing search" in m for m in log))


class LibraryLogTextTests(unittest.TestCase):
    def test_rate_limit_wait_is_shown(self):
        text = library_log_text(
            "INFO", 'No account available for queue "SearchTimeline". Next available at 2026-11-17 01:22:10+00:00')
        self.assertIn("rate limit", text)
        self.assertIn("01:22", text)

    def test_other_info_is_hidden(self):
        self.assertIsNone(library_log_text("INFO", "Account x added successfully (active=True)"))

    def test_warnings_pass(self):
        self.assertIn("Ban detected", library_log_text("WARNING", "Ban detected: 403 - ..."))


if __name__ == "__main__":
    unittest.main()
