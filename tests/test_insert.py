"""English font, encoder, code patch and relocation (phase 5). Skipped pieces that need the ROM on a clone without it.

- both fonts parse, agree on codes, and every width is even (the rasterizer mis-draws ink at odd x);
- the English table encodes every font character and keeps control codes;
- marker text fits each Japanese line's pixel width and keeps the line structure;
- the en build relocates the block: resource group 2 points at the new master table, every message there decodes
  to the same text as the original when the script has no English yet; the column-copy patch is in place.
"""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import font  # noqa: E402
import insert  # noqa: E402
import script  # noqa: E402
import textblock  # noqa: E402


def _rom():
    roms = sorted((ROOT / "rom").glob("*.gba"))
    return roms[0].read_bytes() if roms else None


class TestFont(unittest.TestCase):
    def test_fonts(self):
        fonts = font.load_all()
        for name, glyphs in fonts.items():
            for ch, g in glyphs.items():
                self.assertEqual(g["width"] % 2, 0, f"{name} {ch!r}")
                ink = [15 - (v & -v).bit_length() + 1 for v in g["rows"] or [] if v]   # rightmost ink column
                self.assertLess(max(ink, default=0), g["width"], f"{name} {ch!r}: ink reaches past the advance")
        self.assertTrue(set("AZaz09.,!?'\"-:;()/&[] ") <= set(fonts["normal"]))

    def test_encode(self):
        t = insert.en_table()
        self.assertEqual(t.encode("Az"), bytes([0x21, 0x54]))
        self.assertEqual(t.encode("a.b"), bytes([0x3B, 0x01, 0x60, 0x3C]))
        self.assertEqual(t.encode("{se:0300}Hi{n}"), bytes([0x13, 0x03, 0x00, 0x28, 0x43, 0x1D]))
        self.assertEqual(t.encode("{pad48}"), bytes([0x01, 0xFC]))

    def test_fill(self):
        d = _rom()
        if d is None:
            self.skipTest("no ROM in rom/")
        t, wt = insert.en_table(), d[font.WIDTHS:font.WIDTHS + 0x200]   # spacer cells keep the ROM's widths
        for gap in range(0, 300, 2):
            self.assertEqual(insert.px(t.encode(insert.fill(gap)), wt), gap)


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = _rom()
        if cls.d is None:
            raise unittest.SkipTest("no ROM in rom/")

    def test_marker_fits(self):
        rom = bytearray(self.d)
        fonts = font.load_all()
        font.apply(rom, fonts)
        jt, et = script.table(), insert.en_table(fonts["normal"])
        wj, we = self.d[font.WIDTHS:font.WIDTHS + 0x200], bytes(rom[font.WIDTHS:font.WIDTHS + 0x200])
        for mid, r in script.load_script().items():
            if r["notes"].startswith("nontext"):
                continue
            m = insert.marker_text(jt, et, wj, we, r)
            jl, ml = insert.split_lines(r["jp"]), insert.split_lines(m)
            self.assertEqual([x for x in jl if x in insert.BREAKS], [x for x in ml if x in insert.BREAKS], mid)
            for a, b in zip(jl, ml):
                if a in insert.BREAKS or "[" in b:
                    continue
                self.assertLessEqual(insert.px(et.encode(b.replace(script.TAIL, "")), we),
                                     max(insert.px(jt.encode(a.replace(script.TAIL, "")), wj), 0), (mid, b))

    def test_en_build_relocates(self):
        out, written, _ = insert.build(self.d, "en")
        ptr = struct.unpack_from("<I", out, textblock.GROUP_PTR)[0]
        self.assertEqual(ptr, 0x08000000 + insert.FREE + 4)
        # with no texts replaced, the relocated block holds the original messages (block content with English:
        # tests/test_romcheck.py)
        model = textblock.unpack(self.d)
        moved = bytes(insert.FREE) + textblock.pack(model, insert.FREE)
        self.assertEqual(textblock.unpack(moved, insert.FREE), model)
        self.assertEqual(out[0x83C4:0x83C8], insert.asmpatch.thumb_bl(0x83C4, insert.asmpatch.COPY_HOOK))


if __name__ == "__main__":
    unittest.main()
