#!/bin/sh
# review_pages.sh PAGEDIR OUTDIR PROMPT [PER_CHUNK] [GLOB]: read-only Codex review of sweep images (default p*.png),
# run in parallel chunks; each chunk's prompt ends with the attachment file names in order. Writes OUTDIR/out_NN.txt
# (TSV verdicts) and err_NN.txt. Phase-1 graphics-text sweep (tools/sweep.py pages, tools/bgscreens.py screens).
pages=$1; out=$2; prompt=$3; per=${4:-9}; glob=${5:-p*.png}
mkdir -p "$out"
files=$(cd "$pages" && ls $glob)
n=$(echo "$files" | wc -l)
s=1
while [ "$s" -le "$n" ]; do
  chunk=$(echo "$files" | sed -n "${s},$((s + per - 1))p")
  imgs=""
  for f in $chunk; do imgs="$imgs -i $pages/$f"; done
  tag=$(printf %02d "$s")
  { cat "$prompt"; echo; echo "Attachments in order: $(echo $chunk)"; } > "$out/prompt_$tag.txt"
  # shellcheck disable=SC2086
  codex exec --sandbox read-only --skip-git-repo-check $imgs - < "$out/prompt_$tag.txt" > "$out/out_$tag.txt" 2> "$out/err_$tag.txt" &
  s=$((s + per))
done
wait
echo "done: $out"
