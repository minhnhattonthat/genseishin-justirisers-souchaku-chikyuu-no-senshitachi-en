"""scan_tables.py: find the game's message tables (recon, phase 1).

Format (verified on the story intro, see docs/re/text.md): a run of u16 LE self-relative offsets; the entry at A
points at A + value. Messages end in 0x1F, so every target is either the first byte after the table or follows a
0x1F. Unused slots repeat the last real target (an empty message). Tables sit at odd addresses too.

    python -X utf8 tools/scan_tables.py ROM [--min 4] [--range 1E0000-200000] > work/tables.tsv

Prints: table_start  entries  table_end(first message)  text_end  distinct_targets
"""
import argparse


def scan(d, lo=0, hi=None, min_entries=4):
    hi = min(hi or len(d), len(d) - 2)
    # hit[x]: the u16 at x points forward at a byte that follows a 0x1F
    hit = bytearray(hi + 2)
    for x in range(lo, hi):
        v = d[x] | d[x + 1] << 8
        if 2 <= v < 0x8000:
            t = x + v
            if t < len(d) and d[t - 1] == 0x1F:
                hit[x] = 1
    out = []
    x = lo
    while x < hi:
        if not hit[x]:
            x += 1
            continue
        # the first entry points at the table end (no 0x1F before it); try x-2 as the start
        start = x - 2 if x - 2 >= lo else x
        b = start
        targets = []
        while b < hi:
            v = d[b] | d[b + 1] << 8
            if not 2 <= v < 0x8000:
                break
            t = b + v
            if targets and b >= min(targets):
                break
            if not (hit[b] or t == b + 2 * 0 + v and b == start):
                break
            targets.append(t)
            b += 2
        end = b
        if len(targets) >= min_entries and min(targets) == end:
            last = max(targets)
            e = d.find(b"\x1f", last)
            out.append((start, len(targets), end, e + 1, len(set(targets))))
            x = e + 1
        else:
            x += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--min", type=int, default=4)
    ap.add_argument("--range", default=None)
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    lo, hi = 0, None
    if a.range:
        lo, hi = (int(s, 16) for s in a.range.split("-"))
    for row in scan(d, lo, hi, a.min):
        print("%06X\t%d\t%06X\t%06X\t%d" % row)


if __name__ == "__main__":
    main()
