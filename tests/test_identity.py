"""Identity build (phase 3): unpack -> repack with no edits gives the original bytes. Keep it green forever.

- the script block (master table, 40 sub-tables, messages) repacks byte-identical, and build.py's ROM equals the dump;
- the LZ codec: the Python decompressor matches known output sizes, and compress -> decompress is lossless and no
  bigger than the original on a sample of blocks (the full run is `python -X utf8 tools/klz.py test ROM`, ~80 s).
Skipped on a clone without the ROM.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _rom():
    roms = sorted((ROOT / "rom").glob("*.gba"))
    return roms[0].read_bytes() if roms else None


class TestIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = _rom()
        if cls.d is None:
            raise unittest.SkipTest("no ROM in rom/")

    def test_textblock_repack(self):
        import textblock
        m = textblock.unpack(self.d)
        self.assertEqual(len(m["subs"]), 40)
        self.assertEqual(sum(len(s["msgs"]) for s in m["subs"]), 791)
        self.assertEqual(textblock.pack(m), self.d[textblock.MASTER:textblock.END])

    def test_textblock_relocates(self):
        """Packing at another base keeps every pointer resolving to the same message bytes."""
        import struct
        import textblock
        m = textblock.unpack(self.d)
        base = 0xE00000
        blob = textblock.pack(m, base)
        rom = bytearray(self.d)
        rom[base:base + len(blob)] = blob
        for i in (1, 13, 40):
            a = base + 4 * i
            sub = a + struct.unpack_from("<I", rom, a)[0]
            o = textblock.MASTER + 4 * i
            sub0 = o + struct.unpack_from("<I", self.d, o)[0]
            for k in range(0, 200, 7):
                t1 = sub + 2 * k + struct.unpack_from("<H", rom, sub + 2 * k)[0]
                t0 = sub0 + 2 * k + struct.unpack_from("<H", self.d, sub0 + 2 * k)[0]
                self.assertEqual(rom[t1:t1 + 24], self.d[t0:t0 + 24])

    def test_build_identical(self):
        import build
        self.assertEqual(build.build(self.d), self.d)

    def test_lz_sample(self):
        import klz
        blocks = klz.lz_blocks(self.d)
        self.assertEqual(len(blocks), 77)
        for g, i, o, used in sorted(blocks, key=lambda b: b[3])[:6]:
            data, n = klz.decompress(self.d, o)
            self.assertEqual(n, used)
            c = klz.compress(data)
            self.assertEqual(klz.decompress(c)[0], data)
            self.assertLessEqual(len(c), used)


if __name__ == "__main__":
    unittest.main()
