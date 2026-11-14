"""insert.py: put English (or marker) text into the unpacked script block, write the English font, relocate.

Used by build.py. English text is encoded with en_table(): the glyphs of font/en.txt (tools/font.py) first, then
every entry of tbl/jp.tbl (control codes, spacer cells, and Japanese glyphs as a fallback).

- Messages keep their sub-table slots; a message's `{tail}` markers move its shared-tail slots with the text.
- Rows whose `notes` start with `nontext` are never replaced (debug readouts, placeholders, include templates).
- `{padNN}` cells in a line (name-list columns) are recomputed so the line keeps its original pixel width
  (`fill()`): the English text plus the fewest spacer cells (12/6/4/2/1 px) that make up the difference.
- The block is packed at FREE (trap-tested free space, docs/re/text.md) and resource group 2 is repointed there.
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import asmpatch  # noqa: E402
import bgtext  # noqa: E402
import font  # noqa: E402
import script  # noqa: E402
import textblock  # noqa: E402
from tbl import Table  # noqa: E402

FREE, FREE_END = 0xD23570, 0xF00000   # 0xD2356C-0xF00000 is 0xFF fill (text.md §Free space), 4-aligned start
TOKEN = re.compile(r"(\{[^}]*\})")
BREAKS = ("{n}", "{p}")
# blank spacer cells (normal font widths). Every glyph width is even (tools/font.py), so every gap is too.
PAD_CELLS = [(f"{{pad{w}}}", w) for w in range(204, 0, -12) if w not in (84,)] + [
    ("{sp6}", 6), ("{sp4}", 4), ("{sp2}", 2)]
PANGRAM = ("The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs! "
           "How vexingly quick daft zebras jump? Sphinx of black quartz, judge my vow.")


def en_table(glyphs=None):
    glyphs = glyphs or font.load()
    lines = []
    for ch, g in sorted(glyphs.items(), key=lambda x: x[1]["code"]):
        c = g["code"]
        val = r"\s" if ch == " " else ch
        lines.append(f"{c:02X}={val}" if c < 0x100 else f"{c:04X}={val}")
    return Table(lines + script.table_lines())


def codes(b):
    """Glyph codes in encoded bytes (control codes 0x10-0x1F and their argument bytes skipped)."""
    p = 0
    while p < len(b):
        c = b[p]
        if 0 < c <= 0x0F:
            yield c << 8 | b[p + 1]
            p += 2
        elif 0x10 <= c <= 0x1F or c == 0:
            p += 1 + textblock.ARGS.get(c, 0)
        else:
            yield c
            p += 1


def px(b, wt):
    """Pixel width of encoded bytes given a width table (bytes, codes 0-0x1FF; higher codes are 12 px)."""
    return sum(wt[c] if c < 0x200 else 12 for c in codes(b))


def is_glyph_token(t, tok):
    """True when {tok} encodes to a glyph cell (spacer, {cXXX}, {g135}) rather than a control code."""
    b = t.encode(tok)
    return bool(b) and not 0x10 <= b[0] <= 0x1F


def fill(gap):
    """Spacer tokens totalling `gap` px (gap >= 0)."""
    out = []
    for name, w in PAD_CELLS:
        while gap >= w:
            out.append(name)
            gap -= w
    return "".join(out)


def split_lines(text):
    """'a{n}b{p}c' -> ['a', '{n}', 'b', '{p}', 'c']"""
    return re.split(r"(\{n\}|\{p\})", text)


def has_text(t, line):
    for part in TOKEN.split(line):
        if not part:
            continue
        if part.startswith("{"):
            if is_glyph_token(t, part) and not part.startswith(("{pad", "{sp")):
                return True
        elif part.strip():
            return True
    return False


def marker_line(jt, et, wt_jp, wt_en, line, prefix):
    """One line of marker text: leading controls kept, Japanese replaced by `prefix` + pangram words that fit the
    Japanese line's pixel width, {var}/trailing controls kept after it, pads refilled to the original width."""
    parts = [p for p in TOKEN.split(line) if p]
    width = px(jt.encode(line), wt_jp)
    lead, tail, padded = [], [], False
    seen_text = False
    for p in parts:
        if p.startswith("{") and not is_glyph_token(jt, p):
            (tail if seen_text else lead).append(p)
        elif p.startswith(("{pad", "{sp")) and seen_text:
            padded = True
        elif p.startswith(("{pad", "{sp")):
            lead.append(p)
        elif not seen_text and p.strip() and p != p.lstrip(" "):
            lead.append(p[:len(p) - len(p.lstrip(" "))])   # menu indent before the first text
            seen_text = True
        elif p.strip():
            seen_text = True
        elif not seen_text:
            lead.append(p)
    lead_w = px(jt.encode("".join(lead)), wt_jp)
    tail_w = px(jt.encode("".join(tail)), wt_jp)
    room = width - lead_w - tail_w
    words, out = PANGRAM.split(" "), prefix
    for w in words:
        cand = (out + " " + w) if out else w
        if px(et.encode(cand), wt_en) > room:
            break
        out = cand
    text = "".join(lead) + out + "".join(tail)
    if padded:
        text += fill(max(0, width - px(et.encode(text), wt_en)))
    return text


