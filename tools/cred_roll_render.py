"""Credits RE helper (docs/re/graphics.md §Credits): render 19[700..702] as a W-wide map on 18[n] (layout guess).

    python -X utf8 tools/cred_roll_render.py W        -> work/qa/gfx/s3/roll<n>.png
"""
import sys, struct
sys.path.insert(0, 'tools')
import res, bgscreens, check_rom
from PIL import Image
d = check_rom.original()
R = {(g, i): (o, s) for g, i, o, s in res.resources(d)}
W = int(sys.argv[1])
for n in (700, 701, 702):
    (to, tsz), (mo, msz) = R[(18, n)], R[(19, n)]
    raw = d[mo + 4:mo + msz]
    cnt = len(raw) // 2
    H = cnt // W
    mp = b'B2' + bytes([W & 255, H & 255]) + raw[:2 * W * H]
    if W > 255 or H > 255:
        raise SystemExit('too big')
    w, h, rows = bgscreens.render(d[to:to + tsz], mp)
    im = Image.frombytes('RGB', (w, h), b''.join(bytes(r) for r in rows))
    im.save(f'work/qa/gfx/s3/roll{n}.png')
    print(n, cnt, W, H, d[mo:mo + 4].hex())
