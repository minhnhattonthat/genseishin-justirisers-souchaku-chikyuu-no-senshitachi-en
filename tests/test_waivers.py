"""docs/text_unshown.tsv (textcover.py --waive) must match what tools/gen_waivers.py generates from script/ notes."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import gen_waivers  # noqa: E402


class WaiversCurrent(unittest.TestCase):
    def test_waiver_file_current(self):
        cur = Path(gen_waivers.OUT).read_text(encoding="utf-8") if Path(gen_waivers.OUT).exists() else ""
        self.assertEqual(cur, gen_waivers.render(),
                         "docs/text_unshown.tsv is out of date: run python -X utf8 tools/gen_waivers.py")

    def test_waivers_name_existing_rows(self):
        ids = {r[0] for r in gen_waivers.rows()}
        self.assertTrue(ids, "no waivers generated")
        self.assertEqual(len(ids), len(gen_waivers.rows()), "duplicate waiver ids")


if __name__ == "__main__":
    unittest.main()
