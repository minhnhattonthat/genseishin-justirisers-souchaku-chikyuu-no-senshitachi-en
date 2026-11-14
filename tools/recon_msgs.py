"""recon_msgs.py: list every message reached from the master table and profile control bytes (recon, phase 1).

    python -X utf8 tools/recon_msgs.py ROM [--lead 01-0B] [--args 13=1,14=3,18=2]

Master table: ROM 0x1E90C0, 62 u32 LE self-relative entries -> sub-tables of u16 LE self-relative entries ->
messages ending in 0x1F (see docs/re/text.md). Prints a histogram of control bytes in token position, with the
most common following bytes, under the given lead-byte range and argument counts.
"""
import argparse
import collections
import struct

MASTER, MASTER_N = 0x1E90C0, 62


def subtables(d):
    ts = [MASTER + 4 * i + struct.unpack_from("<I", d, MASTER + 4 * i)[0] for i in range(MASTER_N)]
    return ts


def table_targets(d, s):
    b, tg = s, []
    while not tg or b < min(tg):
        tg.append(b + struct.unpack_from("<H", d, b)[0])
        b += 2
    return tg, b


def messages(d):
    ts = sorted(set(subtables(d)))
    out = set()
    for t in ts[:-1]:
        if t == 0x1E91BF:  # master entry 0 points 7 bytes into the first sub-table (see docs/re/text.md)
            continue
        tg, _ = table_targets(d, t)
        out.update(tg)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("--lead", default="01-0B")
    ap.add_argument("--args", default="")
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    llo, lhi = (int(x, 16) for x in a.lead.split("-"))
    nargs = {int(k, 16): int(v) for k, v in (p.split("=") for p in a.args.split(",") if p)}
    c = collections.Counter()
    ctx = collections.defaultdict(collections.Counter)
    lead = collections.Counter()
    ms = messages(d)
    for m in ms:
        p = m
        while d[p] != 0x1F:
            x = d[p]
            if llo <= x <= lhi:
                lead[x] += 1
                p += 2
                continue
            if x < 0x20:
                c[x] += 1
                ctx[x][d[p + 1:p + 4].hex(" ")] += 1
                p += 1 + nargs.get(x, 0)
                continue
            p += 1
    print("messages", len(ms))
    print("lead bytes", {"%02X" % k: v for k, v in sorted(lead.items())})
    for k in sorted(c):
        print("%02X %5d  %s" % (k, c[k], ctx[k].most_common(5)))


if __name__ == "__main__":
    main()
