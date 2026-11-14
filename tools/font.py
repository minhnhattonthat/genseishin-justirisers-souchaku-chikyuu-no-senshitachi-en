"""font.py: the English fonts: glyph art in font/en.txt (normal) and font/en_small.txt (small), written into the
game's font cells and width tables.

    python -X utf8 tools/font.py extract ROM OUT.txt [--small]   bootstrap: the ROM's own Latin/digit glyphs as
                                                                 art, ink moved to column 0, advance = ink + 1
    python -X utf8 tools/font.py check                           parse both fonts, report problems
    python -X utf8 tools/font.py width TEXT [--small]            pixel width of a plain English string

Font format (docs/re/text.md): ROM 0x2CBC34, 32 bytes per cell, 16 rows of one big-endian u16; MSB-first, but
**each pair of adjacent pixels is swapped** (stored bit 15 = pixel 1, bit 14 = pixel 0, ...).
- normal font: cell = code, advance widths one byte per code 0x000-0x1FF at ROM 0x8C00FA (higher codes 12 px).
- small font (window attr bit 7, `{style:..80}`; name tags): cell = 0xC00 + (code & 0x1FF), 8-row glyphs,
  widths one byte per code at ROM 0x8C02FB.
Both use the same codes, so one encoding (tools/insert.py en_table) serves both; every character of the normal
font must exist in the small one.

Widths are rounded up to even: the rasterizer (0x08007B40) mis-draws glyphs that start at an odd x, and the
game's own widths are all even.

font/en*.txt: blocks of
    = A 21          character, then the code (hex); `= space 20 w4` for the space (width only, cell untouched)
    #......         up to 16 rows of art ('#' ink, '.' blank), top row first
The advance width is the length of the art rows (all rows the same length, spacing column included).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x2CBC34
FONTS = {   # name: (source, first cell, width table)
    "normal": (ROOT / "font" / "en.txt", 0x000, 0x8C00FA),
    "small": (ROOT / "font" / "en_small.txt", 0xC00, 0x8C02FB),
}
WIDTHS = FONTS["normal"][2]


def _swap(v):
    return ((v & 0xAAAA) >> 1) | ((v & 0x5555) << 1)


def cell_rows(rom, cell):
    """-> 16 ints, bit 15 = leftmost pixel (pair swap undone)."""
    o = BASE + cell * 32
    return [_swap(rom[o + 2 * r] << 8 | rom[o + 2 * r + 1]) for r in range(16)]


def cell_bytes(rows):
    out = bytearray()
    for v in rows:
        v = _swap(v)
        out += bytes([v >> 8, v & 0xFF])
    return bytes(out)


def load(name="normal"):
    """-> {char: {"code": int, "width": int, "rows": [16 ints] or None}}"""
    path = FONTS[name][0]
    glyphs, cur = {}, None
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("//"):
            continue
        if line.startswith("= "):
            parts = line[2:].split()
            ch = " " if parts[0] == "space" else parts[0]
            if len(ch) != 1:
                raise ValueError(f"{path}:{n}: one character per glyph, got {ch!r}")
            if ch in glyphs:
                raise ValueError(f"{path}:{n}: {ch!r} defined twice")
            w = next((int(p[1:]) for p in parts[2:] if p.startswith("w")), None)
            cur = glyphs[ch] = {"code": int(parts[1], 16), "width": w, "art": []}
            continue
        if cur is None or set(line) - set("#."):
            raise ValueError(f"{path}:{n}: art row outside a glyph or with characters other than # and .")
        cur["art"].append(line)
    codes = {}
    for ch, g in glyphs.items():
        art = g.pop("art")
        if art:
            if len(art) > 16 or len({len(r) for r in art}) != 1 or len(art[0]) > 16:
                raise ValueError(f"{path}: glyph {ch!r}: up to 16 rows of one length (<= 16)")
            g["width"] = g["width"] or len(art[0])
            g["rows"] = [sum(1 << (15 - x) for x, c in enumerate(r) if c == "#") for r in art]
            g["rows"] += [0] * (16 - len(g["rows"]))
        else:
            g["rows"] = None
            if g["width"] is None:
                raise ValueError(f"{path}: glyph {ch!r} has neither art nor a width")
        g["width"] += g["width"] & 1
        if not 0x20 <= g["code"] < 0x200:
            raise ValueError(f"{path}: glyph {ch!r}: code {g['code']:X} has no width-table entry or is a control")
        if g["code"] in codes:
            raise ValueError(f"{path}: code {g['code']:X} used by {codes[g['code']]!r} and {ch!r}")
        codes[g["code"]] = ch
    return glyphs


def load_all():
    """-> {"normal": glyphs, "small": glyphs}, checked to agree on codes."""
    out = {name: load(name) for name in FONTS}
    for ch, g in out["normal"].items():
        s = out["small"].get(ch)
        if s is None or s["code"] != g["code"]:
            raise ValueError(f"small font: {ch!r} missing or under another code than {g['code']:X}")
    return out


def apply(rom, fonts=None):
    """Write every glyph's cell and width into rom (bytearray). -> list of (start, end) ranges written."""
    fonts = fonts or load_all()
    ranges = []
    for name, glyphs in fonts.items():
        _, first, wtab = FONTS[name]
        for g in glyphs.values():
            c = g["code"]
            if g["rows"] is not None:
                o = BASE + 32 * (first + c)
                rom[o:o + 32] = cell_bytes(g["rows"])
                ranges.append((o, o + 32))
            rom[wtab + c] = g["width"]
            ranges.append((wtab + c, wtab + c + 1))
    return ranges


def widths(name="normal", glyphs=None):
    """-> {char: advance px}"""
    return {ch: g["width"] for ch, g in (glyphs or load(name)).items()}


def text_width(text, w=None):
    """Advance width of plain English text (no control codes); unknown characters count 12 px."""
    w = w or widths()
    return sum(w.get(ch, 12) for ch in text)


def art(rows, width):
    return ["".join("#" if v >> (15 - x) & 1 else "." for x in range(width)) for v in rows]


def extract(rom, out, small=False):
    first, height = (0xC00, 8) if small else (0, 16)
    chars = [(chr(ord("A") + i), 0x21 + i) for i in range(26)] + [(chr(ord("0") + i), 0x56 + i) for i in range(10)]
    if not small:
        chars[26:26] = [(chr(ord("a") + i), 0x3B + i) for i in range(26)]
    lines = [f"// English {'small' if small else 'normal'} font: see tools/font.py for the format. "
             "Bootstrapped from the ROM's Latin glyphs.", "= space 20 w4", ""]
    for ch, code in chars:
        rows = cell_rows(rom, first + code)[:height]
        ink = [x for x in range(16) if any(v >> (15 - x) & 1 for v in rows)]
        lo, hi = min(ink), max(ink)
        rows = [(v << lo) & 0xFFFF for v in rows]
        lines.append(f"= {ch} {code:X}")
        lines += art(rows, hi - lo + 2)
        lines.append("")
    Path(out).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(out)


def main():
    args = [a for a in sys.argv[1:] if a != "--small"]
    small = "--small" in sys.argv
    if len(args) == 3 and args[0] == "extract":
        extract(Path(args[1]).read_bytes(), args[2], small)
        return 0
    if args == ["check"]:
        for name, g in load_all().items():
            print(f"{FONTS[name][0].relative_to(ROOT)}: {len(g)} glyphs ok")
        return 0
    if len(args) == 2 and args[0] == "width":
        print(text_width(args[1], widths("small" if small else "normal")))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
