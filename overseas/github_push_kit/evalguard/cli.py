import ast, sys, json, argparse, pathlib

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
            hits = [{"line": 0, "hit": f"rule error: {e}"}]
        if hits:
            out.append({**m, "hits": hits})
    if PRO_ON[0]:
        from .pro_rules import PRO_RULES
        for fn in PRO_RULES:
            m = fn.meta
            try:
                hits = fn(tree, src, path)
            except Exception as e:
                hits = [{"line": 0, "hit": f"rule error: {e}"}]
            if hits:
                out.append({**m, "hits": hits})
    return out

def main(argv=None):
    p = argparse.ArgumentParser(prog="evalguard",
        description="Static linter for LLM/Agent evaluation scripts. "
                    "Rules trace to a 368-entry empirical failure-mode canon.")
    p.add_argument("path", nargs="+", help="python file(s) or directory")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--severity", choices=["blocker", "warn", "info"], default="info")
    p.add_argument("--pro", action="store_true",
                   help="enable the PRO rule pack (10 additional rules)")
    p.add_argument("--report", metavar="OUT.html",
                   help="write a standalone HTML diagnostic report")
    a = p.parse_args(argv)
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
                print(f"           L{h['line']}: {h['hit']}")
    print(f"\n{'-'*64}\n{nb} blocker · {nw} warn · {ni} info across {len(files)} file(s)")
    return 1 if nb else 0


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
                rows.append((r["severity"], r["eg_id"], f, h["line"],
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
