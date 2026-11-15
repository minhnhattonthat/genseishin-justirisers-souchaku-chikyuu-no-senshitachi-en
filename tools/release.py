"""release.py: build, gate and package a release (references/pipeline.md §Release). Never publishes.

    python -X utf8 tools/release.py [--version 1.0] [--force]

Stops at the first failure:
  build (build.py --verify: dump check, identity build, romcheck incl. leftover Japanese) -> tests (tools/check.py)
  -> smoke (emu.py boot route) -> jp left (tools/romcheck.py en: every message of the built block decoded; the
  skill's jp_left.py assumes NUL-terminated strings, this game ends messages with 0x1F) -> qa_gate.py check on every
  work/qa/**/manifest.tsv (verdicts = the manifest's sibling `verdicts/`; `old_*` dirs are archives, skipped)
  -> textcover.py (0 failing) -> no unticked line in docs/polish.md -> no template placeholder in README.md
  -> debug tool off (the ROM is the default build of this run: no --qa/--marker; the warp tool is a Lua script
  outside the ROM) -> BPS patch -> re-apply to the clean dump and compare -> zip (patch + README.txt).

Output: release/v<version>/Genseishin_Justirisers_EN_v<version>.bps and .zip (gitignored). The playable patched ROM
stays in build/justirisers_en.gba. Refuses to overwrite an existing version's files without --force.
"""
import argparse
import hashlib
import re
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

ROM = ROOT / "build" / "justirisers_en.gba"
NAME = "Genseishin_Justirisers_EN_v{v}"


def skill():
    return Path(subprocess.run([sys.executable, str(ROOT / "tools" / "skill.py")], capture_output=True, text=True,
                               check=True).stdout.strip())


def step(name, cmd):
    print(f"== {name}: {' '.join(str(c) for c in cmd)}", flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=ROOT)
    if r.returncode:
        sys.exit(f"RELEASE STOPPED at {name} (exit {r.returncode})")


def fail(name, msg):
    sys.exit(f"RELEASE STOPPED at {name}: {msg}")


def hashes(data):
    return {"size": len(data), "crc32": f"{zlib.crc32(data):08X}", "md5": hashlib.md5(data).hexdigest(),
            "sha1": hashlib.sha1(data).hexdigest()}


