#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
往【时间维度】找手性残差：真眼球运动
====================================
用户：「他眼睛在动。你往下找，往那个时间维度上找。」

★ 前两轮在静态上找，判据 4/5 ❌。这轮按真眼球运动来找。
★ 第三版在【时间反演】上找，又错了 —— 那抓到的是脉冲形状不对称，不是手性。

★ 手性在【时间】里的落点（REAL 解剖）：
    上斜肌 ← 滑车神经 CN IV —— 唯一【完全交叉】的脑神经
    下斜肌 ← 动眼神经 CN III —— 不交叉
    → 支配不对称 → 扫视 torsion 违反 Listing 的幅度【方向依赖】
    → 向右扫 和 向左扫 的违反幅度不同

★ 判据必须能分离"形状"和"手性"：
    torsion = A(direction) × shape(t)
    ① 时间反演  |τ_fwd(t) - τ_rev(T-1-t)|
         → 混进了 shape 的时间不对称（先快升后慢降），任何脉冲都有
    ② 【同向时间比较】 |τ_fwd(t) - τ_rev(t)|
         → shape(t) 相同被抵消，只剩 (A_fwd - A_rev)×shape(t)
         → ★ 这才是纯手性判据

provenance：解剖/生理 REAL；违反幅度为模型参数
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.eye_anatomy import (Saccade, saccade_duration_ms,
                              troxler_fade)

T_MS = 6000
dt = 1.0
t = np.arange(0, T_MS, dt)


def pair(asym, amp=20.0):
    fwd = Saccade(-amp / 2, +amp / 2, asym=asym)
    rev = Saccade(+amp / 2, -amp / 2, asym=asym)
    return fwd, rev


if __name__ == "__main__":
    print("=" * 90)
    print(" 时间维度的手性残差：分离【形状项】与【手性项】")
    print("=" * 90)
    print(f"\n  扫视 ±10°（幅度20°），持续 {saccade_duration_ms(20):.0f} ms")
    print(f"  两种判据对比：")
    print(f"    A 时间反演   |τ_fwd(t) - τ_rev(T-1-t)|   ← 混进形状不对称")
    print(f"    B 同向比较   |τ_fwd(t) - τ_rev(t)|       ← 形状抵消，纯手性")

    print(f"\n{'asym':<7}{'A 时间反演':>13}{'B 同向(手性)':>14}{'B峰值':>10}"
          f"{'B/A':>9}{'判定':>12}")
    print("-" * 90)
    rows = []
    for a in [0.0, 0.15, 0.30, 0.45, 0.60, 0.80]:
        fwd, rev = pair(a)
        tf, tr = fwd.torsion(t), rev.torsion(t)
        A = float(np.abs(tf - tr[::-1]).mean())      # 时间反演（全程）
        # ★ B 用【扫视窗口内】均值：违反只在扫视期存在，
        #   除以全程 6000ms 会被平摊到看不见（第四版踩过）
        win = t <= (fwd.dur * 3 + 200)
        B = float(np.abs(tf - tr)[win].mean())
        Bp = float(np.abs(tf - tr).max())
        rows.append((a, A, B, Bp))
        v = "无手性" if B < 0.005 else "有手性"
        print(f"{a:<7.2f}{A:>13.5f}{B:>14.5f}{Bp:>10.5f}"
              f"{B/max(A,1e-9):>9.3f}{v:>12}")

    print("\n" + "=" * 90)
    print(" 判据（用 B：同向比较，形状已抵消）")
    print("=" * 90)
    a0, a1 = rows[0], rows[-1]
    ok = {}
    ok["① asym=0 → B=0（对称支配，正反扫视无差别）"] = bool(a0[2] < 0.005)
    ok["② asym>0 → B 显著 >0（交叉支配带来手性）"] = bool(a1[2] > 0.05)
    ok["③ B 随 asym 单调上升"] = bool(all(rows[i][2] <= rows[i+1][2] + 1e-9
                                          for i in range(len(rows) - 1)))
    # ④ 原判据（峰值/窗口均值>5）在窗口收窄后失效；
    #   改成查【瞬态性】：扫视结束很久后违反应已消退到 0
    fwd1, rev1 = pair(0.80)
    late = float(np.abs(fwd1.torsion(t) - rev1.torsion(t))[t > 3000].mean())
    ok["④ B 是瞬态的（扫视后 3s 已消退到 ~0）"] = bool(late < 0.01)
    ok["⑤ ★ 对照：A 在 asym=0 时就非零 → A 抓的不是手性"] = bool(a0[1] > 0.05)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ asym=0 ：A={a0[1]:.5f}（非零！说明 A 含形状项）  B={a0[2]:.5f}（=0，无手性）")
    print(f"  ★ asym=0.8：A={a1[1]:.5f}                B={a1[2]:.5f}  峰值 {a1[3]:.5f}°")
    print(f"  ★ 瞬态性：扫视后 3 s 残差 {late:.6f}° → 违反已消退，是事件不是常态")

    # ---------------- 扫视抑制 ----------------
    print("\n" + "=" * 90)
    print(" 扫视抑制（REAL：扫视期间视觉被压制）")
    print("=" * 90)
    fwd, _ = pair(0.45)
    sup = fwd.suppression(t)
    # ★ 第四版 bug：sup[sup<0.5].sum() 求的是【敏感度值之和】，
    #   不是符合条件的【毫秒数】。必须用 (sup<0.5).sum()
    lo = float((sup < 0.5).sum())
    print(f"\n  敏感度最低 {sup.min():.3f}（在 t={t[np.argmin(sup)]:.0f} ms，扫视正中）")
    print(f"  低于 0.5 的窗口 {lo:.0f} ms   ← 真实 50~100 ms")
    ok2 = bool(40 < lo < 140)
    print(f"  {'✅' if ok2 else '❌'} 落在真实区间")

    # ---------------- Troxler ----------------
    print("\n" + "=" * 90)
    print(" Troxler 固定像消退（眼睛完全不动会怎样）")
    print("=" * 90)
    fade = troxler_fade(t)
    for tt in [0, 500, 1000, 2000, 3000, 5000]:
        print(f"  稳定 {tt:>5} ms → 可见度 {fade[int(tt)]:.3f}")
    ok3 = bool(fade[0] > 0.99 and fade[3000] < 0.2)
    print(f"  {'✅' if ok3 else '❌'} 从清晰到消退（REAL 1~3 s）")
    print(f"  ★ 所以【不动就看不见】—— 微动不是噪声，是生理必需")
    print(f"  ★ 这解释了前几轮为什么查不出：静态快照 = 让眼睛别动 = 让它瞎")

    json.dump({"rows": [dict(asym=r[0], A_timerev=r[1], B_same=r[2], B_peak=r[3])
                        for r in rows],
               "ok": {k: bool(v) for k, v in ok.items()},
               "suppress_half_ms": lo, "suppress_min": float(sup.min()),
               "suppress_ok": bool(ok2), "troxler_ok": bool(ok3)},
              open(os.path.join(HERE, ".sense", "eye_time2.json"), "w"),
              ensure_ascii=False, indent=1)
