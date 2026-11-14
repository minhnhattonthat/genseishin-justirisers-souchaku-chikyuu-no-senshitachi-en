"""inkrows.py: per-line ink extents of light text in a screenshot region (width-gate measurements).

    python -X utf8 tools/inkrows.py SHOT.png|DIR x,y,w,h [--min 200] [--changed]

Groups rows holding "light" pixels (every channel >= --min) into bands and prints, per band, its rows and the
first/last ink column (screen x). With a DIR, prints one line per frame (only frames whose bands changed with
--changed). Used to read where a ruler line stops or wraps without judging pixels by eye.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image


def bands(path, rect, lo):
    x, y, w, h = rect
    im = Image.open(path).convert("RGB")
    px = im.load()
    rows = []
    for yy in range(y, y + h):
        xs = [xx for xx in range(x, x + w) if min(px[xx, yy]) >= lo]
        rows.append((yy, xs))
    out, cur = [], None
    for yy, xs in rows:
        if xs:
            if cur and yy == cur[1] + 1:
                cur = [cur[0], yy, min(cur[2], xs[0]), max(cur[3], xs[-1])]
            else:
                if cur:
                    out.append(cur)
                cur = [yy, yy, xs[0], xs[-1]]
        elif cur:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("rect")
    ap.add_argument("--min", type=int, default=200)
    ap.add_argument("--changed", action="store_true")
    a = ap.parse_args()
    rect = tuple(int(v) for v in a.rect.split(","))
    src = Path(a.src)
    files = sorted(src.glob("*.png")) if src.is_dir() else [src]
    last = None
    for f in files:
        if f.name.startswith("sheet"):
            continue
        b = bands(f, rect, a.min)
        s = "  ".join(f"y{b0}-{b1} x{x0}-{x1}" for b0, b1, x0, x1 in b)
        if a.changed and s == last:
            continue
        last = s
        print(f"{f.stem}\t{s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
