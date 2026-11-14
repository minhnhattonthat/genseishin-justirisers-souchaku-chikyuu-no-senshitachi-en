# Skill gotchas

One line per gotcha: the reference file it belongs in, then the fact.

- references/setup.md: `fetch_emu.py gba-bios` got HTTP 404 from retrobios (2026-11-14); copied a BIOS with the expected SHA-1 300c20df... from a sibling project instead.
- SKILL.md Step 0: the plugin guard hook was not loaded; after adding the `hooks` block to `.claude/settings.json` it took effect within the same session, and it blocks any command containing the canary text, even inside an echo.
- references/emulator-qa.md: Mesen GBA `cpu.r0`..`cpu.r15` are the register keys in `emu.getState()`; `tools/lua/execregs.lua` logs them at an exec address.
- context-mode plugin truncates Bash/Read output over ~4 KB in this environment; print disassembly in ~30-line slices.
- references/graphics.md §Survey: a static sweep can run a game's own custom decompressor under unicorn (`tools/res.py` `Decomp`): exact output with no reimplementation; use `UC_ARM_REG_PC` (not register number 15) to check the return.
- references/emulator-qa.md §Visual QA: in an Orca worker with no subagents, `codex exec --sandbox read-only -i p1.png -i p2.png ... - < prompt.txt` reviewed 29 sweep pages in three background batches.
- references/graphics.md §Survey: GBA BG tilesets can carry a per-tile palette table between palette and tiles (this game: ntiles bytes, padded); a VRAM dump + vramfind.py found the true tile start when every coherence heuristic failed. Render whole screens (map + tileset), not linear tile dumps: Codex read linear BG dumps as 'fragmented' and full screens cleanly.
- scripts/sheet.py: mixed-size images (240x160 next to 240x480) get shrunk to ~70 px wide tiles even with --div 1; send such images to reviewers individually instead.
- Claude Code: an rm with a relative glob after cd is refused by a built-in safety check; write to a fresh output directory instead of clearing one.
- references/emulator-qa.md §Debug tool: for a GBA game with a scene state machine, the fastest warp finder was the main loop: it called a dispatcher indexing a handler table by one RAM byte; poking scene/sub at the dispatcher's entry (L.on_exec) warped cleanly, and a static scan of BL calls to the goto/call helpers (`tools/scenecalls.py`) listed every transition.
- references/emulator-qa.md §emu.py: `--mash` also presses during the boot, so a warp script that waits for a menu gets knocked off it; mash from inside the warp script after the jump instead. A warp's own Start presses must stop before the jump frame: a Start still held when gameplay starts pauses it.
- references/emulator-qa.md §emu.py: Mesen randomises save memory, so the same cold-boot warp run reaches later screens a few hundred frames earlier or later between runs; give scene-list entries slack and test screen conditions, not frames.
- references/emulator-qa.md §Hooks: Mesen GBA Lua has emu.readWord/emu.writeWord (16-bit), not read16/write16.
- references/emulator-qa.md §Hooks: correction to the line above: in this repo's Mesen 2.2.1, GBA Lua `emu.read16`/`emu.read32`/`emu.write32` (addr, memType) do work (sub-81 probe and warp.lua unstick read real values).
- scripts/sheet.py: `--out DIR/sheet.png` fails with FileNotFoundError when DIR doesn't exist; mkdir it first (or the script should create it).
- references/emulator-qa.md §Debug tool: "reaches its scene" (scene byte check) is not proof. 13 of 93 entries passed warp_all's check but showed garbage, a hang, the wrong menu or a cursor that never moved; only reading every entry's sheet (codex exec, read-only) caught them. Also, entries poking past the game's last area (here areas 6-7) "reach" scenes the game never does: check where the game itself goes after the last area before listing more.
- references/emulator-qa.md §Visual QA: a `codex exec` reviewer judges each sheet against the entry description, so a wrong description reads as an issue (9 of 31 here: a carousel menu listed as three items, a CLEAR! banner that boss stages never show). Also, `--every 60` shots can miss a ~30-frame banner: re-run with `--every 20` before calling it missing.
