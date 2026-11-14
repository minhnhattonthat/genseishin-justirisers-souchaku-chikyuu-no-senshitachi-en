-- Log every write of a scene id into the scene machine (0x030052F0 current, 0x030052F6 next): frame, PC, value.
--   emu.py ... --script tools/lua/scenewrites.lua [--var ONLY=11]
-- Finds who enters a scene whose id is computed (no constant goto in tools/scenecalls.py), e.g. the credits.
local M = 0x030052F0
local last = {}
for _, a in ipairs({ M, M + 6 }) do
  L.on_write(a, a, function(addr, value)
    value = value & 0xFF
    if ONLY and value ~= ONLY then return end
    local pc = L.pc()
    local k = string.format("%08X %X %d", pc, addr, value)
    if last[k] then return end
    last[k] = true
    L.log(string.format("f%d pc=%08X %s=%d", L.frame, pc, addr == M and "scene" or "next", value))
  end)
end
