# Phase 8 final re-tour of build/justirisers_en.gba into work/qa/final (docs/status.md; run from Git Bash):
#   bash tools/final_tour.sh        (~1-2 h at --jobs 2; more jobs ran the machine out of memory)
# tour = every warp with the textcover probe (+ regenerates work/states/), tour_adv = the story warps advanced
# with GOD, msgview = unread messages in the real dialogue window (default tables, then s01/s03, which the default
# skips). Then gfxshots (zoomed graphics rows) and inkcheck. The original-ROM tour (work/qa/final/tour_jp) is reused.
# Scenes that FAIL (under low memory MesenCE fails to start: exit 0xC0000142, "no WARP line") are rerun one at a
# time, twice at most; LOG.retry holds the last retry's output, so its FAIL lines are the ones that still fail.
set -x
cd "$(dirname "$0")/.."
R=build/justirisers_en.gba
P=$(python tools/skill.py)/scripts/lua/probes/textcover.lua
ADV=$(ls work/qa/cover/tour_adv)
mkdir -p work/qa/final
# tour LOG "NAMES" OPTIONS...   (NAMES empty = every scene)
tour() {
  local log=$1 names=$2; shift 2
  python -X utf8 tools/debug/warp_all.py $names "$@" --jobs 2 > $log 2>&1
  cp $log $log.retry
  for i in 1 2; do
    local failed=$(grep -o '^FAIL [^ ]*' $log.retry | cut -d' ' -f2 | sort -u | tr '\n' ' ')
    [ -z "$failed" ] && return
    python -X utf8 tools/debug/warp_all.py $failed "$@" --jobs 1 > $log.retry 2>&1
    cat $log.retry >> $log
  done
}
# Resume from a step: bash tools/final_tour.sh [tour|adv|mv|gfx] (default tour). A step reruns whole; delete its
# output dir first (work/qa/final/tour, tour_adv, msgview*).
STEP=${1:-tour}
case $STEP in tour) ;; adv|mv|gfx) ;; *) echo "unknown step $STEP"; exit 2;; esac
[ $STEP = tour ] && tour work/qa/final_tour.log "" --rom $R --out work/qa/final/tour --every 60 --states --script $P --var "RANGES='8D23570-8D3BA00'"
[ $STEP = tour -o $STEP = adv ] && tour work/qa/final_adv.log "$ADV" --rom $R --out work/qa/final/tour_adv --every 120 --extra-frames 2500 --script $P --var "RANGES='8D23570-8D3BA00'" --var ADVANCE=40 --var GOD=1
if [ $STEP != gfx ]; then
  python -X utf8 tools/msgview_run.py work/qa/final --rom $R --jobs 2 > work/qa/final_mv.log 2>&1
  python -X utf8 tools/msgview_run.py work/qa/final --rom $R --jobs 2 --tables s01,s03 >> work/qa/final_mv.log 2>&1
fi
python -X utf8 tools/gfxshots.py > work/qa/final_gfx.log 2>&1
python -X utf8 tools/inkcheck.py > work/qa/final_ink.log 2>&1
bash tools/final_sheets.sh > work/qa/final_sheets.log 2>&1
echo ALLDONE
