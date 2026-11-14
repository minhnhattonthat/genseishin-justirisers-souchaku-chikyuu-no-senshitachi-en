"""msgscenes.py: which warp scenes drew which messages (MSG lines from tools/lua/winlog.lua logs).

    python -X utf8 tools/msgscenes.py DIR [ID_PREFIX,...] [--build marker|en]

DIR holds emu.py run folders with log.txt (e.g. work/qa/marker). Prints, per scene, the first frame each message
id was drawn. With prefixes (e.g. 1E93,1EA4), only ids starting with one of them. Finds the scene to measure a
width-gate variant in.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402
import insert  # noqa: E402

MSG = re.compile(r"MSG f(\d+) addr=([0-9A-F]+)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("prefixes", nargs="?", default="")
    ap.add_argument("--build", default="marker", choices=["marker", "en"])
    a = ap.parse_args()
    orig = check_rom.original()
    addrs = insert.build(orig, a.build)[2]["addresses"]
    inv = addrs  # ROM offset -> message id
    pref = tuple(p for p in a.prefixes.split(",") if p)
    for d in sorted(Path(a.dir).iterdir()):
        lg = d / "log.txt"
        if not lg.exists():
            continue
        seen = {}
        for m in MSG.finditer(lg.read_text(errors="ignore")):
            i = inv.get(int(m.group(2), 16) & 0x1FFFFFF)
            if i and (not pref or i.startswith(pref)) and i not in seen:
                seen[i] = int(m.group(1))
        if seen:
            print(d.name, " ".join(f"{k}@{v}" for k, v in seen.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
