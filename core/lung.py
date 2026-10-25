#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★51 肺 —— 通气、换气、呼吸控制
================================================================
★ 承接 ★49：氧级联里「湿化气道 150 → 肺泡 100」那一段
    ★★ 上一轮我是【当成常数】填进去的 —— 现在把它算出来

★★★ 核心：肺泡气体方程（这是 PAO2=100 的真正来源）
    PiO2 = (Pb − PH2O) × FiO2         海平面 = (760−47)×0.2093 = 149.2
    PAO2 = PiO2 − PACO2/R              R=0.8（呼吸商）
         = 149.2 − 40/0.8 = 99.2 ≈ 100  ★ 对上了

★★ 肺容积（REAL）
    TLC 6.0   VC 4.8   RV 1.2   FRC 2.4   VT 0.5   解剖死腔 0.15 L
    呼吸频率 12/min
    肺泡通气量 VA = (VT − VD) × f = (0.5−0.15)×12 = 4.2 L/min  ★ REAL 4.2

★★★ 判据级对照 1：浅快呼吸是【无效呼吸】
    分钟通气量 MV 相同 = 6.0 L/min 时：
      VT=0.50 f=12 → VA = 4.20
      VT=0.25 f=24 → VA = 2.40
      VT=0.15 f=40 → VA = 0.00   ★★ 全部落在死腔里，等于没呼吸
    ★ MV 一样但 VA 从 4.2 掉到 0 —— 只看 MV 会误判

★★ 力学
    顺应性 C = ΔV/ΔP，正常 0.2 L/cmH2O
      ★ 肺纤维化 C↓（硬，要更大负压）
      ★ 肺气肿 C↑（软，但弹性回缩↓ → 呼气困难）
    气道阻力 R = ΔP/flow，正常 2 cmH2O/(L/s)
    时间常数 τ = R×C，正常 0.2×2×... 单位换算后 ≈ 0.24 s

★★★ 判据级对照 2：表面活性物质（Laplace P = 2T/r）
    两个相通的肺泡，小的内压更大 → 气从小跑到大 → 小肺泡塌陷
      ★ 无表面活性物质：不稳定（半径比从 1.0 发散）
      ★ 有表面活性物质：T 随 r 减小而减小 → 稳定
    纯水 70 dyn/cm → 表面活性物质可降到 <10 dyn/cm

★★★ 判据级对照 3（最漂亮）：弥散障碍 vs 真分流
    两者都造成低氧，但对【给氧】的反应完全相反：
      弥散障碍（肺纤维化）：给氧【有效】（提高 PA → 加大弥散梯度）
      真分流（ARDS/肺不张）：给氧【几乎无效】（血根本没经过肺泡）
    ★ 这是临床真实鉴别点：refractory hypoxemia

    Bohr 积分法：
      (PA − Pc_end) = (PA − Pv) × exp(−DL × t / (Vc × β))
      t = Vc/Q = 毛细血管通过时间
        静息 Q=5  → 0.075/5  min = 0.90 s   ★ REAL 0.75~1.0
        运动 Q=20 → 0.075/20 min = 0.225 s  ★ REAL 0.25~0.3
      Vc = 75 mL，DL 静息 25 mL/min/mmHg

★★★ 判据级对照 4：静息正常 ≠ 运动正常（弥散储备）
    DL=8（弥散障碍）：
      静息 末端 PO2 = 92.2（几乎正常）
      运动 末端 PO2 = 64.0（崩）
    ★ 静息血氧正常不代表弥散功能正常 —— 只有运动才暴露

★★★ 判据级对照 5：过度通气悖论（自由潜水晕厥）
    过度通气 → PaCO2↓ → 脑血管收缩 → 脑血流↓ → 头晕/晕厥
    ★ 但动脉血氧几乎【没有提高】：
      PAO2=100 时 SO2 已 0.975；把 PAO2 提到 120，SO2 只到 0.983
      ★ 多吸的气几乎全浪费，代价却是脑血流掉一半
    ★★ 这是 REAL 现象：自由潜水前过度通气 → 浅水黑视/晕厥

★ 高原：靠的是【过度通气】，不是别的
    珠峰 Pb=253 mmHg：PiO2 = (253−47)×0.2093 = 43.1
    若 PACO2 保持 40 → PAO2 = 43.1 − 50 = −6.9 ★ 不可能存活
    实际登顶者 PACO2 低至 ~7.5 → PAO2 = 43.1 − 9.4 = 33.7 ★ REAL ~35
    ★★ 所以高原靠过度通气，代价是呼吸性碱中毒

