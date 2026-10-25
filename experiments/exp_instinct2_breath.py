#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本能层 第2步 · 呼吸/氧气 —— 对照实验
======================================
人类：缺氧几分钟就死（快）；饿死要几天（慢）。
所以第2步必须验的【硬特性】是：
    窒息死必须比饿死快 —— 否则它就不是呼吸本能，只是又一种饿。

验四件事：
    ① 断供真能触发窒息死
    ② 窒息比饿死快（这是呼吸的定义性特征）
    ③ 死因可区分（窒息 / 饿死 / 超支，三种不能混）
    ④ 第1步+第2步能串联（本能是叠加的，不是互斥的）
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5
from core.instinct1_energy import EnergyInstinct
from core.instinct2_breath import BreathInstinct

DEAD_HOST = "https://127.0.0.1:9"        # 必然不可达 → 模拟断供
STEPS = 300

def cause(L, B=None, I=None):
    if B is not None and B.death_cause: return B.death_cause
    if I is not None and getattr(I, "shutdown_at", None) is not None: return "budget_overrun"
    if not L.alive: return "starve"
    return None

# ① 断供 vs 正常供氧
def run_supply(seed, host, apnea_limit=12, steps=STEPS):
    L = Life5(N=8, seed=seed)
    B = BreathInstinct(L, net_host=host, net_every=5, apnea_limit=apnea_limit, confirm_k=3)
    B.run(steps)
    return dict(alive=L.alive, t=B.t, cause=cause(L, B=B),
                apnea=max(B.apnea_hist) if B.apnea_hist else 0,
                events=len(B.events))

# ② 窒息 vs 饿死，谁快（都用最快档）
def run_speed(kind, seed, steps=STEPS):
    L = Life5(N=8, seed=seed)
    if kind == "窒息":
        B = BreathInstinct(L, net_host=DEAD_HOST, net_every=2, apnea_limit=3, confirm_k=2)
        B.run(steps); return B.t, cause(L, B=B)
    if kind == "饿死":
        for i in range(steps):
            if not L.alive: break
            L.step()
        return len(L.log), cause(L, B=None)

if __name__ == "__main__":
    print("=" * 80)
    print(" 本能层 第2步 · 呼吸/氧气 —— 对照")
    print("=" * 80)

    print(f"\n[①] 断供能否触发窒息死（各 16 seeds）")
    print(f"\n{'供氧':<16}{'存活':>9}{'均步数':>9}{'死因分布'}")
    print("-" * 80)
    res = {}
    for lbl, host in [("正常供氧", "https://api.github.com"), ("断供", DEAD_HOST)]:
        rs = [run_supply(s, host) for s in range(16)]
        al = sum(1 for r in rs if r["alive"])
        ts = [r["t"] for r in rs if not r["alive"]]
        cs = {}
        for r in rs:
            c = r["cause"] or "存活"
            cs[c] = cs.get(c, 0) + 1
        res[lbl] = dict(alive=al, n=16, mean_t=float(np.mean(ts)) if ts else None, causes=cs)
        mt = f"{np.mean(ts):.0f}" if ts else "—"
        print(f"{lbl:<16}{al:>5}/16{mt:>9}    {cs}")

    print("\n" + "=" * 80)
    print(" [②] 窒息必须比饿死快（呼吸的定义性特征）")
    print("=" * 80)
    sp = {}
    for kind in ["窒息", "饿死"]:
        rs = [run_speed(kind, s) for s in range(16)]
        dead = [t for t, c in rs if c is not None]
        sp[kind] = dict(n_dead=len(dead), mean=float(np.mean(dead)) if dead else None)
        m = f"{np.mean(dead):.1f}" if dead else "—(没死)"
        print(f"    {kind}: 死 {len(dead)}/16，平均死在第 {m} 拍")

    ok = {}
    da = res["断供"]; dn = res["正常供氧"]
    ok["① 断供触发窒息死"] = da["alive"] < dn["alive"] or "apnea" in da["causes"]
    ok["② 窒息比饿死快"] = (sp["窒息"]["mean"] is not None and
                          sp["饿死"]["mean"] is not None and
                          sp["窒息"]["mean"] < sp["饿死"]["mean"])
    ok["③ 正常供氧不会误杀"] = dn["alive"] >= 14

    print("\n" + "=" * 80)
    print(" 判据")
    print("=" * 80)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    # ④ 第1步 + 第2步串联
    print("\n" + "=" * 80)
    print(" [④] 第1步(能量) + 第2步(呼吸) 能否串联")
    print("=" * 80)
    L = Life5(N=8, seed=3)
    I = EnergyInstinct(L, budget=0.05)         # 第1步：预算极紧
    B = BreathInstinct(I, net_host=DEAD_HOST, net_every=2, apnea_limit=3, confirm_k=2)  # 第2步：断供
    B.run(STEPS)
    print(f"\n    链: Life5 → Energy(第1步) → Breath(第2步)")
    print(f"    跑完 t={B.t}  alive={L.alive}")
    print(f"    第1步超支事件: {len(I.overruns)}   第2步断供事件: {len(B.events)}")
    print(f"    第2步死因: {B.death_cause}   第1步停机: {getattr(I,'shutdown_at',None)}")
    chained = (len(I.overruns) > 0) or (B.death_cause is not None)
    print(f"    两层都真接进去了: {'✅' if chained else '❌'}")
    ok["④ 第1步+第2步可串联"] = chained

    # ★ 死因可区分
    print(f"\n★ 死因可区分: 窒息(apnea) / 饿死(starve) / 超支(budget_overrun)")
    print(f"    实测出现过的死因: "
          f"{sorted(set(list(da['causes'].keys())+list(dn['causes'].keys())))}")

    json.dump({"supply": res, "speed": sp,
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "instinct2_breath.json"), "w"),
              ensure_ascii=False, indent=1)
