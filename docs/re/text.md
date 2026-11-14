# Text engine

Dump: `rom.sha1` (BGJJ, 16 MiB, FLASH512 save, last byte of the ROM is data: no 0xFF padding at the end).
No earlier fan patch found (web search 2026-11-14). No Shift-JIS text in the ROM (`jp_left.py --sjis`: noise only).
Few BIOS-LZ77 blocks (`tools/gbacomp.py scan`: 37 hits, unverified); the script is **not compressed**.

## Encoding (verified)

Single-byte codes, plus 2-byte codes `LL xx` = glyph `LL*0x100 + xx` for lead bytes 0x01-0x0B. Glyph code = font cell.

How verified: hooked the glyph-draw function 0x08007B40 (`tools/lua/execregs.lua --var EXEC_AT=0x08007B40`, state
`work/states/story_intro_3000.mss`, story intro) and logged r2 = code per drawn glyph for the line
「ハデスふっかつを たくらむ / ドクター・ゾラが…」: DE D6 C8 94 82 6A 83 AE 20 7E 6E A8 | D8 BE CE 01 0B 01 10 CD F8 6B 01 11.
Same bytes found in ROM at 0x1EB423.

| Codes | Glyphs | State |
|---|---|---|
| 0x20 | space (8 px advance; other glyphs advance 12 px) | verified |
| 0x21-0x3A / 0x3B-0x54 | A-Z / a-z (full font already has Latin) | read off the font sheet |
| 0x56-0x5F | 0-9 | font sheet |
| 0x60-0xAF | hiragana ぁ..ん in Unicode/SJIS order without ゎゐゑ (わ=AD を=AE ん=AF) | verified: font sheet + whole-script decode reads as Japanese |
| 0xB0-0xFF | katakana ァ..ン in order without ヮヰヱ (ラ=F8 ワ=FD ヲ=FE ン=FF) | verified (same) |
| 0x100-0x10A | extra signs; used: 0x105 ヴ, 0x10A 々 (我々) | context |
| 0x10B-0x13F | punctuation: ー！？、。・…：”「」『』〜―‼⁉−／＆“ (see `tbl/jp.tbl`) | font sheet + context |
| 0x140-0x14C | kanji numerals 一二三四五六七八九十百千万 | font sheet |
| 0x1ED-0x1FF | blank spacer cells: 6/4/2 px spaces, then 204..12 px padding (name-list columns) | width table |
| 0x200-0x6FF | kanji, in no standard order; the script uses 61, all read (`tbl/jp.tbl`) | zoomed cell sheet + context |

**Table: `tbl/jp.tbl`** (phase 4). Every glyph the script uses is named; `tools/script.py` adds a `{cXXX}` fallback
for any unnamed 2-byte cell so an unread cell never splits into a lead byte + a control code.

**Width table (verified, disassembly of 0x080080D8): ROM 0x8C00FA, one byte per code 0x000-0x1FF** (normal font,
window attr bit 7 clear). Codes > 0x1FF are a fixed 12 px. Latin 0x21-0x54 and space are 8 px, kana 12 px, a few
punctuation cells 8 or 4 px. So the engine already draws proportionally from this table: for English (phase 5) a
narrow Latin font + new widths here may be all the VWF needed. The renderer also **wraps by itself** when the next
glyph would pass the box's right edge (0x080078DE).

Font: ROM **0x2CBC34** (uncompressed, resource id 0x4600 via `bl 0x080202E8`), 16x16 1bpp, 2 bytes per row
big-endian, MSB-first **with each pair of adjacent pixels swapped** (bit 15 = pixel 1, bit 14 = pixel 0; verified
phase 5: the plain MSB reading gives jagged glyphs, the swapped one clean Latin letters), 32 bytes per glyph,
codes up to 0xBFF. A second (small?) font is selected when the
window flag at [0x030028B0 + win*0x24 + 0x23] has bit 7 set: cell = (code & 0x1FF) + 0xC00. Glyph lookup:
0x08008DFC (r0 = window, r1 = code). Width lookup: 0x080080D8 (fixed 12 px, space 8 px observed).
Sheet: `python -X utf8 tools/fontsheet.py work/orig.gba OUT.png --first 200 --count 256`.

