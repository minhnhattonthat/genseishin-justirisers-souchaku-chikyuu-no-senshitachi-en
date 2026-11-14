"""bgtext.py: English lettering for BG-screen graphics text (groups 18 tileset + 20 map, docs/re/graphics.md).

    python -X utf8 tools/bgtext.py probe ROM N x,y,w,h        palette (bank, index) histogram of a rect of screen N
    python -X utf8 tools/bgtext.py render ROM N OUT.png [--zoom 3] [--grid]   screen N as the game draws it
    python -X utf8 tools/bgtext.py preview OUTDIR [--zoom 2]  every screen in gfx/bg.tsv, original | English
    python -X utf8 tools/bgtext.py count ROM [TSV]            tiles per changed tileset vs its VRAM budget (exit 1 over)

gfx/bg.tsv rows (tab-separated, '#' comments), applied by insert.build through apply(rom, orig):
    screen  rect      text              font    ink  shadow  bg  align  note
    653     40,64,96,16  Kids Mode      normal  15   1       2   c      mode select button
  screen  decimal index n of 18[n]/20[n], or T:M = map 20[M] drawn with tileset 18[T] (an overlay layer the game
          loads with another screen's tiles, e.g. 653:654 mode select highlight: reslog.lua shows the pairs). Every
          map that shares the tileset must be listed (or be an 18[i]/20[i] pair) so its tiles are never recycled.
  rect    x,y,w,h in pixels on the screen; every pixel inside is cleared to `bg` (or kept with bg '-'), then the text
          is drawn. A rect may cut through tiles: pixels outside it are kept (tests/test_bgtext.py checks).
  text    '|' separates lines (16 px apart for normal, 9 for small), the block centred vertically on its ink rows
  font    normal (16-row game font) / small (8-row), optional @BANK = palette bank of the indices (default: the
          bank of the rect's centre cell). Pixels are kept as colours; each cell takes a bank holding all its colours.
  ink     index, or a/b/.. bands split over each line's ink rows top to bottom
  shadow  '-' none, N drop shadow at +1,+1, oN 1 px outline, oN+M outline plus drop shadow M
  bg      index the rect is cleared to, '-' to keep the pixels, cN: each pixel row cleared to the colour of column N
          in that row (gradient banners; N outside the text)
  align   l / c / r, then optional b (bold: ink doubled 1 px right) and a tracking number (c-1: 1 px tighter),
          or g (grid: each glyph centred in its own 8 px cell, the line starting on a cell boundary, every line at
          the font's full ink height). Grid letters repeat as whole tiles, so a label costs only its new letters:
          use it where the VRAM tile budget is tight (gfx/bg_budget.tsv). Keep the rect's y on the cell grid too.

Tiles: the rect's cells are re-encoded; a new tile matching an existing one (same pixels, same per-tile palette
bank) reuses it, else it takes a slot that no map sharing this tileset references any more (the old Japanese), else
it is appended. Each changed tileset / map is written once to free space (GFX_FREE) and every group 18 / 20 entry
that pointed at the old one is repointed (self-relative u32). Returns the written ranges for the write log.
"""
import argparse
import csv
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import font  # noqa: E402
import res  # noqa: E402
import sweep  # noqa: E402

TSV = ROOT / "gfx" / "bg.tsv"
GFX_FREE, GFX_END = 0xE00000, 0xF00000   # tbl/allowed.txt: free space after the relocated script block


