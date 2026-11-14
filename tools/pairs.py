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


def main(argv):
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
