"""Read-only visual-QA verdicts through `codex exec` (phase 8; Orca workers can't start reviewer subagents).

    python -X utf8 tools/qa_codex.py work/qa/chunks/chunk_*.txt [--verdicts work/qa/verdicts] [--jobs 4]
                                     [--brief docs/visual-qa-brief.md] [--prefix cx_]

Each chunk file (from `qa_gate.py todo --out-dir`) holds `id<TAB>path` lines. One codex run per chunk, sandbox
read-only, the sheets attached with -i in order, prompt = the brief + the id list. The reply's
`id<TAB>ok|issue<TAB>note` lines for ids of that chunk go to VERDICTS/<prefix><chunk>.tsv (qa_gate.py check reads
every *.tsv there). A chunk whose reply misses an id is reported and its file is not written, so a rerun retries it.
Raw replies: VERDICTS/raw/<chunk>.txt.
"""
import argparse
import concurrent.futures as cf
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_chunk(chunk, brief, vdir, prefix):
    name = os.path.splitext(os.path.basename(chunk))[0]
    out = os.path.join(vdir, prefix + name + '.tsv')
    if os.path.exists(out):
        return name, 'skip (verdict file exists)'
    items = [l.rstrip('\n').split('\t')[:2] for l in open(chunk, encoding='utf-8') if l.strip()]
    prompt = brief + '\n\n## This chunk\nThe attached images, in order, are these sheets (id: file):\n'
    prompt += ''.join('%d. %s\n' % (i + 1, sid) for i, (sid, _) in enumerate(items))
    prompt += '\nReply with exactly one verdict line per id above (id<TAB>ok|issue<TAB>note), then nothing else.\n'
    cmd = ['codex', 'exec', '--sandbox', 'read-only', '--skip-git-repo-check']
    for _, path in items:
        cmd += ['-i', os.path.join(ROOT, path)]
    cmd.append('-')
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding='utf-8', cwd=ROOT,
                       shell=(os.name == 'nt'))
    os.makedirs(os.path.join(vdir, 'raw'), exist_ok=True)
    with open(os.path.join(vdir, 'raw', name + '.txt'), 'w', encoding='utf-8') as f:
        f.write(r.stdout + '\n--- stderr ---\n' + r.stderr[-4000:])
    ids = {sid for sid, _ in items}
    got = {}
    for line in r.stdout.splitlines():
        parts = line.strip().strip('`').split('\t')
        if len(parts) >= 2 and parts[0] in ids and parts[1] in ('ok', 'issue'):
            got[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else '')
    missing = ids - set(got)
    if missing:
        return name, 'FAILED: no verdict for %d ids (rc %d): %s' % (len(missing), r.returncode, sorted(missing)[:3])
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        for sid, _ in items:
            f.write('%s\t%s\t%s\n' % (sid, got[sid][0], got[sid][1]))
    issues = ['  %s: %s' % (s, got[s][1]) for s, _ in items if got[s][0] == 'issue']
    return name, '%d ok, %d issue%s' % (len(items) - len(issues), len(issues),
                                       ('\n' + '\n'.join(issues)) if issues else '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('chunks', nargs='+')
    ap.add_argument('--verdicts', default=os.path.join('work', 'qa', 'verdicts'))
    ap.add_argument('--brief', default=os.path.join('docs', 'visual-qa-brief.md'))
    ap.add_argument('--prefix', default='cx_')
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    brief = open(os.path.join(ROOT, a.brief), encoding='utf-8').read()
    vdir = os.path.join(ROOT, a.verdicts)
    os.makedirs(vdir, exist_ok=True)
    bad = 0
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for name, msg in ex.map(lambda c: run_chunk(c, brief, vdir, a.prefix), a.chunks):
            print('%s: %s' % (name, msg), flush=True)
            bad += msg.startswith('FAILED')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
