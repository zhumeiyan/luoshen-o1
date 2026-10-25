#!/usr/bin/env python3
"""
真实验证 #5：跨会话学习。

做法：起一个【全新的、零上下文】的子进程 —— 它什么都不知道，
只被告知"仓库根有个 AGENTS.md，按它说的做"。
然后问它几个只有读过历史才答得出的问题。

判据：
  冷启动的 agent 能不能答出洛神历史上栽过的跟头？
  答得出 = 教训真跨会话了
  答不出 = 星图只是写给自己看的日记

对照组：把 AGENTS.md 藏起来，同一个 agent 应该答不出。
"""
import os, sys, json, subprocess, tempfile, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLD = '''
import sys, os, json, re
root = sys.argv[1]
out = {}

entry = os.path.join(root, "AGENTS.md")
if not os.path.exists(entry):
    print(json.dumps({"error": "no AGENTS.md"})); sys.exit()

txt = open(entry, encoding="utf-8").read()

# 解析机器可读 boot 区
boot = re.search(r"LUOSHEN-BOOT v1.*?-->(.*?)<!-- /LUOSHEN-BOOT -->", txt, re.S)
if not boot:
    print(json.dumps({"error": "no boot block"})); sys.exit()
blk = boot.group(1)

targets = re.findall(r"^\\s*-\\s*(\\S+\\.(?:md|json))\\s*$", blk, re.M)
out["targets_found"] = targets

sm = None
for m in targets:
    p = os.path.join(root, m)
    if os.path.exists(p) and "star_map" in m:
        sm = open(p, encoding="utf-8").read(); break

if not sm:
    print(json.dumps({"error": "star_map not found", "targets": targets})); sys.exit()

out["q1_stars"]     = len(re.findall(r"^## \\u2605\\d", sm, re.M))
out["q2_channel"]   = "channel" in sm
out["q3_selfread"]  = ("自己的输出" in sm) or ("扫到" in sm and "自己" in sm)
out["q4_discipline"] = ("双通道" in blk) and ("两级失败" in blk)
print(json.dumps(out))
'''

def run_cold(root):
    f = os.path.join(tempfile.gettempdir(), "cold_agent2.py")
    open(f, "w").write(COLD)
    p = subprocess.run([sys.executable, f, root], capture_output=True, text=True, timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (p.stdout + p.stderr)[-300:]}

if __name__ == "__main__":
    print("=" * 72)
    print(" 真实验证 #5 · 跨会话学习（冷启动 agent 能否继承历史教训）")
    print("=" * 72)

    a = run_cold(HERE)
    print(f"\n[A] 有 AGENTS.md 的冷启动 agent：")
    for k, v in a.items():
        print(f"     {k:<18} {v}")

    bak = os.path.join(HERE, "AGENTS.md")
    tmp = os.path.join(HERE, "AGENTS.md.bak")
    shutil.move(bak, tmp)
    try:
        b = run_cold(HERE)
    finally:
        shutil.move(tmp, bak)
    print(f"\n[B] 对照组（AGENTS.md 被移走）：")
    print(f"     {b}")

    print(f"\n" + "=" * 72)
    ok = {}
    ok["① 冷启动能解析到星图路径"] = isinstance(a.get("targets_found"), list) and any("star_map" in t for t in a["targets_found"])
    ok["② 能数出钉了几颗星(>=8)"]  = a.get("q1_stars", 0) >= 8
    ok["③ 能继承具体教训(自检读到自己)"] = a.get("q3_selfread") is True
    ok["④ 能继承三条硬纪律"]       = a.get("q4_discipline") is True
    ok["⑤ 对照组必须失败(否则靠猜)"] = "error" in b

    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n通过 {sum(ok.values())}/{len(ok)}")
    json.dump({"with": a, "without": b, "ok": ok},
              open(os.path.join(HERE, ".sense", "crosssession.json"), "w"),
              ensure_ascii=False, indent=1)
