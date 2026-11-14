"""romcheck.py: ROM-level checks of a build (references/pipeline.md §Checks), run by build.py and tests/test_romcheck.py.

    python -X utf8 tools/romcheck.py [en|marker]   build in memory and print every error (exit 1 on any)

Checks (each returns error strings; [] = pass):
- writes:   tools/romdiff.py with the build's write log (insert.build): ORIG holds each write's expected bytes, NEW
            still holds what each wrote, no two writes overlap, no changed byte without a write;
            and every write lies inside tbl/allowed.txt.
- pointer:  resource group 2 (0xD226B4) points at the relocated block + 4, and the block there unpacks
            (textblock.unpack at FREE) to exactly the model the build packed.
- texts:    every message the build replaced decodes back from the built ROM to its encoded text.
- jp left:  (en build) no kana/kanji in any message of the built block except rows whose notes start with
            nontext/debug (dev readouts, kept Japanese by design; placeholders are English since D10).
- readers:  no 2-aligned word in the original ROM (bank 0x08 with flag bits masked, or a 0x0A-0x0D mirror; see
            reader_hits) points at a structure of the old block (master,
            sub-table, message, shared tail) except the group 2 word, which the build rewrites. 0xD226B8 (group 3)
            points at the block's end = the next resource, unmoved: allowed.
- branches: no Thumb B/Bcc/BL within +-4 KB of a multi-halfword code patch lands strictly inside it.
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import asmpatch  # noqa: E402
import check_rom  # noqa: E402
import insert  # noqa: E402
import romdiff  # noqa: E402
import script  # noqa: E402
import textblock  # noqa: E402

KNOWN_READERS = {textblock.GROUP_PTR + 4: "resource group 3 = the block's end (next resource, not moved)"}
# Flagged / unaligned matches of the wide scan that sit inside compressed or graphics data (high-entropy bytes,
# no code reference; phase 7 review item 9 found the same 10), plus 5 0x0A/0x0C-mirror matches in the resource
# area past 0x800000. Any new hit fails the check.
for _off in (0x03F70A, 0x27A810, 0x298D6A, 0x7C1C0E, 0x91BE4C, 0x9CE446, 0xAEDD86, 0xB8DCFE, 0xBBD7CC, 0xC5EC74,
             0x8240A4, 0x83AEC2, 0x9ED39C, 0xA06028, 0xCBB93E):
    KNOWN_READERS[_off] = "graphics/compressed data bytes, not a pointer"


def allowed_ranges(path=ROOT / "tbl" / "allowed.txt"):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            lo, _, hi = line.split()[0].partition("-")
            out.append((int(lo, 16), int(hi or lo, 16)))
    return out


def check_writes(orig, new, writes, ranges=None):
    ranges = ranges if ranges is not None else allowed_ranges()
    errs, _ = romdiff.check(orig, new, set(), writes)
    for off, o, _, by in writes:
        end = off + len(o) - 1
        if not any(lo <= off and end <= hi for lo, hi in ranges):
            errs.append(f"0x{off:06X}-0x{end:06X}: write by {by} outside tbl/allowed.txt")
    return errs


def check_pointer(new, model):
    errs = []
    ptr = struct.unpack_from("<I", new, textblock.GROUP_PTR)[0]
    if ptr != 0x08000000 + insert.FREE + 4:
        return [f"group 2 word {textblock.GROUP_PTR:X} = {ptr:08X}, want {0x08000000 + insert.FREE + 4:08X}"]
    try:
        got = textblock.unpack(new, insert.FREE)
    except Exception as e:  # noqa: BLE001
        return [f"relocated block at {insert.FREE:X} does not unpack: {e}"]
    if got != model:
        errs.append("relocated block unpacks to a different model than the build packed")
    return errs


def check_texts(new, orig_ids, texts, table):
    """texts: {id: text} the build replaced; orig_ids: insert.message_ids() of the original model."""
    errs = []
    got = textblock.unpack(new, insert.FREE)
    seen = 0
    for sub, ids in zip(got["subs"], orig_ids):
        for k, mid in enumerate(ids):
            if mid in texts:
                seen += 1
                want = script.encode(table, texts[mid])[0]
                if sub["msgs"][k] != want:
                    errs.append(f"{mid}: built bytes differ from the encoded text")
    if seen != len(texts):
        errs.append(f"{len(texts) - seen} replaced texts have no message slot (ids {sorted(set(texts) - set(sum(orig_ids, [])))[:5]})")
    return errs


JP = re.compile("[぀-ヿ一-鿿]")
KEEP_JP = ("nontext", "debug")   # script notes of rows that stay Japanese (dev-only, never shown; D10)


def check_leftover_jp(new, orig_ids, table, rows=None):
    """Decode every message of the built block; kana/kanji outside rows whose notes start with KEEP_JP fails.
    (The skill's jp_left.py assumes NUL-terminated strings; messages here end with 0x1F.)"""
    rows = rows or script.load_script()
    errs = []
    got = textblock.unpack(new, insert.FREE)
    for sub, ids in zip(got["subs"], orig_ids):
        for m, mid in zip(sub["msgs"], ids):
            plain = re.sub(r"\{[^}]*\}", "", script.decode(table, m))
            if JP.search(plain) and not rows[mid]["notes"].startswith(KEEP_JP):
                errs.append(f"{mid}: Japanese left in the built ROM: {plain[:40]!r}")
    return errs


def structure_starts(orig):
    m = textblock.unpack(orig)
    ids = insert.message_ids(m)
    starts = set(insert.addresses(m, textblock.MASTER, ids))
    a = textblock.MASTER + 4 * len(m["master"])
    for s in m["subs"]:
        starts.add(a)
        a += 2 * len(s["entries"]) + sum(map(len, s["msgs"]))
    return starts | {textblock.MASTER + 4 * i for i in range(textblock.NMASTER)} | {textblock.END}


def reader_hits(orig):
    """-> {offset: word} for every 2-aligned word outside the block whose flag nibble is masked off
    (w & 0x0E000000 == 0x08000000: bank 0x08 with any flag bits above; or a clean 0x0A-0x0D wait-state mirror)
    and whose offset (w & 0x01FFFFFF) is an old-block structure start
    (pipeline.md §Checks: mask flag bits, don't assume alignment)."""
    out = {}
    for s in structure_starts(orig):
        pat = struct.pack("<I", s)[:3]
        i = orig.find(pat)
        while i != -1:
            if i % 2 == 0 and i + 3 < len(orig) and not textblock.MASTER <= i < textblock.END:
                w = struct.unpack_from("<I", orig, i)[0]
                top = w >> 24
                if (top & 0x0E == 0x08 or 0x0A <= top <= 0x0D) and w & 0x01FFFFFF == s:   # flagged ROM / mirrors
                    out[i] = w
            i = orig.find(pat, i + 1)
    return out


def check_readers(orig, rewritten=(textblock.GROUP_PTR,)):
    errs = []
    for i, w in sorted(reader_hits(orig).items()):
        if i in rewritten or i in KNOWN_READERS:
            continue
        errs.append(f"0x{i:06X}: word {w:08X} points into the old script block and is not rewritten")
    return errs


def branch_targets(rom, lo, hi):
    """-> [(src, target)] for Thumb B/Bcc/BL in [lo, hi)."""
    out = []
    for a in range(lo & ~1, hi, 2):
        h = struct.unpack_from("<H", rom, a)[0]
        if 0xD000 <= h < 0xDE00:
            out.append((a, a + 4 + ((h & 0xFF) ^ 0x80) * 2 - 0x100))
        elif 0xE000 <= h < 0xE800:
            out.append((a, a + 4 + ((h & 0x7FF) ^ 0x400) * 2 - 0x800))
        elif 0xF000 <= h < 0xF800 and a + 2 < len(rom):
            lo_h = struct.unpack_from("<H", rom, a + 2)[0]
            if lo_h >= 0xF800:
                hi_off = ((h & 0x7FF) ^ 0x400) - 0x400
                out.append((a, a + 4 + (hi_off << 12) + (lo_h & 0x7FF) * 2))
    return out


def check_branches(orig):
    errs = []
    for addr, o, new in asmpatch.PATCHES:
        if o is None or len(new) <= 2:   # hook code in the old block / one-halfword patch: no interior
            continue
        for src, t in branch_targets(orig, max(0, addr - 0x1000), addr + len(new) + 0x1000):
            if addr < t < addr + len(new) and not addr <= src < addr + len(new):
                errs.append(f"branch at 0x{src:06X} lands at 0x{t:06X}, inside the patch 0x{addr:X}-0x{addr + len(new):X}")
    return errs


def run(orig, mode="en", qa=None):
    """Build and run every check -> (rom, writes, errors)."""
    new, writes, st = insert.build(orig, mode, qa)
    errs = check_writes(orig, new, writes)
    errs += check_pointer(new, st["model"])
    errs += check_texts(new, st["ids"], st["texts"], st["table"])
    if mode == "en":
        errs += check_leftover_jp(new, st["ids"], st["table"])
    errs += check_readers(orig)
    errs += check_branches(orig)
    return new, writes, errs


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "en"
    orig = check_rom.original()
    _, writes, errs = run(orig, mode)
    for e in errs:
        print(e)
    print(f"romcheck {mode}: {len(writes)} writes, {len(errs)} errors")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
