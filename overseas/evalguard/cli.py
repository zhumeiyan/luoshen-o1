import ast, sys, json, argparse, pathlib
from .classes import shipped

PRO_ON = [False]


def scan(path):
    src = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"eg_id": "EG000", "severity": "blocker", "title": "SyntaxError",
                 "canon": [], "hits": [{"line": e.lineno or 0, "hit": str(e.msg)}]}]
    out = []
    from .rules import RULES
    from . import rules as _r
    _r._SRC[0] = src          # rules need raw source for cross-line checks
    for fn in RULES:
        m = fn.meta
        try:
            hits = fn(tree, src, path)
        except Exception as e:
            # exp129: a crashing rule used to inherit the rule's own severity,
            # so it was reported as a BLOCKER. A broken rule then looked
            # exactly like a real finding -- 27 phantom blockers in one run.
            out.append({**m, "severity": "info",
                        "hits": [{"line": 0, "hit": f"rule error: {e}"}]})
            continue
        if hits:
            out.append({**m, "hits": hits})
    if PRO_ON[0]:
        from .pro_rules import PRO_RULES
        for fn in PRO_RULES:
            m = fn.meta
            try:
                hits = fn(tree, src, path)
            except Exception as e:
                out.append({**m, "severity": "info",
                            "hits": [{"line": 0, "hit": f"rule error: {e}"}]})
                continue
            if hits:
                out.append({**m, "hits": hits})
    if not PRO_ON[0]:
        # exp135: classes.SYNTAX names the rules we are willing to sell, and
        # it includes EGP01, which lives in the PRO pack. The shipped set was
        # therefore only reachable with --pro: the product as installed did
        # not run one of its own advertised rules. A rule that is in the
        # sellable set must run by default.
        from .pro_rules import PRO_RULES as _PR
        from .classes import SYNTAX as _SYN
        for fn in _PR:
            if fn.meta.get("eg_id") not in _SYN:
                continue
            m = fn.meta
            try:
                hits = fn(tree, src, path)
            except Exception as e:
                out.append({**m, "severity": "info",
                            "hits": [{"line": 0, "hit": f"rule error: {e}"}]})
                continue
            if hits:
                out.append({**m, "hits": hits})
    return _gate(out, src, path)

def _is_demo_file(path):
    """G-ROLE (exp131): is this file a demonstration, not production eval code?

    Measured, not guessed: on the 27-file authoritative corpus, findings on
    files whose path carries a demo token (examples/ docs/ demo/ template/)
    were false under BOTH triage standards -- 0 true out of 2, strict and
    loose alike. A demo file exists to show an API shape, so every
    production-grade expectation we hold (report a baseline, report spread)
    is a category error there.

    Demoted rather than deleted, and counted, so the demotion is auditable
    instead of invisible.
    """
    low = str(path).lower().replace("\\", "/")
    toks = ("example", "/docs/", "docs_", "/demo", "demo_", "template",
            "tutorial", "sample_", "/samples/")
    return any(t in low for t in toks)


def _spec_kind(eg_id):
    """What kind of claim does this rule make? (exp134)

    Falls back to "present" for rules with no declaration, so an undeclared
    rule is judged by the stricter line standard rather than quietly
    escaping to file level. That is the conservative direction.
    """
    try:
        from .spec import ANCHOR_SPEC
        return ANCHOR_SPEC.get(eg_id, {}).get("kind", "present")
    except Exception:
        return "present"


