"""Area chapter cards (tools/cards.py, gfx/cards.tsv): the 19[n] metatile codec roundtrips, every header/title layer
is redrawn in place at its original sizes, its 20[n] map and attribute bytes are untouched, and no ink lands on a
cell without a metatile."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class CardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cards
        cls.orig = check_rom.original()
        cls.rows = cards.load_spec()
        rom = bytearray(cls.orig)
        cls.ranges = cards.apply(rom, cls.orig, cls.rows)
        cls.new = bytes(rom)

    def test_codec_roundtrip(self):
        import cards
        for n in cards.LAYERS:
            o, s = cards.resource(self.orig, 19, n)
            self.assertEqual(cards.encode(*cards.decode(self.orig[o:o + s])), self.orig[o:o + s], n)

    def test_every_layer_redrawn_in_place(self):
        import cards
        self.assertEqual({r["screen"][1] for r in self.rows}, set(cards.LAYERS))
        for n in cards.LAYERS:
            for g in (18, 19, 20):
                self.assertEqual(cards.resource(self.orig, g, n), cards.resource(self.new, g, n), (g, n))
            a, b = cards.load(self.orig, n), cards.load(self.new, n)
            self.assertEqual(a[0].n0, b[0].n0, n)
            self.assertEqual(a[1].e, b[1].e, n)            # 20[n] map
            self.assertEqual(a[2], b[2], n)                # head + attribute bytes
            self.assertEqual(len(a[3]), len(b[3]), n)
            self.assertEqual(b[3][0], (0, 0, 0, 0), n)     # metatile 0 stays blank
            self.assertNotEqual(cards.pixels(*a[:2], a[3]), cards.pixels(*b[:2], b[3]), n)

    def test_writes_inside_resources(self):
        import cards
        spans = [cards.resource(self.orig, g, n) for g in (18, 19) for n in cards.LAYERS]
        for a, b in self.ranges:
            self.assertTrue(any(o <= a and b <= o + s for o, s in spans), hex(a))


if __name__ == "__main__":
    unittest.main()
