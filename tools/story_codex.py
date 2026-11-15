"""Phase 9 story pass through read-only `codex exec` (Orca workers can't start reviewer subagents).

    python -X utf8 tools/story_codex.py work/qa/story/chapters/02_stage1.txt [...] [--jobs 2] [--prefix a_]

One codex run per chapter file with docs/story-reviewer-brief.md; the report goes to
work/qa/story/reports/<prefix><chapter>.md. A report that already exists is skipped. The controller reads each report,
writes `chapter<TAB>ok|issue<TAB>note` into work/qa/story/verdicts/ and moves Minors to docs/polish.md.
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "work/qa/story/reports"


def run(chapter, prefix):
    out = REPORTS / f"{prefix}{chapter.stem}.md"
    if out.exists():
        return f"{out.name}: exists, skipped"
    rel = chapter.resolve().relative_to(ROOT).as_posix()
    prompt = (
        (ROOT / "docs/story-reviewer-brief.md").read_text(encoding="utf-8")
        + f"\n\n## Dispatch\nChapter file: `{rel}`. Also read `docs/synopsis.md`, `docs/style-reference.md`, "
        "`glossary.md`. Do not modify any file. Your final message is the report.\n"
    )
    cmd = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", "-o", str(out), "-"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
                       shell=sys.platform == "win32")
    if r.returncode or not out.exists():
        return f"{out.name}: FAILED rc={r.returncode} {r.stderr[-400:]}"
    return f"{out.name}: done"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="+", type=Path)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--prefix", default="a_")
    a = ap.parse_args()
    REPORTS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        for msg in ex.map(lambda c: run(c, a.prefix), a.chapters):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
