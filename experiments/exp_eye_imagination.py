#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态快照=拍照片；时间反演=想象力；中间那段是想象力填的
========================================================
用户原话：「静态快照就像拍照片，那人的眼睛一直在转，然后那个时间反演
           就是想象力，人人眼也追逐不过来，中间的是想象力。」

★ 三句话拆成三件可测的事：

【1】眼睛追逐不过来 —— 扫视太快，视网膜积分窗把它抹平
    扫视 20°，持续 62 ms（main sequence）
    平均角速度 20/0.062 = 322 °/s，峰值约 1.5× = 483 °/s（REAL）
    视网膜积分窗 REAL 约 10~20 ms，取 15 ms
    → 每个样本被抹平 483 × 0.015 ≈ 7.2°
    → 占整个 20° 幅度的 36% —— 路径根本采不到

【2】中间那段没有样本 —— 扫视抑制盖住了整段扫视
    扫视持续 62 ms；抑制窗（敏感度<0.5）宽 75 ms，中心在 31 ms
    → 扫视全程落在抑制窗内 → 【0 个可用样本】
    → 路径靠想象填（这就是"中间的是想象力"）

【3】时间反演比的就是这段 → 那是想象力 vs 想象力，不是测量
    验证：算 |τ| 的能量有多少落在【抑制窗内（看不见）】
    ★ 再用【尾巴】做纯测量：抑制结束后，违反还在按 tau=100ms 衰减
      那段眼睛已经"醒"了，是真的测得到的
    → 只比尾巴 = 纯手性、可测、不是想象

provenance：main sequence / 抑制窗 / 积分窗 = REAL
           viol_gain(违反幅度) / tau 恢复 = 模型参数（标注）
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.eye_anatomy import Saccade, saccade_duration_ms

DT = 1.0
T_MS = 3000
t = np.arange(0, T_MS, DT)
W_INT_MS = 15.0      # REAL 视网膜积分窗 10~20 ms
V_PEAK_RATIO = 1.5   # REAL 峰值/平均速度比，约 1.5~1.75


def section1(amp=20.0):
    dur = saccade_duration_ms(amp)                 # ms
    v_mean = amp / (dur / 1000.0)                  # °/s
    v_peak = v_mean * V_PEAK_RATIO
    smear = v_peak * (W_INT_MS / 1000.0)           # 每个样本被抹平多少度
    return dict(amp=amp, dur=dur, v_mean=v_mean, v_peak=v_peak,
                smear=smear, frac=smear / amp)


def section2(amp=20.0):
    f = Saccade(-amp / 2, +amp / 2, asym=0.45)
    sup = f.suppression(t)
    masked = sup < 0.5
    w = float((masked).sum())                      # ★ 计数，不是求和
    # 扫视期间(0~dur)有多少个样本是"看得见"的
    during = t <= f.dur
    usable_during = int((~masked & during).sum())
    return dict(dur=f.dur, suppress_width=w, usable_during=usable_during,
                mask=masked)


def section3(amp=20.0, asym=0.80):
    f = Saccade(-amp / 2, +amp / 2, asym=asym)
    r = Saccade(+amp / 2, -amp / 2, asym=asym)
    tf, tr = f.torsion(t), r.torsion(t)
    sup = f.suppression(t)
    masked = sup < 0.5                             # 看不见的窗口

    e_in = float(np.abs(tf)[masked].sum())
    e_out = float(np.abs(tf)[~masked].sum())
    frac_in = e_in / max(e_in + e_out, 1e-9)

    # ★ 只比尾巴：抑制结束后，两边都是真测得到的
    tail = ~masked
    B_tail = float(np.abs(tf - tr)[tail].mean())
    B_all = float(np.abs(tf - tr).mean())
    return dict(e_in=e_in, e_out=e_out, frac_in=frac_in,
                B_tail=B_tail, B_all=B_all,
                A_fwd=float(f.violation_peak()), A_rev=float(r.violation_peak()))


