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
        # gfx/bg.tsv may be empty while screens wait on their VRAM budget (gfx/bg_pending.tsv): test a fixture then
        cls.rows = bgtext.load_rows() or bgtext.load_rows(ROOT / "tests" / "data" / "bg_fixture.tsv")
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
        # an index whose tileset and map are the very resources of a redrawn screen (18/20[510..599] = 600) is that screen
        same = {(R[(18, n[0])], R[(20, n[1])]) for n in done}
        # a map a row draws with another tileset (20[619] on 18[618]) is never shown with 18[619] (= 18[620]); maps
        # in gfx/bg_pairs.tsv are drawn with the tileset listed there
        repaired = {R[(20, n[1])] for n in done if R[(18, n[0])] != R[(18, n[1])]}
        pairs = bgtext.load_pairs()
        for i in range(1001):
            if R[(20, i)] in repaired:
                continue
            if i in pairs:   # check the pair the game draws instead
                if R[(18, pairs[i])] in tsets and (pairs[i], i) not in done:
                    self.assertEqual(bgtext.render_screen(self.orig, (pairs[i], i)),
                                     bgtext.render_screen(self.new, (pairs[i], i)), f"s{pairs[i]:04d}_{i:04d} changed")
                continue
            if R[(18, i)] in tsets and (i, i) not in done and (R[(18, i)], R[(20, i)]) not in same:
                try:
                    a = bgtext.render_screen(self.orig, (i, i))
                except Exception:   # noqa: BLE001 - pairs that are not drawable screens
                    continue
                self.assertEqual(a, bgtext.render_screen(self.new, (i, i)), f"s{i:04d} changed")

    def test_tile_data_offset(self):
        # tiles start one byte after the per-tile banks for odd and even counts (VRAM dump of 18[620], nt 326)
        import bgtext
        import res
        R = {(g, i): (o, s) for g, i, o, s in res.resources(self.orig)}
        for n in (620, 653):   # even / odd tile count; tile 0 is the blank tile
            o, s = R[(18, n)]
            ts = bgtext.Tileset(self.orig[o:o + s])
            self.assertEqual(ts.tiles[0], bytes(32), f"18[{n}] tile 0")
            self.assertEqual(ts.blob(), self.orig[o:o + len(ts.blob())], f"18[{n}] roundtrip")

    def test_budget_enforced(self):
        import bgtext
        big = [dict(r, text="Restore Defaults|Restore Defaults", rect=(8, 40, 200, 40), font="normal", grid=False)
               for r in self.rows[:1]]
        big[0]["screen"] = (620, 620)
        with self.assertRaises(ValueError):
            bgtext.redraw(self.orig, big)

    def test_grid_letters_repeat(self):
        """align g: each glyph in its own 8 px cell, so a repeated letter is the same cell pixels (one tile)."""
        import bgtext
        import font
        row = {"screen": (620, 620), "rect": (37, 40, 64, 16), "text": "oo o", "font": "normal", "bank": 0,
               "ink": [1], "shadow": bgtext.parse_shadow("7"), "bg": 6, "align": "l", "grid": True, "bold": False,
               "track": 0, "note": ""}
        canvas = bgtext.draw({}, row, font.load_all(), lambda v: v)
        cell = lambda cx: [canvas[(8 * cx + k % 8, 40 + k // 8)] for k in range(128)]  # noqa: E731
        self.assertEqual({min(x for (x, _), v in canvas.items() if v == 1) // 8}, {5})   # snapped from 37 to 40
        self.assertNotEqual(set(cell(5)), {6})
        self.assertEqual(cell(5), cell(6))
        self.assertEqual(cell(5), cell(8))
        self.assertEqual(set(cell(7)), {6})   # the space is a blank cell

    def test_rows_parse(self):
        import bgtext
        self.assertTrue(self.rows)
        self.assertEqual(bgtext.parse_shadow("o5+10"), {"outline": 5, "drop": 10})
        self.assertEqual(bgtext.parse_screen("653:654"), (653, 654))


if __name__ == "__main__":
    unittest.main()
