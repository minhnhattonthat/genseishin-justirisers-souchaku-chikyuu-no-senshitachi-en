"""textlint.py: the translation gate (phase 6 batch check, phase 7 lint). Checks every script row with English.

    python -X utf8 tools/textlint.py [IDS_OR_FILES...]   exit 1 on any error; no args = whole script
    python -X utf8 tools/textlint.py --fit "TEXT" [--box dialogue]   width of each line of a dry-run text

Rules (budgets: tbl/windows.json, per-id geometry: tbl/windows_ids.tsv, docs/re/text.md §Windows):
- control codes ({se:..}, {style:..}, {msg:..}, {var}, {tail}...) are the same multiset as in the Japanese;
  {n}/{p} may differ (English breaks its own lines), spacer cells ({padNN}, {spN}) and `{fill}` are free;
- every character encodes (tools/insert.py en_table), ASCII only, no tabs;
- story sub-tables s07-s39 and ids logged as dialogue: line 1 = speaker tag (small font, 64 px, must be the
  glossary form of the Japanese tag), then at most 2 lines per page, 224 px each, a page's last line 216 px;
- other logged windows: px/lines of their variant; `column` rows (notes) and never-drawn rows: each line at most
  the Japanese line's width (column rows: `{fill}` pads the line back to that width at build time);
- glossary: a Characters/Places/Items row whose JP appears in the Japanese (as a whole kana/kanji run) must have
  its EN in the English; no spelling from a row's Avoid column (whole word, any case) may appear in the English;
- honorifics: a '## Honorifics' row (直也さん | Naoya-san) whose JP appears must have its EN form;
- no ordinal suffix glued onto {var}.
Waivers: tbl/lint_waive.tsv (id<TAB>rule<TAB>reason) for known engine work (phase 7).
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import font  # noqa: E402
import insert  # noqa: E402
import script  # noqa: E402

TOKEN = re.compile(r"\{[^}]*\}")
FREE_TOKENS = re.compile(r"^\{(n|p|pad\d+|sp\d+|fill)\}$")
STORY = range(7, 40)


def load_windows():
    data = json.loads((ROOT / "tbl" / "windows.json").read_text(encoding="utf-8"))
    by_id = {}
    with open(ROOT / "tbl" / "windows_ids.tsv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            for name, v in data["variants"].items():
                if all(str(r[k]) == str(val) for k, val in v["match"].items()):
                    by_id.setdefault(r["id"], set()).add(name)
    for name, ids in data.get("assigned", {}).items():
        if not name.startswith("_"):
            for mid in ids:
                by_id.setdefault(mid, set()).add(name)
    return data["variants"], by_id


def kind(char):
    if "぀" <= char <= "ゟ":
        return "hiragana"
    if "゠" <= char <= "ヿ":
        return "katakana"
    if "一" <= char <= "鿿" or char == "々":
        return "kanji"
    return "other"


def has_term(jp, term, honorific=False):
    """term occurs as a whole kana/kanji run (ユカ isn't in ユカイ, ゾラ isn't in ソゾラ). An honorific row
    (直也さん) checks only its start: a particle may follow (直也さんは)."""
    for m in re.finditer(re.escape(term), jp):
        a, b = m.start(), m.end()
        if (a == 0 or kind(jp[a - 1]) != kind(term[0])) and \
                (honorific or b == len(jp) or kind(jp[b]) != kind(term[-1])):
            return True
    return False


def load_glossary():
    """-> [(jp, en, avoid, honorific)] from the glossary tables (JP | EN | max | notes | Avoid). avoid: the Avoid
    cell split on ',' or '/'; honorific: the row sits under the '## Honorifics' heading."""
    out, section = [], ""
    for line in (ROOT / "glossary.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 2 and cells[0] not in ("JP", "") and not set(cells[0]) <= set("-"):
            avoid = [x.strip() for x in re.split(r"[,/]", cells[4]) if x.strip()] if len(cells) > 4 else []
            out.append((cells[0], cells[1], avoid, section.startswith("honorific")))
    return out


def load_waivers():
    p = ROOT / "tbl" / "lint_waive.tsv"
    out = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                mid, rule = line.split("\t")[:2]
                out.add((mid, rule))
    return out


class Lint:
    def __init__(self):
        fonts = font.load_all()
        self.et = insert.en_table(fonts["normal"])
        self.jt = script.table()
        orig = (ROOT / "work" / "orig.gba").read_bytes()
        rom = bytearray(orig)
        font.apply(rom, fonts)
        self.wt_jp = orig[font.WIDTHS:font.WIDTHS + 0x200]
        self.wt_en = bytes(rom[font.WIDTHS:font.WIDTHS + 0x200])
        self.wt_small = bytes(rom[0x8C02FB:0x8C02FB + 0x200])
        self.variants, self.by_id = load_windows()
        self.gloss = load_glossary()
        self.waive = load_waivers()
        self.sub_width = {}   # widest Japanese line per sub-table: the budget of never-drawn rows
        for f in sorted((ROOT / "script").glob("s*.tsv")):
            ws = [self.jp_width(ln) for r in script.read_tsv(f) if not r["notes"].startswith(("nontext", "debug"))
                  for ln in re.split(r"\{n\}|\{p\}", r["jp"])]
            self.sub_width[int(f.name[1:3])] = max(ws or [0])

    def width(self, text, small=False):
        text = text.replace("{fill}", "").replace(script.TAIL, "")
        return insert.px(self.et.encode(text), self.wt_small if small else self.wt_en)

    def jp_width(self, text):
        return insert.px(self.jt.encode(text.replace(script.TAIL, "")), self.wt_jp)

    def tag_en(self, jp_tag):
        for j, e, _, _ in self.gloss:
            if j == jp_tag:
                return e
        return None

    def check(self, sub, r):
        errs = []
        mid, jp, en = r["id"], r["jp"], r["en"]

        def err(rule, msg):
            if (mid, rule) not in self.waive:
                errs.append(f"{mid} [{rule}] {msg}")

        if not en:
            return errs
        if any(ord(c) > 126 for c in en) or "\t" in en or "\\" in en:
            err("ascii", f"non-ASCII, tab or backslash: {en!r}")
        try:
            self.et.encode(en.replace("{fill}", "").replace(script.TAIL, ""))
        except Exception as e:  # noqa: BLE001
            err("encode", str(e))
            return errs
        cj = Counter(t for t in TOKEN.findall(jp) if not FREE_TOKENS.match(t) and not t.startswith("{c"))
        ce = Counter(t for t in TOKEN.findall(en) if not FREE_TOKENS.match(t))
        if cj != ce:
            err("codes", f"control codes differ: jp {dict(cj)} en {dict(ce)}")
        if re.search(r"\{var\}(st|nd|rd|th)\b", en):
            err("ordinal", "suffix glued onto {var}")
        for j, e, avoid, hon in self.gloss:
            if not j.startswith("？") and has_term(jp, j, hon) and e.lower() not in en.lower():
                err("honorific" if hon else "glossary", f"{j} -> {e!r} missing")
            for a in avoid:
                if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", en, re.I):
                    err("avoid", f"{a!r} is a rejected spelling (glossary: {e!r})")
        names = self.by_id.get(mid, set())
        story = sub in STORY
        if story or "dialogue" in names:
            errs += self.check_dialogue(mid, jp, en, err)
            return errs
        if names:
            v = self.variants[sorted(names - {"name_tag"})[0]] if names - {"name_tag"} else None
            if v:
                lines = re.split(r"\{n\}|\{p\}", en)
                lines = [ln for ln in lines]
                if len([ln for ln in lines if ln.strip(" ")]) > (v["lines"] + (1 if mid == "1E9EE8" else 0)):
                    err("lines", f"{len(lines)} lines > {v['lines']}")
                for ln in lines:
                    w = self.width(ln, v["font"] == "small")
                    if w > v["px"]:
                        err("width", f"{w} px > {v['px']}: {ln!r}")
                return errs
        jl, el = re.split(r"\{n\}|\{p\}", jp), re.split(r"\{n\}|\{p\}", en)
        if len(jl) != len(el):
            err("lines", f"{len(el)} lines, Japanese has {len(jl)} (unplaced/column row keeps its lines)")
            return errs
        column = r["notes"].startswith("column")
        lim_sub = self.sub_width.get(sub, 0)
        for a, b in zip(jl, el):
            lim = self.jp_width(a) if column or "{fill}" in b else lim_sub
            w = self.width(b)
            if w > max(lim, 16):
                err("width", f"{w} px > {'column' if column else 'widest Japanese line'} {lim} px: {b!r}")
        return errs

    def check_dialogue(self, mid, jp, en, err):
        jtag, _, jbody = jp.partition("{n}")
        etag, _, ebody = en.partition("{n}")
        if jtag.strip():
            want = self.tag_en(jtag)
            if want is None:
                err("tag", f"speaker {jtag} not in the glossary")
            elif etag != want:
                err("tag", f"speaker {etag!r}, glossary says {want!r}")
            tw = self.width(etag, small=True)
            if tw > 64 and (etag, "tagwidth") not in self.waive:
                err("tagwidth", f"tag {etag!r} {tw} px > 64")
        elif etag != jtag:
            err("tag", f"empty speaker line must stay {jtag!r}, got {etag!r}")
        v = self.variants["dialogue"]
        for page in ebody.split("{p}"):
            lines = page.split("{n}")
            if len(lines) > v["lines"]:
                err("lines", f"{len(lines)} lines on a page: {page!r}")
            for i, ln in enumerate(lines):
                lim = v["last_px"] if i == len(lines) - 1 else v["px"]
                w = self.width(ln)
                if w > lim:
                    err("width", f"{w} px > {lim}: {ln!r}")
        return []


def main(argv):
    if argv[:1] == ["--fit"]:
        lint = Lint()
        text = argv[1]
        for ln in re.split(r"\{n\}|\{p\}", text):
            print(f"{lint.width(ln):4d}  {ln}")
        return 0
    lint = Lint()
    want = set()
    files = sorted((ROOT / "script").glob("s*.tsv"))
    for a in argv:
        if a.endswith(".tsv"):
            files = [Path(a)]
        else:
            want.add(a.upper())
    errs, n, missing = [], 0, 0
    for f in files:
        sub = int(f.name[1:3])
        for r in script.read_tsv(f):
            if want and r["id"] not in want:
                continue
            if r["notes"].startswith(("nontext", "placeholder", "debug")):
                continue
            if not r["en"]:
                missing += 1
                continue
            n += 1
            errs += lint.check(sub, r)
    for e in errs:
        print(e)
    print(f"{n} rows checked, {len(errs)} errors, {missing} text rows without English")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
