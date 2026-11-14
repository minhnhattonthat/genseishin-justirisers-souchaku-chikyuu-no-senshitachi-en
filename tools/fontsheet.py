"""fontsheet.py: render the game's 16x16 1bpp font (2 bytes per row, MSB = left pixel, 32 bytes per glyph) as a
labelled PNG sheet, for building tbl/jp.tbl by eye.

    python -X utf8 tools/fontsheet.py ROM OUT.png [--base 2CBC34] [--first 0] [--count 256] [--zoom 2] [--cols 16]

Font: ROM 0x2CBC34 (resource 0x4600, read by the glyph lookup at 08008DFC); glyph address = base + code * 32.
Needs Pillow (analysis only; the build does not import this).
"""
import argparse

from PIL import Image, ImageDraw

BASE = 0x2CBC34


def glyph(rom, base, code):
    off = base + code * 32
    rows = []
    for y in range(16):
        w = rom[off + 2 * y] << 8 | rom[off + 2 * y + 1]
        rows.append([(w >> (15 - x)) & 1 for x in range(16)])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--base", default="%X" % BASE)
    ap.add_argument("--first", default="0")
    ap.add_argument("--count", type=int, default=256)
    ap.add_argument("--zoom", type=int, default=2)
    ap.add_argument("--cols", type=int, default=16)
    a = ap.parse_args()
    rom = open(a.rom, "rb").read()
    base, first, z = int(a.base, 16), int(a.first, 16), a.zoom
    cw, ch = 16 * z + 4, 16 * z + 12
    rows = (a.count + a.cols - 1) // a.cols
    img = Image.new("RGB", (a.cols * cw, rows * ch), "white")
    d = ImageDraw.Draw(img)
    for i in range(a.count):
        code = first + i
        gx, gy = (i % a.cols) * cw, (i // a.cols) * ch
        d.text((gx + 1, gy), "%03X" % code, fill=(200, 0, 0))
        for y, row in enumerate(glyph(rom, base, code)):
            for x, bit in enumerate(row):
                if bit:
                    d.rectangle([gx + 2 + x * z, gy + 11 + y * z, gx + 2 + x * z + z - 1, gy + 11 + y * z + z - 1],
                                fill="black")
    img.save(a.out)
    print(a.out)


if __name__ == "__main__":
    main()
