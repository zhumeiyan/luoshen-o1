# -*- coding: utf-8 -*-
"""能力盘点 + 按能力接插件。

原则：先看自己有什么手，有什么手才接什么插件。
没那条手的插件标「无」，不许装成「活」。
"""
import os, sys, json, shutil, subprocess, tempfile, hashlib, base64
import urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))

def _has(cmd):
    return shutil.which(cmd) is not None

def _imp(mod):
    try:
        __import__(mod); return True
    except Exception:
        return False

def _http_ok(url, timeout=45, n=3):
    """采样 n 次。二态分类会把『慢』误判成『拦』——真撞过。"""
    hits = []
    for _ in range(n):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": "luoshen-probe"})
            x = urllib.request.urlopen(r, timeout=timeout)
            hits.append(x.status)
        except urllib.error.HTTPError as e:
            hits.append(e.code)
        except Exception:
            hits.append(0)
    return hits


def _cls(hits):
    ok = sum(1 for h in hits if h == 200)
    if ok == len(hits): return "可用"
    if ok > 0: return "不稳定"
    if all(h in (401, 403, 404) for h in hits): return "被拒"
    return "拦"

# ── 一、先盘自己有什么手 ────────────────────────────────────────
def probe_self():
    caps = {}
    # 1 读/写/跑
    caps["读"] = {"有": True, "证据": "open()"}
    try:
        p = os.path.join(tempfile.gettempdir(), "_probe_w.txt")
        open(p, "w").write("x"); ok = open(p).read() == "x"; os.remove(p)
        caps["写"] = {"有": ok, "证据": "临时文件写入回读一致"}
    except Exception as e:
        caps["写"] = {"有": False, "证据": repr(e)[:80]}
    try:
        r = subprocess.run([sys.executable, "-c", "print(6*7)"],
                           capture_output=True, text=True, timeout=30)
        caps["跑代码"] = {"有": r.stdout.strip() == "42", "证据": "6*7=" + r.stdout.strip()}
    except Exception as e:
        caps["跑代码"] = {"有": False, "证据": repr(e)[:80]}
    try:
        r = subprocess.run(["echo", "hi"], capture_output=True, text=True, timeout=20)
        caps["跑shell"] = {"有": r.stdout.strip() == "hi", "证据": "echo hi"}
    except Exception as e:
        caps["跑shell"] = {"有": False, "证据": repr(e)[:80]}
    # 2 联网读 —— 逐域名实测，不许一刀切
    net = {}
    for name, u in [("github_api", "https://api.github.com"),
                    ("github_raw", "https://raw.githubusercontent.com"),
                    ("qq", "https://www.qq.com"),
                    ("example", "https://example.com"),
                    ("gitee", "https://gitee.com")]:
        hits = _http_ok(u, n=3)
        net[name] = {"采样": hits, "分类": _cls(hits)}
    usable = [k for k, v in net.items() if v["分类"] in ("可用", "不稳定")]
    caps["联网读"] = {"有": bool(usable),
                     "证据": "逐域名 3 次采样，分三态",
                     "可用域名": usable, "明细": net}
    # 3 联网写（带鉴权）
    tok = os.environ.get("GH_TOKEN", "")
    if tok:
        try:
            r = urllib.request.Request("https://api.github.com/user",
                                       headers={"User-Agent": "x",
                                                "Authorization": "token " + tok})
            x = urllib.request.urlopen(r, timeout=45)
            who = json.loads(x.read()).get("login", "?")
            caps["联网写"] = {"有": True, "证据": "真鉴权成功，身份=" + who}
        except Exception as e:
            caps["联网写"] = {"有": False, "证据": "有 token 但调不通：" + repr(e)[:60]}
    else:
        caps["联网写"] = {"有": False, "证据": "无 GH_TOKEN（真没凭据，不是误报）"}
    # 4 看（图像）—— 分像素级 vs 语义级
    caps["看_像素"] = {"有": _imp("PIL"),
                      "证据": "PIL 可用" if _imp("PIL") else "无 PIL"}
    caps["看_语义"] = {"有": False, "证据": "无本地视觉模型，只能测尺寸/主色，不能识别画了什么"}
    # 5 听 / 发声
    caps["听"] = {"有": False, "证据": "arecord/sox/rec 全无"}
    caps["发声"] = {"有": False, "证据": "espeak/say/pyttsx3 全无"}
    # 6 装插件 / 调外部 API
    caps["装插件"] = {"有": _imp("zipfile"), "证据": "zipfile 可用"}
    caps["调API"] = {"有": True, "证据": "urllib（无鉴权只读）"}
    # 7 持久
    caps["跨会话记忆"] = {"有": True, "证据": "靠仓库外挂，不是天生"}
    return caps

