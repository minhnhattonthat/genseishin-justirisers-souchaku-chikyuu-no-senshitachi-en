"""script.py: the script block as text: dump the 791 messages to script/*.tsv and encode them back.

    python -X utf8 tools/script.py dump ROM [--force]   write script/sNN_ADDR.tsv (one per sub-table)
    python -X utf8 tools/script.py check ROM            roundtrip + coverage report (exit 1 on any failure)
    python -X utf8 tools/script.py find ROM TEXT        ids of messages whose jp contains TEXT

TSV columns: id, slots, jp, en, notes. One row per message (0x1F-terminated segment) of the block unpacked by
tools/textblock.py, in ROM order.
- id: the message's original ROM offset (6 hex digits), stable across rebuilds.
- slots: the sub-table entries that point at it (`0-3,7`); empty when only reached as a shared tail.
- jp: decoded through tbl/jp.tbl without the final {end}. {n} = 0x1D line break, {p} = 0x1E (break + the caller's
  page wait), other control codes per tbl/jp.tbl and docs/re/text.md. `{tail}` (no bytes) marks where a sub-table
  entry points mid-message (sub-table 3, entries 16-18): the text after it is reached on its own too.
- en: the translation, empty until phase 6. `dump` keeps every existing en/notes value (it refuses to touch an
  existing file without --force, and with --force rewrites only id/slots/jp).
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import textblock  # noqa: E402
from tbl import Table  # noqa: E402

SCRIPT = ROOT / "script"
TBL = ROOT / "tbl" / "jp.tbl"
COLS = ["id", "slots", "jp", "en", "notes"]
TAIL = "{tail}"


def table_lines():
    """tbl/jp.tbl plus a `{cXXX}` name for every 2-byte glyph (lead 0x01-0x0B) it doesn't name, so an unread cell
    decodes as one token and never splits into a lead byte + a control code."""
    lines = TBL.read_text(encoding="utf-8-sig").splitlines()
    named = {ln.partition("=")[0].upper() for ln in lines if "=" in ln and not ln.startswith("#")}
    return lines + [f"{c:04X}={{c{c:03X}}}" for c in range(0x100, 0xC00) if f"{c:04X}" not in named]


def table():
    return Table(table_lines())


def decode(t, msg, tails=()):
    """msg bytes (ending in 0x1F) -> text; tails = byte offsets where a slot points mid-message."""
    assert msg.endswith(b"\x1f"), msg
    body, parts, last = msg[:-1], [], 0
    for off in sorted(set(tails)) + [len(body)]:
        parts.append(t.decode(body, last, off - last)[0])
        last = off
    return TAIL.join(parts)


def encode(t, text):
    """text -> (msg bytes ending in 0x1F, [tail byte offsets])."""
    out, tails = bytearray(), []
    for i, part in enumerate(text.split(TAIL)):
        if i:
            tails.append(len(out))
        out += t.encode(part)
    return bytes(out) + b"\x1f", tails


def ranges(xs):
    xs, out = sorted(xs), []
    for x in xs:
        if out and out[-1][1] == x - 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in out)


def rows(rom, t=None):
    """-> [(file stem, [row dict])] for every sub-table, from the original ROM."""
    t = t or table()
    model = textblock.unpack(rom)
    addr = textblock.MASTER + 4 * len(model["master"])
    out = []
    for si, sub in enumerate(model["subs"]):
        stem = f"s{si:02d}_{addr:06X}"
        a = addr + 2 * len(sub["entries"])
        slots = {k: [] for k in range(len(sub["msgs"]))}
        tails = {k: [] for k in range(len(sub["msgs"]))}
        for i, (k, off) in enumerate(sub["entries"]):
            if k == len(sub["msgs"]):
                continue                      # end-of-text slot (sub 3 entries 305-383): no message
            (tails[k] if off else slots[k]).append(off if off else i)
        rs = []
        for k, msg in enumerate(sub["msgs"]):
            rs.append({"id": f"{a:06X}", "slots": ranges(slots[k]), "jp": decode(t, msg, tails[k]), "en": "", "notes": ""})
            a += len(msg)
        out.append((stem, rs))
        addr = a
    return out


def read_tsv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def write_tsv(path, rs):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLS, delimiter="\t", quoting=csv.QUOTE_NONE, lineterminator="\n")
        w.writeheader()
        w.writerows(rs)


def load_script():
    """-> {id: row} from script/*.tsv."""
    out = {}
    for p in sorted(SCRIPT.glob("s*.tsv")):
        for r in read_tsv(p):
            out[r["id"]] = r
    return out


def dump(rom, force=False):
    SCRIPT.mkdir(exist_ok=True)
    wrote = kept = 0
    for stem, rs in rows(rom):
        path = SCRIPT / f"{stem}.tsv"
        if path.exists():
            if not force:
                kept += 1
                continue
            old = {r["id"]: r for r in read_tsv(path)}
            for r in rs:
                if r["id"] in old:
                    r["en"], r["notes"] = old[r["id"]]["en"], old[r["id"]]["notes"]
        write_tsv(path, rs)
        wrote += 1
    print(f"script/: wrote {wrote} files, kept {kept} existing" + (" (use --force to refresh jp)" if kept else ""))


def check(rom):
    """Roundtrip every message and check the dump covers the whole block. -> list of error strings."""
    t = table()
    errs = []
    model = textblock.unpack(rom)
    addr = textblock.MASTER + 4 * len(model["master"])
    covered = 0
    for si, sub in enumerate(model["subs"]):
        tails = {}
        for k, off in sub["entries"]:
            if off:
                tails.setdefault(k, set()).add(off)
        a = addr + 2 * len(sub["entries"])
        covered += 2 * len(sub["entries"])
        for k, msg in enumerate(sub["msgs"]):
            text = decode(t, msg, tails.get(k, ()))
            back, tl = encode(t, text)
            if back != msg or set(tl) != tails.get(k, set()):
                errs.append(f"{a:06X}: roundtrip differs: {text!r}")
            if rom[a:a + len(msg)] != msg:
                errs.append(f"{a:06X}: message not at its address")
            a += len(msg)
            covered += len(msg)
        addr = a
    covered += 4 * len(model["master"])
    if addr != textblock.END or covered != textblock.END - textblock.MASTER:
        errs.append(f"coverage: tables + messages end at {addr:06X} and cover {covered} bytes; "
                    f"block is {textblock.MASTER:06X}-{textblock.END:06X}")
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dump", "check", "find"])
    ap.add_argument("rom")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    rom = Path(a.rom).read_bytes()
    if a.cmd == "dump":
        dump(rom, a.force)
        return 0
    if a.cmd == "find":
        for stem, rs in rows(rom):
            for r in rs:
                if a.text in r["jp"]:
                    print(f"{stem}\t{r['id']}\t{r['jp']}")
        return 0
    errs = check(rom)
    for e in errs:
        print(e)
    n = sum(len(rs) for _, rs in rows(rom))
    print(f"{n} messages, {len(errs)} errors")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