class Tileset:
    def __init__(self, data):
        p = sweep.p70_parse(data)
        if p is None:
            raise ValueError("not a 00 70/50 31 tileset")
        self.head = bytes(data[:4])
        self.pal, tpal, tiles, self.bpp = p
        self.gap = data[6 + 2 * len(self.pal) + len(tpal)]   # the byte between banks and tiles (sweep.p70_parse)
        if self.bpp != 4:
            raise ValueError("8bpp tileset: not supported yet")
        self.tpal = list(tpal)
        self.tiles = [bytes(tiles[32 * i:32 * i + 32]) for i in range(len(self.tpal))]
        self.n0 = len(self.tiles)

    def blob(self):
        nt = len(self.tiles)
        out = bytearray(self.head) + struct.pack("<H", nt) + struct.pack(f"<{len(self.pal)}H", *self.pal)
        out += bytes(self.tpal) + bytes([self.gap])
        for t in self.tiles:
            out += t
        return bytes(out)

    def pixels(self, t):
        """-> 64 colour indices (row-major) of tile t."""
        b = self.tiles[t]
        return [(b[i // 2] >> 4) if i & 1 else (b[i // 2] & 15) for i in range(64)]

    @staticmethod
    def encode(px):
        return bytes(px[2 * i] | px[2 * i + 1] << 4 for i in range(32))


class Map:
    def __init__(self, data):
        if data[:2] not in (b"B2", b"C1"):
            raise ValueError("not a B2/C1 map")
        self.head, self.w, self.h = bytes(data[:2]), data[2], data[3]
        self.e = list(struct.unpack_from(f"<{self.w * self.h}H", data, 4))

    def blob(self):
        return self.head + bytes([self.w, self.h]) + struct.pack(f"<{len(self.e)}H", *self.e)


def cell_pixels(ts, e):
    """Map entry -> 64 indices as drawn (flips applied)."""
    px = ts.pixels(e & 0x3FF)
    hf, vf = e >> 10 & 1, e >> 11 & 1
    return [px[(7 - y if vf else y) * 8 + (7 - x if hf else x)] for y in range(8) for x in range(8)]


def load_rows(path=TSV):
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
    for r in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        r += [""] * (9 - len(r))
        x, y, w, h = (int(v) for v in r[1].split(","))
        al = r[7] or "c"
        fnt, _, bank = (r[3] or "normal").partition("@")
        t, _, m = r[0].partition(":")
        rows.append({"screen": (int(t), int(m or t)), "rect": (x, y, w, h), "text": r[2], "font": fnt,
                     "bank": int(bank) if bank else None,
                     "ink": [int(v) for v in r[4].split("/")], "shadow": parse_shadow(r[5]),
                     "bg": None if r[6] in ("", "-") else r[6] if r[6].startswith("c") else int(r[6]),
                     "align": al[0], "grid": "g" in al,
                     "bold": "b" in al, "track": int(al[1:].replace("b", "").replace("g", "") or 0), "note": r[8]})
    return rows


def parse_shadow(s):
    """'-' none, 'N' drop shadow N at +1,+1, 'oN' 1 px outline N, 'oN+M' outline N plus drop shadow M."""
    out = {"outline": None, "drop": None}
    if s in ("", "-"):
        return out
    if s.startswith("o"):
        o, _, dr = s[1:].partition("+")
        out["outline"] = int(o)
        out["drop"] = int(dr) if dr else None
    else:
        out["drop"] = int(s)
    return out


def text_px(text, glyphs):
    return sum(glyphs[c]["width"] for c in text)


def ink_rows(text, glyphs, nrows):
    rows = [r for c in text if glyphs[c]["rows"] for r in range(nrows) if glyphs[c]["rows"][r]]
    return (min(rows), max(rows)) if rows else (0, nrows - 1)


def draw(canvas, row, fonts, col, sample=None):
    """Draw one row into canvas {(x, y): colour (rgb555, -1 = transparent)}; col(index) -> colour in the row's bank.
    sample(x, y) -> the original screen's colour there (for bg 'cN': each row cleared to column N's colour)."""
    x0, y0, w, h = row["rect"]
    if isinstance(row["bg"], str):   # 'cN': gradient backgrounds (banners) keep their per-row colour
        n = int(row["bg"][1:])
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                canvas[(x, y)] = sample(n, y)
    elif row["bg"] is not None:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                canvas[(x, y)] = col(row["bg"])
    glyphs = fonts[row["font"]]
    nrows = 16 if row["font"] == "normal" else 8
    lines = row["text"].split("|")
    pitch = 16 if row["font"] == "normal" else 9
    grid = row.get("grid")
    # grid: one ink range for the whole font, so every label sits on the same rows (tiles repeat across labels)
    ref = "".join(c for c in glyphs if c.isascii() and c.isalnum()) if grid else row["text"].replace("|", "")
    lo, hi = ink_rows(ref, glyphs, nrows)
    block = (len(lines) - 1) * pitch + (hi - lo + 1)
    top = y0 + (h - block) // 2 - lo
    ink = []
    for k, line in enumerate(lines):
        bold = 1 if row["bold"] else 0   # bold: every ink pixel doubled 1 px right, advance + 1
        if grid:
            tw = 8 * len(line)
        else:
            tw = text_px(line, glyphs) - 2 + (row["track"] + bold) * (len(line) - 1) + bold   # advance: 2 px spacing
        pad = 2 if row["shadow"]["outline"] is not None and not grid else 0
        if tw + pad > w:
            raise ValueError(f"{label(row['screen'])} {line!r}: {tw + pad} px > rect {w} px")
        x = x0 + {"l": 0, "c": (w - tw) // 2, "r": w - tw}[row["align"]]
        if grid:   # snap to the cell grid, staying inside the rect
            x = min(max(-(-x0 // 8) * 8, (x + 4) // 8 * 8), (x0 + w - tw) // 8 * 8)
            if x < x0:
                raise ValueError(f"{label(row['screen'])} {line!r}: no cell-aligned start inside the rect")
        y = top + k * pitch
        for c in line:
            g = glyphs[c]
            gx0 = 0
            if grid and g["rows"]:   # centre the glyph's ink columns in its cell
                cols = [gx for gx in range(16) if any(r >> (15 - gx) & 1 for r in g["rows"])]
                if cols:
                    gx0 = (8 - (cols[-1] - cols[0] + 1)) // 2 - cols[0]
            for gy in range(nrows if g["rows"] else 0):
                for gx in range(16):
                    if g["rows"][gy] >> (15 - gx) & 1:
                        ink.append((x + gx0 + gx, y + gy))
                        if bold:
                            ink.append((x + gx0 + gx + 1, y + gy))
            x += 8 if grid else g["width"] + row["track"] + bold
    inside = lambda p: x0 <= p[0] < x0 + w and y0 <= p[1] < y0 + h  # noqa: E731
    sh = row["shadow"]
    put = lambda p, v: canvas.__setitem__(p, col(v)) if inside(p) else None  # noqa: E731
    if sh["drop"] is not None:   # drop shadow at +1,+1 (beyond the outline when there is one)
        d = 2 if sh["outline"] is not None else 1
        for px, py in ink:
            for dx, dy in ((d, d), (d - 1, d), (d, d - 1)) if d == 2 else ((1, 1),):
                put((px + dx, py + dy), sh["drop"])
    if sh["outline"] is not None:
        for px, py in ink:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    put((px + dx, py + dy), sh["outline"])
    bands = row["ink"]
    for k, line in enumerate(lines):   # ink bands split each line's ink rows evenly, top to bottom
        y = top + k * pitch
        for px, py in ink:
            if y + lo <= py <= y + hi:
                b = min(len(bands) - 1, (py - y - lo) * len(bands) // (hi - lo + 1))
                put((px, py), bands[b])
    return canvas


def redraw(d, rows):
    """-> {tileset_off: Tileset}, {map_off: Map}, {screen: (tileset_off, map_off)} with rows applied."""
    R = {(g, i): o for g, i, o, _ in res.resources(d)}
    sizes = {o: s for _, _, o, s in res.resources(d)}
    fonts = font.load_all()
    tsets, maps, where = {}, {}, {}
    by_ts = {}
    for i in range(1001):
        by_ts.setdefault(R[(18, i)], set()).add(R[(20, i)])
    for row in rows:
        n = row["screen"]
        to, mo = R[(18, n[0])], R[(20, n[1])]
        where[n] = (to, mo)
        by_ts.setdefault(to, set()).add(mo)   # a T:M pair the game draws: M uses T's tiles
        if to not in tsets:
            tsets[to] = Tileset(d[to:to + sizes[to]])
        if mo not in maps:
            maps[mo] = Map(d[mo:mo + sizes[mo]])
    # per tileset: refcount over every map that uses it (valid maps only)
    for to, ts in tsets.items():
        users = []
        for mo in by_ts[to]:
            if mo not in maps:
                try:
                    m = Map(d[mo:mo + sizes[mo]])
                except ValueError:
                    continue
                if 4 + 2 * m.w * m.h > sizes[mo]:
                    continue
            users.append(mo)
        ts.users = users
    screen_cells = {}
    for r in rows:
        x0, y0, w, h = r["rect"]
        screen_cells.setdefault(r["screen"], set()).update(
            (cx, cy) for cy in range(y0 // 8, (y0 + h - 1) // 8 + 1) for cx in range(x0 // 8, (x0 + w - 1) // 8 + 1))
    order = sorted(screen_cells)
    orig_ts = {}
    for si, n in enumerate(order):
        to, mo = where[n]
        ts, mp = tsets[to], maps[mo]
        # Read pixels from the untouched tileset: an earlier screen may already have recycled a slot that this
        # screen's cells (re-encoded below) still point at.
        ots = orig_ts.setdefault(to, Tileset(d[to:to + sizes[to]]))
        canvas = {}
        my_rows = [r for r in rows if r["screen"] == n]
        cells = screen_cells[n]
        base = min(ts.tpal)
        bank_pal = lambda b: [-1] + ts.pal[(b - base) * 16 + 1:(b - base) * 16 + 16]  # noqa: E731
        for cx, cy in cells:
            e = mp.e[cy * mp.w + cx]
            if e & 0x3FF >= len(ots.tiles):
                # Slot past the tileset: the game shows a leftover VRAM tile there that no resource holds (659:660's
                # Bonus button corner) and that differs once the English loads. Pixels outside the rects copy the
                # nearest real cell to the left in the same row (button edges and shades run horizontally).
                src = next((x for x in range(cx - 1, -1, -1) if mp.e[cy * mp.w + x] & 0x3FF < len(ots.tiles)), None)
                for k in range(64):
                    if src is None:
                        canvas[(cx * 8 + k % 8, cy * 8 + k // 8)] = -1
                        continue
                    e0 = mp.e[cy * mp.w + src]
                    canvas[(cx * 8 + k % 8, cy * 8 + k // 8)] = bank_pal(ots.tpal[e0 & 0x3FF])[cell_pixels(ots, e0)[k]]
                continue
            bp = bank_pal(ots.tpal[e & 0x3FF])
            for k, v in enumerate(cell_pixels(ots, e)):
                canvas[(cx * 8 + k % 8, cy * 8 + k // 8)] = bp[v]
        for r in my_rows:
            if r["bank"] is None:
                x0, y0, w, h = r["rect"]
                r["bank"] = ots.tpal[mp.e[(y0 + h // 2) // 8 * mp.w + (x0 + w // 2) // 8] & 0x3FF]
            bp = bank_pal(r["bank"])

            def sample(x, y, ots=ots, mp=mp):
                e0 = mp.e[(y // 8) * mp.w + x // 8]
                return bank_pal(ots.tpal[e0 & 0x3FF])[cell_pixels(ots, e0)[(y % 8) * 8 + x % 8]]
            draw(canvas, r, fonts, lambda v, bp=bp: bp[v], sample)
        refs = Counter()
        for mo2 in ts.users:
            m = maps.get(mo2) or Map(d[mo2:mo2 + sizes[mo2]])
            refs.update(e & 0x3FF for e in m.e)
        before = Counter(refs)
        for cx, cy in cells:
            refs[mp.e[cy * mp.w + cx] & 0x3FF] -= 1
        # Cells of screens still to come on this tileset are re-encoded too, so their tiles are free now as well
        # (an atlas map processed later can free the tiles an earlier screen needs).
        for n2 in order[si + 1:]:
            if where[n2][0] == to and where[n2][1] != mo:
                m2 = maps[where[n2][1]]
                for cx, cy in screen_cells[n2]:
                    refs[m2.e[cy * m2.w + cx] & 0x3FF] -= 1
        # Recycle only tiles the replaced cells freed: a slot no map of this tileset uses can still be drawn by
        # another layer sharing the char block (mode select's highlight overlay showed such slots as garbage).
        # gfx/bg_budget.tsv may list spare slots: tiles no map uses, checked against the live VRAM maps.
        spare = load_spare().get(n[0], set())
        free = [t for t in range(len(ts.tiles)) if (before[t] > 0 or t in spare) and refs[t] <= 0 and t != 0]
        index = {(ts.tiles[t], ts.tpal[t]): t for t in range(len(ts.tiles)) if refs[t] > 0}
        for cx, cy in sorted(cells, key=lambda c: (c[1], c[0])):
            e = mp.e[cy * mp.w + cx]
            cols = [canvas[(cx * 8 + k % 8, cy * 8 + k // 8)] for k in range(64)]
            need = set(cols) - {-1}
            banks = ([ots.tpal[e & 0x3FF]] if e & 0x3FF < len(ots.tpal) else []) + sorted(set(ts.tpal))
            fits = [b for b in dict.fromkeys(banks) if need <= set(bank_pal(b))]
            if not fits:
                raise ValueError(f"{label(n)} cell {cx},{cy}: no palette bank holds colours "
                                 + " ".join(f"{c:04X}" for c in sorted(need)))
            # Any bank holding the colours will do: prefer one where the same pixels already exist as a tile
            # (blank cells and plain fills otherwise cost one tile per bank).
            enc = [(b, Tileset.encode([0 if c == -1 else bank_pal(b).index(c, 1) for c in cols])) for b in fits]
            bank, tile = next(((b, tl) for b, tl in enc if (tl, b) in index), enc[0])
            t = index.get((tile, bank))
            if t is None:
                if free:
                    t = free.pop(0)
                    ts.tiles[t], ts.tpal[t] = tile, bank
                else:
                    # A map may use slots past the tileset (VRAM after it: blank, or another layer's tiles that
                    # tools/bgvram.py shows). Appending pads over them, so the budget check below decides.
                    # (only slots still referenced: a past-the-end cell inside a rect was just re-encoded)
                    while len(ts.tiles) <= max((k for k, v in refs.items() if v > 0), default=-1):
                        ts.tiles.append(bytes(32))
                        ts.tpal.append(min(ts.tpal))
                    t = len(ts.tiles)
                    ts.tiles.append(tile)
                    ts.tpal.append(bank)
                index[(tile, bank)] = t
            refs[t] += 1
            mp.e[cy * mp.w + cx] = (e & 0xF000) | t
    budget = load_budget()
    tn = {R[(18, i)]: i for i in range(1001)}
    for to, ts in tsets.items():   # the tileset is copied to VRAM as one run: growing it overwrites the next layer
        n = tn.get(to)
        cap = budget.get(n, ts.n0)
        if len(ts.tiles) > cap:
            raise ValueError(f"tileset 18[{n}]: {len(ts.tiles)} tiles > budget {cap} (gfx/bg_budget.tsv; "
                             f"measure with tools/bgvram.py): fewer or smaller labels")
    return tsets, maps, where


BUDGET = ROOT / "gfx" / "bg_budget.tsv"


def _budget_rows(path):
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip() and not ln.startswith("#"):
                yield ln.split("\t")


def load_budget(path=BUDGET):
    """{tileset index: max tiles}: VRAM room measured with tools/bgvram.py. Absent or '-' = the original count."""
    return {int(f[0]): int(f[1]) for f in _budget_rows(path) if f[1] != "-"}


def load_spare(path=BUDGET):
    """{tileset index: {tile}}: column 3 ('131-136,143' or '-'), tiles that no map of the tileset references and no
    live BG map in a VRAM dump of the screen uses, so a redraw may recycle them."""
    out = {}
    for f in _budget_rows(path):
        if len(f) > 2 and f[2] not in ("", "-"):
            s = out.setdefault(int(f[0]), set())
            for part in f[2].split(","):
                a, _, b = part.partition("-")
                s.update(range(int(a), int(b or a) + 1))
    return out


def apply(rom, orig, rows=None):
    """Write every redrawn tileset/map into free space and repoint groups 18/20. -> written ranges."""
    rows = load_rows() if rows is None else rows
    if not rows:
        return []
    tsets, maps, _ = redraw(bytes(orig), rows)
    gs = res.groups(bytes(orig))
    out, a = [], GFX_FREE
    for group, objs in ((18, tsets), (20, maps)):
        base, offs = gs[group]
        for old, obj in sorted(objs.items()):
            blob = obj.blob()
            if a + len(blob) > GFX_END:
                raise SystemExit("bgtext: graphics free space exhausted")
            rom[a:a + len(blob)] = blob
            out.append((a, a + len(blob)))
            for i, o in enumerate(offs):
                if o == old:
                    p = base + 4 * i
                    struct.pack_into("<I", rom, p, (a - p) & 0xFFFFFFFF)
                    out.append((p, p + 4))
            a = (a + len(blob) + 3) & ~3
    return out


def oob_cells(d, n):
    """Cells of screen n whose tile lies past its tileset (VRAM after it; rendered blank once padded)."""
    R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
    (to, tsz), (mo, msz) = R[(18, n[0])], R[(20, n[1])]
    ts, mp = Tileset(d[to:to + tsz]), Map(d[mo:mo + msz])
    return {(k % mp.w, k // mp.w) for k, e in enumerate(mp.e) if e & 0x3FF >= len(ts.tiles)}


def label(n):
    return f"s{n[0]:04d}" if n[0] == n[1] else f"s{n[0]:04d}_{n[1]:04d}"


def parse_screen(s):
    t, _, m = s.partition(":")
    return int(t), int(m or t)


def render_screen(d, n, zoom=1, grid=False):
    import bgscreens
    R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
    (to, tsz), (mo, msz) = R[(18, n[0])], R[(20, n[1])]
    w, h, rows = bgscreens.render(d[to:to + tsz], d[mo:mo + msz])
    out = []
    for y, row in enumerate(rows):
        line = bytearray()
        for x in range(0, len(row), 3):
            c = row[x:x + 3]
            if grid and (x // 3 % 8 == 0 or y % 8 == 0):
                c = bytes(v // 2 + 64 for v in c)
            line += c * zoom
        out.extend([line] * zoom)
    return w * zoom, h * zoom, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("rom")
    p.add_argument("n", type=parse_screen)
    p.add_argument("rect")
    p = sub.add_parser("ink")
    p.add_argument("rom")
    p.add_argument("n", type=parse_screen)
    p.add_argument("rect")
    p.add_argument("idx", help="ink indices, comma-separated (any bank)")
    p = sub.add_parser("render")
    p.add_argument("rom")
    p.add_argument("n", type=parse_screen)
    p.add_argument("out")
    p.add_argument("--zoom", type=int, default=3)
    p.add_argument("--grid", action="store_true")
    p = sub.add_parser("preview")
    p.add_argument("rom")
    p.add_argument("outdir")
    p.add_argument("--zoom", type=int, default=2)
    p = sub.add_parser("count")
    p.add_argument("rom")
    p.add_argument("tsv", nargs="?", default=str(TSV))
    a = ap.parse_args()
    d = Path(a.rom).read_bytes()
    if a.cmd == "count":   # draft rows: tiles per changed tileset against its budget, without stopping on it
        budget = load_budget()
        tn = {o: i for g, i, o, _ in res.resources(d) if g == 18}
        orig_budget = globals()["load_budget"]
        globals()["load_budget"] = lambda path=None: {i: 1 << 20 for i in range(1001)}
        try:
            tsets, _, _ = redraw(d, load_rows(Path(a.tsv)))
        finally:
            globals()["load_budget"] = orig_budget
        bad = 0
        for to, ts in sorted(tsets.items()):
            cap = budget.get(tn[to], ts.n0)
            bad += len(ts.tiles) > cap
            print(f"18[{tn[to]}]: {ts.n0} -> {len(ts.tiles)} tiles, budget {cap}"
                  + ("  OVER" if len(ts.tiles) > cap else ""))
        return 1 if bad else 0
    if a.cmd == "preview":
        rows = load_rows()
        rom = bytearray(d)
        apply(rom, d, rows)
        Path(a.outdir).mkdir(parents=True, exist_ok=True)
        for n in sorted({r["screen"] for r in rows}):
            w, h, ro = render_screen(d, n, a.zoom)
            _, _, re_ = render_screen(bytes(rom), n, a.zoom)
            gap = bytes(3 * 4 * a.zoom)
            sweep.png(str(Path(a.outdir) / f"{label(n)}.png"), 2 * w + 4 * a.zoom, h,
                      [x + gap + y for x, y in zip(ro, re_)])
            print(Path(a.outdir) / f"{label(n)}.png")
        return 0
    if a.cmd in ("probe", "ink"):
        R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
        (to, tsz), (mo, msz) = R[(18, a.n[0])], R[(20, a.n[1])]
        ts, mp = Tileset(d[to:to + tsz]), Map(d[mo:mo + msz])
        x0, y0, w, h = (int(v) for v in a.rect.split(","))
    if a.cmd == "ink":   # bands of rows holding ink, each with its x extent: where to put the English rects
        want = {int(v) for v in a.idx.split(",")}
        hit = {}
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                e = mp.e[(y // 8) * mp.w + x // 8]
                if e & 0x3FF < len(ts.tiles) and cell_pixels(ts, e)[(y % 8) * 8 + x % 8] in want:
                    hit.setdefault(y, []).append(x)
        band = []
        for y in sorted(hit) + [None]:
            if band and (y is None or y != band[-1] + 1):
                xs = [x for b in band for x in hit[b]]
                print(f"y {band[0]}-{band[-1]} (h {len(band)})  x {min(xs)}-{max(xs)} (w {max(xs) - min(xs) + 1})")
                band = []
            if y is not None:
                band.append(y)
        return 0
    if a.cmd == "probe":
        c = Counter()
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                e = mp.e[(y // 8) * mp.w + x // 8]
                if e & 0x3FF >= len(ts.tiles):
                    continue
                c[(ts.tpal[e & 0x3FF], cell_pixels(ts, e)[(y % 8) * 8 + x % 8])] += 1
        print(f"{label(a.n)} 18@{to:X} ({len(ts.tiles)} tiles) 20@{mo:X} {mp.w}x{mp.h}")
        for (bank, v), k in c.most_common():
            col = ts.pal[(bank - min(ts.tpal)) * 16 + v] if (bank - min(ts.tpal)) * 16 + v < len(ts.pal) else 0
            print(f"bank {bank} index {v:2d}  {k:5d} px  rgb555 {col:04X}")
    elif a.cmd == "render":
        w, h, rows = render_screen(d, a.n, a.zoom, a.grid)
        sweep.png(a.out, w, h, rows)
        print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
