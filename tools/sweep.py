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


def as_parse(data):
    """'aS' sprite container (groups 11, 15, 17), verified on 17.606 (dialogue box, tiles at +0xD8 = the OBJ VRAM
    DMA source): 'aS', u8 extra palettes, u8 nframes-1, u16 nobjs-1, u16 ntiles, u16 ?, (extra + 1) x 16 colours,
    nframes x (u16 count-1, u16 first_obj), nobjs x (u16 tile, u16 x | wcode << 12, u16 y | hcode << 12) with 12-bit
    signed x/y and size 8 << code, then ntiles 4bpp tiles in 1D OBJ mapping. 'AS' (4 in group 17) is the same with
    a 256-colour palette and 8bpp tiles (64 bytes, tile numbers in 64-byte units).
    -> (palette, frames=[[(tile, x, y, w, h)]], tiles, bpp) or None."""
    if data[:2] not in (b"aS", b"AS") or len(data) < 42:
        return None
    bpp = 8 if data[:2] == b"AS" else 4
    nf, no, nt = data[3] + 1, struct.unpack_from("<H", data, 4)[0] + 1, struct.unpack_from("<H", data, 6)[0]
    npal = 256 if bpp == 8 else 16 * (data[2] + 1)
    if 10 + 2 * npal > len(data):
        return None
    pal = struct.unpack_from(f"<{npal}H", data, 10)
    fo = 10 + 2 * npal
    oo = fo + 4 * nf
    start = oo + 6 * no
    if start > len(data):
        return None
    objs = []
    for k in range(no):
        t, xv, yv = struct.unpack_from("<HHH", data, oo + 6 * k)
        sx = lambda v: (v & 0xFFF) - 0x1000 if v & 0x800 else v & 0xFFF   # noqa: E731
        objs.append((t, sx(xv), sx(yv), 8 << (xv >> 12 & 3), 8 << (yv >> 12 & 3)))
    frames = []
    for k in range(nf):
        c, first = struct.unpack_from("<HH", data, fo + 4 * k)
        frames.append(objs[first:first + c + 1])
    return pal, frames, data[start:start + 8 * bpp * nt], bpp


def as_tiles(data, cols):
    """Every frame of an 'aS' container assembled from its OBJs (so multi-tile lettering reads as on screen), packed
    left to right into a canvas cols*8 px wide, cut back into 8x8 'grey8' tiles row-major -> [(0, 'grey8', bytes)]."""
    p = as_parse(data)
    if p is None:
        return None
    pal, frames, tiles, bpp = p
    tb = 8 * bpp
    lum = [0] + [max(48, ((c & 31) * 3 + (c >> 5 & 31) * 6 + (c >> 10 & 31)) * 255 // 310) for c in pal[1:]]
    W = cols * 8
    imgs = []
    for f in frames:
        if not f:
            continue
        x0, y0 = min(o[1] for o in f), min(o[2] for o in f)
        w, h = max(o[1] + o[3] for o in f) - x0, max(o[2] + o[4] for o in f) - y0
        if w > W or h > 256:
            continue
        img = [bytearray(w) for _ in range(h)]
        for t, x, y, ow, oh in reversed(f):   # lower OBJ number is drawn on top, as on the GBA
            for ty in range(oh // 8):
                for tx in range(ow // 8):
                    base = tb * (t + ty * (ow // 8) + tx)
                    if base + tb > len(tiles):
                        continue
                    for py in range(8):
                        for px in range(8):
                            if bpp == 8:
                                v = tiles[base + py * 8 + px]
                            else:
                                b = tiles[base + py * 4 + px // 2]
                                v = (b >> 4) if px & 1 else (b & 15)
                            if v:
                                img[y - y0 + ty * 8 + py][x - x0 + tx * 8 + px] = lum[v]
        imgs.append(img)
    if not imgs:
        return []
    rows, cx, cy, sh = [], 0, 0, 0   # shelf packing with a 4 px gap
    canvas = []
    for img in imgs:
        w, h = len(img[0]), len(img)
        if cx + w > W:
            cx, cy, sh = 0, cy + sh + 4, 0
        while len(canvas) < cy + h:
            canvas.append(bytearray(W))
        for y in range(h):
            canvas[cy + y][cx:cx + w] = img[y]
        cx, sh = cx + w + 4, max(sh, h)
    while len(canvas) % 8:
        canvas.append(bytearray(W))
    out = bytearray()
    for ty in range(len(canvas) // 8):
        for tx in range(cols):
            for py in range(8):
                out += canvas[ty * 8 + py][tx * 8:tx * 8 + 8]
    return [(0, "grey8", bytes(out))]


def p70_tiles(data):
    """Group 18 BG tileset: 00, mode (0x70 = 4bpp, 0x50 = 8bpp), 0x31, u8 extra palettes, u16 ntiles, palette
    (4bpp: (extra + 1) * 16 colours; 8bpp: 256), ntiles bytes of per-tile palette (padded to even), then the tiles.
    Verified on 18.0x28D (mode select): palettes = BG banks 1-4, tile 0 at +0x1AE = VRAM tile 16."""
    p = p70_parse(data)
    if p is None:
        return None
    _, _, tiles, bpp = p
    return [(0, "gba8" if bpp == 8 else "gba4", tiles)]


def p70_parse(data):
    """-> (palette list, per-tile palette bytes, tile bytes, bpp) or None (layout in p70_tiles)."""
    if len(data) < 6 or data[0] != 0 or data[2] != 0x31 or data[1] not in (0x50, 0x70):
        return None
    bpp = 8 if data[1] == 0x50 else 4
    nt = struct.unpack_from("<H", data, 4)[0]
    npal = 256 if bpp == 8 else 16 * (data[3] + 1)
    po = 6 + 2 * npal
    start = po + nt + (nt & 1)
    pal = list(struct.unpack_from(f"<{npal}H", data, 6))
    return pal, data[po:po + nt], data[start:start + 8 * bpp * nt], bpp


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
            chunks = as_tiles(data, a.cols)
        if chunks is None:
            chunks = p70_tiles(data)
        if chunks is None and g >= 14:
            print(f"skip {label} {o:07X} {data[:4].hex()} not a tile container (map/animation data)")
            continue
        if chunks is None:
            items.append((label, o, size, kind, a.fmt, data))
            continue
        for k, fmt, blob in chunks:
            items.append((label, o, size, f"{kind} fp#{k}", fmt, blob))
        if not chunks:
            print(f"skip {label} {o:07X} container with no tile chunk")

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
        tb = 32 if fmt == "gba4" else 64   # gba8 and grey8 (pre-assembled 'aS' frames) are 1 byte per pixel
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
                        elif fmt == "grey8":
                            v = data[t * 64 + y * 8 + x]
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