Rendering: glyphs go into an EWRAM canvas at 0x02015C00 + line*0x400 (two lines per box) and are DMA'd to BG VRAM
0x06001000 a column at a time (typewriter); the message itself is copied from ROM into EWRAM 0x0201B100 first.

## Control codes (verified by disassembly, phase 4)

Two passes. **Preprocessor 0x08007568** (r0 = message) copies the message into EWRAM 0x0201B100, expanding
includes and branches (jump table 0x080075B8 for codes 0x10-0x1F). **Renderer 0x08007830** draws the expanded
buffer (jump table 0x0800796C). Bytes 0x01-0x0F are lead bytes of 2-byte glyphs in both passes; 0x00 ends the
buffer (only ever seen as an argument byte).

| Code | Args | tbl name | Meaning |
|---|---|---|---|
| 0x13 | 2 | `{se:LLHH}` | sound: id = HH<<8 \| LL; HH bit 7 set = store id at 0x03002000 instead (music?); flag 0x411 overrides with 0xC014 |
| 0x14 | 3 | `{msg:GGIIII}` | include message II (u16) of sub-table group 0x8200+GG through the resource loader; FF / FFFF = from a variable (0x0800A2E0 / 0x08009244). The script only uses `14 FF FF FF` and `14 02 FF FF` |
| 0x15 | var | - | random branch over a u16 offset list (+ var); **unused by the script** |
| 0x16 | var | - | random branch; **unused** |
| 0x17 | 4 | - | flag test + relative skip; **unused**. No jump offsets in the text: messages can grow freely |
| 0x18 | 2 | `{style:AAOO}` | window attr = (attr & AA) \| OO; FF FF = random. Attr bit 7 = small font (cell = (code & 0x1FF) + 0xC00) |
| 0x19 | 0 | `{var}` | insert a dynamic string (bytes from 0x0800A2E0 up to its 0x1F) when 0x03002DB8 != 0 |
| 0x1A | 0 | `{flush}` | flush the line and return from the draw step (unused) |
| 0x1B | 0 | `{1B}` | calls 0x080081D4 (unused) |
| 0x1C | 0 | `{cr}` | x = left margin (unused) |
| 0x1D | 0 | `{n}` | newline (y += 16, or 8 in small font) |
| 0x1E | 0 | `{p}` | newline, and the caller gets the code back (page / button wait) |
| 0x1F | 0 | `{end}` | end; inside an include, return to the caller |
| 0x10-0x12 | 0 | - | dropped by the preprocessor (unused) |

**Message split is token-aware** (`textblock.msg_end`): `13 1F 00` (sound 0x001F, sub-table 35) and glyph 0x11F
(`01 1F`) contain a 0x1F that is not an end code. Splitting at every 0x1F gave 794 "messages"; the real count is
**791**.

## Pointers (verified: every target lands on a message start)

- **Master table** ROM **0x1E90C0**: 62 u32 LE **self-relative** entries (entry at A points at A + value) -> 41
  distinct sub-tables, plus the end marker 0x1FE9F0 (end of all text). Entry 0 points at 0x1E91BF, 7 bytes into the
  first sub-table (0x1E91B8): odd, maybe unused; preserve it relative to that table when relocating.
- **Sub-tables**: u16 LE **self-relative** entries; the table ends where the first message starts (the smallest
  target). Most story tables have 1025 entries, unused ones all pointing at one empty message. Tables sit at odd
  addresses. Messages follow their table; the next sub-table starts right after the last message (chain, no gaps:
  `tools/chain_tables.py`, validated for every sub-table except the two below).
- Sub-table 0x1E9843 (384 entries) has 3 entries (16-18) pointing **mid-message, just after a 0x1D** (shared tails):
  the extractor must allow targets after 0x1D, and the inserter may write them as separate strings.
