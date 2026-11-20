# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 9. Released: **v1.0 published 2026-11-15** at the user's request
  (https://github.com/minhnhattonthat/genseishin-justirisers-souchaku-chikyuu-no-senshitachi-en/releases/tag/v1.0,
  notes `release/v1.0/notes.md`), repo now **public**, description set to the real title. Zip
  `release/v1.0/Genseishin_Justirisers_EN_v1.0.zip` (the download matches it), patch sha1 4cd30fb2..., patched ROM
  CRC32 1879B614 / sha1 **08de8273...**. Archived QA rounds moved to `work/qa_old/` (the publish guard checks every
  `work/qa/**/manifest.tsv`). Next: player bug reports (GitHub issues, AGENTS.md). Last build: 2026-11-15 `build/justirisers_en.gba` sha1 08de8273, check ok (70 tests),
  smoke ok, `tools/release.py` exit 0 (every gate: visual 717, gfx 58, story 8, textcover 0 failing, polish, README).
- **Session 2026-11-21: v1.1 (issue #1 fixes merged, PR #2).** Emulator switched to the **MesenCE QA fork** (qa-1,
  `fetch_emu.py mesen`): upstream 2.2.1 held ~1.1 GB per run and the re-tour was killed twice for low memory; the
  fork gives identical frames. `tools/debug/warp_all.py` now passes `SCENES=[[abs path]]` (emu.py runs a copy of
  the script from the output dir, so warp.lua's relative default failed every scene). Re-tour of the touched
  scenes only (`work/retour_v1.1.sh`: data_save*, battle_choice, battle_5_win_r2, ending_save, credits, clear_*,
  plus tour_adv), sheets, gfxshots; Codex was out of credits, so the verdicts came from Claude reviewer agents with
  `docs/visual-qa-brief.md` (`work/qa/verdicts/v11_*`, `gv11_*`, `v11b_*`).
  - Found by that QA: **save-card plate "Riser Kageri" 646[1]** sat 1 px above Glen/Gant (the g's descender moves
    the centred line up), and the overwrite prompt hid the R's top ("Kiser"). Rect now 0,1,72,23 plus a
    full-plate clear row (`gfx/obj.tsv`). Pre-existing since v1.0; only visible when the warp catches the prompt.
  - Manifests: stale ids (sheet pages the shorter reruns no longer make) dropped; `changed` times rebuilt (v1.0
    time where the hash is unchanged, else the v1.1 init time when the scene's frames predate the verdicts);
    `manifest.tsv.v10` = the v1.0 copies.
  - **Open (owner's call):** char-select Kageri names (`gfx/bg.tsv` 600:602) at tracking -1: "Phantom Crush" C/r
    touch (reads "Orush"), "Kageri Striker" word gap ~1 px. Since v1.0; tracking 0 doesn't fit the 88 px rect
    (94/98 px). Needs shorter names or pair kerning. Controller verdict `work/qa/verdicts/v11_controller.tsv`.
  - Reporter's wording wishes (roll call as Kenzan/Sanjou/Suisan) still open, see the issue #1 entry below.
- **Session 2026-11-20: issue #1 (branch fix/issue-1, PR pending review, no release).** Reproduced by warping on
  both ROMs (the reporter's save is a RetroArch mGBA state; not needed). Build **66142040**, check ok (71 tests), smoke ok.
  - Save menu 1E9F3A (`data_save`): the cursor covered the first letter (English text began at x 47, the original's
    at x 55, cursor tip x 54): indent 2 -> 5 spaces, text at x 59.
  - Round-2 choice card 18[629] (`battle_choice`): 4 px of the old ケ outline (x 48-51, y 117) sat outside both
    rects: prefix rects now 0,112,52,24 and 122,112,52,24 (same centre, text unmoved).
  - Credits roll 700: pages are fixed 160 px windows (docs/re/graphics.md §Credits); Riser Glen / Armor Gunner /
    Motoyuki Yoshioka straddled page edges and were cut. Cast now on pages 2-3, staff on page 4; new test.
  - Not done (wording preferences from the report, for the owner): roll-call shouts けんざん/さんじょう/すいさん as
    romaji (Kenzan/Sanjou/Suisan) instead of "Here I come!!" / "On the scene!!" / "Reporting for battle!!".
    Raizeros is already spelled as the reporter prefers.
  - Release gates not rerun: the visual manifests need fresh verdicts for data_save, battle_choice, credits before
    a v1.1 `tools/release.py`.
- **Session 2026-11-15 (m), part 2:** codex verdicts on the re-tour found two real graphics bugs, both fixed:
  - **Attract-mode title** (after the story clip, before the real title 5[20]) still showed 装着!地球の戦士たち and
    the Japanese copyright: BG layers 18[247] (maps 20[247]/20[248]) and 18[245], new writer `tools/attract.py` +
    `gfx/attract.tsv` + `tests/test_attract.py`, shot `attract_title` (docs/re/graphics.md §Attract title).
  - **Char-select arrow highlights** 20[603]/20[604] were missing from `gfx/bg_pairs.tsv` (tiles recycled into
    letter fragments for a few frames on a hero switch): listed; `tools/pairsweep.py` + a reslog check found no
    other gap.
  - Other issue verdicts judged by the controller (`work/qa/verdicts/e_controller.tsv`): mode_bonus description
    crossfade = the game's own (original overlaps the same way); clear_5_3 lingering portrait / garbage tiles =
    warp.lua's TIMEOUT81 forcing the post-clear event to end mid-dialogue (the original plays it out with slow A).
    Stale manifest entries for sheet pages the rerun no longer makes were dropped.
  - Only the scenes these changes touch were rerun on 08de8273 (attract_story, char_select*, continue*, plus
    stage_2_3/status/pause); runs are not frame-exact between emulator runs (boot timing shifts), so their sheets got
    fresh codex verdicts (all ok). Text unchanged since 050ac249, so string addresses and textcover logs hold.
  - `tools/final_tour.sh` takes `JOBS=1` for low-memory machines.
- **Session 2026-11-15 (m), part 1: phase 9.**
  - Done: `docs/style-reference.md`; story pass (`tools/pairs.py --chapters work/qa/story/chapters`, 8 chapters,
    `tools/story_codex.py` = read-only codex per chapter, brief `docs/story-reviewer-brief.md`, reports
    `work/qa/story/reports/{a,b,c}_*.md`): one Important (1F0FC6) fixed, Minors fixed or waived; `qa_gate.py check
    work/qa/story/manifest.tsv work/qa/story/verdicts` exit 0. `docs/polish.md` all ticked. README filled (hashes).
    **`tools/release.py`** written (build --verify, check, smoke, romcheck jp-left, qa_gate on every
    `work/qa/**/manifest.tsv` except `old_*`, textcover, polish, README placeholders, debug off, BPS, re-apply, zip in
    `release/v1.0/`).
  - The text changes moved string addresses, so the phase 8 tour logs no longer prove textcover: old tour output moved
    to `work/qa/old_v2/`, full `bash tools/final_tour.sh` started on 050ac249 (log `work/qa/final_tour_run.log`).
    **Claude Code stopped it for low system memory** during step `tour` (~81 of 87 scenes; tour_adv, msgview, gfx,
    inkcheck and sheets not run); orphans killed. Free memory was ~1-1.5 GB with other projects' emulators running.
  - **Re-tour done on 050ac249** (second try, `JOBS=1`; an orphan of the first run finished tour_adv/msgview on the
    same build, every log is newer than the build): tour 87/87, tour_adv 59/59, gfxshots 57 (0 missing), inkcheck
    7/0 failing, **textcover 621 shown, 170 waived, 0 failing**. Sheets regenerated; both manifests re-initialised
    with `--build`: 721 of 727 tour sheets and 13 of 57 gfx shots need new verdicts.
  - Codex verdicts on the re-tour (`work/qa/chunks4`, prefix `d_`; gfx `gd_`): see part 2.
- **Session 2026-11-15 (l): phase 8 done.**
  - Codex verdicts on the last chunks (`work/qa/chunks2` 006..013): 222 ok, 1 issue: `tour_adv/clear_1_2/sheet_2`
    frame f3720 = green stripes of garbage tiles (first frames of the points screen, scene 6 sub 1, palette fade-in).
    **Not reproducible**: the same warp with the same options (and with a shot every frame, on both ROMs) shows a
    clean green fade-in on that frame, identical in the original (the green flash itself is the game's own). It was a
    one-off capture of the memory-starved tour run. Old output kept in `work/qa/old_glitch/clear_1_2`; the scene's
    output replaced by the rerun, its sheets regenerated, manifest re-initialised with `--build`, 3 sheets re-verdicted
    by Codex (`work/qa/chunks3`, prefix `b_`): ok.
  - **Gates on a2ecdeb4**: `qa_gate.py check work/qa/manifest.tsv work/qa/verdicts` exit 0 (713 sheets ok);
    gfx gate exit 0 (57 ok); inkcheck 7/0 failing and textcover 0 failing (session (k)); check ok, smoke ok.
  - **Next (phase 9, `references/pipeline.md` §Release):** write `docs/style-reference.md` (phase 6 review Minor 3,
    see the Next line below), story-pass verdict per chapter (`work/qa/story/manifest.tsv`, `references/translation.md`
    §Review), tick or close every line of `docs/polish.md`, `jp_left.py`/romcheck on the release build, debug tool
    off, README with base ROM hashes, `tools/release.py` (patch + verify, zip). Never `gh release create`.
- **Session 2026-11-15 (k), part 2:**
  - **Re-tour complete on a2ecdeb4**: tour 87/87 + tour_adv 59/59 + msgview (default, s01/s03) + gfxshots (57 shots,
    0 missing) + inkcheck (7 rows, 0 failing) + textcover (621 shown, 170 waived, 0 failing). Most of it ran on
    b9034870; the build then changed only 18[641] (status), 4[6] (intertitle) and 17[601] (top menu), and the scenes
    loading them (top_menu, top_menu_continue, status, status_kageri, status_gant, story_intro; tour_adv
    story_intro) were rerun on a2ecdeb4. msgview runs show only stage 1-1 text, unaffected.
  - Contact sheets: **`tools/final_sheets.sh`** (now also the last step of `final_tour.sh`): 713 sheets.
    `work/qa/manifest.tsv` initialised with `--build` a2ecdeb4.
  - **Gfx gate passes**: `qa_gate.py check work/qa/final/gfx/manifest.tsv work/qa/final/gfx/verdicts` exit 0 (57 ok).
  - **Sheet gate: 490 ok, 0 not ok, 223 without a verdict.** Claude Code stopped the Codex run for low system
    memory. **Next:** `python -X utf8 tools/qa_codex.py work/qa/chunks2/chunk_*.txt --jobs 2 --prefix a_` (done
    chunks are skipped: a_chunk_000..005 exist; 006..013 left), then `qa_gate.py check work/qa/manifest.tsv
    work/qa/verdicts` must exit 0 = phase 8 done. If a sheet gets `issue`, fix, rerun its scene, rerun
    `final_sheets.sh`, re-init the manifest with `--build`, and run `qa_gate.py todo` into a new chunk dir with a
    new `--prefix` (chunk names repeat between todo runs; qa_codex skips by file name).
  - Fixed from the tour verdicts: **status names** (they ran to x 239 over the circuit art): grid names now end at
    x 232, Kageri Striker proportional with a double space; clear strips for the old names' tails at x 232-239.
    18[641] budget **495** (`gfx/bg_budget.tsv`: VRAM 460 is the extra tile, 461-511 is the paused stage's map,
    rewritten on leaving the status screen; description text starts at 512), spare tile 351.
    **Intro intertitle** それから 四五〇ねん… = LZ picture **4[6]** (not in the survey before): "450 years later..."
    (`gfx/obj.tsv` `pic4:6`; `objtext.load_pic` decompresses/recompresses LZ pictures in place; test added; shot
    `intertitle`). **Top menu Continue** off-centre after session (j)'s column-63 fix: rects 62 wide (inkcheck 11/10).
- **Session 2026-11-15 (k), part 1:** build b9034870 rebuilt and unchanged, check ok (66 tests), smoke ok.
  - An orphaned `final_tour.sh` of session (j) was still running and failing every scene (exit 0xC0000142 =
    MesenCE could not start for low memory): killed. Other projects' agents keep ~6 MesenCE instances (~4 GB) on the
    machine, free memory ~1-3 GB of 16.
  - `tools/final_tour.sh` now reruns FAIL scenes one at a time (twice; `LOG.retry` = last retry) and resumes from a
    step: `bash tools/final_tour.sh [tour|adv|mv|gfx]`.
  - **Re-tour: step `tour` done, 87/87 ok** (`work/qa/final/tour`, `work/states/` regenerated on this build). Claude
    Code then stopped the run again for low system memory during `tour_adv` (25 of 59 scenes; orphans killed).
    **Next:** `rm -rf work/qa/final/tour_adv` and `bash tools/final_tour.sh adv` (adv + msgview + gfxshots +
    inkcheck) when the machine has memory free (fewer other emulators); then textcover, `qa_gate.py init` both
    manifests with `--build`, Codex verdicts, `qa_gate.py check` (Next below, step (c)).
- **Session 2026-11-15 (j):**
  - **Area chapter cards done** (`tools/cards.py`, rows `gfx/cards.tsv`, `tests/test_cards.py`, docs/re/graphics.md
    §Area cards). Format solved from the loader: 20[n] = metatile map (15 x 10), 19[n] = `a2`, N, N attribute
    bytes, metatiles 0..N. Layers 207-216 (header + title per area), redrawn in place (white bold, dark outline).
    Titles: "Here Come the Justirisers!", "Infiltrate! The Den of Schemes", "Pursuit! Race Across the Wasteland!",
    "Menace! The Bewitching Cyber Knight", "Showdown! Secret Underground Base". Checked in the emulator:
    `work/qa/cards_en`. Shots `card_1..5` added to `gfx/shots.tsv` (gfxshots now also requires every cards.tsv key).
  - **Stage bar**: 18[625/626/627] are the bright (skill usable) copies of 18[655/656/657]; game over loads 18[626]
    over the English map (the garbled bar). New `gfx/bg_variants.tsv` + `bgtext.derive_variants` rebuild them from
    the redrawn sets (`tests/test_bg_variants.py`). Kageri/Gant rows had ink/shadow inverted (their palette swaps 4
    and 5): fixed. Checked `work/qa/bar_en/bars.png`.
  - **Top menu**: the menu window shows the left item's column 63 at x 88; the New Game glow reached it (grey stroke
    beside Continue). Rects 63 wide now; checked `work/qa/topc_en/z.png`.
  - Triage of the other flagged shots: `save`/`save_gant` "Normal" badge needs ~31 px at 1 px spacing on a ~28 px
    face (D11: no "Mode", no abbreviation): kept, legible; `save_kids` plate spans corner to corner like the
    Japanese; `continue_kageri` complete; `choice` as the original. Judge these ok in the gfx verdicts.
  - Re-tour driver promoted to **`tools/final_tour.sh`** (tour + tour_adv + msgview default and s01/s03 +
    gfxshots + inkcheck). Old run moved to `work/qa/old_v1/` (with the old manifest, chunks, verdicts).
  - **The re-tour was stopped by Claude Code for low system memory** after 20 of 87 tour scenes (8 MesenCE
    instances were running on the machine, other agents' included). Partial output in `work/qa/final/tour`: delete
    `work/qa/final/tour` and rerun `bash tools/final_tour.sh` in full when memory allows (run it in the foreground
    or with fewer other emulators; `--jobs 2` is already the minimum that finished before).
- **Session 2026-11-15 (i): final re-tour started; one big gap found (area chapter cards).**
  - **Runs on build 5421be81** (`work/qa/final/`): `tour` (all warps, textcover probe, states regenerated in
    `work/states/`; driver `work/final_tour.sh`), `tour_adv` (59 story warps, ADVANCE=40 GOD=1, +2500 frames),
    `msgview` (default tables, **then `--tables s01,s03` as a second pass**: the default skips them),
    `tour_jp` (same warps on `work/orig.gba`, for comparisons). Smoke ok. check ok (62 tests).
  - **textcover passes**: `textcover.py work/qa/final build/strings.tsv --waive docs/text_unshown.tsv --mask
    0x1FFFFFF` -> 621 shown, 170 waived, 0 failing.
  - **inkbox passes**: `tools/inkcheck.py` over `gfx/inkbox.tsv` (Yes/No, mode buttons 3 and 4, top menu New
    Game / Continue, battle choice prompt): 7 rows, 0 failing.
  - **Graphics-row shots**: `tools/gfxshots.py` + `gfx/shots.tsv` -> `work/qa/final/gfx/<id>.png` (English | original,
    zoomed) and `brief.md`; every key of gfx/bg.tsv, obj.tsv, credits.tsv has a shot except Zakoul sprites 648/662
    (no warp loads them; checked with `objtext.py render`). New warps (87 scenes now): `top_menu_continue`,
    `data_save_hard/kids/bonus/gant` (F4B difficulty 0 normal, 1 hard, 2 kids, 3 bonus; bonus mode plays Zakoul;
    route confirms the overwrite because Mesen keeps the flash save: run these one at a time),
    `char_select_kageri/gant`, `continue_kageri/gant`.
  - **Visual QA**: old manifest/verdicts moved to `work/qa/old_v0/`. New manifests: `work/qa/manifest.tsv` (712 sheets
    of `work/qa/final`, chunks `work/qa/chunks/chunk_000..023`) and `work/qa/final/gfx/manifest.tsv` (51 shots, chunks
    in `work/qa/final/gfx/chunks/`, brief `work/qa/final/gfx/brief.md`). Codex verdicts: **gfx chunks 0-2 done, tour
    chunks 0-7 done; chunks 8-23 not run** (Claude Code stopped the background run: the system was low on memory).
    Resume: `python -X utf8 tools/qa_codex.py work/qa/chunks/chunk_*.txt --jobs 2` (done chunks are skipped).
  - **Issues from the verdicts so far** (raw replies in `verdicts/raw/`):
    1. **Area chapter cards still Japanese** (エリアN + chapter title; story_intro area 1, battle_1..4_win areas 2-5,
       scene 2 sub 4). They are **group 16 r1 0xCF.. + 18/19/20[206..217]** (story_intro f3514: 16[207], 18[206..208],
       19/20[206..208]; battle_1_win f5030: 16[208], 18[206], 18[209..210]) and load through the **credits loader
       0x0801E1F3** (19[n] = 2x2-metatile rows), so `tools/credits.py` is the model. The old notes filed 18/20[207..217]
       as stage scenery: wrong. Next job: survey all area cards (areas 1-5, maybe 6/7), add rows, redraw, warp-check.
    2. Graphics shots flagged, to triage against the original: `bar_gameover` (game_over f4140 stage bar shows
       Japanese/garbled glyphs after "L+R ="); `save`, `save_gant` ("Normal" badge overflows the face: the known
       cosmetic, now a real issue); `save_kids` ("Riser Kageri" past the card frame?); `continue_kageri` (plate clipped
       at its right edge?); `top_continue` (stray grey stroke left of the backing); `choice` ("Genseishin" against the
       screen edge: the original starts there too, likely ok).
  - Attract clips' character cards (ライザーガント logo + printed "RISER GANT") kept as logo art (D5), survey row added.
- **Session 2026-11-15 (h):**
  - **OBJ lettering done** (`tools/objtext.py`, rows `gfx/obj.tsv`, `tests/test_objtext.py`, docs/re/graphics.md
    §OBJ redraw pipeline): top menu New Game / Continue (17[601] + white backing frames), name plates Riser Glen /
    Kageri / Gant (17[545] char select, 17[630] continue, 17[646] save cards + battle wins), save-card mode badges
    Normal / Hard / Kids / Bonus (17[646] f9-12), Zakoul plates (17[646] f13-15, 17[648], 17[662]), battle hints
    "Mash B!" / "Ⓐ Button: Attack!" (17[633]). Overwrite prompt **Yes / No** = BG tileset 5[0] + map 5[3]
    (`bg5:0:3` rows). **Title** (picture 5[20], `pic5:20` rows): subtitle "Souchaku! Warriors of Earth" over a
    rebuilt star/Earth backdrop, copyright line 1 "© 2004 Justiriser Project / TV Tokyo" (D12).
  - **'aS' parser fixes** (also `tools/sweep.py`): OBJ size = 8*(code+1) (code 0/1/3/7; 32 px OBJs were read as
    64), tile word top nibble = palette bank, one extra tile past the header count. Old sweep renders/verdicts of
    sprites predate this; a re-render of all loaded group-17 sprites (work/qa/gfx/obj/all/) found no other Japanese.
  - Checked in the emulator on the en build (`work/qa/objen/`): top_menu (+ Continue via
    `tools/routes/top_menu_continue.txt`), data_save_slots (cards, badge, Yes/No prompt), continue, char_select,
    attract_battle f1560 (both hints). Bug found and fixed on the way: recycling 5[0] tiles 5[3] doesn't use broke
    the save screen behind the prompt (another layer uses them).
  - Known cosmetic: "Normal" badge text fills the 26 px face edge to edge (ink on the side shade columns).
- **Session 2026-11-15 (g):**
  - **Credits done** (`tools/credits.py`, rows `gfx/credits.tsv`, `tests/test_credits.py`, docs/re/graphics.md
    §Credits): 19[n] = 15-wide rows of 2x2 metatiles (TL, TR, BL, BR); five rolls 700-704 plus the おわり page 705
    ("The End"). Each roll redrawn from blank, tileset padded to its original count and written in place (sizes and
    VRAM layout unchanged). Checked in the emulator on the en build (`work/qa/credits_en`, warp `credits` now 7200
    frames). `tools/credits.py preview` = original | English per roll in `work/qa/gfx/credits/`.
  - Staff names romanized from the kanji (Western order, D1); uncertain readings (no official source found):
    吉岡 基行 Motoyuki Yoshioka, 下道 隆 Takashi Shitamichi, 高宮 成光 Shigemitsu Takamiya, 武馬 佳代 Kayo Buma,
    阿部 徹 Toru Abe, 戸田 篤樹 Atsuki Toda, 北上 一三 Kazumi Kitakami, 牛田 直斗 Naoto Ushida, 森 泰昭 Yasuaki Mori.
    Cast readings (voice actors) are the usual ones. Fix any in `gfx/credits.tsv` (rows keep the kanji in the note).
- **Session 2026-11-15 (f):**
  - **Done** (`gfx/bg.tsv`, checked on the en build in `work/qa/gfxen3/`, sha1 3f2d01ea...): round-2 battle choice 629 / 629:630 / 629:631 (small "Genseishin" / "Genseijuu" + bold "Kenriser" / "Raizeros", prompt "Which will you use?"; warp `battle_choice` f1560), unlock message 651 ("Genseishin Kenriser|is now available!", warp `ending` f2940), stage bar as Kageri 656:626 and Gant 657:627 (warps `status_kageri` / `status_gant` f1500-1740). `gfx/bg_pairs.tsv`: 627->657, 630/631->629, 656/657 never loaded (their own maps pinned tiles: count was over budget until listed).
  - **Checked, nothing to letter**: game over is 656:626 (stage bar, done) + 623 (HP/EN only); 651:652 (art only); battle screens 18[634] + 20[634..637] (sweep: HP/EN, Lv.1 only). 18/20[207..217] are stage-background tilesets (stage_1_1, clear_5_1, ...): scenery fragments, low priority with the group-9 shop signs.
  - **Credits: format not yet understood** (docs/re/graphics.md §Credits): 3 tilesets 18[700..702] in VRAM at once, 20[70x] is a dummy linear map, 19[70x] (`a2`) holds the roll's tile numbers in an unknown layout. Next step there: disassemble the loader 0x0801E1F3 / 0x0801EB07; helpers `tools/cred_roll_render.py W` / `tools/cred_vram_match.py` (VRAM dump `work/qa/credvram`, recreate with the emu.py line in that section's notes: warp `credits` + `tools/lua/bgcnt.lua --var DUMP=3180` on `work/orig.gba`).
- **Session 2026-11-15 (e):**
  - **Done** (`gfx/bg.tsv`, each checked in the emulator on the en build, shots in `work/qa/gfxen/`): points 618 + 618:619 (Clear Points; Action Points / Hit Bonus / Item Points / Total / Grand Total, grid; the game blanks the digit field from x 136, x 128 on the bottom row), status 641 / 641:642 / 641:643 (Status, Riser Glen/Kageri/Gant, Arms / Skill, weapon names right-aligned to x 239; new warps `status_kageri`, `status_gant`), continue legend 632 (Pick / OK), stage map 608 (Stage) + 608:609 (World Map), in-stage bar 655:625 (L+R = Use Skill). HUD 622 / 616 / 617: no Japanese. ひっさつわざ label is now **Skill** (char select too; glossary).
  - **bgtext fixes**: (1) every tileset resource holds **one extra tile past its count**: the game copies it to VRAM and maps show it as slot n0 (the stage bar's L+R "+", likely also the "black squares past the tileset" in earlier notes); `Tileset.extra` keeps it in relocated blobs and pads slot n0 with it (`test_blob_keeps_extra_tile`). (2) **`gfx/bg_pairs.tsv`**: map -> tileset it is really drawn with (20[619] on 18[618] while 18[619] aliases config's 18[620], 20[625] on 18[655], 20[635..637] on 18[634] battle, ...; `-` = no scene loads it). Built from **`work/qa/resall`** (reslog over all 78 scenes; `work/qa/resall_loads.txt` = every 18/20 index loaded). (3) right alignment on the ink edge, ink outside a rect is an error.
  - **Budgets** (`gfx/bg_budget.tsv`): 641 = 444 (the description text canvas starts at VRAM 460: a grown set showed Gant's labels overwritten), 608 = 200 (VRAM 1691-1791 empty on the map).
  - Gotcha: the Edit tool drops a trailing tab at the end of new_string: edit `gfx/bg.tsv` rows with awk to a temp file (or never end new_string on a tab).
- **Session 2026-11-15 (d):**
  - **Which BG screens a scene really loads**: `warp_all.py NAMES --rom work/orig.gba --out work/qa/res --script tools/lua/reslog.lua`; for groups 18/20 the index is **r1** (not id & 0xFF). Logs in `work/qa/res/<scene>/log.txt`. Survey numbers differ: char select = 18/20[600] (+ 20[601] radar, 20[602] name atlas; s0510..599 are the same resources), data = 18[647] + 20[647] save / 20[648] load / 20[649] file-card atlas / 20[650] cursor, points = 618 + 618:619, pause = 633, status = 641 (= 638..640) + 641:644, continue = 632, stage map 608 + 608:609 and 606, HUD 622 + 622:616/617, game over 623 / 656:626, unlock 651 + 651:652 (ending), credits 18[700..702] + 20[700..702], boot-time 18[655]/20[625], 18[625]/20[628].
  - **Done this session** (`gfx/bg.tsv`, all checked in the emulator on the en build): data save/load (header, legend OK/Pick/Back/Erase, Erase Data buttons, file cards Stage / All Clear / Data is damaged: `work/qa/gfxen/data_*`), character select (header, legend, Arms / Special, the six weapon/special names, cycled through all three: `work/qa/gfx/cs_cycle`), pause (Resume Game / Give Up / Status). Glossary: the six weapon/special names.
  - **bgtext changes**: the free-tile pool now spans every pending screen of a tileset (an atlas map frees tiles an earlier screen needs), canvas pixels come from the untouched tileset, padding only to still-referenced past-the-end slots (Counter keys with count 0 used to pad), an identical tile in any fitting bank is reused, `gfx/bg_budget.tsv` columns = index, max tiles or '-', spare tiles or '-', note. `tests/test_bgtext.py` skips indices that alias a redrawn screen's resources.
  - **Budgets** (`gfx/bg_budget.tsv`, docs/re/graphics.md): `tools/bgvram.py` stops at the 512-tile char-block edge, but BG tile numbers run on across blocks: measure with a VRAM dump (`bgcnt.lua --var DUMP=F`) + `watch.lua` on the range after the set (who writes it, and when relative to the screen load). 18[647] = 704 (VRAM 1024 up to screen block 0xD800), 18[600] = 496 (VRAM 489-511 stale).
  - Atlas copies: char select copies atlas 20[602] cells 1-11 to screen cells 19-29 (atlas col 0 is not shown), the OBJ name plate covers x 40-105 (hence "Arms").
  - Still Japanese on these screens, all **OBJ** (need the 'aS' writer): character name plates (ライザーグレン etc., also on the save cards), the save-card mode badge (ノーマルモード), the overwrite prompt's はい / いいえ buttons.
- **Session 2026-11-15 (c):**
  - **VRAM tile budget solved for mode select and config**: every BG tileset is copied to VRAM as one run at tile 16 with 0 tiles of slack (other layers follow at 311 / 342). New align flag **`g` (grid)** in `gfx/bg.tsv`: one glyph per 8 px cell, so repeated letters share tiles (config 383 -> 326 tiles = budget); mode buttons now read Kids / Normal / Hard / Bonus (D11). `bgtext.py count ROM [TSV]` measures drafts against the budget. Rows are back in `gfx/bg.tsv` (`gfx/bg_pending.tsv` gone); cold boot (`work/qa/smoke/final.png`) and warps `options` / `mode_kids` / `mode_hard` look right (`work/qa/gfx/budget_check.png`). Config "Weapon Select" -> "Swap Weapon" (button pill sprites start at x 136), 1E9F76 -> "This is the easy mode.".
  - **4-mode screen** (18[659] + overlay 20[660], shown when F4A > 1, code 0x08027776): new warp `mode_bonus` (76 scenes; `work/states/` lacks its state until the next `warp_all.py --states`). It exposed past-the-end map slots showing leftover VRAM (Bonus button corner went black): `bgtext.redraw` now fills such cells from the left neighbour (docs/re/graphics.md). Zoomed checks `work/qa/gfx/hl_zoom.png`, `hl_z2.png`.
  - Earlier (b): tileset parser fix (`sweep.p70_parse`, tiles one byte after the banks for even counts too), `bgtext.py` refuses any tileset past its budget (`gfx/bg_budget.tsv`, default = original count).
  - Visual QA of the 31 message-viewer runs done: sheets `sheet.py RUN --from 2200 --crop 0,0,240,64 --changed 0.01 --cols 3 --max 30` (131 sheets), manifest `work/qa/manifest.tsv` (first dir `work/qa/cover`, glob `*sheet*.png`, build f2d9fd1f), read-only Codex verdicts through **`tools/qa_codex.py`** (brief `docs/visual-qa-brief.md`; `work/qa/verdicts/cx_chunk_*.tsv`): 124 ok, 7 "one-word last line" = the script's deliberate `{n}` breaks mirroring the Japanese (`recheck_1.tsv`), `qa_gate.py check` exit 0 on that build. The build has since changed (graphics rows out), so the final re-tour must re-run them (`qa_gate.py init ... --build`).
  - `tests/test_waivers.py`: `docs/text_unshown.tsv` must equal `tools/gen_waivers.py` output (so check.py runs it).
- **Phase 8 so far (2026-11-15):**
  - **Text coverage gate passes** (build f2d9fd1f): `textcover.py work/qa/cover build/strings.tsv --waive docs/text_unshown.tsv --mask 0x1FFFFFF` -> 621 shown, 170 waived, 0 failing. `work/qa/cover/` = `tour` (75 scenes) + `tour_adv` (59 story entries, `warp.lua ADVANCE=40`, gained only 3: story text is mid-stage/boss events) + `msgview/` (31 runs, **message viewer**: `tools/msgview_run.py work/qa/cover [--tables sNN,..]` swaps stage 1-1's 32 intro text commands for unread messages, `tools/lua/msgview.lua`; docs/re/scenes.md §Event scripts and the message viewer). Waivers generated by `tools/gen_waivers.py` (nontext/debug/placeholder rows + s00/s04/s05/s06, whose master entries no loader call read: `tools/lua/masterread.lua`). Per-table view: `tools/cover_tables.py work/qa/cover`. Probes `tools/lua/evlog.lua` (event loads: r1 = entry slot), warp `EVSLOT`/`EVSCRIPT` (forcing mid-stage slots shows no dialogue). Rebuilds keep strings.tsv addresses only while the block layout is unchanged: re-run the tour + msgview after any text change before release.
  - Earlier text coverage notes: `build.py` writes `build/strings.tsv` (id, CPU address in the relocated block). Full 75-scene tour on build 69ae6a43 (text only) with `$SKILL/scripts/lua/probes/textcover.lua --var "RANGES='8D23570-8D3BA00'"` -> `work/qa/tour` (states regenerated in `work/states/`). `textcover.py work/qa/tour build/strings.tsv --mask 0x1FFFFFF`: **199/791 shown** (`work/qa/cover.txt`). Never read: s00 38/38, s04 12/12, s05 39/39, s06 26/26 (the guessed-budget tables: likely unused, find a reader or waive with a reason in `docs/text_unshown.tsv`), s03 37/46; story tables mostly unread because warps stop on an event's first lines (e.g. s26 65/76, s31 43/53, s35 41/43, s16 41/53).
  - Graphics: `tools/bgtext.py` + `gfx/bg.tsv` (BG label redraw; see `docs/re/graphics.md` §BG redraw pipeline), `tests/test_bgtext.py`. Mode select (653, overlay 653:654, 4-mode 659 + 659:660) and config (620) in, within budget (session (c)).
- **Done:**
  - Step 0: MesenCE 2.2.1 + BIOS in `tools/mesen/`, guard hook proven, pre-commit gate proven, `tools/check.py`, `rom.sha1`, boot route, AGENTS.md, decisions D1-D7.
  - Phase 1 (`docs/re/text.md`, `docs/re/graphics.md`): custom 8-bit encoding, font 0x2CBC34, master table 0x1E90C0 -> sub-tables -> messages in 0x1E90C0-0x1FE9F0; free space candidate 0xD2356C-0xF00000; resource table 0xD226AC + Konami LZ (`tools/res.py`); sprite/BG formats; full graphics-text survey.
  - Phase 2 (`docs/re/scenes.md`): scene machine, progress block, player struct. Debug tool `tools/debug/warp.lua` + 75-entry scene list (`tools/debug/gen_scenes.py`), every entry reached from a cold boot with an `ok` verdict (`work/qa/warp/verdicts.tsv`). Cheats `@clear[N]`, `@subN`, `@pause`, `@hold`, `GOD=1`; `tools/debug/warp_all.py` (parallel, `--states`).
  - Phase 3 (identity build): `tools/textblock.py` unpacks the script block into a model (master table -> 40 sub-tables -> 794 messages, shared tails and end slots kept) and packs it at any 4-aligned base; `build.py` checks the dump, unpacks, repacks in place and writes `build/justirisers_en.gba`; `--verify` requires it byte-identical (it is). `tools/klz.py`: Python decoder for the game's LZ (matches the ROM's own code under unicorn on all 77 blocks) and an optimal-parse compressor (lossless on all 77, every block smaller than the original). Tests `tests/test_identity.py` (text repack, relocation, build == dump, LZ sample); full LZ check `python -X utf8 tools/klz.py test work/orig.gba` (~80 s).
  - Phase 4 (`docs/re/text.md` §Control codes, §Script dump): control codes verified by disassembly (preprocessor 0x08007568, renderer 0x08007830; no jump codes in the text, so messages can grow). `tbl/jp.tbl` names every glyph the script uses (61 kanji read in context). Message split made token-aware: **791** messages, not 794. `tools/script.py dump` -> `script/sNN_ADDR.tsv` (id, slots, jp, en, notes); `tests/test_script.py`: roundtrip, full block coverage, every glyph named, dump == ROM. No orphan messages; only resource word 0xD226B4 points at the block; no text in this encoding outside it. Found the per-code **width table at ROM 0x8C00FA** (codes 0-0x1FF) and the renderer's own auto-wrap.
  - Phase 5 so far (`docs/re/text.md` §English text engine, §Windows): VWF through the game's own width tables. `font/en.txt` + `font/en_small.txt` (game's Latin glyphs normalized, new punctuation in cells 0x160-0x176, new small lowercase), `tools/font.py`; widths forced even (rasterizer breaks at odd x); `tools/asmpatch.py` hooks the canvas->VRAM column copy 0x080083C4 (narrow glyphs lost tile columns), hook code at 0x1E90C0; block relocated to 0xD23570, group-2 word repointed (`tools/insert.py`); `build.py --marker` / `--qa ID=TEXT`; torture line (all glyphs, both fonts) verified in stage 1-1; `tools/notes.py` filled notes (nontext/debug/placeholder/column widths); `tools/lua/winlog.lua` + `tools/winlog.py` (box variants), `tools/lua/romtrap.lua` (no stray reads so far); `tests/test_insert.py`. The font pixel layout is pair-swapped (fontsheet.py fixed).
  - Phase 5 finished: marker tour of all 75 scenes (`work/qa/marker`), every script box shows its marker id; romtrap: no read of the free space or the old block. **Width gate** (`docs/re/text.md` §Windows, `tbl/windows.json`, per-id geometry `tbl/windows_ids.tsv`, `tests/test_windows.py`): dialogue 224 px x 2 lines/page (216 px on a page's last line: page-wait arrow), name tag 64 px small font, mode/weapon descriptions 224 px x 2, next-stage menu 160 px (incl. 2-space cursor indent), save status 160 px x 1, prompt 144 px x 2, B-button hint 224 px x 2. The renderer character-wraps at the edge, so nothing may exceed its budget. Helpers `tools/inkrows.py` (ink extents per text row), `tools/msgscenes.py` (scene -> ids drawn).
  - Phase 6 (translate): `glossary.md` (rulings, voices, terms; lint-enforced), `docs/synopsis.md`, decisions D8 (romanization of non-official names) and D9 (Armor Gunner tag). Batches in `work/tr/b01-b11*.tsv` (gitignored scratch; `script/*.tsv` `en` is the source of truth), merged by `tools/merge_en.py` (refuses on any lint error). `tools/textlint.py` = the gate (`--fit "TEXT"` dry run): control codes, ASCII/encodable, speaker tag = glossary + 64 px small font, dialogue 2 lines x 224 px (page's last line 216), logged/assigned window variants (`tbl/windows.json` "assigned"), column rows within the Japanese width, never-drawn rows within the widest Japanese line of their sub-table, glossary terms; `tests/test_textlint.py` makes it gate every commit. Column rows (s00 names, s05 stage list) use `{fill}`, which `insert.fill_pads()` turns into spacer cells at build time. `script.write_tsv` now quotechar-free and atomic (a `"` truncated a file once). Review: `codex exec` read-only over `tools/pairs.py` output, report `docs/review/phase6_codex.md`: 0 Critical, 2 Important (1E9581 light bolts, 1EC24A revival) fixed, Minors in `docs/polish.md` (2 open).
  - Phase 6 harness review fixes: textlint enforces the glossary Avoid column (`[avoid]`) and a `## Honorifics` table (直也さん -> Naoya-san, `[honorific]`); glossary JP terms match whole kana/kanji runs only (`has_term`); 11 s00 enemy names added to the glossary; review record follow-up (`docs/review/phase6_codex.md`, ok after fixes); save-status "Cleared to" added to `docs/polish.md`.
  - Phase 7 (`references/pipeline.md` §Checks): **name-tag window 8 -> 9 tiles (72 px)** (`asmpatch.py`: init_window 0x08006C3C calls at 0x08021140-0x080211D6, right tags x 20 -> 19), "Armor Gunner" verified on both sides (`work/qa/tagw/zoom_*.png`), waiver dropped. **`tools/romcheck.py`**, run by every `build.py` and by `tests/test_romcheck.py` (own in-memory builds, negative cases for each rule): write log `build/writes.txt` through `tools/romdiff.py --writes` (logged right after each build step, orig bytes from the clean dump), every write inside `tbl/allowed.txt`, group-2 word -> relocated block that unpacks to the packed model (`textblock.unpack(d, base)`), every replaced text decodes back from the ROM, no aligned pointer in the original left on old-block structures (only 0xD226B8 = group 3 at the block end, allowed), no Thumb branch into a multi-halfword patch, no kana/kanji in any built message except nontext/debug/placeholder rows (the skill's `jp_left.py` assumes NUL-terminated strings; this game ends messages with 0x1F). `asmpatch.apply` checks patch sites against the clean original. textlint rules `missing`, `blanks`, `stub` (dialogue only; 3 lines rebalanced: 1F02C7, 1F4D9B, 1F970A).
  - Phase 7 harness review fixes: tools/tests read the dump through `check_rom.original()` (rom.sha1-checked; `work/orig.gba` no longer needed), tests skip only without `rom/`, and `tools/check.py` fails on any skip while `rom/` exists; textlint prints "N rows on guessed (Japanese-width) budgets" (107: s00 38, s03 3, s04 3, s05 38, s06 25; `tbl/windows.json` defaults `guess`), the CLI runs the `missing` rule, per-id `lines` override (1E9EE8: 3) in `tbl/windows.json`; `build.py` runs textlint on en builds; romcheck reader scan 2-aligned with masked flags + mirrors (15 data hits allowlisted); D9 outcome, D10 (placeholders -> "Error code" / "In development"); jp_left gotcha.
- **Next (phase 8, in this order):** (1) done (text coverage, msgview visual QA, waiver check). (2) BG lettering done for mode select (4-mode too), config, data save/load, char select, pause (session (d)). **Next, in this order** (screen numbers = the resources the scene loads, session (d) list; renders of the originals in `work/qa/gfx/s2/`): points, status, continue, stage map, HUD, stage bar done (session (e)); game over, unlock, battle choice, battle screens done/checked (session (f)); credits 700-705 done (session (g)); OBJ sprites, Yes/No, title subtitle + copyright done (session (h)). **Next (session (j) state)**: (a), (b) done. (c) `bash tools/final_tour.sh` on the
current build (started in session (j)), `textcover.py` (0 failing), `qa_gate.py init` both manifests with `--build`
(`work/qa/manifest.tsv` over work/qa/final `*sheet*.png`, `work/qa/final/gfx/manifest.tsv` over the gfx shots), and
Codex verdicts on all chunks (`tools/qa_codex.py --jobs 2`), until `qa_gate.py check` exits 0 on both; then phase 8 is
done. Older wording of step (3): the final re-tour (all 78 warps on the current build, `--jobs 2`), text coverage again (`textcover.py`, addresses change with every text change), `qa_gate.py init` on the new sheets + read-only Codex verdicts (`tools/qa_codex.py`), `inkbox.py` on choice/centred boxes, then a zoomed cold-boot shot per graphics row (gfx/bg.tsv, gfx/credits.tsv, gfx/obj.tsv) for the phase-8 done-when. Optional: group-9 shop signs. Earlier wording of this step: redraw the remaining BG rows (use grid `g` lettering wherever a screen's budget is tight; `bgtext.py count` before building) of the survey with `bgtext.py` (config s0620, data load/save s0642-47, stage map s0607/17/18, char select s0510 + s0238-44, HUD hint s0625-27, pause s0633/58, status s0638/68/69, unlock s0629/48-51, credits s0675/s0701-05, title copyright); check each screen's overlay pairs with `tools/lua/reslog.lua`. OBJ 'aS' sprites (top menu はじめから/つづきから 17.0601, name plates 17.0545/0630/0646, controls 17.0633, continue) need an 'aS' writer (`tools/sweep.py as_parse` is the parser). Title subtitle 装着!地球の戦士たち is in 'fp' group 9/10 (LZ: `tools/klz.py` compressor ready). (3) Re-tour on the final build, `qa_gate.py init/todo`, codex read-only verdicts (`tools/review_pages.sh`), `inkbox.py` on choice/centred boxes. Earlier phase 8 notes: (`references/emulator-qa.md`, `references/graphics.md`): routes/sheets through changed scenes with a read-only visual-QA verdict per sheet (`qa_gate.py check`), graphics-text rows English in zoomed shots (chapter cards, game over, credits), `inkbox.py` on choice/centred menus, `textcover.py`. Never-drawn rows to place there: 1E9B98 (`{var}/{var}` counter, width pinned by `{fill}`), s00 enemy names and s05 stage-clear list (`{fill}` columns), s06 mission text (budget guessed: widest Japanese line, 156 px), yes/no 1E9B69. Before phase 9: write `docs/style-reference.md` (phase 6 review Minor 3: roll calls 1EBD45/1EBD75/1EBDA6, Glen vs Gant 1EC0AA/1EC0C2 and 1EC170/1EC19A, revived Zauras 1F8302, corrected Gardias 1F6BB7). When the first fit/polish agent is dispatched: `docs/translator-brief.md` from `$SKILL/assets/translator-brief.md` (Minor 4; phase 6 used no translator agents, the controller translated all 725 rows).
- **Open questions (non-blocking):**
  - s00 (enemy names), s05 (stage-clear list), s06 (mission / failure text) and the yes/no 1E9B69 were never drawn in the 75 scenes: maybe unused. Translate them within the Japanese width; phase 8 text coverage decides.
  - Post-clear events of 2-4, 3-4 and 4-1 hang the game after a forced clear (CPU loop in IWRAM 0x030011C8-0x0300121C; likely waiting on the stage boss). Their entries prove the event start (4-1 also its dialogue). 2-4, 3-4 and 4-4 then freeze in the summon (scene 5). If phase 8 text coverage finds their later lines unreached, build a boss-fight route (GOD + reach the boss).
  - Event scripts 3.26-3.29 and 3.32-3.39 are never run by the game's own flow (3.26 shown by `event_3_26`). Check in phase 4/8 whether their text is unique before translating it as live text.
  - Credits (scene 11) have no natural entry found; the `credits` entry forces scene 11.
  - Staff-name romanizations in `gfx/credits.tsv` are readings from the kanji (session (g) list): the owner may
    want to check them against an official source.
  - Unlock message (BG s0629, scene 5 sub 16 when F4A != 0) not yet seen; s0648-s0651 ("Congratulations") near scene 6/7 save code not yet seen. Unknown BG screens s0670-s0673 (HUD code, scene 4) and s0207-s0216 still unplaced: check against stage/battle shots in phase 8.
  - Graphics writers exist for group 18/20 (bgtext.py, relocating), 18/19 rolls (credits.py, in place), 'aS' and group-5 BG/picture (objtext.py, in place, same tile count). No redraw so far needed a container to grow.
- **Open bugs:** none.
- **Waiting on the user:** none.

Savestates (not in git; recreate): `python -X utf8 tools/debug/warp_all.py --rom work/orig.gba --states` writes `work/states/<scene>.mss` for every entry (after phase 5 use the build ROM, default `--rom`). Run with `--jobs 3` or fewer: more has hit the machine's memory limit twice; on 2026-11-15 even `--jobs 3` (with other agents' emulators running) got the tour killed for low memory after 47 scenes, so prefer `--jobs 2`.
