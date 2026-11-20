"""Show every not-yet-covered script message in the real dialogue window (text coverage + visual QA, phase 8).

    python -X utf8 tools/msgview_run.py COVERDIR [--tables s08,s22] [--chunk 30] [--jobs 4] [--dry]

COVERDIR holds earlier warp/tour runs with textcover.lua logs (each in its own subdir). For each sub-table in
--tables (default: s07 on; s01/s03 by name; nontext/debug/placeholder rows skipped), the messages none of those runs read are cut
into chunks of --chunk, and each chunk becomes one cold-boot run COVERDIR/msgview/<table>_<n>/: warp to stage_1_1,
press A every 40 frames (warp.lua ADVANCE) and let tools/lua/msgview.lua swap the n-th event text command for the
n-th message of the chunk (stage 1-1's intro has 32 commands), with textcover.lua logging the reads and a shot
every 20 frames. The table index the game uses is master entry - 1 (docs/re/text.md §Pointers).
The window is the stage-start dialogue box, so this proves the text fits that box and that the game's own
renderer reads it; it does not prove the scene that normally shows it is reachable (see docs/text_unshown.tsv).
"""
import argparse
import concurrent.futures as cf
import csv
import glob
import os
import re
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from skill import SKILL  # noqa: E402
import check_rom  # noqa: E402

MASTER, ENTRIES, MASK, PER_RUN = 0x1E90C0, 62, 0x1FFFFFF, 32
RANGES = '8D23570-8D3BA00'


def table_index():
    """sNN -> the game's table index (first master entry pointing at the sub-table, minus 1)."""
    d = check_rom.original()
    starts = {int(os.path.basename(p)[4:10], 16): os.path.basename(p)[:3] for p in glob.glob(os.path.join(ROOT, 'script', 's*.tsv'))}
    out = {}
    for e in range(1, ENTRIES):
        a = MASTER + 4 * e
        t = a + struct.unpack_from('<i', d, a)[0]
        if t in starts and starts[t] not in out:
            out[starts[t]] = e - 1
    return out


def messages(name):
    path = glob.glob(os.path.join(ROOT, 'script', name + '_*.tsv'))[0]
    with open(path, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            slots = re.findall(r'\d+', row['slots'])  # "5", "5-7", "3,9": the first slot is enough
            if re.match(r'(nontext|debug|placeholder):', row.get('notes') or ''):
                continue  # waived in docs/text_unshown.tsv, never drawn in play
            if slots:
                yield row['id'], int(slots[0])


def shown(coverdir):
    addr2id = {}
    with open(os.path.join(ROOT, 'build', 'strings.tsv'), encoding='utf-8') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) >= 2:
                addr2id[int(p[1], 16) & MASK] = p[0]
    out = set()
    for log in glob.glob(os.path.join(coverdir, '**', 'log.txt'), recursive=True):
        with open(log, encoding='utf-8', errors='replace') as f:
            for m in re.finditer(r'^TEXT ([0-9A-Fa-f]+)', f.read(), re.M):
                i = addr2id.get(int(m.group(1), 16) & MASK)
                if i:
                    out.add(i)
    return out


def run(name, pairs, a):
    out = os.path.join(a.coverdir, 'msgview', name)
    frames = 2800 + 220 * len(pairs)  # the intro's first command runs ~f2235; long narration pages need more
    cmd = [sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts', 'emu.py'), a.rom, '--out', out,
           '--frames', str(frames), '--shot-every', '20', '--timeout', '900',
           '--script', os.path.join(ROOT, 'tools', 'debug', 'warp.lua'), '--var', "SCENE='stage_1_1'",
           '--var', 'ADVANCE=40', '--var', 'GOD=1',
           # emu.py runs a copy of warp.lua from the output dir, so its relative default scenes path misses
           '--var', 'SCENES=[[%s]]' % os.path.join(ROOT, 'tools', 'debug', 'scenes.gba.txt').replace('\\', '/'),
           '--script', os.path.join(ROOT, 'tools', 'lua', 'msgview.lua'),
           '--var', "MSGS='%s'" % ','.join('%d:%d' % p for _, p in pairs),
           '--script', os.path.join(SKILL, 'scripts', 'lua', 'probes', 'textcover.lua'), '--var', "RANGES='%s'" % RANGES]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    log = ''
    try:
        with open(os.path.join(out, 'log.txt'), encoding='utf-8', errors='replace') as f:
            log = f.read()
    except OSError:
        pass
    done = 'MSGVIEW done' in log
    return name, r.returncode == 0 and done, '' if done else 'list not finished (exit %d)' % r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('coverdir')
    ap.add_argument('--tables')
    ap.add_argument('--chunk', type=int, default=30)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--rom', default=os.path.join(ROOT, 'build', 'justirisers_en.gba'))
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    assert a.chunk <= PER_RUN, 'stage 1-1 has %d text commands' % PER_RUN
    idx = table_index()
    names = a.tables.split(',') if a.tables else sorted(n for n in idx if n > 's06')
    seen = shown(a.coverdir)
    jobs = []
    for n in names:
        miss = [(i, (idx[n], s)) for i, s in messages(n) if i not in seen]
        for k in range(0, len(miss), a.chunk):
            jobs.append(('%s_%s' % (n, miss[k][0]), miss[k:k + a.chunk]))  # first id: reruns never overwrite
    print('%d runs, %d messages' % (len(jobs), sum(len(p) for _, p in jobs)))
    if a.dry:
        for name, pairs in jobs:
            print(name, ' '.join(i for i, _ in pairs))
        return
    fails = 0
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for name, ok, note in ex.map(lambda j: run(j[0], j[1], a), jobs):
            print('%s %s %s' % ('ok  ' if ok else 'FAIL', name, note), flush=True)
            fails += not ok
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
