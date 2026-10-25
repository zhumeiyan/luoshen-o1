#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★59 打印机实验
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.printer import (
    cusp_height, surface_ra, print_time,
    eye_resolution_um, tactile_response, perceptible, optimal_layer,
    tensile_strength, anisotropy_ratio,
    overhang_ratio, needs_support, support_volume,
    warp_mm, dimensional_error,
    subtractive_feasible, additive_feasible, compare_process,
    closed_loop, TH_VIB, TH_SPA, MATERIALS,
)

ok = {}
print("=" * 92)
print(" ★59 打印机 —— 增材制造：从「描述」到「实体」")
print("=" * 92)

# ══════════════ 0 先验尺子：REAL 锚点
print("\n【0】★★ 先验尺子：触觉阈值用 REAL 锚点标定（不拍脑袋）")
print("-" * 92)
print("  锚点：0.05mm 手感光滑(不可感知) / 0.10mm 层纹明显(可感知) / 0.30mm 粗台阶(可感知)")
print(f"\n  {'层厚mm':>8}{'频率Hz':>9}{'cusp_μm':>9}{'vib':>8}{'spa':>8}"
      f"{'摸得出':>8}{'Ra_μm':>8}{'看得见':>8}")
for t in (0.02, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30, 0.40, 0.60):
    r = tactile_response(t, 45.0)
    p = perceptible(t, 45.0)
    print(f"  {t:>8.2f}{r['freq_hz']:>9.0f}{r['cusp_um']:>9.1f}"
          f"{r['vib']:>8.1f}{r['spa']:>8.1f}{str(p['tactile']):>8}"
          f"{p['ra_um']:>8.1f}{str(p['visible']):>8}")
anchors = [(0.05, False), (0.10, True), (0.30, True)]
hit = sum(perceptible(t, 45.0)["tactile"] == e for t, e in anchors)
for t, e in anchors:
    g = perceptible(t, 45.0)["tactile"] == e
    print(f"    锚点 t={t:.2f} 期望{str(e):>5} 实测{str(perceptible(t,45.0)['tactile']):>5} "
          f"{'✅' if g else '❌'}")
ok["① 触觉阈值经 REAL 锚点验证（3/3）"] = bool(hit == 3)

# ══════════════ 1 ★★★ 带通：手对层厚的敏感性不是单调
print("\n【1】★★★ 手对层厚的敏感性是【带通】，不是单调")
print("-" * 92)
ts = np.linspace(0.02, 0.60, 60)
vib = [tactile_response(t, 45.0)["vib"] for t in ts]
spa = [tactile_response(t, 45.0)["spa"] for t in ts]
k = int(np.argmax(vib))
TPEAK = float(ts[k])
print(f"  振动通道 vib 峰在 t = {ts[k]:.3f} mm   (vib={max(vib):.1f})")
print(f"    两端: t=0.02 → {vib[0]:.1f}    t=0.60 → {vib[-1]:.1f}")
print(f"    ★ 峰/端 比 = {max(vib)/max(min(vib),1e-9):.1f}×  → 真带通，不是边界")
print(f"  空间通道 spa 单调增: {spa[0]:.1f} → {spa[-1]:.1f}")
print(f"\n  ★★ REAL 对照：FDM 最常用层厚 0.08~0.20 mm")
print(f"     恰恰落在 vib 峰区 → 这就是为什么 FDM 件『摸起来有层纹感』")
interior = 0.02 < ts[k] < 0.60
ok["② ★★★ 振动通道是真带通（峰在内部）"] = bool(interior and max(vib) > 2 * vib[-1])
ok["③ 空间通道单调增（粗层纹靠空间感知）"] = bool(spa[-1] > spa[0])

# ══════════════ 2 ★★★ 硬依赖：约束来自手，不是眼
print("\n【2】★★★ 硬依赖：关掉感官 → 最优层厚必须变")
print("-" * 92)
print(f"  {'眼':>6}{'手':>6}{'最优层厚':>10}{'时间':>9}{'Ra_μm':>9}")
res = {}
for cfg in [(True, True), (True, False), (False, True), (False, False)]:
    r = optimal_layer(45, 50, 2500, eye_on=cfg[0], skin_on=cfg[1])
    res[cfg] = r
    if r.get("ok"):
        print(f"  {str(cfg[0]):>6}{str(cfg[1]):>6}{r['t_mm']:>10.3f}"
              f"{r['time_s']/60:>8.0f}min{r['ra_um']:>9.1f}")
    else:
        print(f"  {str(cfg[0]):>6}{str(cfg[1]):>6}{'✗ ' + r['reason']:>25}")
