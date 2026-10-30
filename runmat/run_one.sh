#!/usr/bin/env bash
# Run one bvar-toolkit unit test under RunMat, isolated and memory-capped.
# Usage: runmat/run_one.sh test_build_lags [timeout_s]
# Prints PASS/FAIL/ERROR/TIMEOUT/OOM <name> <seconds> <first error line>.
set -u
name=$1; tmo=${2:-300}
root=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
# Shims must sit in the working directory: RunMat 0.6.1 fails to compile them
# when they are only reachable through addpath (see README.md).
cp "$root"/runmat/shims/*.m "$work"/
# Sources come from the RunMat-compatible mirror (build_compat.py); the test
# itself and tests/unit/private are copied next to the driver.
build="$root/runmat/.build"
[ -d "$build" ] || python3 "$root/runmat/build_compat.py" >/dev/null
cp "$build/tests/unit/$name.m" "$work/"
# Library code goes in the working directory too, not on the path: a folder
# reached through addpath fails to compile as soon as one of its functions
# assigns an optional argument under "if nargin < k" (README.md, issue 4).
# Only the core files this test reaches (deps.py), copied, not symlinked:
# RunMat fails to compile package files reached through a symlinked folder.
python3 "$root/runmat/deps.py" "$name" | while read -r rel; do
  mkdir -p "$work/$(dirname "$rel")"; cp "$build/core/$rel" "$work/$rel"
done
cp "$build"/third_party/*.m "$work/"
[ -d "$build/tests/unit/private" ] && cp -r "$build/tests/unit/private" "$work/private"
cat > "$work/driver.m" <<M
setappdata(0, 'bvar_repo_root', '$root');
try
  feval('$name');
  disp('__RUNMAT_PASS__');
catch err
  fprintf('__RUNMAT_FAIL__ %s\n', err.message);
end
M
start=$(date +%s.%N)
out=$(cd "$work" && RUST_LOG=off systemd-run --scope -q -p MemoryMax=1500M -p MemorySwapMax=0 --collect \
      timeout "$tmo" runmat run "$work/driver.m" 2>&1 | grep -vE 'wgpu|EGL|DRI2|windowing|No config|surfaceless')
rc=${PIPESTATUS[0]}
secs=$(printf '%.1f' "$(echo "$(date +%s.%N) - $start" | bc)")
rm -rf "$work"
if grep -q '__RUNMAT_PASS__' <<<"$out"; then status=PASS; msg=
elif m=$(grep -m1 '__RUNMAT_FAIL__' <<<"$out"); then status=FAIL; msg=${m#__RUNMAT_FAIL__ }
elif [ "$rc" = 124 ]; then status=TIMEOUT; msg="> ${tmo}s"
elif [ "$rc" = 137 ]; then status=OOM; msg="killed at 1500 MB"
else status=ERROR; msg=$(grep -m1 -iE 'error|panic|unsupported|undefined' <<<"$out" || tail -1 <<<"$out")
fi
printf '%s\t%s\t%s\t%s\n' "$status" "$name" "$secs" "$(tr '\t\n' '  ' <<<"$msg" | cut -c1-240)"
