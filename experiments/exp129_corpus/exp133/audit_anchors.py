"""Audit every finding against its declared anchor spec (exp133).

The spec is a CLAIM. This script is the test of that claim. For each
finding it asks three questions in order:

  Q1  Does the rule declare what it accuses at all?
  Q2  Is there a node of the declared type AT the pinned line?
  Q3  Does that node's own source contain one of the declared keys?

A finding that fails Q2 is pinned to code of the wrong kind.
A finding that fails Q3 is pinned to the right kind of code but the code
does not actually say what the rule says it says.

Neither is a "false positive" in the usual sense: the rule's claim may be
true at file level. What fails is the ARROW, not the claim. But a finding
whose arrow points somewhere else is unusable -- the reader opens the line,
finds nothing, and discards a true finding.
"""
import ast
import json
import pathlib
import sys
import collections

sys.path.insert(0, "/data/workspace/luoshen-o1/overseas")
from evalguard import cli                      # noqa: E402
from evalguard.cli import scan                 # noqa: E402
from evalguard.spec import ANCHOR_SPEC, spec_for  # noqa: E402

cli.PRO_ON[0] = True

CORPUS = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/corpus2")


def nodes_at_line(tree, line):
    """Nodes whose own start line == `line`."""
    out = []
    for n in ast.walk(tree):
        if getattr(n, "lineno", None) == line:
            out.append(n)
    return out


def seg(src, node):
    try:
        return ast.get_source_segment(src, node) or ""
    except Exception:
        return ""


def audit_file(path):
    src = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    # scan() is rule-level; each rule carries a `hits` list of individual
    # pins. Auditing the rule dict instead of the hits would read line=None
    # for every finding and report 100% WRONG_NODE -- a measurement that is
    # wrong because of the reader, not because of the rules. (v1 bug.)
    findings = []
    for r in scan(str(path)):
        for h in (r.get("hits") or [{}]):
            findings.append(dict(r, line=h.get("line"), hit=h.get("hit")))
    rows = []
    for f in findings:
        eg = f.get("eg_id", "?")
        line = f.get("line")
        s = spec_for(eg)
        row = dict(file=pathlib.Path(path).name, eg=eg,
                   sev=f.get("severity", "?"), line=line,
                   hit=(f.get("hit") or "")[:60])
        if s is None:
            row.update(verdict="NO_SPEC", why="rule declares nothing")
            rows.append(row)
            continue
        if s["kind"] == "module":
            # The honest form is NO pin. Anything > 1 is exp130's lie.
            ok = (line in (None, 0, 1))
            row.update(verdict="MODULE_OK" if ok else "MODULE_PINNED",
                       why="module claim, no pin" if ok else
                           f"module claim pinned to line {line}")
            rows.append(row)
            continue
        cands = [n for n in nodes_at_line(tree, line)
                 if isinstance(n, s["node"])]
        if not cands:
            row.update(verdict="WRONG_NODE",
                       why=f"no {[t.__name__ for t in s['node']]} at line {line}")
            rows.append(row)
            continue
        keys = tuple(k.lower() for k in s["keys"])
        hit = None
        for n in cands:
            # exp133 v2: v1 used the node's WHOLE source segment. An
            # ast.For segment is the entire loop body, so a pin on the
            # header line `for task in ...:` was "proven" by a `continue`
            # twenty lines below -- text the reader never sees. The proof
            # must use what the reader is actually sent to: the line.
            lines = src.splitlines()
            t = lines[line - 1] if isinstance(line, int) and 0 < line <= len(lines) \
                else seg(src, n)
            low = t.lower()
            if not keys or any(k in low for k in keys):
                hit = n
                break
        if hit is None:
            row.update(verdict="UNPROVEN",
                       why="node found but its source names none of "
                           f"{list(s['keys'])[:4]}")
        else:
            row.update(verdict="PROVEN", why=seg(src, hit).strip()[:60])
        rows.append(row)
    return rows


def main():
    files = sorted(CORPUS.glob("*.py"))
    rows = []
    for f in files:
        try:
            rows.extend(audit_file(f))
        except Exception as e:
            rows.append(dict(file=f.name, eg="CRASH", sev="-", line=None,
                             hit=str(e)[:60], verdict="CRASH", why=""))
    out = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/exp133")
    out.mkdir(exist_ok=True)
    (out / "audit133.json").write_text(json.dumps(rows, indent=1,
                                                  ensure_ascii=False))

    v = collections.Counter(r["verdict"] for r in rows)
    print("files:", len(files), " findings:", len(rows))
    print("verdicts:", dict(v))
    print()
    print(f"{'eg':7s} {'PROVEN':>6s} {'UNPROV':>6s} {'WRONG':>5s} "
          f"{'MODPIN':>6s} {'NO_SPEC':>7s}   why")
    per = collections.defaultdict(collections.Counter)
    for r in rows:
        per[r["eg"]][r["verdict"]] += 1
    for eg in sorted(per):
        c = per[eg]
        print(f"{eg:7s} {c['PROVEN']:6d} {c['UNPROVEN']:6d} {c['WRONG_NODE']:5d} "
              f"{c['MODULE_PINNED']:6d} {c['NO_SPEC']:7d}   "
              f"{ANCHOR_SPEC.get(eg, {}).get('note', '')[:40]}")
    print()
    tot = len(rows)
    good = v["PROVEN"] + v["MODULE_OK"]
    print(f"proven-or-honest-module: {good}/{tot} = {good/max(tot,1):.1%}")
    print()
    print("--- failures ---")
    for r in rows:
        if r["verdict"] in ("UNPROVEN", "WRONG_NODE", "MODULE_PINNED", "NO_SPEC"):
            print(f"{r['eg']:7s} {r['verdict']:13s} {r['file'][:38]:38s} "
                  f"L{r['line']}  {r['why'][:52]}")


if __name__ == "__main__":
    main()
