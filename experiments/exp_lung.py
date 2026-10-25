#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★51 肺 —— 通气、换气、呼吸控制
================================================================
★ 承接 ★49：氧级联里「湿化气道 150 → 肺泡 100」那一段
    ★★ 上一轮是【常数】，现在算出来

★★★ 本轮硬约束（延续 ★50 原则）
   ① 每个结论必须有【对照】
   ② 数值必须落【REAL 区间】
   ③ 这是【监测 + 执行器】，不是限制 —— 只算状态与代价
   ④ ★ 特别防"低氧就给氧" —— 必须做出给氧【无效】甚至【有害】的场景

★★★ 五组判据级对照
   ① 浅快呼吸 = 无效呼吸（MV 相同，VA 从 4.2 → 0）
   ② 表面活性物质（有 vs 无：稳定 vs 塌陷）
   ③ ★★★ 弥散障碍 vs 真分流（基线配平后，给氧反应相反）
   ④ ★★★ 静息正常 ≠ 运动正常（弥散储备）
   ⑤ ★★★ 过度通气悖论（脑氧输送腰斩，血氧几乎没涨）
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from core.lung import (
    pio2, pao2_alveolar, paco2_alveolar, alveolar_ventilation,
    minute_ventilation, dead_space_fraction, time_constant, elastic_work,
    resistive_work, total_work, optimal_frequency, laplace_pressure,
    surfactant_tension, two_alveoli_stability, capillary_transit_time,
    end_capillary_po2, diffusing_capacity_effective, mixed_arterial_o2,
    po2_from_content, cerebral_blood_flow, o2_delivery_to_brain,
    ventilatory_response, barometric_pressure, altitude_case, LungSense,
    PB_SEA, FIO2_AIR, VT, VD, F_RESP, DL_REST, PVO2, VC_BLOOD,
)
from core.vascular import o2_content, so2

ok = {}
print("=" * 92)
print(" ★51 肺 —— 通气、换气、呼吸控制")
print("=" * 92)

# ================================================================ A
print("\n【A】★ 肺泡气体方程 —— ★49 里那个 100 的来源")
print("-" * 92)
pi = pio2()
pa = pao2_alveolar(40.0)
pc = paco2_alveolar(4.2)
print(f"  PiO2 = (760 − 47) × 0.2093 = {pi:.1f} mmHg")
print(f"  PAO2 = {pi:.1f} − 40/0.8 = {pa:.1f} mmHg")
print(f"  PACO2 = 0.863 × 200 / 4.2 = {pc:.1f} mmHg")
print(f"\n  ★★ ★49 氧级联里我【硬填】的肺泡 PO2 = 100")
print(f"     现在算出来 = {pa:.1f} —— 对上了，而且是从气压和呼吸商推出来的")
ok["① PiO2 落 REAL 145~152 mmHg"] = bool(145 <= pi <= 152)
ok["② ★★ PAO2 算出来落 REAL 95~105（★49 的常数有了来源）"] = bool(95 <= pa <= 105)
ok["③ PACO2 落 REAL 38~42 mmHg"] = bool(38 <= pc <= 42)

# ================================================================ B
print("\n【B】★★ 浅快呼吸 = 无效呼吸（MV 相同，VA 可以归零）")
print("-" * 92)
print(f"  {'VT(L)':<8}{'f(/min)':>8}{'MV':>8}{'VA':>8}{'死腔比':>8}{'PACO2':>9}{'判定':>10}")
rowsB = []
for vt in [0.60, 0.50, 0.35, 0.25, 0.20, 0.15]:
    f = 6.0 / vt                 # ★ 固定 MV = 6.0
    va = alveolar_ventilation(vt, f)
    paco2 = paco2_alveolar(va) if va > 1e-6 else float("inf")
    tag = "有效" if va >= 3.5 else ("不足" if va > 0 else "★死呼吸")
    rowsB.append((vt, f, va, paco2))
    ps = f"{paco2:.0f}" if np.isfinite(paco2) else "  ∞"
    print(f"  {vt:<8.2f}{f:>8.1f}{minute_ventilation(vt,f):>8.2f}{va:>8.2f}"
          f"{dead_space_fraction(vt):>8.2f}{ps:>9}{tag:>10}")
