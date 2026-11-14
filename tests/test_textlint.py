"""Translation gate: tools/textlint.py reports 0 errors on the whole script (widths, control codes, glossary)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

ORIG = ROOT / "work" / "orig.gba"


@unittest.skipUnless(ORIG.exists(), "needs work/orig.gba")
class TextLintTest(unittest.TestCase):
    def test_script_clean(self):
        import script
        import textlint
        lint = textlint.Lint()
        errs = []
        for f in sorted((ROOT / "script").glob("s*.tsv")):
            for r in script.read_tsv(f):
                if not r["notes"].startswith(("nontext", "placeholder", "debug")):
                    errs += lint.check(int(f.name[1:3]), r)
        self.assertEqual(errs, [])

    def test_lint_catches_overflow(self):
        import textlint
        lint = textlint.Lint()
        row = {"id": "TEST", "jp": "グレン{n}あ", "en": "Glen{n}" + "m" * 40, "notes": ""}
        self.assertTrue(any("[width]" in e for e in lint.check(8, row)))
        row["en"] = "Gant{n}ok"
        self.assertTrue(any("[tag]" in e for e in lint.check(8, row)))

    def test_lint_catches_avoid_spelling(self):
        import textlint
        lint = textlint.Lint()
        row = {"id": "TEST", "jp": "カゲリ{n}あ", "en": "Kageri{n}Kagere, wait!", "notes": ""}
        self.assertTrue(any("[avoid]" in e for e in lint.check(8, row)))
        row = {"id": "TEST", "jp": "ゾラ{n}あ", "en": "Zora{n}I am dr. zora!", "notes": ""}
        self.assertTrue(any("[avoid]" in e for e in lint.check(8, row)))
        row["en"] = "Zora{n}I am Doctor Zora!"
        self.assertFalse(any("[avoid]" in e for e in lint.check(8, row)))

    def test_lint_catches_dropped_honorific(self):
        import textlint
        lint = textlint.Lint()
        row = {"id": "TEST", "jp": "カゲリ{n}直也さんは？", "en": "Kageri{n}Where's Naoya?", "notes": ""}
        self.assertTrue(any("[honorific]" in e for e in lint.check(8, row)))
        row["en"] = "Kageri{n}Where's Naoya-san?"
        self.assertEqual(lint.check(8, row), [])

    def test_glossary_matches_whole_runs(self):
        import textlint
        self.assertTrue(textlint.has_term("ユカは", "ユカ"))
        self.assertFalse(textlint.has_term("ユカイ", "ユカ"))
        self.assertFalse(textlint.has_term("バグシーン", "シーン"))
        self.assertTrue(textlint.has_term("直也さんは", "直也さん", honorific=True))
        self.assertFalse(textlint.has_term("直也さんは", "直也さん"))

    def test_fill_pads_column(self):
        import font
        import insert
        import script
        fonts = font.load_all()
        et, jt = insert.en_table(fonts["normal"]), script.table()
        orig = ORIG.read_bytes()
        rom = bytearray(orig)
        font.apply(rom, fonts)
        wj, we = orig[font.WIDTHS:font.WIDTHS + 0x200], bytes(rom[font.WIDTHS:font.WIDTHS + 0x200])
        jp = "ジェナス{pad48}"
        out = insert.fill_pads(jt, et, wj, we, jp, "Jenas{fill}")
        self.assertEqual(insert.px(et.encode(out), we), insert.px(jt.encode(jp), wj))


if __name__ == "__main__":
    unittest.main()
