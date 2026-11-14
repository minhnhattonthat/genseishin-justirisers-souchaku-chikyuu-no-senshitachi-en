# Graphics: resources, compression, graphics-text survey

## Resource table (verified: loader disassembly + `tools/res.py` enumerates every group without overlap errors)

- Loader **0x080202E8** (r0 = id + flags, r1 = sub-index). Group = `(id >> 8) & 0x3F`, index = `id & 0xFF`
  (bit 15 set) or r1 (bit 15 clear; bit 14 picks u32 vs u16 entries). Table of group pointers at ROM **0xD226AC**
  (groups 1-23 valid; the words after group 23 are unrelated data).
- Each group: array of u32 **self-relative** offsets; length = first offset / 4 (group 8: u16 self-relative).
- `tools/lua/reslog.lua` logs every loader call (id, r1, caller) with its first frame: which screen loads what.

| Group | ROM | Distinct | Content (verified by the tour log / sweep render unless marked guess) |
|---|---|---|---|
| 1 | 0x1D0710 | 15 | small tables (guess) |
| 2 | 0x1E90C4 | 41 | script sub-tables (= text master table + 4, see text.md) |
| 3 | 0x1FE9F0 | 34 | per-scene data, loaded with the story (guess) |
| 4 | 0x2185FC | 45 | **Konami-LZ**; story-intro stills (castle, ship, Earth), loaded in the intro |
| 5 | 0x2BCAE8 | 11 | mixed headers (`00 70 31 00` / 'aS'), boot logos (loaded at frame 0) |
| 6 | 0x2CBC2C | 2 | the 16x16 font (text.md) |
| 7, 8, 12, 13 | | small | tables (guess) |
| 9 | 0x03D9DC | 97 | **Konami-LZ 'fp' containers**: stage/title backgrounds (8bpp and 4bpp) |
| 10 | 0x112F78 | 162 | raw 'fp' containers (2-byte prefix): screen layouts (title, menus, map) |
| 11 | 0x20B374 | 18 | 'aS' sprite containers (gameplay) |
| 14 | 0x2E81C0 | 520 | 'ca' animation command scripts (no tiles) |
| 15 | 0x30AA74 | 6209 | small records, 5 'aS' sprite containers |
| 16 | 0x525D60 | 127 | 'aA' animation scripts (no tiles) |
| 17 | 0x54F700.. | 108 | **'aS' / 'AS' OBJ sprite containers**: title menu, name plates, dialogue box, banners, continue |
| 18 | 0x5FE9B0.. | 127 | **BG tilesets** (`00 70|50 31 nn`), paired with the maps of group 20 by index |
| 19 | 0x71DB44.. | 93 | 'a2' u16 n + n 9-byte records (not a map; guess: OBJ placements) |
| 20 | 0x740360.. | 145 | **BG maps** 'B2'/'C1' w h + w*h screen entries; 20[i] is drawn with tileset 18[i] |
| 21 | 0x20744C | 71 | small records (guess) |
| 22 | 0x75B128 | 80 | 'ca' animation scripts; its last entry (22.1000) is a sentinel, not a resource: 0x75F3C0-0xD226AC is PCM sound (m4a wave headers, 8-bit samples), no graphics |

Groups 17-20 are indexed by r1 (bit 15 of the id clear), 1001 entries each, sharing one duplicate pattern; a screen
loads 18[n] + 20[n] (+ 19[n]), e.g. mode select = n 0x28D (tour log `f1671`).

**'fp' container** (verified on 9.0 and 10.0): `'fp' 01 02`, u16 count, then count 10-byte entries
`type u8, flags u8, unit u16, count u16, offset u32` (offset from 'fp'). unit*count = the entry's size; unit 0x20 =
4bpp tiles, 0x40 = 8bpp tiles, 2 = palette/map halfwords. Type codes differ between containers.