va0 = rowsB[1][2]        # VT=0.5
va_last = rowsB[-1][2]   # VT=0.15
print(f"\n  ★★ 分钟通气量全部 = 6.00 L/min，但肺泡通气从 {va0:.2f} 掉到 {va_last:.2f}")
ok["④ ★★ MV 相同(6.0)，VA 可以降到 0（只看 MV 会误判）"] = bool(
    va0 > 4.0 and va_last < 1e-9)
print(f"  ★★ VT=0.15 = 死腔 0.15 → 每次呼吸只把死腔里的气来回搬，零换气")
ratio_va = alveolar_ventilation(0.5, 12) / alveolar_ventilation(0.25, 24)
print(f"\n  ★ 深慢 vs 浅快（MV 都是 6.0）：VA = 4.20 vs 2.40，差 {ratio_va:.2f} 倍")
# ★ 判据阈值改为 1.5：我第一版拍了 >2.0，但真实比值就是 1.75
#   —— 阈值不能凭感觉设，判据⑧的失败正是这个教训
ok["⑤ ★ 深慢呼吸的 VA 显著大于浅快（>1.5 倍）"] = bool(ratio_va > 1.5)
print(f"\n  ★ 正常死腔比 VD/VT = {dead_space_fraction():.2f}（REAL 0.3）")
ok["⑥ 死腔比落 REAL 0.25~0.35"] = bool(0.25 <= dead_space_fraction() <= 0.35)

# ================================================================ C
print("\n【C】★ 力学：顺应性、阻力、时间常数、最优频率")
print("-" * 92)
tau = time_constant()
print(f"  ★ 时间常数 τ = R × C = {tau:.3f} s（REAL 肺 0.2~0.4）")
ok["⑦ 时间常数落 REAL 0.15~0.5 s"] = bool(0.15 <= tau <= 0.5)
print(f"\n  ★★ 固定 VA=4.2 时，不同 VT 的呼吸总功（弹性 + 阻力）")
print(f"  {'VT(L)':<8}{'f(/min)':>9}{'弹性功':>9}{'阻力功':>9}{'总功':>9}")
best = None
for vt in [0.30, 0.35, 0.45, 0.50, 0.60, 0.80, 1.00]:
    f = 4.2 / (vt - VD)
    ew = elastic_work(vt, f); rw = resistive_work(vt, f); tw = ew + rw
    if best is None or tw < best[1]:
        best = (vt, tw, f)
    print(f"  {vt:<8.2f}{f:>9.1f}{ew:>9.3f}{rw:>9.3f}{tw:>9.3f}")
print(f"\n  ★ 最省功的潮气量 = {best[0]:.2f} L（REAL 自主呼吸 0.4~0.6）")
ok["⑧ ★★ 存在最优潮气量，且落 REAL 0.4~0.6 L"] = bool(0.40 <= best[0] <= 0.60)
print(f"  ★ 机制：VT 大→弹性功↑；VT 小→频率必须高→阻力功↑（两害相权）")
ok["⑨ ★ 弹性功随 VT 增大而增大"] = bool(
    elastic_work(1.0, 5.0) > elastic_work(0.5, 12.0))

# ★ 肺纤维化 vs 肺气肿
print(f"\n  ★★ 两种病，顺应性相反：")
print(f"  {'状态':<12}{'C(L/cmH2O)':>12}{'弹性功/分':>16}{'表现':>14}")
for name, c in [("正常", 0.20), ("肺纤维化", 0.08), ("肺气肿", 0.35)]:
    print(f"  {name:<12}{c:>12.2f}{elastic_work(0.5, 12.0, c):>16.3f}"
          f"{'硬,要更大负压' if c < 0.15 else ('软,但呼气难' if c > 0.28 else '正常'):>14}")
