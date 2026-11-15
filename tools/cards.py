"""cards.py: the area chapter cards (エリアN + chapter title) in English (docs/re/graphics.md §Area cards).

    python -X utf8 tools/cards.py preview [OUTDIR]     original | English per card -> OUTDIR/area<k>.png
    python -X utf8 tools/cards.py count                tiles per layer against the original count

A card is three BG layers over each other (VRAM dump of story_intro f3700 on the original, work/qa/cardvram):
BG0 = the 8bpp hero picture 18/19/20[206] (no text), BG1 = the header エリアN (18/19/20[odd n]), BG2 = the chapter
title (18/19/20[n + 1]); BG1/BG2 tiles share char base 0x8000 (header at VRAM tile 174, title right after it), so
neither tileset may grow. Areas 1-5: header/title 207/208, 209/210, 211/212, 213/214, 215/216. Loaded by the
credits-style loader 0x0801E1D2..0x0801E206:
  20[n]  b'B2', w, h (metatiles: 15 x 10 = the screen), then w*h u16 metatile numbers (0 = empty)
  19[n]  b'a2', u16 N (metatile count), then (N + 2) & ~1 attribute bytes (all 0 here), then metatiles 0..N, each
         4 u16 tile numbers of 18[n] (top-left, top-right, bottom-left, bottom-right); metatile 0 is blank
  18[n]  4bpp tileset (bgtext.Tileset); tile 0 is transparent
(The staff roll's 19[n] is the same format: tools/credits.py reads its 600 attribute bytes as a transparent lead-in.)

gfx/cards.tsv rows use the gfx/bg.tsv columns (tools/bgtext.py load_rows): screen = the layer n, rect in screen
pixels, text, font, ink index, shadow (oN = outline), bg '-', align. Each layer with a row is redrawn from blank
(transparent), re-tiled with dedup, padded to its original tile count and written in place with its 19[n]
(metatile contents only; 20[n] and the attribute bytes are unchanged). Ink may only fall on map cells that hold a
metatile.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import res  # noqa: E402

AREAS = {1: (207, 208), 2: (209, 210), 3: (211, 212), 4: (213, 214), 5: (215, 216)}
LAYERS = tuple(n for pair in AREAS.values() for n in pair)
SPEC = ROOT / "gfx" / "cards.tsv"


def resource(d, g, n):
    for gg, i, o, s in res.resources(d):
        if gg == g and i == n:
            return o, s
    raise KeyError((g, n))


def decode(blob):
    """19[n] -> (head+attr bytes, metatiles [(tl, tr, bl, br)] 0..N, tail bytes)."""
    if blob[:2] != b"a2":
        raise ValueError("not an a2 metatile set")
    n = struct.unpack_from("<H", blob, 2)[0]
    start = 4 + ((n + 2) & ~1)
    words = struct.unpack_from(f"<{4 * (n + 1)}H", blob, start)
    mts = [tuple(words[4 * k:4 * k + 4]) for k in range(n + 1)]
    return bytes(blob[:start]), mts, bytes(blob[start + 8 * (n + 1):])


def encode(head, mts, tail):
    return head + b"".join(struct.pack("<4H", *m) for m in mts) + tail


def load(d, n):
    """-> (Tileset, Map, head, metatiles, tail) of layer n."""
    import bgtext
    to, ts = resource(d, 18, n)
    mo, ms = resource(d, 19, n)
    po, ps = resource(d, 20, n)
    head, mts, tail = decode(d[mo:mo + ms])
    return bgtext.Tileset(d[to:to + ts]), bgtext.Map(d[po:po + ps]), head, mts, tail


def cells(m, mts):
    """-> {(cx, cy): tile word} for every 8 px cell that a metatile covers (metatile 0 = no cell)."""
    out = {}
    for k, e in enumerate(m.e):
        if e == 0:
            continue
        my, mx = divmod(k, m.w)
        for j, t in enumerate(mts[e]):
            out[(2 * mx + j % 2, 2 * my + j // 2)] = t
    return out


def pixels(ts, m, mts):
    """-> {(x, y): (bank, index)} of the layer's non-transparent pixels."""
    out = {}
    for (cx, cy), t in cells(m, mts).items():
        if t & 0xFC00:
            raise ValueError(f"tile word {t:#x} with flags/bank bits")
        if t < ts.n0:
            px, b = ts.pixels(t), ts.tpal[t]
        elif t == ts.n0 and ts.extra is not None:   # slot n0 = the resource's extra tile (bgtext.Tileset.extra)
            px, b = [(ts.extra[i // 2] >> 4) if i & 1 else (ts.extra[i // 2] & 15) for i in range(64)], ts.tpal[-1]
        else:
            raise ValueError(f"tile {t} past the tileset ({ts.n0})")
        for i, v in enumerate(px):
            if v:
                out[(8 * cx + i % 8, 8 * cy + i // 8)] = (b, v)
    return out


def load_spec(path=SPEC):
    import bgtext
    return bgtext.load_rows(Path(path))


def redraw(d, n, rows, fonts=None):
    """-> (tileset blob, 19 blob, used tiles) for layer n with its spec rows."""
    import bgtext
    import font
    fonts = fonts or font.load_all()
    ts, m, head, mts, tail = load(d, n)
    if any(ts.pixels(0)):
        raise ValueError(f"card {n}: tile 0 is not transparent")
    bank = max(set(ts.tpal[1:]), key=ts.tpal[1:].count)
    canvas = {}
    for r in rows:
        bgtext.draw(canvas, r, fonts, lambda i: i)
    have = cells(m, mts)
    stray = sorted({(x // 8, y // 8) for (x, y), v in canvas.items() if v and (x // 8, y // 8) not in have})
    if stray:
        raise ValueError(f"card {n}: ink on cells without a metatile: {stray[:6]}")
    blank = bytes(32)
    tiles, index = [blank], {blank: 0}
    new = [mts[0]]
    for k in range(1, len(mts)):
        pos = [(mx, my) for i, e in enumerate(m.e) if e == k for my, mx in [divmod(i, m.w)]]
        if len(pos) != 1:
            raise ValueError(f"card {n}: metatile {k} used {len(pos)} times")
        mx, my = pos[0]
        words = []
        for j in range(4):
            cx, cy = 2 * mx + j % 2, 2 * my + j // 2
            t = bgtext.Tileset.encode([canvas.get((8 * cx + i % 8, 8 * cy + i // 8), 0) for i in range(64)])
            if t not in index:
                index[t] = len(tiles)
                tiles.append(t)
            words.append(index[t])
        new.append(tuple(words))
    used = len(tiles)
    if used > ts.n0:
        raise ValueError(f"card {n}: {used} tiles > the original {ts.n0}: shorter text or grid lettering")
    tsz = resource(d, 18, n)[1]
    msz = resource(d, 19, n)[1]
    ts.tiles = tiles + [blank] * (ts.n0 - used)
    ts.tpal = [bank] * ts.n0
    blob = ts.blob()
    mblob = encode(head, new, tail)
    if len(blob) > tsz or len(mblob) != msz:
        raise ValueError(f"card {n}: blob sizes changed ({len(blob)}/{tsz}, {len(mblob)}/{msz})")
    return blob, mblob, used


def apply(rom, orig, rows=None):
    """Redraw every card layer with spec rows, in place. -> written ranges."""
    rows = load_spec() if rows is None else rows
    out = []
    for n in sorted({r["screen"][1] for r in rows}):
        if n not in LAYERS:
            raise ValueError(f"cards.tsv: {n} is not a card layer {LAYERS}")
        blob, mblob, _ = redraw(bytes(orig), n, [r for r in rows if r["screen"][1] == n])
        for g, b in ((18, blob), (19, mblob)):
            o, _ = resource(orig, g, n)
            rom[o:o + len(b)] = b
            out.append((o, o + len(b)))
    return out


def render(d, ns):
    """-> 160 rows of 240 RGB pixels: layers ns drawn over a dark grey ground."""
    import bgscreens
    img = [[b"\x30\x30\x30"] * 240 for _ in range(160)]
    for n in ns:
        ts, m, _, mts, _ = load(d, n)
        pal = ts.pal
        for (x, y), (b, v) in pixels(ts, m, mts).items():
            if x < 240 and y < 160:
                img[y][x] = bgscreens.rgb(pal[16 * b + v] if len(pal) > 16 * b + v else pal[v])
    return [b"".join(r) for r in img]


def main():
    import argparse
    import check_rom
    import sweep
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("preview", "count"))
    ap.add_argument("outdir", nargs="?", default="work/qa/gfx/cards")
    a = ap.parse_args()
    d = check_rom.original()
    rows = load_spec()
    if a.cmd == "count":
        for n in sorted({r["screen"][1] for r in rows}):
            _, _, used = redraw(d, n, [r for r in rows if r["screen"][1] == n])
            print(f"card {n}: {used} tiles, original {load(d, n)[0].n0}")
        return 0
    rom = bytearray(d)
    apply(rom, d, rows)
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    for k, ns in AREAS.items():
        x, y = render(d, ns), render(bytes(rom), ns)
        p = Path(a.outdir) / f"area{k}.png"
        sweep.png(str(p), 2 * 240 + 8, 160, [u + b"\xff\x00\xff" * 8 + v for u, v in zip(x, y)])
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
