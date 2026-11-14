# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2. Debug tool not started (phase 1 research and recon done). Last build: none yet.
- **Done:**
  - Step 0: MesenCE 2.2.1 + BIOS in `tools/mesen/`, guard hook proven, pre-commit gate proven, `tools/check.py`, `rom.sha1`, boot route, AGENTS.md, decisions D1-D7.
  - Phase 1 text recon (`docs/re/text.md`): custom 8-bit encoding + `01-0B xx` 2-byte codes = font cells; font 0x2CBC34; master table 0x1E90C0 -> 41 sub-tables -> 795 messages; all text in 0x1E90C0-0x1FE9F0.
  - Free space (`text.md`): 0xD2356C-0xF00000, 1.95 MB of 0xFF (candidate; trap-test in phase 5).
  - Resource table 0xD226AC (23 groups), Konami-LZ decompressor run under unicorn (`tools/res.py`), 'fp' container (`docs/re/graphics.md`).
  - Sprite and BG formats decoded (`graphics.md`): 'aS'/'AS' OBJ containers (group 17), BG tilesets (group 18, with a per-tile palette table, verified against a VRAM dump) + BG maps (group 20, paired by index). Groups 14/16/19/22 hold no tiles; 0x75F3C0-0xD226AC is PCM sound.
  - Graphics-text survey complete: every tile-bearing group swept (`tools/sweep.py`, `tools/bgscreens.py`), Codex read-only verdicts in `docs/re/sweep/*.tsv`, survey table in `graphics.md` maps each element (config, pause, mode select, data, char select, map, HUD, status, continue, unlock message, credits, name plates) to its resource. The config labels are BG tiles (s0620), not a second text system.
- **Next (phase 2, debug tool):**
  1. Build `tools/debug/warp.lua` + `tools/debug/scenes.gba.txt` (AGENTS.md "Warp" command): find the game-state / scene variables (RAM search with `$SKILL/scripts/ramsearch.py` across the tour: title -> mode select -> story -> stage map -> stage 1-1), and a way to jump to any story scene, stage, area card, results, game over, continue, ending and credits from a cold boot.
  2. Scene list should cover every survey row incl. "Not yet seen in-game" and the unknown BG screens s0207-s0216, s0670-s0673 (identify them by warping).
  3. Optional before phase 4: read the text interpreter (0x08007594-0x080077FC) to confirm control-code arg counts.
- **Open bugs:** none.
- **Waiting on the user:** none.

Savestates (not in git; recreate): `work/states/story_intro_3000.mss` (`emu.py work/orig.gba --route tools/routes/boot.txt --mash 40 --frames 3600 --state-every 600`); gameplay stage 1-1 at `work/qa/survey/tour1/s010500.mss` (same route, `--frames 12000 --state-every 1500`; start = pause menu). Mode select VRAM dump: `emu.py work/orig.gba --route tools/routes/boot.txt --frames 1800 --script $SKILL/scripts/lua/probes/ppudump.lua`.
