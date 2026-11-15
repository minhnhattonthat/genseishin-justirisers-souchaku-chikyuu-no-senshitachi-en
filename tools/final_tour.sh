# Phase 8 final re-tour of build/justirisers_en.gba into work/qa/final (docs/status.md; run from Git Bash):
#   bash tools/final_tour.sh        (~1-2 h at --jobs 2; more jobs ran the machine out of memory)
# tour = every warp with the textcover probe (+ regenerates work/states/), tour_adv = the story warps advanced
# with GOD, msgview = unread messages in the real dialogue window (default tables, then s01/s03, which the default
# skips). Then gfxshots (zoomed graphics rows) and inkcheck. The original-ROM tour (work/qa/final/tour_jp) is reused.
set -x
cd "$(dirname "$0")/.."
R=build/justirisers_en.gba
P=$(python tools/skill.py)/scripts/lua/probes/textcover.lua
ADV=$(ls work/qa/cover/tour_adv)
mkdir -p work/qa/final
python -X utf8 tools/debug/warp_all.py --rom $R --out work/qa/final/tour --every 60 --jobs 2 --states --script $P --var "RANGES='8D23570-8D3BA00'" > work/qa/final_tour.log 2>&1
python -X utf8 tools/debug/warp_all.py $ADV --rom $R --out work/qa/final/tour_adv --every 120 --extra-frames 2500 --jobs 2 --script $P --var "RANGES='8D23570-8D3BA00'" --var ADVANCE=40 --var GOD=1 > work/qa/final_adv.log 2>&1
python -X utf8 tools/msgview_run.py work/qa/final --rom $R --jobs 2 > work/qa/final_mv.log 2>&1
python -X utf8 tools/msgview_run.py work/qa/final --rom $R --jobs 2 --tables s01,s03 >> work/qa/final_mv.log 2>&1
python -X utf8 tools/gfxshots.py > work/qa/final_gfx.log 2>&1
python -X utf8 tools/inkcheck.py > work/qa/final_ink.log 2>&1
echo ALLDONE