def _gate(out, src, path):
    """G-LINE: a finding must carry an evidence line.

    exp130: 5 of 6 surviving blockers on real corpora pointed at line 1,
    the module docstring. Such a row is unactionable and is visually
    identical to a real hit. Drop it and count it, so the drop rate is
    auditable rather than invisible.
    """
    from . import context
    idx = context.build(src, path)
    # exp135: `dropped` used to absorb TWO different reasons -- no evidence
    # line, AND 'rule is not in the shipped set'. The audit line then
    # reported both as 'dropped (no line)', which is simply the wrong label:
    # on corpus4 it hid the fact that 26 methodology findings were removed
    # by policy, not for lack of a line. Counting them apart is what made
    # the H2 denominator visible again.
    keep, dropped, rescued, demoted, unproven, filelevel = [], 0, 0, 0, 0, 0
    notshipped = 0
    for r in out:
        hits = r.get("hits", [])
        # ---- exp134 R1/R2 -------------------------------------------------
        # A rule whose spec says kind="absent" accuses a MISSING thing and a
        # rule with kind="module" accuses the whole file. Neither has a line
        # that can display the accusation: exp133 measured absent-rule
        # findings at 0/9 strict true when judged at the pinned line, not
        # because the claim is false but because no line can exhibit an
        # absence. Pinning them was the measurement artifact.
        # So: present the claim at file scope, with line=None, and say so.
        _k = _spec_kind(r["eg_id"])
        if _k in ("absent", "module"):
            if not shipped(r["eg_id"]) and r["eg_id"] != "EG000":
                notshipped += 1
                continue
            filelevel += 1
            keep.append({**r, "hits": [
                {"line": None, "kind": _k, "scope": "file",
                 "hit": ("file-level claim (no line can exhibit this): "
                         + hits[0].get("hit", ""))[:150]}]})
            continue
        # ---- end exp134 ---------------------------------------------------
        # exp132: a hit that carries kind="module" was PROVEN to have no
        # localisable evidence node (anchors.resolve checked and failed).
        # Keep it, but keep it honest -- do not rescue it onto a nearby
        # emit call, which is exactly how we ended up pointing at
        # `logger.info("GPU memory: ...")`.
        good = []
        for h in hits:
            ln = h.get("line")
            if isinstance(ln, int) and ln > 1:
                good.append(h)
            elif h.get("kind") == "module":
                good.append({**h, "line": None})
                unproven += 1
        if not good and idx is not None and not any(
                h.get("kind") for h in hits):
            # exp130: dropping every unlocalised finding purged 39 of 51 on
            # the real corpus. Some of those are true -- an *absence* rule
            # (no baseline, no variance) legitimately cannot point at a
            # symbol, because the symbol is missing. Its evidence line is
            # the line of the anchor that lacks the companion.
            ln = _anchor_line(r["eg_id"], idx)
            if ln:
                good = [{"line": ln, "kind": "rescue",
                         "hit": (hits[0].get("hit", "") +
                                 f" (anchor {r['eg_id']})")[:120]}]
                rescued += 1
        if good and idx is not None and _NEEDS_SCOPE.get(r["eg_id"]):
            good = [h for h in good if h.get("line") is None
                     or idx.scope_has_metric(h["line"])]
            if not good:
                dropped += 1
                keep.append(_audit("scope", 1, 0))
                continue
        if good and _is_demo_file(path) and r["eg_id"] != "EG000":
            demoted += 1
            keep.append({**r, "severity": "info",
                         "hits": [{"line": good[0]["line"],
                                   "hit": "demo file — demoted to info "
                                          f"({good[0].get('hit','')})"[:110]}]})
            continue
        if good and not shipped(r["eg_id"]) and r["eg_id"] != "EG000":
            notshipped += 1
            continue
        if good:
            keep.append({**r, "hits": good})
        else:
            dropped += 1
    if dropped or rescued or demoted or unproven or notshipped or filelevel:
        keep.append({"eg_id": "EG000", "canon": [], "severity": "info",
                     "title": "audit: evidence-line gate",
                     "hits": [{"line": 0,
                               "hit": f"{dropped} dropped (no line), "
                                      f"{rescued} rescued via anchor, "
                                      f"{unproven} module-level (unproven anchor), "
                                      f"{demoted} demoted (demo file), "
                                      f"{notshipped} not shipped (policy), "
                                      f"{filelevel} file-level (absent/module)"}]})
    return keep


# Rules whose claim is about a *metric*; their evidence line must fall in a
# scope that actually deals with a metric (G-SCOPE, context.py).
# EGP10 is an indexing-safety rule, not a metric rule: exp130 showed it
# being dropped by the scope gate on a planted fixture whose helper
# function legitimately contains no metric word.
_NEEDS_SCOPE = {"EG002": 1, "EGP06": 1, "EG012": 1, "EG011": 1,
                "EGP09": 1, "EG013": 1}
