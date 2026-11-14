"""Credits RE helper (docs/re/graphics.md §Credits): match BG0 screen rows of a credits VRAM dump
(work/qa/credvram/ppu.vram.bin, screen block 0x1000) against 19[700..702] rows read 30 wide.

    python -X utf8 tools/cred_vram_match.py
"""
import sys, struct
from collections import Counter
sys.path.insert(0, 'tools')
import res, check_rom
d = check_rom.original()
R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
v = open('work/qa/credvram/ppu.vram.bin', 'rb').read()
m = struct.unpack_from('<1024H', v, 0x1000)
print('screen value histogram', Counter(m).most_common(4))
rolls = {n: struct.unpack_from('<2700H', d, R[(19, n)][0] + 4) for n in (700, 701, 702)}
# screen row r (32 wide), compare first 30 columns against every roll row with any base offset
for r in range(32):
    row = [x & 0x3ff for x in m[r * 32:r * 32 + 30]]
    if len(set(row)) <= 2:
        continue
    found = []
    for n, roll in rolls.items():
        for rr in range(90):
            rw = roll[rr * 30:rr * 30 + 30]
            diffs = Counter(a - b for a, b in zip(row, rw) if b > 1)
            if diffs and diffs.most_common(1)[0][1] >= sum(1 for b in rw if b > 1) - 1 and sum(1 for b in rw if b > 1) > 2:
                found.append((n, rr, diffs.most_common(1)[0][0]))
    print('screen row', r, 'pal', set(x >> 12 for x in m[r * 32:r * 32 + 30]), found[:3])
