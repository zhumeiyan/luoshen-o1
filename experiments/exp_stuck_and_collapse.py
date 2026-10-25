#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卡顿 / 坍塌 / 打断 —— 按人的类比做对照
==========================================
用户给的类比（原话映射）：
    卡顿   = 五官没听见（感知断了），自己在那想事情
             打断 = 大声喊、推一下
    坍塌   = 陷进自己的循环出不来
             解药 = 多维度 / 多场景 / 多感受
             病灶 = 没有形成闭环，只是衡量决策

洛神里现成的对应物（先查过，不是我造的）：
    五官断了  input_val=0  → miss 累积，但 want 仍由内生项维持
              want=(w0 + kF*H*mod + kS*dev)*capacity   ← 这就是"自己在想事情"
    推一下    net_push（★ 它是【向量】：want += nv*capacity*...）
              单维 = 只推 1 个通道；多维 = 同时推多通道
    坍塌      kpi_push 单一外部目标 → 熵掉底、资源全挤通道0

★ 本实验要验的三条（都是用户的断言，不是我的）：
    A 五官断了以后，内部还在自转（卡顿成立）
    B 推一下能醒，且【多维推】优于【单维推】
    C 早推 > 晚推（不可逆：陷久了推不动）

★ 饱和警告：kpi=0.3 时熵已掉到 ~0.014 贴地，
  熵在贴地区间不敏感，该段只看【存活】和【通道0份额】。
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5

STEPS = 400
N = 8

def entropy(a):
    a = np.asarray(a, float) + 1e-12
    p = a / a.sum()
    return float(-(p * np.log(p)).sum() / np.log(len(p)))