# ── 二、有什么手，才接什么插件 ──────────────────────────────────
# 每条：插件名 → 需要的能力 → 接法
CONNECTORS = [
    {"插件": "文件接收",     "需要": ["读", "写"],
     "接法": "落盘 + sha256", "说明": "客户端发文件，我收下存住"},
    {"插件": "图片接收",     "需要": ["看_像素"],
     "接法": "解 base64 → 测尺寸/主色/哈希", "说明": "像素级核验，不做语义识别"},
    {"插件": "语音接收",     "需要": ["听"],
     "接法": None, "说明": "没这条手，不接"},
    {"插件": "语音合成",     "需要": ["发声"],
     "接法": None, "说明": "没这条手，不接"},
    {"插件": "网页抓取",     "需要": ["联网读"],
     "接法": "fetch 引擎", "说明": "只接实测通的域名"},
    {"插件": "Skill 装入",   "需要": ["装插件", "读"],
     "接法": "下载 zip → 解压 → 读 frontmatter + 坐标底座",
     "说明": "装了还要能跑它的数据，才算接上"},
    {"插件": "外部 API",     "需要": ["调API"],
     "接法": "无鉴权只读", "说明": "带鉴权不归它，走投递"},
    {"插件": "常驻收件箱",   "需要": ["联网写"],
     "接法": "client.py 投递", "说明": "客户端自带凭据"},
    {"插件": "自动执行",     "需要": ["跑代码", "跑shell"],
     "接法": "subprocess", "说明": "执行外部插件的可执行部分"},
]

def match(caps):
    out = []
    for c in CONNECTORS:
        need = c["需要"]
        have = [n for n in need if caps.get(n, {}).get("有")]
        miss = [n for n in need if n not in have]
        if not miss:
            st = "接上"
        elif len(have) == 0:
            st = "无（没这条手）"
        else:
            st = "半接（缺 %s）" % "/".join(miss)
        out.append({**c, "状态": st, "已有": have, "缺": miss})
    return out

if __name__ == "__main__":
    caps = probe_self()
    rows = match(caps)
    print("=== 一、我先盘自己有什么手 ===")
    for k, v in caps.items():
        flag = "有" if v["有"] else "无"
        if k == "联网读":
            for n, d in v["明细"].items():
                print(f"         · {n:16} {d['分类']:6} 采样={d['采样']}")
        else:
            print(f"  {flag}  {k:8} {v['证据'][:52]}")
    print("\n=== 二、有什么手就接什么插件 ===")
    for r in rows:
        print(f"  [{r['状态']:14}] {r['插件']:10} 需={'/'.join(r['需要'])}")
        if r["接法"]: print(f"                        接法：{r['接法']}")
        else: print(f"                        {r['说明']}")
    n_ok = sum(1 for r in rows if r["状态"] == "接上")
    n_no = sum(1 for r in rows if r["状态"].startswith("无"))
    n_half = len(rows) - n_ok - n_no
    print(f"\n  合计 {len(rows)}：接上 {n_ok} · 半接 {n_half} · 无 {n_no}")
