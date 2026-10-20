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


ENGINES = {"verify": engine_verify, "scan": engine_scan,
           "console": engine_console, "prove": engine_prove,
           "ask": engine_ask, "image": engine_image, "voice": engine_voice}
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
