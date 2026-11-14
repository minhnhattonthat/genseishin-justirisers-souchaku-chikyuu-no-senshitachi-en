"""Extraction (phase 4): the table codec and the script/ dump.

- roundtrip: encode(decode(msg)) == msg for all 791 messages, shared tails included, and the dump covers the whole
  block 0x1E90C0-0x1FE9F0 with no gap (tools/script.py check);
- every glyph the script uses has a name in tbl/jp.tbl (no `{cXXX}` fallback, no `[XX]` byte);
- script/*.tsv matches the ROM: same ids, slots and jp text as a fresh dump, and its jp re-encodes to the ROM bytes;
- the token-aware message split: `13 1F 00` (sound 0x001F) and glyph 0x11F (`01 1F`) do not end a message.
ROM-dependent tests skip on a clone without rom/.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import script  # noqa: E402
import textblock  # noqa: E402


def _rom():
    roms = sorted((ROOT / "rom").glob("*.gba"))
    return roms[0].read_bytes() if roms else None


class TestCodec(unittest.TestCase):
    def test_tail_marker(self):
        t = script.table()
        text = "あ{n}{tail}い"
        msg, tails = script.encode(t, text)
        self.assertEqual(tails, [2])
        self.assertEqual(script.decode(t, msg, tails), text)

    def test_two_byte_fallback(self):
        t = script.table()
        self.assertEqual(t.decode(b"\x06\x99", 0, 2)[0], "{c699}")   # unread kanji cell stays one token
        self.assertEqual(t.encode("{c699}"), b"\x06\x99")

    def test_msg_end_skips_args(self):
        self.assertEqual(textblock.msg_end(b"\x20\x1d\x13\x1f\x00\x61\x1f", 0), 7)
        self.assertEqual(textblock.msg_end(b"\x01\x1f\x61\x1f", 0), 4)


class TestScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = _rom()
        if cls.d is None:
            raise unittest.SkipTest("no ROM in rom/")

    def test_roundtrip_and_coverage(self):
        self.assertEqual(script.check(self.d), [])

    def test_every_glyph_named(self):
        bad = [(r["id"], r["jp"]) for _, rs in script.rows(self.d) for r in rs if "{c" in r["jp"] or "[" in r["jp"]]
        self.assertEqual(bad, [])

    def test_dump_matches_rom(self):
        files = sorted((ROOT / "script").glob("s*.tsv"))
        self.assertEqual(len(files), 40, "run: python -X utf8 tools/script.py dump ROM")
        have = script.load_script()
        t = script.table()
        n = 0
        for stem, rs in script.rows(self.d):
            for r in rs:
                h = have.get(r["id"])
                self.assertIsNotNone(h, f"{stem} {r['id']} missing from script/")
                self.assertEqual((h["slots"], h["jp"]), (r["slots"], r["jp"]), r["id"])
                msg, _ = script.encode(t, h["jp"])
                a = int(r["id"], 16)
                self.assertEqual(msg, self.d[a:a + len(msg)], r["id"])
                n += 1
        self.assertEqual(n, len(have))


if __name__ == "__main__":
    unittest.main()
