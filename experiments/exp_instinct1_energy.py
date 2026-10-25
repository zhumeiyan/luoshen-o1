#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本能层 第1步 · 能量/进食 —— 对照实验
======================================
★ 不做"证明我对"，做"看它到底怎么变"。
   装上节能本能【可能更好，也可能更坏】：
     省了 basal 和吞吐 → 少花钱
     但 cap 降 → 摄食通道 done[forage_ch] 也降 → 少赚钱
   净效果未知。跑出来是什么就是什么。

对照：
    A 原版      Life5 裸跑（basal 恒定，只有 cap_max*e 被动缩）
    B 本能版    EnergyInstinct 包装（主动分档降级）
    C 降级关掉  只记账不降级 —— 用来分离"记账"和"降级"各自的贡献

三个场景：
    不喂 / 半喂 / 足喂
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5
from core.instinct1_energy import EnergyInstinct

STEPS = 600

def run_A(seed, steps=STEPS):
    L = Life5(N=8, seed=seed)
    for _ in range(steps):
        if not L.alive: break
        L.step()
    return dict(alive=L.alive, steps=len(L.log), E=L.E,
                cap=float(L.capacity.mean()), basal=L.basal)

def run_B(seed, steps=STEPS, downgrade=True, budget=1.0):
    L = Life5(N=8, seed=seed)
    I = EnergyInstinct(L, budget=budget, enable_downgrade=downgrade)
    I.run(steps)
    return dict(alive=L.alive, steps=I.t, E=L.E,
                cap=float(L.capacity.mean()), basal=L.basal,
                tier=I.tier, overruns=len(I.overruns),
                tiers=sorted(set(I.tier_hist)))

def sweep(fn, n=32):
    rs = [fn(s) for s in range(n)]
    return dict(alive=sum(1 for r in rs if r["alive"]), n=n,
                steps=float(np.mean([r["steps"] for r in rs])),
                E=float(np.mean([r["E"] for r in rs])),
                cap=float(np.mean([r["cap"] for r in rs])),
                basal=float(np.mean([r["basal"] for r in rs])),
                tiers=sorted(set(t for r in rs for t in r.get("tiers", []))))

if __name__ == "__main__":
    print("=" * 80)
    print(" 本能层 第1步 · 能量/进食 —— 对照")
    print("=" * 80)
    print(f"\n{'组':<26}{'存活':>8}{'均步数':>9}{'终E':>9}{'终capacity':>12}{'终basal':>10}")
    print("-" * 80)
    A = sweep(run_A)
    print(f"{'A 原版(无本能)':<26}{A['alive']:>4}/{A['n']}{A['steps']:>9.1f}"
          f"{A['E']:>9.4f}{A['cap']:>12.4f}{A['basal']:>10.5f}")
    B = sweep(run_B)
    print(f"{'B 本能版(分档降级)':<26}{B['alive']:>4}/{B['n']}{B['steps']:>9.1f}"
          f"{B['E']:>9.4f}{B['cap']:>12.4f}{B['basal']:>10.5f}")
    print(f"    走过档位: {B['tiers']}")
    C = sweep(lambda s: run_B(s, downgrade=False))
    print(f"{'C 只记账不降级':<26}{C['alive']:>4}/{C['n']}{C['steps']:>9.1f}"
          f"{C['E']:>9.4f}{C['cap']:>12.4f}{C['basal']:>10.5f}")
    print(f"    走过档位: {C['tiers']}")

    print("\n" + "=" * 80)
    print(" 判据")
    print("=" * 80)
    ok = {}
    # ① 降级真生效：B 的 basal 必须低于 A（且 A 是恒定的）
    ok["① 降级真生效（basal被调低）"] = B["basal"] < A["basal"] - 1e-9
    # ② 档位真的走过多个（不是一直卡在充足）
    ok["② 真走过多个档位"] = len(B["tiers"]) >= 2
    # ③ 记账组 basal 不该变（分离对照）
    ok["③ 记账组 basal 不变（对照干净）"] = abs(C["basal"] - A["basal"]) < 1e-9
    # ④ 节能的净效果 —— 不预设方向，只记录
    dE = B["E"] - A["E"]
    dstep = B["steps"] - A["steps"]

    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  净效果（不预设方向）：")
    print(f"    终E      B−A = {dE:+.4f}   ({'省下了' if dE>0 else '反而更亏'})")
    print(f"    存活步数 B−A = {dstep:+.1f}  ({'活更久' if dstep>0 else '死更早'})")

    # ---- ③ 超支停机是否真能触发 ----
    print("\n" + "=" * 80)
    print(" ③ 超支停机：预算收紧后会不会真的停？")
    print("=" * 80)
    print(f"\n{'budget':>9}{'停机率':>10}{'均步数':>9}{'超支次数':>10}")
    print("-" * 80)
    shut = []
    for bg in [2.0, 1.0, 0.5, 0.2, 0.1, 0.05]:
        rs = [run_B(s, budget=bg) for s in range(24)]
        n_shut = sum(1 for r in rs if not r["alive"])
        shut.append(dict(budget=bg, shut=n_shut,
                         steps=float(np.mean([r["steps"] for r in rs])),
                         ov=float(np.mean([r["overruns"] for r in rs]))))
        print(f"{bg:>9}{n_shut:>6}/24{float(np.mean([r['steps'] for r in rs])):>9.1f}"
              f"{float(np.mean([r['overruns'] for r in rs])):>10.2f}")
    print("-" * 80)
    mono = all(shut[i]["shut"] <= shut[i+1]["shut"] for i in range(len(shut)-1))
    print(f"  预算越紧停机越多（单调）: {'✅' if mono else '❌ 不单调'}")
    ok["④ 预算越紧停机越多"] = mono

    # ★ 饱和警告
    print(f"\n★ 饱和检查：budget=2.0 与 1.0 若结果完全相同 → 该区间指标不敏感，别拿来下结论")
    if abs(shut[0]["steps"] - shut[1]["steps"]) < 1e-9 and shut[0]["shut"] == shut[1]["shut"]:
        print(f"    ⚠️ budget 2.0 与 1.0 完全一致 —— 这段区间饱和，不可用")
    else:
        print(f"    两者有差异，指标在该区间可用")

    json.dump({"A": A, "B": B, "C": C, "shut": shut,
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "instinct1_energy.json"), "w"),
              ensure_ascii=False, indent=1)
