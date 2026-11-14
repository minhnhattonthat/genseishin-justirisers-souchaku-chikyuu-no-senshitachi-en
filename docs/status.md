# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 1. Research and recon in progress (text, free space, resource table, compression and the tour survey done; static sweep of the OBJ sprite groups 16-20 left). Last build: none yet.
- **Done:**
  - Step 0: MesenCE 2.2.1 + BIOS in `tools/mesen/`, guard hook proven, pre-commit gate proven, `tools/check.py`, `rom.sha1`, boot route, AGENTS.md, decisions D1-D7.
  - Phase 1 text recon (`docs/re/text.md`): custom 8-bit encoding + `01-0B xx` 2-byte codes = font cells; font 0x2CBC34; master table 0x1E90C0 -> 41 sub-tables -> 795 messages; all text in 0x1E90C0-0x1FE9F0.
  - Free space (`text.md`): 0xD2356C-0xF00000, 1.95 MB of 0xFF (candidate; trap-test in phase 5).
  - Resource table 0xD226AC (23 groups), Konami-LZ decompressor 0x08001CD4 run exactly under unicorn (`tools/res.py`), 'fp' container format, loader log probe `tools/lua/reslog.lua` (`docs/re/graphics.md`).
  - Tour survey (`graphics.md` table): boot, title, top menu, config, data load, mode select, story, area card, stage map, character select, HUD, pause, name plates. Menu routes: `tools/routes/survey_*.txt`.
  - Static sweep of groups 1, 4, 5, 9, 10, 11 (`tools/sweep.py`, Codex read-only verdicts in `work/sweep/review/`): Japanese only in logos (group 5) and stage-background shop signs (group 9).
- **Next (finish phase 1):**
  1. Decode the 'aS' sprite container (groups 11, 14-20; e.g. dialogue box 17.606 at ROM 0x5EABA0, tiles at +0xD8; header `'aS' u8 u8 u16 u16 u16 n` + palette, then frame records). Add it to `tools/sweep.py` like `fp_tiles`, sweep groups 16-20 (menus/map/character select/name plates live there) and 14/15/22 if they hold tiles, review the pages with `codex exec --sandbox read-only -i ...` (prompt in `work/sweep/review/prompt.txt`), add rows to `graphics.md`.
  2. Find the source of each tour row marked "graphic" (config, pause, mode select labels): `tools/lua/dmalog.lua` on `tools/routes/survey_option.txt` etc. gives the ROM source; map it to a resource with `tools/res.py list`.
  3. Rows not reachable without the debug tool (game over, results, areas 2+, ending, credits) are listed as "Not yet seen"; phase 2's warp tool adds them.
  4. Optional before phase 4: read the text interpreter (0x08007594-0x080077FC) to confirm control-code arg counts.
- **Open bugs:** none.
- **Waiting on the user:** none.

Savestates (not in git; recreate): `work/states/story_intro_3000.mss` (`emu.py work/orig.gba --route tools/routes/boot.txt --mash 40 --frames 3600 --state-every 600`); gameplay stage 1-1 at `work/qa/survey/tour1/s010500.mss` (same route, `--frames 12000 --state-every 1500`; start = pause menu).