ok["⑩ ★★ 纤维化弹性功 > 正常（硬）"] = bool(
    elastic_work(0.5, 12.0, 0.08) > elastic_work(0.5, 12.0, 0.20))
print(f"  ★★ 肺气肿 C↑ 弹性功反而【低】，但呼气困难 —— 因为弹性回缩力没了")
print(f"     ★ 所以『顺应性好』不等于『呼吸轻松』—— 可证伪")

# ================================================================ D
print("\n【D】★★ 表面活性物质（Laplace P = 2T/r）")
print("-" * 92)
r_no = two_alveoli_stability(False)
r_yes = two_alveoli_stability(True)
print(f"  ★ 两个相通肺泡，初始半径比 1.5，看 200 步后：")
print(f"  {'':<12}{'最终半径比':>12}{'判定':>14}")
print(f"  {'无活性物质':<12}{r_no:>12.2f}{'★发散,小肺泡塌陷':>14}")
print(f"  {'有活性物质':<12}{r_yes:>12.2f}{'稳定':>14}")
ok["⑪ ★★ 无表面活性物质 → 半径比发散（小肺泡塌陷）"] = bool(r_no > 5.0)
ok["⑫ ★★ 有表面活性物质 → 稳定（半径比不发散）"] = bool(r_yes < 5.0)
print(f"\n  ★ 机制：P = 2T/r，小肺泡内压更高 → 把气挤给大肺泡 → 正反馈")
print(f"    表面活性物质让 T 随 r 减小而【下降】，抵消掉这个正反馈")
print(f"    T: r=1.5 时 {surfactant_tension(1.5):.1f} → r=0.5 时 {surfactant_tension(0.5):.1f} dyn/cm")
ok["⑬ ★ 表面活性物质的 T 随半径减小而降低"] = bool(
    surfactant_tension(0.5) < surfactant_tension(1.5))

# ================================================================ E
print("\n【E】★★★ 核心对照：弥散障碍 vs 真分流（给氧反应相反）")
print("-" * 92)
print("  ★ 两者都造成低氧。先把【基线配平到几乎相同】，再给纯氧")
PA_AIR = pao2_alveolar(40.0)
PA_O2 = pao2_alveolar(40.0, PB_SEA, 1.0)     # FiO2 = 1.0
print(f"  ★ 吸入空气 PAO2 = {PA_AIR:.1f}；纯氧 PAO2 = {PA_O2:.1f}\n")

# ★ 组A：真分流。扫描 fs 找基线 PaO2 最低者
# ★ 组B：弥散障碍。扫描 DL 找基线匹配者
def shunt_case(fs, pao2_alv, q=5.0, dl=DL_REST):
    dle = diffusing_capacity_effective(dl, q)
    pce = end_capillary_po2(pao2_alv, dle, q)
    ca = mixed_arterial_o2(fs, o2_content(pce), o2_content(PVO2))
    return pce, ca, po2_from_content(ca)

def diffusion_case(dl, pao2_alv, q=5.0):
    dle = diffusing_capacity_effective(dl, q)
    pce = end_capillary_po2(pao2_alv, dle, q)
    return pce, o2_content(pce), pce

# ★ 配平：让两组基线 PaO2 都落在 50~60
fs_pick, dl_pick = None, None
for fs in np.arange(0.10, 0.71, 0.01):
    _, _, p = shunt_case(fs, PA_AIR)
    if 50 <= p <= 60:
        fs_pick = float(fs); break
for dl in np.arange(8.0, 0.3, -0.05):
    p = diffusion_case(dl, PA_AIR)[0]
    if 50 <= p <= 60:
        dl_pick = float(dl); break

pce_s_a, ca_s_a, pa_s_a = shunt_case(fs_pick, PA_AIR)
pce_d_a, ca_d_a, pa_d_a = diffusion_case(dl_pick, PA_AIR)
pce_s_o, ca_s_o, pa_s_o = shunt_case(fs_pick, PA_O2)
pce_d_o, ca_d_o, pa_d_o = diffusion_case(dl_pick, PA_O2)

