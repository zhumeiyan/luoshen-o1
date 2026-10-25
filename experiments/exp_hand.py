#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手 —— 唯一既是【感受器】又是【输出器】的器官
==========================================================
★ 与前面所有感官根本不同：
    眼耳鼻舌皮肤：把世界【写进】身体
    手：把身体【写到】世界上
  ★ 手是闭环的另一半 —— 没有手，感知到的世界无法被改变

★ 本实验的硬判据（可证伪）：
    ① DOF 分解自洽（各项之和 == 27）
    ② 去拇指后功能掉到 50~60%（REAL 拇指占 40~50%）
    ③ 弓弦效应：滑车失效 → 效率真的掉
    ④ 环指独立性必须【最低】
    ⑤ ★★ 尺神经瘫 → 爪形指数真的变高
    ⑥ 冗余：同一物体姿态能做出【多种不同】手势
    ⑦ 震颤幅度 vs 目标尺寸
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.hand import (
    CARPALS, METACARPALS, PHALANGES, TOTAL_BONES,
    DOF, TOTAL_DOF, THUMB_FUNCTION_SHARE, INDEPENDENCE,
    MOMENT_ARM_MM, PULLEYS, CRITICAL_PULLEYS, CARPAL_TUNNEL,
    TREMOR_HZ, TREMOR_MM, PINCH_FORCE_N, GRIP_FORCE_N,
    TWO_POINT_MM,
    dof_breakdown, kinematic_redundancy, same_pose_many_hands,
    opposition_angle, thumb_ablated_function, thumb_share_check,
    tendon_excursion, bowstring_penalty, serial_coupling,
    independence, coupling_matrix, spread_independence,
    extensor_mechanism, claw_index, ulnar_nerve_palsy,
    median_nerve_palsy,
    grip_choice, grip_capacity, grip_scan,
    fitts_mt, tremor, tremor_vs_target,
    cortical_magnification, active_vs_passive_touch,
)

