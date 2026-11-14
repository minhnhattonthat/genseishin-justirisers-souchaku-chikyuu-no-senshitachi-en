"""glyphmatch.py: guess which character each font cell is by template-matching it against MS Gothic (phase 4 aid).

    python -X utf8 tools/glyphmatch.py ROM CODES [--set kanji|kana|all] [--top 3] [--sheet OUT.png --tbl tbl/jp.tbl]

CODES: comma list of hex codes and ranges (`200-2FF,60`). For each cell prints the best candidates with scores.
--sheet renders each cell beside the MS Gothic glyph of its current tbl value (or the best guess when the tbl has
none), labelled with the code, to check guesses by eye. Analysis only (needs Pillow and numpy); the build does not
import this. A first guess, not a verdict: confirm every kanji in context (docs/re/text.md).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fontsheet import BASE, glyph  # noqa: E402

FONT = "C:/Windows/Fonts/msgothic.ttc"


def cell(rom, code):
    return np.array(glyph(rom, BASE, code), dtype=np.float32)


def charset(kind):
    chars = []
    if kind in ("kana", "all"):
        chars += [chr(c) for c in range(0x3041, 0x3097)] + [chr(c) for c in range(0x30A1, 0x30FB)]
        chars += list("ー・…、。！？「」『』（）〜～−＋×÷＝％＆＊＠☆★○●◎◇◆□■△▲▽▼→←↑↓♪：；，．’”")
    if kind in ("kanji", "all"):
        for hi in range(0x88, 0xEB):
            for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
                try:
                    ch = bytes([hi, lo]).decode("cp932")
                except UnicodeDecodeError:
                    continue
                if len(ch) == 1 and ord(ch) >= 0x4E00:
                    chars.append(ch)
    return chars


def render(ch, font, size=16):
    im = Image.new("L", (size, size), 0)
    ImageDraw.Draw(im).text((0, 0), ch, fill=255, font=font)
    return np.array(im, dtype=np.float32) / 255.0


def norm(a):
    a = np.array(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32)
    a -= a.mean()
    n = np.linalg.norm(a)
    return a / n if n else a


def shifts(a, r=2):
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            yield np.roll(np.roll(a, dy, 0), dx, 1)


def parse_codes(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = (int(x, 16) for x in part.split("-"))
            out += range(a, b + 1)
        elif part:
            out.append(int(part, 16))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("codes")
    ap.add_argument("--set", default="kanji", choices=["kanji", "kana", "all"])
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--sheet")
    ap.add_argument("--tbl")
    a = ap.parse_args()
    rom = Path(a.rom).read_bytes()
    font = ImageFont.truetype(FONT, 16)
    chars = charset(a.set)
    refs = np.stack([norm(render(c, font)) for c in chars])          # (N,16,16)
    codes = parse_codes(a.codes)
    best = {}
    for code in codes:
        g = cell(rom, code)
        if not g.any():
            print(f"{code:03X}\t(blank)")
            continue
        sc = np.max([np.tensordot(refs, norm(s), axes=([1, 2], [0, 1])) for s in shifts(g)], axis=0)
        idx = np.argsort(-sc)[:a.top]
        best[code] = chars[idx[0]]
        print(f"{code:03X}\t" + "  ".join(f"{chars[i]} {sc[i]:.2f}" for i in idx))
    if a.sheet:
        tbl = {}
        if a.tbl:
            for line in Path(a.tbl).read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition("=")
                if v and not line.startswith("#") and not v.startswith("{"):
                    tbl[int(k, 16) if len(k) <= 2 else int(k, 16)] = v
        z, cols = 3, 8
        lab = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
        w, h = (16 * 2 + 6) * z + 40, 16 * z + 14
        rows = (len(codes) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, rows * h), "white")
        dr = ImageDraw.Draw(sheet)
        for i, code in enumerate(codes):
            x, y = (i % cols) * w, (i // cols) * h
            g = Image.fromarray((255 - cell(rom, code) * 255).astype(np.uint8)).resize((16 * z, 16 * z), Image.NEAREST)
            sheet.paste(g, (x + 4, y + 12))
            key = (code >> 8) << 8 | (code & 0xFF)
            ch = tbl.get(key, best.get(code, "?"))
            ref = Image.fromarray((255 - render(ch, font) * 255).astype(np.uint8)).resize((16 * z, 16 * z), Image.NEAREST)
            sheet.paste(ref, (x + 8 + 16 * z, y + 12))
            dr.text((x + 4, y), f"{code:03X}", fill="red", font=lab)
        sheet.save(a.sheet)
        print("sheet", a.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
