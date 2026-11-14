-- Where is the CPU? Logs the PC at the end of every SAMPLE_EVERY-th frame from FROM, plus a count of
-- dispatcher (0x08026684) calls since the last sample: 0 calls means the main loop is stuck elsewhere.
--   emu.py ... --script tools/lua/pcsample.lua --var FROM=2600 [--var SAMPLE_EVERY=30 --var TO=3000]
local from, every, to = FROM or 0, SAMPLE_EVERY or 30, TO or math.huge
local calls = 0
L.on_exec(0x08026684, 0x08026684, function() calls = calls + 1 end)
L.on_frame(function()
  if L.frame < from or L.frame > to or L.frame % every ~= 0 then return end
  L.log(string.format("PC f%d pc=%08X dispatcher_calls=%d", L.frame, L.pc(), calls))
  calls = 0
end)
