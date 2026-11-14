"""winlog.py: read tools/lua/winlog.lua logs and list which window (box variant) each message is drawn into.

    python -X utf8 tools/winlog.py DIR [--build marker|en|orig] [--out work/qa/windows.tsv]

DIR holds emu.py run folders (each with log.txt), e.g. work/qa/winlog from
    python -X utf8 tools/debug/warp_all.py --rom build/justirisers_marker.gba --out work/qa/winlog \
        --script tools/lua/winlog.lua
--build says which ROM the logs came from, so message addresses map back to script ids (default: marker).
Writes one row per (id, window geometry) and prints the variants: (w tiles, start x, attr) -> ids.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import insert  # noqa: E402
import textblock  # noqa: E402

WIN = re.compile(r"WIN f(\d+) addr=([0-9A-F]+) win=(\d+) x=(\d+) y=(\d+) w=(\d+) h=(\d+) x0=(\d+) attr=([0-9A-F]+)")


def address_map(orig, build):
    if build == "orig":
        m = textblock.unpack(orig)
        return insert.addresses(m, textblock.MASTER, insert.message_ids(m))
    return insert.build(orig, build)[2]["addresses"]


def main():
    import build as b
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--build", default="marker", choices=["marker", "en", "orig"])
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "windows.tsv"))
    a = ap.parse_args()
    amap = address_map(b.rom_path().read_bytes(), a.build)
    rows, unknown = {}, set()
    for log in sorted(Path(a.dir).glob("*/log.txt")):
        for m in WIN.finditer(log.read_text(encoding="utf-8", errors="replace")):
            addr = int(m[2], 16) & 0x1FFFFFF
            mid = amap.get(addr)
            if mid is None:
                unknown.add(f"{addr:06X}")
                continue
            geo = tuple(int(m[i]) for i in range(3, 9)) + (m[9],)
            rows.setdefault((mid, geo), (log.parent.name, int(m[1])))
    variants = defaultdict(set)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("id\twin\tx\ty\tw\th\tx0\tattr\tscene\tframe\n")
        for (mid, geo), (scene, frame) in sorted(rows.items()):
            f.write("\t".join([mid] + [str(g) for g in geo] + [scene, str(frame)]) + "\n")
            win, x, y, w, h, x0, attr = geo
            variants[(w, x0, h, attr)].add(mid)
    print(f"{len(rows)} (id, window) pairs, {len({k[0] for k in rows})} ids -> {a.out}")
    if unknown:
        print(f"{len(unknown)} addresses not in the script block: {' '.join(sorted(unknown)[:12])}")
    for (w, x0, h, attr), ids in sorted(variants.items()):
        print(f"w={w} tiles x0={x0} h={h} attr={attr}: {len(ids)} ids, e.g. {' '.join(sorted(ids)[:6])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
