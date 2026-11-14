"""Where each BG tileset sits in VRAM, so a redraw knows its tile budget (docs/re/graphics.md §BG redraw pipeline).

    python -X utf8 tools/bgvram.py VRAM.bin ROM N [N..]

VRAM.bin: `ppu.vram.bin` from `tools/lua/bgcnt.lua --var DUMP=<frame>` on the screen in question. For each screen
N, finds tileset 18[N]'s tiles in VRAM (char block 0-3; 4bpp) and prints its first VRAM tile, its tile count, and
the next VRAM tile below 512 * blocks that holds something else (the budget: the tileset can grow up to there).
A tile all zero is counted as free.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import bgtext  # noqa: E402
import res  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vram")
    ap.add_argument("rom")
    ap.add_argument("n", nargs="+", type=int)
    a = ap.parse_args()
    v = Path(a.vram).read_bytes()[:0x10000]
    d = Path(a.rom).read_bytes()
    R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
    vt = [v[32 * i:32 * i + 32] for i in range(len(v) // 32)]
    for n in a.n:
        o, s = R[(18, n)]
        ts = bgtext.Tileset(d[o:o + s])
        nz = next(i for i, t in enumerate(ts.tiles) if any(t))   # first non-blank tile anchors the search
        hits = [i - nz for i, t in enumerate(vt) if t == ts.tiles[nz] and i >= nz]
        base = next((b for b in hits if all(vt[b + k] == ts.tiles[k] for k in range(min(len(ts.tiles), len(vt) - b)))),
                    None)
        if base is None:
            print(f"18[{n}]: not found in VRAM (not loaded on this frame, or loaded in part)")
            continue
        end = base + len(ts.tiles)
        nxt = next((i for i in range(end, (base // 512 + 1) * 512) if any(vt[i])), (base // 512 + 1) * 512)
        print(f"18[{n}]: VRAM tiles {base}-{end - 1} ({len(ts.tiles)} tiles), next used tile {nxt}: "
              f"budget {nxt - base} tiles (+{nxt - end})")


if __name__ == "__main__":
    main()
