import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.anonymize import NAME_TOKEN, NameRedactor, names_pattern  # noqa: E402
from scraper.models import Post  # noqa: E402
from scraper.output import CsvStream, StreamClosed  # noqa: E402


def post(text, names=(), source="twitter", group=""):
    return Post(source=source, method="m", query="q", text=text, raw_id="x",
                names=set(names), sample_group=group)


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class CsvStreamTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_rows_hit_disk_before_finish(self):
        s = CsvStream(self.dir, "yapay zeka")
        s.add([post("bir"), post("iki")])
        self.assertEqual(len(read_rows(s.partial_path)), 2)
        s.finish()

    def test_name_seen_later_is_redacted_from_earlier_rows(self):
        s = CsvStream(self.dir, "q")
        s.add([post("Ahmet Yılmaz haklı")])
        s.add([post("ikinci", names={"Ahmet Yılmaz"})])
        rows = read_rows(s.finish())
        self.assertEqual(rows[0]["text"], f"{NAME_TOKEN} haklı")

    def test_final_name_counts_and_partial_removed(self):
        s = CsvStream(self.dir, "yapay zeka", prefix="offensive")
        s.add([post("a"), post("b")])
        s.add([post("c", source="eksisozluk")])
        path = s.finish()
        self.assertRegex(path.name, r"^\d{8}-\d{6}_offensive_tw2_eksi1_yapay-zeka\.csv$")
        self.assertFalse(s.partial_path.exists())
        self.assertEqual(sorted(p.name for p in Path(self.dir).iterdir()), [path.name])

    def test_incomplete_suffix(self):
        s = CsvStream(self.dir, "q")
        s.add([post("a")])
        self.assertTrue(s.finish(incomplete=True).name.endswith("_incomplete.csv"))

    def test_empty_stream_writes_nothing(self):
        s = CsvStream(self.dir, "q")
        self.assertIsNone(s.finish())
        self.assertEqual(list(Path(self.dir).iterdir()), [])

    def test_shuffle_renumbers_rows(self):
        s = CsvStream(self.dir, "q", shuffle=True)
        s.add([post(str(i)) for i in range(50)])
        rows = read_rows(s.finish())
        self.assertEqual([r["row"] for r in rows], [str(i) for i in range(1, 51)])
        self.assertEqual(sorted(int(r["text"]) for r in rows), list(range(50)))

    def test_add_after_finish_raises(self):
        s = CsvStream(self.dir, "q")
        s.add([post("a")])
        s.finish()
        with self.assertRaises(StreamClosed):
            s.add([post("b")])

    def test_groups_counted(self):
        s = CsvStream(self.dir, "q")
        s.add([post("a", group="offensive_candidate"), post("b", group="control"), post("c", group="control")])
        self.assertEqual(s.groups, {"offensive_candidate": 1, "control": 2})
        s.finish()


class NameRedactorTests(unittest.TestCase):
    NAMES = {"Ahmet Yılmaz", "ssg", "x.ali", "ŞEYMA", "İsmail", "😀😀😀", "pena"}
    TEXTS = [
        "ssg haklı, ahmet yılmaz da öyle dedi",
        "bak x.ali dedi", "şeyma burada", "ismail geldi", "hi 😀😀😀 there",
        "penalti", "@ssg", "#ŞEYMA", "", "hiçbiri yok",
    ]

    def test_same_result_as_single_regex(self):
        r = NameRedactor(self.NAMES)
        pattern = names_pattern(self.NAMES)
        for text in self.TEXTS:
            self.assertEqual(r.sub(text), pattern.sub(NAME_TOKEN, text), text)

    def test_add_extends(self):
        r = NameRedactor()
        self.assertEqual(r.sub("ssg haklı"), "ssg haklı")
        r.add({"ssg"})
        self.assertEqual(r.sub("ssg haklı"), f"{NAME_TOKEN} haklı")


if __name__ == "__main__":
    unittest.main()
