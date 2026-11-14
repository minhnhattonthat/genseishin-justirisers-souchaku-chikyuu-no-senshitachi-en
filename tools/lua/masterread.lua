-- Log each distinct (pc, master entry) that reads the relocated master text table (docs/re/text.md §Pointers).
--   emu.py build/justirisers_en.gba --script tools/debug/warp.lua --var "SCENE='status'" --script tools/lua/masterread.lua
-- Lines: "MASTER e=<entry> pc=<hex> lr=<hex> f<frame>". --var MASTER=0x08D23570 for another base.
local base = MASTER or 0x08D23570
local seen = {}
emu.addMemoryCallback(L.safe(function(addr)
  local e = (addr - base) // 4
  local st = emu.getState()
  local pc, lr = st["cpu.r15"] or 0, st["cpu.r14"] or 0
  local k = e .. ":" .. pc
  if seen[k] then return end
  seen[k] = true
  L.log(string.format("MASTER e=%d pc=%08X lr=%08X f%d", e, pc, lr, L.frame))
end), emu.callbackType.read, base, base + 62 * 4 - 1, emu.cpuType.gba, emu.memType.gbaMemory)
