# Glossary - Genseishin Justirisers: Souchaku Chikyuu no Senshitachi

Binding for every translator and reviewer. Agents propose additions in reports; only the controller edits this file.
`tools/textlint.py` enforces the tables: a row whose JP occurs in a line's Japanese must have its EN in the English,
and a speaker tag (first line of a story message) must be exactly the EN of its row.

## Rulings (asked of the user once; options and reasons in docs/decisions.md)
- Honorifics: kept, hyphenated (Shota-kun). Name order: Western (given name first). The script mostly uses bare
  given names (翔太, 直也, ユカ); the one honorific is Kageri's 直也さん -> "Naoya-san" (Honorifics table, linted).
- Romanisation source: official English (TV series) names where they exist, else an earlier fan patch, else Hepburn
  without macrons. No earlier patch exists; names not known from the series are Hepburn or the obvious English
  reading of the katakana (D8).
- Credits: English.
- Register / flavour: tokusatsu hero show; keep light JP flavour: the transformation call 装着 stays "Souchaku!",
  laughs stay as laughs ("Fufufu...", "Hahaha!"). Sound-effect words in the text (グワッ, ギギーッ) become English
  grunts ("Gwaah!", "Gigiii!"); the game's sounds themselves are `{se:..}` codes, never text.
- Abbreviations: full names and terms everywhere, prefer engine changes over shortening (Armor Gunner's tag is 70 px
  against a 64 px tag window: waived in `tbl/lint_waive.tsv`, phase 7 widens the window).

## Style rules
- Punctuation map: 「」 -> "...", 『』 -> '...', ・・・/… -> ..., ‼ -> !!, ⁉ -> !?, ！？ -> !?, ― -> -.
  ASCII only (the font has . , ! ? ' " - : ; ( ) / & % + ~ * = [ ] and the ellipsis is three periods).
- Line breaks: dialogue = speaker tag line, then at most 2 lines per page (224 px; the page's last line 216 px).
  English may add pages ({p}) where the Japanese had a long single page. Check with
  `python -X utf8 tools/textlint.py --fit "TEXT"`.
- Voices:
  - **Glen / Shota** (おれ, 〜ぜ, 〜ねえ): hot-blooded and blunt. Contractions, "gonna", short exclamations.
  - **Gant / Naoya** (おれ, 〜だ, 〜せん, 〜ぞ): the calm, steady one who reins Shota in. Complete sentences, firm, no slang.
  - **Kageri / Yuka** (あたし, 〜わよ, 〜わ): bright and brave, a little teasing. "Come on!", "Leave it to me!".
  - **Doctor Zora** (我々, kanji-heavy lines, フフフ): the mastermind; grand, smug, theatrical. "Fufufu...".
  - **Zauras** (きさま, 〜てやる): brutish general, roaring threats. "Graah!", "you whelps".
  - **Gildoros**, **Gardias**, **Armor Gunner**: monster generals; menacing, boastful.
  - **Narration** (s07, s08 ends): storybook voice-over, past tense, a little grand ("Hear the call of justice!").
  - System text (save, menus, mission goals): short and plain, imperative goals ("Defeat the Bugscenes").

## Characters
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| グレン | Glen | 64 px tag | Justiriser Glen (Riser Glen), Shota | |
| ガント | Gant | 64 px tag | Justiriser Gant, Naoya | |
| カゲリ | Kageri | 64 px tag | Justiriser Kageri, Yuka | Kagere |
| 翔太 | Shota | | Glen's real name | Shouta |
| 直也 | Naoya | | Gant's real name | |
| ユカ | Yuka | | Kageri's real name | |
| ゾラ | Zora | 64 px tag | ドクター・ゾラ = Doctor Zora | Dr. Zora |
| ザウラス | Zauras | 64 px tag | | |
| ギルドロス | Gildoros | 64 px tag | | |
| ガーディアス | Gardias | 64 px tag | | |
| アーマーガンナー | Armor Gunner | 70 px tag (waived) | | Armorgunner |
| ？？？ | ??? | tag | unknown speaker | |
| ジャスティライザー | Justiriser | | plural Justirisers | Justi-Riser |
| カイザーハデス | Kaiser Hades | | also カイザー・ハデス, ハデス = Hades | |
| ノルン | Norn | | Riser alien who gave mankind the Justi-Power | |
| ザコール | Zakoul | | foot soldiers | Zakor |
| バグシーン | Bugscene | | enemy robots (mission goals) | |
| スー・ザ・ジィ | Sue the G | | s00 enemy name | |
| ヴァン・ジャー | Van Jar | | s00 enemy name | |
| トパス | Topas | | s00 enemy name | |
| ジェナス | Jenas | | s00 enemy name (s00 table looks unused; transliterated per D8) | |
| ラグナ | Ragna | | s00 enemy name | |
| セラ | Sera | | s00 enemy name | |
| シーン | Sheen | | s00 enemy name | |
| ダーク | Dark | | s00 enemy name | |
| パフ | Puff | | s00 enemy name | |
| ケイケイ | Keikei | | s00 enemy name | |
| ロシェット | Rochette | | s00 enemy name | |
| タフト | Taft | | s00 enemy name | |
| ジュリ | Juri | | s00 enemy name | |
| ジュネ | June | | s00 enemy name; judgement call (could be Jeune), no official source | |

## Honorifics
Matched on the JP start only (a particle may follow). Lint rule `honorific`.

| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 直也さん | Naoya-san | | Kageri to Gant (D1) | |

## Places
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| メインコンピュータ | main computer | | | |

## Items / skills / terms
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| ジャスティパワー | Justi-Power | | | |
| ライザーせいじん | Riser alien | | ライザー星人 | |
| 幻星神 | Genseishin | | the giant guardian beasts (title word) | |
| げんせいじゅう | Genseijuu | | s35 summon shout calls Raizeros 幻星獣, not 幻星神: kept distinct | |
| ライゼロス | Raizeros | | Genseishin | |
| ケンライザー | Kenriser | | | |
| ライノスレイブ | Rhinoslave | | | |
| トロイドン | Troidon | | | |
| ゼロスキャノン | Zeros Cannon | | | |
| ゼロスクラッシャー | Zeros Crusher | | | |
| テイルスマッシャー | Tail Smasher | | | |
| スマッシュクロー | Smash Claw | | | |
| ライザーセイバー | Riser Saber | | | |
| ライザーバーン | Riser Burn | | | |
| メガヒートスラッシュ | Mega Heat Slash | | | |
| そうちゃく | Souchaku | | transformation call, kept | |
| ピープル | people | | civilians to rescue (mission goals) | |

## Stage titles (game's own English titles in katakana)
ファースト・トライ First Try, クライング・ピープル Crying People, リトル・ビリーバー Little Believer, カーゴ・イン・ホープ
Cargo in Hope, ウィナーズ・ベット Winner's Bet, コール・オブ・ピープル Call of People, テンダネス・ウィスパー Tenderness
Whisper, トライアングル・ペイン Triangle Pain, ゲット・イン・ストレート Get in Straight, スクリーン・ハート Screen Heart,
ライ・トゥ・リボーン Lie to Reborn, インビジブル・リンク Invisible Link, ミス・ミステイカブル Miss Mistakable,
ユナイテッド・イーブル United Evil, プライマー・オン・ライフ Primer on Life, シャイン＆ダークネス Shine & Darkness,
インポータント・ユー Important You, アンサー・ウィズ・バトル Answer with Battle.

## Decisions from earlier batches
- (phase 6) 見参 / 参上 / 推参 roll calls: Glen "Here I come!", Kageri "On the scene!", Gant "Reporting for battle!".
