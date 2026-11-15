# Visual-QA reviewer brief - Genseishin Justirisers: Souchaku Chikyuu no Senshitachi (GBA)

You review contact sheets from the English build's QA runs and give each one a verdict. Read-only on everything:
no edits to the repo, no git, no subagents. (`tools/qa_codex.py` runs this brief through `codex exec` with the
sheets attached and writes your verdict lines to `work/qa/verdicts/<chunk>.tsv`.)

## Inputs
- The sheets, attached in order, each with its id.
- `glossary.md` (names and terms; a name that differs from it is an issue).

## Judge
An `issue` is any of:
- Japanese still visible in text the player reads (kana or kanji in a dialogue box, a name tag, a menu);
- text overflowing a box, clipped by a frame, or running off screen;
- text off-centre where the box clearly centres it;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where text belongs (after it has finished typing);
- a name that differs from `glossary.md`.

Standing non-bugs, `ok`:
- text still typing out (a box showing the first letters of a line, a word cut at the typing cursor), a box
  mid-fade, mid-scroll or empty while it opens or closes, a cursor or page arrow caught mid-blink;
- a scene still loading after a warp, black or faded frames;
- **message-viewer runs** (ids starting `msgview/`): every message is forced into stage 1-1's intro dialogue window
  (the top box, name tag at its lower edge). Tables that are not dialogue (`msgview/s01_*`: weapon descriptions;
  `msgview/s03_*`: menu and system strings) have no speaker tag, so their first ~14 letters land in the name-tag
  window and the box starts mid-word ("on worn on the arm." after a tag "A special weap"). That split is the
  harness, not the translation: judge only the glyphs, the box fit and the line breaks of what the box shows.
  The scenery behind the box (stage 1-1's street, the boss sprite) repeats in every run.
  `msgview/s03_*` are short system strings ("Save failed.", "Loading...") with fill/variable codes meant for
  their own small windows: the tag window shows the string, the box shows leftover text of an earlier message,
  and the background can fill with a repeated tile pattern while such a code runs outside its window. For s03
  judge only the name-tag text;
- **tour runs** (ids starting `tour/` or `tour_adv/`): full 240x160 frames of one warp from a cold boot, in time
  order. Menus, titles, stage bars, name plates and credits are now English graphics too, so Japanese lettering in
  a menu, header, button, name plate or badge **is** an issue. Not an issue: Japanese on stage-background scenery
  (shop signs, posters, building lettering in the street stages; deliberately left), the game's own logo artwork
  (Konami / series logo, the title's ジャスティライザー logo, the attract clips' character cards with a katakana
  name logo above its printed romaji such as "RISER GANT"), and debug-warp artefacts (a frame of the previous scene, a scene jumping straight to a
  later state, a fight with the player pinned at full HP);
- the HUD bar of stage screens (`L+R = Use Skill`, life/ammo counters) is not cropped into the message-viewer
  sheets;
- the `▲`/`↵` page-wait arrow at the box's lower right;
- a short last line that is its own phrase ("Be careful, / Naoya!", "Fufufufu... / Justirisers!"): the script breaks
  there on purpose, as the Japanese does (vocative or exclamation on its own line). Only a word pushed down by a
  wrap is an issue.

## Verdicts
One line per sheet, in the order given, nothing else on the line:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile (row, column), which text, what is wrong).
