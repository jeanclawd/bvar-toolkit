#!/usr/bin/env bash
# Run every bvar-toolkit unit test under RunMat, one isolated process each.
# Usage: runmat/run_all.sh [timeout_s]   -> runmat/results/results.tsv + summary
set -u
here=$(cd "$(dirname "$0")" && pwd); root=$(dirname "$here")
python3 "$here/build_compat.py"
mkdir -p "$here/results"
out="$here/results/results.tsv"
printf 'status\ttest\tseconds\tdetail\n' > "$out"
for f in "$root"/tests/unit/test_*.m; do
  name=$(basename "$f" .m)
  line=$("$here/run_one.sh" "$name" "${1:-300}")
  echo "$line"; echo "$line" >> "$out"
done
echo; tail -n +2 "$out" | cut -f1 | sort | uniq -c | sort -rn
