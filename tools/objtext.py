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
        else:
            target = ("obj", int(r[0]), int(r[1]))
        al = r[8] or "c"
        glow = int(r[4][5:]) if r[4].startswith("glow:") else None
        rows.append({"target": target, "screen": target[1:], "rect": (x, y, w, h), "text": r[3],
                     "font": "glow" if glow is not None else r[4] or "small", "glow": glow,
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
