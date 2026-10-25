#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★49 循环层 —— 血管、血流、氧级联
================================================================
★ 承接 ★48：心脏把血【泵】出来，循环把血【送】到细胞
    ★★ 没有循环，心脏的 VO2max 只是个数字，到不了线粒体

★★★ 本轮要钉的核心悖论
    ★ 泊肃叶：Q ∝ r⁴  —— 半径是极强的杠杆（+10% 半径 → +46% 血流）
    ★★ 但血管【不能全身扩张】：
        局部（运动肌肉）扩张 → 该处血流↑↑，总外周阻力只略降，靠 CO 代偿
        全身扩张 → TPR 崩塌 → MAP 掉 → 灌注压不够 → 反而缺血
        ★ REAL 对应：脓毒性休克 / 过敏性休克 = 全身血管扩张 → 血压崩塌
    ★★★ 所以"扩张血管好"这个直觉只在【局部】成立

★★ 真参数（REAL）
    血容量 5 L        红细胞压积 Hct 0.45
    血压 120/80 mmHg  MAP ≈ 93（= DBP + 脉压/3）
    MAP = CO × TPR（欧姆定律类比）
    主动脉 d 2.5 cm，平均流速 ~17 cm/s，峰值 40~50
    毛细血管 d 7~10 μm，流速 0.5~1 mm/s（★ 总横截面积最大 → 最慢）
    红细胞过毛细血管 0.5~2 s
    全血粘度 3~4 cP，血浆 1.2 cP
    ★ 小动脉/微动脉是主要阻力部位（占总阻力 60~70%）
    剪切应力 10~20 dyn/cm²（1~2 Pa）→ 触发 eNOS 释放 NO
    PWV（脉搏波速度）：青年 5~8 m/s，老年 10~15（Moens-Korteweg）
    自动调节：脑/肾血流在 MAP 60~150 之间基本恒定

★★★ 氧级联（oxygen cascade）—— PO2 一路下降
    干燥空气 160 → 湿化气道 150 → 肺泡 ~100 → 动脉 95
    → 组织毛细血管 ~40 → 线粒体 1~10 mmHg
    ★ 每一级都是真实的压降，不是常数

★ 氧解离曲线（Hill 方程）
    SO2 = PO2^n / (P50^n + PO2^n)，n≈2.7，P50≈26.8 mmHg
    CaO2 = 1.34 × Hb × SO2 + 0.003 × PO2     Hb=15 g/dL
    → 动脉 SO2 0.975 → CaO2 ≈ 196 mL/L  ★ 与 ★48 的 CAO2=200 对上
    ★ Bohr 效应：pH↓ / CO2↑ → 曲线右移 → 组织更容易拿到氧
      Δlog10(P50)/ΔpH ≈ −0.48

★★★ 有氧 vs 无氧（本轮接回 ★第1步 能量本能）
    葡萄糖完全氧化 净 ~30~32 ATP，耗 6 O2  → 约 5 ATP / O2
    无氧糖酵解     净 2 ATP（不耗氧）
    ★ 效率差约 15 倍
    ★★ 所以"氧输送速率"就是【有氧功率上限】= 能量预算的物理天花板
       超出部分只能走无氧 → 低效 + 乳酸（氧债，事后要还）
