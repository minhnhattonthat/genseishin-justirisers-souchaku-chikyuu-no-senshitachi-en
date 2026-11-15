"""pairsweep.py: find overlay maps a BG redraw may have broken (gfx/bg_pairs.tsv gaps).

    python -X utf8 tools/pairsweep.py [--span 12] [--out work/qa/pairsweep]

For every tileset 18[T] that gfx/bg.tsv redraws, draws each map 20[M] with M within --span of T (M != T, M not
already a listed user of T) with 18[T] on the original and on build/justirisers_en.gba. A map whose picture
changes is a candidate overlay the game may draw with 18[T] (the char-select arrow highlights 20[603]/20[604] were
found this way: their tiles had been recycled into letters). Writes OUT/<T>_<M>.png (original | English) per
candidate; decide from the picture and a reslog.lua run whether it is a real pair, then list it in gfx/bg_pairs.tsv.
Maps that draw with tile numbers past the original tileset are skipped (they belong to another tileset).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bgtext  # noqa: E402
import check_rom  # noqa: E402
import res  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--span", type=int, default=12)
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "pairsweep"))
    a = ap.parse_args()
    from PIL import Image
    orig = check_rom.original()
    new = (ROOT / "build" / "justirisers_en.gba").read_bytes()
    R = {(g, i): (o, s) for g, i, o, s in res.resources(orig)}
    rows = bgtext.load_rows()
    pairs = bgtext.load_pairs()
    users = {}
    for r in rows:
        users.setdefault(r["screen"][0], set()).add(r["screen"][1])
    for m, t in pairs.items():
        if t is not None:
            users.setdefault(t, set()).add(m)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    found = 0
    for t in sorted(users):
        to, tsz = R[(18, t)]
        try:
            n0 = bgtext.Tileset(orig[to:to + tsz]).n0
        except ValueError:
            continue
        for m in range(t - a.span, t + a.span + 1):
            if m == t or m in users[t] or (20, m) not in R:
                continue
            mo, msz = R[(20, m)]
            try:
                mp = bgtext.Map(orig[mo:mo + msz])
            except ValueError:
                continue
            tiles = [e & 0x3FF for e in mp.e]
            if not any(tiles) or max(tiles) > n0:
                continue
            try:
                wo, ho, po = bgtext.render_screen(orig, (t, m))
                we, he, pe = bgtext.render_screen(new, (t, m))
            except Exception:
                continue
            if po == pe:
                continue
            found += 1
            im = Image.new("RGB", (wo + we + 8, max(ho, he)))
            im.paste(Image.frombytes("RGB", (wo, ho), b"".join(po)), (0, 0))
            im.paste(Image.frombytes("RGB", (we, he), b"".join(pe)), (wo + 8, 0))
            im.save(out / f"{t}_{m}.png")
            print(f"candidate 20[{m}] on 18[{t}]: {wo}x{ho}, {sum(1 for x in tiles if x)} cells")
    print(f"{found} candidates -> {out}")


if __name__ == "__main__":
    main()
