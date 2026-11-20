"""Staff roll (tools/credits.py, gfx/credits.tsv): the 19[n] metatile codec roundtrips, every roll is redrawn in place
at its original sizes (so redrawn from blank: only `keep` rects carry original pixels), and the roll's transparent
lead-in is untouched."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class CreditsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import credits
        cls.orig = check_rom.original()
        cls.rows = credits.load_spec()
        rom = bytearray(cls.orig)
        cls.ranges = credits.apply(rom, cls.orig, cls.rows)
        cls.new = bytes(rom)

    def test_codec_roundtrip(self):
        import credits
        for n in credits.ROLLS:
            o, s = credits.resource(self.orig, 19, n)
            head, cells, nm = credits.decode(self.orig[o:o + s])
            self.assertEqual(credits.encode(head, cells, nm), self.orig[o:o + s], n)

    def test_every_roll_redrawn_in_place(self):
        import bgtext
        import credits
        self.assertEqual({r["roll"] for r in self.rows}, set(credits.ROLLS))
        for n in credits.ROLLS:
            for g in (18, 19):
                self.assertEqual(credits.resource(self.orig, g, n), credits.resource(self.new, g, n), (g, n))
            o, s = credits.resource(self.new, 18, n)
            self.assertEqual(bgtext.Tileset(self.new[o:o + s]).n0, credits.load_count(self.orig, n), n)
            _, a = credits.load(self.orig, n)
            _, b = credits.load(self.new, n)
            clear = 1 if n == 705 else 0
            self.assertEqual([k for k, e in enumerate(a) if e == clear], [k for k, e in enumerate(b) if e == clear], n)
            self.assertNotEqual(a, b, n)

    def test_lines_inside_one_page(self):
        """Scene 11 shows rolls 700-704 as four still pages (roll y 80-239, 240-399, 400-559, 560-719, measured in
        the emulator): a line whose ink crosses a page edge is cut in half on both pages (issue #1)."""
        import credits
        import font
        fonts = font.load_all()
        edges = (240, 400, 560)
        for r in self.rows:
            if r["font"] == "keep" or r["roll"] == 705:
                continue
            lo, hi = credits.ink_band(fonts[r["font"]])
            top = r["y"] - (lo + hi + 1) // 2
            if "g" in r["align"]:
                top = (top + 4) // 8 * 8
            a, b = top + lo, top + hi
            self.assertGreaterEqual(a, 80, r)
            self.assertLess(b, 720, r)
            for e in edges:
                self.assertFalse(a < e <= b, f"{r['roll']} {r['text']!r}: ink {a}..{b} crosses page edge {e}")

    def test_writes_inside_resources(self):
        import credits
        spans = [credits.resource(self.orig, g, n) for g in (18, 19) for n in credits.ROLLS]
        for a, b in self.ranges:
            self.assertTrue(any(o <= a and b <= o + s for o, s in spans), hex(a))


if __name__ == "__main__":
    unittest.main()
