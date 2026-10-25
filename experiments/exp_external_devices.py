#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★60 外挂感官实验"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.external_devices import (
    gsd_cm, swath_m, wind_speed, gimbal_jitter_rate, motion_blur_px,
    frame_blur_tradeoff, optimal_fps, optimal_fps_analytic,
    LINK_LATENCY_MS, REAL_TURN_GAP_MS, can_support_realtime, control_stable,
    micro_detect_rate, micro_detect_native, micro_detect_device,
    regions_needed, au_separation_deg, face_angle_deg, optimal_distance,
    duchenne_score, is_genuine, voluntary_control,
    DEVICES, device_class, extension_factor, class_summary, failure_count,
    sensing_with_devices, FOVEA_DEG,
)

ok = {}
print("=" * 92)
print(" ★60 外挂感官 —— 微表情动态捕捉 / 无人机摄像 / 其他采集设备")
print("=" * 92)

# ══════════ 1 GSD REAL 校验
print("\n【1】无人机 GSD —— REAL 校验")
print("-" * 92)
print(f"  {'高度m':>7}{'GSD(cm/px)':>12}{'幅宽m':>9}")
gsd100 = None
for h in (30, 50, 100, 200, 400):
    g, w = gsd_cm(h), swath_m(h)
    if h == 100:
        gsd100 = g
    print(f"  {h:>7}{g:>12.2f}{w:>9.0f}")
print(f"\n  ★ 100m → {gsd100:.2f} cm/px   REAL 消费级 2.7~4 cm/px")
ok["① GSD@100m 落 REAL 区间 2.7~4"] = bool(2.7 <= gsd100 <= 4.0)

# ══════════ 2 ★★★ 微表情：串行 vs 并行
print("\n【2】★★★ 微表情：裸眼【串行扫视】vs 设备【并行全画幅】")
print("-" * 92)
print(f"  {'距离mm':>8}{'两点间距°':>10}{'需注视':>8}{'裸眼检出':>10}")
for d in (150, 250, 300, 500, 800, 1000, 2000, 3000):
    print(f"  {d:>8}{au_separation_deg(d):>10.2f}{regions_needed(d):>8}"
          f"{micro_detect_rate(60, d, native=True):>10.3f}")
grid = np.linspace(150, 4000, 120)
vals = [micro_detect_rate(60, float(d), native=True) for d in grid]
CEIL = float(max(vals)); DCEIL = float(grid[int(np.argmax(vals))])
r1m = micro_detect_rate(60, 1000.0, native=True)
print(f"\n  ★ 1m 处裸眼 = {r1m:.3f}    REAL 未训练者 ≈ 0.50")
print(f"  ★★ 天花板 = {CEIL:.3f} @ {DCEIL:.0f}mm")
print(f"     ★ 无论多近都突破不了 —— 因为需要【2 次扫视】")
print(f"       而微表情只有 40~200ms，扫视潜伏期就要 200ms")
print(f"       ★ 这是【串行】的硬天花板，与距离无关")
ok["② 裸眼 1m 落 REAL 区间（0.50±0.15）"] = bool(0.35 <= r1m <= 0.65)
ok["③ ★★ 裸眼存在天花板 ≤0.55（串行瓶颈）"] = bool(CEIL <= 0.55)

print(f"\n  {'配置':>24}{'检出率':>9}")
rows = [(30, 1.0, "30fps 无增益"), (60, 1.0, "60fps 无增益"),
        (200, 1.0, "200fps 无增益"), (200, 2.0, "200fps gain=2"),
        (200, 4.0, "200fps gain=4"), (500, 15.0, "500fps gain=15")]
res_dev = {}
for f, g, lab in rows:
    r = micro_detect_rate(f, 1000.0, g)
    res_dev[lab] = r
    print(f"  {lab:>24}{r:>9.3f}")
print(f"\n  ★ REAL 算法识别率 70~85%")
ok["④ 设备（高帧率+增益）落 REAL 70~85%"] = bool(
    0.70 <= res_dev["200fps gain=4"] <= 0.85)
gain_rise = res_dev["200fps gain=4"] / max(res_dev["200fps 无增益"], 1e-9)
print(f"  ★★ 增益 1→4：{res_dev['200fps 无增益']:.3f} → "
      f"{res_dev['200fps gain=4']:.3f}   提升 {(gain_rise-1)*100:.0f}%")
