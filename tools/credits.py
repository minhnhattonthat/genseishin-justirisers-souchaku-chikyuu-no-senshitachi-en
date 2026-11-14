"""credits.py: the staff roll (scene 11) in English (docs/re/graphics.md §Credits).

    python -X utf8 tools/credits.py preview [OUTDIR]     original | English per roll -> OUTDIR/roll<n>.png
    python -X utf8 tools/credits.py count                tiles per roll against the original count

Scene 11 rolls five pages 700..704, then shows おわり (705). Each is tileset 18[n] + roll 19[n]; 20[n] is only a
linear map of screen slots. 19[n]: b'a2', u16 (slots - 1), then metatiles 15 per row, each 4 u16 tile numbers
(top-left, top-right, bottom-left, bottom-right): 15 x 45 = a 30 x 90 tile roll read top to bottom (705: 170
metatiles). Tile numbers index 18[n] (rolls: 0 = transparent, 1 = blank; 705 the other way round);
slot n0 (one past the count) is the resource's extra tile, which the game loads too (Tileset.extra).

gfx/credits.tsv rows (tab-separated, '#' comments):
    roll  y    x    align  font    text            note
    700   127  24   l      normal  Original Work   原作
  y      centre of the line's ink band in roll pixels (0..719; the font's full ink height, so lines share rows)
  x      left edge (l), centre (c) or right edge (r); a trailing g (lg, cg) = grid lettering: one glyph per 8 px
         cell, the line snapped to tile rows and columns, so letters repeat as whole tiles (tight tile counts)
  font   normal / small (the game's English fonts, tools/font.py), or keep: text = x,y,w,h, a rect whose original
         pixels stay (the second copyright line is English already)
Roll 700 (the first page) with text on rows 12-13 showed stale tiles of that text in screen columns 0-1 at the top
of the screen (work/qa/credits_en, f1050-1200); starting at row 16, like the Japanese (row 15), it is clean. Keep
roll 700's first line at y >= 137 (rows 16+).
Every roll with a row is redrawn from blank: ink index 1 (white) on the roll's own background (tile 1's colour).
The new tileset keeps the original tile count (padded with blanks) and size, so both are written in place and the
VRAM layout (the three sets back to back) is unchanged.
"""
import csv
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import res  # noqa: E402

ROLLS = (700, 701, 702, 703, 704, 705)   # 705 = the closing おわり ("The End") page, same format
W = 30                 # roll width in tiles (15 metatiles); rolls are 90 tiles tall, page 705 22
MW = W // 2
SPEC = ROOT / "gfx" / "credits.tsv"
INK = 1


def resource(d, g, n):
    for gg, i, o, s in res.resources(d):
        if gg == g and i == n:
            return o, s
    raise KeyError((g, n))


