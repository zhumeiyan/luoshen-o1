#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★48 心脏层 —— 可以训练强度
================================================================
★★★ 用户指令
    "你可以那个训那个训练那个心脏强度。"

★★ 心脏跟骨骼肌根本不同（本轮要钉的第一件事）
    骨骼肌  可以完全休息；靠【招募更多纤维】加大力量
    心脏    ★ 永远不能停 —— 它的"休息"只是舒张期
            ★ 几乎每根纤维每次都全力收缩 —— 靠前负荷 + 心率调节
    ★★ 所以"训练心脏"改变的不是"收缩得更有力"，而是：
        ① 心室腔更大（EDV↑，离心性肥大）
        ② 收缩性↑（EF↑）
        ③ 静息心率↓（自主神经平衡改变）
        ④ ★★ 储备↑ —— 静息更省力，需要时更能输出

★★★ 核心悖论（与 ★28 转椅悖论同构）
    ★ 冠状动脉只在【舒张期】被灌注（收缩期心肌挤压血管 → 血流≈0）
    → 心率越快，舒张期占比越小
    → 心率超过某点，冠脉供需失衡 → 心输出量反而【下降】
    → ★★ 存在【最优心率】，不是越快越好

★ 真参数（REAL）
    静息心率 60~100（运动员 40~60）    每搏输出量 SV ~70 mL（运动员 100~120）
    心输出量 CO ~5 L/min 静息；最大 20~25（运动员 35~40）
    射血分数 EF 0.55~0.70              EDV ~120 mL
    收缩期随心率缩短但不按比例（t_sys ≈ 0.30·√RR）
    VO2max 普通 35~45，运动员 60~85 mL/kg/min
    Fick：VO2 = CO × (CaO2 − CvO2)，CaO2≈200，极限时 CvO2→50
    冠脉血流储备 CFR：运动时可扩张 3~5 倍

★ 训练适应（REAL）
    有氧 →【离心性】肥大：腔扩大（EDV↑）为主
    力量 →【向心性】肥大：室壁增厚，腔不大   ★ 两者不同，不能混
    8~12 周见效；停训数周回退（detraining）
    HRV↑（副交感增强）；运动后 1 分钟心率恢复 HRR 运动员 >30 次/分

★★ 训练动力学：冲量-响应（Banister 类）+ 超量恢复
    fitness ↑慢（tau 30 天）  fatigue ↑快、消退快（tau 3 天）
    performance = fitness − fatigue
    ★★ 自带反直觉结论：
        练完【立刻】测，表现是【下降】的（疲劳 > 适应）
        等疲劳消退、适应还在 → 才出现【超量恢复】峰值
        ★ 所以"练完马上测有效"是错的 —— 可验证