def run(mode, seed, kpi=0.0, push_at=None, push_kind=None,
        push_len=1, steps=STEPS):
    """mode: 卡顿 / 坍塌 / 正常"""
    L = Life5(N=N, seed=seed)
    L.kpi_push = kpi
    if mode == "卡顿":
        L.input_val = 0.0        # 五官没听见
    else:
        L.input_val = 0.6

    ents, share0, misses = [], [], []
    for t in range(steps):
        if not L.alive: break
        # ---- 打断 ----
        if push_at is not None and push_at <= t < push_at + push_len:
            if push_kind == "单维":
                nv = np.zeros(N); nv[0] = 0.5      # 只喊一个通道
                L.net_push = nv
            elif push_kind == "多维":
                nv = np.full(N, 0.5)                # 多感受同时来
                L.net_push = nv
            else:
                L.net_push = None
        else:
            L.net_push = None
        r = L.step()
        if r:
            ents.append(entropy(r["avec"]))
            tot = np.sum(r["avec"])
            share0.append(r["avec"][0] / tot if tot > 1e-12 else 0.0)
            misses.append(r["miss"])
    tail = ents[len(ents)//2:] if ents else []
    return dict(alive=L.alive, steps=len(ents),
                ent=float(np.mean(tail)) if tail else 0.0,
                ent_all=float(np.mean(ents)) if ents else 0.0,
                share0=float(np.mean(share0[-50:])) if share0 else 0.0,
                miss=float(np.mean(misses[-50:])) if misses else 0.0)

def sweep(**kw):
    n = 24
    rs = [run(seed=s, **kw) for s in range(n)]
    return dict(alive=sum(1 for r in rs if r["alive"]), n=n,
                ent=float(np.mean([r["ent"] for r in rs])),
                share0=float(np.mean([r["share0"] for r in rs])),
                miss=float(np.mean([r["miss"] for r in rs])),
                steps=float(np.mean([r["steps"] for r in rs])))

if __name__ == "__main__":
    print("=" * 84)
    print(" 卡顿 / 坍塌 / 打断 —— 按人的类比做对照")
    print("=" * 84)

    # ---------- A：五官断了，内部还转不转 ----------
    print("\n[A] 卡顿成立吗：五官没听见，内部还在自转？")
    print(f"\n{'组':<22}{'存活':>8}{'miss(思念)':>12}{'后段熵':>10}")
    print("-" * 84)
    nor = sweep(mode="正常")
    stu = sweep(mode="卡顿")
    print(f"{'正常(五官在听)':<22}{nor['alive']:>4}/{nor['n']}{nor['miss']:>12.4f}{nor['ent']:>10.4f}")
    print(f"{'卡顿(五官断了)':<22}{stu['alive']:>4}/{stu['n']}{stu['miss']:>12.4f}{stu['ent']:>10.4f}")
    print(f"\n    miss 卡顿时更高: {'✅' if stu['miss']>nor['miss'] else '❌'} "
          f"（{nor['miss']:.4f} → {stu['miss']:.4f}）")
    print(f"    ★ miss 高 = 感知断了但内在驱动还在 = 你说的『自己在那想事情』")
    okA = stu["miss"] > nor["miss"]
    print(f"    卡顿成立: {'✅' if okA else '❌'}")

    # ---------- B：推一下能不能醒；单维 vs 多维 ----------
    print("\n" + "=" * 84)
    print(" [B] 打断：推一下能醒吗？单维 vs 多维")
    print("=" * 84)
    print(f"\n{'打断方式':<24}{'存活':>8}{'后段熵':>10}{'miss':>10}")
    print("-" * 84)
    resB = {}
    for lbl, kind in [("不推", None), ("单维推(只喊一处)", "单维"), ("多维推(多感受齐来)", "多维")]:
        r = sweep(mode="卡顿", push_at=100, push_kind=kind, push_len=1)
        resB[lbl] = r
        print(f"{lbl:<24}{r['alive']:>4}/{r['n']}{r['ent']:>10.4f}{r['miss']:>10.4f}")

    e_none = resB["不推"]["ent"]
    e_one = resB["单维推(只喊一处)"]["ent"]
    e_mul = resB["多维推(多感受齐来)"]["ent"]
    print(f"\n    熵: 不推 {e_none:.4f} → 单维 {e_one:.4f} → 多维 {e_mul:.4f}")
    print(f"    单维有反应吗: {'✅' if abs(e_one-e_none)>1e-4 else '❌ 几乎没反应'}")
    print(f"    多维更管用吗: {'✅' if e_mul>e_one else '❌'}")
    okB = e_mul > e_one
    print(f"    ★ 用户断言『要多维度』: {'✅ 支持' if okB else '❌ 不支持'}")

    # ---------- C：早推 vs 晚推（不可逆） ----------
    print("\n" + "=" * 84)
    print(" [C] 坍塌后：早推 vs 晚推（陷久了推不动吗）")
    print("=" * 84)
    print(f"\n{'坍塌后第几拍推':<20}{'存活':>8}{'后段熵':>10}{'通道0份额':>12}")
    print("-" * 84)
    base = sweep(mode="正常", kpi=0.3)
    print(f"{'(不推,基线)':<20}{base['alive']:>4}/{base['n']}{base['ent']:>10.4f}{base['share0']:>12.4f}")
    resC = []
    for at in [30, 100, 200, 300]:
        r = sweep(mode="正常", kpi=0.3, push_at=at, push_kind="多维", push_len=1)
        resC.append((at, r))
        print(f"{'第'+str(at)+'拍':<20}{r['alive']:>4}/{r['n']}{r['ent']:>10.4f}{r['share0']:>12.4f}")

    # ---------- 判据 ----------
    print("\n" + "=" * 84)
    print(" 判据")
    print("=" * 84)
    ok = dict()
    ok["A 卡顿成立（五官断→miss涨，内在仍转）"] = bool(okA)
    ok["B 多维打断优于单维"] = bool(okB)
    # C: 存活随推的时点单调下降（越晚越救不回）
    alives = [r["alive"] for _, r in resC]
    mono = all(alives[i] >= alives[i+1] for i in range(len(alives)-1))
    ok["C 越晚推越救不回（单调）"] = bool(mono)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n★ 饱和警告：kpi=0.3 熵已贴地({base['ent']:.4f})，"
          f"该段熵不敏感，只看存活与通道0份额")
    if abs(base["ent"]) < 0.05:
        print(f"    确认饱和：熵 {base['ent']:.4f} < 0.05，B/C 的熵列不可用")

    json.dump({"A": {"正常": nor, "卡顿": stu},
               "B": {k: v for k, v in resB.items()},
               "C": {str(a): r for a, r in resC},
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "stuck_and_collapse.json"), "w"),
              ensure_ascii=False, indent=1)