t_both = res[(True, True)].get("t_mm")
t_eye = res[(True, False)].get("t_mm")
t_none = res[(False, False)]
print(f"\n  ★ 只开眼 → {t_eye:.3f} mm")
print(f"    加上手 → {t_both:.3f} mm     收紧 {t_eye/t_both:.1f}×")
print(f"  ★★ 结论：【手摸】才是约束，不是眼")
print(f"     眼 25cm 阈值 {eye_resolution_um(250):.1f} μm  vs  手阈值 {TH_VIB} μm·响应")
ok["④ ★★ 加上手后最优层厚显著收紧（≥2×）"] = bool(t_eye / t_both >= 2.0)
ok["⑤ ★★ 两感官全关 → 抛错，不许回退默认"] = bool(not t_none.get("ok"))

# ══════════════ 3 台阶效应
print("\n【3】台阶效应：层厚与倾角")
print("-" * 92)
print(f"  {'倾角°':>7}" + "".join(f"t={t:<5.2f}" for t in (0.1, 0.2, 0.3)))
for th in (90, 60, 45, 30, 10, 0):
    row = "".join(f"{cusp_height(t, th)*1000:>8.1f}" for t in (0.1, 0.2, 0.3))
    print(f"  {th:>7}{row}   (μm)")
v90 = cusp_height(0.2, 90)
v45 = cusp_height(0.2, 45)
print(f"\n  ★ 垂直壁(90°) cusp={v90*1000:.1f} μm  斜面(45°) cusp={v45*1000:.1f} μm")
ok["⑥ 垂直壁无台阶、斜面有台阶"] = bool(v90 < 1e-9 and v45 > 0)

# ══════════════ 4 时间权衡
print("\n【4】时间 ∝ 1/层厚（权衡的另一半）")
print("-" * 92)
print(f"  {'层厚mm':>8}{'时间min':>10}{'Ra_μm':>9}")
tt = {}
for t in (0.05, 0.1, 0.2, 0.3, 0.4):
    tm = print_time(50, 2500, t) / 60.0
    tt[t] = tm
    print(f"  {t:>8.2f}{tm:>10.1f}{surface_ra(t,45)*1000:>9.1f}")
ratio_t = tt[0.1] / tt[0.2]
print(f"\n  ★ 层厚减半(0.2→0.1) → 时间 ×{ratio_t:.2f}   (理论 2.00)")
ok["⑦ 时间与层厚成反比"] = bool(abs(ratio_t - 2.0) < 0.05)

# ══════════════ 5 各向异性
print("\n【5】各向异性：层间结合弱")
print("-" * 92)
print(f"  {'材料':>8}{'Z/XY强度比':>12}{'XY(MPa)':>10}{'Z(MPa)':>9}")
for m in ("PLA", "ABS", "PETG", "树脂"):
    r = anisotropy_ratio(m)
    print(f"  {m:>8}{r:>12.2f}{tensile_strength(m,'XY'):>10.1f}"
          f"{tensile_strength(m,'Z'):>9.1f}")
rp = anisotropy_ratio("PLA")
print(f"\n  ★ PLA Z 方向只有 XY 的 {rp*100:.0f}%   (REAL FDM 50~80%)")
ok["⑧ 各向异性 Z<XY 且落 REAL 区间"] = bool(0.5 <= rp <= 0.8)

# ══════════════ 6 悬垂与支撑
print("\n【6】悬垂 45° 规则")
print("-" * 92)
print(f"  {'倾角°':>7}{'悬垂比':>9}{'需支撑':>9}")
for th in (0, 20, 40, 44, 45, 60, 90):
    print(f"  {th:>7}{overhang_ratio(th):>9.2f}{str(needs_support(th)):>9}")
ok["⑨ ≥45° 自支撑、<45° 需支撑"] = bool(
    (not needs_support(45)) and needs_support(44))

# ══════════════ 7 收缩翘曲
print("\n【7】收缩与翘曲（大件更容易翘）")
print("-" * 92)
print(f"  {'材料':>8}{'收缩率':>9}" + "".join(f"{l}mm".rjust(9)
                                             for l in (20, 50, 100, 200)))
for m in ("PLA", "ABS", "尼龙"):
    row = "".join(f"{warp_mm(m,l):>9.3f}" for l in (20, 50, 100, 200))
    print(f"  {m:>8}{MATERIALS[m]['shrink']:>9.3f}{row}")
