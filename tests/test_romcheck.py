"""ROM-level checks (tools/romcheck.py): each test builds its own ROM in memory from the clean dump."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
class RomCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import insert
        cls.orig = check_rom.original()
        cls.new, cls.writes, cls.st = insert.build(cls.orig, "en")

    def test_en_build_clean(self):
        import romcheck
        self.assertEqual(romcheck.check_writes(self.orig, self.new, self.writes), [])
        self.assertEqual(romcheck.check_pointer(self.new, self.st["model"]), [])
        self.assertEqual(romcheck.check_texts(self.new, self.st["ids"], self.st["texts"], self.st["table"]), [])
        self.assertEqual(romcheck.check_readers(self.orig), [])
        self.assertEqual(romcheck.check_branches(self.orig), [])
        self.assertGreater(self.st["replaced"], 700)

    def test_marker_build_clean(self):
        import romcheck
        _, _, errs = romcheck.run(self.orig, "marker")
        self.assertEqual(errs, [])

    def test_leftover_jp(self):
        import romcheck
        import script
        self.assertEqual(romcheck.check_leftover_jp(self.new, self.st["ids"], self.st["table"]), [])
        rows = script.load_script()
        mid = next(m for m in self.st["texts"] if not rows[m]["notes"].startswith(romcheck.KEEP_JP))
        rows[mid] = dict(rows[mid], notes="")
        import insert
        new, _, st = insert.build(self.orig, "en", {mid: "Glen{n}" + "まだ"})
        self.assertTrue(romcheck.check_leftover_jp(new, st["ids"], st["table"], rows))

    def test_stray_byte_fails(self):
        import romcheck
        bad = bytearray(self.new)
        bad[0x100] ^= 0xFF
        self.assertTrue(romcheck.check_writes(self.orig, bytes(bad), self.writes))

    def test_write_outside_allowed_fails(self):
        import romcheck
        errs = romcheck.check_writes(self.orig, self.new, self.writes, ranges=[(0xD23570, 0xEFFFFF)])
        self.assertTrue(any("outside tbl/allowed.txt" in e for e in errs))

    def test_pointer_and_texts_fail_when_broken(self):
        import insert
        import romcheck
        bad = bytearray(self.new)
        struct.pack_into("<I", bad, insert.textblock.GROUP_PTR, 0x081E90C4)
        self.assertTrue(romcheck.check_pointer(bytes(bad), self.st["model"]))
        mid = next(iter(self.st["texts"]))
        texts = dict(self.st["texts"], **{mid: "Something else entirely"})
        self.assertTrue(romcheck.check_texts(self.new, self.st["ids"], texts, self.st["table"]))

    def test_stale_reader_fails(self):
        import insert
        import romcheck
        bad = bytearray(self.orig)
        struct.pack_into("<I", bad, 0x100, 0x08000000 + int(self.st["ids"][8][0], 16))   # a message start
        errs = romcheck.check_readers(bytes(bad))
        self.assertTrue(any("0x000100" in e for e in errs), errs)
        self.assertEqual(insert.FREE % 4, 0)

    def test_stale_reader_unaligned_flagged(self):
        import romcheck
        bad = bytearray(self.orig)
        struct.pack_into("<I", bad, 0x102, 0xF8000000 + int(self.st["ids"][8][0], 16))   # 2-aligned, mirror + flags
        errs = romcheck.check_readers(bytes(bad))
        self.assertTrue(any("0x000102" in e for e in errs), errs)

    def test_branch_decoder(self):
        import asmpatch
        import romcheck
        rom = bytearray(0x200)
        rom[0x10:0x14] = asmpatch.thumb_bl(0x10, 0x180)
        rom[0x20:0x22] = struct.pack("<H", 0xD0FE)   # beq . (self)
        rom[0x30:0x32] = struct.pack("<H", 0xE7FE)   # b . (self)
        self.assertEqual(romcheck.branch_targets(bytes(rom), 0, 0x40), [(0x10, 0x180), (0x20, 0x20), (0x30, 0x30)])


if __name__ == "__main__":
    unittest.main()
