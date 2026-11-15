"""Zoomed English | Japanese shots of every graphics-text row, from cold-boot warp runs (phase 8 done-when).

    python -X utf8 tools/gfxshots.py [--tour work/qa/final/tour] [--jp work/qa/final/tour_jp]
                                     [--out work/qa/final/gfx] [--shots gfx/shots.tsv]

gfx/shots.tsv: id, scene, frame (f001560 or final), crop x,y,w,h (or -), zoom, rows (which gfx/*.tsv rows the
shot proves), expect (the English the shot must show). Each id gives OUT/<id>.png = the English frame beside the
original ROM's same frame (when the jp tour has it), cropped and zoomed with the skill's sheet.py. Also writes
OUT/brief.md = docs/visual-qa-brief.md + the expected text per id, for tools/qa_codex.py --brief, and checks
that every screen/sprite/roll of gfx/bg.tsv, gfx/obj.tsv and gfx/credits.tsv is named in some shot's rows
column (exit 1 if one is not, or a frame is missing). A row with scene `-` marks keys no warp reaches (expect
says why and how they were checked instead).
"""
import argparse
import csv
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))


def skill_dir():
    return subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'skill.py')], capture_output=True,
                          text=True, check=True).stdout.strip()


def rows(path):
    with open(path, encoding='utf-8') as f:
        return [r for r in csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE) if r and not r[0].startswith('#')]


def gfx_keys():
    """Every screen (bg), sprite[frame]/bg5/pic5 key (obj) and roll (credits) that has lettering rows."""
    keys = set()
    for r in rows(os.path.join(ROOT, 'gfx', 'bg.tsv')):
        keys.add('bg:' + r[0])
    for r in rows(os.path.join(ROOT, 'gfx', 'obj.tsv')):
        keys.add('obj:' + r[0] if ':' in r[0] else 'obj:%s[%s]' % (r[0], r[1]))
    for r in rows(os.path.join(ROOT, 'gfx', 'credits.tsv')):
        keys.add('cred:' + r[0])
    return keys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tour', default='work/qa/final/tour')
    ap.add_argument('--jp', default='work/qa/final/tour_jp')
    ap.add_argument('--out', default='work/qa/final/gfx')
    ap.add_argument('--shots', default='gfx/shots.tsv')
    a = ap.parse_args()
    sheet = os.path.join(skill_dir(), 'scripts', 'sheet.py')
    os.makedirs(os.path.join(ROOT, a.out), exist_ok=True)
    shots = rows(os.path.join(ROOT, a.shots))
    covered, bad, brief = set(), 0, []
    for sid, scene, frame, crop, zoom, keys, expect in shots:
        covered.update(k.strip() for k in keys.split(','))
        if scene == '-':  # no warp shows it; expect says why and how it was checked instead
            print('UNREACHED', sid, keys, '-', expect)
            continue
        en = os.path.join(ROOT, a.tour, scene, frame + '.png')
        jp = os.path.join(ROOT, a.jp, scene, frame + '.png')
        if not os.path.exists(en):
            print('MISSING', sid, en)
            bad += 1
            continue
        cmd = [sys.executable, '-X', 'utf8', sheet, en, '--zoom', zoom, '--out',
               os.path.join(ROOT, a.out, sid + '.png')]
        if crop != '-':
            cmd += ['--crop', crop]
        if os.path.exists(jp):
            cmd += ['--compare', jp]
        subprocess.run(cmd, check=True, capture_output=True)
        brief.append('- `gfx/%s` (%s %s): %s' % (sid, scene, frame, expect))
    missing = sorted(gfx_keys() - covered)
    for k in missing:
        print('NO SHOT for', k)
    with open(os.path.join(ROOT, 'docs', 'visual-qa-brief.md'), encoding='utf-8') as f:
        text = f.read()
    text += ('\n## Graphics-row shots (ids starting `gfx/`)\n'
             'Each image is one zoomed frame: the English build on the left, the original ROM at the same frame on '
             'the right when there is one (a missing right half = no original run for that warp). Judge the left '
             'half: the listed English must be there, legible, inside its frame or button, with no Japanese left '
             'in that lettering and no stray pixels or garbage tiles around it. The right half only shows where '
             'the Japanese was.\n' + '\n'.join(brief) + '\n')
    with open(os.path.join(ROOT, a.out, 'brief.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    print('%d shots in %s, %d gfx keys, %d without a shot, %d missing frames' % (
        len(shots) - bad, a.out, len(gfx_keys()), len(missing), bad))
    return 1 if missing or bad else 0


if __name__ == '__main__':
    sys.exit(main())
