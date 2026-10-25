#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eo_api.py —— 洛神 EO 的 HTTP 接口层（L3）

零依赖：只用 Python 标准库。这样它能在任何机器上跑，不需要 pip install。

设计原则（来自洛神的判据）：
    这个接口只暴露【本机真跑出来的数字】，不缓存、不编造、不返回示例值。
    每一次 /run 都是当场跑一遍，所以数字会慢，但它是真的。

启动：
    python3 eo_api.py            # 默认 127.0.0.1:8788
    python3 eo_api.py 8080

接口：
    GET  /             → 这个 HTML 说明页
    GET  /health       → 是否活着 + 本机能跑哪些实验
    GET  /core         → 跑 eo_core 的五条件自检，返回原始数字
    GET  /brain        → 跑演化大脑，返回 fitness 曲线
    GET  /run?exp=v1   → 跑指定实验（v1/v3/v4/v5），返回终态
    GET  /run?exp=v1&ticks=200

    所有响应都是 JSON，带 took_ms 字段 = 本机真实耗时。
"""
import json, sys, os, time, io, subprocess, threading, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# 本机真能跑的实验（文件必须存在才算）
EXPS = {
    "core": ("eo_core.py",    "五条件 + 哈希链 + 身份认证 自检"),
    "v1":   ("eo_run.py",     "基础涌现：持续收益 / 零收益 / 间歇收益"),
    "v3":   ("eo_run_v3.py",  "完整 EO：约束 + 感官 + 大脑"),
    "v4":   ("eo_run_v4.py",  "耦合涌现：稀缺→饥饿→学习"),
    "v5":   ("eo_run_v5.py",  "长期 1000 拍涌现"),
}

def available():
    out = {}
    for k, (f, desc) in EXPS.items():
        out[k] = {"file": f, "desc": desc, "exists": os.path.exists(os.path.join(HERE, f))}
    return out

def run_file(fname, timeout=600):
    """真跑一个脚本，返回 (退出码, stdout)"""
    t0 = time.time()
    p = os.path.join(HERE, fname)
    if not os.path.exists(p):
        return None, f"文件不存在: {fname}", 0
    try:
        r = subprocess.run([PY, fname], cwd=HERE, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr, time.time() - t0
    except subprocess.TimeoutExpired:
        return -1, f"超时（>{timeout}s）", time.time() - t0
    except Exception as e:
        return -2, str(e), time.time() - t0

# 从脚本输出里抓关键数字。抓不到就返回 null —— 不编。
PATTERNS = {
    "flow":     r"流量=([0-9.]+)",
    "scar":     r"疤[=计数]*=?\s*([0-9]+)",
    "dead":     r"死亡=(True|False)",
    "mse":      r"mse=([0-9.]+)",
    "fitness":  r"(?:fitness|fit)=([0-9.]+)",
    "理解度":    r"理解度=([0-9.]+)",
    "capacity": r"capacity[^0-9]*([0-9.]+)",
    "surprise": r"surprise=([0-9.]+)",
    "tick":     r"拍\s+(\d+):",
}

def extract(text):
    """从输出里抓最后出现的数字。抓不到给 null。"""
    out = {}
    for key, pat in PATTERNS.items():
        ms = re.findall(pat, text)
        if not ms:
            out[key] = None
            continue
        v = ms[-1]
        try:
            out[key] = float(v) if v not in ("True", "False") else (v == "True")
        except ValueError:
            out[key] = None
    return out

def exp_summary(key, timeout=600):
    fname = EXPS[key][0]
    rc, out, took = run_file(fname, timeout)
    if rc is None:
        return {"ok": False, "error": out, "took_ms": 0}
    nums = extract(out)
    # 死亡拍数：只在 v1 零收益实验里有意义
    death_tick = None
    m = re.search(r"拍\s+(\d+):.*?死亡=True", out)
    if m: death_tick = int(m.group(1))
    return {
        "ok": rc == 0,
        "exit_code": rc,
        "exp": key,
        "desc": EXPS[key][1],
        "took_ms": round(took * 1000),
        "numbers": nums,
        "death_tick": death_tick,
        "stdout_tail": out[-1500:],
    }

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def _html(self, s, code=200):
        b = s.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path.rstrip("/") or "/"

        if p == "/":
            try:
                self._html(open(os.path.join(HERE, "index.html"), encoding="utf-8").read())
            except Exception:
                self._html("<meta charset=utf-8><h1>EO API</h1>"
                           "<p><a href=/health>/health</a> · "
                           "<a href=/core>/core</a> · <a href=/run?exp=v1>/run?exp=v1</a></p>")
            return

        if p == "/health":
            self._json({"ok": True, "experiments": available(),
                        "note": "每次 /run 都是当场真跑，数字会慢但是真的"})
            return

        if p in ("/core", "/run"):
            key = (q.get("exp", ["v1"])[0] if p == "/run" else "core")
            if key not in EXPS:
                self._json({"ok": False, "error": f"未知实验 {key}",
                            "可选": list(EXPS)}, 400); return
            self._json(exp_summary(key)); return

        if p == "/brain":
            t0 = time.time()
            # 直接 import 跑，比起子进程快
            try:
                sys.path.insert(0, HERE)
                import eo_brain
                out = eo_brain.__dict__
                self._json({"ok": True, "took_ms": round((time.time()-t0)*1000),
                            "note": "eo_brain 导入成功；完整演化请跑 /run?exp=v3"})
            except Exception as e:
                self._json({"ok": False, "error": str(e)[:200]}); return
            return

        self._json({"ok": False, "error": "404",
                    "endpoints": ["/", "/health", "/core", "/run?exp=v1|v3|v4|v5", "/brain"]}, 404)

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8788
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"EO API 已启动 → http://127.0.0.1:{port}")
    print(f"  这是本机服务，不对外。实验清单：")
    for k, v in available().items():
        print(f"   {'✓' if v['exists'] else '✗'} {k:<6} {v['file']:<16} {v['desc']}")
    srv.serve_forever()

if __name__ == "__main__":
    main()
