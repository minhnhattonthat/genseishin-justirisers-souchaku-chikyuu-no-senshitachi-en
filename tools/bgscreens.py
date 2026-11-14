"""bgscreens.py: render every BG screen of the menu/map resource set (phase 1 graphics-text sweep).

    python -X utf8 tools/bgscreens.py ROM OUTDIR [--zoom 2]

Groups 18, 19 and 20 share one index (1001 entries each, same duplicate pattern):
  18[i] tileset: 00, mode (0x70 4bpp / 0x50 8bpp), 0x31, u8 extra palettes, u16 ntiles, palette, per-tile palette
        bytes, tiles (sweep.p70_parse)
  19[i] 'a2' u16 n, then n 9-byte records (not a map; guess: OBJ/animation placements)
  20[i] BG map: 'B2' or 'C1', u8 w, u8 h, then w*h GBA screen entries (tile | hflip << 10 | vflip << 11 | pal << 12)
Each distinct (tileset, map) pair is drawn with its own palette into OUTDIR/s<index>.png; skipped pairs are printed.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import res  # noqa: E402
import sweep  # noqa: E402


def rgb(c):
    return bytes(((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31))


def render(ts, mp):
    """-> (w_px, h_px, rows of RGB bytes) or a string saying why not."""
    p = sweep.p70_parse(ts)
    if p is None:
        return f"tileset {ts[:4].hex()}"
    if mp[:2] not in (b"B2", b"C1"):
        return f"map {mp[:4].hex()}"
    rawpal, tpal, tiles, bpp = p
    pal = [rgb(c) for c in rawpal] + [b"\xff\x00\xff"] * (256 - len(rawpal))
    base = min(tpal) if tpal else 0   # the table holds VRAM bank numbers; the palettes load from that bank up
    w, h = mp[2], mp[3]
    if 4 + 2 * w * h > len(mp):
        return "map shorter than w*h"
    rows = [bytearray(w * 8 * 3) for _ in range(h * 8)]
    tb = 8 * bpp
    for my in range(h):
        for mx in range(w):
            e = struct.unpack_from("<H", mp, 4 + 2 * (my * w + mx))[0]
            t, hf, vf = e & 0x3FF, e >> 10 & 1, e >> 11 & 1
            pb = ((e >> 12) + (tpal[t] - base if t < len(tpal) else 0)) * 16
            if tb * (t + 1) > len(tiles):
                continue
            for py in range(8):
                sy = 7 - py if vf else py
                for px in range(8):
                    sxp = 7 - px if hf else px
                    if bpp == 8:
                        v = tiles[tb * t + sy * 8 + sxp]
                        c = pal[v]
                    else:
                        b = tiles[tb * t + sy * 4 + sxp // 2]
                        v = (b >> 4) if sxp & 1 else (b & 15)
                        c = pal[(pb + v) % 256] if v else pal[0]
                    p = (mx * 8 + px) * 3
                    rows[my * 8 + py][p:p + 3] = c
    return w * 8, h * 8, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--zoom", type=int, default=2)
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
    os.makedirs(a.out, exist_ok=True)
    seen, n = set(), 0
    for i in range(1001):
        (to, tsz), (mo, msz) = R[(18, i)], R[(20, i)]
        if (to, mo) in seen:
            continue
        seen.add((to, mo))
        r = render(d[to:to + tsz], d[mo:mo + msz])
        if isinstance(r, str):
            print(f"skip s{i:04d} 18@{to:07X} 20@{mo:07X}: {r}")
            continue
        w, h, rows = r
        z = a.zoom
        zr = []
        for row in rows:
            line = bytearray()
            for p in range(0, len(row), 3):
                line += row[p:p + 3] * z
            zr.extend([line] * z)
        sweep.png(os.path.join(a.out, f"s{i:04d}.png"), w * z, h * z, zr)
        n += 1
    print(f"{n} screens -> {a.out}")


if __name__ == "__main__":
    main()
