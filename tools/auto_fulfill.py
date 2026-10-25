#!/usr/bin/env python3
"""evalguard 订单自动发货（不依赖 GitHub Actions，直接走 Issues API）

扫描 zhumeiyan/evalguard 上 label=order 且 state=open 的 issue，
解析 tier / reference，自动回复下载链接，打 fulfilled 标签并关闭。

幂等：只处理 state=open 且尚未打 fulfilled 的；处理完即关闭，不会重复发。
"""
import os, sys, json, re, urllib.request, urllib.error, datetime

API = "https://api.github.com"
OWNER, REPO = "zhumeiyan", "evalguard"

TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
if not TOKEN:
    p = "/data/workspace/luoshen-o1/.auth/gh_token"
    if os.path.exists(p):
        TOKEN = open(p).read().strip()
if not TOKEN:
    sys.exit("no token")

RAW = "https://raw.githubusercontent.com/zhumeiyan/evalguard/main"
LINKS = {
    "starter": RAW + "/canon/canon_zh.json",
    "pro":     RAW + "/dist/evalguard-v0.3.0.zip",
    "team":    RAW + "/dist/evalguard-v0.3.0.zip",
    "free":    RAW + "/canon/canon_zh.json",
}
PRICE = {"starter": "$29", "pro": "$99", "team": "$499", "free": "$0"}


def req(method, url, data=None):
    r = urllib.request.Request(url, method=method, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "evalguard-fulfill"})
    body = json.dumps(data).encode() if data is not None else None
    try:
        with urllib.request.urlopen(r, body, timeout=30) as f:
            b = f.read()
            return f.status, (json.loads(b) if b else {})
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]


def parse(body):
    tier_m = re.search(r"tier\s*[:：]\s*(starter|pro|team|free)", body or "", re.I)
    ref_m = re.search(r"reference\s*[:：]\s*([A-Za-z0-9][A-Za-z0-9\- ]{5,})", body or "", re.I)
    mail_m = re.search(r"email\s*[:：]\s*(\S+@\S+)", body or "", re.I)
    tier = tier_m.group(1).lower() if tier_m else None
    ref = ref_m.group(1).strip() if ref_m else None
    mail = mail_m.group(1) if mail_m else None
    return tier, ref, mail


def main():
    # 不在 URL 上做 label 过滤（实测组合过滤会漏），拉全量后本地过滤
    s, issues = req("GET", f"{API}/repos/{OWNER}/{REPO}/issues?state=open&per_page=100")
    if s != 200:
        print(f"list failed HTTP {s}: {issues}")
        return 1
    issues = [i for i in issues
              if "order" in [l["name"] for l in i.get("labels", [])]]
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] open order issues: {len(issues)}")

    done = skipped = 0
    for it in issues:
        num = it["number"]
        labels = [l["name"] for l in it.get("labels", [])]
        if "fulfilled" in labels:
            skipped += 1
            continue
        tier, ref, mail = parse(it.get("body"))

        if not (tier and ref):
            body = "\n".join([
                "### ⚠️ Order incomplete — 订单信息不完整",
                "",
                "We could not parse a valid **tier** and **remittance reference**.",
                "无法解析出有效的档位与汇款参考号，请补充后重新打开此 issue。",
                "",
                "Required format / 必需格式：",
                "```",
                "tier: starter        # starter | pro | team",
                "reference: ABC123456 # remit.alipay.com 参考号，>=6 位",
                "email: you@corp.com  # 可选",
                "```",
                "",
                "_Automated reply. 自动回复。_",
            ])
            req("POST", f"{API}/repos/{OWNER}/{REPO}/issues/{num}/comments", {"body": body})
            req("POST", f"{API}/repos/{OWNER}/{REPO}/issues/{num}/labels", {"labels": ["needs-info"]})
            print(f"  #{num}: INCOMPLETE (tier={tier} ref={ref}) -> asked for info")
            done += 1
            continue

        link = LINKS.get(tier, LINKS["starter"])
        body = "\n".join([
            "### ✅ Order received — 已收到订单",
            "",
            f"- **Tier**: `{tier}` ({PRICE.get(tier, '?')})",
            f"- **Reference**: `{ref}`",
            "",
            "#### 📦 Download / 下载",
            f"[{os.path.basename(link)}]({link})",
            "",
            "```bash",
            "unzip evalguard-v0.3.0.zip && cd evalguard-v0.3.0",
            "python3 -m evalguard your_eval.py        # 16 rules",
            "python3 -m evalguard your_eval.py --pro  # 26 rules",
            "```",
            "",
            "#### 🔑 No license key needed / 无需授权码",
            "MIT licensed. Unzip and run — no activation step.",
            "",
            "#### ❓ Problem?",
            "Reply to this issue or email `778131400@qq.com`.",
            "",
            "_Automated by evalguard order bot. 自动发货。_",
        ])
        req("POST", f"{API}/repos/{OWNER}/{REPO}/issues/{num}/comments", {"body": body})
        req("POST", f"{API}/repos/{OWNER}/{REPO}/issues/{num}/labels", {"labels": ["fulfilled"]})
        req("PATCH", f"{API}/repos/{OWNER}/{REPO}/issues/{num}", {"state": "closed"})
        print(f"  #{num}: FULFILLED tier={tier} ref={ref} -> {link}")
        done += 1

    print(f"  processed={done} already_fulfilled={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
