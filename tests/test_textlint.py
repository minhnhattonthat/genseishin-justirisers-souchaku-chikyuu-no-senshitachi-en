"""Translation gate: tools/textlint.py reports 0 errors on the whole script (widths, control codes, glossary)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402


@unittest.skipUnless(check_rom.have_rom(), "no ROM in rom/")
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

    def test_guessed_budgets_reported(self):
        """Rows linted on a Japanese-width guess (no measured window) are counted per sub-table in the CLI summary."""
        import io
        import contextlib
        import textlint
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            textlint.main([])
        line = next((ln for ln in out.getvalue().splitlines() if "guessed (Japanese-width) budgets" in ln), "")
        self.assertRegex(line, r"^\d+ rows on guessed")
        lint = textlint.Lint()
        lint.check(6, {"id": "TEST", "jp": "あいう", "en": "Abc", "notes": ""})
        self.assertIn("s06 1", lint.guessed_summary())

    def test_cli_fails_on_missing_english(self):
        import textlint
        lint = textlint.Lint()
        errs = lint.check(6, {"id": "TEST", "jp": "あいう", "en": "", "notes": ""})
        self.assertTrue(any("[missing]" in e for e in errs))

    def test_line_cap_override(self):
        import textlint
        self.assertEqual(textlint.load_line_caps().get("1E9EE8"), 3)

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

    def test_lint_missing_blanks_stub(self):
        import textlint
        lint = textlint.Lint()
        row = {"id": "TEST", "jp": "グレン{n}いくぜ", "en": "", "notes": ""}
        self.assertTrue(any("[missing]" in e for e in lint.check(8, row)))
        row = {"id": "TEST", "jp": " グレン{n}いくぜ", "en": "Glen{n}Let's go!", "notes": ""}
        self.assertTrue(any("[blanks]" in e for e in lint.check(1, row)))
        row = {"id": "TEST", "jp": "グレン{n}いくぜ{n}ユカ", "en": "Glen{n}Let's go,{n}Yuka!", "notes": ""}
        self.assertTrue(any("[stub]" in e for e in lint.check(8, row)))
        row["en"] = "Glen{n}Let's go, Yuka!"
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
        orig = check_rom.original()
        rom = bytearray(orig)
        font.apply(rom, fonts)
        wj, we = orig[font.WIDTHS:font.WIDTHS + 0x200], bytes(rom[font.WIDTHS:font.WIDTHS + 0x200])
        jp = "ジェナス{pad48}"
        out = insert.fill_pads(jt, et, wj, we, jp, "Jenas{fill}")
        self.assertEqual(insert.px(et.encode(out), we), insert.px(jt.encode(jp), wj))


if __name__ == "__main__":
    unittest.main()