print(f"  {'':<16}{'基线PaO2':>10}{'给纯氧后':>11}{'提升':>10}{'判定':>14}")
print(f"  {'真分流 fs=%.2f'%fs_pick:<16}{pa_s_a:>10.1f}{pa_s_o:>11.1f}"
      f"{pa_s_o-pa_s_a:>10.1f}{'★几乎无效':>14}")
print(f"  {'弥散障碍 DL=%.1f'%dl_pick:<16}{pa_d_a:>10.1f}{pa_d_o:>11.1f}"
      f"{pa_d_o-pa_d_a:>10.1f}{'★有效':>14}")
print(f"\n  ★★ 基线几乎相同（{pa_s_a:.1f} vs {pa_d_a:.1f}，差 {abs(pa_s_a-pa_d_a):.1f}）")
print(f"     给氧后差 {(pa_d_o-pa_d_a)/max(pa_s_o-pa_s_a,1e-9):.1f} 倍")
ok["⑭ ★★ 两组基线配平成功（差 <10 mmHg）"] = bool(abs(pa_s_a - pa_d_a) < 10)
ok["⑮ ★★★ 真分流对纯氧反应差（提升 <40 mmHg）"] = bool(pa_s_o - pa_s_a < 40)
ok["⑯ ★★★ 弥散障碍对纯氧反应好（提升 >150 mmHg）"] = bool(pa_d_o - pa_d_a > 150)
print(f"\n  ★★★ 为什么：")
print(f"     真分流：那部分血【根本没经过肺泡】，永远是静脉血 → 与 PAO2 无关")
print(f"     弥散障碍：抬高 PAO2 → 加大弥散(PA−Pc)梯度 → 有效")
print(f"     ★ REAL 鉴别点：顽固性低氧血症 refractory hypoxemia")
print(f"     ★★ 所以『低氧就给氧』不是万能的 —— 可证伪")

# ★ 单调性判据（比单点更稳）
print(f"\n  ★ 更稳的判据：分流越大，给氧收益越小（单调）")
print(f"  {'分流':<8}{'基线':>9}{'给氧后':>10}{'提升':>10}")
gains = []
for fs in [0.05, 0.15, 0.30, 0.45, 0.60]:
    _, _, p_a = shunt_case(fs, PA_AIR)
    _, _, p_o = shunt_case(fs, PA_O2)
    gains.append(p_o - p_a)
    print(f"  {fs:<8.2f}{p_a:>9.1f}{p_o:>10.1f}{p_o-p_a:>10.1f}")
ok["⑰ ★★ 分流越大给氧收益越小（单调不增）"] = bool(
    all(gains[i] >= gains[i+1] - 1.0 for i in range(len(gains)-1)))

# ================================================================ F
print("\n【F】★★★ 静息正常 ≠ 运动正常（弥散储备）")
print("-" * 92)
print(f"  {'DL':<7}{'静息Q=5':>10}{'运动Q=20':>10}{'运动降幅':>10}{'判定':>12}")
rowsF = []
for dl in [25.0, 15.0, 8.0, 5.0]:
    p_rest = end_capillary_po2(PA_AIR, diffusing_capacity_effective(dl, 5.0), 5.0)
    p_ex = end_capillary_po2(PA_AIR, diffusing_capacity_effective(dl, 20.0), 20.0)
    rowsF.append((dl, p_rest, p_ex))
    tag = "正常" if p_ex > 90 else (" borderline" if p_ex > 75 else "★运动低氧")
    print(f"  {dl:<7.1f}{p_rest:>10.1f}{p_ex:>10.1f}{p_rest-p_ex:>10.1f}{tag:>12}")
ok["⑱ ★★ DL=8 时静息几乎正常(>88) 但运动显著下降(<80)"] = bool(
    rowsF[2][1] > 88 and rowsF[2][2] < 80)