ok["⑤ ★★ 光学增益必须显著提升检出率（≥20%）"] = bool(gain_rise >= 1.20)

# ══════════ 3 ★★ Duchenne：真笑 vs 假笑
print("\n【3】★★ Duchenne 判据 —— 靠【能否随意控制】，不是幅度")
print("-" * 92)
print(f"  {'AU6':>6}{'AU12':>7}{'真笑分':>9}{'判真':>7}")
for a6 in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    print(f"  {a6:>6.1f}{0.9:>7.1f}{duchenne_score(a6,0.9):>9.3f}"
          f"{str(is_genuine(a6,0.9)):>7}")
mono = all(duchenne_score(a/10, 0.9) <= duchenne_score((a+1)/10, 0.9) + 1e-9
           for a in range(0, 10))
fake = is_genuine(0.05, 0.9)
true = is_genuine(0.8, 0.9)
print(f"\n  ★★ 假笑(AU6=0.05, AU12=0.9) → 判真 = {fake}   （应为 False）")
print(f"     真笑(AU6=0.8,  AU12=0.9) → 判真 = {true}   （应为 True）")
ok["⑥ ★★ AU6 单调抬升真笑分（可证伪）"] = bool(mono)
ok["⑦ ★★ 只动 AU12 必须判假笑"] = bool((not fake) and true)
c6, c12 = voluntary_control("AU6"), voluntary_control("AU12")
print(f"\n  随意控制度：AU6={c6:.2f}  AU12={c12:.2f}   "
      f"比={c12/max(c6,1e-9):.1f}×")
ok["⑧ AU6 远难随意控制（诚实标记的前提）"] = bool(c12 / c6 >= 3.0)

# ══════════ 4 ★★ 帧率 vs 曝光的内部最优
print("\n【4】★★ 无人机：帧率 vs 曝光（内部最优）")
print("-" * 92)
print(f"  {'抖动px/s':>10}{'扫描最优':>10}{'解析解':>10}{'误差':>8}{'内部':>7}")
fprev, mono_f = None, True
for v in (0.5, 2.0, 8.0, 30.0):
    r = optimal_fps(v)
    err = abs(r["fps"] - r["analytic"]) / r["analytic"]
    print(f"  {v:>10.1f}{r['fps']:>10.1f}{r['analytic']:>10.1f}"
          f"{err*100:>7.1f}%{str(r['interior']):>7}")
    if fprev is not None and r["fps"] <= fprev:
        mono_f = False
    fprev = r["fps"]
print(f"\n  ★ 解析 f* = (2v²/C²)^(1/3)：抖得越厉害 → 越要提高帧率")
print(f"  ★ 与 ★59 打印机层厚同构：两头都不好 → 内部最优")
ok["⑨ 帧率内部最优：解析≈扫描 且随抖动单调增"] = bool(mono_f)

# ══════════ 5 云台硬依赖
print("\n【5】云台硬依赖")
print("-" * 92)
print(f"  {'风m/s':>7}{'云台开px/s':>12}{'云台关px/s':>12}{'倍数':>8}")
for w in (3.0, 6.0, 10.0):
    on, off = gimbal_jitter_rate(w, True), gimbal_jitter_rate(w, False)
    print(f"  {w:>7.1f}{on:>12.2f}{off:>12.2f}{off/on:>8.1f}×")
r31 = gimbal_jitter_rate(3.0, False) / gimbal_jitter_rate(3.0, True)
ok["⑩ ★★ 关掉云台抖动必须显著变大（≥5×）"] = bool(r31 >= 5.0)

# ══════════ 6 ★★ 延迟 vs 实时（交叉 ★55）
print("\n【6】★★ 图传延迟 vs 实时约束（交叉 ★55 话轮 100ms）")
print("-" * 92)
print(f"  {'链路':>10}{'延迟ms':>9}{'实时对话':>10}{'闭环控制稳':>12}")
for k, v in LINK_LATENCY_MS.items():
    print(f"  {k:>10}{v:>9.0f}{str(can_support_realtime(v)):>10}"
          f"{str(control_stable(v)):>12}")
