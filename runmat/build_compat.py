#!/usr/bin/env python3
"""Build a RunMat-compatible mirror of core/, third_party/ and tests/unit/ in runmat/.build/.

The repo's MATLAB sources are left untouched. Each rewrite below works around a
RunMat 0.6.1 gap that README.md documents; MATLAB accepts both forms, so the
mirror stays valid MATLAB too. Rerun after changing any source.
"""
import re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / ".build"
REWRITES = [
    # "function name" with no argument list -> "function name()"
    ("noarg-header", re.compile(r"^(\s*function\s+(?:\[[^\]]*\]\s*=\s*|\w+\s*=\s*)?[A-Za-z_]\w*)\s*$", re.M), r"\1()"),
    # a bare call to lastwarn reads as an undefined variable when RunMat lowers a package file
    ("bare-lastwarn", re.compile(r"\blastwarn\b(?!\s*\()"), "lastwarn()"),
]

TRANSPOSE_AFTER = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_)]}.'")


def split_top(body, sep):
    """Split body on sep at bracket depth 0, outside strings and comments."""
    parts, depth, cur, i, prev = [], 0, "", 0, ""
    while i < len(body):
        ch = body[i]
        if ch in "\"'" and not (ch == "'" and prev in TRANSPOSE_AFTER):
            j = body.find(ch, i + 1)
            j = len(body) - 1 if j < 0 else j
            cur += body[i:j + 1]; i = j + 1; prev = ch; continue
        if ch == "%":
            j = body.find("\n", i)
            j = len(body) if j < 0 else j
            cur += body[i:j]; i = j; continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
        if not ch.isspace():
            prev = ch
        i += 1
    parts.append(cur)
    return parts


def fix_mixed_rows(text):
    """[A; b, c] -> [A; [b, c]]: RunMat 0.6.1 rejects a matrix literal whose rows
    have different element counts even when the concatenated widths agree."""
    out, i, prev, n = [], 0, "", 0
    while i < len(text):
        ch = text[i]
        if ch == "%" :
            j = text.find("\n", i); j = len(text) if j < 0 else j
            out.append(text[i:j]); i = j; continue
        if ch in "\"'" and not (ch == "'" and prev in TRANSPOSE_AFTER):
            j = text.find(ch, i + 1); j = len(text) - 1 if j < 0 else j
            out.append(text[i:j + 1]); i = j + 1; prev = ch; continue
        if ch == "[":
            depth, j = 1, i + 1
            while j < len(text) and depth:
                c = text[j]
                if c in "\"'" and not (c == "'" and text[j - 1] in TRANSPOSE_AFTER):
                    k = text.find(c, j + 1); j = (len(text) - 1 if k < 0 else k) + 1; continue
                depth += c == "["; depth -= c == "]"; j += 1
            inner, m = fix_mixed_rows(text[i + 1:j - 1])
            n += m
            rows = split_top(inner, ";")
            counts = {len(split_top(r, ",")) for r in rows if r.strip()}
            if len(rows) > 1 and len(counts) > 1:
                rows = [r if not r.strip() or len(split_top(r, ",")) == 1 else
                        r[:len(r) - len(r.lstrip())] + "[" + r.strip() + "]" + r[len(r.rstrip()):]
                        for r in rows]
                inner = ";".join(rows); n += 1
            out.append("[" + inner + "]"); i = j; prev = "]"; continue
        out.append(ch)
        if not ch.isspace():
            prev = ch
        i += 1
    return "".join(out), n


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    counts = {name: 0 for name, _, _ in REWRITES}
    for sub in ("core", "third_party", "tests/unit"):
        for src in (ROOT / sub).rglob("*"):
            dst = OUT / sub / src.relative_to(ROOT / sub)
            if src.is_dir():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.suffix != ".m":
                shutil.copy2(src, dst)
                continue
            text = src.read_bytes().decode("utf-8", errors="surrogateescape")  # keeps CRLF as is
            for name, pat, rep in REWRITES:
                text, n = pat.subn(rep, text)
                counts[name] += n
            text, n = fix_mixed_rows(text)
            counts["mixed-rows"] = counts.get("mixed-rows", 0) + n
            dst.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    print("built", OUT, counts)

if __name__ == "__main__":
    main()