# exp131: EGP08 was mis-classified as a metric rule by G-SCOPE and its only
# planted hit (an assert inside `check()`) was filtered out -- the gate
# silently ate recall. G-SCOPE "only removed 1 finding" on the real corpus
# (exp130) while costing a planted hit here; it is not free.


def _audit(kind, dropped, rescued):
    return {"eg_id": "EG000", "canon": [], "severity": "info",
            "title": f"audit: {kind} gate",
            "hits": [{"line": 0,
                      "hit": f"{dropped} dropped (no line), "
                             f"{rescued} rescued via anchor"}]}


def _anchor_line(eg_id, idx):
    """Where the thing that *lacks* a companion actually is."""
    if eg_id in ("EG002", "EGP06", "EG012", "EG011", "EGP10"):
        return (idx.metric_anchor() or
                idx.locate("accuracy", "recall", "precision", "f1", "score",
                           "bleu", "rouge", "exact_match", "pass@1",
                           "re:\\bacc\\b", "re:\\bem\\b"))
    if eg_id == "EG016":
        return idx.locate("requests.get", "requests.post", "urlopen",
                          "re:\\bhttp", "session.get", "client.get")
    if eg_id in ("EG013", "EG005"):
        return idx.locate("re:/", "re://")
    if eg_id == "EG007":
        return idx.locate("re:\\bsaved", "re:\\barchiv", "re:\\bwrit", "dump")
    if eg_id in ("EGP08", "EGP09"):
        return idx.emits_metric()
    return None


def _gate_old(out, src, path):
    keep, dropped = [], 0
    for r in out:
        hits = [h for h in r.get("hits", [])
                if isinstance(h.get("line"), int) and h["line"] > 1]
        if hits:
            keep.append({**r, "hits": hits})
        else:
            dropped += 1
    if dropped:
        keep.append({"eg_id": "EG000", "canon": [], "severity": "info",
                     "title": "suppressed: no localisable evidence line",
                     "hits": [{"line": 0, "hit": f"{dropped} finding(s) dropped"}]})
    return keep

def main(argv=None):
    p = argparse.ArgumentParser(prog="evalguard",
        description="Static linter for LLM/Agent evaluation scripts. "
                    "Rules trace to a 368-entry empirical failure-mode canon.")
    p.add_argument("path", nargs="+", help="python file(s) or directory")
    p.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    p.add_argument("--severity", choices=["blocker", "warn", "info"], default="info")
    p.add_argument("--pro", action="store_true",
                   help="enable the PRO rule pack (10 additional rules)")
    p.add_argument("--report", metavar="OUT.html",
                   help="write a standalone HTML diagnostic report")
    a = p.parse_args(argv)
    if a.format == "sarif":
        # One SARIF document covering every path given, not one per file:
        # GitHub expects a single upload per tool per run.
        from .api import scan_paths
        print(json.dumps(scan_paths([str(x) for x in a.path], pro=a.pro)
                         .limit(a.severity).to_sarif(),
                         indent=2, ensure_ascii=False))
        return 0
    PRO_ON[0] = a.pro
    order = {"blocker": 0, "warn": 1, "info": 2}
    files = []
    for t in a.path:
        pth = pathlib.Path(t)
        if pth.is_dir(): files += sorted(pth.rglob("*.py"))
        else: files.append(pth)
    report = {}
    for f in files:
        res = [r for r in scan(str(f)) if order[r["severity"]] <= order[a.severity]]
        report[str(f)] = res
    if a.format == "json":
        print(json.dumps(report, indent=1, ensure_ascii=False)); return 0
    if a.report:
        _html(report, a.report)
        print(f"report written: {a.report}")
    nb = nw = ni = 0
    for f, res in report.items():
        print(f"\n{'='*64}\n{f}\n{'='*64}")
        if not res: print("  clean — no canon-backed failure mode detected"); continue
        for r in sorted(res, key=lambda x: order[x["severity"]]):
            tag = {"blocker": "BLOCK", "warn": "WARN ", "info": "INFO "}[r["severity"]]
            nb += r["severity"] == "blocker"; nw += r["severity"] == "warn"; ni += r["severity"] == "info"
            cn = ",".join(f"#{c}" for c in r["canon"])
            print(f"  [{tag}] {r['eg_id']}  canon {cn}\n         {r['title']}")
            for h in r["hits"][:3]:
                print(f"           {_fmt_line(h)}: {h['hit']}")
    print(f"\n{'-'*64}\n{nb} blocker · {nw} warn · {ni} info across {len(files)} file(s)")
    return 1 if nb else 0


