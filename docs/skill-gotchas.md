# Skill gotchas

One line per gotcha: the reference file it belongs in, then the fact.

- references/setup.md: `fetch_emu.py gba-bios` got HTTP 404 from retrobios (2026-11-14); copied a BIOS with the expected SHA-1 300c20df... from a sibling project instead.
- SKILL.md Step 0: the plugin guard hook was not loaded; after adding the `hooks` block to `.claude/settings.json` it took effect within the same session, and it blocks any command containing the canary text, even inside an echo.