"""
from __future__ import annotations
import numpy as np


# =================================================================
# 一、真参数（REAL）
# =================================================================
BLOOD_VOLUME = 5.0            # L
HCT = 0.45                    # 红细胞压积（REAL 0.40~0.50）
HB = 15.0                     # g/dL 血红蛋白（REAL 13~17）
HUFNER = 1.34                 # mL O2 / g Hb
SOL_O2 = 0.003                # mL O2 / dL / mmHg（溶解氧）
P50 = 26.8                    # mmHg
HILL_N = 2.7
BOHR = -0.48                  # Δlog10(P50)/ΔpH

ETA_PLASMA = 1.2e-3           # Pa·s
ETA_BLOOD = 3.5e-3            # Pa·s（REAL 3~4 cP）
RHO_BLOOD = 1060.0            # kg/m³

MAP_REST = 93.0               # mmHg（REAL ~93）
CO_REST = 5.0                 # L/min
TPR_REST = MAP_REST / CO_REST  # mmHg·min/L


# =================================================================
# 二、血管树：每级直径、数量、总横截面积、流速
# =================================================================
class VesselLevel:
    def __init__(self, name, d_cm, n, total_area_cm2, is_resistance=False):
        self.name = name
        self.d_cm = d_cm
        self.n = n
        self.area = total_area_cm2        # cm² 总横截面积
        self.is_resistance = is_resistance


def vessel_tree():
    """
    ★ 血管树：从主动脉到腔静脉
      ★★ 关键：总横截面积在【毛细血管】处最大 → 流速最慢
      ★ 这不是巧合：慢 = 交换有足够时间
    """
    return [
        VesselLevel("主动脉",   2.5,        1,    4.9),
        VesselLevel("大动脉",   0.5,       40,   20.0),
        VesselLevel("小动脉",   0.005,  1.0e6,  125.0, is_resistance=True),
        VesselLevel("微动脉",   0.0025, 4.0e7,  500.0, is_resistance=True),
        VesselLevel("毛细血管", 0.0008, 1.0e10, 1000.0),
        VesselLevel("小静脉",   0.003,  2.0e7,  570.0),
        VesselLevel("腔静脉",   3.0,        1,    7.1),
    ]


def velocity_cm_s(co_L_min: float, level: VesselLevel) -> float:
    """流速 = 流量 / 总横截面积"""
    q_cm3_s = co_L_min * 1000.0 / 60.0      # cm³/s
    return q_cm3_s / level.area


def reynolds(v_cm_s: float, d_cm: float,
             eta: float = ETA_BLOOD, rho: float = RHO_BLOOD) -> float:
    """Re = ρvd/η   —— <2000 层流；主动脉峰值可到 1500~4000"""
    return rho * (v_cm_s / 100.0) * (d_cm / 100.0) / eta


# =================================================================
# 三、★ 泊肃叶 r⁴ —— 血管调节的核心杠杆
# =================================================================
def poiseuille_flow(dp: float, r: float, L: float,
                    eta: float = ETA_BLOOD) -> float:
    """Q = π·ΔP·r⁴ /(8ηL)   （SI：m³/s）"""
    return np.pi * dp * r ** 4 / (8.0 * eta * L)


def resistance(r: float, L: float, eta: float = ETA_BLOOD) -> float:
    """R = 8ηL/(πr⁴)   ★★ r 的四次方在分母上"""
    return 8.0 * eta * L / (np.pi * r ** 4)


def flow_gain(r_ratio: float) -> float:
    """★★ 半径放大 r_ratio 倍 → 血流放大 r_ratio⁴ 倍（ΔP 不变时）"""
    return r_ratio ** 4


# =================================================================
# 四、★★ 局部 vs 全身扩张 —— 本轮核心悖论
# =================================================================
def tpr_of_beds(beds: dict) -> float:
    """
    ★ 并联血管床：1/R_total = Σ 1/R_i
      beds: {名字: (阻力R_i, 权重(静息血流占比))}
    """
    inv = sum(1.0 / r for r, _ in beds.values())
    return 1.0 / inv


def dilate_local(beds: dict, target: str, ratio: float) -> dict:
    """★ 只扩张一个床（代谢性/局部）"""
    out = {k: (v[0], v[1]) for k, v in beds.items()}
    if target in out:
        r, w = out[target]
        out[target] = (r / (ratio ** 4), w)     # ★ r↑ → R = R/ratio⁴
    return out


def dilate_all(beds: dict, ratio: float) -> dict:
    """★ 全部床一起扩张（全身性：脓毒/过敏/药物）"""
    return {k: (v[0] / (ratio ** 4), v[1]) for k, v in beds.items()}


def map_from(co: float, tpr: float) -> float:
    """★ MAP = CO × TPR（欧姆定律类比）"""
    return co * tpr


def perfusion_of_bed(map_: float, r_i: float) -> float:
    """★ 单个床的血流 = MAP / R_i（灌注压驱动）"""
    return map_ / r_i


# =================================================================
# 五、★ 自动调节：肌源性 + 代谢性
# =================================================================
def autoregulation(map_: float, lo: float = 60.0, hi: float = 150.0,
                   q_target: float = 1.0, gain_up: float = 3.0,
                   gain_dn: float = 2.0) -> float:
    """
    ★★ 血流自动调节：MAP 在 [lo,hi] 之间时，血流基本【恒定】
      机制：压力↑ → 肌源性收缩（血管缩，R↑，抵消压力↑）
           代谢物↑ → 舒张（R↓）
      超出范围 → 被动（压力依赖）
      REAL：脑/肾在 MAP 60~150 之间血流恒定
    """
    if map_ < lo:
        return q_target * (map_ / lo) ** gain_dn      # 低压：被动下降
    if map_ > hi:
        return q_target * (map_ / hi) ** gain_dn      # 高压：突破，被动上升
    return q_target                                    # ★ 平台：恒定


def myogenic_tone(map_: float, setpoint: float = 100.0,
                  k: float = 1.0, r_base: float = 1.0) -> float:
    """★ 肌源性反应：压力高于设定点 → 收缩（半径变小）"""
    return float(np.clip(r_base * (1.0 - k * (map_ - setpoint) / setpoint),
                         0.4, 1.6))


def metabolic_tone(demand: float, k: float = 0.5) -> float:
    """★ 代谢性：代谢需求↑ → 舒张（半径变大），但有上限（最大扩张）"""
    return float(np.clip(1.0 + k * demand, 1.0, 2.2))


def bed_radius(map_: float, demand: float) -> float:
    """★ 最终半径 = 肌源性 × 代谢性（两个机制叠加）"""
    return myogenic_tone(map_) * metabolic_tone(demand)


# =================================================================
# 六、★★ 氧级联 + 氧解离曲线
# =================================================================
def so2(po2: float, p50: float = P50, n: float = HILL_N) -> float:
    """★ Hill 氧解离曲线（sigmoid）"""
    po2 = max(po2, 0.0)
    return float(po2 ** n / (p50 ** n + po2 ** n))


def p50_bohr(ph: float = 7.4) -> float:
    """
    ★ Bohr 效应：pH↓（酸）→ P50↑ → 曲线右移 → 组织更容易拿到氧
      REAL：Δlog10(P50)/ΔpH ≈ −0.48（pH 降 0.1 → P50 升约 12%）
      ★ 我只实现 pH 项。CO2 项我第一版写了 `* (1.0 + 0.0*(...))`
        乘 0 = 恒等于没有 —— 那是【假实现】，已删除，不假装实现了
    """
    return P50 * 10 ** (BOHR * (ph - 7.4))


def o2_content(po2: float, hb: float = HB, ph: float = 7.4) -> float:
    """★ CaO2 = 1.34·Hb·SO2 + 0.003·PO2   （mL O2 / L 血）"""
    s = so2(po2, p50_bohr(ph))
    return HUFNER * hb * s * 10.0 + SOL_O2 * po2 * 10.0


def oxygen_cascade():
    """
    ★★★ PO2 一路下降（REAL 值）
      每一级压降都有物理原因，不是常数
    """
    return [
        ("干燥空气", 160.0),
        ("湿化气道", 150.0),
        ("肺泡",     100.0),
        ("动脉血",    95.0),
        ("组织毛细血管", 40.0),
        ("线粒体",    5.0),
    ]


def fick_delivery(co_L_min: float, cao2: float, cvo2: float) -> float:
    """★ Fick：VO2 = CO × (CaO2 − CvO2)   mL O2/min"""
    return co_L_min * (cao2 - cvo2)


# =================================================================
# 七、★★★ 有氧 / 无氧 —— 接回第1步能量本能
# =================================================================
ATP_PER_O2 = 5.0              # 有氧：约 5 ATP / O2 分子（30 ATP / 6 O2）
O2_MOL_PER_L = 1.0 / 22.4     # mol / L（标准状态）
ATP_YIELD_AEROBIC = 30.0      # ATP / 葡萄糖
ATP_YIELD_ANAEROBIC = 2.0     # ATP / 葡萄糖（糖酵解）
O2_PER_GLUCOSE = 6.0


def aerobic_power_vo2(vo2_ml_min: float) -> float:
    """★ 有氧 ATP 产生速率（mol ATP/min）"""
    mol_o2 = vo2_ml_min / 1000.0 * O2_MOL_PER_L
    return mol_o2 * ATP_PER_O2


def atp_supply(vo2_max_ml_min: float, demand_atp: float):
    """
    ★★ 供能切换
      需求 ≤ 有氧上限 → 全走有氧（高效，30 ATP/葡萄糖）
      需求 > 有氧上限 → 超出部分走无氧（2 ATP/葡萄糖，效率 1/15）
      ★ 返回有氧占比、乳酸（氧债）速率、综合效率
    """
    cap = aerobic_power_vo2(vo2_max_ml_min)
    if demand_atp <= cap:
        return 1.0, 0.0, 1.0
    aer = cap
    ana = demand_atp - cap
    # ★ 效率比：无氧每单位 ATP 需要 15 倍葡萄糖
    debt = ana * (ATP_YIELD_AEROBIC / ATP_YIELD_ANAEROBIC - 1.0)
    eff = aer / demand_atp
    return float(aer / demand_atp), float(debt), float(eff)


# =================================================================
# 八、★ 剪切力 → NO（血管的训练适应）
# =================================================================
def shear_stress(v_cm_s: float, d_cm: float, eta: float = ETA_BLOOD) -> float:
    """
    ★ 管壁剪切应力 τ = 4ηQ/(πr³) = 32ηQ/(πd³) = 8η·v_mean/d
      （dyn/cm²；1 Pa = 10 dyn/cm²）
      ★★ REAL 区间要看血管级别，不是一个数：
         主动脉 1~7 dyn/cm²（大管、流速虽快但直径大）
         小动脉/微循环 10~20 dyn/cm²
         ★ 我第一版只写"10~20"是错的 —— 那是微循环的值
    """
    v = v_cm_s / 100.0
    d = d_cm / 100.0
    pa = 8.0 * eta * v / d
    return pa * 10.0


def no_release(tau_dyn: float, tau_set: float = 15.0) -> float:
    """
    ★ 剪切应力↑ → eNOS → NO → 血管舒张
      ★ REAL：运动时血流↑ → 剪切力↑ → NO↑ → 血管舒张能力增强
      ★ 这是"血管也能被训练"的机制，与 ★48 心脏训练呼应
    """
    return float(np.tanh(max(tau_dyn, 0.0) / tau_set))


def pwv(age: int = 30) -> float:
    """★ 脉搏波速度（Moens-Korteweg）：随年龄增加 = 动脉硬化
       REAL：青年 5~8 m/s，老年 10~15"""
    return 4.5 + 0.11 * age


# =================================================================
# 九、★★★ 闭环：循环 → 能量（接第1步本能）
# =================================================================
# =================================================================
# 九、★★★ 循环是【监测工具】，不是【限制】
# =================================================================
# ★★★ 用户原则（2026-10-24）：
#     "是一个监测工具。你写进去就是限制它。"
#
#   ★ 血管/循环的作用是【感知】：测血压、测血流、测氧输送、测氧债
#     —— 它【报告】现在怎么样，不【决定】能做什么
#
#   ★★ 如果把它写成硬性约束（超上限就拒绝/停机），就是在限制：
#        · 它永远到不了上限之外，因而永远发现不了氧债可偿还
#        · 它学不会"短暂透支 + 事后还"这个真实存在的策略
#        · 上限一旦写错，它连纠正的机会都没有（被卡在错误边界内）
#
#   ★★★ 所以这里只提供 Sense（只读），Constraint 仅作为【对照反例】保留
# =================================================================
class CirculatorySense:
    """
    ★ 只读监测器 —— 报告状态，不执行任何动作
      ★ 唯一的输出是【描述】，没有"拒绝""停机""限流"
    """

    def __init__(self, heart, weight: float = 70.0, hb: float = HB):
        self.heart = heart
        self.weight = weight
        self.hb = hb
        self.debt = 0.0
        self.vo2 = 0.0
        self.log = []

    def cao2(self, ph: float = 7.4) -> float:
        return o2_content(95.0, self.hb, ph)

    def cvo2(self, ph: float = 7.4) -> float:
        return o2_content(40.0, self.hb, ph)

    def vo2_max(self) -> float:
        co = self.heart.co_max()
        return fick_delivery(co, self.cao2(), self.heart.cvo2)

    def atp_capacity(self) -> float:
        return aerobic_power_vo2(self.vo2_max())

    # ★ 只有 observe，没有 enforce
    def observe(self, demand_atp: float, ph: float = 7.4) -> dict:
        """★ 观测一次供需：返回描述，不改变任何外部状态"""
        frac, debt, eff = atp_supply(self.vo2_max(), demand_atp)
        self.debt += debt
        rec = dict(demand=demand_atp, aerobic_frac=frac,
                   debt_added=debt, debt_total=self.debt,
                   efficiency=eff, vo2max=self.vo2_max(),
                   headroom=demand_atp / max(self.atp_capacity(), 1e-12))
        self.log.append(rec)
        return rec

    def repay(self, extra_vo2: float) -> float:
        """★ 还氧债（EPOC）—— 这是它【自己】发现的策略，不是被允许才有的"""
        gain = aerobic_power_vo2(extra_vo2)
        used = min(gain, self.debt)
        self.debt -= used
        return used


class ConstraintGate:
    """
    ★★ 反例对照 —— 把循环写成【限制】会发生什么
       ⚠️ 这个类存在的唯一目的是【被对照证明有害】
          正常路径请用 CirculatorySense
    """

    def __init__(self, sense: CirculatorySense, hard: bool = True):
        self.sense = sense
        self.hard = hard
        self.rejected = 0
        self.allowed = 0

    def try_act(self, demand_atp: float) -> bool:
        """★ 超过有氧上限就拒绝 —— 这就是把监测写成限制"""
        cap = self.sense.atp_capacity()
        if self.hard and demand_atp > cap:
            self.rejected += 1
            return False
        self.allowed += 1
        return True


# ★ 兼容旧名（★49 用过）—— 指向 Sense，语义已改为只读
CirculatoryEnergy = CirculatorySense
