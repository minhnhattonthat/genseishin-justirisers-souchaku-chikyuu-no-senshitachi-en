"""pairs.py: review pairs file from script/*.tsv, in script order (sub-table order is roughly story order).

    python -X utf8 tools/pairs.py OUT.txt [s07 s08 ...]

Each entry: `>> id | JP` then `   EN`, control codes other than {n}/{p} stripped, {n} shown as ' / ', {p} as ' // '.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import script  # noqa: E402


def clean(t):
    t = t.replace("{p}", " // ").replace("{n}", " / ")
    return re.sub(r"\{(se|style|msg|sp|pad|fill)[^}]*\}", "", t).strip()


# Story-pass chapters (docs/synopsis.md): name -> sub-table range, inclusive.
CHAPTERS = [
    ("00_system", 0, 6), ("01_prologue", 7, 7), ("02_stage1", 8, 12), ("03_stage2", 13, 17),
    ("04_stage3", 18, 25), ("05_stage4", 26, 27), ("06_stage5", 28, 34), ("07_battle", 35, 39),
]


def chapters(outdir):
    """One file per chapter: `>> id | speaker | JP` / `   EN`, speaker = the tag line of a story message."""
    outdir.mkdir(parents=True, exist_ok=True)
    for name, lo, hi in CHAPTERS:
        lines = []
        for f in sorted((ROOT / "script").glob("s*.tsv")):
            if not lo <= int(f.name[1:3]) <= hi:
                continue
            lines.append(f"## {f.stem}")
            for r in script.read_tsv(f):
                if r["notes"].startswith(("nontext", "placeholder", "debug")) or not r["en"]:
                    continue
                jp, en, spk = r["jp"], r["en"], "-"
                if lo >= 7 and "{n}" in jp and not jp.startswith((" ", "{n}")):
                    spk = en.split("{n}")[0]
                    jp, en = jp.split("{n}", 1)[1], en.split("{n}", 1)[1]
                lines.append(f">> {r['id']} | {spk} | {clean(jp)}")
                lines.append(f"   {clean(en)}")
        (outdir / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{name}: {sum(1 for x in lines if x.startswith('>>'))} entries")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__ + "\n    python -X utf8 tools/pairs.py --chapters DIR   (story-pass chapter files)")
        return
    if argv[0] == "--chapters":
        return chapters(Path(argv[1]))
    out, subs = Path(argv[0]), set(argv[1:])
    lines = []
    for f in sorted((ROOT / "script").glob("s*.tsv")):
        if subs and f.name[:3] not in subs:
            continue
        lines.append(f"## {f.stem}")
        for r in script.read_tsv(f):
            if r["notes"].startswith(("nontext", "placeholder", "debug")) or not r["en"]:
                continue
            lines.append(f">> {r['id']} | {clean(r['jp'])}")
            lines.append(f"   {clean(r['en'])}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}: {sum(1 for x in lines if x.startswith('>>'))} entries")


if __name__ == "__main__":
    main(sys.argv[1:])
