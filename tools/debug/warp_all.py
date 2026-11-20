"""Warp to every scene in tools/debug/scenes.gba.txt (or the names given) from a cold boot, in parallel.

    python -X utf8 tools/debug/warp_all.py [NAME|PREFIX* ..] [--rom build/justirisers_en.gba] [--out work/qa/warp]
                                           [--frames 900] [--jobs 3] [--states] [--every 60]
                                           [--var NAME=LUA].. [--script probe.lua]..

Each scene gets DIR/<name>/ with shots every --every frames, final.png and log.txt; --states also saves
work/states/<name>.mss at the end of the run (regenerate them all after code, font or graphics changes).
A run passes when its log has the WARP line and the scene byte reached the entry's scene after it; the summary
lists FAIL lines and the exit code is 1 if any failed. Frames per scene: the entry's own column 7 if set.
"""
import argparse
import concurrent.futures as cf
import fnmatch
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from skill import SKILL  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIST = os.path.join(ROOT, 'tools', 'debug', 'scenes.gba.txt')


def read_scenes(path=LIST):
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            col = line.split('\t')
            out.append({'name': col[0], 'scene': int(col[1]), 'sub': int(col[2]),
                        'frames': int(col[6]) if len(col) > 6 and col[6].strip() else None})
    return out


def run(entry, a):
    out = os.path.join(a.out, entry['name'])
    frames = (entry['frames'] or a.frames) + a.extra_frames
    cmd = [sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts', 'emu.py'), a.rom, '--out', out,
           '--frames', str(frames), '--shot-every', str(a.every),
           '--script', os.path.join(ROOT, 'tools', 'debug', 'warp.lua'),
           '--var', "SCENE='%s'" % entry['name'], '--timeout', '900',
           # emu.py runs a copy of the script from the output dir, so warp.lua's relative default path misses
           '--var', 'SCENES=[[%s]]' % LIST.replace('\\', '/')]
    if a.states:
        cmd += ['--state-out', os.path.join(ROOT, 'work', 'states', entry['name'] + '.mss')]
    for v in a.var or []:
        cmd += ['--var', v]
    for s in a.script or []:
        cmd += ['--script', s]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    log = ''
    try:
        with open(os.path.join(out, 'log.txt'), encoding='utf-8', errors='replace') as f:
            log = f.read()
    except OSError:
        pass
    m = re.search(r'^WARP \S+ f(\d+)', log, re.M)
    ok = r.returncode == 0 and m is not None
    note = 'no WARP line' if m is None else ''
    if m:
        after = [int(x) for f, x in re.findall(r'^SCENE f(\d+) scene=(\d+)', log, re.M) if int(f) >= int(m.group(1))]
        if entry['scene'] not in after:
            ok, note = False, 'scene %d never reached' % entry['scene']
    if r.returncode:
        note = (note + ' exit %d ' % r.returncode + r.stdout[-300:] + r.stderr[-300:]).strip()
    return entry['name'], ok, note


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('names', nargs='*')
    ap.add_argument('--rom', default=os.path.join(ROOT, 'build', 'justirisers_en.gba'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'work', 'qa', 'warp'))
    ap.add_argument('--frames', type=int, default=900)
    ap.add_argument('--extra-frames', type=int, default=0, help='added to every entry\'s frame budget')
    ap.add_argument('--every', type=int, default=60)
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--states', action='store_true')
    ap.add_argument('--var', action='append', help='extra --var passed to emu.py (e.g. GOD=1)')
    ap.add_argument('--script', action='append', help='extra Lua probe passed to emu.py (e.g. tools/lua/romtrap.lua)')
    a = ap.parse_args()
    if not os.path.exists(a.rom):
        sys.exit('no ROM at %s (build first, or pass --rom work/orig.gba)' % a.rom)
    scenes = read_scenes()
    if a.names:
        scenes = [s for s in scenes if any(fnmatch.fnmatch(s['name'], n) for n in a.names)]
    if not scenes:
        sys.exit('no scene matches %s' % a.names)
    fails = 0
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for name, ok, note in ex.map(lambda e: run(e, a), scenes):
            print('%s %s %s' % ('ok  ' if ok else 'FAIL', name, note), flush=True)
            fails += not ok
    print('%d/%d ok' % (len(scenes) - fails, len(scenes)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
