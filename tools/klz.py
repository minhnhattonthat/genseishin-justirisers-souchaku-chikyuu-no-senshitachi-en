"""klz.py: the game's flag-bit LZ (decompressor 0x08001CD4), in Python, with a compressor.

    python -X utf8 tools/klz.py test ROM        decompress every group 4/9 block, recompress, check both ways

Format (read off the disassembly of 0x08001CD4, docs/re/graphics.md §Compression):
- Flag bits are read MSB first from flag bytes. A flag byte is fetched from the stream at the moment a bit is needed
  and the previous one is used up, so flag bytes sit between the data bytes.
- bit 1: literal byte.
- bits 0 0 a b, byte o: copy 2 + (a*2 + b) bytes (2..5) from dst - 256 + o.
- bits 0 1, u16 big-endian v: offset = (v >> 3) - 8192 (-8192..-1); n = v & 7:
  n != 0: copy n + 2 bytes (3..9); n == 0: byte c; c == 0 ends the stream, else copy c + 1 bytes (2..256).
- When a flag byte fetched for a type bit is 0xFF the game copies 8 literals at once: the same result as decoding
  it bit by bit, so the compressor needs no special case.
"""
import sys


def decompress(src, off=0):
    """-> (data, consumed bytes)."""
    out = bytearray()
    p = off
    flags, nbits = 0, 0

    def bit():
        nonlocal flags, nbits, p
        if nbits == 0:
            flags, nbits = src[p], 8
            p += 1
        nbits -= 1
        return (flags >> nbits) & 1

    while True:
        if bit():
            out.append(src[p])
            p += 1
            continue
        if bit() == 0:
            n = 2 + bit() * 2
            n += bit()
            dist = 256 - src[p]
            p += 1
        else:
            v = src[p] << 8 | src[p + 1]
            p += 2
            dist = 8192 - (v >> 3)
            n = v & 7
            if n:
                n += 2
            else:
                c = src[p]
                p += 1
                if c == 0:
                    return bytes(out), p - off
                n = c + 1
        s = len(out) - dist
        if s < 0:
            raise ValueError("back-reference before the start at out %d" % len(out))
        for i in range(n):
            out.append(out[s + i])


class _Writer:
    def __init__(self):
        self.out = bytearray()
        self.fpos, self.nbits = 0, 8

    def bit(self, b):
        if self.nbits == 8:
            self.fpos = len(self.out)
            self.out.append(0)
            self.nbits = 0
        if b:
            self.out[self.fpos] |= 0x80 >> self.nbits
        self.nbits += 1


def _cost(dist, n):
    """Bits for a match, or None when the form can't encode it."""
    if 2 <= n <= 5 and dist <= 256:
        return 4 + 8
    if 3 <= n <= 9:
        return 2 + 16
    if 2 <= n <= 256:
        return 2 + 24
    return None


def compress(data, max_chain=256):
    """Optimal parse (shortest bit count) over hash-chain match candidates."""
    data = bytes(data)
    size = len(data)
    # candidate matches per position: list of (length, dist) with the longest length for each dist band
    head, prev = {}, [-1] * size
    best = [None] * size
    for i in range(size):
        cands = []
        if i + 2 <= size:
            key = data[i:i + 3] if i + 3 <= size else None
            # 2-byte matches only matter for the short form (dist <= 256)
            j = i - 1
            lim = max(0, i - 256)
            got2 = False
            while j >= lim and not got2:
                if data[j] == data[i] and data[j + 1] == data[i + 1]:
                    cands.append((2, i - j))
                    got2 = True
                j -= 1
            if key is not None:
                j = head.get(key, -1)
                chain = 0
                bestlen = 2
                while j >= 0 and i - j <= 8192 and chain < max_chain:
                    k = 3
                    while i + k < size and k < 256 and data[j + k] == data[i + k]:
                        k += 1
                    if k > bestlen or (i - j <= 256 and k <= 5):
                        cands.append((k, i - j))
                        bestlen = max(bestlen, k)
                    if k == 256:
                        break
                    j = prev[j]
                    chain += 1
        best[i] = cands
        if i + 3 <= size:
            key = data[i:i + 3]
            prev[i] = head.get(key, -1)
            head[key] = i
    INF = float("inf")
    cost = [INF] * (size + 1)
    choice = [None] * (size + 1)
    cost[size] = 0
    for i in range(size - 1, -1, -1):
        c = 9 + cost[i + 1]
        ch = None
        for length, dist in best[i]:
            # any shorter length from the same dist is also valid; try the cheap breakpoints
            for n in {length, min(length, 5), min(length, 9), 2, 3}:
                if n < 2 or n > length:
                    continue
                bc = _cost(dist, n)
                if bc is None:
                    continue
                t = bc + cost[i + n]
                if t < c:
                    c, ch = t, (n, dist)
        cost[i], choice[i] = c, ch
    w = _Writer()
    i = 0
    while i < size:
        ch = choice[i]
        if ch is None:
            w.bit(1)
            w.out.append(data[i])
            i += 1
            continue
        n, dist = ch
        w.bit(0)
        if n <= 5 and dist <= 256:
            w.bit(0)
            w.bit((n - 2) >> 1)
            w.bit((n - 2) & 1)
            w.out.append(256 - dist)
        else:
            w.bit(1)
            v = (8192 - dist) << 3
            if 3 <= n <= 9:
                v |= n - 2
                w.out += bytes([v >> 8, v & 0xFF])
            else:
                w.out += bytes([v >> 8, v & 0xFF, n - 1])
        i += n
    w.bit(0)
    w.bit(1)
    w.out += b"\x00\x00\x00"
    return bytes(w.out)


def lz_blocks(d):
    """[(group, index, offset, size)] of the LZ blocks in groups 4 and 9 (unique offsets)."""
    from res import resources
    seen, out = set(), []
    for g, i, o, size in resources(d):
        if g not in (4, 9) or o in seen:
            continue
        seen.add(o)
        try:
            data, used = decompress(d, o)
        except (ValueError, IndexError):
            continue
        if abs(used - size) <= 16 and len(data) > size:
            out.append((g, i, o, used))
    return out


def main():
    if len(sys.argv) != 3 or sys.argv[1] != "test":
        print(__doc__)
        return 2
    d = open(sys.argv[2], "rb").read()
    bad = 0
    tot_o = tot_n = 0
    for g, i, o, used in lz_blocks(d):
        data, _ = decompress(d, o)
        c = compress(data)
        back, _ = decompress(c)
        ok = back == data
        bad += not ok
        tot_o += used
        tot_n += len(c)
        print(f"{g}.{i:04d} {o:07X} orig {used} new {len(c)} {'ok' if ok else 'MISMATCH'}")
    print(f"total orig {tot_o} new {tot_n}; {bad} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
