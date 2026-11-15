"""attract.py: the attract-mode title intro in English (docs/re/graphics.md §Attract title).

    python -X utf8 tools/attract.py preview [OUTDIR]    original | English of the intro's final frame -> OUTDIR/attract.png
    python -X utf8 tools/attract.py count               tiles / metatiles used against the budgets

After the attract story clip (scene 17) the game builds the title in BG layers before it loads the real title
picture 5[20] (f1263 of the `attract_story` warp): stars + Earth + copyright 18/19/20[245] (4bpp), the logo
18/19/20[246] (8bpp, kept: D5), and the subtitle 装着!地球の戦士たち from tileset 18[247] (8bpp, 112 tiles) and metatiles
19[247] (N 149) drawn by two maps: 20[247] = its top half, 20[248] = its bottom half (with the ruby). The two halves
slide in from opposite sides, then rest at scroll 0. Same metatile format as the area cards (tools/cards.py):
  20[n]  b'B2', w 32, h 10 (metatiles), u16 metatile numbers (0 = none); only columns 0-15 are on screen
  19[n]  b'a2', u16 N, attribute bytes (0), metatiles 0..N of 4 u16 tile numbers (TL, TR, BL, BR)

gfx/attract.tsv rows use the gfx/bg.tsv columns (tools/bgtext.py load_rows):
- layer 247: the English subtitle drawn on a blank canvas, ink/outline = 8bpp palette indices of 18[247] (0 is
  transparent). Pixel rows above SPLIT go to map 20[247], the rest to 20[248], so the halves still slide. Tiles and
  metatiles are rebuilt with dedup and padded to the original counts; all three resources keep their size.
- layer 245: drawn over the original picture. A row with a bg clears its rect to black; ink pixels are white. Each
  changed tile is re-encoded in its own palette bank (nearest colour), so the rest of the picture is untouched.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bgtext  # noqa: E402
import cards  # noqa: E402
import sweep  # noqa: E402

SPEC = ROOT / "gfx" / "attract.tsv"
SUB, MAPS, COPY = 247, (247, 248), 245
SPLIT = 102         # subtitle pixel rows < SPLIT -> map 20[247] (top half), the rest -> 20[248]
COLS, ROWS = 16, 10  # metatiles on screen
BLACK, WHITE = (0, 0, 0), (248, 248, 248)


def rgb(c):
    return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)


class Tileset8:
    """18[n] 8bpp tileset: 00 50 31 xx, u16 nt, 256 colours, nt per-tile bytes, gap byte, nt*64 tile bytes, tail."""

    def __init__(self, data):
        pal, tpal, tiles, bpp = sweep.p70_parse(data)
        if bpp != 8:
            raise ValueError("not an 8bpp tileset")
        self.pal, self.tpal = pal, bytes(tpal)
        self.n0 = len(tpal)
        start = 6 + 512 + self.n0 + 1
        self.pre = bytes(data[:start])
        self.tiles = [bytes(tiles[64 * i:64 * i + 64]) for i in range(self.n0)]
        self.tail = bytes(data[start + 64 * self.n0:])

    def blob(self):
        return self.pre + b"".join(self.tiles) + self.tail


def load_spec(path=SPEC):
    return bgtext.load_rows(Path(path))


def canvas_for(rows, fonts):
    """Rows drawn into {(x, y): index}; font 'normal*2' = the title's scaled lettering (objtext.scaled_text)."""
    import objtext
    canvas = {}
    for r in rows:
        base, _, scale = r["font"].partition("*")
        if scale:
            objtext.scaled_text(canvas, dict(r, font=base, shadow=dict(r["shadow"], rings=[])), fonts, int(scale))
        else:
            bgtext.draw(canvas, r, fonts, lambda i: i)
    return canvas


