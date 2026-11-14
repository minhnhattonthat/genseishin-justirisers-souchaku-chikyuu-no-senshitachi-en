"""The dump in rom/ matches rom.sha1 (skipped on a clone without the ROM)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestRom(unittest.TestCase):
    def test_rom_sha1(self):
        if not any((ROOT / "rom").glob("*.gba")):
            self.skipTest("no ROM in rom/")
        import check_rom
        check_rom.check()


if __name__ == "__main__":
    unittest.main()
