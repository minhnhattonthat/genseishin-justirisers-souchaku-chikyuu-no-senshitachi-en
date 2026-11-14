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
| 14, 15 | 0x2E81C0, 0x30AA74 | 520, 6209 | 'ca' / 'aS' animation + sprite data (gameplay) |
| 16-20 | 0x525D60-0x740360 | 93-145 each | 'aA'/'aS'/`00 70 31 00` sprite containers (menus, map, character select, dialogue box) |
| 21 | 0x20744C | 71 | small records (guess) |
| 22 | 0x75B128 | 80 | 'ca' containers, 9 MB (largest group; gameplay; guess: animation/streams) |

**'fp' container** (verified on 9.0 and 10.0): `'fp' 01 02`, u16 count, then count 10-byte entries
`type u8, flags u8, unit u16, count u16, offset u32` (offset from 'fp'). unit*count = the entry's size; unit 0x20 =
4bpp tiles, 0x40 = 8bpp tiles, 2 = palette/map halfwords. Type codes differ between containers.

**'aS' / 'aA' / 'ca' sprite containers**: not decoded yet. 'aS' looks like `'aS' u8 u8 u16 u16 u16 ncolours` +
RGB555 palette + pixel data (guess from 11.0, 15.2, 17.1).

## Compression (verified: run on the ROM's own code)

- **Konami flag-bit LZ** at **0x08001CD4** (r0 = dst, r1 = src). `tools/res.py` runs it under unicorn on the ROM's
  code, so decompression is exact; a block counts as LZ when the run returns and consumes the resource's size
  (groups 4 and 9 only). A recompressor is still needed for phase 5+ (or store edited blocks uncompressed and
  repoint: the loader decides by caller, not by a header, so check the caller's flag before doing that).
- BIOS LZ77 hits from `tools/gbacomp.py scan` (text.md) are mostly false positives.

## Static sweep

`python -X utf8 tools/sweep.py work/orig.gba work/sweep/all --groups 1,4,5,9,10,11` renders every distinct resource
(decompressed, 'fp' entries from their own offsets, gba8 for unit 0x40) into labelled pages + `index.tsv`; skipped
resources are printed with the reason (tiny or no tile entry). Review verdicts: `work/sweep/review/` (Codex,
read-only). Groups 14-22 (sprite containers) still need a decoder before they can be swept; until then the tour
below covers their on-screen text.

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
| Top menu | ◀ はじめから / つづきから / OPTION ▶ (OPTION already English) | OBJ graphic | translate はじめから, つづきから |
| Config (OPTION) | header コンフィグ | OBJ graphic | translate |
| Config | help 「こうもく を えらんで ボタンを おしてください」, labels こうげき / ジャンプ / ガード / こうげき せんたく / せってい を もどす / けってい | font-like, **not in the script encoding** | find source (graphic or second text system) |
| Data load (つづきから) | header データロード, legend Ⓐ=けってい ✚=せんたく Ⓑ=もどる ✚=しょうきょ, button データをけす | OBJ graphic | translate; "File01", "NO DATA" already English |
| Mode select | 「モードを えらんでください」 header, buttons キッズモード / ノーマルモード / ハードモード | graphic (not in text) | translate |
| Mode select | description 「ふつうの モードです」 etc. | text (0x1E9F5D) | script |
| Story | dialogue box frame | OBJ, ROM 0x5EAC78 (group 17) | no text |
| Story | speaker name plate (e.g. ザウラス, bottom-right of the box) | OBJ graphic | translate (every speaker) |
| Story | vertical narration 「それから 四五〇〇年…」 | BG | check: script or graphic |
| Story | area card 「エリア1」 + 「『ジャスティライザー とうじょう!』」 | BG over still | check source; one per area |
| Stage map | header ぜんたいマップ, banner ステージ 1-1, counters | OBJ graphic | translate |
| Character select | header キャラクターセレクト, name ライザーグレン, ぶき / グレンリード, ひっさつわざ / レイジング フレイム, legend ✚=せんたく Ⓐ=けってい; STR/DEF/SPD/HP/EN English | OBJ graphic | translate (each character) |
| Gameplay HUD | "L+R = ひっさつわざをつかう", ×05 / ×00 counters, HP/EN | OBJ graphic | translate the hint |
| Gameplay | "START!" banner | OBJ | keep (English) |
| Pause (start in gameplay) | PAUSE (English); ゲームを つづける / リタイア / ステータス | OBJ/BG graphic (not in text, SJIS or UTF-16) | translate |
| Stage backgrounds | shop signs with small Japanese lettering (sweep: 9.0008, 9.0021, 9.0022, 9.0024, 9.0030, 9.0036, 9.0037; "CRASH" sign 9.0003 English) | BG, group 9 LZ | decide per sign (scenery; low priority) |
| Boot/title logos | 5.0019 ジャスティライザー logo art, 5.0000 stylised lettering | group 5 | keep logo (D5) |

Codex sweep verdict on groups 1, 4, 5, 9, 10, 11 (`work/sweep/review/out_*.txt`): Japanese only in the logo
resources of group 5 and the shop signs above; **no menu labels there**, so the menu, config, pause, map and
character-select labels are in the OBJ sprite groups 16-20 ('aS' containers). Dialogue box = resource 17.606
(ROM 0x5EABA0, 'aS'); its tiles start at +0xD8, DMA'd raw to OBJ VRAM.
| Not yet seen | pause menu, game over, continue, stage clear / results, areas 2+, boss names, ending, credits | | reach with the phase-2 debug tool and add rows |