ok["⑲ ★ 正常 DL=25 运动仍能维持（储备够）"] = bool(rowsF[0][2] > 90)
print(f"\n  ★ 机制：毛细血管通过时间")
print(f"     静息 {capillary_transit_time(5.0):.2f} s（REAL 0.75~1.0）")
print(f"     运动 {capillary_transit_time(20.0):.2f} s（REAL 0.25~0.30）")
ok["⑳ 静息通过时间落 REAL 0.75~1.0 s"] = bool(0.75 <= capillary_transit_time(5.0) <= 1.0)
ok["㉑ 运动通过时间落 REAL 0.20~0.35 s"] = bool(0.20 <= capillary_transit_time(20.0) <= 0.35)
print(f"  ★★ 正常人靠『静息 0.9s 里 0.25s 就平衡完』的储备；运动时储备被吃光")
print(f"     ★ 所以静息血氧正常【不代表】弥散功能正常 —— 只有运动才暴露")

# ================================================================ G
print("\n【G】★★★ 过度通气悖论（自由潜水晕厥）")
print("-" * 92)
print(f"  {'PACO2':<8}{'PAO2':>8}{'SO2':>8}{'CaO2':>9}{'脑血流':>9}{'脑氧输送':>11}{'判定':>12}")
rowsG = []
for paco2 in [40, 35, 30, 25, 20]:
    pao2 = pao2_alveolar(paco2)
    s = so2(pao2)
    c = o2_content(pao2)
    cbf = cerebral_blood_flow(paco2)
    dob = o2_delivery_to_brain(pao2, paco2)
    rowsG.append((paco2, pao2, s, c, cbf, dob))
    tag = "正常" if paco2 >= 35 else ("↓" if paco2 >= 25 else "★危险")
    print(f"  {paco2:<8}{pao2:>8.1f}{s:>8.3f}{c:>9.1f}{cbf:>9.2f}{dob:>11.1f}{tag:>12}")
d_s = rowsG[-1][2] - rowsG[0][2]
d_dob = (rowsG[0][5] - rowsG[-1][5]) / rowsG[0][5]
print(f"\n  ★★ 过度通气把 PAO2 从 {rowsG[0][1]:.1f} 提到 {rowsG[-1][1]:.1f}")
print(f"     但 SO2 只从 {rowsG[0][2]:.3f} 到 {rowsG[-1][2]:.3f}（+{d_s:.3f}）")
print(f"     ★ 因为 Hb 在 PAO2=100 时【已经饱和】，多吸的气几乎全浪费")
print(f"     代价：脑血流 ×{rowsG[-1][4]:.2f}，脑氧输送 ↓{d_dob:.0%}")
ok["㉒ ★★★ 过度通气使 SO2 提升极小（<0.03）"] = bool(d_s < 0.03)
ok["㉓ ★★★ 过度通气使脑氧输送下降 >40%"] = bool(d_dob > 0.40)
print(f"\n  ★★★ REAL：自由潜水前过度通气 → 浅水黑视/晕厥，就是这条")
print(f"     ★★ 又是『低氧就多吸氧』的反例 —— 缺氧的 bottleneck 不在肺泡")

# ================================================================ H
print("\n【H】★ 高原：靠的是【过度通气】，不是别的")
print("-" * 92)
print(f"  {'高度(m)':<9}{'Pb':>7}{'PiO2':>8}{'PAO2(PACO2=40)':>17}{'PAO2(过度通气)':>16}")
rowsH = []
for alt in [0, 2000, 4000, 6000, 8848]:
    pb, pi_, pa40 = altitude_case(alt, 40.0)
    pa_hyper = altitude_case(alt, 10.0)[2]
    rowsH.append((alt, pb, pi_, pa40, pa_hyper))
    print(f"  {alt:<9}{pb:>7.0f}{pi_:>8.1f}{pa40:>17.1f}{pa_hyper:>16.1f}")
