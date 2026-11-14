-- GBA DMA3 log: one line per distinct (src, dst) pair whose destination is in [DST_LO, DST_HI].
--   emu.py ... --script tools/lua/dmalog.lua [--var DST_LO=0x06010000 --var DST_HI=0x06017FFF] [--var FROM=0 --var TO=N]
-- Hooks writes to DMA3SAD/DMA3DAD (0x040000D4/D8); value args may arrive per halfword, so it rebuilds 32-bit words.
local dlo, dhi = DST_LO or 0x06010000, DST_HI or 0x06017FFF
local from, to = FROM or 0, TO or math.huge
local regs = {}
local seen = {}
L.on_write(0x040000D4, 0x040000DF, function(addr, value)
  local base = addr & ~3
  local shift = (addr & 3) * 8
  local cur = regs[base] or 0
  if addr & 3 == 0 and value > 0xFFFF then cur = value
  else
    local mask = (addr & 1 == 0) and 0xFFFF or 0xFF
    cur = (cur & ~(mask << shift)) | ((value & mask) << shift)
  end
  regs[base] = cur
  if base == 0x040000DC and L.frame >= from and L.frame <= to then
    local src, dst = regs[0x040000D4] or 0, regs[0x040000D8] or 0
    if dst >= dlo and dst <= dhi then
      local key = string.format("%08X>%08X", src, dst)
      if not seen[key] then
        seen[key] = true
        L.log(string.format("f%d src=%08X dst=%08X cnt=%08X pc=%08X", L.frame, src, dst, cur, L.pc()))
      end
    end
  end
end)
