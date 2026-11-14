"""merge_en.py: merge translation batch files (id<TAB>en per line, '#' comments) into the `en` column of script/*.tsv.

    python -X utf8 tools/merge_en.py work/tr/b01.tsv [...] [--dry]

Refuses the whole merge when an id is unknown, duplicated, or the merged rows fail tools/textlint.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import script  # noqa: E402
import textlint  # noqa: E402


def read_batch(path):
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        mid, sep, en = line.partition("\t")
        if not sep:
            raise SystemExit(f"{path}:{n}: no tab")
        mid = mid.strip().upper()
        if mid in out:
            raise SystemExit(f"{path}:{n}: {mid} twice")
        out[mid] = en.rstrip("\r")
    return out


def main(argv):
    dry = "--dry" in argv
    new = {}
    for p in [a for a in argv if not a.startswith("--")]:
        for k, v in read_batch(p).items():
            if k in new:
                raise SystemExit(f"{k} in two batch files")
            new[k] = v
    lint = textlint.Lint()
    files = sorted((ROOT / "script").glob("s*.tsv"))
    seen, errs, staged = set(), [], []
    for f in files:
        rows = script.read_tsv(f)
        changed = False
        for r in rows:
            if r["id"] in new:
                seen.add(r["id"])
                r["en"] = new[r["id"]]
                changed = True
                errs += lint.check(int(f.name[1:3]), r)
        if changed:
            staged.append((f, rows))
    unknown = set(new) - seen
    if unknown:
        raise SystemExit(f"unknown ids: {sorted(unknown)}")
    for e in errs:
        print(e)
    if errs:
        print(f"{len(errs)} errors: nothing merged")
        return 1
    if not dry:
        for f, rows in staged:
            script.write_tsv(f, rows)
    print(f"{len(new)} rows {'checked' if dry else 'merged'} into {len(staged)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
