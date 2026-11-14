# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

All of D1-D7 came from the owner's standing answers injected into the Orca one-shot run (2026-11-14).

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-11-14 | Honorifics and name order | keep (-san), drop; JP or Western order | Keep honorifics; Western order (given name first). Owner's standing preference. |
| D2 | 2026-11-14 | Romanization source for names | official art, earlier patch, Hepburn | Official English names where they exist (the Justirisers TV series' official romanizations, e.g. "Justirisers"), else an earlier fan patch, else Hepburn without macrons. |
| D3 | 2026-11-14 | Credits | stay Japanese, translate | English. |
| D4 | 2026-11-14 | Abbreviations | engine work first (default), abbreviate | Skill default: full names and terms; engine work before abbreviating, abbreviation only as a flagged last resort. |
| D5 | 2026-11-14 | Graphics text left in Japanese | none (default), list | Translate all of it (titles, menus, banners, cards); leave the original Japanese logo only if it has no official English version. |
| D6 | 2026-11-14 | Specs and plans | need approval, pre-approved | Pre-approved: keep going through every checkpoint, report at the end. |
| D7 | 2026-11-14 | Existing saves / savestates | user's saves, none | None provided; build the debug tool (phase 2) as usual. |
| D8 | 2026-11-15 | Names with no known official English (phase 6, agent default under D2/D6) | Hepburn (Zakoru), English reading of the katakana (Zakoul) | Series names as the series romanizes them (Justiriser, Glen, Gant, Kageri, Kaiser Hades, Norn, Raizeros); other katakana coinages by their evident English reading (Bugscene, Rhinoslave, Zeros Cannon, Tail Smasher), else Hepburn (Zauras, Gildoros, Gardias, Zakoul, Troidon). The transformation call 装着 stays "Souchaku!" (title word, JP flavour). Revisit if the owner has official spellings. |
| D9 | 2026-11-15 | Armor Gunner's name tag is 70 px, tag window 64 px (phase 6, agent default under D4) | abbreviate ("A. Gunner"), drop the space (66 px, still over), widen the tag window | Keep "Armor Gunner"; phase 7 widens the name-tag window to 9 tiles (72 px). Done in phase 7 (`tools/asmpatch.py`, tag window 9 tiles), waiver removed, verified in `work/qa/tagw/zoom_*.png`. |
| D10 | 2026-11-15 | 38 `placeholder` rows (エラーコード filling unused slots) | translate as "Error code", leave Japanese | Translate as "Error code" (fits any box, costs nothing; an unused slot ever indexed shows English). The 14 `debug` rows stay Japanese (dev-only). |
| D11 | 2026-11-15 | Mode select and config BG lettering exceed the VRAM tile budget (0 spare tiles; phase 8, agent default under D4/D6) | move the next VRAM layer (code work, unknown loader), smaller/abbreviated labels, drop "Mode" from the buttons + cell-grid lettering | Buttons read Kids / Normal / Hard / Bonus under the header "Choose a mode" (no meaning lost: the header names the choice); config labels and the mode header use grid lettering (`bgtext.py` align `g`: one glyph per 8 px cell, repeated letters share tiles), config "Weapon Select" became "Swap Weapon" to end before the button sprites at x 136. Mode description 1E9F76 "This is the easy mode." (やさしい is an adjective, not a fourth mode name). |
| D12 | 2026-11-15 | Title subtitle 装着!地球の戦士たち and the OBJ name plates (phase 8, agent default under D8) | "Souchaku! Warriors of Earth" / "Armor On! Warriors of Earth" / romaji "Souchaku! Chikyuu no Senshitachi"; plates "Riser Glen" vs "Glen" | "Souchaku! Warriors of Earth" (D8 keeps 装着 as Souchaku!, the rest in English like the series subtitle reads); plates keep the full "Riser Glen / Riser Kageri / Riser Gant" (tight tracking where the plate is narrow). Revisit with an official English title if one exists. |
