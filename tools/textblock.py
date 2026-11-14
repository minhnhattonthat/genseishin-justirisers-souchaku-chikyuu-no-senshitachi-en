"""textblock.py: unpack and repack the script block (master table, sub-tables, messages), docs/re/text.md.

    python -X utf8 tools/textblock.py info ROM       one line per sub-table
    python -X utf8 tools/textblock.py verify ROM     pack(unpack(ROM)) == ROM[0x1E90C0:0x1FE9F0]

Layout (verified: every target lands on a message start or just after a 0x1D, and the chain is gap-free):
- Master table at 0x1E90C0: 62 u32 LE self-relative entries. Resource group 2 = master + 4 (table 0xD226AC).
  Entry 0 (0xFF) points 7 bytes into the first sub-table; entries 51-61 point at the end of the block.
- Sub-tables back to back from 0x1E91B8: u16 LE self-relative entries up to the first message, then the messages
  (each ends with 0x1F), then the next sub-table. One table (0x1E9843) has entries pointing inside a message, just
  after a 0x1D (shared tails).

Model (what unpack returns and pack takes):
  {"master": [(sub, delta) | ("end", 0)] * 62,
   "subs":   [{"entries": [(msg, off)], "msgs": [bytes]}]}
A master entry is the byte delta from the start of sub-table `sub`; a sub-table entry is message `msg` + `off`
bytes, with msg == len(msgs) for a slot pointing at the end of the table's text (0x1E9843 entries 305-383). pack lays the tables and messages out in the same order, so an unedited model gives the original bytes.
"""
import struct
import sys

MASTER, END, NMASTER = 0x1E90C0, 0x1FE9F0, 62
GROUP_PTR = 0xD226AC + 4 * 2   # resource-table word for group 2 (= master + 4, as a 0x08xxxxxx pointer)


ARGS = {0x13: 2, 0x14: 3, 0x18: 2}   # control codes with argument bytes (preprocessor 0x08007568, docs/re/text.md)


def msg_end(b, p):
    """Offset just past the 0x1F that ends the message at b[p], stepping over 2-byte glyphs (lead 0x01-0x0F) and
    control-code arguments: `13 1F 00` (sound 0x001F, sub-table 35) holds a 0x1F that is not an end code."""
    while True:
        c = b[p]
        if c == 0x1F:
            return p + 1
        p += 2 if 0 < c <= 0x0F else 1 + ARGS.get(c, 0)


def _sub(d, s, nxt):
    entries_addr, targets = s, []
    while not targets or entries_addr < min(targets):
        v = struct.unpack_from("<H", d, entries_addr)[0]
        targets.append(entries_addr + v)
        entries_addr += 2
    if min(targets) != entries_addr:
        raise ValueError("sub-table %X: first message %X is not right after the table %X"
                         % (s, min(targets), entries_addr))
    region = d[entries_addr:nxt]
    if not region.endswith(b"\x1f"):
        raise ValueError("sub-table %X: text does not end with 1F before %X" % (s, nxt))
    starts, msgs, p = [], [], 0
    while p < len(region):
        e = msg_end(region, p)
        starts.append(entries_addr + p)
        msgs.append(bytes(region[p:e]))
        p = e
    entries = []
    for t in targets:
        if t == nxt:   # unused slot pointing at the end of this table's text (0x1E9843 entries 305-383)
            entries.append((len(msgs), 0))
            continue
        if t > nxt:
            raise ValueError("sub-table %X: target %X is past its text end %X" % (s, t, nxt))
        k = max(i for i, a in enumerate(starts) if a <= t)
        off = t - starts[k]
        if off and d[t - 1] != 0x1D:
            raise ValueError("sub-table %X: target %X is mid-message, not after 1D" % (s, t))
        entries.append((k, off))
    return {"entries": entries, "msgs": msgs}


def unpack(d):
    raw = [(MASTER + 4 * i + struct.unpack_from("<I", d, MASTER + 4 * i)[0]) & 0xFFFFFFFF for i in range(NMASTER)]
    first = MASTER + 4 * NMASTER
    # sub-table starts: master targets that are not the end marker and not the odd entry 0
    starts = sorted({t for t in raw if t != END and t >= first})
    # entry 0 points inside the first table: keep only real table starts (those a chain walk reaches)
    chain, s = [], first
    while s < END:
        if s not in starts:
            raise ValueError("chain reached %X, which no master entry points at" % s)
        e, lo = s, None
        while lo is None or e < lo:   # the table runs up to its first message
            t = e + struct.unpack_from("<H", d, e)[0]
            lo = t if lo is None else min(lo, t)
            e += 2
        nxt = min([t for t in starts if t > e] + [END])
        chain.append((s, nxt))
        s = nxt
    subs = [_sub(d, s, nxt) for s, nxt in chain]
    addr = [s for s, _ in chain]
    master = []
    for t in raw:
        if t == END:
            master.append(("end", 0))
        else:
            k = max(i for i, a in enumerate(addr) if a <= t)
            master.append((k, t - addr[k]))
    return {"master": master, "subs": subs}


def pack(model, base=MASTER):
    """-> bytes of the whole block placed at ROM offset `base` (4-aligned)."""
    assert base % 4 == 0
    out = bytearray(4 * len(model["master"]))
    sub_addr = []
    for sub in model["subs"]:
        s = base + len(out)
        sub_addr.append(s)
        n = len(sub["entries"])
        msg_addr, a = [], s + 2 * n
        for m in sub["msgs"]:
            msg_addr.append(a)
            a += len(m)
        msg_addr.append(a)   # entry (len(msgs), 0) = end of this table's text
        tbl = bytearray()
        for i, (k, off) in enumerate(sub["entries"]):
            v = msg_addr[k] + off - (s + 2 * i)
            if not 0 < v < 0x10000:
                raise ValueError("sub-table at %X entry %d: offset %X does not fit a u16" % (s, i, v))
            tbl += struct.pack("<H", v)
        out += tbl
        for m in sub["msgs"]:
            if not m.endswith(b"\x1f"):
                raise ValueError("message without its 1F end code: %r" % m[:16])
            out += m
    end = base + len(out)
    for i, (k, delta) in enumerate(model["master"]):
        t = end if k == "end" else sub_addr[k] + delta
        struct.pack_into("<I", out, 4 * i, (t - (base + 4 * i)) & 0xFFFFFFFF)
    return bytes(out)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("info", "verify"):
        print(__doc__)
        return 2
    d = open(sys.argv[2], "rb").read()
    m = unpack(d)
    if sys.argv[1] == "info":
        a = MASTER + 4 * NMASTER
        for i, s in enumerate(m["subs"]):
            size = 2 * len(s["entries"]) + sum(map(len, s["msgs"]))
            tails = sum(1 for _, off in s["entries"] if off)
            print(f"{i:2d}\t{a:06X}\t{len(s['entries'])} entries\t{len(s['msgs'])} msgs\t{size} bytes"
                  + (f"\t{tails} shared tails" if tails else ""))
            a += size
        print(f"master: {m['master']}")
        print(f"{sum(len(s['msgs']) for s in m['subs'])} messages, end {a:06X}")
        return 0
    blob = pack(m)
    ok = blob == d[MASTER:END]
    print("identical" if ok else "DIFFERENT (%d vs %d bytes)" % (len(blob), END - MASTER))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