- 795 distinct message starts in total. Text + tables span **0x1E90C0-0x1FE9F0** (~88 KB; most of it is tables).
- **Unpacker/packer `tools/textblock.py`** (verified: phase 3 identity build, `build.py --verify`): 40 real
  sub-tables chained from 0x1E91B8 (master entry 0 points 7 bytes into the first; entries 51-61 = end of block),
  **791 messages** (0x1F-terminated, split token-aware; no orphans: every one is reached by a slot or as a tail). Sub-table 0x1E9843's entries 305-383 point at the end of its own
  text (= the next table's start): unused slots, kept as "end" entries. pack() takes any 4-aligned base, so the
  block can move to free space; only the resource-table word for group 2 (0xD226B4 = master + 4) would need
  repointing then. Checked (phase 4): of the 75 aligned words in the ROM whose value falls in 0x081E90C0-0x081FE9F0,
  only 0xD226B4 (= 0x081E90C4) hits a table or message start; the rest are graphics data.

## Script dump (phase 4)

`python -X utf8 tools/script.py dump ROM` -> `script/sNN_ADDR.tsv` (one file per sub-table; columns id = original
ROM offset, slots, jp, en, notes). `check` = roundtrip + coverage (0 errors on all 791), tested by
`tests/test_script.py`. A scan of the whole ROM for kana-heavy runs ending in 0x1F outside the block found only
noise in graphics data: all game text in this encoding is in the block. Debug-only messages sit in sub-table 3
(ASSERT, map/BG/anim number readouts, 「開発中」 placeholders): flag them as non-text in the marker build (phase 5).

## English text engine (phase 5)

**Decision: a VWF through the game's own width tables, no new renderer.** The renderer already advances by a
per-code width, so English = narrow glyphs + their widths + two fixes below. Tools: `tools/font.py` (fonts),
`tools/insert.py` (encode, marker, pads, relocation), `tools/asmpatch.py` (code patch), `build.py --marker`.

- **Fonts.** `font/en.txt` (normal font, cells = codes) and `font/en_small.txt` (small font, cells 0xC00 + code,
  widths at **0x8C02FB**, fixed 8 px in the original; pads 0x1F0-0x1FF there are 128..8 px). Both keep the game's
  own A-Z / a-z / 0-9 glyphs (ink moved to column 0, advance = ink + 1 px gap); punctuation `. , ! ? ' " - : ; ( )
  / & … % + ~ * — = [ ]` is new, in the unused cells **0x160-0x176** (2-byte codes `01 60`..; 0x15D-0x1EC are
  0xFF-filled, unused). The small font had no lowercase: drawn new (x-height 5, descender 1 row). Space 0x20 = 4 px.
  The encoder table is built from the font files plus every `tbl/jp.tbl` entry (`insert.en_table()`).
- **Even widths only.** The rasterizer 0x08007B40 writes 4bpp pixel pairs into the canvas and mis-draws a glyph
  that starts at an odd x (verified: odd widths made most of a line vanish; the game's own widths are all even).
  `font.py` rounds every advance up to even.
- **Column-copy patch (verified in-game).** After each glyph the renderer calls 0x08008384(win, x_before, x_after,
  line) to copy canvas tile columns to VRAM. The original returns early when the advance is <= 7 px and copies
  ceil(advance/8) tiles from the tile holding x_before, so with narrow glyphs a tile column is sometimes never
  copied (right half of 'k', 'x', 'M' missing). `asmpatch.py` hooks 0x080083C4 (`bl` to a 5-instruction routine at
  0x081E90C0, the old block start) that aligns x_before down to its tile: every tile from floor(x_before/8) to
  ceil(x_after/8) is copied, skipped only when nothing advanced.
- **Relocation.** The block is packed at **0xD23570** (after the resource table) and resource group 2
  (word 0xD226B4) repointed to it + 4. The old block 0x1E90C0-0x1FE9F0 is then free (hook code at its start).
- **Name tag** = the first line of a dialogue message, drawn in the small font, right- or left-aligned by speaker
  side.
- **Pads.** Name/stage list lines are `{padNN}`-padded to a fixed width (`column: N px` in the notes);
  `insert.fill()` refills the pads after the English text so the line keeps its width.

### Windows and the width gate (all 75 warp scenes toured; budgets measured)

`python -X utf8 tools/winlog.py work/qa/marker --out tbl/windows_ids.tsv` (id -> window geometry, 199 ids from the
full tour). **Budgets: `tbl/windows.json`** (measured with ruler lines, `build.py --qa ID=...`, read with
`tools/inkrows.py`; `tests/test_windows.py` checks every logged geometry maps to one variant). Right edge = (x + w)
* 8 for attr 7xxx windows, (x + w - 2) * 8 for F000 windows; budget = edge - x0. `tools/msgscenes.py DIR [prefixes]`
lists which scene drew which ids.

| Variant | w | x0 | attr | px per line | lines | Notes |
|---|---|---|---|---|---|---|
| dialogue | 28 | 8 | 7020 | 224 | 2 per page | page-wait arrow covers x226-234 on line 2: a page's last line 216 px. Also s35 summon shouts |
| name tag | 8 | 16 / 160 / 184 | 7080 small | 64 | 1 | first line of a dialogue message; over 64 px spills onto the box's line 1. "Armor Gunner" = 70 px |
| mode description | 28 | 8 | 7000 | 224 | 2 | |
| weapon description | 28 | 8 | 7A00 | 224 | 2 | status screen (s01) |
| next stage menu | 22 (h6) | 40 | F000 | 160 | 2 | includes the 2-space cursor indent |
| save status | 22 (h4) | 40 | F000 | 160 | 1 | saving / loading / erasing results |
| prompt | 20 | 48 | F000 | 144 | 2 (3 without buttons) | line 3 runs under the yes/no buttons |
| button hint | 30 | 8 | F000 | 224 | 2 | battle B-button hint |

**The renderer wraps by character at the window edge** ("over t|he lazy"), and the wrapped text pushes lines onto a
new page or below the box; an overlong 9-line ruler in prompt 1E9EE8 left the next prompt blank. So the phase 7
lint must hold every line to its budget; nothing may rely on the engine's wrap.

Not drawn in any of the 75 scenes (no window logged): s00 enemy names (96 px pad column), s05 stage-clear list
(216 px column), s06 mission / failure-condition text, s03 yes/no 1E9B69. Budget = the Japanese width until phase 8
text coverage places them; they may be unused.

## Free space (trap test done)

Trap test (`tools/lua/romtrap.lua` on the marker build, all 75 warp scenes): no CPU read of 0xD3A6B4-0xF00000
(free space after the relocated block) or of the old block 0x1E90CC-0x1FE9F0.


- **0xD2356C-0xF00000: 1,952,404 bytes of 0xFF** (scan for runs >= 4 KB, 2026-11-14). It sits right after the
  resource table (0xD226AC, graphics.md) and before the data at 0xF00000; no resource offset points into it. 1344
  aligned words in the ROM fall in 0x08D2356C-0x08F00000, about what random graphics data gives for a range that
  size, so no pointer table was seen; trap-fill it and tour before use (phase 5). This is the main relocation target
  for text and redrawn graphics.
- 0x00 runs of 4-13 KB at 0x157497, 0x18C981, 0x18E9FD, 0x190A79, 0x192AF6, 0x194B72, 0x7C5BB4, 0x8130D1,
  0x829205, 0x9B357C: inside data (image padding), not free.

- The ROM is a full 16 MiB with no trailing padding. Going past 16 MiB means a 32 MiB ROM and an xdelta/BPS patch
  (FLASH512 save: check it still works). Search for internal 0x00/0xFF runs in phase 5; the tables themselves hold
  ~70 KB of mostly-identical "empty" entries that a rebuilt table could not shrink (indices are fixed) but whose
  messages are tiny, so in-place growth room is limited to repacking 0x1E90C0-0x1FE9F0.

## Not in this system

- Mode-select prompt 「モードをえらんでください」 is in neither this encoding (8- or 16-bit) nor Shift-JIS: likely a
  graphic. See `graphics.md`.
