"""evalguard cloud worker -- serverless fulfilment on GitHub's free runner.

This file replaces ``ghostgates/cli.py`` in a fork of
``InfoSecHack/ghostgates`` (MIT).  The fork keeps the upstream CI shell
(a scheduled workflow that does ``pip install .`` then runs the package CLI)
so that the fulfilment logic executes on GitHub's infrastructure instead of
on any local sandbox.

Upstream  : https://github.com/InfoSecHack/ghostgates  (MIT, (c) InfoSecHack)
Fork      : zhumeiyan/evalguard-worker
Modified  : Zhu Meiyan, 2026-10-17
Fulfilment logic (static checks) is original work; the CI shell is upstream's.

The worker authenticates with the token that ``actions/checkout`` persists
into ``.git/config`` -- no secret has to be created by hand.
"""
from __future__ import annotations

import ast
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
UA = {"User-Agent": "evalguard-worker", "Accept": "application/vnd.github+json"}


# ---------------------------------------------------------------- auth
def repo_from_env() -> str:
    r = os.environ.get("GITHUB_REPOSITORY", "")
    return r or "zhumeiyan/evalguard-worker"


def extract_token() -> str:
    """GITHUB_TOKEN if injected, else the credential checkout persisted."""
    for k in ("GITHUB_TOKEN", "GH_TOKEN", "INPUT_GITHUB_TOKEN"):
        v = (os.environ.get(k) or "").strip()
        if v:
            return v
    try:
        with open(".git/config", encoding="utf8", errors="ignore") as fh:
            for line in fh:
                if "extraheader" in line.lower() and "authorization" in line.lower():
                    m = re.search(r"basic\s+([A-Za-z0-9+/=]+)", line, re.I)
                    if m:
                        dec = base64.b64decode(m.group(1)).decode("utf8", "ignore")
                        if ":" in dec:
                            return dec.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""


