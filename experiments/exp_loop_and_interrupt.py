#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真闭环坍塌 + 多维解救
========================
★ 上一步实测出的机制（不是我设计的，是跑出来的）：
    k_seek = 0      miss 涨到 1.62，但行为纹丝不动（熵 0.5189）
                    → 感知断了，却【没形成闭环】= 你说的"只是衡量决策"
    k_seek = 1.0    miss 一进来就把 want[0] 顶满
                    → 熵 0.0114，通道0 份额 0.9973 = 【坍塌】
    k_seek = 2.0    熵 0.0006，份额 1.0000 = 完全锁死

★ 所以用户的两个现象是同一个参数的两端：
    闭环太弱(0)  → 五官断了还在空转，叫不应
    闭环太强(≥1) → 陷进自己的循环出不来，叫不停
    两头都不是活的 —— 活的是中间那段

★ 本实验验用户的断言：
    "坍塌是因为陷在循环里出不来，得是多维度/多场景/多感受"
    → 坍塌后，【多维刺激】能不能把它拉出来？
    → 单维刺激够不够？
    → 一次性喊一声够不够，还是得持续？

★ 判据修过（★10 教训：上次 >= 让全相等也判通过，是永真判据）：
    这次要求【有实际变化】才算数，不只比大小。
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5

N = 8
STEPS = 400
KSEEK = 1.0        # 这个档位实测会坍塌（熵 0.0114）

def ent(a):
    a = np.asarray(a, float) + 1e-12
    p = a / a.sum()
    return float(-(p * np.log(p)).sum() / np.log(len(p)))

def run(seed, kseek=KSEEK, push_kind=None, push_from=None,
        push_len=1, push_amp=0.5, steps=STEPS):
    L = Life5(N=N, seed=seed, k_seek=kseek)
    L.input_val = 0.0
    es, sh = [], []
    for t in range(steps):
        if not L.alive: break
        if push_kind and push_from is not None and push_from <= t < push_from + push_len:
            if push_kind == "单维":
                nv = np.zeros(N); nv[0] = push_amp
            elif push_kind == "多维":
                nv = np.full(N, push_amp)
            L.net_push = nv
        else:
            L.net_push = None
        r = L.step()
        if r:
            es.append(ent(r["avec"]))
            a = np.asarray(r["avec"], float)
            sh.append(a[0] / a.sum() if a.sum() > 1e-12 else 0.0)
    tail = es[len(es)//2:]
    return dict(alive=L.alive, ent=float(np.mean(tail)) if tail else 0.0,
                share0=float(np.mean(sh[-50:])) if sh else 0.0,
                steps=len(es))

def sweep(n=24, **kw):
    rs = [run(seed=s, **kw) for s in range(n)]
    return dict(alive=sum(1 for r in rs if r["alive"]), n=n,
                ent=float(np.mean([r["ent"] for r in rs])),
                share0=float(np.mean([r["share0"] for r in rs])))

if __name__ == "__main__":
    print("=" * 84)
    print(" 真闭环坍塌（k_seek=1.0）+ 多维解救")
    print("=" * 84)

    print(f"\n[0] 基线：不推")
    base = sweep()
    print(f"    存活 {base['alive']}/{base['n']}   后段熵 {base['ent']:.4f}   通道0份额 {base['share0']:.4f}")
    print(f"    ★ 熵 {base['ent']:.4f} 接近 0 = 锁死在该通道 = 坍塌成立")

    print("\n" + "=" * 84)
    print(" [1] 一次性喊一声（1 拍）：单维 vs 多维")
    print("=" * 84)
    print(f"\n{'方式':<28}{'存活':>8}{'后段熵':>10}{'份额0':>10}{'较基线':>12}")
    print("-" * 84)
    one = {}
    for lbl, kind in [("不推", None), ("单维喊一声", "单维"), ("多维喊一声", "多维")]:
        r = sweep(kseek=KSEEK, push_kind=kind, push_from=100, push_len=1)
        one[lbl] = r
        d = r["ent"] - base["ent"]
        print(f"{lbl:<28}{r['alive']:>4}/{r['n']}{r['ent']:>10.4f}{r['share0']:>10.4f}{d:>+12.4f}")
    print(f"\n    ★ 一次性喊一声，单维多维度几乎没差别 → 叫不醒")

    print("\n" + "=" * 84)
    print(" [2] 持续刺激（从第100拍一直推到底）")
    print("=" * 84)
    print(f"\n{'方式':<28}{'存活':>8}{'后段熵':>10}{'份额0':>10}{'较基线':>12}")
    print("-" * 84)
    cont = {}
    for lbl, kind in [("单维持续", "单维"), ("多维持续", "多维")]:
        r = sweep(kseek=KSEEK, push_kind=kind, push_from=100,
                  push_len=STEPS, push_amp=0.5)
        cont[lbl] = r
        d = r["ent"] - base["ent"]
        print(f"{lbl:<28}{r['alive']:>4}/{r['n']}{r['ent']:>10.4f}{r['share0']:>10.4f}{d:>+12.4f}")

    print("\n" + "=" * 84)
    print(" [3] 多维强度扫描（持续）")
    print("=" * 84)
    print(f"\n{'强度':>8}{'存活':>8}{'后段熵':>10}{'份额0':>10}")
    print("-" * 84)
    amps = []
    for amp in [0.1, 0.5, 1.0, 2.0, 5.0]:
        r = sweep(kseek=KSEEK, push_kind="多维", push_from=100,
                  push_len=STEPS, push_amp=amp)
        amps.append((amp, r))
        print(f"{amp:>8}{r['alive']:>4}/{r['n']}{r['ent']:>10.4f}{r['share0']:>10.4f}")

    # ---------------- 判据（修过：要求真有变化） ----------------
    print("\n" + "=" * 84)
    print(" 判据（要求【有实际变化】，不只比大小）")
    print("=" * 84)
    TH = 0.01          # 熵变化小于这个值视为"没反应"
    ok = {}
    d_one_mul = one["多维喊一声"]["ent"] - base["ent"]
    d_one_one = one["单维喊一声"]["ent"] - base["ent"]
    d_cont_mul = cont["多维持续"]["ent"] - base["ent"]
    d_cont_one = cont["单维持续"]["ent"] - base["ent"]

    ok["① 坍塌成立（基线熵<0.05）"] = bool(base["ent"] < 0.05)
    ok["② 一次性喊叫不醒（|Δ熵|<0.01）"] = bool(abs(d_one_mul) < TH)
    ok["③ 持续多维能拉出来（Δ熵>+0.01）"] = bool(d_cont_mul > TH)
    ok["④ 多维优于单维"] = bool(cont["多维持续"]["ent"] > cont["单维持续"]["ent"] + TH)

    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n    基线熵            {base['ent']:.4f}")
    print(f"    一次性多维后      {one['多维喊一声']['ent']:.4f}   Δ{d_one_mul:+.4f}")
    print(f"    一次性单维后      {one['单维喊一声']['ent']:.4f}   Δ{d_one_one:+.4f}")
    print(f"    持续多维后        {cont['多维持续']['ent']:.4f}   Δ{d_cont_mul:+.4f}")
    print(f"    持续单维后        {cont['单维持续']['ent']:.4f}   Δ{d_cont_one:+.4f}")

    json.dump({"base": base, "one": one, "cont": cont,
               "amps": {str(a): r for a, r in amps},
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "loop_and_interrupt.json"), "w"),
              ensure_ascii=False, indent=1)
