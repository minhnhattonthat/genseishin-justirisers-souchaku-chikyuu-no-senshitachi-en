-- Log the scene machine at 0x030052F0 (docs/re/scenes.md) whenever scene, sub-state or stack depth changes.
--   emu.py ... --script tools/lua/scenelog.lua
-- Optional raw jump for recon: --var JUMP_AT=1300 --var SC=5 [--var SUB=0] writes scene/sub at the dispatcher
-- entry (0x08026684) on the first call at or after frame JUMP_AT; --var "POKE={[0x03001F48]=1}" writes bytes first.
local M, B = 0x030052F0, emu.memType.gbaMemory
local function rd(a) return emu.read(a, B) end
local last = ""
L.on_frame(function(f)
  local k = string.format("scene=%d sub=%d depth=%d", rd(M), rd(M + 1), rd(M + 5))
  if k ~= last then L.log(string.format("f%d %s", f, k)); last = k end
end)
if JUMP_AT then
  local done = false
  L.on_exec(0x08026684, 0x08026684, function()
    if done or L.frame < JUMP_AT then return end
    done = true
    for a, v in pairs(POKE or {}) do emu.write(a, v, B) end
    emu.write(M, SC, B); emu.write(M + 1, SUB or 0, B)
    emu.write(M + 2, 0, B); emu.write(M + 3, 0, B)
    L.log(string.format("f%d jump scene=%d sub=%d", L.frame, SC, SUB or 0))
  end)
end
