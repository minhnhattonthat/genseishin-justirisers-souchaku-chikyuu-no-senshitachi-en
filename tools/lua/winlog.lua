-- Box variants: log each message the game prints with the window it is drawn into (docs/re/text.md §Windows).
--   emu.py ... --script tools/lua/winlog.lua        (or warp_all.py --script tools/lua/winlog.lua)
-- `MSG f<frame> addr=<ROM addr>` when the preprocessor 0x08007568 expands a message (r0 = its ROM address), then
-- `WIN f<frame> addr=<last msg> win=<n> x=<tile> y=<tile> w=<tiles> h=<tiles> x0=<px> attr=<0x22><0x23>` on the
-- first renderer call (0x08007830, r0 = window) for that message. Window struct: 0x030028B0 + win * 0x24;
-- +0x18 x, +0x19 y, +0x1E w, +0x1F h (tiles), +0x1A current x (px), +0x22/+0x23 attributes (bit 7 = small font).
-- tools/winlog.py maps addresses back to script ids and sums the variants.
local B = emu.memType.gbaMemory
local last, logged = 0, {}
local function reg(i) local s = emu.getState(); return s["cpu.r" .. i] or s["cpu.R" .. i] or -1 end
L.on_exec(0x08007568, 0x08007568, function()
  last = reg(0)
  logged[last] = nil
  L.log(string.format("MSG f%d addr=%08X", L.frame, last))
end)
L.on_exec(0x08007830, 0x08007830, function()
  local win = reg(0) & 0xFF
  local key = last * 16 + win
  if logged[key] then return end
  logged[key] = true
  local s = 0x030028B0 + win * 0x24
  L.log(string.format("WIN f%d addr=%08X win=%d x=%d y=%d w=%d h=%d x0=%d attr=%02X%02X", L.frame, last, win,
    emu.read(s + 0x18, B), emu.read(s + 0x19, B), emu.read(s + 0x1E, B), emu.read(s + 0x1F, B),
    emu.read(s + 0x1A, B), emu.read(s + 0x22, B), emu.read(s + 0x23, B)))
end)