if __name__ == "__main__":
    print("="*88); print(" 手：把身体写到世界上的那一半"); print("="*88)
    ok = {}

    # ---------- 1 骨与自由度 ----------
    print("\n【实验1】骨与自由度（分解必须自洽）")
    print("-"*88)
    print(f"  腕骨 {CARPALS} + 掌骨 {METACARPALS} + 指骨 {PHALANGES} = {TOTAL_BONES}")
    d = dof_breakdown()
    for k, v in d.items():
        if k != "_合计":
            print(f"    {k:<12}{v:>3} DOF")
    print(f"    {'合计':<12}{d['_合计']:>3} DOF")
    ok["① ★ 骨数 = 27（腕8+掌5+指14）"] = bool(TOTAL_BONES == 27)
    ok["② ★★ DOF 分解自洽：各项之和 == 声明值"] = bool(
        d["_合计"] == TOTAL_DOF == 27)
    print(f"\n  ★ 文献引用 22~27 不等，取决于是否计入腕/掌弓/小指掌腕")
    print(f"  ★ 本实现的 27 是自洽的（★ 第一版算成 25，与声明不符，已修）")

    # ---------- 2 ★★ 冗余 ----------
    print("\n【实验2】★★ 运动冗余：27 DOF 控制 6 DOF")
    print("-"*88)
    r = kinematic_redundancy()
    print(f"  手 {r['total_dof']} DOF   刚体只需 {r['object_dof']} DOF   "
          f"→ 零空间 {r['nullspace_dim']} 维")
    hands = same_pose_many_hands(5)
    diffs = [float(np.abs(hands[0] - x).max()) for x in hands[1:]]
    print(f"  ★ 同一物体姿态做出的 5 种手势，与第1种的最大差：")
    for i, dd in enumerate(diffs, 1):
        print(f"      手势{i+1}: {dd:.3f}")
    ok["③ ★ 零空间维 = 27−6 = 21"] = bool(r["nullspace_dim"] == 21)
    ok["④ ★★ 同一姿态能做出【多种不同】手势（冗余真实存在）"] = bool(
        min(diffs) > 0.05)
    print("\n  ★★ 这正是手能『抓着杯子同时翘小指』的原因 —— 那 21 维是自由的")

    # ---------- 3 ★★ 拇指 ----------
    print("\n【实验3】★★ 拇指占手部功能约 40%")
    print("-"*88)
    t = thumb_share_check()
    print(f"  拇指功能占比 {t['share']:.0%}   去拇指后剩余 {t['remaining']:.0%}")
    print(f"  REAL 临床区间 40~50%：{'✅' if t['in_real_range'] else '❌'}")
    opp_n = opposition_angle(0.9, 0.9)
    opp_p = opposition_angle(0.9, 0.2)
    print(f"  ★ 对掌需要【屈曲+外展】联合：正常 {opp_n:.2f}")
    print(f"    正中神经瘫（拇短展瘫）→ {opp_p:.2f}  丢 {opp_n-opp_p:.2f}")
    ok["⑤ ★ 拇指占比落在 REAL 区间 40~50%"] = bool(t["in_real_range"])
    ok["⑥ ★ 去拇指后剩余 50~60%"] = bool(0.5 <= t["remaining"] <= 0.6)
    ok["⑦ ★ 对掌需要屈曲+外展两项，缺一项就不完全"] = bool(
        opp_p < opp_n * 0.5)
    print(f"\n  ★ CMC 是【鞍状关节】—— 两个互相垂直的凹面，这是能对掌的解剖基础")

    # ---------- 4 ★ 肌腱串激与弓弦 ----------
    print("\n【实验4】★ 肌腱是【串激】的：一条腱驱动三个关节")
    print("-"*88)
    print(f"  力矩臂(mm)：MCP {MOMENT_ARM_MM['MCP']}  PIP {MOMENT_ARM_MM['PIP']}"
          f"  DIP {MOMENT_ARM_MM['DIP']}")
    b = bowstring_penalty()
    print(f"  正常腱位移 {b['normal_mm']:.1f} mm")
    print(f"  滑车失效（弓弦）→ {b['bowstring_mm']:.1f} mm，效率损失 "
          f"{b['efficiency_loss']:.0%}")
    sc = serial_coupling()
    print(f"  ★ 只屈 DIP 需 {sc['only_dip_mm']:.1f} mm，自然屈曲需 {sc['natural_mm']:.1f} mm")
    ok["⑧ ★ 弓弦效应：滑车失效后需要更多腱位移"] = bool(b["ratio"] > 1.2)
    ok["⑨ ★ 肌腱串激：不能只屈一个关节"] = bool(not sc["independent"])
    print(f"\n  ★ 关键滑车 {CRITICAL_PULLEYS}（A2/A4 防止腱离开骨面）")
    print(f"  ★ 腕管：{CARPAL_TUNNEL['屈肌腱']} 条腱 + {CARPAL_TUNNEL['神经']} 条正中神经挤在一起")
    print(f"     → 这就是腕管综合征的解剖来源")

    # ---------- 5 ★★ 手指不能真正独立 ----------
    print("\n【实验5】★★ 手指不能真正独立（EDC 腱间连接）")
    print("-"*88)
    print(f"  {'手指':<8}{'伸展独立性':>12}")
    for f in ["食指", "中指", "环指", "小指"]:
        print(f"  {f:<8}{independence(f):>12.0%}")
    sp = spread_independence()
    print(f"\n  ★ 最好 {sp['best']}（{independence(sp['best']):.0%}）  "
          f"最差 {sp['worst']}（{independence(sp['worst']):.0%}）")
    print(f"  ★ 环指最差 —— 因为它【两侧】都有腱间连接")
    ok["⑩ ★★ 环指独立性必须是四指里最低（REAL）"] = bool(sp["worst"] == "环指")
    ok["⑪ ★ 食指独立性最高"] = bool(sp["best"] == "食指")
    ok["⑫ ★ 独立性排序：食指 > 中指 > 小指 > 环指"] = bool(
        INDEPENDENCE["食指"] > INDEPENDENCE["中指"]
        > INDEPENDENCE["小指"] > INDEPENDENCE["环指"])

    # ---------- 6 ★★★ 爪形手 ----------
    print("\n【实验6】★★★ 内在肌耦合 → 爪形手（尺神经损伤）")
    print("-"*88)
    print(f"  {'内在肌':>8}{'MCP伸':>10}{'IP伸':>10}{'MCP净':>10}{'爪形指数':>12}")
    for iv in [1.0, 0.6, 0.3, 0.0]:
        m = extensor_mechanism(iv)
        print(f"  {iv:>8.1f}{m['mcp_extension']:>10.2f}{m['ip_extension']:>10.2f}"
              f"{m['mcp_net']:>10.2f}{claw_index(iv):>12.3f}")
    u = ulnar_nerve_palsy()
    print(f"\n  ★ 正常 爪形 {u['normal_claw']:.3f} → 尺神经瘫 {u['palsy_claw']:.3f}"
          f"  恶化 {u['worse']}  Δ={u['delta']:.3f}")
    mn = median_nerve_palsy()
    print(f"  ★ 正中神经瘫：对掌 {mn['opposition_normal']:.2f} → "
          f"{mn['opposition_palsy']:.2f}  丢 {mn['lost']:.2f}")
    ok["⑬ ★★ EDC 不能直接伸 IP（ip_extension 只随内在肌变）"] = bool(
        extensor_mechanism(0.0)["ip_extension"] == 0.0
        and extensor_mechanism(0.0)["mcp_extension"] > 0)
    ok["⑭ ★★ 尺神经瘫 → 爪形指数真的变高"] = bool(u["worse"])
    ok["⑮ ★ 正常手爪形指数 ≈ 0"] = bool(u["normal_claw"] < 0.05)
    ok["⑯ ★ 正中神经瘫 → 对掌能力真的下降"] = bool(mn["lost"] > 0.3)
    print(f"\n  ★★ 机制：EDC 只伸 MCP，伸 IP 必须靠内在肌经【腱帽侧束】")
    print(f"     蚓状肌起点在指深屈肌腱、止点在伸肌腱帽")
    print(f"     → 它【同时】屈 MCP 和伸 IP，这两个是耦合的，不能只做一个")
    print(f"  ★★ 尺神经瘫 → 内在肌全瘫 → MCP 过伸 + IP 屈 = 爪形手")

    # ---------- 7 抓握选择 ----------
    print("\n【实验7】抓握选择（Napier：由尺寸与力共同决定）")
    print("-"*88)
    print(f"  {'尺寸(mm)':>10}{'力(N)':>8}{'抓握':>12}{'容量(N)':>16}")
    for s, f, g in grip_scan():
        lo, hi = grip_capacity(g)
        print(f"  {s:>10}{f:>8}{g:>12}{f'{lo}~{hi}':>16}")
    ok["⑰ ★ 小尺寸小力 → 精细捏取"] = bool(grip_choice(20, 50) == "精细捏取")
    ok["⑱ ★ 大尺寸大力 → 力性抓握"] = bool(grip_choice(120, 350) == "力性抓握")
    ok["⑲ ★ 力性抓握容量 > 精细捏取"] = bool(
        grip_capacity("力性抓握")[1] > grip_capacity("精细捏取")[1] * 3)
    print(f"\n  ★ 捏力 {PINCH_FORCE_N[0]:.0f}~{PINCH_FORCE_N[1]:.0f} N  "
          f"vs 握力 {GRIP_FORCE_N[0]:.0f}~{GRIP_FORCE_N[1]:.0f} N —— 约 5 倍")

    # ---------- 8 震颤与 Fitts ----------
    print("\n【实验8】震颤与速度精度权衡")
    print("-"*88)
    tv = tremor_vs_target(1.0)
    print(f"  生理性震颤 {TREMOR_HZ[0]:.0f}~{TREMOR_HZ[1]:.0f} Hz，幅度 {TREMOR_MM} mm")
    print(f"  目标 1.0mm 时信噪比 {tv['snr']:.0f}")
    for w in [20, 10, 5, 2, 1]:
        print(f"  Fitts D=100 W={w:>2} → {fitts_mt(100, w):.3f} s")
    ok["⑳ ★ 目标越小（W↓）耗时越长（Fitts）"] = bool(
        fitts_mt(100, 1) > fitts_mt(100, 20))
    ok["21 ★ 震颤幅度 < 精细捏取目标尺寸"] = bool(TREMOR_MM < 1.0)
    print(f"\n  ★ 震颤 0.1mm 是【精度地板】—— 比这更细的操作必须靠工具")

    # ---------- 9 手的感受侧 ----------
    print("\n【实验9】★ 手的感受侧（接 ★27 皮肤）")
    print("-"*88)
    print(f"  {'部位':<8}{'两点辨别(mm)':>14}{'皮质放大':>10}")
    for s in TWO_POINT_MM:
        print(f"  {s:<8}{TWO_POINT_MM[s]:>14}{cortical_magnification(s):>10.1f}×")
    av = active_vs_passive_touch()
    print(f"\n  ★ 主动触觉 {av['active_mm']} mm vs 被动 {av['passive_mm']} mm")
    ok["22 ★ 指尖两点辨别最小（2mm）"] = bool(
        min(TWO_POINT_MM, key=TWO_POINT_MM.get) == "指尖")
    ok["23 ★ 指尖皮质放大倍数最大"] = bool(
        cortical_magnification("指尖") > cortical_magnification("背部") * 10)
    ok["24 ★ 主动触觉优于被动（接 ★27/★30）"] = bool(av["active_better"])
    print(f"\n  ★★ 手既是感受器又是输出器 —— 皮质放大最大的部位，同时也是执行器")
    print(f"  ★ 这不是巧合：需要精细感觉的地方，正是需要精细动作的地方")

    print("\n"+"="*88); print(" 判据汇总"); print("="*88)
    for k, v in ok.items():
        print(f"  {'✅' if v else '❌'} {k}")
    print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
    print("\n  ❌ 未建模：掌弓的动态适应（抓不同形状时掌弓会变）")
    print("  ❌ 未建模：肌腱的粘弹性与滞后")
    print("  ❌ 未建模：手指接触力学（摩擦锥、软垫变形）")
    print("  ⚠️ DOF 27 是众多分解之一，文献 22~27 不等")
    json.dump({k: bool(v) for k, v in ok.items()},
              open(os.path.join(HERE, ".sense", "hand.json"), "w"),
              ensure_ascii=False, indent=1)
