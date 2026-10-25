#!/usr/bin/env python3
"""把所有交付物通过 contents API 推到 zhumeiyan/evalguard
二进制用 base64。幂等：已存在则带 sha 覆盖。"""
import os, sys, json, base64, io, urllib.request, urllib.error

API = "https://api.github.com"
TK = os.environ.get("GITHUB_TOKEN", "")
OWNER, REPO = "zhumeiyan", "evalguard"
ROOT = "/data/workspace/luoshen-o1/overseas"

if not TK:
    sys.exit("need GITHUB_TOKEN")


def req(method, url, data=None, raw=False):
    r = urllib.request.Request(url, method=method,
        headers={"Authorization": f"Bearer {TK}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "evalguard-pusher"})
    body = json.dumps(data).encode() if data is not None else None
    try:
        with urllib.request.urlopen(r, body) as f:
            b = f.read()
            if raw:
                return f.status, b
            return f.status, json.load(io.BytesIO(b))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]


def get_sha(path):
    s, j = req("GET", f"{API}/repos/{OWNER}/{REPO}/contents/{path}")
    if s == 200 and isinstance(j, dict):
        return j.get("sha")
    return None


def put(local, remote, msg=None):
    if not os.path.exists(local):
        print(f"  SKIP (missing) {local}")
        return False
    with open(local, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    payload = {"message": msg or f"add {remote}", "content": b64}
    sha = get_sha(remote)
    if sha:
        payload["sha"] = sha
    s, j = req("PUT", f"{API}/repos/{OWNER}/{REPO}/contents/{remote}", payload)
    ok = s in (200, 201)
    print(f"  {remote:44s} {len(data):>8d}B  HTTP {s}  {'OK' if ok else j}")
    return ok


FILES = [
    (f"{ROOT}/repo/.github/workflows/order-fulfill.yml",
     ".github/workflows/order-fulfill.yml"),
    (f"{ROOT}/repo/.github/ISSUE_TEMPLATE/order.yml",
     ".github/ISSUE_TEMPLATE/order.yml"),
    (f"{ROOT}/evalguard-v0.3.0.zip",
     "dist/evalguard-v0.3.0.zip"),
    (f"{ROOT}/canon/canon_zh.json",
     "canon/canon_zh.json"),
    (f"{ROOT}/canon/canon_zh.csv",
     "canon/canon_zh.csv"),
    (f"{ROOT}/site/index.html",
     "index.html"),
]

print("pushing to", f"{OWNER}/{REPO}")
n_ok = 0
for local, remote in FILES:
    if put(local, remote):
        n_ok += 1
print(f"done {n_ok}/{len(FILES)}")