"""
from __future__ import annotations
import numpy as np


# =================================================================
# 一、真参数（REAL）
# =================================================================
HR_REST_SEDENTARY = 72.0      # 久坐者静息心率（REAL 60~100）
HR_REST_TRAINED = 48.0        # 运动员（REAL 40~60）
T_SYS_REF = 0.30              # 参考收缩期（RR=1.0s 时）
FILL_TAU = 0.14               # 充盈时间常数（★ 标定过，见下）

EDV_REST_SED = 120.0          # 静息舒张末容积（REAL ~120）
EDV_REST_TRAINED = 170.0      # 运动员静息 EDV（REAL 150~200）
EDV_STRUCT_SED = 220.0        # 前负荷极限（结构上限）
EDV_STRUCT_TRAINED = 300.0
EDV_OPT = 170.0               # Starling 曲线的 EF 最优点
EF_MAX_SED = 0.61             # 基础收缩性
EF_MAX_TRAINED = 0.70
SYMP_MAX = 1.30               # 交感对收缩性的最大增强（饱和）
FAT_CRIT = 0.50               # ★ 疲劳临界：超过此值适应被抑制（过度训练）
CFR = 3.5                     # 冠脉血流储备（REAL 3~5）

CAO2 = 200.0                  # mL/L
CVO2_SED = 55.0               # 久坐者极量时静脉血氧 → 差 145
CVO2_TRAINED = 38.0           # 运动员 → 差 162
WEIGHT = 70.0                 # kg


def hr_max(age: int = 30) -> float:
    return 220.0 - age


# =================================================================
# 二、心动周期 —— ★ 收缩期缩短但不按比例
# =================================================================
def cycle(hr: float) -> tuple:
    """
    ★ T = 60/HR；t_sys = 0.30·√RR（Bazett 类经验式）
      ★★ 关键：t_sys 缩短得比 T 慢 → 【舒张期被压缩得更狠】
      HR 60 : T=1.000  收缩 0.300  舒张 0.700
      HR 190: T=0.316  收缩 0.169  舒张 0.147   ← 舒张只剩 47%
    """
    hr = max(hr, 1e-6)
    T = 60.0 / hr
    rr = T
    t_sys = T_SYS_REF * np.sqrt(rr)
    if t_sys >= T:
        t_sys = T * 0.95
    return T, t_sys, T - t_sys


def filling_fraction(hr: float, tau: float = FILL_TAU) -> float:
    """★ 充盈完成度 = 1 − exp(−t_dia/tau) —— 心率不能无限快的物理原因"""
    _, _, t_dia = cycle(hr)
    return float(1.0 - np.exp(-max(t_dia, 0.0) / tau))


def preload(hr: float, hr_rest: float = HR_REST_SEDENTARY,
            hr_peak: float = 190.0) -> float:
    """
    ★ 前负荷：运动时代谢需求↑ → 静脉回流↑、心房收缩增强
      → 可充盈到的容积上限【本身】也升高
    """
    return float(np.clip((hr - hr_rest) / max(hr_peak - hr_rest, 1e-6), 0.0, 1.0))


def sympathetic(hr: float, hr_rest: float = HR_REST_SEDENTARY,
                sat_at: float = 160.0, smax: float = SYMP_MAX) -> float:
    """★ 交感增强收缩性，但在 ~160 bpm 饱和（★ 不再升高，这是关键）"""
    return float(1.0 + (smax - 1.0) * np.clip((hr - hr_rest) /
                                              max(sat_at - hr_rest, 1e-6), 0.0, 1.0))


def frank_starling(edv: float, ef_max: float = EF_MAX_SED) -> float:
    """
    ★ Starling 曲线：前负荷↑ → EF↑，但【过度拉伸会下降】
      ★ x = edv/edv_opt，ef = ef_max·(1 − 0.45(x−1)²)
      ★ 这是"心脏不能无限扩张"的机制（心衰时走到下行支）
    """
    x = edv / EDV_OPT
    return float(np.clip(ef_max * (1.0 - 0.45 * (x - 1.0) ** 2), 0.05, 0.92))


def stroke_volume(hr: float, edv_rest: float = EDV_REST_SED,
                  edv_struct: float = EDV_STRUCT_SED,
                  ef_max: float = EF_MAX_SED,
                  hr_rest: float = HR_REST_SEDENTARY) -> tuple:
    """
    ★ SV = EDV × EF
      EDV = min(可用容积) × 充盈完成度
      可用容积 = edv_rest + (edv_struct − edv_rest)·preload
    """
    avail = edv_rest + (edv_struct - edv_rest) * preload(hr, hr_rest)
    edv = avail * filling_fraction(hr)
    ef = frank_starling(edv, ef_max) * sympathetic(hr, hr_rest)
    ef = float(np.clip(ef, 0.05, 0.92))
    return edv * ef, edv, ef


def cardiac_output(hr: float, **kw) -> float:
    sv, _, _ = stroke_volume(hr, **kw)
    return hr * sv / 1000.0


def optimal_hr(lo: float = 60.0, hi: float = 230.0, **kw) -> float:
    """★★ 存在最优心率 —— CO 在此处最大，再快反而下降"""
    hrs = np.linspace(lo, hi, 500)
    cos = [cardiac_output(h, **kw) for h in hrs]
    return float(hrs[int(np.argmax(cos))])


# =================================================================
# 三、★★★ 冠脉灌注悖论
# =================================================================
def coronary_supply(hr: float, dilation: float = CFR) -> float:
    """
    ★ 冠脉只在舒张期灌注
      每搏灌注 ∝ t_dia；每分钟灌注 = 每搏 × 心率 × 扩张倍数
    """
    _, _, t_dia = cycle(hr)
    dil = 1.0 + (dilation - 1.0) * preload(hr)
    return t_dia * (hr / 60.0) * dil


def coronary_demand(hr: float, hr_rest: float = HR_REST_SEDENTARY) -> float:
    """★ 心肌耗氧 ∝ 心率（以静息为基准做归一化，使静息比≈1）"""
    base = coronary_supply(hr_rest) / (hr_rest / hr_rest)
    return hr / hr_rest * base


def coronary_ratio(hr: float, **kw) -> float:
    """★ 供需比：<1 = 供不应求 = 缺血"""
    return coronary_supply(hr, **kw) / max(coronary_demand(hr), 1e-9)


# =================================================================
# 四、Fick 方程 → VO2max
# =================================================================
def vo2max(co_max: float, cvo2: float = CVO2_SED,
           weight: float = WEIGHT) -> float:
    """★ VO2 = CO × (CaO2 − CvO2) → mL/kg/min"""
    return co_max * (CAO2 - cvo2) / weight


# =================================================================
# 五、★★ 可训练的心脏
# =================================================================
class Heart:
    def __init__(self, fitness: float = 0.0, fatigue: float = 0.0,
                 k_fit: float = 0.011, k_fat: float = 0.060,
                 tau_fit: float = 30.0, tau_fat: float = 3.0,
                 age: int = 30, weight: float = WEIGHT):
        self.fitness = fitness
        self.fatigue = fatigue
        self.k_fit, self.k_fat = k_fit, k_fat
        self.tau_fit, self.tau_fat = tau_fit, tau_fat
        self.age = age
        self.weight = weight
        self.history = []
        self.adapt()

    # ---- ★ 结构适应：fitness → 真实解剖改变（有氧 = 离心性） ----
    def adapt(self):
        f = max(0.0, self.fitness)
        t = np.tanh(f)
        self.edv_rest = EDV_REST_SED + (EDV_REST_TRAINED - EDV_REST_SED) * t
        self.edv_struct = EDV_STRUCT_SED + (EDV_STRUCT_TRAINED - EDV_STRUCT_SED) * t
        self.ef_max = EF_MAX_SED + (EF_MAX_TRAINED - EF_MAX_SED) * t
        self.hr_rest = HR_REST_SEDENTARY - (HR_REST_SEDENTARY - HR_REST_TRAINED) * np.tanh(f * 0.9)
        self.cvo2 = CVO2_SED - (CVO2_SED - CVO2_TRAINED) * t

    def _kw(self):
        return dict(edv_rest=self.edv_rest, edv_struct=self.edv_struct,
                    ef_max=self.ef_max, hr_rest=self.hr_rest)

    def sv_rest(self):
        sv, _, _ = stroke_volume(self.hr_rest, **self._kw())
        return sv

    def co_rest(self):
        return cardiac_output(self.hr_rest, **self._kw())

    def co_max(self):
        return cardiac_output(hr_max(self.age), **self._kw())

    def vo2max(self):
        return vo2max(self.co_max(), self.cvo2, self.weight)

    def optimal_hr(self):
        return optimal_hr(**self._kw())

    def reserve(self):
        """★★ 储备 = 最大/静息 —— 训练真正提高的是这个"""
        return self.co_max() / max(self.co_rest(), 1e-9)

    def performance(self):
        return self.fitness - self.fatigue

    def step(self, load: float):
        """
        ★ 一天：施加负荷
          fitness ↑慢、衰减慢（tau 30d）；fatigue ↑快、消退快（tau 3d）
          ★★ 这个时间尺度差，就是【超量恢复】能出现的唯一原因

          ★★★ 过度训练机制（overtraining syndrome）
            适应速率被疲劳抑制：k_eff = k_fit·max(0, 1 − fatigue/FAT_CRIT)
            ★ 疲劳超过临界 → 【适应完全停止甚至倒退】
            ★ REAL：持续超负荷不休息 = 过度训练综合征，表现反而下降
            ★ 没有这一项，线性模型会得出"练得越多越好"的错误结论
        """
        gate = max(0.0, 1.0 - max(0.0, self.fatigue) / FAT_CRIT)
        self.fitness += self.k_fit * load * gate - self.fitness / self.tau_fit
        self.fatigue += self.k_fat * load - self.fatigue / self.tau_fat
        self.adapt()
        self.history.append((load, self.fitness, self.fatigue,
                             self.performance(), gate))
        return self.performance()

    def detrain(self, days: int):
        for _ in range(days):
            self.step(0.0)


# =================================================================
# 六、★ 自主训练策略（靠自己的状态信号调节）
# =================================================================
def choose_load(heart: Heart, base: float = 1.0,
                penalty: float = 2.5) -> float:
    """
    ★ 闭环：疲劳高就减量，疲劳低就加量
      ★ 不靠外部课表，靠自身状态 —— 与 ★22 自修改、★39 自学习同构
    """
    load = base * (1.0 - penalty * np.tanh(max(0.0, heart.fatigue)))
    return float(np.clip(load, 0.0, 2.0))


def adaptive_base(heart: Heart, base: float, prev_metric: float,
                  step: float = 0.10, patience: int = 14,
                  day: int = 0) -> tuple:
    """
    ★★ 让洛神【自己搜索】训练强度，而不是我替它设 base
      ★ 每 patience 天评估一次：指标（VO2max）还在涨 → 加量；不涨 → 减量
      ★ 与 ★38 的线搜索同构：不靠我拍脑袋，靠它自己的反馈
      ★★ 起因：固定 base 的自主策略【输了】（见 ★48 判据）
         根因是纯疲劳负反馈太保守 —— 它不知道"适度疲劳是正常的"
    """
    if day == 0 or day % patience != 0:
        return base, prev_metric
    cur = heart.vo2max()
    if cur > prev_metric + 1e-6:
        base += step          # 还在涨 → 加量
    else:
        base -= step          # 不涨了 → 减量
    base = float(np.clip(base, 0.1, 3.0))
    return base, cur
