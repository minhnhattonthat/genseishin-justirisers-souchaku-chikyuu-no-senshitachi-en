# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| text.md | encoding, font, control codes, master + sub pointer tables, text range, free space | encoding/pointers verified; control-code args guessed |
| scenes.md | scene machine, scene ids, progress block, warp / debug tool mechanics | verified by warps (credits entry forced) |
| graphics.md | resource table, Konami LZ, 'fp' container, graphics-text survey + static sweep | table/LZ verified; sweep of sprite groups 16-20 pending ('aS' undecoded) |

Recon helpers: `tools/fontsheet.py` (font sheet), `tools/scan_tables.py` / `tools/chain_tables.py` (message tables),
`tools/recon_msgs.py` (control-code profile), `tools/lua/execregs.lua` (registers at an address),
`tools/lua/dmalog.lua` (DMA3 sources into VRAM), `tools/gbacomp.py` (BIOS LZ77).
