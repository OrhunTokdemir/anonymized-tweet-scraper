import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.anonymize import anonymize_query, anonymize_text  # noqa: E402
from scraper.output import slugify  # noqa: E402


class AnonymizeTests(unittest.TestCase):
    def test_twitter_mentions(self):
        self.assertEqual(
            anonymize_text("RT @elonmusk: hi @ali_veli and @AhmetYılmaz!"),
            "RT @username: hi @username and @username!",
        )

    def test_eksi_bkz_with_spaces(self):
        self.assertEqual(
            anonymize_text("katılıyorum (bkz: @deli dolu yazar) aynen"),
            "katılıyorum (bkz: @username) aynen",
        )

    def test_known_names_bare(self):
        out = anonymize_text("ssg haklı, Ahmet Yılmaz da öyle dedi", {"ssg", "Ahmet Yılmaz"})
        self.assertEqual(out, "#username haklı, #username da öyle dedi")

    def test_known_name_not_inside_words(self):
        self.assertEqual(anonymize_text("penalti", {"pena"}), "penalti")

    def test_short_names_ignored(self):
        self.assertEqual(anonymize_text("ab cd", {"ab"}), "ab cd")

    def test_email_and_phone(self):
        out = anonymize_text("yaz: foo.bar@example.com veya +90 532 123 45 67")
        self.assertEqual(out, "yaz: [email] veya [phone]")

    def test_year_not_phone(self):
        self.assertEqual(anonymize_text("2026 yılında 15 kişi"), "2026 yılında 15 kişi")

    def test_profile_and_status_urls(self):
        out = anonymize_text(
            "see https://x.com/someone/status/123 and https://eksisozluk.com/biri/ssg"
        )
        self.assertEqual(out, "see https://x.com/username and https://eksisozluk.com/biri/username")

    def test_hashtag_and_search_urls_kept(self):
        text = "#python https://x.com/hashtag/python"
        self.assertEqual(anonymize_text(text), text)

    def test_html_stripped(self):
        self.assertEqual(anonymize_text("a <b>kalın</b> &amp; b"), "a kalın & b")

    def test_query_operators(self):
        self.assertEqual(anonymize_query("from:someone to:other kedi"), "from:username to:username kedi")

    def test_profile_links_of_users_named_like_x_pages(self):
        # regression: usernames starting with "home"/"search" used to slip through
        self.assertEqual(anonymize_text("https://x.com/homer_s/status/5"), "https://x.com/username")
        self.assertEqual(anonymize_text("https://x.com/searchlight"), "https://x.com/username")
        self.assertEqual(anonymize_text("https://twitter.com/explorer1"), "https://x.com/username")

    def test_x_own_pages_kept(self):
        for url in ("https://x.com/search?q=kedi", "https://x.com/home", "https://x.com/explore",
                    "https://x.com/hashtag/kedi", "https://x.com/i/lists/123"):
            self.assertEqual(anonymize_text(url), url)

    def test_phone_numbers(self):
        self.assertEqual(
            anonymize_text("ara +90 532 123 45 67 / 0532-123-4567 / (0212) 555 44 33"),
            "ara [phone] / [phone] / [phone]",
        )

    def test_dates_and_numbers_are_not_phones(self):
        for text in ("2026-11-15 14:30 tarihinde", "15.11.2026 14:30", "nüfus 85.372.377 kişi",
                     "skor 3-2, saat 14.30", "2026-11-15T14:30:02"):
            self.assertEqual(anonymize_text(text), text)
        self.assertEqual(anonymize_query("kedi since:2026-01-01 until:2026-02-01"),
                         "kedi since:2026-01-01 until:2026-02-01")

    def test_phone_after_date_still_redacted(self):
        out = anonymize_text("2026-11-15 0532 123 45 67")
        self.assertIn("[phone]", out)
        self.assertNotIn("0532", out)

    def test_docs_worked_example(self):
        # keep in sync with docs/anonymization.md
        tw = ("@ayse_k Selin Demir dün söyledi, bilgi için selin.demir@example.com ya da "
              "+90 532 123 45 67. Profil: https://x.com/selindemir_42/status/1234567890 #yapayzeka")
        self.assertEqual(
            anonymize_text(tw, {"selindemir_42", "Selin Demir", "ayse_k", "Ayşe K."}),
            "@username #username dün söyledi, bilgi için [email] ya da [phone]. "
            "Profil: https://x.com/username #yapayzeka",
        )
        ek = ("katılıyorum. (bkz: @kuzey_yildizi) ayrıca kuzey_yildizi bu konuda haklıydı. "
              "https://eksisozluk.com/biri/kuzey_yildizi")
        self.assertEqual(
            anonymize_text(ek, {"kuzey_yildizi"}),
            "katılıyorum. (bkz: @username) ayrıca #username bu konuda haklıydı. "
            "https://eksisozluk.com/biri/username",
        )

    def test_slugify(self):
        self.assertEqual(slugify("Yapay Zekâ lang:tr", "çılgın"), "yapay-zeka-lang-tr-cilgin")
        self.assertEqual(slugify("https://eksisozluk.com/python--109286"), "python-109286")
        self.assertEqual(slugify(""), "posts")


if __name__ == "__main__":
    unittest.main()
