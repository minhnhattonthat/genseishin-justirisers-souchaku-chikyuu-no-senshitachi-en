# Polish pass (Minor review findings)

One line per Minor finding; the polish pass ticks each `[x]` (fixed, or `waived: reason`). Release refuses while any
line is unticked. Source: phase 6 review, `docs/review/phase6_codex.md`.

- [ ] 1EB33C - prologue: "Tenka Fubu" left unexplained; reviewer suggests "Warlords fought to unite Japan by force...", "far overhead" for はるか じょうくう. Weigh JP flavour (glossary) against clarity.
- [ ] 1F0F35 - Kageri's confirmation variant reads as a copy of 1F0EED with "?"; suggestion: "So Doctor Zora got away... just when we almost had him?"
- [x] 1F2034 - "sortie" -> "go forth!" (fixed in phase 6)
- [x] 1F4F75 - "Pull yourself together!" -> "Hang in there!" (fixed in phase 6)
- [x] 1F6BB7 1F6C55 1F6CE9 1F6D81 - Gardias: "He/She is under my control!!" (fixed in phase 6)
- [x] 1F8BC3 - "Let's split up and find the missiles!" (fixed in phase 6)
- [x] 1FC766 1FC7F4 1FC883 1FC903 - フィニッシュだ -> "This ends now!" (fixed in phase 6)
- [ ] 1EA49B-1EA618 - save-status stage list: "Cleared to X" reads unfinished; まで = up to and including -> "Cleared through X" (or "Cleared up to X"), check the 160 px budget with `textlint.py --fit`. (harness review phase 6, Minor 6)
