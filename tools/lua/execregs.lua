-- Log r0-r7 (+lr) each time the CPU executes EXEC_AT (GBA), up to MAX lines.
--   emu.py ... --script tools/lua/execregs.lua --var EXEC_AT=0x08007B40 [--var MAX=200 --var FROM=0]
-- Set KEYS=1 to print the emulator's cpu state keys once (to learn register names).
local at, max, from = assert(EXEC_AT, "set EXEC_AT"), MAX or 200, FROM or 0
local n = 0
local function reg(s, i)
  return s["cpu.r" .. i] or s["cpu.R" .. i] or s[string.format("cpu.r[%d]", i)] or -1
end
L.on_exec(at, at, function()
  if L.frame < from or n >= max then return end
  n = n + 1
  local s = emu.getState()
  if KEYS and n == 1 then
    local ks = {}
    for k, _ in pairs(s) do if k:sub(1, 4) == "cpu." then ks[#ks + 1] = k end end
    table.sort(ks)
    L.log(table.concat(ks, " "))
  end
  local parts = {}
  for i = 0, 7 do parts[#parts + 1] = string.format("r%d=%08X", i, reg(s, i)) end
  parts[#parts + 1] = string.format("lr=%08X", reg(s, 14))
  L.log(string.format("f%d %s", L.frame, table.concat(parts, " ")))
end)
