-- Trap test: log CPU reads of ROM ranges that should never be read (free space, the old script block).
--   emu.py ... --script tools/lua/romtrap.lua --var "TRAP={{0x08D30000,0x08EFFFFF},{0x081E90D0,0x081FE9EF}}"
-- Default: the free space 0xD2356C-0xF00000. Logs the first 20 hits as `TRAP f<frame> pc=<pc> read <addr>`
-- and the total at the end of each 600 frames that saw any; no TRAP line = nothing read there.
local ranges = TRAP or { { 0x08D2356C, 0x08EFFFFF } }
local n, shown = 0, 0
for _, r in ipairs(ranges) do
  L.on_read(r[1], r[2], function(addr, value)
    n = n + 1
    if shown < 20 then
      shown = shown + 1
      L.log(string.format("TRAP f%d pc=%08X read %08X", L.frame, L.pc(), addr))
    end
  end)
end
local last = 0
L.on_frame(function()
  if L.frame % 600 == 0 and n ~= last then
    L.log(string.format("TRAP total %d reads by f%d", n, L.frame))
    last = n
  end
end)
