"""chain_tables.py: walk the message tables as a chain: table, its messages, the next table right after.

    python -X utf8 tools/chain_tables.py ROM [--start 1E91B8] [--max 200]

A table at S: u16 LE self-relative entries until the entry address reaches the smallest target (= first message).
Its text runs to the 0x1F that ends the message with the largest target. Prints one row per table and stops at the
first place where the next bytes don't parse as a table.
"""
import argparse


def parse_table(d, s):
    b, targets = s, []
    while True:
        if targets and b >= min(targets):
            break
        v = d[b] | d[b + 1] << 8
        if not 2 <= v < 0x8000:
            return None
        targets.append(b + v)
        b += 2
    end = b
    if min(targets) != end:
        return None
    for t in targets:
        if t != end and d[t - 1] != 0x1F:
            return None
    text_end = d.find(b"\x1f", max(targets)) + 1
    return targets, end, text_end


def chain(d, start, max_tables=500):
    rows = []
    s = start
    while len(rows) < max_tables:
        r = parse_table(d, s)
        if r is None:
            break
        targets, end, text_end = r
        rows.append((s, len(targets), end, text_end, len(set(targets))))
        s = text_end
    return rows, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--start", default="1E91B8")
    ap.add_argument("--max", type=int, default=500)
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    rows, stop = chain(d, int(a.start, 16), a.max)
    for r in rows:
        print("%06X\t%d\t%06X\t%06X\t%d" % r)
    print("# stopped at %06X: %s" % (stop, d[stop:stop + 16].hex(" ")))


if __name__ == "__main__":
    main()
