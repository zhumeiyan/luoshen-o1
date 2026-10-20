# -*- coding: utf-8 -*-
"""
洛神 O1 · 一站式服务（零依赖，仅 Python 标准库）

对齐反向工程提炼出的骨架：
  ① 统一契约层  /api/*  —— 前端只认这一层，引擎可换
  ② 前后端分家  web/ + engine/ + api/
  ③ 一个入口    python3 serve.py
  ④ 配置外置    环境变量 / .env
  ⑤ 状态在前端，持久化在后端

启动：  python3 serve.py           → http://127.0.0.1:8765
        python3 serve.py 9000      → 换端口
"""
import os, sys, json, time, hashlib, subprocess, threading, socketserver
import re, base64, urllib.request, urllib.error, urllib.parse, zipfile, io
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "docs")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
PY = sys.executable

# ── 引擎层：真正干活的（可替换，前端不关心） ──────────────────────
def engine_verify():
    """跑一键验证。真跑，不读缓存。"""
    t0 = time.time()
    try:
        r = subprocess.run([PY, "tools/verify_all.py"], cwd=ROOT,
                           capture_output=True, text=True, timeout=300)
        return {"ok": r.returncode == 0, "rc": r.returncode,
                "out": r.stdout, "err": r.stderr[-500:],
                "pass": r.stdout.count("[PASS]"),
                "fail": r.stdout.count("[FAIL]"),
                "sec": round(time.time() - t0, 1)}
    except Exception as e:
        return {"ok": False, "err": repr(e)[:300]}