def decode(blob):
    """19[n] blob -> (header bytes, cells: W-wide rows of tile numbers, row-major, metatile count). The rolls hold
    675 metatiles (45 rows); the 'The End' page 705 holds 170 (11 rows + 5): the last row is padded with 0."""
    if blob[:2] != b"a2":
        raise ValueError("not an a2 roll")
    nm = (len(blob) - 4) // 8
    words = struct.unpack_from(f"<{4 * nm}H", blob, 4)
    cells = [0] * (W * 2 * -(-nm // MW))
    for m in range(nm):
        my, mx = divmod(m, MW)
        for k in range(4):
            cells[(2 * my + k // 2) * W + 2 * mx + k % 2] = words[4 * m + k]
    return bytes(blob[:4]), cells, nm


def encode(head, cells, nm):
    words = []
    for m in range(nm):
        my, mx = divmod(m, MW)
        words += [cells[(2 * my + k // 2) * W + 2 * mx + k % 2] for k in range(4)]
    return head + struct.pack(f"<{len(words)}H", *words)


def load(d, n):
    """-> (18[n] tileset bytes, cells)."""
    to, ts = resource(d, 18, n)
    mo, ms = resource(d, 19, n)
    return bytes(d[to:to + ts]), decode(d[mo:mo + ms])[1]


def load_spec(path=SPEC):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
    out = []
    for r in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        r += [""] * (7 - len(r))
        out.append({"roll": int(r[0]), "y": int(r[1] or 0), "x": int(r[2] or 0), "align": r[3] or "l",
                    "font": r[4] or "normal", "text": r[5], "note": r[6]})
    return out


def _tiles(ts):
    """Original tiles as pixel lists, slot n0 = the extra tile."""
    t = [ts.pixels(i) for i in range(len(ts.tiles))]
    if ts.extra is not None:
        t.append([(ts.extra[i // 2] >> 4) if i & 1 else (ts.extra[i // 2] & 15) for i in range(64)])
    return t


def pixels(ts, cells):
    """-> 8 * rows lines of 240 colour indices as the roll is drawn (cells past the tileset: index 0)."""
    tl = _tiles(ts)
    rows = [[0] * (8 * W) for _ in range(8 * (len(cells) // W))]
    for k, e in enumerate(cells):
        cy, cx = divmod(k, W)
        px = tl[e] if e < len(tl) else [0] * 64
        for i in range(64):
            rows[cy * 8 + i // 8][cx * 8 + i % 8] = px[i]
    return rows


def ink_band(glyphs):
    rows = [r for c, g in glyphs.items() if c.isascii() and c.isalnum() and g["rows"]
            for r in range(16) if g["rows"][r]]
    return min(rows), max(rows)


def line_width(text, glyphs):
    return sum(glyphs[c]["width"] for c in text) - 2


def draw_line(canvas, row, fonts):
    glyphs = fonts[row["font"]]
    bad = [c for c in row["text"] if c not in glyphs]
    if bad:
        raise ValueError(f"credits {row['roll']} {row['text']!r}: no glyph for {bad}")
    lo, hi = ink_band(glyphs)
    top = row["y"] - (lo + hi + 1) // 2
    grid = "g" in row["align"]
    tw = 8 * len(row["text"]) if grid else line_width(row["text"], glyphs)
    x = {"l": row["x"], "c": row["x"] - tw // 2, "r": row["x"] - tw}[row["align"][0]]
    if grid:   # one glyph per 8 px cell on tile rows: letters repeat as whole tiles (tight tile budgets)
        top, x = (top + 4) // 8 * 8, (x + 4) // 8 * 8
    if x < 0 or x + tw > 8 * W:
        raise ValueError(f"credits {row['roll']} {row['text']!r}: x {x}..{x + tw} outside the 240 px roll")
    for c in row["text"]:
        g = glyphs[c]
        gx0 = 0
        if grid and g["rows"]:
            cols = [gx for gx in range(16) if any(r >> (15 - gx) & 1 for r in g["rows"])]
            gx0 = (8 - (cols[-1] - cols[0] + 1)) // 2 - cols[0] if cols else 0
        for gy in range(16 if g["rows"] else 0):
            for gx in range(16):
                if g["rows"][gy] >> (15 - gx) & 1:
                    p = canvas[top + gy]
                    if p[x + gx0 + gx] == INK:
                        raise ValueError(f"credits {row['roll']} {row['text']!r}: ink overlaps another line")
                    p[x + gx0 + gx] = INK
        x += 8 if grid else g["width"]


def redraw(d, n, rows, fonts=None):
    """-> (tileset blob, roll blob, used tile count) for roll n with spec rows applied."""
    import bgtext
    import font
    fonts = fonts or font.load_all()
    to, tsz = resource(d, 18, n)
    mo, msz = resource(d, 19, n)
    ts = bgtext.Tileset(d[to:to + tsz])
    head, cells, nm = decode(d[mo:mo + msz])
    orig = pixels(ts, cells)
    # Tiles 0 and 1: one is all transparent, the other the plain background (rolls: 0 / 1, page 705: 1 / 0).
    clear = 0 if not any(ts.pixels(0)) else 1
    bg = ts.pixels(1 - clear)[0]
    canvas = [[bg] * (8 * W) for _ in range(len(orig))]
    for r in rows:
        if r["font"] == "keep":
            x0, y0, w, h = (int(v) for v in r["text"].split(","))
            for y in range(y0, y0 + h):
                canvas[y][x0:x0 + w] = orig[y][x0:x0 + w]
    for r in rows:
        if r["font"] != "keep":
            if n == ROLLS[0] and r["y"] < 137:
                raise ValueError(f"credits {n} {r['text']!r}: y {r['y']} < 137 (stale tiles at the screen's left edge)")
            draw_line(canvas, r, fonts)
    tiles = [ts.tiles[0], ts.tiles[1]]
    index = {t: i for i, t in enumerate(tiles)}
    new = []
    for k, e in enumerate(cells):
        cy, cx = divmod(k, W)
        px = [canvas[cy * 8 + i // 8][cx * 8 + i % 8] for i in range(64)]
        if e == clear:   # transparent cells (the roll's lead-in) stay transparent
            if any(p not in (0, bg) for p in px):
                raise ValueError(f"credits {n}: ink in transparent cell {cx},{cy}")
            new.append(clear)
            continue
        t = bgtext.Tileset.encode(px)
        if t not in index:
            index[t] = len(tiles)
            tiles.append(t)
        new.append(index[t])
    used = len(tiles)
    if used > ts.n0:
        raise ValueError(f"credits {n}: {used} tiles > the original {ts.n0}: shorter lines or small font")
    ts.tiles = tiles + [ts.tiles[1 - clear]] * (ts.n0 - used)
    blob = ts.blob()
    roll = encode(head, new, nm)
    if len(blob) > tsz or len(roll) != msz:
        raise ValueError(f"credits {n}: blob sizes changed ({len(blob)}/{tsz}, {len(roll)}/{msz})")
    return blob, roll, used


def apply(rom, orig, rows=None):
    """Redraw every roll with spec rows, in place. -> written ranges."""
    rows = load_spec() if rows is None else rows
    out = []
    for n in sorted({r["roll"] for r in rows}):
        blob, roll, _ = redraw(bytes(orig), n, [r for r in rows if r["roll"] == n])
        for g, b in ((18, blob), (19, roll)):
            o, _ = resource(orig, g, n)
            rom[o:o + len(b)] = b
            out.append((o, o + len(b)))
    return out


def main():
    import argparse
    import bgscreens
    import check_rom
    import sweep
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("preview", "count"))
    ap.add_argument("outdir", nargs="?", default="work/qa/gfx/credits")
    a = ap.parse_args()
    d = check_rom.original()
    rows = load_spec()
    if a.cmd == "count":
        for n in sorted({r["roll"] for r in rows}):
            _, _, used = redraw(d, n, [r for r in rows if r["roll"] == n])
            print(f"roll {n}: {used} tiles, original {load_count(d, n)}")
        return 0
    rom = bytearray(d)
    apply(rom, d, rows)
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    import bgtext
    for n in ROLLS:
        out = []
        for src in (d, bytes(rom)):
            tsb, cells = load(src, n)
            ts = bgtext.Tileset(tsb)
            pal = [bgscreens.rgb(c) for c in ts.pal[:16]]
            pal[0] = b"\x40\x00\x40"   # transparent: dark magenta
            out.append([b"".join(pal[v] for v in row) for row in pixels(ts, cells)])
        p = Path(a.outdir) / f"roll{n}.png"
        sweep.png(str(p), 2 * 8 * W + 8, len(out[0]), [x + bytes(24) + y for x, y in zip(*out)])
        print(p)
    return 0


def load_count(d, n):
    import bgtext
    o, s = resource(d, 18, n)
    return bgtext.Tileset(d[o:o + s]).n0


if __name__ == "__main__":
    sys.exit(main())
