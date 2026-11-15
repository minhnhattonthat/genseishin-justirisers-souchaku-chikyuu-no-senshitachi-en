"""Recoloured tileset copies (gfx/bg_variants.tsv, bgtext.derive_variants): after bgtext.apply every variant 18[V]
is repointed to a new set with the redrawn base's tile count, and each of its tiles equals the base's tile except
for the listed index swaps (the bright stage bar 18[625] = grey 18[655] with ink 4 -> 3; the game over showed the
old Japanese 18[626] under the English map before this)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class VariantsTest(unittest.TestCase):
    def test_variants_follow_their_base(self):
        import bgtext
        import res
        orig = check_rom.original()
        rom = bytearray(orig)
        bgtext.apply(rom, orig)
        R0 = {(g, i): o for g, i, o, _ in res.resources(orig)}
        R1 = {(g, i): (o, s) for g, i, o, s in res.resources(bytes(rom))}
        variants = bgtext.load_variants()
        self.assertTrue(variants)
        for v, b, swap in variants:
            self.assertNotEqual(R0[(18, v)], R1[(18, v)][0], f"18[{v}] not repointed")
            tv = bgtext.Tileset(rom[R1[(18, v)][0]:sum(R1[(18, v)])])
            tb = bgtext.Tileset(rom[R1[(18, b)][0]:sum(R1[(18, b)])])
            self.assertEqual(len(tv.tiles), len(tb.tiles), v)
            self.assertEqual(tv.tpal, tb.tpal, v)
            for t in range(len(tb.tiles)):
                for pb, pv in zip(tb.pixels(t), tv.pixels(t)):
                    self.assertIn(pv, (pb, swap.get(pb, pb)), (v, t))


if __name__ == "__main__":
    unittest.main()
