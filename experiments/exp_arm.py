#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手臂与肩膀 —— 把手【送到】空间里去
==========================================================
★ 手（★34）是末端执行器，但它自己到不了任何地方
★ 手臂负责【定位】，肩膀负责【朝向】

★ 硬判据（可证伪）
    ① 肩肱节律 2:1，合计 180°
    ② ★★ 肩胛冻结 → 外展只剩 120°
    ③ 屈伸与旋前旋后是【两根不同的轴】
    ④ ★ 腕的尺偏 > 桡偏（不对称 15°）
    ⑤ 腕中立位握力最大
    ⑥ ★★ 7 DOF 控制 6 DOF → 自运动存在（肘能摆，手不动）
    ⑦ ★★ 惯性各向异性，且在手臂接近伸直时【爆炸】
    ⑧ ★ 各向异性只随肘角变，不随肩角变（旋转不变性对照）
    ⑨ 双关节肌：肩姿势改变肘能发出的力
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.arm import (
    GH_COVERAGE, SHOULDER_DISLOCATION_SHARE,
    GH_ABDUCT_MAX, SCAPULA_UPROT_MAX, SHOULDER_COMPLEX,
    ELBOW_FLEX_RANGE, PRONATION_DEG, SUPINATION_DEG, CARRYING_ANGLE,
    WRIST_FLEX_DEG, WRIST_RADIAL_DEG, WRIST_ULNAR_DEG,
    RADIAL_STYLOID_LOWER_MM,
    DOF_ARM, TOTAL_ARM_DOF, BIARTICULAR,
    gh_stability, shoulder_complex, scapulohumeral, scapula_frozen,
    elbow_flexion, forearm_rotation, rotation_axis_check,
    carrying_angle, carrying_check,
    wrist_deviation, grip_vs_wrist, wrist_neutral_best,
    arm_dof, self_motion, redundancy_check, bernstein_problem,
    endpoint_mass_matrix, anisotropy, anisotropy_scan,
    biarticulate_coupling, biarticulate_check,
    chain_to_space, coordinate_error,
)

