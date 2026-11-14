"""Text coverage per sub-table: which ids a set of warp/tour runs read, grouped by script file.

    python -X utf8 tools/cover_tables.py LOGDIR [LOGDIR ..] [--strings build/strings.tsv] [--by-scene] [--missing sNN]

Reads every LOGDIR/**/log.txt (`TEXT <hex addr>` lines from `$SKILL/scripts/lua/probes/textcover.lua`) and maps
the first-byte address of each string in build/strings.tsv to its id and sub-table (script/sNN_*.tsv).
Prints `sNN shown/total` per sub-table; --by-scene lists which scene dirs touched each sub-table; --missing sNN
lists that table's unread ids with their Japanese text.
"""
import argparse
import collections
import csv
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASK = 0x1FFFFFF


def tables():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'script', 's*.tsv'))):
        name = os.path.basename(path)[:3]
        with open(path, encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                out[row['id']] = (name, row.get('jp', ''))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('logdirs', nargs='+')
    ap.add_argument('--strings', default=os.path.join(ROOT, 'build', 'strings.tsv'))
    ap.add_argument('--by-scene', action='store_true')
    ap.add_argument('--missing')
    a = ap.parse_args()
    addr2id = {}
    with open(a.strings, encoding='utf-8') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 2:
                addr2id[int(p[1], 16) & MASK] = p[0]
    tab = tables()
    shown, scenes = set(), collections.defaultdict(set)
    for d in a.logdirs:
        for log in glob.glob(os.path.join(d, '**', 'log.txt'), recursive=True):
            scene = os.path.basename(os.path.dirname(log))
            with open(log, encoding='utf-8', errors='replace') as f:
                for m in re.finditer(r'^TEXT ([0-9A-Fa-f]+)', f.read(), re.M):
                    i = addr2id.get(int(m.group(1), 16) & MASK)
                    if i:
                        shown.add(i)
                        scenes[tab[i][0]].add(scene)
    total = collections.Counter(t for t, _ in tab.values())
    got = collections.Counter(tab[i][0] for i in shown)
    for t in sorted(total):
        line = '%s %3d/%3d' % (t, got[t], total[t])
        if a.by_scene:
            line += '  ' + ' '.join(sorted(scenes[t]))
        print(line)
    print('all %d/%d' % (len(shown), len(tab)))
    if a.missing:
        for i, (t, jp) in sorted(tab.items()):
            if t == a.missing and i not in shown:
                print(i, jp[:60])


if __name__ == '__main__':
    main()