**'aS' sprite container** (verified: 17.606 dialogue box, tiles at +0xD8 = OBJ VRAM DMA source; every group-17
container parses, `tests/test_containers.py`): `'aS'`, u8 extra palettes, u8 nframes-1, u16 nobjs-1, u16 ntiles,
u16 ?, (extra+1)*16 colours, nframes x (u16 count-1, u16 first_obj), nobjs x (u16 tile, u16 x | wcode<<12,
u16 y | hcode<<12) with 12-bit signed x/y, then ntiles 4bpp tiles in 1D OBJ mapping (lower OBJ number on top).
**'AS'** = same with a 256-colour palette and 8bpp tiles (tile numbers in 64-byte units).
Parser: `tools/sweep.py as_parse`, `tools/objtext.py Sprite`. Corrected 2026-11-15 (h):
- **OBJ size = 8 * (code + 1)**, code = bits 12-14 (only 0/1/3/7 occur = 8/16/32/64 px). The old reading
  `8 << (code & 3)` drew every 32 px OBJ as 64, so earlier sweep renders of sprites (and their review verdicts) show
  scrambled lettering.
- The tile word's **top nibble is the OBJ's palette bank** (tile = low 10 bits); colour variants of one label (red
  Glen / blue Kageri / green Gant) mostly use different indices of one bank, the save-card badges different banks.
- **One extra tile**: OBJs reach exactly one tile past the header count in nearly every container, and its bytes
  follow (like the BG tilesets' extra tile): 17[648] frame 2's last OBJ is that tile. `Sprite` reads it.

## OBJ redraw pipeline (phase 8, `tools/objtext.py` + `gfx/obj.tsv`, `tests/test_objtext.py`)

- Rows: sprite, frame, rect (relative to the frame's bounding box), text, font, ink bands, shadow (`oN,M,..` =
  outline N then 1 px rings M..), bg (`N` clear, `N:a,b` recolour indices a, b to N, `-` keep), align, note. Text is
  drawn with `bgtext.draw` on the frame's index canvas and written back into every tile the rect covers (in place,
  same size, frame/OBJ tables untouched). Ink where no OBJ covers the frame is an error (17[545] plates have no OBJ
  on two 8x8 corners); outline/ring pixels there are dropped. `glow:F` rows regenerate the top menu's white backing
  frame from text frame F. `objtext.py preview` = original | English per frame (`work/qa/gfx/obj/obj_preview.png`),
  `render N [--frames ..] [--bank B]`, `info N`.
- Done (2026-11-15 (h)): top menu 17[601] (New Game / Continue + backings), name plates 17[545] (char select:
  non-bold, 64 px usable), 17[630] (continue), 17[646] frames 0-2 (save cards, battle wins), save-card mode badges
  17[646] 9-12 (Normal / Hard / Kids / Bonus, D11), Zakoul plates 17[646] 13-15, 17[648], 17[662], battle hints
  17[633] (Mash B!, Ⓐ Button: Attack!; frames 44/45 share the tiles).
- **はい/いいえ** of the overwrite prompt are **BG**: tileset **5[0]** + map **5[3]** (16x4: both buttons, both
  highlight states), handled as `bg5:0:3` rows. Other layers draw with 5[0] too: recycling tiles 5[3] doesn't use
  (tile 0 among them) turned the save screen behind the prompt into a tile pattern, so only the touched cells' old
  tiles are recycled.
- Checked on the en build (`work/qa/objen/`): top_menu, data_save_slots (cards + prompt), continue, char_select,
  attract_battle f1560 (both hints).

**BG tileset (group 18)** (verified against a VRAM dump of mode select): `00`, mode (0x70 4bpp / 0x50 8bpp), `31`,
u8 extra palettes, u16 ntiles, palette ((extra+1)*16 colours, or 256), **ntiles bytes of per-tile palette bank**
(padded to even; values are VRAM banks, palettes load from the lowest), then the tiles. Tile 0 of 18[0x28D] lands at
VRAM tile 16. Map entries carry tile numbers relative to the tileset and palette bits 0; the game adds the per-tile
bank. Parser: `tools/sweep.py p70_parse`; renderer `tools/bgscreens.py`.

## Compression (verified: run on the ROM's own code)

- **Konami flag-bit LZ** at **0x08001CD4** (r0 = dst, r1 = src). `tools/res.py` runs it under unicorn on the ROM's
  code, so decompression is exact; a block counts as LZ when the run returns and consumes the resource's size
  (groups 4 and 9 only, 77 blocks).
