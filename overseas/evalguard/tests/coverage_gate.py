"""Coverage gate (exp135).

Why this file exists: canon #613. exp129-135 gated exclusively on precision.
Six rounds of pruning bought 90% precision and, silently, a tool that is
mute on professional code: 0.02-0.03 findings per KB, and no findings at
all on 9 of 12 corpus4 files. Precision alone cannot see that.

This gate measures three numbers that precision cannot:

    per_kb        findings per 1000 bytes of real code
    silent_files  fraction of files with zero findings
    concentration largest single file's share of all findings

A linter that is mute is as unsellable as a linter that cries wolf, for the
opposite reason, and neither failure shows up in a precision number.
"""
import sys, json, pathlib, os, argparse

ROOT = "/data/workspace/luoshen-o1"
sys.path.insert(0, ROOT + "/overseas")
os.chdir(ROOT)

from evalguard import cli
from evalguard.classes import SYNTAX

# Measured on exp135 (corpus1+corpus3+corpus4, 55 files, 1.09 MB):
#   per_kb 0.024 / 0.031 / 0.020 ; silent 9/12 on corpus4 ; concentration 15/17
# These are reported, not yet gated: one measurement is not a threshold.
MIN_PER_KB = 0.0
MAX_SILENT = 1.0
MAX_CONCENTRATION = 1.0


def measure(d):
    files = sorted(pathlib.Path(d).glob("*.py"))
    n = 0
    byt = 0
    per = {}
    for f in files:
        byt += f.stat().st_size
        k = 0
        for r in cli.scan(str(f)):
            if r["eg_id"] in SYNTAX:
                k += len(r.get("hits", []))
        per[f.name] = k
        n += k
    silent = sum(1 for v in per.values() if v == 0)
    top = max(per.values()) if per else 0
    return {
        "corpus": str(d), "files": len(files), "bytes": byt, "findings": n,
        "per_kb": round(n / max(1, byt // 1000), 4),
        "silent_files": silent,
        "silent_frac": round(silent / max(1, len(files)), 3),
        "concentration": round(top / n, 3) if n else None,
        "top_file": max(per, key=per.get) if per else None,
        "per_file": per,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    rows = [measure(d) for d in a.dirs]
    for r in rows:
        print("%-58s files=%-3d bytes=%-8d findings=%-3d per_kb=%.4f "
              "silent=%d/%d conc=%s" % (
                  r["corpus"][-58:], r["files"], r["bytes"], r["findings"],
                  r["per_kb"], r["silent_files"], r["files"],
                  r["concentration"]))
    json.dump(rows, open("overseas/evalguard/tests/coverage_last.json", "w"),
              indent=1)
    bad = [r for r in rows if r["per_kb"] < MIN_PER_KB
           or r["silent_frac"] > MAX_SILENT
           or (r["concentration"] or 0) > MAX_CONCENTRATION]
    if bad:
        print("COVERAGE FAIL", [r["corpus"] for r in bad])
        return 1
    print("COVERAGE OK (thresholds not yet armed — reporting only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
