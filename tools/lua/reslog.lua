-- Log every call of the resource loader 0x080202E8 (r0 = id + flags, r1 = sub-index): one line per distinct
-- (id, r1, caller) with the first frame it was seen. Group = (id >> 8) & 0x3F, index = id & 0xFF (tools/res.py).
--   emu.py ... --script tools/lua/reslog.lua
local seen = {}
L.on_exec(0x080202E8, 0x080202E8, function()
  local s = emu.getState()
  local r0, r1, lr = s["cpu.r0"], s["cpu.r1"], s["cpu.r14"]
  local key = string.format("%08X %04X %08X", r0, r1 & 0xFFFF, lr)
  if not seen[key] then
    seen[key] = true
    L.log(string.format("f%d id=%08X g=%d i=%d r1=%04X lr=%08X", L.frame, r0, (r0 >> 8) & 0x3F, r0 & 0xFF, r1 & 0xFFFF, lr))
  end
end)