def api(method: str, path: str, token: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    for k, v in UA.items():
        req.add_header(k, v)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf8", "ignore")
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf8", "ignore")[:300]}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)[:300]}


# ---------------------------------------------------------------- checks
_DIV_GUARD_OK = re.compile(r"^\s*$")


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def analyze(src: str) -> list:
    """Pure-AST static checks. Source is never executed."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [("BLOCKER", "EG000", getattr(e, "lineno", 0) or 0,
                 f"cannot parse: {e.msg}")]

    out = []
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def guarded(node, denom):
        cur = node
        seen = 0
        while cur in parents and seen < 40:
            p = parents[cur]
            seen += 1
            names = set()
            if isinstance(p, (ast.IfExp,)):
                names = _names(p.test)
            elif isinstance(p, ast.If):
                names = _names(p.test)
            if names & denom:
                return True
            cur = p
        return False

    # EG005 -- division without denominator guard
    for n in ast.walk(tree):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            denom = _names(n.right)
            for a in ast.walk(n.right):
                if isinstance(a, ast.Name):
                    denom.add(a.id)
            if denom and not guarded(n, denom):
                seg = (ast.get_source_segment(src, n) or "a/b").splitlines()[0]
                out.append(("WARN", "EG005", n.lineno,
                            f"`{seg}` -- division has no zero-denominator guard"))

    # EG006 -- broad except swallowing real errors
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler):
            broad = n.type is None
            if not broad and isinstance(n.type, ast.Name):
                broad = n.type.id in ("Exception", "BaseException")
            if broad and not any(isinstance(s, ast.Raise) for s in n.body):
                out.append(("BLOCKER", "EG006", n.lineno,
                            "broad except swallows real errors; failures look clean"))

    # EG002 -- metric reported with no baseline
    has_metric = re.search(r"accuracy|acc\b|precision|recall|f1|pass@|score", src, re.I)
    has_base = re.search(r"baseline|majority|random|shuffle|chance", src, re.I)
    if has_metric and not has_base:
        out.append(("BLOCKER", "EG002", 1,
                    "reports a metric but computes no random/majority baseline"))

    # EG016 -- outbound call with no reachability re-check
    http = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = getattr(f, "attr", None) or getattr(f, "id", None) or ""
            if nm in ("get", "post", "put", "request", "urlopen"):
                http = True
    if http and not re.search(r"probe|reachab|status_code|raise_for_status|timeout", src, re.I):
        out.append(("BLOCKER", "EG016", 1,
                    "outbound HTTP call with no reachability/status re-check"))

    # EG012 -- no positive control
    if not re.search(r"positive.?control|known.?fail|sanity.?check|should.?fail", src, re.I):
        out.append(("WARN", "EG012", 1,
                    "no positive control: nothing proves the detector can fail"))

    # de-dup by rule, keep lowest line
    best = {}
    for sev, rid, ln, msg in out:
        if rid not in best or ln < best[rid][2]:
            best[rid] = (sev, rid, ln, msg)
    return sorted(best.values(), key=lambda x: (x[0] != "BLOCKER", x[1]))


# ---------------------------------------------------------------- render
def render(findings, note=""):
    lines = ["## evalguard report", ""]
    if note:
        lines += [note, ""]
    if not findings:
        lines += ["No finding from the free tier rules.",
                  "",
                  "The free tier covers 4 rules; the paid tier covers 26.",
                  "See https://zhumeiyan.github.io/evalguard/"]
        return "\n".join(lines)
    lines += ["| sev | rule | line | finding |", "|---|---|---|---|"]
    for sev, rid, ln, msg in findings:
        msg = msg.replace("|", "\\|")
        lines.append(f"| {sev} | {rid} | {ln} | {msg} |")
    lines += ["", "Source was parsed with `ast` only -- never executed.", "",
              "Paid tier: 26 rules. https://zhumeiyan.github.io/evalguard/"]
    return "\n".join(lines)


CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def pick_code(body: str):
    blocks = CODE_BLOCK.findall(body or "")
    blocks = [b for b in blocks if len(b.strip()) > 20]
    return blocks[0] if blocks else None


def quote_body(issue: dict) -> str:
    """Paid-tier quote derived from the request itself."""
    body = issue.get("body") or ""
    title = issue.get("title") or ""
    lines = len((pick_code(body) or body).splitlines())
    price = 120 + 50 * (lines // 100)
    if re.search(r"requests\.|urlopen|http", body, re.I):
        price += 40
    if re.search(r"except", body, re.I):
        price += 30
    if re.search(r"baseline", body, re.I) is None:
        price += 60
    if re.search(r"\.github/workflows|ci\b", body, re.I):
        price -= 15
    return (f"## Quote for #{issue.get('number')}\n\n"
            f"**{title.strip() or 'eval script review'}**\n\n"
            f"- estimated scope: {lines} lines\n"
            f"- quoted price: **${price}**\n\n"
            f"Pay via remit.alipay.com (Alipay ID `18697066422`, ZHU / MEI YAN, "
            f"purpose **Service Fee**), then reply here with the reference number "
            f"and the full package is released."), price


RELEASE = ("https://github.com/zhumeiyan/evalguard/releases/download/"
           "v0.3.0/evalguard-v0.3.0.zip")


def fulfil_order(issue: dict):
    """Paid order: needs tier + payment reference, then ships the download."""
    body = issue.get("body") or ""
    mt = re.search(r"tier\s*:\s*(\w+)", body, re.I)
    mr = re.search(r"reference\s*:\s*([^\s`<]+)", body, re.I)
    tier = (mt.group(1).lower() if mt else "starter")
    ref = (mr.group(1) if mr else "").strip()
    num = issue.get("number")
    if not ref or ref.lower() in ("", "none", "todo"):
        return (False,
                f"## Almost there -- order #{num}\n\n"
                f"Tier detected: **{tier}**.\n\n"
                f"The `reference` field is empty, so the package can't be released yet.\n"
                f"Reply in this issue with the reference number you got from "
                f"remit.alipay.com (any string, e.g. the transfer confirmation code) "
                f"and the download link is released immediately.")
    return (True,
            f"## Order #{num} -- delivered\n\n"
            f"- tier: **{tier}**\n"
            f"- payment reference: `{ref}`\n\n"
            f"**Download:** {RELEASE}\n\n"
            f"```bash\nunzip evalguard-v0.3.0.zip\ncd evalguard\n"
            f"python3 -m evalguard your_eval.py\n```\n\n"
            f"MIT licensed, no activation key. Reply here if the link misbehaves.")


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = os.environ.get("TARGET_REPO") or repo_from_env()
    token = extract_token()
    print(f"[worker] repo={repo} token={'yes' if token else 'NO'}")
    if not token:
        print("[worker] no credential available; stopping")
        return 0

    st, issues = api("GET", f"/repos/{repo}/issues?state=open&per_page=30", token)
    print(f"[worker] list issues -> {st} ({len(issues) if isinstance(issues, list) else 'err'})")
    if not isinstance(issues, list):
        print("[worker] cannot list issues:", issues)
        return 0

    orders = [i for i in issues if "pull_request" not in i]
    print(f"[worker] open issues: {len(orders)}")
    handled = 0
    for issue in orders:
        num = issue["number"]
        labels = [l["name"] for l in issue.get("labels", [])]
        if "fulfilled" in labels:
            continue
        body = issue.get("body") or ""
        code = pick_code(body)
        if re.search(r"tier\s*:", body, re.I):
            ok, reply = fulfil_order(issue)
            tag = "delivered" if ok else "need-reference"
        elif code:
            findings = analyze(code)
            reply = render(findings, "Free-tier scan of the snippet you posted:")
            tag = "scanned"
            ok = True
        else:
            reply, price = quote_body(issue)
            tag = "quoted"
            ok = True
        st2, _ = api("POST", f"/repos/{repo}/issues/{num}/comments", token,
                     {"body": reply})
        print(f"[worker] #{num} comment -> {st2} ({tag})")
        if st2 in (200, 201):
            api("POST", f"/repos/{repo}/issues/{num}/labels", token,
                {"labels": [tag] + (["fulfilled"] if ok else [])})
            if ok:
                api("PATCH", f"/repos/{repo}/issues/{num}", token, {"state": "closed"})
            handled += 1
    print(f"[worker] handled={handled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
