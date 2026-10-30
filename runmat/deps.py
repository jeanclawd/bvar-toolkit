#!/usr/bin/env python3
"""Print the core files a unit test needs, following bvar.<sub>.<fn> calls transitively.

run_one.sh copies only these into the test's working directory. RunMat 0.6.1
compiles every file of a +package folder it touches, so one file it cannot
handle (or one that overflows its stack) breaks unrelated tests; giving each
test only its own closure keeps failures attributable.
"""
import re, sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent / ".build"
CALL = re.compile(r"\bbvar\.(\w+)\.(\w+)")

def closure(test):
    todo = [BUILD / "tests" / "unit" / f"{test}.m"]
    priv = BUILD / "tests" / "unit" / "private"
    src = todo[0].read_text(errors="replace") if todo[0].exists() else ""
    todo += [f for f in priv.glob("*.m") if re.search(rf"\b{f.stem}\b", src)] if priv.is_dir() else []
    seen, need = set(), set()
    while todo:
        f = todo.pop()
        if f in seen or not f.exists():
            continue
        seen.add(f)
        for sub, fn in CALL.findall(f.read_text(errors="replace")):
            dep = BUILD / "core" / "+bvar" / f"+{sub}" / f"{fn}.m"
            if dep.exists() and dep not in need:
                need.add(dep); todo.append(dep)
    return sorted(need)

if __name__ == "__main__":
    for p in closure(sys.argv[1]):
        print(p.relative_to(BUILD / "core"))
