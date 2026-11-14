-- Log every resource-loader call (0x080202E8) for an event script (group 3): "EVLOAD r0=<id> r1=<arg> lr=<hex> f<frame>".
--   emu.py ROM --script tools/debug/warp.lua --var "SCENE='stage_1_1'" --script tools/lua/evlog.lua
-- --var EVGROUP=n logs another group instead.
local G = EVGROUP or 3
L.on_exec(0x080202E8, 0x080202E8, function()
  local st = emu.getState()
  local r0, r1 = st["cpu.r0"], st["cpu.r1"]
  if (r0 >> 8) & 0x3F ~= G then return end
  L.log(string.format("EVLOAD r0=%08X r1=%08X lr=%08X f%d", r0, r1, st["cpu.r14"], L.frame))
end)
