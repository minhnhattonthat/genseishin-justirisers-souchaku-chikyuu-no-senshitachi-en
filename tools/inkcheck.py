"""Run the skill's inkbox.py over every centred box in gfx/inkbox.tsv (phase 8 done-when).

    python -X utf8 tools/inkcheck.py [--tour work/qa/final/tour] [--tsv gfx/inkbox.tsv]

Each row: id, scene, frame, rects (x,y,w,h;..), extra inkbox args or '-', note. Shots come from a warp tour
directory (DIR/<scene>/<frame>.png). Prints inkbox's margins per row; exit 1 if any row is off-centre or a shot is
missing.
"""
import argparse
import csv
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tour', default='work/qa/final/tour')
    ap.add_argument('--tsv', default='gfx/inkbox.tsv')
    a = ap.parse_args()
    skill = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'skill.py')], capture_output=True,
                           text=True, check=True).stdout.strip()
    inkbox = os.path.join(skill, 'scripts', 'inkbox.py')
    bad = 0
    with open(os.path.join(ROOT, a.tsv), encoding='utf-8') as f:
        rows = [r for r in csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE) if r and not r[0].startswith('#')]
    for rid, scene, frame, rects, extra, note in rows:
        png = os.path.join(ROOT, a.tour, scene, frame + '.png')
        if not os.path.exists(png):
            print('MISSING', rid, png)
            bad += 1
            continue
        cmd = [sys.executable, '-X', 'utf8', inkbox, png] + rects.split(';') + ([] if extra == '-' else extra.split())
        r = subprocess.run(cmd, capture_output=True, text=True)
        print('%-4s %s (%s): %s' % ('ok' if r.returncode == 0 else 'FAIL', rid, note,
                                    ' | '.join(r.stdout.split('\n')).strip(' |')))
        bad += r.returncode != 0
    print('%d rows, %d failing' % (len(rows), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