if __name__ == "__main__":
    print("="*88); print(" 手臂与肩膀：把手送到空间里去"); print("="*88)
    ok = {}

    # ---------- 1 ★ 肩 ----------
    print("\n【实验1】★ 肩：活动度最大，稳定性最差")
    print("-"*88)
    g = gh_stability()
    print(f"  关节盂只覆盖肱骨头 {g['coverage']:.0%}")
    print(f"  → 肩脱位占全部关节脱位 {g['dislocation_share']:.0%}（REAL）")
    print(f"  ★ 权衡：{g['tradeoff']}")
    print(f"\n  ★ 肩不是单一关节，是四个协同：{shoulder_complex()}")
    ok["① ★ 关节盂覆盖约 1/3（浅 → 能转最多，也最容易脱位）"] = bool(
        0.25 <= GH_COVERAGE <= 0.40)
    ok["② ★ 肩是四关节复合体，不是单一关节"] = bool(len(SHOULDER_COMPLEX) == 4)

    # ---------- 2 ★★ 肩肱节律 ----------
    print("\n【实验2】★★ 肩肱节律（REAL 2:1）")
    print("-"*88)
    sr = scapulohumeral()
    print(f"  外展 {sr['total_deg']:.0f}° = 盂肱 {sr['gh_deg']:.0f}° "
          f"+ 肩胛上旋 {sr['scapula_deg']:.0f}°   比例 {sr['ratio']:.0f}:1")
    print(f"  REAL：GH {GH_ABDUCT_MAX}° + 肩胛 {SCAPULA_UPROT_MAX}°")
    sf = scapula_frozen()
    print(f"\n  ★★ 肩胛骨冻结 → 只能抬到 {sf['max_frozen']:.0f}°，丢 "
          f"{sf['loss_deg']:.0f}°")
    print(f"  ★ 胸长神经损伤（翼状肩）就是这个后果")
    ok["③ ★★ 肩肱节律 2:1 且 GH=120°"] = bool(
        abs(sr["gh_deg"] - 120.0) < 1.0 and abs(sr["scapula_deg"] - 60.0) < 1.0)
    ok["④ ★★ 肩胛冻结 → 外展只剩 120°"] = bool(sf["max_frozen"] == GH_ABDUCT_MAX)
    ok["⑤ ★ GH 与肩胛之和 = 180°"] = bool(
        abs(GH_ABDUCT_MAX + SCAPULA_UPROT_MAX - 180.0) < 1e-6)

    # ---------- 3 ★ 肘 ----------
    print("\n【实验3】★ 肘：屈伸与旋转【分离】")
    print("-"*88)
    lo, hi = ELBOW_FLEX_RANGE
    print(f"  屈伸 {lo:.0f}~{hi:.0f}°   （真正的铰链）")
    print(f"  旋前 {PRONATION_DEG[1]:.0f}°   旋后 {SUPINATION_DEG[1]:.0f}°")
    ra = rotation_axis_check()
    print(f"\n  ★ 屈伸与旋前旋后同轴？{ra['same_axis']}")
    print(f"  ★ 旋前/旋后【不在肘】，是桡骨绕尺骨转 —— 另一根轴")
    print(f"  提携角：男 {carrying_angle('男')}  女 {carrying_angle('女')}")
    cc = carrying_check()
    print(f"  ★ 女性提携角更大（REAL）：{cc['female_larger']}")
    ok["⑥ ★ 屈伸与旋前旋后是两根不同的轴"] = bool(not ra["same_axis"])
    ok["⑦ ★ 肘屈伸范围 0~145°"] = bool(hi == 145.0)
    ok["⑧ ★ 女性提携角 > 男性"] = bool(cc["female_larger"])
    ok["⑨ ★ 旋前旋后各约 80~90°"] = bool(
        75 <= PRONATION_DEG[1] <= 95 and 75 <= SUPINATION_DEG[1] <= 95)

    # ---------- 4 ★ 腕不对称 ----------
    print("\n【实验4】★ 腕：尺偏 > 桡偏（不对称）")
    print("-"*88)
    w = wrist_deviation()
    print(f"  桡偏 {w['radial_deg']:.0f}°   尺偏 {w['ulnar_deg']:.0f}°   "
          f"不对称 {w['asymmetry_deg']:.0f}°")
    print(f"  ★ 原因：桡骨茎突比尺骨茎突低约 {w['cause_mm']} mm → 桡侧先撞上")
    wn = wrist_neutral_best()
    print(f"\n  ★ 握力：中立 {wn['neutral_N']:.0f} N / 屈30° {wn['flex30_N']:.0f} N "
          f"/ 伸30° {wn['ext30_N']:.0f} N")
    print(f"  ★ 中立位最大（REAL 屈伸30°掉 20~30%）：{wn['neutral_best']}")
    ok["⑩ ★★ 尺偏 > 桡偏，差约 15°"] = bool(w["asymmetry_deg"] == 15.0)
    ok["⑪ ★ 腕中立位握力最大"] = bool(wn["neutral_best"])
    ok["⑫ ★ 屈伸30° 握力掉 20~30%"] = bool(
        0.15 <= 1 - wn["flex30_N"] / wn["neutral_N"] <= 0.35)

    # ---------- 5 ★★ 七自由度自运动 ----------
    print("\n【实验5】★★ 七自由度：手不动，肘还能摆")
    print("-"*88)
    d = arm_dof()
    for k, v in d.items():
        if k != "_合计":
            print(f"    {k:<12}{v} DOF")
    print(f"    {'合计':<12}{d['_合计']} DOF")
    r = redundancy_check()
    print(f"\n  ★ {r['arm_dof']} DOF 控制 {r['task_dof']} DOF → 冗余 {r['redundancy']} 维")
    sm = self_motion(8)
    print(f"  ★★ 自运动（同一手位姿下的 8 个肘角）：")
    print(f"      {[round(x, 2) for x in sm]}")
    print(f"      极值差 {max(sm)-min(sm):.2f} —— 肘真的能摆")
    bp = bernstein_problem()
    print(f"\n  ★ Bernstein 问题：臂 {bp['arm_dof']} DOF + 手 {bp['hand_dof']} DOF "
          f"= {bp['total_dof']} DOF")
    print(f"    → 自由度远超任务需求，必须靠【协同】约束")
    ok["⑬ ★ 手臂 7 DOF（肩3+肘1+前臂旋1+腕2）"] = bool(TOTAL_ARM_DOF == 7)
    ok["⑭ ★★ 冗余 1 维 → 自运动存在"] = bool(r["redundancy"] == 1)
    ok["⑮ ★★ 手位姿不变时肘角可取多个不同值"] = bool(max(sm) - min(sm) > 1.0)
    ok["⑯ ★ DOF 分解自洽"] = bool(d["_合计"] == TOTAL_ARM_DOF)

    # ---------- 6 ★★ 惯性各向异性 ----------
    print("\n【实验6】★★ 惯性各向异性（端点质量矩阵）")
    print("-"*88)
    print(f"  {'肩角':>6}{'肘角':>8}{'各向异性比':>14}")
    rows = anisotropy_scan()
    for sh, el, ra_ in rows:
        mark = "  ← 接近伸直，接近奇异" if el == 20.0 else ""
        print(f"  {sh:>6.0f}{el:>8.0f}{ra_:>14.2f}{mark}")
    a20 = anisotropy(0, 20)["ratio"]
    a90 = anisotropy(0, 90)["ratio"]
    a135 = anisotropy(0, 135)["ratio"]
    print(f"\n  ★★ 肘 20°（近伸直）各向异性 {a20:.1f} → 肘 135°（弯曲）{a135:.2f}")
    print(f"  ★ 手臂越伸直，越接近【奇异位形】—— 沿臂方向动不了")
    ok["⑰ ★★ 各向异性比 > 1.5（不是各向同性）"] = bool(a90 > 1.5)
    ok["⑱ ★★ 越伸直各向异性越大（接近奇异）"] = bool(a20 > a90 > a135)

    # ★★ 旋转不变性对照
    same_shoulder = [r_ for sh, el, r_ in rows if el == 90.0]
    rot_invariant = max(same_shoulder) - min(same_shoulder) < 1e-6
    print(f"\n  ★★ 旋转不变性对照：肘角固定 90° 时，三个不同肩角")
    print(f"      的各向异性比 = {[round(x,4) for x in same_shoulder]}")
    print(f"      完全相同：{rot_invariant}")
    print(f"  ★ 这是【正确】的：整体旋转不改变质量矩阵特征值")
    print(f"    ⚠️ 第一版我以为这是 bug，其实不是 —— 这是旋转不变性")
    ok["⑲ ★★ 各向异性只随肘角变，不随肩角变（旋转不变，非 bug）"] = bool(
        rot_invariant)

    # ---------- 7 ★ 双关节肌 ----------
    print("\n【实验7】★ 双关节肌：一个肌肉管两个关节")
    print("-"*88)
    print(f"  {'肌肉':<14}{'跨关节':<16}{'肩0°时肘力矩':>14}{'肩90°时':>10}")
    for m in ["肱二头肌", "肱三头肌长头"]:
        a = biarticulate_coupling(m, 0.0, 90.0)
        b = biarticulate_coupling(m, 90.0, 90.0)
        print(f"  {m:<14}{str(BIARTICULAR[m]):<16}"
              f"{a['elbow_torque_factor']:>14.2f}{b['elbow_torque_factor']:>10.2f}")
    bc = biarticulate_check()
    print(f"\n  ★ 肩的角度变了 → 肘能发出的力真的变了：{bc['differs']}")
    print(f"  ★ 因为肌肉跨两个关节，一端位置变了，肌纤维长度就变了")
    ok["⑳ ★ 双关节肌：肩姿势影响肘力矩"] = bool(bc["differs"])

    # ---------- 8 ★ 坐标链 ----------
    print("\n【实验8】★ 手在空间里 = 一串坐标系串联")
    print("-"*88)
    c = chain_to_space()
    print(f"  {' → '.join(c['chain'])}")
    print(f"\n  位置觉：{c['position_sense']}")
    print(f"  头朝向：{c['head_orientation']}")
    print(f"  眼：{c['eye']}")
    print(f"  ★ {c['note']}")
    err = coordinate_error(1.0, 7, 0.6)
    print(f"\n  ★ 每节 1° 误差（随机累积）→ 手端偏 {err:.1f} mm")
    print(f"  ★ 这就是为什么【闭环视觉】必须存在 —— 开链误差累积太大")
    ok["21 ★ 坐标链 7~8 节串联"] = bool(len(c["chain"]) >= 7)
    ok["22 ★ 每节1°误差 → 手端误差 > 10mm（开链不可靠）"] = bool(err > 10.0)

    print("\n"+"="*88); print(" 判据汇总"); print("="*88)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：肩袖四肌的协同稳定（动态稳定器）")
    print("  ❌ 未建模：肌腱/韧带的粘弹性")
    print("  ❌ 未建模：三维肩胛运动（只做了 2D 平面两连杆）")
    print("  ⚠️ 各向异性用的是简化平面两连杆，非真实三维手臂")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "arm.json"), "w"),
              ensure_ascii=False, indent=1)
