"""build.py: build the English ROM.

    python -X utf8 build.py              -> build/justirisers_en.gba: English font, the script's `en` text, block
                                            relocated to free space (prints size and SHA-1)
    python -X utf8 build.py --marker     -> build/justirisers_marker.gba: every text message replaced by
                                            `[id] pangram...` filling the Japanese line's pixel width
    python -X utf8 build.py --qa ID=TEXT -> also override message ID (repeatable; stress lines for the width gate)
    python -X utf8 build.py --verify     also build the identity ROM (unpack + repack in place, no edits) and
                                         require it to be byte-identical to the original

Steps: check the dump against rom.sha1, unpack the script block (tools/textblock.py), write the English font
(tools/font.py), swap in English/marker text (tools/insert.py), pack the block at 0xD23570 and repoint resource
group 2. tools/romcheck.py then checks the result: every write logged (build/writes.txt, tools/romdiff.py --writes)
and inside tbl/allowed.txt, the group 2 word on the relocated block, every replaced text in it, no reader of the
old block left, no branch into a code patch. Any error stops the build.
"""
import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

import check_rom  # noqa: E402
import textblock  # noqa: E402

OUT = ROOT / "build" / "justirisers_en.gba"
MARKER = ROOT / "build" / "justirisers_marker.gba"


def rom_path():
    return check_rom.rom_path()


def lint_script(skip_ids):
    """The text lint (tools/textlint.py) gates every en build, so an overflowing TSV edit never reaches the
    emulator. Ids overridden with --qa are stress tests and skipped."""
    import script
    import textlint
    lint, errs = textlint.Lint(), []
    for f in sorted((ROOT / "script").glob("s*.tsv")):
        for r in script.read_tsv(f):
            if r["id"] in skip_ids or r["notes"].startswith(("nontext", "placeholder", "debug")):
                continue
            errs += lint.check(int(f.name[1:3]), r)
    if errs:
        raise SystemExit("textlint failed:\n" + "\n".join(errs[:40]))


def write_strings(addrs):
    """build/strings.tsv for $SKILL/scripts/textcover.py: one 'id<TAB>CPU address' per message the game reads
    (first byte, in the relocated block; shared tails are reached through their owner and left out)."""
    rows = sorted((mid, a) for a, mid in addrs.items() if not mid.endswith("+tail"))
    (ROOT / "build" / "strings.tsv").write_text(
        "".join(f"{mid}\t{0x08000000 + a:X}\n" for mid, a in rows), encoding="utf-8")


def build(orig, mode="identity", qa=None):
    """mode 'identity': repack in place, no edits (== orig). 'en' / 'marker': see tools/insert.py, checked by
    tools/romcheck.py (write log -> build/writes.txt; raises on any error)."""
    if mode != "identity":
        import insert
        import romcheck
        if mode == "en":
            lint_script({k.upper() for k in (qa or {})})
        st = {}
        rom, writes, errs = romcheck.run(orig, mode, qa, st)
        (ROOT / "build").mkdir(exist_ok=True)
        (ROOT / "build" / "writes.txt").write_text(insert.write_log(writes), encoding="utf-8")
        write_strings(st["addresses"])
        if errs:
            raise SystemExit("romcheck failed:\n" + "\n".join(errs[:40]))
        return rom
    rom = bytearray(orig)
    blob = textblock.pack(textblock.unpack(orig), textblock.MASTER)
    rom[textblock.MASTER:textblock.MASTER + len(blob)] = blob
    return bytes(rom)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="also check the identity build equals the original")
    ap.add_argument("--marker", action="store_true", help="build the marker ROM instead")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT", help="override one message")
    ap.add_argument("--out", help="output path")
    a = ap.parse_args()
    check_rom.check()
    orig = rom_path().read_bytes()
    qa = dict(x.split("=", 1) for x in a.qa)
    out_path = Path(a.out) if a.out else (MARKER if a.marker else OUT)
    out = build(orig, "marker" if a.marker else "en", qa)
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_bytes(out)
    print(f"{out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path}: {len(out)} bytes, "
          f"sha1 {hashlib.sha1(out).hexdigest()}")
    if a.verify:
        ident = build(orig)
        if ident != orig:
            print(f"identity build NOT identical: {sum(1 for x, y in zip(ident, orig) if x != y)} bytes differ")
            return 1
        print("identity build identical to the original")
    return 0


if __name__ == "__main__":
    sys.exit(main())
