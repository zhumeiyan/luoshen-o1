#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★52 心肺耦合 —— V̇/Q̇ 匹配
================================================================
★ 承接 ★48(心脏) + ★49(循环) + ★51(肺)
    ★★ 前三个是分别建的。肺把氧放进血，心脏把血泵出去，
       但【放进去的那口血和泵出去的那口血是不是同一口】没人管
    ★★★ 这一层就是管这个：通气 V̇ 和血流 Q̇ 的匹配

★★★ 核心方程（单元级氧守恒）
    对每个肺单元：
      通气侧：V̇O2 = V̇A × (FiO2 − FAO2) × 1000
              FAO2 = PAO2 / (Pb − PH2O)
      灌注侧：V̇O2 = Q̇ × (CcO2(PAO2) − CvO2)
    联立（记 r = V̇A/Q̇）：
      ★ 1000 × r × (PiO2 − PAO2)/(Pb − PH2O) = CcO2(PAO2) − CvO2
    ★ 左边随 PAO2 下降而上升，右边随 PAO2 下降而下降 → 唯一交点

★★ 混合必须按【含量】加权，不能按【分压】加权
    ★★ 解离曲线非线性 → 平均 PO2 ≠ PO2 的平均值
    真实做法：CaO2 = Σ wᵢ × CcO2ᵢ，再反解 PaO2
    ★ 这是可证伪的：两种算法结果不同，且只有含量加权是REAL

★★★ 判据级对照 1：均匀肺 vs 真实 V/Q 分布
    ★ 均匀肺（所有单元 V/Q 相同）算出的 PaO2 偏【高】
    ★ 真实肺有重力梯度（肺尖 ≈3.3，肺底 ≈0.6）+ 少量真分流
      → 低 V/Q 区的血落在解离曲线【陡峭段】，含量显著低
      → 高 V/Q 区落在【平台段】，含量几乎不涨
      ★★ 所以不均【必然】拉低平均 —— 这是曲线非线性决定的

★★★ 判据级对照 2：低氧性肺血管收缩 HPV 是双刃剑
    局部缺氧（痰堵/肺不张）：HPV 把血从坏区引流到好区 → PaO2 保住 ★有益
    全肺缺氧（高原/弥漫性肺病）：全肺收缩 → 肺动脉高压 → 右心负荷 ★有害
    ★★ 同一个机制，范围不同，结果相反 —— 可证伪

★★★ 判据级对照 3：分流 vs 死腔，O2 与 CO2 反应【相反】
    分流（V̇/Q̇ → 0）：PaO2 大幅下降，但 PaCO2 正常甚至↓
    ★  因为缺氧驱动化学感受器 → 过度通气 → 把 CO2 吹出去
    死腔（V̇/Q̇ → ∞）：PaCO2 升高，PaO2 下降较轻
    ★  因为那部分通气白做了，CO2 排不掉

★★ 判据级对照 4：体位
    直立：重力使肺底血流多、通气也多，但血流梯度【更陡】
          → 肺底 V/Q 低、肺尖 V/Q 高
    仰卧：重力方向变了（前后），梯度变缓 → V/Q 分布更均匀

★★ 判据级对照 5：运动时的心肺匹配
    CO 从 5 → 20 L/min，VA 从 4.2 → 60+ L/min
    ★ V/Q 从 0.84 升到 ~3（通气涨得比血流快）
    ★ 且静息时未开放的肺尖毛细血管被招募 → 弥散面积↑

⚠️ 贯彻 ★50 原则：这是【监测 + 调节】，不是限制
    ★ HPV 确实会【动】（它是调节器），但下面的函数只算状态与代价