def readme_text(v, orig, built, patch_sha1):
    o, b = hashes(orig), hashes(built)
    return f"""Genseishin Justirisers: Souchaku Chikyuu no Senshitachi - English translation v{v}
================================================================================

Unofficial English fan translation of Genseishin Justirisers: Souchaku Chikyuu no Senshitachi
(Game Boy Advance, Konami, 2004). This zip holds only a patch: no game data. Do not share patched ROMs.

Translated: all story dialogue (every hero's version of each event), battle shouts, menus, save/load, options,
status and mission text, stage names, and the text drawn as graphics (title subtitle, chapter cards, mode buttons,
HUD, pause, points/clear screens, game over, banners, credits roll). Left as in the original: the official
Justirisers and Choseishin logos and the Japanese voice samples. The game has no name entry.

How to patch
------------
1. You need your own dump of the Japanese cartridge:
     No-Intro name: Genseishin Justirisers - Souchaku Chikyuu no Senshitachi (Japan)
     Size:   {o['size']} bytes
     CRC32:  {o['crc32']}
     MD5:    {o['md5']}
     SHA-1:  {o['sha1']}
2. Apply {NAME.format(v=v)}.bps with a BPS patcher: Floating IPS (flips), beat, or https://www.marcrobledo.com/RomPatcher.js/
3. The patched ROM should have:
     CRC32:  {b['crc32']}
     MD5:    {b['md5']}
     SHA-1:  {b['sha1']}
   Patch file SHA-1: {patch_sha1}

Play
----
Tested in MesenCE 2.2.1 with the official GBA BIOS; any accurate GBA emulator or a flash cart should work.
Start from a cold boot: do not load savestates made with the Japanese ROM. In-game saves carry over.

Known issues: none known. Report bugs (a savestate helps most):
https://github.com/minhnhattonthat/genseishin-justirisers-souchaku-chikyuu-no-senshitachi-en/issues

Credits
-------
Translation, hacking and tools: minhnhattonthat. No earlier fan translation of this game exists.
The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
Fonts and their licences: docs/fonts.md in the repository.

Genseishin Justirisers is (c) 2004 Konami, Justiriser Project and TV Tokyo. This is an unofficial fan project, not
affiliated with them.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--force", action="store_true", help="overwrite this version's existing release files")
    a = ap.parse_args()
    v = a.version
    out = ROOT / "release" / f"v{v}"
    bps_path, zip_path = out / f"{NAME.format(v=v)}.bps", out / f"{NAME.format(v=v)}.zip"
    if (bps_path.exists() or zip_path.exists()) and not a.force:
        fail("start", f"{out} already holds v{v} files; pass --force to overwrite")
    py, S = sys.executable, skill()

    step("build", [py, "-X", "utf8", "build.py", "--verify"])
    built_sha1 = hashlib.sha1(ROM.read_bytes()).hexdigest()
    step("tests", [py, "-X", "utf8", "tools/check.py"])
    step("smoke", [py, "-X", "utf8", S / "scripts" / "emu.py", ROM, "--out", "work/qa/smoke", "--route",
                   "tools/routes/boot.txt", "--smoke"])
    step("jp left", [py, "-X", "utf8", "tools/romcheck.py", "en"])

    manifests = sorted(m for m in (ROOT / "work" / "qa").rglob("manifest.tsv")
                       if not any(p.startswith("old_") for p in m.relative_to(ROOT).parts))
    if not any(m.parent.name == "story" for m in manifests):
        fail("qa gate", "no story-pass manifest (work/qa/story/manifest.tsv)")
    for m in manifests:
        step(f"qa gate {m.relative_to(ROOT).as_posix()}",
             [py, "-X", "utf8", S / "scripts" / "qa_gate.py", "check", m, m.parent / "verdicts"])
    step("textcover", [py, "-X", "utf8", S / "scripts" / "textcover.py", "work/qa/final", "build/strings.tsv",
                       "--waive", "docs/text_unshown.tsv", "--mask", "0x1FFFFFF"])

    open_polish = [ln for ln in (ROOT / "docs" / "polish.md").read_text(encoding="utf-8").splitlines()
                   if ln.startswith("- [ ]")]
    if open_polish:
        fail("polish", f"{len(open_polish)} unticked line(s) in docs/polish.md:\n" + "\n".join(open_polish))
    holes = re.findall(r"<(?!https?:|br>)[A-Za-z][^<>\n]*>", (ROOT / "README.md").read_text(encoding="utf-8"))
    if holes:
        fail("readme", f"template placeholders left in README.md: {sorted(set(holes))}")

    built = ROM.read_bytes()
    if hashlib.sha1(built).hexdigest() != built_sha1:
        fail("debug off", "build/justirisers_en.gba changed after this run's default build")

    import check_rom  # noqa: E402
    orig, orig_path = check_rom.original(), check_rom.rom_path()
    out.mkdir(parents=True, exist_ok=True)
    step("patch", [py, "-X", "utf8", "tools/bps.py", "make", orig_path, ROM, bps_path])
    check = out / "check.gba"
    step("re-apply", [py, "-X", "utf8", "tools/bps.py", "apply", orig_path, bps_path, check])
    if check.read_bytes() != built:
        fail("re-apply", "patched clean dump differs from build/justirisers_en.gba")
    check.unlink()

    patch = bps_path.read_bytes()
    text = readme_text(v, orig, built, hashlib.sha1(patch).hexdigest())
    (out / "README.txt").write_text(text, encoding="utf-8", newline="\r\n")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(bps_path, bps_path.name)
        z.writestr("README.txt", text.replace("\n", "\r\n"))
    h = hashes(built)
    print(f"RELEASE OK v{v}: {zip_path.relative_to(ROOT).as_posix()} ({zip_path.stat().st_size} bytes), "
          f"patch {len(patch)} bytes sha1 {hashlib.sha1(patch).hexdigest()}, patched ROM CRC32 {h['crc32']} "
          f"sha1 {h['sha1']}")


if __name__ == "__main__":
    main()
