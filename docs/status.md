# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2. Debug tool fixed and all 75 entries re-run; 31 entries still need a verdict (see Next). Last build: none yet.
- **Done:**
  - Step 0: MesenCE 2.2.1 + BIOS in `tools/mesen/`, guard hook proven, pre-commit gate proven, `tools/check.py`, `rom.sha1`, boot route, AGENTS.md, decisions D1-D7.
  - Phase 1 (`docs/re/text.md`, `docs/re/graphics.md`): custom 8-bit encoding, font 0x2CBC34, master table 0x1E90C0 -> 41 sub-tables -> 795 messages in 0x1E90C0-0x1FE9F0; free space candidate 0xD2356C-0xF00000; resource table 0xD226AC + Konami LZ (`tools/res.py`); sprite/BG formats; full graphics-text survey.
  - Phase 2 (`docs/re/scenes.md`): scene machine 0x030052F0 (dispatcher 0x08026684, table 0x08D22CA0), progress block 0x03001E10, player struct (*0x08D2275C: +0x34 x, +0x38 y), scene 4 sub 81/82 (post-clear event). Debug tool `tools/debug/warp.lua` + **75-entry** scene list (`tools/debug/gen_scenes.py`; test `tests/test_scenes.py`): title, top menu, mode select (kids/normal/hard), intro story (entered the game's way), options, load/save/slots/overwrite prompt, points, character select, pause, status, continue, game over, stages 1-1..5-4 with their stage-start events, every stage clear with its post-clear event, 5 mecha battles + win / lose, genseishin choice, round-2 area 5 win (`battle_5_win_r2`), ending (+ save), credits (forced), attract battle/story, `event_3_26`. Cheats `@clear[N]` (now with unstick + TIMEOUT81 for post-clear walks), `@subN`, `@pause`, `@hold`, `GOD=1`. `tools/debug/warp_all.py` runs any subset in parallel, `--states` regenerates `work/states/`. New probe `tools/lua/pcsample.lua` (where the CPU is, dispatcher calls per sample).
  - This session: 46 unproven entries re-run (46/46 reached their scene), then every entry's sheet reviewed by `codex exec` (read-only): 17 issues, all investigated and fixed or documented. Findings: the game has **5 areas**, not 7; both rounds end after the area 5 battle (verified), so the 18 area 6-7 entries were removed (poked states: fade hang, instant death, garbage battle; 7-1's event is the attract script). Title/top-menu/story_intro entries were wrong (scene 0 sub 4 is the PUSH START title; scene 1 must be called from the menu). mode_kids/hard pressed before the screen took input. Post-clear walks hit walls after a forced clear (unstick added). 1-1 needed a bigger budget.
- **Next (finish phase 2):**
  1. Re-review the 31 entries without a verdict: `work/qa/warp/chunks/redo_00..02` (30 re-run entries; each `name<TAB>expected`) plus `attract_story` (the first pass skipped it). Sheets are current (`work/qa/warp/<name>/sheet*.png`). Run them one chunk at a time (memory): `cd work/qa/warp/chunks && cat brief.md redo_00 | codex exec -s read-only -C ../../../.. - > verdict_redo_00.tsv` (then 01, 02; add attract_story to one). The parallel run was killed by Claude Code for low system memory before it wrote anything. Append the verdicts to `work/qa/warp/verdicts.tsv` (44 current `ok` rows there now); fix any `issue`.
  2. Then phase 3 (identity build, `references/pipeline.md` §Identity).
- **Open questions (non-blocking, phase 2 leftovers):**
  - Post-clear events of 2-4, 3-4 and 4-1 hang the game after a forced clear (CPU loop in IWRAM 0x030011C8-0x0300121C; likely waiting on the stage boss). Their entries prove CLEAR! and the event start (4-1 also its dialogue). If phase 8 text coverage finds their later lines unreached, build a boss-fight route (GOD + reach the boss).
  - Event scripts 3.26-3.29 and 3.32-3.39 are never run by the game's own flow (3.26 shown by `event_3_26`). Check in phase 4/8 whether their text is unique before translating it as live text.
  - Credits (scene 11) have no natural entry found; the `credits` entry forces scene 11.
  - Unlock message (BG s0629, scene 5 sub 16 when F4A != 0) not yet seen; s0648-s0651 ("Congratulations") near scene 6/7 save code not yet seen. Unknown BG screens s0670-s0673 (HUD code, scene 4) and s0207-s0216 still unplaced: check against stage/battle shots in phase 8.
  - Optional before phase 4: read the text interpreter (0x08007594-0x080077FC) to confirm control-code arg counts.
- **Open bugs:** none.
- **Waiting on the user:** none.

Savestates (not in git; recreate): `python -X utf8 tools/debug/warp_all.py --rom work/orig.gba --states` writes `work/states/<scene>.mss` for every entry (after phase 5 use the build ROM, default `--rom`). Run with `--jobs 3` or fewer: more has hit the machine's memory limit twice.
