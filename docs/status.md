# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 1. Research and recon in progress (text side done; graphics survey and free-space search left). Last build: none yet.
- **Done:**
  - Step 0: MesenCE 2.2.1 + BIOS in `tools/mesen/`, guard hook proven (blocks `sed -i`), pre-commit gate proven, `tools/check.py`, `rom.sha1`, boot route to mode select, AGENTS.md, decisions D1-D7.
  - Phase 1 text recon (`docs/re/text.md`): uncompressed custom 8-bit encoding + `01-0B xx` 2-byte codes = font cells; font at ROM 0x2CBC34 (16x16 1bpp); master table 0x1E90C0 (62 u32 self-relative) -> 41 sub-tables (u16 self-relative) -> 795 messages ending 0x1F; all text in 0x1E90C0-0x1FE9F0. No earlier fan patch.
- **Next (finish phase 1):**
  1. Graphics-text survey: tour the title menu, mode select, every mode's screens, options, pause, game over, area cards, stage map, character select, ending, credits; fill `docs/re/graphics.md` (layer, source guess). Use `tools/lua/dmalog.lua` + `ppudump.lua` for sources. The display uses OBJ sprites heavily (the dialogue box is OBJ; BG2 only on the intro).
  2. Free-space candidates: 0x00/0xFF runs inside the 16 MiB ROM (no trailing padding); note in text.md.
  3. Optional before phase 4: read the text interpreter (PCs 0x08007594-0x080077FC) to confirm control-code arg counts.
- **Open bugs:** none.
- **Waiting on the user:** none.

Savestate: `work/states/story_intro_3000.mss` (story intro, a few hundred frames before the first dialogue box; not in git, recreate with `emu.py work/orig.gba --route tools/routes/boot.txt --mash 40 --frames 3600 --state-every 600`, state s003000).
