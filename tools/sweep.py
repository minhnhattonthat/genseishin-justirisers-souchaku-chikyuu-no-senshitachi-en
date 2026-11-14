"""sweep.py: static graphics-text sweep (phase 1). Renders every distinct resource of the chosen groups as GBA 4bpp
tiles (grey ramp), decompressed when it is a Konami-LZ block (tools/res.py), into numbered pages with a label per
resource, plus an index. Reviewers list the labels whose tiles show Japanese.

    python -X utf8 tools/sweep.py ROM OUTDIR [--groups 1,4,5,9,10,11] [--cols 64] [--rows 80] [--zoom 2]

Every resource is either drawn or printed as "skip <label> <reason>" (never dropped silently).
Label format on the page: GG.IIII (group.index) in the left margin of the resource's first row.
"""
import argparse
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import res  # noqa: E402

DIGITS = {  # 3x5
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001010010",
    "8": "111101111101111", "9": "111101111001111", ".": "000000000000010",
}
MARGIN = 36


def png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    def chunk(t, b):
        return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def fp_tiles(data):
    """'fp' container (groups 9 LZ / 10 raw, the latter with a 2-byte prefix): 'fp' 01 02, u16 count, then count
    10-byte entries (type u8, flags u8, u16 unit, u16 count, u32 offset from 'fp'). Type 0x2X = tiles with unit 0x20
    (4bpp) or 0x40 (8bpp); 0x1X palettes, 0x3X maps (guess). -> [(entry, fmt, bytes)] or None if not fp."""
    for base in (0, 2):
        if data[base:base + 2] == b"fp":
            break
    else:
        return None
    n = struct.unpack_from("<H", data, base + 4)[0]
    out = []
    for k in range(n):
        e = base + 6 + 10 * k
        if e + 10 > len(data):
            break
        t, _, unit, cnt, off = struct.unpack_from("<BBHHI", data, e)
        # type codes differ between containers, so render every entry of a tile's worth or more from its own
        # offset (tile data starts there; a tile-aligned whole-blob render would shear it)
        if unit * cnt >= 256:
            out.append((k, "gba8" if unit == 0x40 else "gba4", data[base + off:base + off + unit * cnt]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--groups", default="1,4,5,9,10,11")
    ap.add_argument("--cols", type=int, default=64)
    ap.add_argument("--rows", type=int, default=80)
    ap.add_argument("--zoom", type=int, default=2)
    ap.add_argument("--max-tiles", type=int, default=4096, help="cap per resource (rest noted in the index)")
    ap.add_argument("--fmt", choices=["gba4", "gba8"], default="gba4")
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    dc = res.Decomp(d)
    want = {int(x) for x in a.groups.split(",")}
    os.makedirs(a.out, exist_ok=True)
    seen, items = set(), []
    for g, i, o, size in res.resources(d):
        if g not in want:
            continue
        if o in seen:
            continue
        seen.add(o)
        if size < 32:
            print(f"skip {g:02d}.{i:04d} {o:07X} size {size} < one tile")
            continue
        r = dc.run(o) if size >= 4 else None
        lz = r is not None and abs(r[1] - size) <= 16 and len(r[0]) > size
        data = r[0] if lz else d[o:o + size]
        label = f"{g:02d}.{i:04d}"
        kind = "lz" if lz else "raw"
        chunks = fp_tiles(data)
        if chunks is None:
            items.append((label, o, size, kind, a.fmt, data))
            continue
        for k, fmt, blob in chunks:
            items.append((label, o, size, f"{kind} fp#{k}", fmt, blob))
        if not chunks:
            print(f"skip {label} {o:07X} fp container with no tile chunk")

    W = MARGIN + a.cols * 8
    page, lines, index = 1, [], []

    def flush():
        nonlocal page, lines
        if not lines:
            return
        z = a.zoom
        rows = []
        for ln in lines:
            zr = bytearray()
            for px in range(0, len(ln), 3):
                zr += ln[px:px + 3] * z
            rows.extend([zr] * z)
        png(os.path.join(a.out, f"p{page:03d}.png"), W * z, len(lines) * z, rows)
        page += 1
        lines = []

    for label, o, size, kind, fmt, data in items:
        tb = 32 if fmt == "gba4" else 64
        ntiles = len(data) // tb
        capped = ntiles > a.max_tiles
        ntiles = min(ntiles, a.max_tiles)
        trows = (ntiles + a.cols - 1) // a.cols
        if len(lines) // 8 + trows > a.rows and lines:
            flush()
        index.append(f"p{page:03d}\t{label}\t{o:07X}\t{size}\t{kind}\t{fmt}\t{len(data)}"
                     + ("\tcapped" if capped else ""))
        for tr in range(trows):
            for y in range(8):
                ln = bytearray([40, 0, 0] * W)   # dark red margin
                ln[MARGIN * 3 - 3:MARGIN * 3] = b"\xff\x00\x00"
                for tc in range(a.cols):
                    t = tr * a.cols + tc
                    if t >= ntiles:
                        break
                    for x in range(8):
                        if tb == 32:
                            b = data[t * 32 + y * 4 + x // 2]
                            v = ((b >> 4) if x & 1 else (b & 15)) * 17
                        else:   # 8bpp: index scrambled so neighbouring indices differ visibly
                            v = (data[t * 64 + y * 8 + x] * 37) & 0xFF
                        p = (MARGIN + tc * 8 + x) * 3
                        ln[p:p + 3] = bytes([v] * 3)
                if tr == 0 and 1 <= y <= 5:
                    for k, ch in enumerate(label):
                        bits = DIGITS[ch][(y - 1) * 3:(y - 1) * 3 + 3]
                        for bx, bit in enumerate(bits):
                            if bit == "1":
                                p = (1 + k * 4 + bx) * 3
                                ln[p:p + 3] = b"\xff\xff\x00"
                lines.append(ln)
            if len(lines) // 8 >= a.rows:
                flush()
        # separator
        lines.append(bytearray([255, 0, 0] * W))
    flush()
    with open(os.path.join(a.out, "index.tsv"), "w", encoding="utf-8") as f:
        f.write("page\tlabel\trom\tsize\tkind\tbytes\n" + "\n".join(index) + "\n")
    print(f"{len(items)} resources, {page - 1} pages -> {a.out}")


if __name__ == "__main__":
    main()
