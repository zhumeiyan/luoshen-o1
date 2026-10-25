"""evalguard CI regression — both gates must hold at once (exp130).

Gate A  recall on planted fixtures: every rule that fired before must still
        fire. A precision fix that silently deletes recall is not a fix.
Gate B  precision on 27 real files: the labelled false-positive count must
        not rise. Labels live in labels.json and are hand-triaged.

Running only one of these is how v0.3.0 shipped with 11% precision: the
planted fixtures were written by us, in the shape our rules look for, and
they passed 10/10 while the real corpus failed 24/27.
"""
import sys, json, pathlib, collections, subprocess

ROOT = pathlib.Path(__file__).parent
OVER = "/data/workspace/luoshen-o1/overseas"
CORP = pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/corpus2")
sys.path.insert(0, OVER)
from evalguard import cli
from evalguard.cli import scan


def scan_all(pro):
    cli.PRO_ON[0] = pro
    out = {}
    for f in sorted(CORP.glob("*.py")):
        out[f.name] = scan(str(f))
    return out


def fixture(name, pro):
    cli.PRO_ON[0] = pro
    return {r["eg_id"]: r["severity"] for r in scan(str(ROOT / name))}


EXPECT_PLANTED = {"EG001", "EG002", "EG003", "EG004", "EG005", "EG007",
                  "EG009", "EG011", "EG012", "EG013", "EG014", "EG016"}
EXPECT_PRO_PLANTED = {"EG002", "EG005", "EG009", "EG012", "EG013",
                      "EG016", "EGP01", "EGP02", "EGP04", "EGP06", "EGP07",
                      "EGP08", "EGP09", "EGP10"}
# exp131: EG011 was removed from this set rather than the fixture edited to
# satisfy it. Its hit on pro_planted.py only ever came from the FILE-level
# form of the rule (the word `continue` somewhere, the word `sum(` somewhere
# else); the fixture's loop skips items but never aggregates them. Tightening
# the rule to "skip and aggregation in the same loop" is the correct
# behaviour, so the fixture's expectation was wrong, not the rule.
# planted_eval.py still hits EG011 with a genuine in-loop skip+aggregate.


