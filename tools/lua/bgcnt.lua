-- Log DISPCNT and BG0-3CNT whenever they change: char base (16 KB block) and screen base (2 KB block) per BG, so a
-- BG redraw knows how many tiles its tileset may grow to before it reaches another layer's tiles or map
-- (docs/re/graphics.md §BG redraw pipeline: tile budget).
--   emu.py ... --script tools/debug/warp.lua --script tools/lua/bgcnt.lua [--var DUMP=<frame>]
local B = emu.memType.gbaMemory
local last = ""
L.on_frame(function()
  local disp = emu.read16(0x04000000, B)
  local parts = { string.format("DISPCNT=%04X", disp) }
  for i = 0, 3 do
    local c = emu.read16(0x04000008 + 2 * i, B)
    parts[#parts + 1] = string.format("BG%d%s pri=%d char=%05X screen=%05X size=%d %s", i,
      (disp >> (8 + i)) & 1 == 1 and "on" or "off", c & 3, ((c >> 2) & 3) * 0x4000,
      ((c >> 8) & 31) * 0x800, c >> 14, (c >> 7) & 1 == 1 and "8bpp" or "4bpp")
  end
  local s = table.concat(parts, " | ")
  if s ~= last then
    L.log(string.format("f%d %s", L.frame, s))
    last = s
  end
  if DUMP and L.frame == DUMP then L.dump_ppu("ppu") end   -- --var DUMP=880: ppu.vram.bin etc. for tools/bgvram.py
end)