w20, w200 = warp_mm("ABS", 20), warp_mm("ABS", 200)
print(f"\n  ★ ABS 20mm→{w20:.3f}mm   200mm→{w200:.3f}mm   放大 {w200/w20:.0f}×")
ok["⑩ 翘曲随尺寸超线性增长"] = bool(w200 / w20 > 10)

# ══════════════ 8 增材 vs 减材
print("\n【8】增材 vs 减材：互补，不是替代")
print("-" * 92)
print(f"  {'特征':>12}{'减材':>8}{'增材':>8}{'赢家':>18}")
wins = {}
for f in ("内腔", "晶格", "倒扣", "外表面", "通孔", "平面"):
    c = compare_process(f)
    wins[f] = c["winner"]
    print(f"  {f:>12}{str(c['subtractive']):>8}{str(c['additive']):>8}{c['winner']:>18}")
print(f"\n  ★ 减材赢：{sum(1 for v in wins.values() if v.startswith('减材'))} 项")
print(f"    增材赢：{sum(1 for v in wins.values() if v.startswith('增材'))} 项")
ok["⑪ 两种工艺各赢一部分（真互补）"] = bool(
    any(v.startswith("减材") for v in wins.values()) and
    any(v.startswith("增材") for v in wins.values()))

# ══════════════ 9 ★★ 闭环
print("\n【9】★★ 闭环：打印 → 自己看 → 自己摸 → 判定")
print("-" * 92)
print(f"  {'层厚':>6}{'眼':>6}{'手':>6}{'看着':>7}{'摸着':>7}{'判定':>10}")
for t in (0.05, 0.10, 0.30, 0.60):
    c = closed_loop(t, 45.0)
    print(f"  {t:>6.2f}{'开':>6}{'开':>6}{str(c['visible']):>7}"
          f"{str(c['tactile']):>7}{str(c['verdict']):>10}")
c_noskin = closed_loop(0.30, 45.0, eye_on=True, skin_on=False)
c_noeye = closed_loop(0.60, 45.0, eye_on=False, skin_on=True)
c_none = closed_loop(0.30, 45.0, eye_on=False, skin_on=False)
print(f"\n  ★ 关掉手：t=0.30 判定 = {c_noskin['verdict']}"
      f"  （手是唯一能抓到它的通道 → 判不了 = None）")
print(f"  ★ 关掉眼：t=0.60 判定 = {c_noeye['verdict']}")
print(f"  ★ 全关  ：判定 = {c_none['verdict']}  ← 不许编，必须 None")
ok["⑫ ★★ 感官全关 → verdict 必须是 None（不许下结论）"] = bool(
    c_none["verdict"] is None)
ok["⑬ 关掉手后，粗层纹不再被判为可感知"] = bool(
    c_noskin["verdict"] is not False or c_noskin["tactile"] is None)

print("\n" + "=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")
print(f"""
  ★★★ 本轮结论
    ★★ 手对层厚的敏感性是【带通】（vib 峰在 t≈{TPEAK:.2f} mm）
       两端都摸不出，中段最敏感
       REAL: FDM 常用 0.08~0.20mm 正落峰区 → 这就是「层纹感」的来源
    ★★ 约束来自【手】，不是眼
       只开眼 → {t_eye:.3f}mm；加上手 → {t_both:.3f}mm，收紧 {t_eye/t_both:.1f}×
    ★★ 感官全关 → 判定为 None，不许编（硬依赖）
    ★  制造方式把各向异性写进材料：Z 只有 XY 的 {rp*100:.0f}%
    ★  增材/减材互补：内腔晶格靠增材，表面质量靠减材

  ❌ 修掉的两个自己的错
    ① 触觉阈值写死 0.5 μm（Pacini 位移阈值）→ 混淆了位移与粗糙度
       导致任何层厚都「摸得出」，永远不合格
    ② 把 vib/spa 相加 → SA1 单调项把 Pacini 的【带通】盖掉
       必须分开保留，才能看到带通

  ⚠️ 没建模：热应力/层间温度、挤出波动、填充图案对强度的影响
  ⚠️ 阈值 TH_VIB/TH_SPA 由 3 个 REAL 锚点反推，锚点少 → 只能算标定，不算验证""")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "vib_peak_mm": TPEAK,
           "t_eye_only": float(t_eye), "t_both": float(t_both)},
          open(os.path.join(HERE, ".sense", "printer.json"), "w"),
          ensure_ascii=False, indent=1)
