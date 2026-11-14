"""notes.py: fill the `notes` column of script/*.tsv with what the marker build learned (only empty cells).

    python -X utf8 tools/notes.py ROM

- `nontext: ...`  no text at all (include templates, spacer rows); tools/insert.py never replaces these.
- `debug: ...`    development readouts (sub-table 3: ASSERT, map/BG/anim numbers, script errors); translated
                  like any text but never seen in normal play.
- `placeholder: ...` 開発中 / エラーコード in unused sub-tables and slots.
- `column: N px`  lines padded with {padNN} to a fixed width (name and stage lists); the build refills the pads
                  so the English line keeps N px (tools/insert.py fill()); the English text must stay <= N px.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import insert  # noqa: E402
import script  # noqa: E402

DEBUG_IDS = {"1E9BBA", "1E9BD1", "1E9BF1", "1E9BFC", "1E9C08", "1E9C2C", "1E9C90", "1E9CC0", "1E9CE8", "1E9CEC",
             "1E9CF9", "1E9D1A", "1E9E0B", "1E9E25"}


def note_for(jt, wt, r):
    jp = r["jp"]
    if not insert.has_text(jt, jp.replace(script.TAIL, "")):
        return "nontext: no text (include template or spacer row); kept as is"
    if r["id"] in DEBUG_IDS:
        return "debug: development readout, not seen in normal play"
    if jp == "開発中":
        return "placeholder: 'in development', fills an unused sub-table"
    if jp == "エラーコード":
        return "placeholder: 'error code', fills unused slots"
    if "{pad" in jp:
        cols = [insert.px(jt.encode(seg), wt) for seg in insert.split_lines(jp) if "{pad" in seg]
        return "column: " + ", ".join(f"{w} px" for w in cols) + " wide line (build refills the pads)"
    return ""


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    rom = Path(sys.argv[1]).read_bytes()
    wt = rom[insert.font.WIDTHS:insert.font.WIDTHS + 0x200]
    jt = script.table()
    changed = 0
    for path in sorted(script.SCRIPT.glob("s*.tsv")):
        rows = script.read_tsv(path)
        n = 0
        for r in rows:
            if not r["notes"]:
                r["notes"] = note_for(jt, wt, r)
                n += bool(r["notes"])
        if n:
            script.write_tsv(path, rows)
            changed += n
    print(f"notes: filled {changed} cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