★ 呼吸控制：CO2 是主驱动，O2 是次驱动
    中枢化学感受器（CO2 经 pH）斜率 2~3 L/min 每 mmHg
    外周（颈动脉体）PaO2 < 60 mmHg 才显著
    ★★ COPD 患者长期 CO2 潴留 → 中枢钝化 → 靠低氧驱动
       → 此时给高浓度氧会抑制呼吸 → CO2 更高 → 昏迷（真实现象）

⚠️ 贯彻 ★50 原则：这是【监测 + 执行器】，不是限制
    ★ 呼吸确实会【动】（它是执行器），但下面的函数只计算状态与代价
"""
from __future__ import annotations
import numpy as np

# ---- 常数（REAL）----
PB_SEA = 760.0        # mmHg 海平面大气压
PH2O = 47.0           # mmHg 37°C 饱和水蒸气压
FIO2_AIR = 0.2093
R_QUOTIENT = 0.8      # 呼吸商
VCO2 = 200.0          # mL/min CO2 产生量

VT = 0.50             # L 潮气量
VD = 0.15             # L 解剖死腔
F_RESP = 12.0         # /min

TLC, VC, RV, FRC = 6.0, 4.8, 1.2, 2.4    # L
C_LUNG = 0.20         # L/cmH2O 顺应性
R_AW = 2.0            # cmH2O/(L/s) 气道阻力
VC_BLOOD = 0.075      # L 肺毛细血管血容量
DL_REST = 25.0        # mL/min/mmHg 弥散量

PVO2 = 40.0           # mmHg 混合静脉 PO2
PACO2_N = 40.0        # mmHg 正常肺泡/动脉 CO2


# =================================================================
# 一、★ 肺泡气体方程
# =================================================================
def pio2(pb: float = PB_SEA, fio2: float = FIO2_AIR) -> float:
    """★ PiO2 = (Pb − PH2O) × FiO2"""
    return (pb - PH2O) * fio2


def pao2_alveolar(paco2: float = PACO2_N, pb: float = PB_SEA,
                  fio2: float = FIO2_AIR, R: float = R_QUOTIENT) -> float:
    """★★ PAO2 = PiO2 − PACO2/R"""
    return pio2(pb, fio2) - paco2 / R


def paco2_alveolar(va_L_min: float, vco2: float = VCO2) -> float:
    """
    ★ PACO2 = 0.863 × VCO2 / VA
      0.863 是单位换算（BTPS→STPD）
      正常 VA=4.2 → 0.863×200/4.2 = 41.1  ★ REAL 40
    """
    return 0.863 * vco2 / va_L_min


# =================================================================
# 二、★★ 浅快呼吸 = 无效呼吸
# =================================================================
def alveolar_ventilation(vt: float = VT, f: float = F_RESP, vd: float = VD):
    """★ VA = (VT − VD) × f      MV = VT × f"""
    return max((vt - vd), 0.0) * f


def minute_ventilation(vt: float = VT, f: float = F_RESP):
    return vt * f


def dead_space_fraction(vt: float = VT, vd: float = VD):
    """★ 死腔占比 VD/VT，正常 0.3"""
    return vd / vt


# =================================================================
# 三、★ 力学：顺应性、阻力、时间常数
# =================================================================
def compliance(pressure: float, volume: float) -> float:
    return volume / pressure


def time_constant(r_aw: float = R_AW, c: float = C_LUNG) -> float:
    """★ τ = R × C。R: cmH2O/(L/s), C: L/cmH2O → τ 单位 s"""
    return r_aw * c


def elastic_work(vt: float = VT, f: float = F_RESP, c: float = C_LUNG) -> float:
    """
    ★ 弹性功 = 【每分钟】 f × VT²/(2C)
      ★★ 我第一版写的是 VT²/(2C) 且没乘 f，而阻力功却按每分钟算
         两人口径不一致 → 最优潮气量算到扫描边界 0.35（单调），
         REAL 自主呼吸是 0.4~0.6 —— 判据⑧失败才暴露出来
    """
    return f * vt ** 2 / (2.0 * c)


def resistive_work(vt: float, f: float, r_aw: float = R_AW) -> float:
    """
    ★ 阻力功 = 【每分钟】 R × flow_rms² × 60
      flow_peak = π × VT × f/60（正弦近似），flow_rms² = flow_peak²/2
      → W = R × (π·VT·f/60)² / 2 × 60 = π²/120 × R × VT² × f²
      ★ (π²/120) = 0.0822
    """
    return (np.pi ** 2 / 120.0) * r_aw * vt ** 2 * f ** 2


def total_work(vt: float = VT, f: float = F_RESP,
               c: float = C_LUNG, r_aw: float = R_AW):
    return elastic_work(vt, f, c) + resistive_work(vt, f, r_aw)


def optimal_frequency(vt: float = VT, c: float = C_LUNG,
                      r_aw: float = R_AW, target_va: float = 4.2):
    """
    ★★ 给肺泡通气量定死后，存在一个【最优呼吸频率】使总功最小
      ★ 慢深呼吸 → 弹性功大（VT 大）
      ★ 快浅呼吸 → 阻力功大（flow 大）+ 死腔浪费
      ★ REAL：正常自主呼吸就落在这个最优附近
    """
    if vt <= VD:
        return None
    f = target_va / (vt - VD)
    if f <= 0:
        return None
    return f, total_work(vt, f, c, r_aw)


# =================================================================
# 四、★★ 表面活性物质（Laplace）
# =================================================================
def laplace_pressure(tension: float, radius: float) -> float:
    """★ P = 2T/r"""
    return 2.0 * tension / radius


def surfactant_tension(radius: float, r0: float = 1.0,
                       t_max: float = 30.0, t_min: float = 5.0) -> float:
    """
    ★★ 表面活性物质：表面张力随【面积减小】而下降
      呼气时肺泡缩小 → 分子密集 → T 显著下降 → 抵消 r 变小带来的 P 上升
      ★ 纯水 T 恒定 ≈ 70 dyn/cm（这里用 30 代表无活性物质的生理液）
    """
    x = np.clip(radius / r0, 0.2, 1.5)
    return t_min + (t_max - t_min) * np.clip((x - 0.2) / (1.5 - 0.2), 0, 1)


def two_alveoli_stability(use_surfactant: bool, r_ratio0: float = 1.0,
                          steps: int = 200, dt: float = 0.05) -> float:
    """
    ★★ 两个相通肺泡（半径 r1 > r2），无表面活性物质时会怎样
      无：P1 = 2T/r1 < P2 = 2T/r2 → 气从低压(大)流向高压? 
          ★ 注意：压力高的小肺泡把气【挤】到大肺泡 → 小肺泡塌陷
      模拟：dr ∝ (P_other − P_self)，看半径比是否发散
      返回最终半径比 r_big/r_small
    """
    r_big, r_small = 1.2 * r_ratio0, 0.8 * r_ratio0
    T_fixed = 30.0
    for _ in range(steps):
        if use_surfactant:
            p_big = laplace_pressure(surfactant_tension(r_big), r_big)
            p_small = laplace_pressure(surfactant_tension(r_small), r_small)
        else:
            p_big = laplace_pressure(T_fixed, r_big)
            p_small = laplace_pressure(T_fixed, r_small)
        # ★ 气从高压流到低压：小肺泡(p大) → 大肺泡(p小)
        flow = (p_small - p_big) * dt * 0.01
        r_small -= flow
        r_big += flow
        r_small = max(r_small, 0.05)
    return r_big / r_small


# =================================================================
# 五、★★★ 弥散（Bohr 积分法）
# =================================================================
def capillary_transit_time(q_L_min: float, vc: float = VC_BLOOD) -> float:
    """★ t = Vc / Q（分钟）→ 转秒。静息 0.90 s，运动 0.225 s"""
    return vc / q_L_min * 60.0


def end_capillary_po2(pao2: float, dl: float = DL_REST,
                      q_L_min: float = 5.0, pvo2: float = PVO2,
                      cao2_fn=None) -> float:
    """
    ★ Bohr： (PA − Pc_end) = (PA − Pv) × exp(−DL·t/(Vc·β))
      β = 有效解离曲线斜率 mL O2/(L blood·mmHg)
      ★ 我用 (CcO2(PA) − CvO2)/(PA − Pv) 近似
    """
    t = capillary_transit_time(q_L_min) / 60.0     # 回分钟
    if cao2_fn is None:
        from core.vascular import o2_content
        cao2_fn = o2_content
    c_art = cao2_fn(pao2)
    c_ven = cao2_fn(pvo2)
    if abs(pao2 - pvo2) < 1e-9:
        return pao2
    beta = (c_art - c_ven) / (pao2 - pvo2)         # mL/(L·mmHg)
    if beta <= 0:
        beta = 0.78
    exponent = -dl * t / (VC_BLOOD * beta)
    exponent = max(exponent, -50.0)
    return pao2 - (pao2 - pvo2) * float(np.exp(exponent))


def diffusing_capacity_effective(dl: float, q_L_min: float,
                                 vc: float = VC_BLOOD) -> float:
    """★ 运动时 DL 会【升高】（毛细血管招募 + 扩张），REAL 静息25→运动50~80"""
    recruit = 1.0 + 0.6 * np.clip((q_L_min - 5.0) / 15.0, 0, 1)
    return dl * recruit


# =================================================================
# 六、★★★ 真分流 vs 弥散障碍（给氧反应相反）
# =================================================================
def mixed_arterial_o2(shunt: float, c_end: float, c_ven: float) -> float:
    """★ 分流方程：CaO2 = (1−fs)·CcO2 + fs·CvO2"""
    return (1.0 - shunt) * c_end + shunt * c_ven


def po2_from_content(c: float, pao2_guess: float = 100.0) -> float:
    """★ 从含量反解 PO2（二分，因为解离曲线非线性）"""
    from core.vascular import o2_content
    lo, hi = 0.0, 700.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if o2_content(mid) < c:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# =================================================================
# 七、★★★ 过度通气悖论（脑血流）
# =================================================================
def cerebral_blood_flow(paco2: float, cbf0: float = 1.0,
                        paco2_0: float = 40.0) -> float:
    """
    ★★ CO2 是脑血管最强的调节因子
      PaCO2 20 → CBF ×0.5；PaCO2 60 → CBF ×1.5（REAL 近似）
    """
    return cbf0 * (paco2 / paco2_0)


def o2_delivery_to_brain(pao2: float, paco2: float) -> float:
    """
    ★★★ 脑的氧输送 = CaO2 × CBF
      ★ 过度通气：CaO2 几乎不变（Hb 已饱和）× CBF 腰斩 = 净下降
    """
    from core.vascular import o2_content
    return o2_content(pao2) * cerebral_blood_flow(paco2)


# =================================================================
# 八、★ 呼吸控制
# =================================================================
def ventilatory_response(paco2: float, pao2: float,
                         co2_slope: float = 2.5,
                         paco2_set: float = 40.0,
                         hypoxic_threshold: float = 60.0,
                         hypoxic_gain: float = 1.0,
                         peripheral_blunted: bool = False) -> float:
    """
    ★ 通气驱动 = CO2 项（主） + 低氧项（次）
      CO2 项：slope × (PaCO2 − 40)，REAL 2~3 L/min/mmHg
      低氧项：PaO2 < 60 才显著
      peripheral_blunted：COPD 长期 CO2 潴留 → 中枢钝化
    """
    if peripheral_blunted:
        co2_slope = co2_slope * 0.2
    drive = co2_slope * (paco2 - paco2_set)
    if pao2 < hypoxic_threshold:
        drive += hypoxic_gain * (hypoxic_threshold - pao2) * 0.5
    return max(drive, 0.0)


# =================================================================
# 九、★ 高原
# =================================================================
def barometric_pressure(altitude_m: float) -> float:
    """★ 简化气压高度公式（REAL 海平面 760，珠峰 8848 → ~253）"""
    return 760.0 * np.exp(-altitude_m / 7400.0)


def altitude_case(altitude_m: float, paco2: float = 40.0):
    """★ 给定高度和 PACO2，算 PAO2"""
    pb = barometric_pressure(altitude_m)
    return pb, pio2(pb), pao2_alveolar(paco2, pb)


# =================================================================
# 十、★ 肺是【监测 + 执行】，不是限制
# =================================================================
class LungSense:
    """
    ★ 只读监测 —— 报告通气/换气状态与代价，不替它决定要不要呼吸
      呼吸本身是执行器（它会动），但这里只【算状态】
    """

    def __init__(self, dl: float = DL_REST, shunt: float = 0.02):
        self.dl = dl
        self.shunt = shunt
        self.log = []

    def observe(self, vt: float = VT, f: float = F_RESP,
                q_L_min: float = 5.0, fio2: float = FIO2_AIR,
                pb: float = PB_SEA) -> dict:
        """★ 一次呼吸状态观测"""
        va = alveolar_ventilation(vt, f)
        mv = minute_ventilation(vt, f)
        paco2 = paco2_alveolar(va)
        pao2 = pao2_alveolar(paco2, pb, fio2)
        dl_eff = diffusing_capacity_effective(self.dl, q_L_min)
        pc_end = end_capillary_po2(pao2, dl_eff, q_L_min)
        from core.vascular import o2_content
        c_end = o2_content(pc_end)
        c_ven = o2_content(PVO2)
        ca = mixed_arterial_o2(self.shunt, c_end, c_ven)
        pao2_art = po2_from_content(ca)
        rec = dict(va=va, mv=mv, deadspace=dead_space_fraction(vt),
                   paco2=paco2, pao2_alv=pao2, pao2_art=pao2_art,
                   pc_end=pc_end, cao2=ca,
                   cbf=cerebral_blood_flow(paco2),
                   o2_to_brain=o2_delivery_to_brain(pao2_art, paco2),
                   transit_s=capillary_transit_time(q_L_min))
        self.log.append(rec)
        return rec