print(f"\n  ★★ 珠峰顶 PACO2 若保持 40 → PAO2 = {rowsH[-1][3]:.1f}（负数=不可能存活）")
print(f"     必须过度通气把 PACO2 压到 ~7.5~10 → PAO2 = {rowsH[-1][4]:.1f}")
ok["㉔ ★★ 珠峰若不过度通气则 PAO2 ≤ 0（不可能存活）"] = bool(rowsH[-1][3] <= 0)
ok["㉕ ★★ 过度通气后 PAO2 转正且落 REAL 25~40"] = bool(25 <= rowsH[-1][4] <= 40)
print(f"  ★ 珠峰实测气压约 253 mmHg，我用国际标准大气公式得 "
      f"{barometric_pressure(8848):.0f}（差 {(253-barometric_pressure(8848))/253:.0%}，"
      f"因标准大气温度递减率与实际不同）—— 如实标注，不修正掩盖")

# ================================================================ I
print("\n【I】★ 呼吸控制：CO2 是主驱动，O2 是次驱动")
print("-" * 92)
print(f"  {'状态':<16}{'PaCO2':>7}{'PaO2':>7}{'通气驱动':>10}")
d1 = ventilatory_response(40, 100)
d2 = ventilatory_response(50, 100)
d3 = ventilatory_response(40, 50)
print(f"  {'正常':<16}{40:>7}{100:>7}{d1:>10.1f}")
print(f"  {'CO2潴留':<16}{50:>7}{100:>7}{d2:>10.1f}")
print(f"  {'低氧':<16}{40:>7}{50:>7}{d3:>10.1f}")
ok["㉖ ★ CO2 升高 10 mmHg 的驱动 > 低氧到 50 的驱动"] = bool(d2 > d3)
print(f"\n  ★★ COPD：中枢钝化后，给高浓度氧会怎样")
print(f"  {'':<20}{'给氧前驱动':>12}{'给氧后驱动':>12}{'判定':>12}")
for lbl, bl in [("正常人", False), ("COPD(中枢钝化)", True)]:
    before = ventilatory_response(55, 50, peripheral_blunted=bl)
    after = ventilatory_response(55, 90, peripheral_blunted=bl)
    print(f"  {lbl:<20}{before:>12.2f}{after:>12.2f}"
          f"{'安全' if not bl else '★呼吸被抑制':>12}")
    if bl:
        ok["㉗ ★★ COPD 给高浓度氧 → 呼吸驱动下降（真实现象）"] = bool(after < before)
print(f"  ★★ 正常人靠 CO2 驱动，给氧不影响；COPD 靠低氧驱动，给氧=撤掉驱动")
print(f"     ★★ 又是『低氧就给氧』的反例 —— 第三次")

# ================================================================ J
print("\n【J】⚠️ 诚实：不能说什么")
print("-" * 92)
print("  ❌ 不能说『这是临床实测数据』—— 是教科书参数标定")
print("  ❌ 分流/弥散对照里的 β 用了单点近似 (CcO2−CvO2)/(PA−Pv)，")
print("     不是沿毛细血管积分 —— 结论方向稳健，绝对值不精确")
print("  ❌ 珠峰气压用标准大气公式，实测 253 vs 算得 236，差 7%，没掩盖")
print("  ❌ 表面活性物质的 T(r) 曲线是我构造的单调函数，不是实测")
print("  ✅ 能说：① 数值落 REAL  ② 五组对照均成立")
print("          ③ 『低氧就给氧』在三种场景下失效（分流/过度通气/COPD）")

print("\n" + "=" * 92)
print(" 判据")
print("=" * 92)
for k, v in ok.items():
    print(f"  {'✅' if v else '❌'} {k}")
print(f"\n  ✅ {sum(ok.values())}/{len(ok)}")

json.dump({"ok": {k: bool(v) for k, v in ok.items()},
           "alveolar": {"PiO2": pi, "PAO2": pa, "PACO2": pc},
           "shunt_vs_diffusion": {"fs": fs_pick, "dl": dl_pick,
                                  "base_shunt": pa_s_a, "base_diff": pa_d_a,
                                  "o2_shunt": pa_s_o, "o2_diff": pa_d_o},
           "hyperventilation": [{"paco2": r[0], "pao2": r[1], "so2": r[2],
                                 "cbf": r[4], "o2_brain": r[5]} for r in rowsG]},
          open(os.path.join(HERE, ".sense", "lung.json"), "w"),
          ensure_ascii=False, indent=1)
