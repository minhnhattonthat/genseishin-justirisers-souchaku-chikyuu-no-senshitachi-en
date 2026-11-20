# Genseishin Justirisers: Souchaku Chikyuu no Senshitachi English translation

Unofficial English fan translation of **Genseishin Justirisers: Souchaku Chikyuu no Senshitachi** (Game Boy Advance,
Konami, 2004): the source text and tools that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue / story (prologue, all five stages, every hero's version of each event, battle shouts) | Translated |
| Menus, save/load, options, character select, status screens, mission goals, stage names | Translated |
| Graphics with text (title subtitle, chapter cards, mode buttons, HUD, pause, points/clear screens, game over, banners) | Translated |
| Name entry | None in this game |
| Credits roll | Translated |
| Logos (Justirisers title logo, Choseishin series logo) and voice clips | Left as in the original (official logo art, Japanese voice samples) |

Known issues: none known; see [Issues](../../issues).

## Base ROM

| | |
|---|---|
| No-Intro name | Genseishin Justirisers - Souchaku Chikyuu no Senshitachi (Japan) |
| Size | 16,777,216 bytes (16 MiB) |
| CRC32 | 580A00A5 |
| MD5 | 8905016d29e691975ebb176dec1dce4e |
| SHA-1 | 54de19108f2b8411ff2e52f7b5bf8e68bb19ae6d |

Tested in MesenCE 2.2 with the official GBA BIOS. Start from a cold boot (no savestates from the Japanese game).

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `gfx/` | Graphics-text rows (English lettering redrawn into the game's screens, sprites and credits). |
| `tools/` | Python build chain: extract, insert, lint, graphics, QA, release. |
| `tests/` | unittest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.codex/agents/`, `.opencode/agents/` | Subagent types (translator, reviewer, visual QA, playtester, graphics) for Codex and opencode; Claude Code gets them from the plugin. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/genseishin-justirisers-souchaku-chikyuu-no-senshitachi-en
cd genseishin-justirisers-souchaku-chikyuu-no-senshitachi-en
# copy your dump to: rom/Genseishin Justirisers - Souchaku Chikyuu no Senshitachi (Japan).gba
#   (16777216 bytes, SHA-1 54de19108f2b8411ff2e52f7b5bf8e68bb19ae6d; the build refuses any other dump, see rom.sha1)
python -X utf8 build.py                                # -> build/justirisers_en.gba
python -X utf8 tools/check.py                          # tests + text lint
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Konami's and is included only so the
translation can be checked against it. Genseishin Justirisers: Souchaku Chikyuu no Senshitachi is (c) 2004 Konami,
Justiriser Project and TV Tokyo; this project is not affiliated with them. Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