"""
from __future__ import annotations
import numpy as np

PB = 760.0
PH2O = 47.0
DRY = PB - PH2O          # 713 mmHg
PIO2 = 149.2             # 干空气 PiO2

LAP = 8.0                # mmHg 左房压
RAP = 4.0                # mmHg 右房压


def o2_content_curve(po2: float, hb: float = 15.0):
    """★ CaO2 = 1.34 × Hb × SO2 + 0.003 × PO2   (mL/L，PO2 用 mmHg)"""
    so2 = so2_hill(po2)
    return 1.34 * hb * so2 * 10.0 + 0.003 * po2 * 10.0


def so2_hill(po2: float) -> float:
    """★ Hill 型解离曲线（P50=26.8，n=2.7）"""
    if po2 <= 0:
        return 0.0
    return float(po2 ** 2.7 / (po2 ** 2.7 + 26.8 ** 2.7))


def po2_from_content(c: float) -> float:
    """★ 从含量反解 PO2（二分）"""
    lo, hi = 0.0, 700.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if o2_content_curve(mid) < c:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# =================================================================
# 一、★★ 单元求解器
# =================================================================
def solve_unit_pao2(va_q: float, pio2: float = PIO2,
                    cvo2: float = None, hb: float = 15.0):
    """
    ★ 解  1000·r·(PiO2 − PAO2)/DRY = CcO2(PAO2) − CvO2
      返回 (PAO2, CcO2)，无解返回 (None, None)
    """
    if cvo2 is None:
        cvo2 = o2_content_curve(40.0, hb)
    if va_q <= 0:
        # ★ V̇/Q̇ = 0 → 真分流：血不经过通气，末端 = 混合静脉血
        return None, cvo2

    def f(pa):
        return 1000.0 * va_q * (pio2 - pa) / DRY - (o2_content_curve(pa, hb) - cvo2)

    lo, hi = 0.0, pio2
    # ★ 单调性：f(0) > 0（通气侧最大），f(PiO2) < 0（灌注侧最大）
    if f(lo) < 0 or f(hi) > 0:
        return None, None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    pa = (lo + hi) / 2.0
    return pa, o2_content_curve(pa, hb)


# =================================================================
# 二、★★ West 重力梯度：V/Q 分布
# =================================================================
def west_zones(n: int = 9, apex_vq: float = 3.3, base_vq: float = 0.45,
               posture: str = "upright"):
    """
    ★ 沿重力从肺尖到肺底，V/Q 递减
      ★ 血流权重也随重力递增（肺底血多）
      posture='upright'  梯度陡（REAL 肺尖3.3 / 肺底0.6）
      posture='supine'   梯度缓（前后径更短，重力效应弱）
    """
    if posture == "supine":
        apex_vq, base_vq = 1.9, 0.75      # ★ 分布更均匀
    frac = np.linspace(0.0, 1.0, n)
    # ★ 几何插值（V/Q 沿肺是近似指数的）
    vq = apex_vq * (base_vq / apex_vq) ** frac
    # ★ 血流权重：随重力递增
    w = 0.4 + 1.6 * frac
    w = w / w.sum()
    return vq, w


# =================================================================
# 三、★★★ 全局混合
# =================================================================
def mix_arterial(vq_list, w_list, shunt: float = 0.02,
                 pio2: float = PIO2, cvo2: float = None, hb: float = 15.0):
    """
    ★★ CaO2 = (1−fs)·Σwᵢ·CcO2ᵢ + fs·CvO2
      ★ 必须按【含量】加权（解离曲线非线性）
      shunt：真分流（支气管静脉 + 心最小静脉），REAL 2~5%
    """
    if cvo2 is None:
        cvo2 = o2_content_curve(40.0, hb)
    vq_list = np.asarray(vq_list, dtype=float)
    w_list = np.asarray(w_list, dtype=float)
    w_list = w_list / w_list.sum()

    contents, pao2s, weights = [], [], []
    for vq, w in zip(vq_list, w_list):
        pa, cc = solve_unit_pao2(vq, pio2, cvo2, hb)
        if pa is None:
            continue
        contents.append(cc); pao2s.append(pa); weights.append(w)
    contents = np.array(contents); pao2s = np.array(pao2s)
    weights = np.array(weights); weights = weights / weights.sum()

    ca_cap = float(np.sum(weights * contents))          # ★ 含量加权
    pa_weighted = float(np.sum(weights * pao2s))        # ✗ 分压加权（错误对照）
    ca = (1.0 - shunt) * ca_cap + shunt * cvo2
    pao2 = po2_from_content(ca)

    return dict(pao2=pao2, cao2=ca, cao2_capillary=ca_cap,
                pao2_content_weighted=pao2,
                pao2_pressure_weighted=pa_weighted,   # ★ 两种算法的差
                units=list(zip(vq_list, pao2s, contents, weights)))


# =================================================================
# 四、★★★ HPV 低氧性肺血管收缩
# =================================================================
def hpv_factor(pao2_alv: float, p50: float = 30.0,
               max_gain: float = 0.85) -> float:
    """
    ★ 局部肺泡 PO2 越低，该区血管收缩越强（血流权重打折）
      REAL：PO2 从 100 降到 40，局部血流可降到 50% 以下
      ★★ 返回【血流保留比例】 0~1
    """
    if pao2_alv >= 100.0:
        return 1.0
    x = np.clip((100.0 - pao2_alv) / (100.0 - 25.0), 0.0, 1.0)
    return 1.0 - max_gain * (x ** 1.6)


def redistribute(vq_list, w_list, pio2: float = PIO2,
                 cvo2: float = None, hb: float = 15.0,
                 hpv_on: bool = True):
    """
    ★★ HPV 重定向血流：先算各区肺泡 PO2 → 按 hpv_factor 打折 → 重归一
      ★ 打折省下的血流被按比例分给通气好的区
    """
    vq_list = np.asarray(vq_list, dtype=float)
    w0 = np.asarray(w_list, dtype=float); w0 = w0 / w0.sum()
    if cvo2 is None:
        cvo2 = o2_content_curve(40.0, hb)

    pa_list = []
    for vq in vq_list:
        pa, _ = solve_unit_pao2(vq, pio2, cvo2, hb)
        pa_list.append(pa if pa is not None else 0.0)
    pa_list = np.array(pa_list)

    if not hpv_on:
        return w0, pa_list, np.ones_like(w0)

    f = np.array([hpv_factor(p) for p in pa_list])
    w_new = w0 * f
    w_new = w_new / w_new.sum()
    return w_new, pa_list, f


# =================================================================
# 五、★ 肺动脉压与右心负荷
# =================================================================
def pulmonary_pressure(co: float, pvr: float = 1.4, lap: float = LAP) -> float:
    """★ Ohm 定律：mPAP = LAP + CO × PVR
       正常 CO=5, PVR=1.4 → mPAP = 15 mmHg  (REAL 10~20)"""
    return lap + co * pvr


def hpv_global_pvr(pao2_alv_mean: float, base_pvr: float = 1.4,
                   max_pvr: float = 5.0) -> float:
    """
    ★★ 全肺缺氧 → 全肺血管收缩 → PVR 升高
      PO2 100 → PVR 1.4（正常）
      PO2  40 → PVR 最高到 5.0（REAL 高原/COPD 肺动脉高压）
    """
    x = np.clip((100.0 - pao2_alv_mean) / 60.0, 0.0, 1.0)
    return base_pvr + (max_pvr - base_pvr) * (x ** 1.3)


def rv_work(mPAP: float, co: float, rap: float = RAP) -> float:
    """★ 右心做功 ∝ (mPAP − RAP) × CO"""
    return max(mPAP - rap, 0.0) * co


# =================================================================
# 六、★ 死腔 vs 分流（CO2 侧）
# =================================================================
def arterial_pco2(va_effective: float, vco2: float = 200.0) -> float:
    """★ PaCO2 = 0.863 × VCO2 / VA_effective"""
    if va_effective <= 1e-6:
        return float("inf")
    return 0.863 * vco2 / va_effective


def alveolar_dead_space(vt: float, f: float, vd_anat: float = 0.15,
                        vd_alv: float = 0.0):
    """★ 总死腔 = 解剖死腔 + 肺泡死腔（有通气无灌注的部分）"""
    vd_tot = vd_anat + vd_alv
    va = max(vt - vd_tot, 0.0) * f
    return va, vd_tot / vt


# =================================================================
# 七、★ 监测器（★50 原则：只报告，不限制）
# =================================================================
class CardiopulmonarySense:
    """★ 只读监测 —— 报告 V/Q 匹配状态与代价"""

    def __init__(self, n: int = 9, shunt: float = 0.02, hb: float = 15.0):
        self.n = n
        self.shunt = shunt
        self.hb = hb
        self.log = []

    def observe(self, posture: str = "upright", hpv_on: bool = True,
                co: float = 5.0, va_total: float = 4.2,
                pio2: float = PIO2, vd_alv: float = 0.0,
                vt: float = 0.5, f: float = 12.0) -> dict:
        vq, w = west_zones(self.n, posture=posture)
        q_total = co
        # ★ 各单元的 V̇A/Q̇ 由分布给出，总 VA 由外部给（用于 CO2 侧）
        w_new, pa_list, f_hpv = redistribute(vq, w, pio2, None, self.hb, hpv_on)
        cvo2 = o2_content_curve(40.0, self.hb)
        res = mix_arterial(vq, w_new, self.shunt, pio2, cvo2, self.hb)

        va_eff, vd_frac = alveolar_dead_space(vt, f, 0.15, vd_alv)
        paco2 = arterial_pco2(va_eff)

        # ★ 肺动脉压：用全局平均肺泡 PO2 驱动
        pa_mean = float(np.mean(pa_list))
        pvr = hpv_global_pvr(pa_mean) if hpv_on else 1.4
        mpap = pulmonary_pressure(co, pvr)

        rec = dict(pao2=res["pao2"], cao2=res["cao2"], paco2=paco2,
                   pa_alv_mean=pa_mean, vq_spread=float(vq.max() / vq.min()),
                   vd_fraction=vd_frac, va_eff=va_eff,
                   mpap=mpap, pvr=pvr, rv_work=rv_work(mpap, co),
                   hpv_retention=float(np.min(f_hpv)))
        self.log.append(rec)
        return rec
