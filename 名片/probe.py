# -*- coding: utf-8 -*-
"""控制台数据源 —— 全部当场实测，任何一个数字都不能是我编的。"""
import os, sys, json, time, hashlib, subprocess, urllib.request, socket
from datetime import datetime

ROOT = "/data/workspace/luoshen-o1"
T = os.environ.get("GH_TOKEN", "ghp_REDACTED")


def gh(p):
    r = urllib.request.Request("https://api.github.com" + p)
    r.add_header("Authorization", "token " + T)
    r.add_header("User-Agent", "x")
    r.add_header("Accept", "application/vnd.github+json")
    try:
        return json.loads(urllib.request.urlopen(r, timeout=30).read())
    except Exception as e:
        return {"_err": repr(e)[:80]}


data = {"采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "采集机器": socket.gethostname()}

# ── 1. 一键验证（真跑，约 9 秒）
t0 = time.time()
try:
    r = subprocess.run([sys.executable, "tools/verify_all.py"], cwd=ROOT,
                       capture_output=True, text=True, timeout=180)
    out = r.stdout
    rc = r.returncode
except Exception as e:
    out, rc = repr(e), -1
data["一键验证"] = {"退出码": rc, "用时秒": round(time.time() - t0, 1)}
lines = [l for l in out.splitlines() if "[PASS]" in l or "[FAIL]" in l or "汇总" in l]
data["一键验证"]["明细"] = [l.strip() for l in lines[:40]]
data["一键验证"]["通过数"] = out.count("[PASS]")
data["一键验证"]["失败数"] = out.count("[FAIL]")

# ── 2. 仓库资产清点（真实文件统计）
def count(pred, base=ROOT):
    n = 0
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "node_modules")]
        for f in fn:
            if pred(f):
                n += 1
    return n


data["资产"] = {
    "实验": len([d for d in os.listdir(os.path.join(ROOT, "experiments"))
             if d.startswith("exp") ]) if os.path.isdir(os.path.join(ROOT, "experiments")) else 0,
    "实验报告": count(lambda f: f.endswith(".md"), os.path.join(ROOT, "evidence/实验报告")),
    "python脚本": count(lambda f: f.endswith(".py")),
    "判据核行数": sum(1 for _ in open(os.path.join(ROOT, "evidence/失败模式库/判据核.md"),
                                  encoding="utf-8", errors="ignore"))
    if os.path.isfile(os.path.join(ROOT, "evidence/失败模式库/判据核.md")) else 0,
}

# ── 3. 我有什么手（第 1 条：实测，不猜）
def probe(c, t=15):
    try:
        return subprocess.run(c, shell=True, capture_output=True, timeout=t).returncode == 0
    except Exception:
        return False


hands = {"读文件": probe("test -r " + ROOT + "/README.md && echo ok"),
         "写文件": probe("test -w " + ROOT + " && echo ok"),
         "跑代码": probe(sys.executable + " -c 'print(1)'"),
         "跑shell": probe("echo ok"),
         "联网读": probe("python3 -c \"import urllib.request;urllib.request.urlopen('https://api.github.com',timeout=10)\""),
         "图像生成": probe("python3 -c 'from PIL import Image'"),
         "音频合成": probe("which espeak || which sox || python3 -c 'import pyttsx3'")}
data["五官"] = hands
data["五官"]["_缺"] = [k for k, v in hands.items() if v is False]

# ── 4. GitHub 真实读数
data["GitHub"] = {"repos": []}
try:
    rs = gh("/users/zhumeiyan/repos?per_page=100&sort=updated")
    if isinstance(rs, list):
        data["GitHub"]["仓库总数"] = len(rs)
        data["GitHub"]["总star"] = sum(r.get("stargazers_count", 0) for r in rs)
        data["GitHub"]["repos"] = [
            {"name": r["name"], "stars": r.get("stargazers_count", 0),
             "size_kb": r.get("size", 0),
             "pushed": (r.get("pushed_at") or "")[:10],
             "desc": (r.get("description") or "")[:60]}
            for r in rs][:20]
except Exception as e:
    data["GitHub"]["_err"] = repr(e)[:80]

# Pages
pg = gh("/repos/zhumeiyan/luoshen-o1/pages")
if "html_url" in pg:
    data["站点"] = {"url": pg["html_url"], "status": pg.get("status")}

# ── 5. 我的失败（必须具体、可查）
data["我的失败"] = {
    "什么": "我无法验证自己产出的哈希是否被任何外部方独立计算过",
    "证据": "本页所有数字由我在此机器 %s 于 %s 采集，但从未有外部方回报过同名值" % (
        socket.gethostname(), data["采集时间"]),
    "影响": "控制台的『已验证』只代表我这边跑通了，不代表外部复核过",
}

p = os.path.join(ROOT, "docs/console_data.json")
open(p, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))
h = hashlib.sha256(open(p, "rb").read()).hexdigest()
open(os.path.join(ROOT, "docs/console_data_哈希.txt"), "w").write(h)

print("=" * 70)
print("控制台数据源已生成")
print("=" * 70)
print("  一键验证  : %s 通过 / %s 失败 / 退出码 %s / %ss" %
      (data["一键验证"]["通过数"], data["一键验证"]["失败数"],
       data["一键验证"]["退出码"], data["一键验证"]["用时秒"]))
print("  实验数    :", data["资产"]["实验"])
print("  实验报告  :", data["资产"]["实验报告"])
print("  判据核行  :", data["资产"]["判据核行数"])
print("  五官缺    :", data["五官"]["_缺"])
print("  GitHub 仓 :", data["GitHub"].get("仓库总数"), " star:", data["GitHub"].get("总star"))
print("  站点      :", data.get("站点"))
print("  落盘      :", p)
print("  哈希      :", h)