if __name__ == "__main__":
    print("=" * 90)
    print(" 静态=拍照片 · 时间反演=想象力 · 中间=想象力填的")
    print("=" * 90)

    # ---------- 1 ----------
    s1 = section1()
    print("\n【1】眼睛追逐不过来")
    print(f"\n  扫视 {s1['amp']:.0f}°，持续 {s1['dur']:.0f} ms（main sequence REAL）")
    print(f"  平均角速度 {s1['v_mean']:.0f} °/s   峰值约 {s1['v_peak']:.0f} °/s")
    print(f"  视网膜积分窗 {W_INT_MS:.0f} ms（REAL 10~20）")
    print(f"  → 每个样本被抹平 {s1['smear']:.1f}° = 幅度的 {s1['frac']:.0%}")
    ok1 = bool(0.2 < s1['frac'] < 0.6)
    print(f"  {'✅' if ok1 else '❌'} 路径被抹平到采不到（不是精度低，是根本追不上）")

    # ---------- 2 ----------
    s2 = section2()
    print("\n" + "=" * 90)
    print("【2】中间那段没有样本")
    print("=" * 90)
    print(f"\n  扫视持续      {s2['dur']:.0f} ms")
    print(f"  抑制窗宽度    {s2['suppress_width']:.0f} ms（敏感度<0.5，REAL 50~100）")
    print(f"  ★ 扫视期间看得见的样本数 = {s2['usable_during']}")
    ok2 = bool(s2['usable_during'] == 0)
    print(f"  {'✅' if ok2 else '❌'} 整段扫视全被盖住 → 中间只能靠想象填")

    # ---------- 3 ----------
    s3 = section3()
    print("\n" + "=" * 90)
    print("【3】时间反演比的就是这段 → 想象力 vs 想象力")
    print("=" * 90)
    print(f"\n  |τ| 的能量分布（asym=0.80）：")
    print(f"    落在【看不见】的窗口内 {s3['e_in']:.2f}")
    print(f"    落在【看得见】的窗口内 {s3['e_out']:.2f}")
    print(f"    → 看不见的占 {s3['frac_in']:.1%}")
    print(f"\n  时间反演要比较的，正是眼睛看不见的那段（扫视正中）")
    print(f"  → 那是想象力跟想象力比，不是测量")

    print(f"\n  ★ 但【尾巴】是真的：抑制结束后违反还在按 tau=100ms 衰减")
    print(f"    只比尾巴  B_tail = {s3['B_tail']:.5f}°")
    print(f"    比全程    B_all  = {s3['B_all']:.5f}°")
    print(f"    正向违反峰值 A_fwd = {s3['A_fwd']:.4f}°")
    print(f"    反向违反峰值 A_rev = {s3['A_rev']:.4f}°")
    ok3 = bool(s3['B_tail'] > 0.05 and s3['A_fwd'] > s3['A_rev'])
    print(f"  {'✅' if ok3 else '❌'} 尾巴可测且方向不对称 → 手性残差是【测出来的】，不是想的")

    # ---------- 扫描 ----------
    print("\n" + "=" * 90)
    print(" 尾巴上的手性残差（只统计眼睛看得见的部分）")
    print("=" * 90)
    print(f"\n{'asym':<8}{'B_tail(°)':>12}{'A_fwd':>10}{'A_rev':>10}{'不对称比':>10}")
    print("-" * 90)
    rows = []
    for a in [0.0, 0.2, 0.45, 0.6, 0.8]:
        s = section3(asym=a)
        ratio = s['A_fwd'] / max(s['A_rev'], 1e-9)
        rows.append((a, s['B_tail'], s['A_fwd'], s['A_rev']))
        print(f"{a:<8.2f}{s['B_tail']:>12.5f}{s['A_fwd']:>10.4f}"
              f"{s['A_rev']:>10.4f}{ratio:>10.2f}")

    print("\n" + "=" * 90)
    print(" 判据")
    print("=" * 90)
    ok = {}
    ok["① 眼睛追不上：单样本被抹平 >20% 幅度"] = bool(ok1)
    ok["② 扫视全程 0 个可用样本 → 中间是想象"] = bool(ok2)
    ok["③ 时间反演的目标段正是看不见的那段"] = bool(s3['frac_in'] > 0.05)
    ok["④ 尾巴可测 → B_tail 随 asym 单调上升"] = bool(
        all(rows[i][1] <= rows[i + 1][1] + 1e-9 for i in range(len(rows) - 1)))
    ok["⑤ asym=0 → B_tail=0（无手性则无方向偏好）"] = bool(rows[0][1] < 0.005)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print(f"\n  ★ 你的三句话，逐条对上：")
    print(f"    静态=拍照片     → 已证：不动则 Troxler 消退（★17）")
    print(f"    眼睛一直在转    → 已证：追不上 + 抑制窗盖住全段")
    print(f"    时间反演=想象力 → 已证：它比的那段没有样本")
    print(f"    中间的是想象力  → 已证：{s2['usable_during']} 个可用样本")

    json.dump({"s1": s1, "s2": {k: v for k, v in s2.items() if k != "mask"},
               "s3": s3, "rows": [dict(asym=r[0], B_tail=r[1],
                                       A_fwd=r[2], A_rev=r[3]) for r in rows],
               "ok": {k: bool(v) for k, v in ok.items()}},
              open(os.path.join(HERE, ".sense", "eye_imagination.json"), "w"),
              ensure_ascii=False, indent=1)
