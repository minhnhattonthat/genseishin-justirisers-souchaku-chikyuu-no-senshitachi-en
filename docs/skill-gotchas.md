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
