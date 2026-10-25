#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evalguard free-scan service.

Customer opens an issue labelled `scan` with their eval script in a fenced code
block. This reads it, runs evalguard (pure AST, never executes their code),
posts the diagnostic back, labels `scanned`, closes.

Fulfilment of paid orders is handled by fulfil.py; this is the top-of-funnel
free tier that turns a stranger into a buyer.
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

REPO = "zhumeiyan/evalguard"
API = "https://api.github.com/repos/" + REPO
TOKEN = os.environ.get("GITHUB_TOKEN", "")
# parent dir must be on sys.path so `evalguard` imports as a package
# (cli.py uses relative `from .rules import RULES`)
EG = os.path.dirname(os.path.abspath(__file__))

CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def gh(path, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header("Authorization", "token " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "evalguard-scan")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        sys.stderr.write("  api fail %s %s: %s\n" % (method, path, e))
        return None


def labels_of(issue):
    return [l["name"] for l in issue.get("labels", [])]


def run_scan(code):
    """Run evalguard on a snippet. Never executes it."""
    d = tempfile.mkdtemp(prefix="egscan_")
    f = os.path.join(d, "customer_eval.py")
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(code)
    cmd = [sys.executable, "-c",
           "import sys;sys.path.insert(0,%r);"
           "from evalguard.cli import scan;"
           "import json;print(json.dumps(scan(%r)))" % (EG, f)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        return None, p.stderr.strip()[:400]
    try:
        return json.loads(p.stdout.strip().splitlines()[-1]), None
    except Exception as e:
        return None, "unparsable output: %s" % e


def render(findings, pro=False):
    if not findings:
        return ("**evalguard: no findings in the free tier.**\n\n"
                "That means the 10 free rules found nothing — not that the script is correct. "
                "The PRO pack adds 16 rules (multi-seed, significance, dedup, leakage, injection surface). "
                "→ https://zhumeiyan.github.io/evalguard/")
    lines = ["**evalguard free-tier report** · %d finding(s)\n" % len(findings),
             "| sev | rule | line | what |", "|---|---|---|---|"]
    for f in findings:
        sev = f.get("severity", "?")
        for h in f.get("hits", [])[:6]:
            lines.append("| %s | `%s` | %s | %s |" % (
                sev, f.get("eg_id", "?"), h.get("line", "?"),
                str(h.get("hit", ""))[:90].replace("|", "\\|")))
    nb = sum(1 for f in findings if f.get("severity") == "blocker")
    lines.append("\n%d blocker · %d warn" % (
        nb, sum(1 for f in findings if f.get("severity") == "warn")))
    lines.append("\nEach rule traces to an entry in the 368-failure-mode canon (`canon/`).")
    lines.append("\nPRO adds 16 more rules → https://zhumeiyan.github.io/evalguard/")
    return "\n".join(lines)


def main():
    if not TOKEN:
        sys.stderr.write("no GITHUB_TOKEN\n")
        return 2
    # NOTE: do NOT filter by label in the URL — that silently returns [] on
    # this endpoint. Pull all, filter locally. (bug found 2026-10-17)
    issues = gh("/issues?state=open&per_page=100") or []
    targets = [i for i in issues if "scan" in labels_of(i) and "scanned" not in labels_of(i)]
    sys.stderr.write("open=%d scan_targets=%d\n" % (len(issues), len(targets)))
    acted = 0
    for iss in targets:
        num = iss["number"]
        blocks = CODE_BLOCK.findall(iss.get("body") or "")
        if not blocks:
            gh("/issues/%d/comments" % num, "POST",
               {"body": "No Python code block found. Please paste your script "
                        "inside a fenced ```python ...``` block and reopen this issue."})
            gh("/issues/%d/labels" % num, "POST", {"labels": ["needs-info"]})
            sys.stderr.write("  #%d no code block -> needs-info\n" % num)
            acted += 1
            continue
        code = max(blocks, key=len)
        findings, err = run_scan(code)
        if err:
            body = "evalguard could not parse this input.\n\n```\n%s\n```" % err
        else:
            body = render(findings)
        gh("/issues/%d/comments" % num, "POST", {"body": body})
        gh("/issues/%d/labels" % num, "POST", {"labels": ["scanned"]})
        gh("/issues/%d" % num, "PATCH", {"state": "closed"})
        sys.stderr.write("  #%d scanned %d findings\n" % (num, len(findings or [])))
        acted += 1
    sys.stderr.write("acted=%d\n" % acted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
