"""Width-gate data: tbl/windows.json (measured budgets) covers every window geometry the tour logged."""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def variant_for(variants, row):
    hits = []
    for name, v in variants.items():
        m = v["match"]
        if all(str(row[k]) == str(val) for k, val in m.items()):
            hits.append(name)
    return hits


class WindowsTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "tbl" / "windows.json").read_text(encoding="utf-8"))
        with open(ROOT / "tbl" / "windows_ids.tsv", encoding="utf-8", newline="") as f:
            self.rows = list(csv.DictReader(f, delimiter="\t"))

    def test_budgets_measured(self):
        for name, v in self.data["variants"].items():
            self.assertGreater(v["px"], 0, name)
            self.assertNotIn("PENDING", v["measured"], name)
            self.assertIn(v["font"], ("normal", "small"), name)

    def test_every_logged_window_has_one_variant(self):
        self.assertTrue(self.rows)
        for r in self.rows:
            hits = variant_for(self.data["variants"], r)
            self.assertEqual(len(hits), 1, f"{r['id']} w={r['w']} h={r['h']} x0={r['x0']} attr={r['attr']}: {hits}")


if __name__ == "__main__":
    unittest.main()