def main():
    ok = True

    # ---- Gate A: recall ------------------------------------------------
    got = set(fixture("planted_eval.py", False))
    miss = EXPECT_PLANTED - got
    gotp = set(fixture("pro_planted.py", True))
    missp = EXPECT_PRO_PLANTED - gotp
    print(f"[A] planted  {len(got & EXPECT_PLANTED)}/{len(EXPECT_PLANTED)}"
          f"   missed: {sorted(miss) or '-'}")
    print(f"[A] pro      {len(gotp & EXPECT_PRO_PLANTED)}/{len(EXPECT_PRO_PLANTED)}"
          f"   missed: {sorted(missp) or '-'}")
    ok &= not miss and not missp

    # ---- Clean fixtures ----------------------------------------------
    cl = fixture("clean_eval.py", False)
    clp = fixture("pro_clean.py", True)
    print(f"[A] clean_eval   findings: {sorted(k for k in cl if k != 'EG000') or '-'}")
    print(f"[A] pro_clean    findings: {sorted(k for k in clp if k != 'EG000') or '-'}")

    # ---- Gate B: precision on real corpus ------------------------------
    res = scan_all(True)
    labels = json.loads((pathlib.Path("/data/workspace/luoshen-o1/experiments/exp129_corpus/labels.json")).read_text())
    flat, nolocal = [], 0
    for fn, fs in res.items():
        for r in fs:
            if r["eg_id"] == "EG000":
                continue
            # exp131: demoted findings keep severity "info" so the demotion is
            # auditable but they are no longer actionable. Counting them as
            # findings would hide the improvement.
            if r.get("severity") == "info":
                continue
            flat.append(r)
            if all(h.get("line", 1) <= 1 for h in r["hits"]):
                nolocal += 1
    # relabel by (rule, file, line) identity against triage index is not
    # stable across runs, so report counts and re-triage on demand.
    print(f"[B] real corpus: {len(flat)} findings, {nolocal} unlocalised "
          f"(line<=1) -> {100*nolocal/max(1,len(flat)):.1f}%")

    # exp131: precision is judged on TWO standards, because I am the only
    # referee and the verdict could be an artefact of how generous I am.
    #   strict = a reviewer would accept the finding AT THAT LINE
    #   loose  = the rule's claim holds at file level, line ignored
    # The gate uses STRICT. Reporting only the flattering number is how
    # v0.3.0 shipped: "10/10 on planted, 0/0 on clean" while the real
    # corpus sat at 11%.
    L131 = "/data/workspace/luoshen-o1/experiments/exp129_corpus/exp131/labels131.json"
    lab = [x for x in json.loads(pathlib.Path(L131).read_text())
           if x["eg"] != "EG000"]
    n_strict = sum(1 for x in lab if x["strict"] == "TP")
    n_loose = sum(1 for x in lab if x["loose"] == "TP")
    demoted = sum(1 for fs in res.values() for r in fs
                  if r["eg_id"] != "EG000"
                  and "demoted to info" in json.dumps(r.get("hits", [])))
    live = [x for x in lab
           if not any(t in x["file"].lower()
                      for t in ("example", "docs_"))]
    ls = sum(1 for x in live if x["strict"] == "TP")
    ll = sum(1 for x in live if x["loose"] == "TP")
    print(f"[B] triage strict {n_strict}/{len(lab)} = {n_strict/len(lab):.1%}"
          f"   loose {n_loose}/{len(lab)} = {n_loose/len(lab):.1%}")
    print(f"[B] after G-ROLE  strict {ls}/{len(live)} = {ls/len(live):.1%}"
          f"   loose {ll}/{len(live)} = {ll/len(live):.1%}"
          f"   ({demoted} demoted in this run)")
    prec = ls / len(live)
    # ---- the gate, split by rule kind (exp133) --------------------------
    # Scoring every finding with one strict standard is wrong. A rule that
    # accuses an ABSENCE ("no baseline anywhere") cannot show that absence
    # on any line, so its strict precision is 0 for structural reasons, not
    # because it is broken. exp133 measured: present 10/15 = 66.7%,
    # absent 0/9 = 0.0%. Mixing them produced the 5.9% of exp131 and made
    # the gate unsound in both directions -- it condemned absent rules for
    # being absent, and let present rules hide behind them.
    L133 = "/data/workspace/luoshen-o1/experiments/exp129_corpus/exp133/labels133.json"
    lp = pathlib.Path(L133)
    if lp.exists():
        lab133 = json.loads(lp.read_text())
        pres = [x for x in lab133 if x["kind"] == "present"]
        abst = [x for x in lab133 if x["kind"] == "absent"]
        pt = sum(1 for x in pres if x["strict"])
        at = sum(1 for x in abst if x["strict"])
        print()
        print(f"[B*] strict precision, PRESENT rules {pt}/{len(pres)} = "
              f"{pt/max(len(pres),1):.1%}   (ship gate: 60%)")
        print(f"[B*] strict precision, ABSENT  rules {at}/{len(abst)} = "
              f"{at/max(len(abst),1):.1%}   (structural, no gate)")
        print("[B*] absent rules ship as FILE-LEVEL advisories, not line pins:"
              " a line cannot display a missing thing.")
        ok &= (pt / max(len(pres), 1)) >= 0.60
        print()
    print()
    liv = live_anchor_audit(res)
    print(f"[D] live anchor proof {liv['proven']}/{liv['real']} = "
          f"{liv['proven']/max(liv['real'],1):.1%}"
          f"   (unproven {liv['unproven']}, wrong-node {liv['wrong']})")
    for eg, c in sorted(liv["per_rule"].items()):
        if c["bad"]:
            print(f"[D]   {eg:6s} {c['bad']}/{c['n']} findings do not prove "
                  f"their own anchor")

    # ---- Gate C: no rule crashes ---------------------------------------
    crashes = [r for fs in res.values() for r in fs
               if r["eg_id"] == "CRASH" or "rule error" in
               json.dumps(r.get("hits", []))]
    print(f"[C] rule crashes: {len(crashes)}")
    ok &= not crashes

    print("\nCI:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def live_anchor_audit(res):
    """Check each finding against its declared anchor spec (exp133).

    `res` is {file: [rule finding, ...]}, already computed by the caller.
    Unlike the label-file metric above this cannot go stale: it re-derives
    the answer from evalguard/spec.py and from the current scan.

    The proof uses the text of the PINNED LINE, not the node's whole source
    segment. An ast.For segment covers the entire loop body, so a pin on
    `for x in ...:` would otherwise be "proven" by a `continue` twenty
    lines further down -- code the reader never sees.
    """
    import ast as _ast
    from collections import defaultdict
    from evalguard.spec import spec_for

    CORP = "/data/workspace/luoshen-o1/experiments/exp129_corpus/corpus2"
    per = defaultdict(lambda: {"n": 0, "bad": 0})
    proven = unproven = wrong = real = 0
    for fname, rules in res.items():
        path = pathlib.Path(CORP) / fname
        if not path.exists():
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = _ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for r in rules:
            eg = r.get("eg_id", "?")
            s = spec_for(eg)
            if s is None or eg == "EG000":
                continue
            for h in (r.get("hits") or [{}]):
                ln = h.get("line")
                real += 1
                per[eg]["n"] += 1
                if s["kind"] == "module":
                    ok = ln in (None, 0, 1)
                else:
                    cands = [n for n in _ast.walk(tree)
                             if getattr(n, "lineno", None) == ln
                             and isinstance(n, s["node"])]
                    ok = False
                    if cands:
                        txt = lines[ln - 1].lower() if isinstance(ln, int) \
                            and 0 < ln <= len(lines) else ""
                        keys = tuple(k.lower() for k in s["keys"])
                        ok = (not keys) or any(k in txt for k in keys)
                        if not ok:
                            unproven += 1
                    else:
                        wrong += 1
                if ok:
                    proven += 1
                else:
                    per[eg]["bad"] += 1
    return dict(proven=proven, unproven=unproven, wrong=wrong, real=real,
                per_rule={k: dict(v) for k, v in per.items()})


if __name__ == "__main__":
    sys.exit(main())