def redraw_sub(d, rows, fonts):
    """-> {(group, n): blob} for 18[247], 19[247], 20[247], 20[248], and (tiles, metatiles) used."""
    to, tsz = cards.resource(d, 18, SUB)
    mo, msz = cards.resource(d, 19, SUB)
    ts = Tileset8(d[to:to + tsz])
    head, mts, tail = cards.decode(d[mo:mo + msz])
    canvas = canvas_for(rows, fonts)
    if any(x >= 8 * 2 * COLS or y >= 8 * 2 * ROWS for (x, y), v in canvas.items() if v):
        raise ValueError("attract subtitle: ink off the 256 x 160 layer")
    blank = bytes(64)
    tiles, tindex = [blank], {blank: 0}
    metas, mindex = [mts[0]], {tuple(mts[0]): 0}
    maps = {}
    for k, mapn in enumerate(MAPS):
        po, psz = cards.resource(d, 20, mapn)
        m = bgtext.Map(d[po:po + psz])
        e = [0] * len(m.e)
        for my in range(ROWS):
            for mx in range(COLS):
                words = []
                for j in range(4):
                    cx, cy = 2 * mx + j % 2, 2 * my + j // 2
                    px = []
                    for i in range(64):
                        x, y = 8 * cx + i % 8, 8 * cy + i // 8
                        mine = (y < SPLIT) == (k == 0)
                        px.append(canvas.get((x, y), 0) if mine else 0)
                    t = bytes(max(v, 0) for v in px)
                    if t not in tindex:
                        tindex[t] = len(tiles)
                        tiles.append(t)
                    words.append(tindex[t])
                w = tuple(words)
                if w == (0, 0, 0, 0):
                    continue
                if w not in mindex:
                    mindex[w] = len(metas)
                    metas.append(w)
                e[my * m.w + mx] = mindex[w]
        m.e = e
        maps[(20, mapn)] = m.blob()
        if len(maps[(20, mapn)]) != psz:
            raise ValueError(f"attract: map 20[{mapn}] size changed")
    if len(tiles) > ts.n0:
        raise ValueError(f"attract subtitle: {len(tiles)} tiles > {ts.n0}: shorter text")
    if len(metas) > len(mts):
        raise ValueError(f"attract subtitle: {len(metas)} metatiles > {len(mts)}")
    used = (len(tiles), len(metas))
    ts.tiles = tiles + [blank] * (ts.n0 - len(tiles))
    metas += [(0, 0, 0, 0)] * (len(mts) - len(metas))
    out = {(18, SUB): ts.blob(), (19, SUB): cards.encode(head, metas, tail)}
    out.update(maps)
    for (g, n), b in out.items():
        if len(b) != cards.resource(d, g, n)[1]:
            raise ValueError(f"attract: {g}[{n}] size changed")
    return out, used