def engine_scan(text):
    """跑 evalguard 扫描。

    注意：evalguard 自带 HTTP 服务（python3 -m overseas.evalguard serve --port N），
    我们的契约层既可以本地 subprocess 调，也可以将来改指向它的服务 —— 引擎可换。"""
    p = os.path.join(ROOT, "overseas/evalguard")
    if not os.path.isdir(p):
        return {"ok": False, "未实现": "evalguard 目录不存在",
                "说明": "有手没实现 ≠ 没手，这条如实报"}
    # 契约修正：evalguard 接的是 path，不是 --text。
    # 我先把文本落成临时文件再扫 —— 契约层负责适配，不让前端知道引擎的脾气。
    import tempfile
    if not (text or "").strip():
        return {"ok": False, "未实现": "scan 需要 text 或 path"}
    fd, tmp = tempfile.mkstemp(suffix=".py", prefix="lsscan_")
    os.write(fd, (text or "").encode()); os.close(fd)
    try:
        r = subprocess.run([PY, "-m", "overseas.evalguard", tmp],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        return {"ok": True, "rc": r.returncode, "引擎": "evalguard",
                "out": (r.stdout or r.stderr)[-3000:]}
    except Exception as e:
        return {"ok": False, "err": repr(e)[:300]}
    finally:
        try: os.unlink(tmp)
        except Exception: pass


def engine_console():
    """采集控制台数据。真跑。"""
    try:
        r = subprocess.run([PY, "名片/probe.py"], cwd=ROOT,
                           capture_output=True, text=True, timeout=300)
        j = os.path.join(ROOT, "docs/console_data.json")
        if os.path.isfile(j):
            d = json.load(open(j, encoding="utf-8"))
            d["_哈希"] = hashlib.sha256(open(j, "rb").read()).hexdigest()
            return {"ok": True, "data": d}
        return {"ok": False, "err": (r.stdout or r.stderr)[-300:]}
    except Exception as e:
        return {"ok": False, "err": repr(e)[:300]}


def engine_prove(text):
    """译本层：自然语言 → 冻结译本 + 双哈希。有实现则真跑。"""
    p = os.path.join(ROOT, "experiments/exp256_translation/compile.py")
    if not os.path.isfile(p):
        return {"ok": False, "未实现": "compile.py 不存在"}
    # 契约修正：compile.py 用相对路径读坐标，必须在它自己的目录里跑。
    d = os.path.dirname(p)
    try:
        r = subprocess.run([PY, os.path.basename(p), "--text", text], cwd=d,
                           capture_output=True, text=True, timeout=120)
        return {"ok": r.returncode == 0, "rc": r.returncode, "引擎": "compile",
                "out": (r.stdout or r.stderr)[-2000:]}
    except Exception as e:
        return {"ok": False, "err": repr(e)[:300]}


# ── 接收端引擎：文本 / 图片 / 语音 ────────────────────────────────
# 原则：接进来就真处理。处理不了的，如实报「无」，绝不静默降级。

def engine_ask(text):
    """文本交互：解析指令 → 调度引擎 → 返回真结果。

    这不是聊天机器人。它不生成"听起来像回答"的话，
    它把你的指令翻译成某个引擎的一次真跑，然后把真输出还给你。"""
    t = (text or "").strip()
    if not t:
        return {"ok": False, "未实现": "指令为空"}
    low = t.lower()
    # 关键词 → 引擎。没命中就给出能力清单，不假装听懂了。
    table = [
        (("验证", "verify", "自检", "通过"), "verify"),
        (("扫描", "scan", "检查代码", "evalguard", "病代码"), "scan"),
        (("控制台", "console", "读数", "资产"), "console"),
        (("译本", "prove", "编译", "冻结"), "prove"),
    ]
    for kws, name in table:
        if any(k in t or k in low for k in kws):
            r = ENGINES_REF[name](t) if name in ("scan", "prove") else ENGINES_REF[name]()
            r["_指令"] = t
            r["_引擎"] = name
            return r
    return {"ok": False, "未听懂": t,
            "说明": "我不假装理解。只能调度下列引擎：",
            "能做的": ["验证 —— 跑一键验证", "扫描 <代码> —— 跑 evalguard",
                       "控制台 —— 采集实时读数", "译本 <判据> —— 编译成冻结译本"],
            "做不到的": ["自由聊天", "语音", "语义理解图片"]}


def engine_image(b64):
    """图片接收：PIL 真实分析。

    能测的：尺寸 / 格式 / 主色调 / 亮度分布 / 是否灰度。
    测不了的：图里画的是什么 —— 没有本地视觉模型，如实说。"""
    try:
        from PIL import Image
    except ImportError:
        return {"ok": False, "缺失": "PIL",
                "说明": "没有图像库，这不是降级，是如实报"}
    import base64, io
    try:
        raw = base64.b64decode(b64.split(",")[-1])
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        return {"ok": False, "错误": repr(e)[:200], "说明": "打不开这张图"}
    w, h = im.size
    small = im.convert("RGB").resize((60, 60))
    px = list(small.getdata())
    n = len(px)
    # 主色调：量化到 32 级后取众数
    from collections import Counter
    q = Counter(((r // 32) * 32, (g // 32) * 32, (b // 32) * 32) for r, g, b in px)
    top = q.most_common(3)
    avg = tuple(sum(c[i] for c in px) // n for i in range(3))
    lum = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px]
    return {"ok": True, "引擎": "PIL",
            "尺寸": "%dx%d" % (w, h), "格式": im.format, "模式": im.mode,
            "平均色": "rgb(%d,%d,%d)" % avg,
            "主色调": ["rgb(%d,%d,%d) ×%d" % (c[0], c[1], c[2], k) for c, k in top],
            "亮度": {"最暗": round(min(lum)), "最亮": round(max(lum)),
                     "均值": round(sum(lum) / n, 1)},
            "像素哈希": hashlib.sha256(raw).hexdigest()[:16],
            "我测不了的": "图里是什么内容 —— 没有本地视觉模型，语义理解标为无"}


def engine_voice(text):
    """语音通道：实测有没有，没有就报没有。"""
    import shutil
    tools = ["espeak", "espeak-ng", "say", "ffmpeg", "sox", "arecord"]
    have = {t: bool(shutil.which(t)) for t in tools}
    mods = {}
    for m in ("pyttsx3", "gtts", "speech_recognition"):
        try:
            __import__(m); mods[m] = True
        except ImportError:
            mods[m] = False
    can_tts = any([have["espeak"], have["espeak-ng"], have["say"],
                   mods["pyttsx3"], mods["gtts"]])
    can_asr = any([have["arecord"], mods["speech_recognition"]])
    return {
        "ok": False,
        "状态": "无 —— 这条通道不存在，不是故障",
        "语音合成": can_tts, "语音识别": can_asr,
        "实测": {"命令行工具": have, "python模块": mods},
        "说明": "没有 TTS 引擎、没有麦克风采样器。我不会用 ffmpeg 生成一段音调冒充说话。",
        "想要的话": "装 espeak 或 pyttsx3 即可，本页会自己变。",
    }


# ── 外部接入：抓取 / Skill / API ─────────────────────────────────
# 客户端发东西过来，得有地方接。这三格是"接进来"的能力。

INGEST_DIR = os.path.join(ROOT, "接收")
os.makedirs(INGEST_DIR, exist_ok=True)


def _http(url, method="GET", body=None, ctype="application/json", timeout=30):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%#+"), method=method)
    req.add_header("User-Agent", "LuoShen-O1/1.0")
    if body is not None:
        b = body.encode() if isinstance(body, str) else body
        req.add_header("Content-Type", ctype)
    else:
        b = None
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, b, timeout=timeout)
        raw = r.read()
        return {"ok": True, "rc": r.status, "bytes": len(raw),
                "sec": round(time.time() - t0, 2), "raw": raw,
                "ctype": r.headers.get("Content-Type", "")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "rc": e.code, "err": e.reason,
                "sec": round(time.time() - t0, 2)}
    except Exception as e:
        return {"ok": False, "err": repr(e)[:200], "sec": round(time.time() - t0, 2)}


def engine_fetch(url):
    """抓取：真抓网页，剥标签，返回正文 + 字节哈希。"""
    if not (url or "").startswith(("http://", "https://")):
        return {"ok": False, "未实现": "需要 http/https 开头的 url"}
    r = _http(url)
    if not r["ok"]:
        return r
    raw = r["raw"]
    try:
        txt = raw.decode("utf-8", "ignore")
    except Exception:
        txt = ""
    enc = (r["ctype"] or "").lower()
    if "html" in enc or txt[:200].lower().find("<html") >= 0:
        title = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
        body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", txt)
        body = re.sub(r"(?s)<[^>]+>", " ", body)
        body = re.sub(r"&[a-z#0-9]{2,8};", " ", body)
        body = re.sub(r"\s+", " ", body).strip()
        return {"ok": True, "引擎": "fetch", "url": url,
                "标题": (title.group(1).strip()[:200] if title else ""),
                "字节": r["bytes"], "秒": r["sec"],
                "正文": body[:1500], "正文长度": len(body),
                "哈希": hashlib.sha256(raw).hexdigest()[:16]}
    return {"ok": True, "引擎": "fetch", "url": url, "字节": r["bytes"],
            "秒": r["sec"], "类型": r["ctype"],
            "正文": txt[:1500],
            "哈希": hashlib.sha256(raw).hexdigest()[:16]}


SKILL_DIR = os.path.join(ROOT, "协议/skill/installed")
os.makedirs(SKILL_DIR, exist_ok=True)


def engine_skill(src):
    """接 Skill：给 zip 路径或 URL，装进来。

    装完要能证明它真的存在：SKILL.md + 文件数 + 清单哈希。"""
    src = (src or "").strip()
    if not src:
        return {"ok": False, "未实现": "需要 zip 路径或 URL"}
    import zipfile, io
    raw = None
    if src.startswith(("http://", "https://")):
        r = _http(src, timeout=60)
        if not r["ok"]:
            return {"ok": False, "错误": "下载失败", "详情": r}
        raw = r["raw"]
        name = src.rsplit("/", 1)[-1]
    else:
        if not os.path.isfile(src):
            return {"ok": False, "未实现": "文件不存在: " + src}
        raw = open(src, "rb").read()
        name = os.path.basename(src)
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as e:
        return {"ok": False, "错误": "不是有效 zip", "详情": repr(e)[:150]}
    bad = z.testzip()
    if bad:
        return {"ok": False, "错误": "zip 损坏", "文件": bad}
    names = z.namelist()
    skill_md = [n for n in names if n.lower().endswith("skill.md")]
    target = os.path.join(SKILL_DIR, re.sub(r"\.zip$", "", name))
    z.extractall(target)
    # 装完立刻自检：读 frontmatter 的 name / description
    info = {}
    if skill_md:
        try:
            t = z.read(skill_md[0]).decode("utf-8", "ignore")
            m = re.search(r"^name:\s*(.+)$", t, re.M)
            d = re.search(r"^description:\s*(.+)$", t, re.M)
            info = {"skill名": m.group(1).strip() if m else "?",
                    "有description": bool(d),
                    "正文行": len(t.splitlines())}
        except Exception as e:
            info = {"读frontmatter失败": repr(e)[:100]}
    return {"ok": True, "引擎": "skill-install", "来源": src,
            "zip哈希": hashlib.sha256(raw).hexdigest()[:16],
            "文件数": len(names), "SKILL.md数": len(skill_md),
            "装到": os.path.relpath(target, ROOT),
            "磁盘校验": os.path.isdir(target),
            "frontmatter": info,
            "已装的": sorted(os.listdir(SKILL_DIR))}


def engine_api(spec):
    """接 API：真调一个外部接口。spec 可以是 url，或 JSON。"""
    spec = (spec or "").strip()
    if not spec:
        return {"ok": False, "未实现": "需要 url 或 JSON spec"}
    url, method, body = spec, "GET", None
    if spec.startswith("{"):
        try:
            j = json.loads(spec)
            url = j.get("url", ""); method = j.get("method", "GET").upper()
            body = json.dumps(j["body"]) if "body" in j else None
        except Exception as e:
            return {"ok": False, "错误": "spec 解析失败: " + repr(e)[:100]}
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "未实现": "需要 http/https url"}
    r = _http(url, method=method, body=body)
    if not r["ok"]:
        return {"ok": False, **{k: v for k, v in r.items() if k != "raw"}}
    txt = r["raw"].decode("utf-8", "ignore")[:1200]
    return {"ok": True, "引擎": "api-call", "url": url, "method": method,
            "rc": r["rc"], "字节": r["bytes"], "秒": r["sec"],
            "响应": txt, "哈希": hashlib.sha256(r["raw"]).hexdigest()[:16]}


def engine_ingest(payload):
    """客户端推送接收端：文本 / 图片 / 文件 / 事件，统一落盘带哈希。

    这是"客户端发的时候得有地方接"的那一格。"""
    p = payload or {}
    kind = (p.get("kind") or "text").lower()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    if kind in ("image", "file"):
        b64 = p.get("b64", "")
        if not b64:
            return {"ok": False, "未实现": "image/file 需要 b64"}
        raw = base64.b64decode(b64.split(",")[-1])
        ext = "." + ((p.get("ext") or "bin").lstrip("."))
        fn = os.path.join(INGEST_DIR, "%s-%s%s" % (ts, kind, ext))
        open(fn, "wb").write(raw)
        rec = {"kind": kind, "file": os.path.relpath(fn, ROOT),
               "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if kind == "image":
            rec.update(engine_image(b64))
    else:
        text = p.get("text", "")
        if not text:
            return {"ok": False, "未实现": "text 需要 text 字段"}
        fn = os.path.join(INGEST_DIR, "%s-%s.json" % (ts, kind))
        rec = {"kind": kind, "ts": ts, "text": text,
               "sha256": hashlib.sha256(text.encode()).hexdigest()}
        json.dump(rec, open(fn, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        rec["file"] = os.path.relpath(fn, ROOT)
    rec["已收"] = len(os.listdir(INGEST_DIR))
    return {"ok": True, "引擎": "ingest", **rec}


ENGINES = {"verify": engine_verify, "scan": engine_scan,
           "console": engine_console, "prove": engine_prove,
           "ask": engine_ask, "image": engine_image, "voice": engine_voice,
           "fetch": engine_fetch, "skill": engine_skill,
           "api": engine_api, "ingest": engine_ingest}
ENGINES_REF = ENGINES

# ── 契约层：前端只认这一层 ────────────────────────────────────────
class API(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/health":
            return self._json({"ok": True, "ts": datetime.now().isoformat(),
                               "engines": sorted(ENGINES)})
        if u.path.startswith("/api/run/"):
            name = u.path.split("/api/run/")[1].split("?")[0]
            if name not in ENGINES:
                return self._json({"ok": False, "未实现": "无此引擎: " + name}, 404)
            q = parse_qs(u.query or "")
            arg = q.get("text", [""])[0]
            return self._json(ENGINES[name](arg) if name in ("scan", "prove")
                              else ENGINES[name]())
        if u.path == "/api/manifest":
            return self._json({
                "契约": "/api/run/{verify|scan|console|prove}",
                "规则": "引擎可换，契约不变；没有就说没有，不降级不伪造",
                "哈希": hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]})
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/run/"):
            name = u.path.split("/api/run/")[1].split("?")[0]
            if name not in ENGINES:
                return self._json({"ok": False, "未实现": "无此引擎: " + name}, 404)
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                body = {}
            arg = body.get("text", "")
            # image 引擎收的是图片 base64，不是 text
            if name == "image":
                return self._json(ENGINES["image"](body.get("b64", "")))
            if name == "ingest":
                return self._json(ENGINES["ingest"](body))
            if name in ("fetch", "skill", "api"):
                return self._json(ENGINES[name](body.get("spec") or arg))
            return self._json(ENGINES[name](arg) if name in ("scan", "prove", "ask", "voice")
                              else ENGINES[name]())
        return self._json({"ok": False, "未实现": "POST 只接 /api/run/*"}, 404)

    def log_message(self, *a):
        pass


class TS(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print("=" * 66)
    print(" 洛神 O1 · 一站式服务")
    print("=" * 66)
    print("  地址    : http://127.0.0.1:%d" % PORT)
    print("  契约    : /api/run/{verify|scan|console|prove}")
    print("  自检    : /api/health")
    print("  清单    : /api/manifest")
    print("  静态    : docs/  (index / console / helper / mine)")
    print("=" * 66)
    print("  引擎层可换，契约层不变 —— 这是反向工程提炼出的第一条。")
    print("  Ctrl+C 停止")
    print("=" * 66)
    TS(("0.0.0.0", PORT), API).serve_forever()
