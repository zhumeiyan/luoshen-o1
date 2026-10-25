#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
耳朵：按真人听觉器官组成 + 怎么接大脑，一层一层拆
（与 eye_anatomy / vocal_anatomy 完全同构）
================================================================

★ 声音走的路（REAL）：
    外耳  耳廓 pinna + 外耳道 ~25 mm（1/4 波长共振 → 约 3 kHz 增益约 10~15 dB）
      ↓
    中耳  鼓膜 → 三块听小骨（锤骨 malleus / 砧骨 incus / 镫骨 stapes）
            ★ 阻抗匹配：空气→耳蜗液体，增益约 20~25 dB（否则全反射）
      ↓
    内耳  耳蜗 cochlea，约 35 mm，卷约 2.5 圈
            基底膜 basilar membrane：蜗底(base)窄硬→高频，蜗顶(apex)宽软→低频
            ★ Greenwood 频率-位置函数（REAL 人）：f = A(10^(a·x) − k)
              A=165.4  a=2.1  k=0.88   x=0 蜗顶 → 1 蜗底
      ↓
    毛细胞 hair cells
      内毛细胞 IHC  ~3500 个  传入（约 95% 听神经纤维接这里）
      外毛细胞 OHC ~12000 个  ★ 主动放大（耳蜗放大器）prestin 电致运动
      ↓
    听神经 auditory nerve 约 30000 纤维

★ ★ ★ 耳朵的手性（REAL，两层）★★ ★

    【细胞级手性】毛细胞静纤毛束 stereocilia bundle
      · 静纤毛阶梯排列，动纤毛 kinocilium 在【最高侧】
      · 偏转【朝向】动纤毛 → MET 通道开放 → 去极化
        偏转【离开】       → 通道关闭     → 超极化
      ★ 且响应【不对称】：去极化幅度 >> 超极化幅度（整流，约 2~5:1）
      ★ 平面细胞极性 PCP：整个耳蜗所有毛细胞束【朝向一致】
        → 全耳蜗有统一的极性方向 = 真正的组织级手性

    【系统级不对称】通路双侧投射但对侧优势（约 70~80% 交叉）
      → 右耳优势 REA（言语材料，约 2~5% 正确率 / 10~20 ms 反应时）

★ 耳朵也"一直在动"（REAL）：
    中耳肌反射：镫骨肌 stapedius（CN VII）/ 鼓膜张肌（CN V）
      潜伏期 40~80 ms，衰减 10~20 dB（<1 kHz），发声前还会【预激活】
      ★ 与扫视抑制、说话抑制完全同构：自己出声 → 自己听不见那么多
    OHC 持续调增益：压缩非线性 0.2~0.5 dB/dB（正常约 0.3）
      ★ OHC 损坏 → 压缩消失 → 变线性约 1.0 dB/dB（重振 recruitment）

★ ★ 耳朵的"残差"：总和电位 SP（summating potential）★★
    定义：MET 整流 → 对正弦输入的响应【时间平均 ≠ 静息值】→ DC 位移
    ★ 完全对称的传递函数 → 只产生奇次失真 → DC = 0
    ★ 不对称（整流/手性）→ 产生 DC 位移 = SP
    REAL：临床 ECochG，SP/AP 正常 < 0.4；梅尼埃病（内淋巴积水）> 0.4

★ ★ 关键对照：DPOAE vs SP ★★
    DPOAE (2f1−f2) 是【三阶】失真，对称非线性（tanh/sigmoid）就能产生
      → 手性 = 0 时 DPOAE 依然存在
      → 它测的是"非线性"，不是"手性"
    SP 是【DC】，只有不对称才产生
      → 手性 = 0 时 SP = 0
      → 它才测"手性"
    ★ 与 ★17 的 A(时间反演) vs B(同向比较) 完全同构：
        一个量在手性=0 时非零（测别的），另一个精确归零（测手性）