def redraw_copy(d, rows, fonts):
    """-> {(18, 245): blob}, changed tile count: rows drawn over the original picture, tiles re-encoded in place."""
    to, tsz = cards.resource(d, 18, COPY)
    ts, m, _, mts, _ = cards.load(d, COPY)
    cl = cards.cells(m, mts)
    canvas = canvas_for(rows, fonts)     # bg rows give their bg index (cleared), ink rows their ink index
    clear = set()
    for r in rows:
        if r["bg"] is not None:
            x0, y0, w, h = r["rect"]
            clear |= {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
    inks = {v for r in rows if r["bg"] is None for v in r["ink"]}   # text rows: bg '-', ink 15 (any index != bg)
    ink = {p for p, v in canvas.items() if v in inks}
    touched = {(x // 8, y // 8) for (x, y) in clear | ink}
    changed = 0
    for (cx, cy) in sorted(touched):
        if (cx, cy) not in cl:
            raise ValueError(f"attract copyright: cell {cx},{cy} has no metatile")
        t = cl[(cx, cy)]
        bank = ts.tpal[t]
        cols = [rgb(c) for c in ts.pal[16 * bank:16 * bank + 16]]
        px = ts.pixels(t)
        new = []
        for i, v in enumerate(px):
            p = (8 * cx + i % 8, 8 * cy + i // 8)
            want = WHITE if p in ink else BLACK if p in clear else None
            if want is None:
                new.append(v)
            else:
                new.append(min(range(1, 16), key=lambda k: sum((a - b) ** 2 for a, b in zip(cols[k], want))))
        if new != px:
            if sum(1 for c in cl.values() if c == t) != 1:
                raise ValueError(f"attract copyright: tile {t} is shared")
            ts.tiles[t] = bgtext.Tileset.encode(new)
            changed += 1
    blob = ts.blob()     # the resource's 0-3 alignment bytes after the blob stay as they are
    if len(blob) > tsz:
        raise ValueError("attract: 18[245] grew")
    return {(18, COPY): blob}, changed


def build(d, rows=None, fonts=None):
    import font
    rows = load_spec() if rows is None else rows
    fonts = fonts or font.load_all()
    out = {}
    sub = [r for r in rows if r["screen"][0] == SUB]
    cop = [r for r in rows if r["screen"][0] == COPY]
    if len(sub) + len(cop) != len(rows):
        raise ValueError(f"attract.tsv: layers must be {SUB} or {COPY}")
    used = changed = None
    if sub:
        o, used = redraw_sub(d, sub, fonts)
        out.update(o)
    if cop:
        o, changed = redraw_copy(d, cop, fonts)
        out.update(o)
    return out, used, changed


def apply(rom, orig, rows=None):
    """Write the attract title layers in place. -> written ranges."""
    out, _, _ = build(bytes(orig), rows)
    ranges = []
    for (g, n), b in sorted(out.items()):
        o, _ = cards.resource(orig, g, n)
        rom[o:o + len(b)] = b
        ranges.append((o, o + len(b)))
    return ranges


def render(d):
    """-> PIL image of the rested title: 245, 246, 247 (map 247 + map 248) composed, 240 x 160."""
    from PIL import Image
    im = Image.new("RGB", (240, 160), (0, 0, 0))
    ts5, m5, _, mts5, _ = cards.load(d, COPY)
    for (x, y), (b, v) in cards.pixels(ts5, m5, mts5).items():
        if x < 240 and y < 160:
            im.putpixel((x, y), rgb(ts5.pal[16 * b + v]))
    for tn, maps in ((246, (246,)), (SUB, MAPS)):
        to, tsz = cards.resource(d, 18, tn)
        ts = Tileset8(d[to:to + tsz])
        mo, msz = cards.resource(d, 19, tn)
        _, mts, _ = cards.decode(d[mo:mo + msz])
        for mapn in maps:
            po, psz = cards.resource(d, 20, mapn)
            for (cx, cy), t in cards.cells(bgtext.Map(d[po:po + psz]), mts).items():
                if t >= ts.n0:
                    continue
                for i, v in enumerate(ts.tiles[t]):
                    x, y = 8 * cx + i % 8, 8 * cy + i // 8
                    if v and x < 240 and y < 160:
                        im.putpixel((x, y), rgb(ts.pal[v]))
    return im


def main():
    import check_rom
    cmd = sys.argv[1] if len(sys.argv) > 1 else "count"
    orig = check_rom.original()
    out, used, changed = build(orig)
    if cmd == "count":
        print(f"subtitle: {used[0]} of 112 tiles, {used[1]} of 150 metatiles; copyright: {changed} tiles changed")
    elif cmd == "preview":
        from PIL import Image
        new = bytearray(orig)
        for (g, n), b in out.items():
            o, _ = cards.resource(orig, g, n)
            new[o:o + len(b)] = b
        odir = Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / "work" / "qa" / "attract")
        odir.mkdir(parents=True, exist_ok=True)
        im = Image.new("RGB", (480, 160))
        im.paste(render(orig), (0, 0))
        im.paste(render(bytes(new)), (240, 0))
        im.resize((960, 320), Image.NEAREST).save(odir / "attract.png")
        print(odir / "attract.png")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
