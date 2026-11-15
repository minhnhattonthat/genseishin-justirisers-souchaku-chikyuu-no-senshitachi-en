# Phase 8: contact sheets for the visual-QA gate from the re-tour frames in work/qa/final (run from Git Bash):
#   bash tools/final_sheets.sh [tour|tour_adv|msgview]...   (default: all three)
# tour / tour_adv: every frame at full scale, 4 columns, 16 per page, held frames dropped (--changed 0.02).
# msgview: the dialogue window only (top 64 px) from frame 2200, 3 columns, 30 per page (session (c) settings).
# Writes DIR/sheet.png, sheet_2.png... per scene, replacing old pages. Then:
#   python -X utf8 $SKILL/scripts/qa_gate.py init work/qa/manifest.tsv work/qa/final --glob "*sheet*.png" --build build/justirisers_en.gba
cd "$(dirname "$0")/.."
SHEET=$(python tools/skill.py)/scripts/sheet.py
KINDS=${*:-tour tour_adv msgview}
for kind in $KINDS; do
  for d in work/qa/final/$kind/*/; do
    d=${d%/}
    ls "$d"/f0*.png > /dev/null 2>&1 || continue
    rm -f "$d"/sheet*.png
    if [ "$kind" = msgview ]; then
      python -X utf8 "$SHEET" "$d" --out "$d/sheet.png" --from 2200 --crop 0,0,240,64 --changed 0.01 --cols 3 --max 30 > /dev/null
    else
      python -X utf8 "$SHEET" "$d" --out "$d/sheet.png" --div 1 --cols 4 --max 16 --changed 0.02 > /dev/null
    fi || echo "FAIL $d"
  done
done
echo SHEETS_DONE
