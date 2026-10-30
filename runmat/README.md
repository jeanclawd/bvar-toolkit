# Running bvar-toolkit on RunMat

This branch tests whether bvar-toolkit runs on [RunMat](https://runmat.org), an open-source
MATLAB-compatible runtime, without changing the toolkit's own code. Everything RunMat-specific
lives in this folder. `core/`, `third_party/` and `tests/` are untouched.

Tested with `runmat 0.6.1` on Linux x86-64, CPU only.

## How to run

```bash
runmat/run_all.sh            # every unit test, one RunMat process each -> runmat/results/results.tsv
runmat/run_one.sh test_vech  # a single test; prints STATUS, test, seconds, detail
```

`run_one.sh` caps each RunMat process at 1.5 GB and 300 s (`systemd-run --scope -p
MemoryMax=1500M`, `timeout`): an uncapped RunMat can exhaust a small machine's memory.

## What the harness does

| File | Role |
|---|---|
| `build_compat.py` | Builds `runmat/.build/`, a mirror of `core/`, `third_party/` and `tests/unit/` with the rewrites below. Each rewrite is valid MATLAB too. |
| `deps.py` | Lists the core files a test reaches through `bvar.<sub>.<fn>` calls, transitively. |
| `run_one.sh` | Makes a temporary working directory holding the test, its private helpers, its core closure (from `deps.py`), `third_party/` and the shims, then runs a driver that calls the test and reports PASS or the error. |
| `shims/` | `setappdata`, `getappdata`, `lastwarn`, `isstruct`, which RunMat 0.6.1 lacks. |
| `run_all.sh` | Runs every `tests/unit/test_*.m` through `run_one.sh` and tallies the results. |

Rewrites in the mirror (counts across core, third_party and tests/unit):

| Rewrite | Count | Why |
|---|---|---|
| `function name` → `function name()` | 75 | RunMat rejects a declaration with no argument list (`Syntax error at position 0: expected '('`). |
| `[A; b, c]` → `[A; [b, c]]` | 5 | RunMat rejects a matrix literal whose rows have different element counts, even when the widths agree (`RunMat:AggregateShapeMismatch`). |
| `lastwarn` → `lastwarn()` | 1 | Inside a package function a bare call lowers as an undefined variable. |

## RunMat issues found

Each one has a minimal reproduction; run them with `runmat run repro.m`.

1. **A matrix literal whose rows have different element counts fails to lower.** MATLAB gives
   a 4×3 matrix here:
   ```matlab
   F = [ones(2,3); eye(2), zeros(2,1)]   % RunMat: tensor literal rows must have consistent column counts
   ```
   `[ones(2,3); [eye(2), zeros(2,1)]]` and `vertcat(...)` work. bvar-toolkit builds its
   companion matrix this way (`core/+bvar/+util/simulate_var.m`).
2. **One file RunMat cannot lower blocks its whole package folder.** With `simulate_var.m` (issue 1)
   or `report.m` (issue 6) present, even `bvar.util.build_lags`, which has neither problem, fails
   with that file's error.
3. **A no-argument declaration without parentheses does not parse.** `function test_x` (75
   files in this repo) fails with `expected '('`.
4. **A folder reached through `addpath` fails to compile as soon as one of its functions assigns
   an optional argument under `if nargin < k`.** Every function in that folder then fails with
   `local may be read before it is assigned`, even the ones that never touch `nargin`. The same
   files work when they sit in the working directory:
   ```matlab
   % lib/g.m:  function y = g(x)        y = 2*x;               end
   % lib/h.m:  function y = h(x, a)     if nargin < 2, a = 1; end; y = a*x;   end
   addpath('lib'); disp(g(21))          % RunMat: Could not compile ... g.m: local may be read before it is assigned
   ```
   The harness therefore copies each test's code into its working directory instead of using
   `addpath`. A package folder reached through a symlink fails the same way.
5. **Lowering the whole `+bvar` package overflows the stack.** With all of `core/+bvar` in the
   working directory, a call to `bvar.util.build_lags` aborts with `thread 'main' has overflowed
   its stack`. The trigger is in `+sv` (`ksc_rw_h0.m`, `ksc_ar1_mean.m`, `nu_studentt.m`) and
   `+samplers` (`nu_psi_ng.m`). Each crashes the process when it sits beside `+util`, and none
   of the cut-down versions we tried reproduces it alone. The harness copies only the files each
   test reaches.
6. **Missing builtins:** `setappdata`, `getappdata`, `lastwarn`, `isstruct`, `psi` (digamma).
   `sum` of a sparse matrix is unsupported. `datetime('now')` fails with `unable to parse
   date/time text 'now'`.
7. **A `containers.Map` held in a `persistent` variable fails when indexed**
   (`RunMat:SliceNonTensor`). A persistent struct works, so the appdata shim uses one.

8. **Calling a script by bare name from inside a function fails**, even when the script sits in
   the working directory:
   ```matlab
   % myscript.m:  x = 41; disp(x+1)
   % t.m:         function t()  myscript;  end
   t();          % RunMat: undefined variable 'myscript' (RunMat:UndefinedVariable)
   ```
   Most of the tests that check the library against the published replication code work this
   way: they copy a legacy script to a temporary folder, `addpath` it, and run it by name.

What works: `+package` functions resolve (from the working directory), `rng`, `randn`,
`gamrnd`, `normpdf`, `fminbnd`, `assert`, `feval`, `containers.Map` outside `persistent`,
sparse construction with `speye`/`spdiags`.

## Results (runmat 0.6.1, 30 Oct 2026)

No unit test passes yet. 75 unit tests: 0 pass, 41 fail (an error raised inside the test), 34 error (RunMat could not load or crashed).

| Cause | Tests |
|---|---|
| Stack overflow while lowering (issue 5) | 13 |
| Script or helper called by bare name (issue 8) | 10 |
| Indexing gaps ("Slicing only supported on tensors") | 8 |
| Process crash (core dump) | 7 |
| Type conversion error ("... to f64") | 7 |
| Indexed assignment shape mismatch | 4 |
| Ragged-row matrix literal (issue 1) | 4 |
| Index out of bounds | 4 |
| `if` on a non-scalar logical (MATLAB uses all()) | 3 |
| Compile failure in replication code (issue 4) | 3 |
| Sparse matrix unsupported in kron/mldivide/sum | 2 |
| Dimension mismatch | 2 |
| mtimes on unsupported operand types | 2 |
| Parse failure | 2 |
| Other: fill value must be a scalar  | 1 |
| Other: unable to parse numeric value 'GDP' on line 1 column 2  | 1 |
| Other: semantic function bvar.sv.sv0_params expected 2 inputs, got  | 1 |
| Other: unable to parse date/time text 'now'  | 1 |

The four ragged-literal failures are rows split across lines, which `build_compat.py` does not rewrite yet. Per-test detail: `results/results.tsv`. Rerun with `runmat/run_all.sh`.

Next steps, in order of tests unblocked: avoid the stack overflow (13 tests), find a way to run the legacy scripts the equivalence tests call (10), then work through the indexing gaps.
