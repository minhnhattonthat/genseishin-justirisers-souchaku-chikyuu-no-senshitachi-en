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
u16 y | hcode<<12) with 12-bit signed x/y and size 8<<code, then ntiles 4bpp tiles in 1D OBJ mapping (lower OBJ
number on top). **'AS'** = same with a 256-colour palette and 8bpp tiles (tile numbers in 64-byte units).
Parser: `tools/sweep.py as_parse`.

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
| Top menu | ◀ はじめから / つづきから / OPTION ▶ (OPTION already English) | OBJ 'aS' 17.0601 (with PUSH START) | translate はじめから, つづきから |
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