- **Format** (read off the disassembly; `tools/klz.py`, verified: its Python decompressor gives the same bytes and
  consumed length as the ROM's code under unicorn on all 77 blocks): flag bits MSB first, a flag byte fetched
  between data bytes when the previous is used up. `1` = literal byte; `0 0 a b` + byte o = copy 2..5 from
  dst-256+o; `0 1` + u16 BE v = offset (v>>3)-8192, length (v&7)+2 (3..9), or v&7 == 0: byte c, c == 0 ends,
  else length c+1 (2..256). A flag byte 0xFF fetched for a type bit is a fast path for 8 literals (same result).
- **Compressor** `klz.compress` (optimal parse): lossless on all 77 blocks and every output is smaller than the
  original (1,124,052 vs 1,153,905 bytes in total), so a redrawn LZ graphic can usually go back in place.
  `python -X utf8 tools/klz.py test work/orig.gba` (~80 s) runs the full check.
- BIOS LZ77 hits from `tools/gbacomp.py scan` (text.md) are mostly false positives.

## Static sweep

`python -X utf8 tools/sweep.py work/orig.gba work/sweep/all --groups 1,4,5,9,10,11` renders every distinct resource
(decompressed, 'fp' entries from their own offsets, gba8 for unit 0x40) into labelled pages + `index.tsv`; skipped
resources are printed with the reason (tiny or no tile entry). Review verdicts: `work/sweep/review/` (Codex,
read-only).

Sprite and BG groups (complete: every tile-bearing group is now swept):
- `python -X utf8 tools/sweep.py work/orig.gba work/sweep/obj --groups 11,15,17,18`: 'aS'/'AS' frames assembled
  from their OBJs (lettering reads as on screen); verdicts `work/sweep/review_obj/out_*.txt`.
- `python -X utf8 tools/bgscreens.py work/orig.gba work/sweep/bg2`: every 18[n]+20[n] screen in its own palettes
  (156 screens); verdicts `work/sweep/review_bg2/found.tsv`.
- Reviews run with `sh tools/review_pages.sh DIR OUT PROMPT [N] [GLOB]` (Codex read-only, parallel chunks).

## BG redraw pipeline (phase 8)

`tools/bgtext.py` + `gfx/bg.tsv` (one row per label: screen, rect, English, font@bank, ink bands, outline/shadow,
bg, align): the en build (`insert.build`) re-encodes each rect's cells, writes changed tilesets/maps to 0xE00000+
and repoints group 18/20 entries (allowed in `tbl/allowed.txt`). `bgtext.py probe ROM N x,y,w,h` lists the
(bank, index) colours of a rect; `preview ROM DIR` writes original | English per screen. `tests/test_bgtext.py`:
no pixel changes outside the rects, other screens on the same tileset unchanged.
- **Overlay maps use another screen's tileset** (`tools/lua/reslog.lua` shows the pairs): mode select loads
  18[653] + 20[653] and 20[654] (highlighted buttons, tiles 230-295 of 18[653], 295 = past its end). Write such
  layers as `T:M` rows; recycling a slot no listed map uses showed as garbage around the highlight. Every known
  pairing (also for maps no row touches) is in `gfx/bg_pairs.tsv` (from `work/qa/resall`: reslog over all 78 warps,
  `warp_all.py --rom work/orig.gba --out work/qa/resall --script tools/lua/reslog.lua --jobs 2`); `-` = never loaded.
- **Each tileset resource holds one extra tile** after its counted tiles (then 0-3 alignment bytes). The loader
  copies it to VRAM after the set and maps use it as slot n0 (stage bar 20[625] on 18[655]: the "+" of L+R).
  `bgtext.Tileset.extra` keeps it; renders still draw slot n0 as a black square.
- **VRAM tile budget (verified: VRAM dumps of mode select and config, `tools/lua/bgcnt.lua --var DUMP=880` +
  `tools/bgvram.py`)**: BG0-2 share char block 0; the screen's tileset lands at VRAM tile 16 as one run and another
  layer's tiles follow at once (18[653]: 16-310, next used 311; 18[620]: 16-341, next used 342). A tileset that
  grows overwrites that layer (dot grid, missing background). `bgtext.py` enforces `gfx/bg_budget.tsv` (default:
  the original count). Japanese glyph tiles are shared between labels, so a tile frees only when every label
  using it is redrawn.
- Tile data starts one byte after the per-tile banks for even and odd counts (`sweep.p70_parse`; even counts
  were read one byte early before 2026-11-15, so older renders of even-count tilesets are shifted).
- **Tile-thrifty lettering** (2026-11-15): align flag `g` puts each glyph in its own 8 px cell (ink centred, the
  line on a cell boundary, every row at the font's full ink height), so repeated letters are the same tile and a
  label costs only its new letters (the game's Latin glyphs are 8 px advance except i l t j I). Kana labels share
  tiles the same way (16 px pitch on the grid); proportional English made every cell unique: config 326 -> 383
  tiles, grid 326. Mode buttons dropped "Mode" (D11): 653 295 -> 295, 659 335 -> 335. VRAM on mode select:
  BG0/BG1 char base 0, tiles 311-317 / 320-359 / 384-427 / 448-491 belong to other layers (text canvases),
  maps at screen blocks 27 and 31. On config the L-button pill sprites start at x 136: labels end by x 135.
  Measure a draft with `bgtext.py count ROM [TSV]` (tiles per changed tileset vs budget, the budget check off).
- **Past-the-end map slots** show VRAM the tileset doesn't own. 653:654 slot 295 = VRAM 311 = tile 55 of 18[654]
  (61 tiles, loaded at VRAM 256, its first 55 tiles equal 653's 240-294). 659:660 slot 335 (Bonus button corner)
  = a leftover tile no group-18 resource holds, overwritten by other data in the English build (black hole /
  garbage). `bgtext.redraw` therefore fills a past-the-end cell inside a rect from the nearest real cell to its
  left (same row) and encodes it as a real tile. The 4-mode screen (F4A > 1, warp `mode_bonus`) is checked.
- **Measuring a budget (2026-11-15 (d))**: `tools/bgvram.py` stops at the tileset's 512-tile char-block edge, but a
  BG's tile numbers (0-1023) run on into the next char blocks, so the real limit is the first live data after the
  set: dump VRAM on the screen (`bgcnt.lua --var DUMP=F`), then `watch.lua --var WATCH_LO=0x06..` over the range
  after the set to see who writes it and whether that happens after the screen's load (live) or before (stale,
  free to overwrite). 18[647] sits at VRAM tile 1024, room to the first screen block 0xD800 (tile 1728): 704.
  18[600] at 16-488, 489-491 stale, live data from 512: 496. Tiles no map of the set uses and no live BG map shows
  can be listed as spares (column 3 of `gfx/bg_budget.tsv`).
- **Tile pool**: all screens of one tileset share one free pool in `bgtext.redraw` (cells of screens processed
  later are re-encoded too, so their tiles are free from the start); pixels are always read from the original tiles.
- **Atlas maps** (data file cards 20[649], char select names 20[602]) hold labels the code copies into the screen
  map: check in the emulator which atlas columns reach the screen (char select: cells 1-11 -> screen 19-29).
- Pilot rows (mode select 653, 653:654, 659, 659:660; config 620) are in `gfx/bg.tsv`, cold-boot checked
  (`work/qa/gfx/budget_check.png`, `work/qa/smoke/final.png`). `bgtext.py ink ROM N rect IDX` prints the ink bands of a rect (where to place the English); bg `cN` clears each
  row to column N's colour (gradient banners). おまけモード = "Bonus Mode".

## Credits (scene 11) format (solved 2026-11-15 (g); writer `tools/credits.py`, rows `gfx/credits.tsv`)

Five rolls, 700..704, each tileset 18[n] + roll 19[n] (16[n] palette-ish, 20[n] is only a linear 0..599 map, `B2`
15x40). Loads (`work/qa/resall/credits/log.txt`): at f804 16[700], 18[700..702] (three tilesets), then per roll 20[n]
+ 19[n] (700 at f804, 701 at f2304, 702 at f3504; callers lr 0801E1D7 / 0801E1F3 / 0801EAED / 0801EB07); 703/704
(own tileset header `00 70 31 00`, 704 on a lighter background, index 14) come after the warp's 3900-frame budget.
- **19[n] layout**: `a2`, u16 599, then **15 x 45 metatiles of 4 u16** (top-left, top-right, bottom-left,
  bottom-right) = a 30 x 90 tile roll (240 x 720 px) read top to bottom. Values are 18[n] tile numbers: 0 =
  transparent (rows 0-9 and the first two cells of row 10: the lead-in, kept), 1 = blank, and slot n0 (one past the
  count) is the resource's extra tile (`Tileset.extra`), used by the last glyph of a roll. (The old "strides 3,1,3,1"
  puzzle: consecutive screen columns alternate between the two words of a metatile row.)
- VRAM (dump `work/qa/credvram`, warp `credits` + `bgcnt.lua --var DUMP=3180`): BG0 only, BG0CNT 0x0204 (char base
  VRAM tile 512, screen block 0x1000). The three tilesets sit back to back: 18[700] at tiles 512-988 (+ extra 989),
  18[701] 990-1206, 18[702] 1208-1644; the code adds each set's VRAM offset to the roll's tile numbers.
- **English**: every roll is redrawn from blank (white ink, index 1, on tile 1's colour), re-tiled with dedup and
  **padded to the original tile count**, so tileset and roll keep their sizes and are written in place (no repoint;
  `tbl/allowed.txt`) and the back-to-back VRAM layout does not move. Budgets: 700 477, 701 217, 702 437, 703 293,
  704 162 tiles; `python -X utf8 tools/credits.py count` / `preview` (original | English per roll). Proportional
  lines fit 700-703 on tile-aligned rows; 704 needs grid lettering. Copyright: "© 2004" of line 1 and all of line 2
  (English already) are `keep` rects. `tests/test_credits.py`.
- **おわり page 705** (after roll 704, ~f6750): same format, 170 metatiles, 24 tiles; here tile 0 is the dark
  background and tile 1 the transparent one (the reverse of the rolls). "The End", 14 tiles.
- Gotcha: roll 700 with its first line on rows 12-13 showed stale copies of that line's tiles in screen columns 0-1
  at the top of the screen (f1050-1200); starting on row 16 (the Japanese starts on 15) it is clean, and
  `credits.py` refuses roll-700 lines above y 137. Rolls 701-703 start on rows 12-14 without it.
- Checked in the emulator on the en build: `work/qa/credits_en` (warp `credits`, 7200 frames).

## Graphics-text survey (tour)

Routes: `tools/routes/boot.txt` + menu routes in `tools/routes/survey_*.txt`; mash-A tour
`emu.py ... --route tools/routes/boot.txt --mash 40 --frames 12000 --script tools/lua/reslog.lua`.
"Text" = found in the script encoding (text.md), so it is translated as text, not graphics.

| Screen | Element | Layer / source | Plan |
|---|---|---|---|
| Boot | Konami logo, Konami Computer Entertainment Japan | BG, group 5 | keep (English) |
| Boot | 超星神シリーズ series logo | BG | keep: official series logo, no English version (D5) |
| Title | 幻星神ジャスティライザー logo + "THE JUSTIRISERS" + 装着!地球の戦士たち subtitle | BG, 'fp' 9.x/10.0 | logo: keep JP (D5); subtitle 装着!地球の戦士たち: translate (graphic) |
| Title | "PUSH START" | BG/OBJ | keep (English) |
| Title | copyright line "©2004 ジャスティライザープロジェクト・テレビ東京" | BG graphic | translate (romanise: Justiriser Project / TV Tokyo) |
| Top menu | ◀ はじめから / つづきから / OPTION ▶ (OPTION already English) | OBJ 'aS' 17.0601 (with PUSH START) | done: New Game / Continue (gfx/obj.tsv) |
| Config (OPTION) | header コンフィグ, help 「こうもく を えらんで ボタンを おしてください」, labels こうげき / ジャンプ / ガード / こうげき せんたく / せってい を もどす / けってい | **BG screen 18/20 #0x26C (s0620)**, not text | translate (BG redraw) |
| Data load/save (つづきから) | header データロード / データセーブ, legend Ⓐ=けってい ✚=せんたく Ⓑ=もどる ✚=しょうきょ, button データをけす, ステージ | BG screens s0642-s0647 | translate; "File", "NO DATA" already English |
| Mode select | 「モードを えらんでください」 header, buttons キッズモード / ノーマルモード / ハードモード | BG screens s0652, s0653, s0659 (verified: VRAM dump) | translate |
| Mode select | description 「ふつうの モードです」 etc. | text (0x1E9F5D) | script |
| Story | dialogue box frame | OBJ, ROM 0x5EAC78 (group 17) | no text |
| Story | speaker name plate (e.g. ザウラス, bottom-right of the box) | OBJ 'aS' 17.0545, 17.0630, 17.0646 (katakana name labels) | translate (every speaker) |
| Story | vertical narration 「それから 四五〇〇年…」 | BG | check: script or graphic |
| Story | area card 「エリア1」 + 「『ジャスティライザー とうじょう!』」 | BG over still | check source; one per area |
| Stage map | header ぜんたいマップ, banner ステージ 1-1, クリアポイント, counters | BG screens s0607, s0617, s0618 | translate |
| Character select | header キャラクターセレクト, ぶき, ひっさつわざ, legend ✚=せんたく Ⓐ=けってい; STR/DEF/SPD/HP/EN English | BG screen s0510 | translate |
| Character select | names ライザーグレン / ライザーカゲリ / ライザーガント / ライゼロス (+ romaji RISER GLEN...), weapon and special names | BG screens s0238-s0244; per-character names: check s0655-s0666 | translate (each character) |
| Gameplay HUD | "L・R = ひっさつわざをつかう", ×05 / ×00 counters, HP/EN | BG screens s0625-s0627 | translate the hint |
| Gameplay | "START!", "CLEAR!", "GAME OVER", "YOU LOSE" banners | OBJ 17.0635-17.0638 | keep (English) |
| Gameplay | control instructions (A/B labels + Japanese) | OBJ 17.0633 | translate |
| Pause (start in gameplay) | PAUSE (English); ゲームを つづける / リタイア / ステータス | BG screens s0633, s0658 | translate |
| Status | ステータス, ぶき, ひっさつわざ, こうげき, enemy names (ザコール), Lv.1-3 | BG screens s0638, s0668, s0669 | translate |
| Continue | コンティニュー | OBJ 17.0646, 17.0648, 17.0662 | translate |
| Unlock message | 「げんせいしん ケンライザーが つかえるように なりました」 + "Congratulations" | BG screens s0629, s0648-s0651 | translate |
| Title variants | 幻星神ジャスティライザー logo | BG screens s0234, s0235, s0246, s0247 | keep logo (D5) |
| Credits | staff roll (ディレクター, サウンド, サブプログラム, キャラクターグラフィック, デバッグ, スペシャルサンクス, names) | BG screens s0675, s0701-s0705 | translate to English (D3) |
| Unknown | ジャスティライザー fragments / small katakana | BG screens s0207-s0216, s0670-s0673 | identify by warp in phase 2 |
| Stage backgrounds | shop signs with small Japanese lettering (sweep: 9.0008, 9.0021, 9.0022, 9.0024, 9.0030, 9.0036, 9.0037; "CRASH" sign 9.0003 English) | BG, group 9 LZ | decide per sign (scenery; low priority) |
| Boot/title logos | 5.0019 ジャスティライザー logo art, 5.0000 stylised lettering | group 5 | keep logo (D5) |

| Not yet seen in-game | game over, stage clear / results, areas 2+, boss names, ending, credits | static rows above | confirm each by warping in phase 2 |

`sNNNN` = BG screen 18[N]+20[N] rendered by `tools/bgscreens.py` (N decimal). Codex sweep verdicts: groups 1-11
(`docs/re/sweep/groups_1_11.tsv`): Japanese only in the group-5 logos and group-9 shop signs; groups 15/17/18
sprites (`docs/re/sweep/obj_sprites.tsv`); BG screens (`docs/re/sweep/bg_screens.tsv`, every JP/EN screen). The
config labels that are not in the script encoding are BG tiles (s0620), so there is no second text system for them.
