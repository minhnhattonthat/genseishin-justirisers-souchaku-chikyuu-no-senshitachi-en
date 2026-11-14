"""build.py: build the English ROM.

    python -X utf8 build.py            -> build/justirisers_en.gba (prints size and SHA-1)
    python -X utf8 build.py --verify   build, then require it to be byte-identical to the original (identity build)

Steps: check the dump against rom.sha1, unpack the script block (tools/textblock.py), repack it in place.
Phase 3 (identity build): no edits yet, so the output equals the original; tests/test_identity.py keeps it so.
Later phases feed the English script into the model before pack().
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


def rom_path():
    line = next(x for x in (ROOT / "rom.sha1").read_text(encoding="utf-8").splitlines()
                if x.strip() and not x.startswith("#"))
    return ROOT / line.split(None, 1)[1].strip().lstrip("*")


def build(orig):
    rom = bytearray(orig)
    model = textblock.unpack(orig)
    blob = textblock.pack(model, textblock.MASTER)
    room = textblock.END - textblock.MASTER
    if len(blob) > room:
        raise SystemExit(f"script block is {len(blob)} bytes, {len(blob) - room} over its {room}-byte home "
                         "(relocation comes with the insert step)")
    rom[textblock.MASTER:textblock.MASTER + len(blob)] = blob
    return bytes(rom)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="fail unless the output equals the original")
    a = ap.parse_args()
    check_rom.check()
    orig = rom_path().read_bytes()
    out = build(orig)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(out)
    print(f"{OUT.relative_to(ROOT)}: {len(out)} bytes, sha1 {hashlib.sha1(out).hexdigest()}")
    if a.verify:
        if out != orig:
            diff = sum(1 for x, y in zip(out, orig) if x != y)
            print(f"NOT identical: {diff} bytes differ")
            return 1
        print("identical to the original")
    return 0


if __name__ == "__main__":
    sys.exit(main())
