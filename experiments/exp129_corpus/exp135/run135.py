"""exp135 — third independent corpus (corpus4).

exp134 found a syntax/methodology split, but that split was made AFTER
seeing the data. This run measures it on 12 files from 7 repos that have
never been used in exp129-134, with the hypothesis written down first
(PREREG.md).

Design note discovered while building this: the shipped pipeline (cli.scan)
DROPS methodology findings by design since exp134, and its audit line
reports them as "dropped (no line)" -- which is the wrong label, they are
dropped because they are not shipped, not because they lack a line. So
running only cli.scan cannot test H2: the denominator is gone.

Therefore this script collects BOTH:
    raw   = every rule hit before any gate
    gated = what a customer actually sees
That is the only way to confirm "methodology is not shippable" rather than
merely assuming it.
"""
import ast, json, pathlib, sys, os

ROOT = "/data/workspace/luoshen-o1"
sys.path.insert(0, ROOT + "/overseas")
os.chdir(ROOT)

from evalguard import cli, classes
from evalguard import rules as _rules
from evalguard import pro_rules as _pro

CORPUS = pathlib.Path(ROOT + "/experiments/exp129_corpus/exp135/corpus4")


def raw_scan(path):
    """Every rule hit, before any gate."""
    src = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"eg_id": "PARSE", "severity": "blocker", "line": e.lineno,
                 "hit": str(e.msg), "title": "SyntaxError"}]
    out = []
    _rules._SRC[0] = src
    for fn in _rules.RULES:
        try:
            hits = fn(tree, src, path)
        except Exception as e:
            out.append({"eg_id": fn.meta["eg_id"], "severity": "CRASH",
                        "line": 0, "hit": "rule error: %s" % e,
                        "title": fn.meta.get("title", "")})
            continue
        for h in hits:
            out.append({"eg_id": fn.meta["eg_id"],
                        "severity": fn.meta.get("severity", ""),
                        "line": h.get("line"), "hit": h.get("hit", ""),
                        "title": fn.meta.get("title", "")})
    for fn in _pro.PRO_RULES:
        try:
            hits = fn(tree, src, path)
        except Exception as e:
            out.append({"eg_id": fn.meta["eg_id"], "severity": "CRASH",
                        "line": 0, "hit": "rule error: %s" % e,
                        "title": fn.meta.get("title", "")})
            continue
        for h in hits:
            out.append({"eg_id": fn.meta["eg_id"],
                        "severity": fn.meta.get("severity", ""),
                        "line": h.get("line"), "hit": h.get("hit", ""),
                        "title": fn.meta.get("title", "")})
    return out


def main():
    files = sorted(CORPUS.glob("*.py"))
    raw, gated = [], []
    for f in files:
        for r in raw_scan(str(f)):
            raw.append({"file": f.name, **r})
        for r in cli.scan(str(f)):
            for h in r.get("hits", []):
                gated.append({"file": f.name, "eg": r["eg_id"],
                              "sev": r.get("severity"), "line": h.get("line"),
                              "hit": h.get("hit", ""), "title": r.get("title", "")})

    # classify
    for r in raw + gated:
        eg = r.get("eg_id") or r.get("eg")
        r["class"] = ("experimental" if eg in classes.EXPERIMENTAL_1_OF_1
                      else classes.cls_of(eg) if eg in classes.SYNTAX
                      or eg.startswith("EG") else "meta")
    # fix: cls_of returns syntax only for SYNTAX members
    for r in raw + gated:
        eg = r.get("eg_id") or r.get("eg")
        if eg in classes.EXPERIMENTAL_1_OF_1:
            r["class"] = "experimental"
        elif eg in classes.SYNTAX:
            r["class"] = "syntax"
        elif eg in ("EG000", "PARSE"):
            r["class"] = "meta"
        else:
            r["class"] = "methodology"

    json.dump(raw, open("experiments/exp129_corpus/exp135/raw135.json", "w"),
              indent=1, ensure_ascii=False)
    json.dump(gated, open("experiments/exp129_corpus/exp135/gated135.json", "w"),
              indent=1, ensure_ascii=False)

    from collections import Counter
    print("files:", len(files))
    print("\n== RAW by class ==")
    for k, v in Counter(r["class"] for r in raw).most_common():
        print("  %-14s %d" % (k, v))
    print("\n== RAW by rule ==")
    for k, v in Counter((r.get("eg_id") or r.get("eg")) for r in raw).most_common():
        print("  %-8s %d" % (k, v))
    print("\n== crashes ==", sum(1 for r in raw if r["severity"] == "CRASH"))
    print("== parse errors ==", sum(1 for r in raw if r.get("eg_id") == "PARSE"))
    print("\n== GATED by class ==")
    for k, v in Counter(r["class"] for r in gated).most_common():
        print("  %-14s %d" % (k, v))
    print("\n== syntax findings (the shipped set) ==")
    for r in raw:
        if r["class"] in ("syntax", "experimental"):
            print("  %-46s %-7s L%-5s %s" % (r["file"][:46], r.get("eg_id") or r.get("eg"),
                                             r.get("line"), str(r.get("hit"))[:60]))


if __name__ == "__main__":
    main()