def marker_text(jt, et, wt_jp, wt_en, row):
    """Marker for a whole message: every line with Japanese text gets pangram filler, the first one the id."""
    prefix = f"[{row['id'][1:]}]"
    out = []
    for seg in split_lines(row["jp"]):
        if seg in BREAKS or not has_text(jt, seg.replace(script.TAIL, "")):
            out.append(seg)
            continue
        tails = seg.split(script.TAIL)
        seg_out = []
        for piece in tails:
            if has_text(jt, piece):
                seg_out.append(marker_line(jt, et, wt_jp, wt_en, piece, prefix))
                prefix = ""
            else:
                seg_out.append(piece)
        out.append(script.TAIL.join(seg_out))
    return "".join(out)


def fill_pads(jt, et, wt_jp, wt_en, jp, en):
    """Replace each `{fill}` in an English line with spacer cells that bring the line back to the pixel width of
    the Japanese line in the same position (column rows: name lists, stage-clear list)."""
    if "{fill}" not in en:
        return en
    jl, el = split_lines(jp), split_lines(en)
    if len(jl) != len(el):
        raise ValueError(f"{{fill}} needs the Japanese line layout: {en!r}")
    out = []
    for a, b in zip(jl, el):
        if "{fill}" in b:
            gap = px(jt.encode(a.replace(script.TAIL, "")), wt_jp) - px(et.encode(b.replace("{fill}", "")), wt_en)
            b = b.replace("{fill}", fill(max(0, gap)), 1).replace("{fill}", "")
        out.append(b)
    return "".join(out)


def message_ids(model):
    """-> [[id of each message] per sub-table], ids = original ROM offsets as in script/*.tsv."""
    addr = textblock.MASTER + 4 * len(model["master"])
    out = []
    for sub in model["subs"]:
        a = addr + 2 * len(sub["entries"])
        ids = []
        for m in sub["msgs"]:
            ids.append(f"{a:06X}")
            a += len(m)
        out.append(ids)
        addr = a
    return out


def addresses(model, base, ids):
    """-> {ROM offset: id} for every message (and shared-tail target) of `model` packed at `base`, where
    ids = message_ids() of the original model (same shape)."""
    out, a = {}, base + 4 * len(model["master"])
    for sub, sub_ids in zip(model["subs"], ids):
        a += 2 * len(sub["entries"])
        starts = []
        for m, mid in zip(sub["msgs"], sub_ids):
            out[a] = mid
            starts.append(a)
            a += len(m)
        for k, off in sub["entries"]:
            if off:
                out[starts[k] + off] = sub_ids[k] + "+tail"
    return out


