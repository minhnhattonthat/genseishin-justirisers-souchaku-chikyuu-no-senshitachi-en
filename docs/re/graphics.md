# Graphics text survey (phase 1, INCOMPLETE)

Screens seen so far on cold boot + story start (`tools/routes/boot.txt`, then mash A; shots in `work/qa/boot2`,
`work/qa/story0`). Source guesses are unverified. A fresh session must finish the tour: title menu options, mode
select options, options/sound test, pause, game over, continue, results, every area card, ending, credits.

| Screen | Element | Layer | Source guess | Plan |
|---|---|---|---|---|
| Boot | Konami logo | BG | graphic | keep (English already) |
| Boot | 超星神シリーズ series logo | BG | graphic | keep unless an official English logo exists (D5) |
| Title | 幻星神ジャスティライザー 装着!地球の戦士たち logo | BG | graphic | keep Japanese logo (no official English logo known, D5); recheck |
| Title | "PUSH START", copyright lines | BG | graphic | check: already English? |
| Top menu | menu option under the logo (Japanese, centred) | BG? | graphic | translate |
| Mode select | 「モードをえらんでください」 prompt + mode icons/labels | ? | not in text encoding: graphic | translate |
| Story | dialogue box (sprite frame, ROM 0x5EAC78 DMA to OBJ VRAM) + font text | OBJ + BG | box: raw tiles; text: font | text via script |
| Story | vertical narration 「それから 四五〇〇年…」 | BG | font drawn vertically? | check source |
| Story | area card 「エリア1 『ジャスティライザー とうじょう!』」 | BG | graphic or font | check source |
| Stage map | area name banner (top-left) and "ステージ..." label | BG/OBJ | graphic | translate |
| Character select | header, character names, stat labels (カタログ?) | BG/OBJ | graphic + font? | translate |
| In-game HUD | icons, counters | OBJ | graphic (no Japanese seen yet) | check |
