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
| 0x60-0xAF | hiragana ぁ..ん in Shift-JIS order (code = SJIS low byte - 0x3F; ゎゐゑ absent so わ=AD? を=AE ん=AF) | か/く/た/っ/つ/ふ/ら/を verified; rest guess |
| 0xB0-0x10A | katakana ァ.. in Shift-JIS order (SJIS 0x8340 + n -> 0xB0 + n, minus 1 after the 0x837F gap: ラ=F8) | ス/デ/ハ/ド/ク/タ/ゾ/ラ verified |
| 0x10B ー, 0x110 ・, 0x111 … | punctuation block 0x10B-0x13F | verified (ー ・ …) |
| 0x140-0x15F | kanji numerals 一二三四五六七八九十百千万 (+ a small set at 0x150) | font sheet |
| 0x200-0x6FF | kanji (lead bytes 02-06 are used in the script) | to read in phase 4 |

Font: ROM **0x2CBC34** (uncompressed, resource id 0x4600 via `bl 0x080202E8`), 16x16 1bpp, 2 bytes per row
big-endian (MSB = left pixel), 32 bytes per glyph, codes up to 0xBFF. A second (small?) font is selected when the
window flag at [0x030028B0 + win*0x24 + 0x23] has bit 7 set: cell = (code & 0x1FF) + 0xC00. Glyph lookup:
0x08008DFC (r0 = window, r1 = code). Width lookup: 0x080080D8 (fixed 12 px, space 8 px observed).
Sheet: `python -X utf8 tools/fontsheet.py work/orig.gba OUT.png --first 200 --count 256`.

Rendering: glyphs go into an EWRAM canvas at 0x02015C00 + line*0x400 (two lines per box) and are DMA'd to BG VRAM
0x06001000 a column at a time (typewriter); the message itself is copied from ROM into EWRAM 0x0201B100 first.

## Control codes (guess from byte statistics, `tools/recon_msgs.py`; verify against the interpreter in phase 4)

| Code | Args | Meaning (guess) |
|---|---|---|
| 0x1F | 0 | end of message (verified: every table target follows a 0x1F) |
| 0x1D | 0 | newline; first byte pair of a dialogue message is `20 1D` (blank speaker/name line?) |
| 0x1E | 0 | wait for button / new page |
| 0x19 | 0 | appears in runs `20 19 20 19` (pause/delay?) |
| 0x13 | 2 | e.g. `13 0B 00`, `13 05 00..02` (portrait/face?) |
| 0x14 | 3 | `14 FF FF FF` |
| 0x18 | 2 | `18 FF FF`, `18 7F 80`, `18 7F 00` |
| 0x00 | ? | 82 left over in one table that looks like binary data; see below |

Text interpreter reads the message at PCs 0x08007594-0x080077FC (read-watch on the ROM text).

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

## Free space (candidates, not yet trap-tested)

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
