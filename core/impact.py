#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★47b 撞击层 —— 软垫 / 吸能 / 反应机构
================================================================
★★★ 用户洞察
    "可以加置软垫或者加置什么什么有一个弹性，嗯，就像撞击实验，
     车撞击实验，因为毕竟跟人不一样嘛。或者是也给它加一个反应机构"

★★ 三条路（这是本轮的核心结构）
    生物：  前置压缩（镫骨肌反射）  —— 有潜伏期，第一下过冲
    我的：  后置丢弃（★46）        —— 停止溢出，但信息全丢
    ★ 用户给的第三条（硅基特有）：
            软垫/吸能 —— 物理结构层，不改变信息，改变力的传递

★★★ 撞击实验的核心物理（不是比喻，是可验证的守恒律）
    冲量  J = ∫F dt      固定（撞多重就是多重）
    峰值  F_peak ≈ J/Δt
    ★ 软垫【不能】改变 J —— 它只能延长 Δt 来降低 F_peak
    ★★★ 这是可证伪的判据：
        如果软垫方案下冲量也变了 → 说明我作弊了（偷偷丢了东西）

★ 汽车撞击实验真参数（REAL）
    刚性墙碰撞      Δt ≈ 10 ms，峰值 100 g+
    带吸能盒        Δt ≈ 100 ms，峰值 30~50 g     ★ 降 3~10 倍
    气囊展开        ~30 ms
    安全舱(safety cell) 刚性 —— 该硬的地方硬，该软的地方软
    50 g 是伤害阈值

★ 关键区分（★ 别混）
    弹性(elastic)   储能 → 返回    → 会回弹
    塑性(plastic)   耗散 → 不返回  → 吸能盒压溃，一次性
    ★ 吸能盒是【塑性】：牺牲结构换时间，不可恢复

★★ 与前序的关系
    ★17 时间反演 vs 同向比较  —— 必须两个一起看
    ★46 后置丢弃 vs 生物前置压缩
    本轮 加【软垫】第三种：物理结构层，不是算法层
