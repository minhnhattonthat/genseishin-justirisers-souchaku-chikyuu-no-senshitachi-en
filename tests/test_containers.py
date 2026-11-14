"""Sprite/BG container parsers in tools/sweep.py and tools/bgscreens.py agree with known ROM facts (needs the ROM)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rom():
    files = sorted((ROOT / "rom").glob("*.gba"))
    return files[0].read_bytes() if files else None


class TestContainers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = rom()
        if cls.d is None:
            raise unittest.SkipTest("no ROM in rom/")
        import res
        cls.R = {(g, i): (o, s) for g, i, o, s in res.resources(cls.d)}

    def blob(self, g, i):
        o, s = self.R[(g, i)]
        return self.d[o:o + s]

    def test_dialogue_box_tiles_start_at_d8(self):
        import sweep
        b = self.blob(17, 606)
        pal, frames, tiles, bpp = sweep.as_parse(b)
        self.assertEqual(bpp, 4)
        self.assertEqual(len(frames), 15)
        self.assertEqual(tiles[:32], b[0xD8:0xD8 + 32])   # OBJ VRAM DMA source seen in the tour

    def test_8bpp_as(self):
        import sweep
        pal, frames, tiles, bpp = sweep.as_parse(self.blob(17, 150))
        self.assertEqual((bpp, len(pal)), (8, 256))

    def test_every_group17_container_parses(self):
        import sweep
        bad = []
        for i in range(1001):
            if (17, i) not in self.R:
                break
            b = self.blob(17, i)
            if b[:2] in (b"aS", b"AS") and sweep.as_parse(b) is None:
                bad.append(i)
        self.assertEqual(bad, [])

    def test_bg_screen_renders(self):
        import bgscreens
        r = bgscreens.render(self.blob(18, 0x28D), self.blob(20, 0x28D))   # mode select
        self.assertNotIsInstance(r, str)
        self.assertEqual(r[:2], (240, 160))

    def test_tileset_tiles_match_vram_layout(self):
        import sweep
        b = self.blob(18, 0x28D)
        pal, tpal, tiles, bpp = sweep.p70_parse(b)
        self.assertEqual((bpp, len(pal), len(tpal)), (4, 64, 0x127))
        self.assertEqual(tiles[:32], b[0x1AE:0x1AE + 32])   # = VRAM tile 16 on the mode-select screen


if __name__ == "__main__":
    unittest.main()
