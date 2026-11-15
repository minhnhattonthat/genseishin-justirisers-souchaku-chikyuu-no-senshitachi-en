"""objtext.py: OBJ ('aS', group 17) sprite lettering (docs/re/graphics.md §OBJ redraw).

    python -X utf8 tools/objtext.py render N [N..] [--out DIR] [--rom ROM]   every frame of 17[N], 4x, numbered
    python -X utf8 tools/objtext.py info N                                   frames, OBJs and tile use of 17[N]

'aS' layout (sweep.as_parse): 'aS', u8 extra palettes, u8 nframes-1, u16 nobjs-1, u16 ntiles, u16 ?, palette,
nframes x (u16 count-1, u16 first_obj), nobjs x (u16 tile, u16 x | wcode<<12, u16 y | hcode<<12), then ntiles 4bpp
tiles (1D mapping; an OBJ of w x h tiles uses w*h consecutive tiles from its first).
"""
import argparse
import csv
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import res  # noqa: E402

GROUP = 17
TSV = ROOT / "gfx" / "obj.tsv"


def resource(d, n, g=GROUP):
    for gg, i, o, s in res.resources(d):
        if gg == g and i == n:
            return o, s
    raise KeyError((g, n))


class Sprite:
    """A parsed 4bpp 'aS' container; tiles as bytearrays of 32 bytes, editable and re-serialised in place."""

    def __init__(self, data):
        if data[:2] != b"aS":
            raise ValueError("not an 'aS' container")
        self.extra = data[2]
        nf = data[3] + 1
        no = struct.unpack_from("<H", data, 4)[0] + 1
        nt = struct.unpack_from("<H", data, 6)[0]
        npal = 16 * (self.extra + 1)
        self.head = bytes(data[:10])
        self.pal = list(struct.unpack_from(f"<{npal}H", data, 10))
        fo = 10 + 2 * npal
        self.frames = [struct.unpack_from("<HH", data, fo + 4 * k) for k in range(nf)]
        oo = fo + 4 * nf
        self.objs = [list(struct.unpack_from("<HHH", data, oo + 6 * k)) for k in range(no)]
        self.tstart = oo + 6 * no
        # The OBJs reach one tile past the header's count (nearly every group-17 container), and its bytes follow:
        # like the BG tilesets' extra tile, the game copies count + 1 tiles. Keep it as a normal tile.
        if len(data) >= self.tstart + 32 * (nt + 1):
            nt += 1
        self.tiles = [bytearray(data[self.tstart + 32 * k:self.tstart + 32 * k + 32]) for k in range(nt)]
        self.size = self.tstart + 32 * nt

    @staticmethod
    def obj_geom(o):
        t, xv, yv = o
        sx = lambda v: (v & 0xFFF) - 0x1000 if v & 0x800 else v & 0xFFF   # noqa: E731
        # size = 8 * (code + 1), code = bits 12-14 (0/1/3/7 = 8/16/32/64 px); t >> 12 = palette bank
        return t & 0x3FF, sx(xv), sx(yv), 8 * ((xv >> 12 & 7) + 1), 8 * ((yv >> 12 & 7) + 1)

    def frame_objs(self, f):
        c, first = self.frames[f]
        return [self.obj_geom(o) for o in self.objs[first:first + c + 1]]

    def frame_tiles(self, f):
        """-> {tile: [(screen x, screen y)]} of every 8x8 tile the frame shows."""
        out = {}
        for t, x, y, w, h in self.frame_objs(f):
            for ty in range(h // 8):
                for tx in range(w // 8):
                    out.setdefault(t + ty * (w // 8) + tx, []).append((x + 8 * tx, y + 8 * ty))
        return out

    def px(self, t, i):
        b = self.tiles[t][i // 2]
        return (b >> 4) if i & 1 else (b & 15)

    def set_px(self, t, i, v):
        b = self.tiles[t][i // 2]
        self.tiles[t][i // 2] = (b & 0x0F) | (v << 4) if i & 1 else (b & 0xF0) | v

    def bbox(self, f):
        ob = self.frame_objs(f)
        if not ob:
            return 0, 0, 0, 0
        x0, y0 = min(o[1] for o in ob), min(o[2] for o in ob)
        return x0, y0, max(o[1] + o[3] for o in ob) - x0, max(o[2] + o[4] for o in ob) - y0

    def canvas(self, f):
        """-> (x0, y0, rows of colour indices) of frame f as drawn (lower OBJ number on top; 0 = transparent)."""
        x0, y0, w, h = self.bbox(f)
        img = [[0] * w for _ in range(h)]
        for t, x, y, ow, oh in reversed(self.frame_objs(f)):
            for ty in range(oh // 8):
                for tx in range(ow // 8):
                    tt = t + ty * (ow // 8) + tx
                    if tt >= len(self.tiles):
                        continue
                    for i in range(64):
                        v = self.px(tt, i)
                        if v:
                            img[y - y0 + 8 * ty + i // 8][x - x0 + 8 * tx + i % 8] = v
        return x0, y0, img

    def rgb_canvas(self, f, bg=b"\x40\x00\x40"):
        """-> rows of RGB bytes of frame f in each OBJ's own palette bank (t >> 12)."""
        x0, y0, w, h = self.bbox(f)
        img = [bytearray(bg * w) for _ in range(h)]
        c, first = self.frames[f]
        for raw in reversed(self.objs[first:first + c + 1]):
            t, x, y, ow, oh = self.obj_geom(raw)
            bank = (raw[0] >> 12) % (len(self.pal) // 16)
            for ty in range(oh // 8):
                for tx in range(ow // 8):
                    tt = t + ty * (ow // 8) + tx
                    if tt >= len(self.tiles):
                        continue
                    for i in range(64):
                        v = self.px(tt, i)
                        if v:
                            px, py = x - x0 + 8 * tx + i % 8, y - y0 + 8 * ty + i // 8
                            img[py][3 * px:3 * px + 3] = rgb(self.pal[16 * bank + v])
        return img

    def blob(self):
        """Re-serialised container (same layout; only tiles and palette may have changed)."""
        npal = len(self.pal)
        out = bytearray(self.head) + struct.pack(f"<{npal}H", *self.pal)
        for c, first in self.frames:
            out += struct.pack("<HH", c, first)
        for o in self.objs:
            out += struct.pack("<HHH", *o)
        for t in self.tiles:
            out += t
        return bytes(out)

    def objs_unique(self):
        """-> sorted distinct (tile, w, h) blocks the OBJs use."""
        return sorted({(t, w, h) for t, x, y, w, h in (self.obj_geom(o) for o in self.objs)})


def load(d, n):
    o, s = resource(d, n)
    return Sprite(d[o:o + s]), o


# ---------------------------------------------------------------- spec rows (gfx/obj.tsv)

def load_rows(path=TSV):
    """Rows as bgtext rows plus 'target' (('obj', n, frame) or ('bg5', tileset, map)) and 'glow' (frame or None)."""
    import bgtext
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
    rows = []
    for r in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        r += [""] * (10 - len(r))
        x, y, w, h = (int(v) for v in r[2].split(","))
        if r[0].startswith("bg5:"):
            _, t, m = r[0].split(":")
            target = ("bg5", int(t), int(m))
        elif r[0].startswith("pic"):   # picG:N = 8bpp picture G[N] (5[20] title, 4[6] intro intertitle; LZ allowed)
            g, _, n = r[0][3:].partition(":")
            target = ("pic" + g, int(n), 0)
        else:
            target = ("obj", int(r[0]), int(r[1]))
        al = r[8] or "c"
        glow = int(r[4][5:]) if r[4].startswith("glow:") else None
        fnt, _, sc = (r[4] or "small").partition("*")
        rows.append({"target": target, "screen": target[1:], "rect": (x, y, w, h), "text": r[3],
                     "font": "glow" if glow is not None else fnt, "glow": glow, "scale": int(sc or 1),
                     "ink": [int(v, 16) for v in r[5].split("/")] if r[5] not in ("", "-") else [],
                     "shadow": parse_shadow(r[6]), "bg": parse_bg(r[7]),
                     "align": al[0], "grid": False, "bold": "b" in al,
                     "track": int(al[1:].replace("b", "") or 0), "note": r[9]})
    return rows


def parse_bg(s):
    """'-' keep, 'N' clear the rect to N, 'N:a,b,..' recolour only indices a, b.. to N (old glyphs off a shaded
    face, the shading kept)."""
    if s in ("", "-"):
        return None
    if s.startswith(("inpaint:", "earth:")):   # 'inpaint:LO-HI,N,..' (decimal) / 'earth:CX/CY/R:IDX' (title)
        return s
    n, _, old = s.partition(":")
    return (int(n, 16), {int(v, 16) for v in old.split(",")}) if old else int(n, 16)


def parse_shadow(s):
    """'-' none, 'N' drop shadow at +1,+1, 'oN' 1 px outline, 'oN,M,..' outline N then rings M.. (hex indices)."""
    out = {"outline": None, "drop": None, "rings": []}
    if s in ("", "-"):
        return out
    if s.startswith("o"):
        v = [int(x, 16) for x in s[1:].split(",")]
        out["outline"], out["rings"] = v[0], v[1:]
    else:
        out["drop"] = int(s, 16)
    return out


def draw_text(canvas, row, fonts):
    """bgtext.draw on an index canvas {(x, y): index}, plus 1 px rings around the outline (name plates: dark
    outline, white ring, grey ring). Rings are clipped at the rect; ink and outline must fit (bgtext.draw checks)."""
    import bgtext
    sh = row["shadow"]
    r = dict(row, shadow={"outline": sh["outline"], "drop": sh["drop"]})
    if isinstance(row["bg"], tuple):   # recolour: old glyph colours -> the face colour, then draw on top
        n, old = row["bg"]
        x0, y0, w, h = row["rect"]
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if canvas.get((x, y)) in old:
                    canvas[(x, y)] = n
        row = r = dict(r, bg=None)
    if not sh.get("rings"):
        return bgtext.draw(canvas, r, fonts, lambda v: v)
    x0, y0, w, h = row["rect"]
    mask = {}
    bgtext.draw(mask, dict(r, bg=None, ink=[1], shadow={"outline": 1, "drop": None}), fonts, lambda v: v)
    mask = set(mask)
    if row["bg"] is not None:
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                canvas[(x, y)] = row["bg"]
    for ring in sh["rings"]:
        grown = {(px + dx, py + dy) for px, py in mask for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        for q in grown - mask:
            if x0 <= q[0] < x0 + w and y0 <= q[1] < y0 + h:
                canvas[q] = ring
        mask = grown
    return bgtext.draw(canvas, dict(r, bg=None), fonts, lambda v: v)


def glow(text_img, rect, levels=(7, 6, 5)):
    """White backing for the top-menu labels (17[601] odd frames): the text frame's silhouette, filled across its
    middle rows and grown 1 px per level (core, inner ring, outer ring), as the game's own glow frames are drawn."""
    x0, y0, w, h = rect
    m = {(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w) if text_img[y][x]}
    if not m:
        return {}
    ys = [y for _, y in m]
    top, bot = min(ys), max(ys)
    core = set(m)
    for y in range(top + 2, bot - 1):
        xs = [x for x, yy in m if yy == y]
        if xs:
            core |= {(x, y) for x in range(min(xs), max(xs) + 1)}
    core |= {(x, y + dy) for x, y in core for dy in (1, 2)}
    core |= {(x + dx, y) for x, y in core for dx in (-1, 1)}
    out = {p: levels[0] for p in core}
    edge = core
    for lv in levels[1:]:
        ring = {(x + dx, y + dy) for x, y in edge for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} - set(out)
        for p in ring:
            out[p] = lv
        edge = edge | ring
    return {p: v for p, v in out.items() if x0 <= p[0] < x0 + w and y0 <= p[1] < y0 + h}


def redraw_sprite(sp, rows, fonts):
    """Apply rows (one sprite) to sp's tiles in place. Rect coordinates are relative to the frame's bounding box.
    Each rect pixel is written to every tile that shows it (top OBJ gets the value, OBJs under it 0); a tile shown
    at two places with different new pixels, or ink where no OBJ covers the frame, is an error."""
    canv = {}
    for r in rows:   # text rows first, glow rows read the redrawn text frame
        if r["glow"] is not None:
            continue
        f = r["target"][2]
        x0, y0, img = sp.canvas(f)
        c = canv.setdefault(f, {(x, y): v for y, row in enumerate(img) for x, v in enumerate(row)})
        draw_text(c, r, fonts)
        _write(sp, f, c, r["rect"], set(r["ink"]))
    for r in rows:
        if r["glow"] is None:
            continue
        f = r["target"][2]
        _, _, timg = sp.canvas(r["glow"])
        x0, y0, img = sp.canvas(f)
        rx, ry, w, h = r["rect"]
        c = {(x, y): v for y, row in enumerate(img) for x, v in enumerate(row)}
        for y in range(ry, ry + h):
            for x in range(rx, rx + w):
                c[(x, y)] = 0
        c.update(glow(timg, r["rect"]))
        _write(sp, f, c, r["rect"])
    return sp


def _write(sp, f, canvas, rect, ink=None):
    """ink: colours that must land on an OBJ (outline/ring pixels past the OBJs' cover are dropped)."""
    x0, y0, _, _ = sp.bbox(f)
    rx, ry, w, h = rect
    objs = sp.frame_objs(f)
    new = {}
    covered = set()
    for rank, (t, ox, oy, ow, oh) in enumerate(objs):   # rank 0 = drawn on top
        for ty in range(oh // 8):
            for tx in range(ow // 8):
                tt = t + ty * (ow // 8) + tx
                if tt >= len(sp.tiles):   # past the container's tiles: VRAM it does not own, never written
                    continue
                for i in range(64):
                    x, y = ox - x0 + 8 * tx + i % 8, oy - y0 + 8 * ty + i // 8
                    if not (rx <= x < rx + w and ry <= y < ry + h):
                        continue
                    v = canvas.get((x, y), 0) if (x, y) not in covered else 0
                    covered.add((x, y))
                    k = (tt, i)
                    if k in new and new[k] != v:
                        raise ValueError(f"17 frame {f}: tile {tt} is shown twice with different new pixels")
                    new[k] = v
    lost = [(x, y) for (x, y), v in canvas.items() if v and (ink is None or v in ink)
            and rx <= x < rx + w and ry <= y < ry + h and (x, y) not in covered]
    if lost:
        raise ValueError(f"17 frame {f}: ink at {sorted(lost)[:4]}.. where no OBJ covers the frame")
    for (tt, i), v in new.items():
        sp.set_px(tt, i, v)


def redraw_bg5(d, rows, fonts):
    """はい/いいえ buttons: tileset 5[t] + map 5[m] (BG). Cells in the rects are re-encoded, tiles deduplicated and
    the set padded to its original count, so both resources keep their size. -> (ts blob, map blob)."""
    import bgtext
    t, m = rows[0]["target"][1:]
    to, tsz = resource(d, t, 5)
    mo, msz = resource(d, m, 5)
    ts, mp = bgtext.Tileset(d[to:to + tsz]), bgtext.Map(d[mo:mo + msz])
    tl = [ts.pixels(i) for i in range(ts.n0)]
    if ts.extra is not None:
        tl.append([(ts.extra[i // 2] >> 4) if i & 1 else (ts.extra[i // 2] & 15) for i in range(64)])
    canvas = {}
    for k, e in enumerate(mp.e):
        cy, cx = divmod(k, mp.w)
        hf, vf = e >> 10 & 1, e >> 11 & 1
        px = tl[e & 0x3FF]
        for i in range(64):
            y, x = divmod(i, 8)
            canvas[(8 * cx + x, 8 * cy + y)] = px[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
    for r in rows:
        draw_text(canvas, r, fonts)
    touched = set()
    for r in rows:
        x0, y0, w, h = r["rect"]
        touched |= {(x // 8, y // 8) for y in range(y0, y0 + h) for x in range(x0, x0 + w)}
    keep = {mp.e[cy * mp.w + cx] & 0x3FF for cy in range(mp.h) for cx in range(mp.w) if (cx, cy) not in touched}
    tiles = list(ts.tiles)
    # Only the old tiles of the touched cells may be recycled: other layers draw with this tileset too (recycling
    # tiles 5[3] never uses, tile 0 among them, turned the save screen behind the prompt into a tile pattern).
    old = {mp.e[cy * mp.w + cx] & 0x3FF for cx, cy in touched}
    free = sorted(i for i in old if i not in keep and 0 < i < ts.n0)
    index = {(tiles[i], ts.tpal[i]): i for i in keep if i < ts.n0}
    bank = ts.tpal[0]
    for cx, cy in sorted(touched, key=lambda c: (c[1], c[0])):
        px = [canvas[(8 * cx + i % 8, 8 * cy + i // 8)] for i in range(64)]
        enc = bgtext.Tileset.encode(px)
        if (enc, bank) not in index:
            if not free:
                raise ValueError(f"bg5 {t}:{m}: out of tiles ({ts.n0})")
            j = free.pop(0)
            tiles[j] = enc
            ts.tpal[j] = bank
            index[(enc, bank)] = j
        k = cy * mp.w + cx
        mp.e[k] = (mp.e[k] & 0xF000) | index[(enc, bank)]
    ts.tiles = tiles   # leftover old glyph tiles stay as they were (count and size unchanged)
    tb, mb = ts.blob(), mp.blob()
    if len(tb) > tsz or len(mb) != msz:
        raise ValueError(f"bg5 {t}:{m}: sizes changed")
    return (to, tb), (mo, mb)


class Pic:
    """Group-5 8bpp picture (5[20] = the title screen): u8 1 (8bpp), u8 w, u8 h, u8 0, u16 colours (256), u16 ntiles,
    u16 palette offset (0x4BC), u16 tiles offset (0x6BC); the w x h map (u16 entries, no flips seen) at +0xC."""

    def __init__(self, data):
        if data[0] != 1:
            raise ValueError("not an 8bpp group-5 picture")
        self.w, self.h = data[1], data[2]
        self.nt, self.po, self.to = struct.unpack_from("<HHH", data, 6)
        self.head = bytes(data[:0xC])
        self.e = list(struct.unpack_from(f"<{self.w * self.h}H", data, 0xC))
        self.mid = bytes(data[0xC + 2 * self.w * self.h:self.to])   # palette
        self.tiles = [bytes(data[self.to + 64 * i:self.to + 64 * i + 64]) for i in range(self.nt)]
        self.size = self.to + 64 * self.nt

    def blob(self):
        return (self.head + struct.pack(f"<{len(self.e)}H", *self.e) + self.mid + b"".join(self.tiles))

    def canvas(self):
        c = {}
        for k, e in enumerate(self.e):
            cy, cx = divmod(k, self.w)
            t = self.tiles[e & 0x3FF]
            for i in range(64):
                c[(8 * cx + i % 8, 8 * cy + i // 8)] = t[i]
        return c


def inpaint(canvas, rect, idx):
    """Pixels of the rect with an index in idx (the old lettering) take the colour of the nearest pixel outside
    that set (breadth-first from the background around them)."""
    x0, y0, w, h = rect
    hole = {(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w) if canvas[(x, y)] in idx}
    front = [p for p in hole if any((p[0] + dx, p[1] + dy) in canvas and (p[0] + dx, p[1] + dy) not in hole
                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    seen = set()
    while front:
        nxt = []
        for x, y in front:
            if (x, y) in seen:
                continue
            nb = [canvas[q] for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                  if q in canvas and (q not in hole or q in seen)]
            if not nb:
                continue
            canvas[(x, y)] = max(set(nb), key=nb.count)
            seen.add((x, y))
            nxt += [q for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)) if q in hole and q not in seen]
        front = nxt


def parse_idx(s):
    """'63-124,10,14' (decimal) -> set of indices."""
    out = set()
    for part in s.split(","):
        lo, _, hi = part.partition("-")
        out |= set(range(int(lo), int(hi or lo) + 1))
    return out


def earth_backdrop(canvas, rect, circle, emblem):
    """Rebuild the title's starfield + Earth limb behind the old subtitle (bg 'earth:CX/CY/R:IDX'): the horizon is
    the circle (fitted to the limb in the columns left and right of the emblem); above it each row takes its sky
    colour from those side columns, below it the Earth takes limb texture from the side columns at the same depth,
    or (deeper than 10 px) the texture mirrored from just below the rect. Inside the rect every pixel is rebuilt;
    outside it only pixels in the emblem's colours (its spikes reach past the rect)."""
    import math
    from collections import Counter
    cx, cy, r = circle
    x0, y0, w, h = rect
    W = max(x for x, _ in canvas) + 1
    orig = dict(canvas)
    hz = lambda x: cy - math.sqrt(r * r - (x - cx) ** 2)   # noqa: E731
    side = [x for x in range(W) if x < x0 or x >= x0 + w]
    ok = lambda q: q in orig and orig[q] not in emblem and q[1] < y0 + h + 14   # noqa: E731
    sky, last = {}, None
    for y in range(y0, y0 + h):
        cand = [orig[(x, y)] for x in side if y < hz(x) - 1 and orig[(x, y)] not in emblem]
        if cand:
            last = Counter(cand).most_common(1)[0][0]
        sky[y] = last
    for y in range(y0 + h - 1, y0 - 1, -1):   # rows with no sky at the sides take the nearest row above's
        if sky[y] is None:
            sky[y] = next((sky[k] for k in range(y - 1, y0 - 1, -1) if sky[k] is not None), 0)
    bottom = y0 + h
    left, right = [x for x in side if x < x0][2:], [x for x in side if x >= x0 + w][2:-2]

    def earth(x, y):
        dd = y - hz(x)
        mirror = (x, 2 * bottom - 1 - y)
        if dd > 10 and ok(mirror):
            return orig[mirror]
        src = left if x < cx else right
        xs = src[x % len(src)]
        ys = int(round(hz(xs) + dd))
        for k in range(12):   # the side column at the same depth, else the nearest usable depth
            for q in ((xs, ys - k), (xs, ys + k), (mirror[0], mirror[1] + k)):
                if ok(q) and q[1] >= hz(q[0]):
                    return orig[q]
        return sky[y]

    for y in range(y0, y0 + h):
        for x in range(W):
            if not (x0 <= x < x0 + w) and orig[(x, y)] not in emblem:
                continue
            canvas[(x, y)] = sky[y] if y < hz(x) else earth(x, y)


def scaled_text(canvas, row, fonts, scale):
    """Text at an integer scale (title lettering): the line's 1x ink (bold/tracking as in bgtext) scaled up, centred
    in the rect, ink bands over its scaled ink rows, then the outline and rings 1 px each."""
    x0, y0, w, h = row["rect"]
    g = fonts[row["font"]]
    nrows = 16 if row["font"] == "normal" else 8
    ink, x = set(), 0
    for c in row["text"]:
        gl = g[c]
        for gy in range(nrows if gl["rows"] else 0):
            for gx in range(16):
                if gl["rows"][gy] >> (15 - gx) & 1:
                    ink.add((x + gx, gy))
                    if row["bold"]:
                        ink.add((x + gx + 1, gy))
        x += gl["width"] + row["track"] + (1 if row["bold"] else 0)
    mx0, mx1 = min(p[0] for p in ink), max(p[0] for p in ink)
    my0, my1 = min(p[1] for p in ink), max(p[1] for p in ink)
    tw, th = (mx1 - mx0 + 1) * scale, (my1 - my0 + 1) * scale
    pad = 1 + len(row["shadow"]["rings"]) if row["shadow"]["outline"] is not None else 0
    if tw + 2 * pad > w or th + 2 * pad > h:
        raise ValueError(f"{row['text']!r}: {tw}x{th} px (+{pad} outline) > rect {w}x{h}")
    ox = x0 + {"l": pad, "c": (w - tw) // 2, "r": w - tw - pad}[row["align"]]
    oy = y0 + (h - th) // 2
    big = {(ox + (px - mx0) * scale + i, oy + (py - my0) * scale + j)
           for px, py in ink for i in range(scale) for j in range(scale)}
    sh = row["shadow"]
    if sh["outline"] is not None:   # paint rings outermost first
        layers, m = [], set(big)
        for ring in [sh["outline"]] + sh["rings"]:
            g2 = {(px + dx, py + dy) for px, py in m for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            layers.append((ring, g2))
            m = g2
        for ring, area in reversed(layers):
            for p in area:
                if x0 <= p[0] < x0 + w and y0 <= p[1] < y0 + h:
                    canvas[p] = ring
    bands = row["ink"]
    for px, py in big:
        b = min(len(bands) - 1, (py - oy) * len(bands) // th)
        canvas[(px, py)] = bands[b]


def load_pic(d, g, n):
    """-> (Pic, offset, size, lz) of picture G[n]; an LZ resource (intro stills, group 4) is decompressed."""
    import klz
    o, s = resource(d, n, g)
    lz = d[o] == 0xFF
    return Pic(klz.decompress(d[o:o + s])[0] if lz else d[o:o + s]), o, s, lz


def redraw_pic(d, rows, fonts):
    """Picture G[n] (title 5[20], intro stills 4[n]): rows drawn on its 8bpp canvas, touched cells re-encoded; new
    tiles may only take the old tiles of the touched cells (the count and size stay). An LZ picture is compressed
    again and must fit its old resource. -> (offset, blob)."""
    import klz
    g, n = int(rows[0]["target"][0][3:]), rows[0]["target"][1]
    pic, o, s, lz = load_pic(d, g, n)
    canvas = pic.canvas()
    before = dict(canvas)
    for r in rows:
        if isinstance(r["bg"], str) and r["bg"].startswith("inpaint:"):
            inpaint(canvas, r["rect"], parse_idx(r["bg"][8:]))
            r = dict(r, bg=None)
        elif isinstance(r["bg"], str) and r["bg"].startswith("earth:"):
            _, circ, idx = r["bg"].split(":")
            earth_backdrop(canvas, r["rect"], tuple(float(v) for v in circ.split("/")), parse_idx(idx))
            r = dict(r, bg=None)
        if r["text"]:
            sc = r.get("scale", 1)
            if sc > 1 or r["shadow"]["rings"]:
                scaled_text(canvas, r, fonts, sc)
            else:
                draw_text(canvas, r, fonts)
    touched = {(x // 8, y // 8) for (x, y), v in canvas.items() if before[(x, y)] != v}
    keep = {pic.e[cy * pic.w + cx] & 0x3FF for cy in range(pic.h) for cx in range(pic.w) if (cx, cy) not in touched}
    old = {pic.e[cy * pic.w + cx] & 0x3FF for cx, cy in touched}
    free = sorted(t for t in old if t not in keep and t > 0)
    index = {pic.tiles[t]: t for t in keep}
    for cx, cy in sorted(touched, key=lambda c: (c[1], c[0])):
        enc = bytes(canvas[(8 * cx + i % 8, 8 * cy + i // 8)] for i in range(64))
        if enc not in index:
            if not free:
                raise ValueError(f"{g}[{n}]: out of tiles (the redraw needs more unique tiles than it frees)")
            t = free.pop(0)
            pic.tiles[t] = enc
            index[enc] = t
        k = cy * pic.w + cx
        pic.e[k] = (pic.e[k] & 0xFC00) | index[enc]
    b = pic.blob()
    if len(b) != pic.size:
        raise ValueError(f"{g}[{n}]: size changed")
    if lz:
        b = klz.compress(b)
        if len(b) > s:
            raise ValueError(f"{g}[{n}]: {len(b)} bytes compressed > {s} (the resource's room)")
    return o, b


def apply(rom, orig, rows=None):
    """Redraw every sprite / bg5 screen with rows, written in place. -> written ranges."""
    import font
    rows = load_rows() if rows is None else rows
    if not rows:
        return []
    fonts = font.load_all()
    d = bytes(orig)
    out = []
    for n in sorted({r["target"][1] for r in rows if r["target"][0] == "obj"}):
        sp, o = load(d, n)
        redraw_sprite(sp, [r for r in rows if r["target"][:2] == ("obj", n)], fonts)
        b = sp.blob()
        if len(b) != sp.size:
            raise ValueError(f"17[{n}]: size changed")
        rom[o:o + len(b)] = b
        out.append((o, o + len(b)))
    bg = [r for r in rows if r["target"][0] == "bg5"]
    for key in sorted({r["target"] for r in bg}):
        for o, b in redraw_bg5(d, [r for r in bg if r["target"] == key], fonts):
            rom[o:o + len(b)] = b
            out.append((o, o + len(b)))
    pics = [r for r in rows if r["target"][0].startswith("pic")]
    for key in sorted({r["target"] for r in pics}):
        o, b = redraw_pic(d, [r for r in pics if r["target"] == key], fonts)
        rom[o:o + len(b)] = b
        out.append((o, o + len(b)))
    return out


def rgb(c):
    return bytes(((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31))


def render(sp, zoom=4, bank=0, frames=None):
    """-> (w, h, rows) of every frame (or the listed ones) side by side with a gap, transparent = dark magenta."""
    pal = [rgb(c) for c in sp.pal[16 * bank:16 * bank + 16]]
    pal[0] = b"\x40\x00\x40"
    imgs = [sp.canvas(f)[2] for f in (frames if frames is not None else range(len(sp.frames)))]
    W = sum(len(i[0]) if i else 0 for i in imgs) + 4 * len(imgs)
    H = max((len(i) for i in imgs), default=0)
    rows = [bytearray(b"\x20\x20\x20" * W) for _ in range(H)]
    x = 0
    for img in imgs:
        for y, r in enumerate(img):
            rows[y][3 * x:3 * (x + len(r))] = b"".join(pal[v] for v in r)
        x += (len(img[0]) if img else 0) + 4
    out = []
    for r in rows:
        zr = b"".join(r[3 * i:3 * i + 3] * zoom for i in range(W))
        out += [zr] * zoom
    return W * zoom, H * zoom, out


def render_blocks(sp, zoom=3, bank=0, width=480):
    """-> (w, h, rows): every distinct OBJ tile block (tile, w, h) shelf-packed, so each label reads on its own."""
    pal = [rgb(c) for c in sp.pal[16 * bank:16 * bank + 16]]
    pal[0] = b"\x40\x00\x40"
    blocks = sp.objs_unique()
    place, cx, cy, sh = [], 0, 0, 0
    for t, w, h in blocks:
        if cx + w > width:
            cx, cy, sh = 0, cy + sh + 4, 0
        place.append((t, w, h, cx, cy))
        cx, sh = cx + w + 4, max(sh, h)
    H = cy + sh
    rows = [bytearray(b"\x20\x20\x20" * width) for _ in range(H)]
    for t, w, h, bx, by in place:
        for ty in range(h // 8):
            for tx in range(w // 8):
                tt = t + ty * (w // 8) + tx
                if tt >= len(sp.tiles):
                    continue
                for i in range(64):
                    x, y = bx + 8 * tx + i % 8, by + 8 * ty + i // 8
                    rows[y][3 * x:3 * x + 3] = pal[sp.px(tt, i)]
    out = []
    for r in rows:
        zr = b"".join(r[3 * i:3 * i + 3] * zoom for i in range(width))
        out += [zr] * zoom
    return width * zoom, H * zoom, out, place


def preview(d, outdir, zoom):
    """original | English of every frame / bg5 screen in gfx/obj.tsv -> OUTDIR/obj_preview.png (one row each)."""
    import bgscreens
    import bgtext
    import sweep
    rows = load_rows()
    rom = bytearray(d)
    apply(rom, d, rows)
    strips = []
    for key in sorted({r["target"] for r in rows}, key=str):
        pair = []
        for src in (d, bytes(rom)):
            if key[0] == "obj":
                sp, _ = load(src, key[1])
                pair.append(sp.rgb_canvas(key[2]))
            elif key[0].startswith("pic"):
                pic = load_pic(src, int(key[0][3:]), key[1])[0]
                pal = struct.unpack_from("<256H", pic.mid)
                c = pic.canvas()
                pair.append([bytearray(b"".join(rgb(pal[c[(x, y)]]) for x in range(8 * pic.w)))
                             for y in range(8 * pic.h)])
            else:
                to, tsz = resource(src, key[1], 5)
                mo, msz = resource(src, key[2], 5)
                ts, mp = bgtext.Tileset(src[to:to + tsz]), bgtext.Map(src[mo:mo + msz])
                img = [bytearray(3 * 8 * mp.w) for _ in range(8 * mp.h)]
                for k, e in enumerate(mp.e):
                    cy, cx = divmod(k, mp.w)
                    if (e & 0x3FF) >= ts.n0:
                        continue
                    for i, v in enumerate(bgtext.cell_pixels(ts, e)):
                        y, x = 8 * cy + i // 8, 8 * cx + i % 8
                        img[y][3 * x:3 * x + 3] = bgscreens.rgb(ts.pal[v])
                pair.append(img)
        strips.append(pair)
    W = max(2 * len(p[0][0]) // 3 + 8 for p in strips)
    out = []
    for a_img, b_img in strips:
        h = len(a_img)
        for y in range(h):
            line = bytes(a_img[y]) + b"\x20\x20\x20" * 8 + bytes(b_img[y])
            line += b"\x20\x20\x20" * (W - len(line) // 3)
            z = b"".join(line[3 * i:3 * i + 3] * zoom for i in range(W))
            out += [z] * zoom
        out += [b"\x10\x10\x10" * W * zoom] * (4 * zoom)
    Path(outdir).mkdir(parents=True, exist_ok=True)
    p = Path(outdir) / "obj_preview.png"
    sweep.png(str(p), W * zoom, len(out), out)
    print(p)
    return 0


def main():
    import check_rom
    import sweep
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "info", "preview"))
    ap.add_argument("n", nargs="*", type=int)
    ap.add_argument("--out", default="work/qa/gfx/obj")
    ap.add_argument("--rom")
    ap.add_argument("--bank", type=int, default=0)
    ap.add_argument("--frames", help="comma list of frames to render (default: all)")
    ap.add_argument("--zoom", type=int, default=4)
    a = ap.parse_args()
    d = Path(a.rom).read_bytes() if a.rom else check_rom.original()
    if a.cmd == "preview":
        return preview(d, a.out, a.zoom)
    for n in a.n:
        sp, off = load(d, n)
        if a.cmd == "info":
            print(f"17[{n}] at 0x{off:X}: {len(sp.frames)} frames, {len(sp.objs)} objs, {len(sp.tiles)} tiles, "
                  f"{len(sp.pal) // 16} palettes")
            for f in range(len(sp.frames)):
                ft = sorted(sp.frame_tiles(f))
                print(f"  frame {f}: bbox {sp.bbox(f)} objs {sp.frame_objs(f)} tiles {ft[:1]}..{ft[-1:]} ({len(ft)})")
            continue
        Path(a.out).mkdir(parents=True, exist_ok=True)
        fr = [int(v) for v in a.frames.split(",")] if a.frames else None
        w, h, rows = render(sp, zoom=a.zoom, bank=a.bank, frames=fr)
        p = Path(a.out) / (f"obj{n}_f{a.frames.replace(',', '_')}.png" if fr else f"obj{n}.png")
        sweep.png(str(p), w, h, rows)
        w, h, rows, place = render_blocks(sp, bank=a.bank)
        q = Path(a.out) / f"obj{n}_blocks.png"
        sweep.png(str(q), w, h, rows)
        print(p, q)
        print("  blocks (tile w h @x,y):", " ".join(f"{t}:{bw}x{bh}@{x},{y}" for t, bw, bh, x, y in place))
    return 0


if __name__ == "__main__":
    sys.exit(main())
