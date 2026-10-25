#!/usr/bin/env python3
"""一键验证 evalguard 的全部对外接口。

为什么要有这个文件
------------------
接口文档里写的和接口真的能跑，是两件事。本文档型项目最容易出的毛病就是
前者齐全、后者没人验过。这个脚本把"拿过来就能测"变成一条命令：

    python3 接口自检.py

它会自己起服务、打完四个端点、验完 CLI 退出码和 SARIF 结构，然后关掉服务，
打印一张通过/失败表。退出码 0 = 全通过。

不依赖 pytest，不联网，标准库 only。
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = os.path.join(HERE, "overseas")          # evalguard 包的父目录
PORT = 8787
BASE = f"http://127.0.0.1:{PORT}"

BAD_SRC = "def f():\n    try:\n        pass\n    except Exception:\n        pass\n"
CLEAN_SRC = "import random\nrandom.seed(0)\n\ndef f(x):\n    return x\n"

_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    _results.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode())


def main() -> int:
    print("evalguard 接口自检")
    print("=" * 64)

    # ---- 0. CLI（不需要服务）-------------------------------------------
    print("\n[0] 命令行")
    env = dict(os.environ, PYTHONPATH=PKG_ROOT)
    tmp = os.path.join(HERE, ".selfcheck_bad.py")
    with open(tmp, "w") as fh:
        fh.write(BAD_SRC)
    try:
        p = subprocess.run([sys.executable, "-m", "evalguard", tmp],
                           capture_output=True, text=True, env=env, cwd=PKG_ROOT)
        check("CLI 对病代码退出码 = 1", p.returncode == 1, f"rc={p.returncode}")
        p2 = subprocess.run([sys.executable, "-m", "evalguard", "--help"],
                            capture_output=True, text=True, env=env, cwd=PKG_ROOT)
        check("CLI --help 不崩溃", p2.returncode == 0, f"rc={p2.returncode}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    # ---- 1. 起服务 ------------------------------------------------------
    print("\n[1] 启动 HTTP 服务")
    srv = None
    if port_open(PORT):
        check("端口已占用，复用现有服务", True, f"{BASE}")
    else:
        srv = subprocess.Popen(
            [sys.executable, "-m", "evalguard", "serve"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=env, cwd=PKG_ROOT,
        )
        for _ in range(40):
            if port_open(PORT):
                break
            time.sleep(0.25)
        check("服务在 10s 内起来", port_open(PORT), BASE)

    try:
        # ---- 2. GET 端点 ------------------------------------------------
        print("\n[2] GET 端点")
        h = get("/health")
        check("/health ok=true", h.get("ok") is True, json.dumps(h, ensure_ascii=False)[:80])
        check("/health 报出规则数 26", h.get("rules") == 26, f"rules={h.get('rules')}")

        rl = get("/rules")
        rules = rl if isinstance(rl, list) else rl.get("rules", [])
        shipped = [r for r in rules if r.get("shipped")]
        check("/rules 返回 26 条", len(rules) == 26, f"n={len(rules)}")
        check("出货规则恰好 3 条", len(shipped) == 3,
              ",".join(r.get("eg_id", "?") for r in shipped))

        # ---- 3. POST /scan ----------------------------------------------
        print("\n[3] POST /scan")
        bad = post("/scan", {"source": BAD_SRC, "path": "bad.py"})
        check("病代码 ok=false", bad.get("ok") is False, f"counts={bad.get('counts')}")
        check("病代码出 1 个 blocker",
              bad.get("counts", {}).get("blocker") == 1,
              str([f["eg_id"] for f in bad.get("findings", [])]))
        clean = post("/scan", {"source": CLEAN_SRC, "path": "clean.py"})
        # 这一条是最容易坏的：假阳性会让"干净代码"也报东西
        check("干净代码 0 findings", len(clean.get("findings", [])) == 0,
              f"counts={clean.get('counts')}")

        # ---- 4. SARIF ----------------------------------------------------
        print("\n[4] POST /scan/sarif")
        s = post("/scan/sarif", {"source": BAD_SRC, "path": "x.py"})
        run = s.get("runs", [{}])[0]
        check("SARIF 版本 2.1.0", s.get("version") == "2.1.0", s.get("version", ""))
        check("driver 名称正确",
              run.get("tool", {}).get("driver", {}).get("name") == "evalguard")
        check("至少 1 条 result", len(run.get("results", [])) >= 1,
              f"n={len(run.get('results', []))}")
        check("每条 result 有 startLine",
              all(r["locations"][0]["physicalLocation"]["region"].get("startLine")
                  for r in run.get("results", [])))

        # ---- 5. 仓库接口产物 ---------------------------------------------
        print("\n[5] 仓库接口文件")
        for rel, why in [
            ("overseas/evalguard/action.yml", "GitHub Action 入口"),
            ("overseas/evalguard/examples/ci.yml", "可复制的 workflow"),
            ("overseas/evalguard/examples/pre-commit-config.yaml", "pre-commit 钩子"),
            ("overseas/evalguard/API.md", "接口文档"),
        ]:
            check(f"存在 {os.path.basename(rel)}", os.path.exists(os.path.join(HERE, rel)), why)

    except (urllib.error.URLError, OSError) as e:
        check("HTTP 端点可达", False, f"{type(e).__name__}: {e}")
    finally:
        if srv:
            srv.terminate()
            try:
                srv.wait(timeout=5)
            except subprocess.TimeoutExpired:
                srv.kill()

    # ---- 汇总 -----------------------------------------------------------
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print("\n" + "=" * 64)
    print(f"{passed}/{total} 通过")
    if passed < total:
        print("\n失败项：")
        for name, ok, detail in _results:
            if not ok:
                print(f"  - {name}  {detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