provenance：解剖/生理/临床数值 = REAL；asym 与 SP 的定量关系 = 本模型
"""
from __future__ import annotations
import numpy as np

# ---------------- REAL 外耳 / 中耳 ----------------
CANAL_MM = 25.0            # 外耳道长度
CANAL_GAIN_DB = 12.0       # 共振增益（约 3 kHz）
MIDDLE_EAR_GAIN_DB = 22.0  # 中耳阻抗匹配增益（20~25）

# ---------------- REAL 耳蜗 ----------------
COCHLEA_MM = 35.0
COCHLEA_TURNS = 2.5
GW_A, GW_a, GW_k = 165.4, 2.1, 0.88   # Greenwood 人耳
IHC_N = 3500
OHC_N = 12000
AN_FIBERS = 30000

# ---------------- REAL 时间参数 ----------------
STAP_LATENCY_MS = 60.0     # 镫骨肌反射潜伏期（40~80）
STAP_ATTEN_DB = 15.0       # 衰减（10~20，<1kHz）
TEMPORAL_INTEG_MS = 200.0  # 响度时间整合饱和时长（200~300）
INTEG_SLOPE_DB = 3.0       # 短音：-3 dB / 倍时长（能量积分）
GAP_DETECT_MS = 2.5        # 静音间隙检测阈值（2~3 ms）

# ---------------- REAL OHC / 临床 ----------------
COMPRESS_NORMAL = 0.3      # dB/dB，正常压缩
COMPRESS_LOSS = 1.0        # OHC 损失后（线性=重振）
SPAP_NORMAL = 0.4          # SP/AP 正常上限；>0.4 提示梅尼埃
DPOAE_RATIO = 1.2          # f2/f1 标准比
DPOAE_DB_NORMAL = (5.0, 20.0)   # 正常 DPOAE 幅度区间 dB SPL

# ---------------- REAL 双耳 ----------------
ITD_JND_US = 10.0          # 双耳时间差最小可觉差（行为，约 10 μs）
ILD_JND_DB = 0.75          # 双耳强度差阈值（0.5~1 dB）
CROSS_FRAC = 0.75          # 听觉通路交叉比例（对侧优势，70~80%）


def greenwood(x, A=GW_A, a=GW_a, k=GW_k):
    """Greenwood 频率-位置函数（REAL）：f = A(10^(a·x) − k)。

    x: 0 = 蜗顶(apex, 低频) → 1 = 蜗底(base, 高频)
    """
    x = np.asarray(x, float)
    return A * (10 ** (a * x) - k)


def greenwood_inv(f, A=GW_A, a=GW_a, k=GW_k):
    """反函数：频率 → 归一化位置。"""
    f = np.asarray(f, float)
    return np.log10(f / A + k) / a


# ---------------- 行波包络（REAL：von Békésy 不对称） ----------------
def traveling_wave_envelope(x, x_cf=0.6, sharp_hi=18.0, soft_lo=6.0):
    """基底膜行波包络（REAL 定性）：★ 高频侧陡、低频侧缓。

    行波从蜗底(base)向蜗顶(apex)单向传播，在特征频率处达到峰值，
    然后能量被快速吸收 → 峰值【高频侧】陡峭，【低频侧】平缓。
    ★ 这种沿频率轴的方向不对称，本身就是一种手性。
    返回：包络（幅度）
    """
    x = np.asarray(x, float)
    # ★ sharp_hi 是【衰减率】：值大 → 衰减快 → 包络更窄更陡
    #   第一版我把 sharp_hi 设成 6.0（比 soft_lo 小），结果高频侧反而更宽，
    #   不对称度算出 -0.5（符号反）。REAL 是高频侧陡 → 衰减率必须【更大】。
    s = np.where(x > x_cf, sharp_hi, soft_lo)   # 蜗底侧(高频)陡 → 衰减率大
    return np.exp(-np.abs(x - x_cf) * s)


def wave_asymmetry(x_cf=0.6, sharp_hi=18.0, soft_lo=6.0):
    """行波包络不对称度：越不对称 → 越接近 1。"""
    xs = np.linspace(0, 1, 2001)
    env = traveling_wave_envelope(xs, x_cf, sharp_hi, soft_lo)
    half = env >= 0.5
    if half.sum() < 3:
        return 0.0
    hi = xs[half].max() - x_cf      # 高频侧半宽
    lo = x_cf - xs[half].min()      # 低频侧半宽
    return float((lo - hi) / max(lo + hi, 1e-12))


# ---------------- OHC 主动放大（压缩非线性） ----------------
def ohc_compress(db_in, comp=COMPRESS_NORMAL, knee=40.0):
    """OHC 压缩：输入每增 1 dB，基底膜响应只增 comp dB。

    ★ comp=1.0 = 线性（OHC 损坏 → 重振）
    ★ 斜率【小于 1】正是 OHC 主动放大的证据
    """
    d = np.asarray(db_in, float)
    return np.where(d < knee, d, knee + comp * (d - knee))


# ---------------- ★ MET 传递函数：手性的落点 ----------------
def met_current(x, x0=0.0, s_pos=1.0, asym=0.0, imax=1.0):
    """毛细胞机械电转导 MET 电流（Boltzmann），★ 含方向不对称。

    x     : 静纤毛束位移（正 = 朝向动纤毛 / 去极化方向）
    asym  : 手性参数 0~1
            0   = 完全对称（s_neg = s_pos）→ 只产生奇次失真 → SP = 0
            >0  = 整流（s_neg > s_pos：超极化侧更平缓）→ 产生 DC = SP
    REAL  : 整流比约 2~5:1

    ★ 注意：对称 sigmoid 就是【非线性】的，会产生 2f1−f2（三阶）
      所以 DPOAE 在手性=0 时就存在，SP 才真正测手性。
    """
    x = np.asarray(x, float)
    s_pos = float(s_pos)
    s_neg = s_pos * (1.0 + asym) / max(1.0 - asym, 1e-9)
    s = np.where(x >= x0, s_pos, s_neg)
    return imax / (1.0 + np.exp(-(x - x0) / s))


def met_dc_and_spectrum(x_t, fs, f1, f2, x0=0.0, s_pos=1.0, asym=0.0):
    """给 MET 喂双音，返回 (DC位移=SP, 2f1−f2 的 DPOAE 幅度, 基频幅度≈AP)。"""
    i_t = met_current(x_t, x0=x0, s_pos=s_pos, asym=asym)
    rest = float(met_current(np.array([x0]), x0=x0, s_pos=s_pos,
                             asym=asym)[0])
    sp = float(i_t.mean() - rest)              # ★ SP = DC 位移
    spec = np.fft.rfft(i_t) / len(i_t)
    freqs = np.fft.rfftfreq(len(i_t), 1.0 / fs)

    def amp(f):
        k = int(np.argmin(np.abs(freqs - f)))
        return float(np.abs(spec[k]) * 2)

    dp_f = 2 * f1 - f2                          # 2f1−f2（三阶失真）
    dp = amp(dp_f)
    ap = amp(f1)                                # 基频 ≈ 复合动作电位 AP
    return sp, dp, ap


# ---------------- 镫骨肌反射（自己出声 → 自己听不见） ----------------
def stapedius_reflex(t_ms, onset=0.0, latency=STAP_LATENCY_MS,
                     atten_db=STAP_ATTEN_DB):
    """中耳肌反射：发声/大声 → 镫骨肌收缩 → 传导降低。

    ★ 与扫视抑制、说话抑制同构：自己发起动作 → 该通道感知被压低
    REAL：潜伏期 40~80 ms，衰减 10~20 dB（<1 kHz）
    """
    t = np.asarray(t_ms, float)
    g = 1.0 / (1.0 + np.exp(-(t - onset - latency) / 15.0))
    return 10 ** (-(atten_db * g) / 20.0)      # 线性增益


# ---------------- 时间整合（耳朵的"追不上"） ----------------
def temporal_integration(dur_ms, integ=TEMPORAL_INTEG_MS,
                         slope=INTEG_SLOPE_DB):
    """响度时间整合：短音阈值随时长下降，到约 200 ms 饱和。

    REAL：约 −3 dB / 倍时长（能量积分），200~300 ms 饱和
    ★ 在整合窗内，声音的【时间结构被积分掉】，只留总能量
      → 与眼睛"扫视被抹平36%"、发音"47.5%过渡段"同构
    """
    d = np.asarray(dur_ms, float)
    d_eff = np.minimum(d, integ)
    import math
    return -slope * np.log2(np.maximum(d_eff, 1.0) / 1.0)


def gap_detectable(gap_ms, thr=GAP_DETECT_MS):
    """静音间隙能否被检出（REAL 阈值 2~3 ms）。"""
    g = np.asarray(gap_ms, float)
    return 1.0 / (1.0 + np.exp(-(g - thr) / (thr * 0.3)))