def _fmt_line(h):
    """Render a finding's location for the terminal.

    exp138: this function was called at the print site but never defined,
    so `python3 -m evalguard` raised NameError *after* doing all the work
    -- the scan succeeded and the report was unprintable. It was fixed
    once inside a packaged zip and never in the source tree, which is why
    it came back. The lesson is the same one as exp138's decorator bug:
    a fix made in an artifact instead of in the source is not a fix.
    Returns a 5-char field so severities line up in the column.
    """
    ln = h.get("line")
    if ln is None:
        return "(file)"
    try:
        return f"{int(ln):>5d}"
    except (TypeError, ValueError):
        return "(file)"


def _html(report, out):
    order = {"blocker": 0, "warn": 1, "info": 2}
    nb = nw = ni = 0
    rows = []
    for f, res in report.items():
        for r in sorted(res, key=lambda x: order[x["severity"]]):
            if r["severity"] == "blocker": nb += 1
            elif r["severity"] == "warn": nw += 1
            else: ni += 1
            for h in r["hits"]:
                rows.append((r["severity"], r["eg_id"], f, (h.get("line") if h.get("line") is not None else "(module)"),
                             r["title"], h["hit"],
                             ",".join(f"#{c}" for c in r["canon"]),
                             r.get("fix", "")))
    rows.sort(key=lambda x: order[x[0]])
    body = "".join(
        f"<tr class='{r[0]}'><td class='s'>{r[0].upper()}</td><td>{r[1]}</td>"
        f"<td class='p'>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td>"
        f"<td class='h'>{r[5]}</td><td class='c'>{r[6]}</td>"
        f"<td class='f'>{r[7]}</td></tr>" for r in rows)
    html = f"""<!doctype html><meta charset=utf-8>
<title>evalguard report</title><style>
body{{font:14px/1.55 ui-monospace,Menlo,monospace;margin:32px;color:#111;background:#fff}}
h1{{font-size:19px;margin:0 0 4px}} .sub{{color:#666;margin:0 0 22px}}
.kpi{{display:flex;gap:26px;margin:0 0 22px;padding:14px 0;border-top:2px solid #111;border-bottom:1px solid #ddd}}
.kpi b{{font-size:24px;display:block}} .kpi span{{color:#666;font-size:11px;letter-spacing:.06em}}
table{{border-collapse:collapse;width:100%}}
td{{border-bottom:1px solid #eee;padding:7px 9px;vertical-align:top}}
th{{text-align:left;border-bottom:2px solid #111;padding:7px 9px;font-size:11px;letter-spacing:.06em}}
.s{{font-weight:700;font-size:11px}} tr.blocker .s{{color:#b00}} tr.warn .s{{color:#a60}} tr.info .s{{color:#666}}
.p{{color:#555;font-size:12px}} .h{{font-size:12px}} .c{{color:#777;font-size:12px}}
.f{{color:#444;font-size:12px;max-width:330px}}
</style>
<h1>evalguard &mdash; evaluation integrity report</h1>
<p class=sub>Rules trace to the Luoshen Failure-Mode Canon (368 entries mined from 100+ real experiments).</p>
<div class=kpi><div><b>{nb}</b><span>BLOCKER</span></div><div><b>{nw}</b><span>WARN</span></div>
<div><b>{ni}</b><span>INFO</span></div><div><b>{len(report)}</b><span>FILES</span></div></div>
<table><tr><th>SEV</th><th>RULE</th><th>FILE</th><th>LN</th><th>FAILURE MODE</th><th>EVIDENCE</th><th>CANON</th><th>FIX</th></tr>
{body}</table>"""
    pathlib.Path(out).write_text(html, encoding="utf-8")
