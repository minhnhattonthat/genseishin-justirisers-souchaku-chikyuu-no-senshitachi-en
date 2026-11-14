"""check_rom.py: refuse to build from a dump that isn't the one listed in rom.sha1.

A wrong revision or an already-patched copy otherwise builds fine and breaks at random offsets in game.
Call check() at the top of build.py; run it alone to check a fresh dump. Exit 1 on a missing or wrong file."""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(listing=ROOT / "rom.sha1"):
    for line in listing.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        want, name = line.split(None, 1)
        path = ROOT / name.strip().lstrip("*")
        if not path.is_file():
            sys.exit(f"missing {name.strip()}: copy your dump there (see README)")
        with open(path, "rb") as f:
            got = hashlib.file_digest(f, "sha1").hexdigest()
        if got != want.lower():
            sys.exit(f"{name.strip()}: SHA-1 {got}, expected {want}. Wrong revision, a header, or already patched?")


def rom_path(listing=ROOT / "rom.sha1"):
    """Path of the first dump listed in rom.sha1 (it may not exist on a clone)."""
    line = next(x for x in listing.read_text(encoding="utf-8").splitlines()
                if x.strip() and not x.startswith("#"))
    return ROOT / line.split(None, 1)[1].strip().lstrip("*")


def have_rom():
    """True when the dump is present: ROM-dependent tests skip only when this is False."""
    return rom_path().is_file()


_ORIG = None


def original():
    """Bytes of the verified original dump (rom.sha1-checked once per process). Exits on a wrong or missing dump."""
    global _ORIG
    if _ORIG is None:
        check()
        _ORIG = rom_path().read_bytes()
    return _ORIG


if __name__ == "__main__":
    check()
    print("rom ok")
