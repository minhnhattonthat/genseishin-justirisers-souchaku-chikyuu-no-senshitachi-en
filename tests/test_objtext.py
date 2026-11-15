"""OBJ sprite lettering (tools/objtext.py, gfx/obj.tsv): every 'aS' container of group 17 roundtrips through the
parser (its extra tile included), redraws stay in place at the same size with frame/OBJ tables untouched, every
listed frame changes, frames sharing no tile with a listed one stay identical, and the はい/いいえ redraw only
recycles the old glyph tiles of the cells it rewrites (other layers draw with tileset 5[0] too)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class ObjTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import objtext
        cls.orig = check_rom.original()
        cls.rows = objtext.load_rows()
        rom = bytearray(cls.orig)
        cls.ranges = objtext.apply(rom, cls.orig, cls.rows)
        cls.new = bytes(rom)

    def test_containers_roundtrip(self):
        import objtext
        import res
        seen = set()
        for g, i, o, s in res.resources(self.orig):
            if g != 17 or o in seen or self.orig[o:o + 2] != b"aS":
                continue
            seen.add(o)
            sp = objtext.Sprite(self.orig[o:o + s])
            self.assertEqual(sp.blob(), self.orig[o:o + sp.size], i)
        self.assertGreater(len(seen), 50)

    def test_extra_tile_is_read(self):
        import objtext
        sp, _ = objtext.load(self.orig, 648)   # frame 2's last OBJ reaches tile 53 = the header count
        self.assertEqual(len(sp.tiles), 54)

    def test_in_place_and_tables_kept(self):
        import objtext
        for n in sorted({r["target"][1] for r in self.rows if r["target"][0] == "obj"}):
            a, oa = objtext.load(self.orig, n)
            b, ob = objtext.load(self.new, n)
            self.assertEqual(oa, ob, n)
            self.assertEqual(self.new[ob:ob + b.tstart], self.orig[oa:oa + a.tstart], n)   # header, palette, OBJs

    def test_listed_frames_changed_others_kept(self):
        import objtext
        for n in sorted({r["target"][1] for r in self.rows if r["target"][0] == "obj"}):
            a, _ = objtext.load(self.orig, n)
            b, _ = objtext.load(self.new, n)
            listed = {r["target"][2] for r in self.rows if r["target"][:2] == ("obj", n)}
            changed = {t for t in range(len(a.tiles)) if a.tiles[t] != b.tiles[t]}
            for f in range(len(a.frames)):
                if f in listed:
                    self.assertNotEqual(a.canvas(f), b.canvas(f), (n, f))
                elif not changed & set(a.frame_tiles(f)):
                    self.assertEqual(a.canvas(f), b.canvas(f), (n, f))

    def test_bg5_recycles_only_rewritten_cells(self):
        import bgtext
        import objtext
        to, ts_ = objtext.resource(self.orig, 0, 5)
        mo, ms = objtext.resource(self.orig, 3, 5)
        a, b = bgtext.Tileset(self.orig[to:to + ts_]), bgtext.Tileset(self.new[to:to + ts_])
        self.assertEqual(a.n0, b.n0)
        m = bgtext.Map(self.orig[mo:mo + ms])
        used = {e & 0x3FF for e in m.e}
        for t in range(a.n0):
            if t not in used:
                self.assertEqual(a.tiles[t], b.tiles[t], t)


    def test_title_picture_in_place(self):
        import objtext
        o, s = objtext.resource(self.orig, 20, 5)
        a, b = objtext.Pic(self.orig[o:o + s]), objtext.Pic(self.new[o:o + s])
        self.assertEqual((a.head, a.mid, a.nt), (b.head, b.mid, b.nt))   # header, palette, tile count
        ca, cb = a.canvas(), b.canvas()
        rows = [r for r in self.rows if r["target"][0] == "pic5"]
        y0 = min(r["rect"][1] for r in rows)
        y1 = max(r["rect"][1] + r["rect"][3] for r in rows)
        self.assertTrue(any(ca[p] != cb[p] for p in ca))
        self.assertEqual([p for p in ca if ca[p] != cb[p] and not y0 <= p[1] < y1], [])   # logo, 2nd copyright line

    def test_lz_picture_recompressed_in_place(self):
        """Intro intertitle 4[6]: LZ again, inside the old resource, same header/palette/tile count, and only the
        lettering rows' rects change."""
        import objtext
        rows = [r for r in self.rows if r["target"][0] == "pic4"]
        self.assertTrue(rows)
        for n in sorted({r["target"][1] for r in rows}):
            a, o, s, lz = objtext.load_pic(self.orig, 4, n)
            b, o2, s2, lz2 = objtext.load_pic(self.new, 4, n)
            self.assertTrue(lz and lz2)
            self.assertEqual((o, s), (o2, s2))
            self.assertEqual((a.head, a.mid, a.nt), (b.head, b.mid, b.nt))
            ca, cb = a.canvas(), b.canvas()
            rects = [r["rect"] for r in rows if r["target"][1] == n]
            inside = lambda p: any(x <= p[0] < x + w and y <= p[1] < y + h for x, y, w, h in rects)   # noqa: E731
            self.assertTrue(any(ca[p] != cb[p] for p in ca))
            self.assertEqual([p for p in ca if ca[p] != cb[p] and not inside(p)], [])


if __name__ == "__main__":
    unittest.main()
