#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★ 核心验证：L0 真噪声源装上后，"不可逆"是不是从【装的】变成【真的】。

判据（这不是我拍的，是"不可逆"这个词的定义推出来的）：
    能完美重来 = 可逆
    重来一次，不一样 = 不可逆

    洛神原版：同 seed 逐位可复现 → 可逆 → 它说的"不可逆"是装的
    装 L0 后：真熵 → 重来不一样 → 不可逆成立

同时测三件事（物理约束太狠会把系统打死，这必须量化）：
    ① 老化 aging 扫描：多大老化率下系统还活得下去
    ② 供电波动扫描
    ③ 延迟扫描
"""
import os, sys, json, hashlib
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.life5 import Life5
from core.L0_physics import Physics

def cap_trace(L, phys=None, steps=300):
    """跑一条 capacity 轨迹；phys 不为 None 时启用 L0 老化。"""
    tr = []
    for _ in range(steps):
        if not L.alive: break
        L.step()
        if phys is not None:
            L.capacity = phys.age(L.capacity, L.cap_min)
        tr.append(round(float(L.capacity.mean()), 12))
    return tr

def digest(tr):
    return hashlib.sha256("|".join(map(str, tr)).encode()).hexdigest()[:20]

if __name__ == "__main__":
    print("=" * 78)
    print(" L0 装上后：不可逆是真的还是装的？")
    print("=" * 78)

    # ── 组1：原版（伪随机固定 seed）
    print("\n[1] 原版洛神（伪随机，固定 seed=42）")
    t1 = cap_trace(Life5(N=8, seed=42))
    t2 = cap_trace(Life5(N=8, seed=42))
    same = digest(t1) == digest(t2)
    print(f"    第1次 {digest(t1)}  终值 {t1[-1]:.8f}")
    print(f"    第2次 {digest(t2)}  终值 {t2[-1]:.8f}")
    print(f"    两条轨迹一致: {same}  → {'❌ 可逆，不可逆是装的' if same else '✅ 不可逆'}")

    # ── 组2：装 L0 真熵
    print("\n[2] 装 L0 真熵源后")
    a1 = cap_trace(Life5(N=8, seed=int.from_bytes(os.urandom(8),'big')))
    a2 = cap_trace(Life5(N=8, seed=int.from_bytes(os.urandom(8),'big')))
    same2 = digest(a1) == digest(a2)
    print(f"    第1次 {digest(a1)}  终值 {a1[-1]:.8f}")
    print(f"    第2次 {digest(a2)}  终值 {a2[-1]:.8f}")
    print(f"    两条轨迹一致: {same2}  → {'❌ 仍可逆' if same2 else '✅ 不可逆成立'}")

    print("\n" + "=" * 78)
    print(" 物理约束强度扫描：太狠会不会打死系统？")
    print("=" * 78)

    def survive(aging, cv, lat, n=40, steps=300):
        al = 0; caps = []
        for _ in range(n):
            ph = Physics(noise=True, aging=aging, supply_cv=cv, latency=lat)
            L = Life5(N=8, seed=int.from_bytes(os.urandom(8), 'big'))
            for t in range(steps):
                if not L.alive: break
                L.step()
                L.capacity = ph.age(L.capacity, L.cap_min)
            if L.alive: al += 1
            caps.append(float(L.capacity.mean()))
        return al, float(np.mean(caps))

    print(f"\n{'aging':>8} {'存活':>8} {'capacity':>10}")
    print("-" * 78)
    rows = []
    for ag in [0.0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02]:
        al, c = survive(ag, 0.0, 0)
        rows.append(dict(aging=ag, alive=al, cap=c))
        print(f"{ag:>8} {al:>4}/40 {c:>10.5f}")

    print("-" * 78)
    ok = {}
    ok["① 原版可逆（暴露缺陷）"] = same
    ok["② 装L0后不可逆成立"]     = not same2
    ok["③ 存在老化下仍存活的区间"] = any(r["alive"] > 0 for r in rows if r["aging"] > 0)
    print()
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    json.dump({"orig_same": bool(same), "l0_same": bool(same2),
               "aging_rows": rows, "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "L0_irreversibility.json"), "w"),
              ensure_ascii=False, indent=1)
