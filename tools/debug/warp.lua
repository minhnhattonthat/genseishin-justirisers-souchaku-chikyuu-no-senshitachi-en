-- Warp to any scene of the scene list from a cold boot (phase 2 debug tool; docs/re/scenes.md).
--   emu.py ROM --out DIR --script tools/debug/warp.lua --var "SCENE='stage_1_2'" --frames 1500 --sheet
-- Opt-in: --var GOD=1 (pin the player's HP in stages), --var CLEAR=n (see below), --var DEBUG=1,
--         --var SCENES=[[abs path]] (default: tools/debug/scenes.gba.txt), --var LIST=1 (log scene names, stop).
-- Scene list: tools/debug/gen_scenes.py writes it (columns and options are documented there).
-- How: boots normally, presses Start through the logos and title, and on the first scene-dispatcher call
-- (0x08026684) with the top menu up (scene 0, sub 4) writes the entry's pokes into the progress block at
-- 0x03001E10, then sets scene/sub at 0x030052F0. The entry's presses are queued after the jump.
-- Logs "WARP <name> f<frame>" at the jump and "SCENE scene=.. sub=.." on every change, so a run proves itself.
local M, P, B = 0x030052F0, 0x03001E10, emu.memType.gbaMemory
local ALIAS = {  -- progress block fields (docs/re/scenes.md); value = absolute address
  area = P + 0x138,     -- 0x03001F48: area - 1
  stage = P + 0x139,    -- 0x03001F49: stage - 1 within the area (0-4)
  stageno = P + 0x130,  -- 0x03001F40: area*5 + stage + 1 (map / clear bookkeeping)
  event = P + 0x131,    -- 0x03001F41: event script 3.N run by the stage (same formula)
  lives = P + 0x133,    -- 0x03001F43
  char = P + 0x136,     -- 0x03001F46: character chosen on character select
  mode = P + 0x13B,     -- 0x03001F4B: difficulty (0 kids, 1 normal, 2 hard)
  unlock = P + 0xC2,    -- 0x03001ED2: unlocked characters bitfield
}

local function parse_line(line)
  local f = {}
  for col in (line .. "\t"):gmatch("([^\t]*)\t") do f[#f + 1] = col end
  return f
end
local function load_scenes(path)
  local t, order = {}, {}
  for line in io.lines(path) do
    if line ~= "" and not line:match("^#") then
      local f = parse_line(line)
      local e = { name = f[1], scene = tonumber(f[2]), sub = tonumber(f[3]), pokes = {}, presses = f[5] or "-", opt = {} }
      for o in (f[4] or ""):gmatch("@(%w+)") do e.opt[o] = true end  -- @clear: see CLEAR below
      for k, v in (f[4] or ""):gmatch("([%w_]+)=(%w+)") do
        local a = ALIAS[k] or tonumber(k)
        assert(a, "unknown poke " .. k .. " in " .. e.name)
        e.pokes[#e.pokes + 1] = { a, tonumber(v) }
      end
      t[e.name] = e; order[#order + 1] = e.name
    end
  end
  return t, order
end

-- emu.py concatenates scripts into one _run.lua and Mesen runs in tools/mesen/, so the default is relative to that.
local path = SCENES or "../debug/scenes.gba.txt"
local scenes, order = load_scenes(path)
if LIST then
  for _, n in ipairs(order) do L.log(n) end
  L.finish(0)
  return
end
local want = assert(scenes[SCENE or ""], "unknown SCENE '" .. tostring(SCENE) .. "' (see " .. path .. ")")

local function rd(a) return emu.read(a, B) end
local warped, mash, god_max = false, nil, 0

-- CLEAR (--var CLEAR=1 or @clear in the entry): once gameplay's play loop (scene 4 sub 16) has run CLEAR_AFTER
-- frames (default 90), jump to its stage-clear sub 80, which plays CLEAR!, the points screen and the save menu.
-- CLEAR=n repeats for n stages in a row.
-- @subN in the entry: the same, but jump to sub N of the play loop's scene once (scene 4: 32 pause, 36 status,
-- 48 continue, 64 game over, 80 clear; scene 13: 64 lose, 80 win: docs/re/scenes.md).
-- @pause: press Start once the play loop has run that long. @hold: stop the entry's mash after either.
local clears = CLEAR or 0
for o in pairs(want.opt) do  -- @clear = 1, @clear3 = 3 play loops in a row (stage, then its mecha battle, ...)
  local n = o:match("^clear(%d*)$")
  if n then clears = math.max(clears, tonumber(n) or 1) end
end
if clears > 0 then CLEAR = CLEAR or clears end  -- the menu-driving code below keys on CLEAR
local force_sub
for o in pairs(want.opt) do local n = o:match("^sub(%d+)$"); if n then force_sub = tonumber(n) end end
local pause = want.opt.pause
local playing, pausing = 0, 0
L.on_exec(0x08026684, 0x08026684, function()
  if not warped then return end
  -- the play loop is sub 16 in both side-scrolling stages (scene 4) and mecha battles (scene 13)
  local sc = rd(M)
  -- frames spent in it since the scene was entered (a battle leaves sub 16 for every special attack)
  if sc ~= 4 and sc ~= 13 then playing = 0 end
  local in_loop = (sc == 4 or sc == 13) and rd(M + 1) == 16  -- any stack depth: a battle can be entered by call
  if in_loop then playing = playing + 1 end
  if DEBUG and L.frame % 300 == 0 then L.log(string.format("DBG f%d sc=%d playing=%d clears=%d", L.frame, sc, playing, clears)) end
  if not in_loop or playing < (CLEAR_AFTER or 90) then return end
  if clears > 0 or force_sub then
    local to = clears > 0 and 80 or force_sub
    emu.write(M + 1, to, B); emu.write(M + 2, 0, B); emu.write(M + 3, 0, B)
    if clears > 0 then clears = clears - 1 else force_sub = nil end
    if want.opt.hold then mash = nil end  -- @hold: stop mashing, so the screen stays put
    playing = 0
    L.log(string.format("FORCE f%d sub=%d", L.frame, to))
  elseif pause then
    pause, pausing, mash = false, 6, nil
    L.log(string.format("PAUSE f%d", L.frame))
  end
end)
L.on_exec(0x08026684, 0x08026684, function()
  if warped or rd(M) ~= 0 or rd(M + 1) ~= 4 or rd(M + 5) ~= 0 then return end
  warped = true
  for _, p in ipairs(want.pokes) do emu.write(p[1], p[2], B) end
  emu.write(M, want.scene, B); emu.write(M + 1, want.sub, B)
  emu.write(M + 2, 0, B); emu.write(M + 3, 0, B)
  L.log(string.format("WARP %s f%d scene=%d sub=%d", want.name, L.frame, want.scene, want.sub))
  if want.presses ~= "-" and want.presses ~= "" then
    for step in want.presses:gmatch("[^;]+") do
      local m, key = step:match("^%s*mash(%d+)(%a*)%s*$")  -- "mash60" / "mash60b": that key every N frames from here on
      if m then mash = { every = tonumber(m), key = key ~= "" and key or "a", from = L.frame }; break end
      local n, spec = step:match("^%s*(%d+)%s+(%S+)%s*$")
      assert(n, "bad press '" .. step .. "' in " .. want.name)
      L.press(spec, tonumber(n))
    end
  end
end)

-- Start through the logos and the title until the warp fires (the driver's queue is empty before it).
emu.addEventCallback(L.safe(function()
  -- only on the logos (scene 0 sub 2/3) and the PUSH START title (scene 15 sub 1): a Start still held when the
  -- warp lands would pause the gameplay scene at once
  local sc, sub = rd(M), rd(M + 1)
  local skip = (sc == 0 and (sub == 2 or sub == 3)) or (sc == 15 and sub == 1)
  if not warped and skip and L.frame % 40 < 6 then emu.setInput({ start = true }, 0) end
  if pausing > 0 then emu.setInput({ start = true }, 0); pausing = pausing - 1 end
  -- CLEAR flow: A on the points screen (scene 6); on the menu after it (scene 7 sub 18: next stage / save,
  -- cursor byte 0x03005324: 0 next, 1 save) Up until the cursor is on "next stage", then A
  if warped and (CLEAR or want.opt.clear) and L.frame % 40 < 6 then
    if sc == 6 then emu.setInput({ a = true }, 0)
    elseif sc == 7 and sub == 18 then emu.setInput(rd(M + 0x34) == 0 and { a = true } or { up = true }, 0)
    elseif sc == 7 and sub == 15 then emu.setInput({ a = true }, 0) end  -- after the ending: "save clear data" note
  end
  -- "mashN" runs once the entry's fixed presses are done (L.route_done)
  local in_clear = (CLEAR or want.opt.clear) and (sc == 6 or sc == 7)
  if mash and not in_clear and L.route_done() and (L.frame - mash.from) % mash.every < 6 then emu.setInput({ [mash.key] = true }, 0) end
end), emu.eventType.inputPolled)

local last = ""
L.on_frame(function(f)
  local k = string.format("scene=%d sub=%d", rd(M), rd(M + 1))
  if k ~= last then
    local pb = {}  -- progress block 0x03001F40-0x03001F4B and the area-card flag 0x03001F58
    for a = P + 0x130, P + 0x13B do pb[#pb + 1] = string.format("%02X", rd(a)) end
    L.log(string.format("SCENE f%d %s  F40=%s F58=%02X", f, k, table.concat(pb, " "), rd(P + 0x148)))
    last = k
  end
  if GOD and rd(M) ~= 4 then god_max = 0 end
  if GOD and rd(M) == 4 and rd(M + 1) == 16 then
    -- stage play loop: pin the player's HP (u16 0x03005264, 16 at full on stage 1-2) to the highest seen in it
    local hp = emu.readWord(0x03005264, B)  -- 0xFFFE until the stage sets it on the loop's first frames
    if hp > 0xFF then
    elseif hp > god_max then god_max = hp elseif hp < god_max then emu.writeWord(0x03005264, god_max, B) end
  end
end)
