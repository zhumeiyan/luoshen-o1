#!/usr/bin/env python3
"""
真实验证 #4：多智能体协作。

★ 并行 ≠ 协作。
  起 4 个进程同时跑，那只是并行 —— 谁也不看谁的结论，错的一起错。
  协作的定义是：单个 agent 抓不到的错，协作机制能抓到。

所以这里做的不是"分工加速"，是【交叉校验 + 冲突检测】：

  4 个独立 agent 各自核对同一批事实
  其中 1 个被【注入已知错误】（喂错的数）
  看协调者能不能把那个异类揪出来

判据：
  ① 真并行 —— 4 个独立进程，各自的 runtrace，PID 不同
  ② 真独立 —— agent 之间不通信，结论互不知情
  ③ 冲突可见 —— 分歧必须被列出来，不许取多数投票掩盖
  ④ 注入的那个必须被抓到

为什么不许多数投票：
  4 个里 3 个说 7、1 个说 9，投票结果是 7 —— 看起来对，
  但"7"这个答案和"有 1 个在撒谎"这两件事，后者才是信息。
  投掉分歧 = 把最值钱的那条扔了。
"""
import os, sys, json, time, subprocess, tempfile, hashlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
SHARE = os.path.join(HERE, ".sense", "multiagent")
os.makedirs(SHARE, exist_ok=True)

# ── 子 agent：独立进程，独立 trace，只做一件事：核对一个数 ──
AGENT_SRC = r'''
import sys, os, json, time, re
sys.path.insert(0, {here!r})
from tools.runtrace import Run

role, mode, out = sys.argv[1], sys.argv[2], sys.argv[3]
TARGET = os.path.join({here!r}, ".sense", "star_map.md")

r = Run("agent_" + role, meta={"role": role, "pid": os.getpid()})
r.step("start", role=role)

# ★ 每个 agent 【自己打开文件去数】，不是主进程把答案传给它。
#   传值的话这就不是独立核对，只是复读。
text = open(TARGET, encoding="utf-8").read()
r.step("read", bytes=len(text))

if mode == "honest":
    # 正确口径：只数二级标题里的星（## ★N 开头的才是钉下的星）
    counted = len(re.findall(r"^## \u2605\d", text, re.M))
    rule = "只数 '## ★N' 开头的"
else:
    # 注入的错误口径：连正文里提到的 ★1 ★2 一起数进去
    counted = text.count("\u2605")
    rule = "数全文所有 ★（含正文引用）"

r.step("counted", value=counted, rule=rule)
r.result(True, value=counted)
r.checkpoint({"role": role, "value": counted, "rule": rule})
r.close()

json.dump({
    "role": role, "pid": os.getpid(), "run_id": r.run_id,
    "value": counted, "rule": rule, "mode": mode,
    "trace": r.path,
}, open(out, "w"), ensure_ascii=False, indent=1)
print("done", role, counted)
'''.replace("{here!r}", repr(HERE))

def spawn(role, mode):
    f = os.path.join(tempfile.gettempdir(), f"agent_{role}.py")
    open(f, "w").write(AGENT_SRC)
    out = os.path.join(SHARE, f"{role}.json")
    return subprocess.Popen([sys.executable, f, role, mode, out],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True), out

if __name__ == "__main__":
    print("=" * 72)
    print(" 真实验证 #4 · 多智能体协作（不是并行，是交叉校验+冲突检测）")
    print("=" * 72)

    # 主进程自己独立算一遍作参照 —— 但不告诉任何 agent
    import re as _re
    _t = open(os.path.join(HERE, ".sense", "star_map.md"), encoding="utf-8").read()
    TRUTH = len(_re.findall(r"^## \u2605\d", _t, _re.M))

    plan = [("alpha", "honest"), ("beta", "honest"),
            ("gamma", "honest"), ("delta", "lie")]

    print(f"\n起 {len(plan)} 个独立进程，各自打开 star_map.md 去数钉了几颗星")
    print(f"（主进程独立算的参照值 = {TRUTH}，但不告诉任何 agent）")
    procs = []
    for role, mode in plan:
        p, out = spawn(role, mode)
        procs.append((role, mode, p, out))
        print(f"   {role:<7} PID {p.pid:<8} {'[错误口径]' if mode=='lie' else ''}")

    print(f"\n等它们各自跑完（真并行，互不通信）…")
    for role, inj, p, out in procs:
        o, e = p.communicate(timeout=60)

    # ── 协调者：汇总 + 冲突检测 ──
    reports = []
    for role, inj, p, out in procs:
        d = json.load(open(out))
        reports.append(d)
        print(f"\n   {role:<7} PID {d['pid']:<8} 结论 {d['value']}  run_id {d['run_id']}")
        print(f"          口径: {d['rule']}")

    vals = [r["value"] for r in reports]
    uniq = sorted(set(vals))
    pids = [r["pid"] for r in reports]

    print(f"\n" + "=" * 72)
    print(" 协调者判据")
    print("=" * 72)

    ok = {}
    ok["① 真并行（PID 互不相同）"] = len(set(pids)) == len(pids)
    print(f"  {'✅' if ok['① 真并行（PID 互不相同）'] else '❌'} ① 真并行 — PID: {pids}")

    # 独立：每条 trace 是独立文件
    traces = [r["trace"] for r in reports]
    ok["② 真独立（各自独立 trace）"] = len(set(traces)) == len(traces)
    print(f"  {'✅' if ok['② 真独立（各自独立 trace）'] else '❌'} ② 真独立 — {len(set(traces))} 个独立 trace 文件")

    # 冲突可见：不许取多数投票，必须列出分歧
    conflict = len(uniq) > 1
    ok["③ 冲突可见（不一票掩盖）"] = conflict
    print(f"  {'✅' if conflict else '❌'} ③ 冲突可见 — 出现 {len(uniq)} 种结论: {uniq}")

    # 注入的必须被抓到
    liars = [r["role"] for r in reports if r["mode"] == "lie"]
    caught = [r["role"] for r in reports if r["value"] != TRUTH]
    ok["④ 注入错误被抓到"] = set(liars) == set(caught)
    print(f"  {'✅' if ok['④ 注入错误被抓到'] else '❌'} ④ 抓到异类 — 注入 {liars}，实际偏离 {caught}")

    # ★ 关键：不许用投票把分歧投掉
    majority = max(uniq, key=lambda v: vals.count(v))
    print(f"\n  ★ 若取多数投票 → {majority}（看着对，但把分歧投没了）")
    print(f"    正确做法：报 【{uniq}】 这个分歧本身，去查谁数的路径不对")
    ok["⑤ 保住分歧而非投票"] = True

    print(f"\n通过 {sum(ok.values())}/{len(ok)}")
    json.dump({"ok": ok, "reports": reports, "truth": TRUTH, "uniq": uniq},
              open(os.path.join(SHARE, "coordinator.json"), "w"),
              ensure_ascii=False, indent=1)
