"""Attract-mode title (tools/attract.py, gfx/attract.tsv): every resource is rewritten in place at its size, the
subtitle fits its tile and metatile budgets with both halves (maps 20[247] / 20[248]) non-empty, and the copyright
redraw changes only tiles of the bottom rows of 18[245]."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class AttractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import attract
        cls.orig = check_rom.original()
        cls.out, cls.used, cls.changed = attract.build(cls.orig)
        rom = bytearray(cls.orig)
        cls.ranges = attract.apply(rom, cls.orig)
        cls.new = bytes(rom)

    def test_in_place(self):
        import cards
        self.assertEqual(set(self.out), {(18, 245), (18, 247), (19, 247), (20, 247), (20, 248)})
        for (g, n), b in self.out.items():
            o, s = cards.resource(self.orig, g, n)
            self.assertLessEqual(len(b), s, (g, n))
            self.assertEqual(cards.resource(self.new, g, n), (o, s), (g, n))
        spans = [cards.resource(self.orig, g, n) for g, n in self.out]
        for a, b in self.ranges:
            self.assertTrue(any(o <= a and b <= o + s for o, s in spans), hex(a))

    def test_budgets_and_halves(self):
        import attract
        import bgtext
        import cards
        tiles, metas = self.used
        self.assertLessEqual(tiles, 112)
        self.assertLessEqual(metas, 150)
        for mapn in attract.MAPS:
            o, s = cards.resource(self.new, 20, mapn)
            self.assertTrue(any(bgtext.Map(self.new[o:o + s]).e), mapn)

    def test_copyright_tiles_only(self):
        import cards
        ts_a, m, _, mts, _ = cards.load(self.orig, 245)
        ts_b = cards.load(self.new, 245)[0]
        rows = {cy for (cx, cy), t in cards.cells(m, mts).items()
                if t < ts_a.n0 and ts_a.tiles[t] != ts_b.tiles[t]}   # slot n0 = the resource's extra tile
        self.assertTrue(rows)
        self.assertLessEqual(rows, {17, 18})      # copyright line 1 = pixel rows 138-147
        self.assertEqual(ts_a.tpal, ts_b.tpal)


if __name__ == "__main__":
    unittest.main()
