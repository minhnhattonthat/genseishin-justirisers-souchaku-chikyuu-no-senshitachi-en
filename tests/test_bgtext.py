"""BG lettering (tools/bgtext.py, gfx/bg.tsv): every redrawn screen differs from the original only inside its rects,
and every other screen sharing a changed tileset is unchanged pixel for pixel."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class BgTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import bgtext
        cls.orig = check_rom.original()
        cls.rows = bgtext.load_rows()
        rom = bytearray(cls.orig)
        bgtext.apply(rom, cls.orig, cls.rows)
        cls.new = bytes(rom)

    def test_changes_only_inside_rects(self):
        import bgtext
        for n in sorted({r["screen"] for r in self.rows}):
            rects = [r["rect"] for r in self.rows if r["screen"] == n]
            oob = bgtext.oob_cells(self.orig, n)   # slots past the tileset: padded blank on purpose
            w, h, a = bgtext.render_screen(self.orig, n)
            _, _, b = bgtext.render_screen(self.new, n)
            bad = [(x, y) for y in range(h) for x in range(w)
                   if a[y][3 * x:3 * x + 3] != b[y][3 * x:3 * x + 3] and (x // 8, y // 8) not in oob
                   and not any(rx <= x < rx + rw and ry <= y < ry + rh for rx, ry, rw, rh in rects)]
            self.assertEqual(bad[:5], [], f"{bgtext.label(n)}: {len(bad)} pixels changed outside its rects")
            self.assertNotEqual(a, b, f"{bgtext.label(n)}: rows applied but nothing changed")

    def test_other_users_of_a_tileset_unchanged(self):
        import bgtext
        import res
        R = {(g, i): o for g, i, o, _ in res.resources(self.orig)}
        done = {r["screen"] for r in self.rows}
        tsets = {R[(18, n[0])] for n in done}
        for i in range(1001):
            if R[(18, i)] in tsets and (i, i) not in done:
                try:
                    a = bgtext.render_screen(self.orig, (i, i))
                except Exception:   # noqa: BLE001 - pairs that are not drawable screens
                    continue
                self.assertEqual(a, bgtext.render_screen(self.new, (i, i)), f"s{i:04d} changed")

    def test_rows_parse(self):
        import bgtext
        self.assertTrue(self.rows)
        self.assertEqual(bgtext.parse_shadow("o5+10"), {"outline": 5, "drop": 10})
        self.assertEqual(bgtext.parse_screen("653:654"), (653, 654))


if __name__ == "__main__":
    unittest.main()