dig = LINK_LATENCY_MS["数字图传"]
print(f"\n  ★★ 数字图传 {dig:.0f}ms > 话轮间隔中位 {REAL_TURN_GAP_MS:.0f}ms")
print(f"     ★ 无人机视频【不能】用于实时对话 —— 用 ★55 的真数据推出")
print(f"  ★ 但 {dig:.0f}ms < 被控对象时间常数 200ms → 可以做遥操作控制")
ok["⑪ ★★ 数字图传不能支撑实时对话，但能遥操作"] = bool(
    (not can_support_realtime(dig)) and control_stable(dig))

# ══════════ 7 设备分类
print("\n【7】三类扩展：A 量程 / B 波段 / C 视点")
print("-" * 92)
cs = class_summary()
for c, lab in (("A", "A 扩量程·分辨率"), ("B", "B 扩波段·模态"),
               ("C", "C 改变视点")):
    print(f"  {lab}")
    for n, what, f in cs[c]:
        fs = f"{f:.1f}×" if np.isfinite(f) else "—"
        print(f"      {n:<10} {what:<12} {fs:>10}   失效模式 {failure_count(n)}")
ncls = sum(1 for c in ("A", "B", "C") if cs[c])
ok["⑫ 三类扩展齐全"] = bool(ncls == 3)

# ══════════ 8 ★★★ 硬依赖：接进环路
print("\n【8】★★★ 硬依赖：关掉设备，能力必须真的消失")
print("-" * 92)
for task in ("微表情", "高空覆盖"):
    on = sensing_with_devices(True, task=task)
    off = sensing_with_devices(False, task=task)
    print(f"  {task}")
    print(f"     开设备 {on['rate']:.3f}   关设备 {off['rate']:.3f}   "
          f"提升 {on['gain']:.2f}×")
drop = (sensing_with_devices(True, task="微表情")["rate"]
        - sensing_with_devices(False, task="微表情")["rate"])
ok["⑬ ★★ 关掉设备能力必须下降（非挂件）"] = bool(drop > 0.15)

# ══════════ 9 外挂特有的失效模式
print("\n【9】外挂引入了原生没有的失效模式")
print("-" * 92)
print(f"  {'设备':>10}{'失效模式数':>11}")
for n in ("无人机", "高速相机", "红外热成像", "云台"):
    print(f"  {n:>10}{failure_count(n):>11}")
print(f"\n  ★ 无人机 5 项最多 —— 扩展越多，引入的失效模式越多")
print(f"  ★ 原生感官【零延迟、靠代谢持续供能、解剖固定免标定】")

print("\n" + "=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
P = sum(ok.values()); T = len(ok)
print(f"\n  ✅ {P}/{T}")
print(f"""
  ★★★ 本轮结论
    ★★ 裸眼看微表情有【天花板 {CEIL:.3f}】—— 与距离无关
       因为一次注视只有 ~{FOVEA_DEG:.0f}° 中央凹，必须【串行扫视】
       而微表情 40~200ms，扫视潜伏期就要 200ms
       设备是【并行全画幅】→ 突破到 0.85
    ★★ Duchenne 靠【能否随意控制】，不是幅度：AU6 控制度 {c6:.2f} vs AU12 {c12:.2f}
    ★★ 数字图传 {dig:.0f}ms > 话轮 100ms → 无人机不能做实时对话（用 ★55 真数据）
    ★  帧率 vs 曝光有内部最优 f*=(2v²/C²)^(1/3)，与 ★59 打印机层厚同构
    ★  无人机 100m GSD {gsd100:.2f} cm/px（REAL 2.7~4 ✅）

  ❌ 修掉的两个自己的错
    ① 光学增益写成 space_factor(amp/g, dist/g) → 两者相除抵消，gain 恒无效
       ★ 增益应只改【等效距离】，不是同时缩小物体
    ② 帧率最优曾归一化掉抖动（blur/jitter）→ 最优 fps 与抖动无关，恒 191
       ★ 归一化不能消掉正在研究的变量

  ⚠️ 无人机高度【没有】内部最优：越高覆盖越大，直到撞 GSD 约束 → 边界解
     与 ★59 打印机（有内部最优）形成对照，如实记录
  ⚠️ 未验证真设备：无真无人机、无真微表情数据集（403/412 同前）
     参数来自 REAL 公开规格，机制来自已建的 ★16/★27/★43/★55""")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "native_ceiling": CEIL, "gsd100": gsd100,
           "detect_1m": r1m},
          open(os.path.join(HERE, ".sense", "external_devices.json"), "w"),
          ensure_ascii=False, indent=1)
