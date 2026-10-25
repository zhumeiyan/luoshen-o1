#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前庭 —— 测量【自己】的运动（惯性导航）
========================================
★ 唯一一个测量自身运动状态的感官

★ 核心：
  ① 半规管是【带通】的角速度计，不是加速度计
  ② ★ 转椅悖论：匀速转久了以为不转，停下反而更晕
  ③ ★ 耳石无法区分重力与加速度（自由落体 = 太空静止）
  ④ VOR 潜伏期 10ms << 视觉 80ms —— 头动靠它稳像
  ⑤ ★ 积分漂移：闭眼走直线会走偏
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.vestibular import (
    TAU_CUPULA, CANAL_BAND_HZ, G, OTOLITH_THRESHOLD,
    VOR_GAIN, VOR_LATENCY_MS, OKN_LATENCY_MS,
    cupula_response, cupula_gain, rotation_chair, post_rotation_decay,
    otolith_output, otolith_scenarios, tilt_from_otolith,
    somatogravic_illusion, vor_eye_velocity, retinal_slip,
    vor_compensation_ratio, image_stabilization, imu_drift,
    path_integration_error,
)

if __name__ == "__main__":
    print("="*88); print(" 前庭：惯性导航，测的是【自己】的运动"); print("="*88)
    ok = {}

    # ---------- 1 带通 ----------
    print("\n【实验1】★ 半规管是【带通】的角速度计（不是加速度计）")
    print("-"*88)
    print(f"  {'频率(Hz)':>10}{'增益':>10}")
    g = {}
    for f in [0.001, 0.01, 0.05, 0.1, 1, 5, 10, 50, 200]:
        g[f] = float(cupula_gain(np.array([f]))[0])
        print(f"  {f:>10}{g[f]:>10.4f}")
    ok["① ★ 极低频(0.001Hz)增益 < 0.1（不是加速度计）"] = bool(g[0.001] < 0.1)
    ok["② 中频(0.1~10Hz)增益 > 0.9（对角速度线性）"] = bool(
        g[0.1] > 0.9 and g[1] > 0.9 and g[10] > 0.9)
    ok["③ 高频(200Hz)增益衰减（内淋巴惯性）"] = bool(g[200] < 0.5)
    print(f"\n  ★ 若是加速度计，低频增益应趋于常数；实际 0.001Hz 只有 {g[0.001]:.4f}")
    print(f"  ★ 带通 {CANAL_BAND_HZ[0]}~{CANAL_BAND_HZ[1]} Hz（REAL）")

    # ---------- 2 ★★ 转椅悖论 ----------
    print("\n【实验2】★★ 转椅悖论：停下反而更晕")
    print("-"*88)
    t = np.arange(0, 60, 0.01)
    r = rotation_chair(t, 90.0, 30.0)
    print(f"  {'时刻':<12}{'信号(°/s)':>12}{'预期理论':>12}")
    pts = [("转 0.5s", 50), ("转 3s", 300), ("转 10s", 1000),
           ("转 20s", 2000), ("转 29s", 2900)]
    for lbl, i in pts:
        exp = 90 * np.exp(-i * 0.01 / TAU_CUPULA)
        print(f"  {lbl:<12}{r[i]:>12.3f}{exp:>12.3f}")
    print("  " + "-"*36)
    i0 = 3000
    for lbl, k in [("停后 0.5s", 50), ("停后 3s", 300),
                   ("停后 6s", 600), ("停后 20s", 2000)]:
        exp = -90 * np.exp(-k * 0.01 / TAU_CUPULA)
        print(f"  {lbl:<12}{r[i0+k]:>12.3f}{exp:>12.3f}")
    ok["④ ★ 匀速转 29s 后信号衰减到 <5°/s（以为不转了）"] = bool(abs(r[2900]) < 5.0)
    ok["⑤ ★ 停止后信号【反向】且幅度大（|信号|>40°/s）"] = bool(r[i0+50] < -40)
    ok["⑥ 停止后衰减符合 exp(-t/τc)，τc≈6s"] = bool(
        abs(abs(r[i0+600]) / abs(r[i0+50]) - np.exp(-5.5 / TAU_CUPULA)) < 0.1)
    ok["⑦ ★ 停止后【更晕】：停后幅度 > 停止前幅度"] = bool(
        abs(r[i0+50]) > abs(r[2900]))
    print(f"\n  ★ 停止前(29s) {r[2900]:.3f}°/s  →  停止后(0.5s) {r[i0+50]:.1f}°/s")
    print(f"  ★ 差 {abs(r[i0+50])/max(abs(r[2900]),1e-9):.0f} 倍 —— 这就是'停下反而更晕'")
    print(f"  ★ τc = {TAU_CUPULA}s（REAL 5~7s），主观晕感持续约 10~30s")

    # ---------- 3 ★★ 重力不可分辨 ----------
    print("\n【实验3】★★ 耳石无法区分重力与加速度")
    print("-"*88)
    sc = otolith_scenarios()
    print(f"  {'场景':<14}{'输出模长(m/s²)':>16}")
    for k, v in sc.items():
        print(f"  {k:<14}{np.linalg.norm(v):>16.3f}")
    free = np.linalg.norm(sc["自由落体"])
    space = np.linalg.norm(sc["太空静止"])
    ground = np.linalg.norm(sc["地面静止"])
    ok["⑧ ★★ 自由落体与太空静止【输出完全相同】"] = bool(abs(free - space) < 1e-9)
    ok["⑨ 地面静止输出 = 1g（测到重力）"] = bool(abs(ground - G) < 0.01)
    ok["⑩ ★ 1g 向上加速 ≠ 静止（可区分加速度与静止）"] = bool(
        abs(np.linalg.norm(sc["1g向上加速"]) - ground) > 1.0)
    print(f"\n  ★ 自由落体 {free:.3f} = 太空静止 {space:.3f} —— 耳石【分不出】")
    print(f"  ★ 这是爱因斯坦升降机等价原理的生物学版本")
    print(f"  ★ 数学表达：耳石输出 = 真实加速度 − 重力 → 落体时两项抵消")
    ill = somatogravic_illusion(0.5 * G)
    ok["⑪ 体感重力错觉：0.5g 前加速 → 感知上仰约 26.6°"] = bool(
        abs(ill - 26.57) < 1.0)
    print(f"\n  ★ 飞行员错觉：向前加速 0.5g → 感知机头上仰 {ill:.1f}°")
    print("  ★ 真实事故：夜间起飞加速，飞行员误判姿态 → 可控飞行撞地")

    # ---------- 4 VOR ----------
    print("\n【实验4】VOR 稳像：潜伏期 10ms << 视觉 80ms")
    print("-"*88)
    print(f"  {'头速(°/s)':>10}{'眼速(°/s)':>12}{'有VOR滑动':>12}{'无VOR滑动':>12}")
    for v in [50, 150, 300]:
        print(f"  {v:>10}{vor_eye_velocity(v):>12.1f}"
              f"{image_stabilization(v, True):>12.1f}{image_stabilization(v, False):>12.1f}")
    ok["⑫ VOR 增益 0.9~1.0（REAL）"] = bool(0.9 <= VOR_GAIN <= 1.0)
    ok["⑬ ★ 有 VOR 时视网膜滑动 < 无 VOR 的 10%"] = bool(
        image_stabilization(150, True) < 0.1 * image_stabilization(150, False))
    ok["⑭ ★ 前庭 VOR(10ms) 比视觉 VOR(80ms) 快 5 倍以上"] = bool(
        OKN_LATENCY_MS / VOR_LATENCY_MS > 5)
    print(f"\n  ★ 头速 150°/s：无 VOR 滑动 150°/s（全糊）→ 有 VOR 只剩 "
          f"{image_stabilization(150,True):.1f}°/s")
    print(f"  ★ 前庭 {VOR_LATENCY_MS}ms vs 视觉 {OKN_LATENCY_MS}ms —— 头动时视觉来不及")
    print("  ★ 这也解释了 ★25/★28：头不动时立体/运动视差消失，但 VOR 还在工作")

    # ---------- 5 ★ 积分漂移 ----------
    print("\n【实验5】★ 积分漂移：闭眼走直线会走偏")
    print("-"*88)
    print(f"  {'偏置(m/s²)':>12}{'60秒后位置误差(m)':>20}")
    for b in [0.001, 0.005, 0.01, 0.05]:
        print(f"  {b:>12}{path_integration_error(b, 60):>20.1f}")
    ok["⑮ ★ 误差随时间【二次】增长（不是线性）"] = bool(
        abs(path_integration_error(0.01, 120) /
            path_integration_error(0.01, 60) - 4.0) < 0.01)
    ok["⑯ 极小偏置(0.01 m/s²) 60 秒后也偏 >10 m"] = bool(
        path_integration_error(0.01, 60) > 10)
    print(f"\n  ★ 0.01 m/s² 的微小偏置（远低于 {OTOLITH_THRESHOLD} 阈值，感觉不到）")
    print(f"  ★ 60 秒后就偏 {path_integration_error(0.01,60):.0f} m")
    print("  ★ 这就是 IMU 必须靠外部锚点（GPS/视觉/地磁）修正的根本原因")
    print("  ★ 生物对应现象：闭眼原地踏步会走偏，蒙眼走直线会绕圈")

    print("\n"+"="*88); print(" 判据汇总"); print("="*88)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：三管非正交(实际约 90°±10)、推拉不对称(Ewald第二定律)")
    print("  ❌ 未建模：前庭-眼-颈多感觉整合的贝叶斯加权")
    print("  ⚠️ 耳石输出用向量差近似，未建模耳石膜粘弹性动力学")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "vestibular.json"), "w"),
              ensure_ascii=False, indent=1)