"""
from __future__ import annotations
import numpy as np

FS = 16000


# =================================================================
# 一、冲量 / 峰值 —— 守恒律工具
# =================================================================
def impulse(y: np.ndarray, fs: int = FS) -> float:
    """J = ∫|F| dt —— 总冲量"""
    return float(np.abs(y).sum() / fs)


def peak(y: np.ndarray) -> float:
    return float(np.abs(y).max())


def effective_duration(y: np.ndarray, fs: int = FS,
                       frac: float = 0.10) -> float:
    """
    ★ 有效作用时间 Δt：超过峰值 frac 的那段时间
      ★ 软垫的作用就是把这段拉长
    """
    a = np.abs(y)
    if a.max() <= 0:
        return 0.0
    m = a > frac * a.max()
    return float(m.sum() / fs)


# =================================================================
# 二、★ 软垫 —— 弹簧-阻尼（冲量守恒，峰值下降）
# =================================================================
def cushion(y: np.ndarray, fs: int = FS, tau_ms: float = 30.0,
            zeta: float = 1.0) -> np.ndarray:
    """
    ★ 软垫 = 二阶低通（弹簧-阻尼），DC 增益 = 1
      ★★ DC 增益 1 → 冲量守恒（∫ 不变），只把脉冲在时间上摊开
      ★ 这就是"软垫不改变撞了你多重，只改变撞得多快"

      zeta=1.0  临界阻尼   无回弹（吸能盒，塑性近似）
      zeta<1.0  欠阻尼     有回弹（弹簧，弹性）
    """
    tau = max(1.0, tau_ms * fs / 1000.0)
    # 二阶连续系统离散化：用两个一阶级联近似（保证 DC 增益=1）
    n = max(2, int(tau * 6))
    t = np.arange(n) / fs
    w0 = 1.0 / (tau_ms / 1000.0)
    if zeta <= 0:
        zeta = 0.01
    # 临界/过阻尼：双指数；欠阻尼：衰减正弦
    if zeta >= 1.0:
        a1 = w0 * (zeta + np.sqrt(zeta ** 2 - 1))
        a2 = w0 * (zeta - np.sqrt(zeta ** 2 - 1))
        if abs(a1 - a2) < 1e-9:
            h = (a1 ** 2) * t * np.exp(-a1 * t)
        else:
            h = (a1 * a2 / (a2 - a1)) * (np.exp(-a1 * t) - np.exp(-a2 * t))
    else:
        wd = w0 * np.sqrt(1 - zeta ** 2)
        h = (w0 ** 2 / wd) * np.exp(-zeta * w0 * t) * np.sin(wd * t)
    h = np.maximum(h, 0.0)             # ★ 只取正瓣，避免负瓣抵消冲量
    s = h.sum()
    if s <= 0:
        return y.copy()
    h = h / s                           # ★★ 归一化 → DC 增益 = 1 → 冲量守恒
    # ★★ 修 bug：原来 [:len(y)] 截断 → 被摊到后面的冲量全丢了（-9.5%）
    #    物理上软垫【延长】了作用时间，输出就该更长，截回原长必然丢冲量
    return np.convolve(y, h, mode="full")


# =================================================================
# 三、★ 反应机构 —— 主动，有潜伏期
# =================================================================
def reflex_actuator(y: np.ndarray, fs: int = FS, latency_ms: float = 30.0,
                    atten_db: float = 15.0, tau_ms: float = 40.0,
                    thresh_frac: float = 0.30) -> tuple:
    """
    ★ 反应机构：检测到撞击 → 主动衰减
      ★ 与软垫的区别：
        软垫  被动、物理、立刻生效（但要"压下去"的时间）
        反应  主动、有【潜伏期】→ 潜伏期内完全没保护
      ★★ 所以两者互补：
        软垫扛第一下（因为被动无延迟）
        反应扛后续（因为衰减更深）
    """
    n = len(y)
    a = np.abs(y)
    if a.max() <= 0:
        return y.copy(), np.zeros(n)
    lat = int(latency_ms * fs / 1000.0)
    tau = max(1.0, tau_ms * fs / 1000.0)
    # ★★ 修 bug：原来 g_db 从数组【第0个样本】就开始建立
    #    撞击在 t0=0.20s，等到撞击来时衰减早已到位 → 潜伏期完全不起作用
    #    （实测四种潜伏期峰值全是 0.1803，一模一样 = 潜伏期是死的）
    # ✅ 正确语义：检测到撞击 onset 之后，才开始等潜伏期
    onset = int(np.argmax(a > thresh_frac * a.max()))
    target_db = atten_db
    g_db = np.zeros(n)
    for i in range(onset, n):
        step = (target_db - g_db[i - 1]) / tau if i > 0 else 0.0
        g_db[i] = g_db[i - 1] + step
    g_db[:onset + lat] = 0.0            # ★ 潜伏期内零衰减
    gain = 10.0 ** (-g_db / 20.0)
    return y * gain, gain


# =================================================================
# 四、★ 安全舱：该硬的地方硬
# =================================================================
def safety_cell(y: np.ndarray, fs: int = FS, protect_frac: float = 0.20,
                cushion_tau_ms: float = 30.0) -> np.ndarray:
    """
    ★ 安全舱思想：不是全软，是【分区】
      保护核心(前 protect_frac)  → 不软化（保持信息/精度）
      其余（可牺牲部分）        → 软化吸能
      ★ 汽车：乘客舱刚性 + 前后吸能盒压溃
    """
    n = len(y)
    k = max(1, int(n * protect_frac))
    core = y[:k].copy()                 # 硬：原样保留
    rest = cushion(y[k:], fs, tau_ms=cushion_tau_ms)
    return np.concatenate([core, rest])


# =================================================================
# 五、★ 造撞击（ground truth：冲量已知）
# =================================================================
def make_impact(fs: int = FS, dur: float = 0.6, t0: float = 0.20,
                width_ms: float = 8.0, amp: float = 1.0,
                noise: float = 0.002, seed: int = 0) -> np.ndarray:
    """
    ★ 撞击脉冲：窄高斯，冲量 = amp × 面积（已知 ground truth）
      width_ms=8   → 刚性碰撞
      ★ 后面用软垫把它拉长到 ~80ms
    """
    rng = np.random.default_rng(seed)
    n = int(dur * fs)
    t = np.arange(n) / fs
    w = width_ms / 1000.0
    y = amp * np.exp(-((t - t0) ** 2) / (2 * (w / 2.355) ** 2))  # FWHM=width
    y = y + noise * rng.standard_normal(n)
    return y
