-- Message viewer for text coverage and visual QA: the event command that shows a dialogue message calls the
-- resource loader at 0x080214A8 with r7 = text sub-table index (group 2, master entry - 1) and r4 = message slot
-- (docs/re/scenes.md §Message viewer). This probe logs each call ("MSG t=<table> s=<slot> f<frame>") and, with
-- --var "MSGS='t:s,t:s,..'", replaces the n-th call's (table, slot) with the n-th pair of the list ("MSGVIEW").
-- Run it on an entry with a long stage-start event (stage_1_1: about 30 messages) plus warp.lua's ADVANCE=40.
--   emu.py ROM --script tools/debug/warp.lua --var "SCENE='stage_1_1'" --var ADVANCE=40 --script tools/lua/msgview.lua --var "MSGS='25:0,25:1'"
local list = {}
for t, s in string.gmatch(MSGS or "", "(%d+):(%d+)") do list[#list + 1] = { tonumber(t), tonumber(s) } end
local n = 0
L.on_exec(0x080214A8, 0x080214A8, function()
  local st = emu.getState()
  local t, s = st["cpu.r7"], st["cpu.r4"]
  n = n + 1
  local w = list[n]
  if w then
    emu.setState({ ["cpu.r7"] = w[1], ["cpu.r4"] = w[2] })
    L.log(string.format("MSGVIEW %d t=%d s=%d (was %d:%d) f%d", n, w[1], w[2], t, s, L.frame))
  else
    L.log(string.format("MSG t=%d s=%d f%d", t, s, L.frame))
  end
  if #list > 0 and n == #list then L.log(string.format("MSGVIEW done f%d", L.frame)) end
end)