def replace(model, texts, table):
    """texts: {id: text}. Encode each and swap it into the model, moving shared-tail slots."""
    for sub, ids in zip(model["subs"], message_ids(model)):
        for k, mid in enumerate(ids):
            if mid not in texts:
                continue
            data, tails = script.encode(table, texts[mid])
            old = sorted({off for kk, off in sub["entries"] if kk == k and off})
            if len(old) != len(tails):
                raise ValueError(f"{mid}: {len(old)} shared tails in the original, {len(tails)} {{tail}} in the text")
            remap = dict(zip(old, tails))
            sub["entries"] = [(kk, remap[off] if kk == k and off else off) for kk, off in sub["entries"]]
            sub["msgs"][k] = data
    return model


def relocate(rom, model):
    """Pack the block at FREE and repoint resource group 2. -> written ranges."""
    blob = textblock.pack(model, FREE)
    if FREE + len(blob) > FREE_END:
        raise SystemExit(f"script block {len(blob)} bytes does not fit the free space {FREE:X}-{FREE_END:X}")
    rom[FREE:FREE + len(blob)] = blob
    old = struct.unpack_from("<I", rom, textblock.GROUP_PTR)[0]
    if old != 0x08000000 + textblock.MASTER + 4:
        raise SystemExit(f"resource group 2 word at {textblock.GROUP_PTR:X} is {old:08X}, not the master + 4")
    struct.pack_into("<I", rom, textblock.GROUP_PTR, 0x08000000 + FREE + 4)
    return [(FREE, FREE + len(blob)), (textblock.GROUP_PTR, textblock.GROUP_PTR + 4)]


def log_writes(orig, rom, ranges, by):
    """Merge the ranges one build step just wrote -> write-log entries (offset, ORIG bytes, bytes now in rom, by).
    Taken right after the step, so tools/romdiff.py --writes catches a later step overwriting it."""
    out = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    pad = lambda s, e: bytes(orig[s:e]).ljust(e - s, b"\xff")  # noqa: E731
    return [(s, pad(s, e), bytes(rom[s:e]), by) for s, e in out]


def write_log(writes):
    """-> romdiff.py --writes text: `OFFSET ORIG_HEX NEW_HEX writer` per line."""
    return "".join(f"{off:X} {o.hex()} {n.hex()} {by}\n" for off, o, n, by in writes)


def build(orig, mode="en", qa=None):
    """mode 'en': English where the script has it; 'marker': marker text in every text message.
    qa: {id: text} overrides (stress lines). -> (rom bytes, write log [(off, orig, new, by)], stats dict)"""
    rom = bytearray(orig)
    fonts = font.load_all()
    writes = log_writes(orig, rom, font.apply(rom, fonts), "font")
    jt, et = script.table(), en_table(fonts["normal"])
    wt_jp, wt_en = orig[font.WIDTHS:font.WIDTHS + 0x200], bytes(rom[font.WIDTHS:font.WIDTHS + 0x200])
    rows = script.load_script()
    texts = {}
    for mid, r in rows.items():
        if r["notes"].startswith("nontext"):
            continue
        if mode == "marker":
            if has_text(jt, r["jp"].replace(script.TAIL, "")):
                texts[mid] = marker_text(jt, et, wt_jp, wt_en, r)
        elif r["en"]:
            texts[mid] = fill_pads(jt, et, wt_jp, wt_en, r["jp"], r["en"])
    texts.update(qa or {})
    model = textblock.unpack(orig)
    ids = message_ids(model)
    model = replace(model, texts, et)
    block, ptr = relocate(rom, model)
    writes += log_writes(orig, rom, [block], "script-block")
    writes += log_writes(orig, rom, [ptr], "group2-pointer")
    # its hooks go in the old block's place, so only after relocating; checked against the clean original
    writes += log_writes(orig, rom, asmpatch.apply(rom, orig), "asmpatch")
    if mode == "en":   # graphics text: BG screens redrawn in English (gfx/bg.tsv)
        writes += log_writes(orig, rom, bgtext.apply(rom, orig), "bgtext")
    return bytes(rom), writes, {"replaced": len(texts), "addresses": addresses(model, FREE, ids), "model": model,
                                "ids": ids, "texts": texts, "table": et}
