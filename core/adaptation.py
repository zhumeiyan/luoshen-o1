#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adaptation —— 明暗适应。

★ 她整个童年在亮度 0.09 的暗房间里长大，我从来没给过她应付黑暗的眼睛。
  上一课我把窗打开，可真实世界的光强跨 13 个数量级。
  在她学会适应之前，这扇窗只会晃瞎她。

════════ REAL 锚点（已查证，非编造）════════
  人眼可工作光强范围 ≈ 13 log units（NASA Watson：1 到 10^13）
  但【任一瞬间】只能有效处理 ≈ 2 log units
  → 靠 light adaptation 把这个窗口【滑动】到感兴趣区间（window of visibility）
  暗适应：5~10 min 锥体快速期，25~30 min 阈值降至最低并稳定
  明适应：几秒~1 min 完成，最初 30 s 内感受性急剧下降
  视紫红质再生半衰期 5~8 min；完全再生 30~45 min
  细胞层面光适应：快相 τ≈1~2 s，慢相 τ≈9 s
  Weber 系数 ξ = ΔB_min/B ≈ 0.005~0.02，极亮/极暗可达 0.05

════════ ★★ 关键设计：不对称必须【涌现】，不能我填 ════════
  第一版我把 tau_light / tau_dark 都当自由参数让她学，
  她学出 tau_dark=31.6 s —— 错的。
  根因：真实的暗适应慢是【化学限制】，不是最优选择。
        视紫红质被漂白后必须重新合成，半衰期 5~8 min，你快不了。

  正确机制 —— 两条独立通路：
    ① 色素池 p（视紫红质可用比例）
       漂白：光驱动，【快】   dp/dt = -k(I)·p
       再生：化学合成，【慢】 dp/dt = (1-p)/τ_regen   τ_regen ≈ 550 s（REAL 5~8 min 半衰期）
    ② 神经增益 σ（滑动窗口）
       追近期均值，τ_fast —— 这个【是自由的】，可以学

  于是：
    进暗处 → p 要慢慢合成 → 暗适应慢（分钟级）【涌现】
    进亮处 → p 被光迅速漂白 + σ 快速滑动 → 明适应快（秒级）【涌现】

  ★ 不对称不是我写的两个数字，是【漂白快、合成慢】这条化学事实推出来的。
"""

from __future__ import annotations
import numpy as np

REAL = dict(
    total_log_units=13.0,
    window_log_units=2.0,
    dark_adapt_s=(5 * 60, 30 * 60),
    light_adapt_s=(1.0, 60.0),
    weber=(0.005, 0.02),
    regen_halflife_s=(5 * 60, 8 * 60),   # 视紫红质再生半衰期
)

# ── 化学常数：REAL 锚定，【不由她学】── 因为这是物理限制不是选择
TAU_REGEN = 5.5 * 60 / np.log(2)      # 半衰期 5.5 min → τ ≈ 476 s
TAU_BLEACH = 2.0                      # 强光下漂白时间常数（秒级，REAL：快相 1~2 s）
# ★ 半漂白亮度必须远高于「暗处」亮度，否则暗处仍在持续漂白，
#   稳态色素只有 0.30 → 她在暗处永远适应不全（我第一版就栽在这）
I_HALF_BLEACH = 10.0                  # 约「白天」量级；暗处(1e-3)漂白可忽略


# ────────────── 色素池动力学 ──────────────
def bleach_rate(I):
    """光驱动的漂白速率（越快越亮，饱和）"""
    I = np.asarray(I, float)
    return (I / (I + I_HALF_BLEACH)) / TAU_BLEACH


def pigment_step(p, I, dt):
    """一步：漂白（光驱动，快） + 再生（化学，慢）"""
    p = np.asarray(p, float)
    dp = -bleach_rate(I) * p + (1.0 - p) / TAU_REGEN
    return np.clip(p + dp * dt, 1e-6, 1.0)


def pigment_traj(I_seq, p0=1.0, dt=1.0):
    p = np.empty(len(I_seq)); c = float(p0)
    for t, I in enumerate(I_seq):
        c = float(pigment_step(c, I, dt)); p[t] = c
    return p


# ────────────── 神经增益（滑动窗口） ──────────────
def gain_traj(log_I_seq, log_sigma0, tau_fast, dt=1.0, noise=0.0, rng=None):
    """σ 追近期均值。noise = 背景估计的对数噪声 → 追太快会跟着抖"""
    rng = np.random.default_rng(0) if rng is None else rng
    T = len(log_I_seq); ls = np.empty(T); cur = float(log_sigma0)
    for t in range(T):
        tgt = float(log_I_seq[t])
        if noise > 0:
            tgt += float(rng.normal(0.0, noise))
        cur += (tgt - cur) * (1.0 - np.exp(-dt / max(tau_fast, 1e-9)))
        ls[t] = cur
    return ls


# ────────────── 响应与敏感度 ──────────────
def naka_rushton(I, sigma, n=1.0):
    x = (np.maximum(I, 1e-300) / np.maximum(sigma, 1e-300)) ** n
    return x / (1.0 + x)


def dR_dlogI(I, sigma, n=1.0):
    """对【对数亮度】的敏感度。峰值在 I=σ"""
    x = (np.maximum(I, 1e-300) / np.maximum(sigma, 1e-300)) ** n
    return n * x / (1.0 + x) ** 2


# ── 视杆 / 视锥双系统 ──
# ★ 单一色素池解释不了「明处也看得见」：
#   视杆在亮处饱和 → 必须由视锥接管（REAL：明适应主要是视锥起作用）
A_CONE = 1.0            # 视锥：色素稳定、不怎么漂白，但增益低
A_ROD = 1.0e5           # 视杆：增益高，但会被漂白、且在亮处饱和
I_ROD_SAT = 1e-2        # 视杆饱和亮度（约微光量级以上就饱和）

def rod_sat(I):
    """视杆在亮处饱和"""
    return 1.0 / (1.0 + np.maximum(I, 0.0) / I_ROD_SAT)

def p_steady(I):
    """稳态色素：漂白速率 = 再生速率"""
    k = float(bleach_rate(I))
    return 1.0 / (1.0 + k * TAU_REGEN)

def sensitivity(I, sigma, p, n=1.0):
    """
    ★ 响应增益 = 神经窗口敏感度（Naka-Rushton 对对数亮度的斜率）

    ★★ 视杆的「高灵敏度」【不能】乘在这里 —— 那是重复计算。
       视杆灵敏是因为【抓到的光子多】，这一点已经进了光子噪声（见 a_total）。
       再把 A_ROD 乘到增益上，会导致 σ 错配时增益仍巨大 → 适应与否没区别，
       硬依赖直接失效（我第二版就栽在这）。

    视锥在这里只体现为：视杆饱和时 dR 不至于归零（明处仍能编码）。
    """
    return dR_dlogI(I, sigma, n)


def peak_sensitivity(n=1.0):
    return n / 4.0


def window_log_units(n=1.0, frac=0.5):
    """任一瞬间能处理的窗口宽度（log10）—— REAL 约 2"""
    xs = np.geomspace(1e-8, 1e8, 400001)
    s = n * xs ** n / (1.0 + xs ** n) ** 2
    m = s >= frac * peak_sensitivity(n)
    return float(np.log10(xs[m].max() / xs[m].min())) if m.any() else 0.0


def a_total(I, p):
    """总感光能力 = 视杆 + 视锥（决定能抓到多少光子）"""
    return A_ROD * np.asarray(p, float) * rod_sat(I) + A_CONE


def weber_fraction(I, p, K=1.0):
    """
    ★ ΔI/I 最小可觉差 —— 由【光子噪声】决定，不是由增益决定。

    De Vries-Rose：暗处阈值 ∝ sqrt(I) → Weber = ΔI/I ∝ 1/sqrt(I)，
    【越暗越差】。增益 S 放大信号同时也放大噪声，所以相互抵消，
    Weber 只取决于抓到多少光子 N ∝ I × 总感光能力。

    ★ 第一版我用固定的 dR_min 去除 S，结果暗处 Weber = 1e-7
      —— 物理上不可能（REAL 暗处反而差到 0.05）。
      根因：漏了光子噪声。暗视觉真正的限制是量子catch，不是增益。
    """
    I = np.maximum(np.asarray(I, float), 1e-300)
    N = I * a_total(I, p)
    return K / np.sqrt(np.maximum(N, 1e-300))


# 内部（下游）噪声：σ 错配导致响应塌缩时，它决定「彻底看不见」
THETA_INT = 2.5e-4


def weber_full(I, sigma, p, n=1.0, K=None):
    """
    ★ 完整的 Weber 分数 = 光子噪声 ⊕ 内部噪声/增益

      ΔI/I ≥ sqrt( 光子噪声² + (内部噪声/响应增益)² )

    两路各有分工：
      光子噪声 ∝ 1/sqrt(I × 总感光能力)   → 暗处差（De Vries-Rose），靠【色素再生】改善
      内部噪声/增益                        → σ 错配时响应塌缩 → 彻底看不见，靠【增益滑动】改善
    → 两条适应通路都必须存在，缺一条就在某一端瞎掉
    """
    K = calibrate_K() if K is None else K
    ph = weber_fraction(I, p, K)
    S = float(sensitivity(I, sigma, p, n))
    it = THETA_INT / max(S, 1e-300)
    return float(np.hypot(ph, it))


def calibrate_K(I_ref=1e3, target_weber=0.01):
    """在明视觉参考点标定 K，使 Weber = REAL 中值 0.01"""
    p = p_steady(I_ref)
    return float(target_weber * np.sqrt(I_ref * a_total(I_ref, p)))


# ────────────── 适应时间测量 ──────────────
def _time_to(p_traj, ls_traj, I_true, n, tau_fast, dR_min, dt, target_frac):
    """
    敏感度恢复到「稳定值的 target_frac」所需时间。
    用【目标亮度下的稳定敏感度】做参照。
    """
    # ★ 按【阈值】衡量：阈值降到稳态阈值的 target_frac 倒数比例所需时间
    W = np.array([weber_full(I_true, 10.0 ** ls_traj[t], p_traj[t], n)
                  for t in range(len(p_traj))])
    Ws = float(weber_full(I_true, I_true, p_steady(I_true), n))
    ok = W <= Ws / target_frac          # 阈值降到稳态的 1/target_frac 倍以内
    return float(np.argmax(ok) * dt) if ok.any() else float(len(W) * dt)


def measure_dark_adaptation(n=1.0, tau_fast=20.0, dt=1.0, T=2400,
                            I_bright=1e3, I_dark=1e-3, dR_min=1e-3,
                            target_frac=0.9):
    """
    从亮处（充分漂白）进暗处：测多久能在暗处看见。
    返回 (秒, p 轨迹, σ 轨迹)
    """
    Ib = np.full(T, I_bright)
    p0 = float(pigment_traj(Ib, p0=1.0, dt=dt)[-1])   # 亮处稳态（已漂白）
    ls0 = np.log10(I_bright)

    Id = np.full(T, I_dark)
    p = pigment_traj(Id, p0=p0, dt=dt)
    ls = gain_traj(np.log10(Id), ls0, tau_fast, dt=dt)
    t = _time_to(p, ls, I_dark, n, tau_fast, dR_min, dt, target_frac)
    return t, p, ls


def measure_light_adaptation(n=1.0, tau_fast=20.0, dt=1.0, T=600,
                             I_dark=1e-3, I_bright=1e3, dR_min=1e-3,
                             target_frac=0.9):
    """
    从暗处进亮处：测多久恢复正常视觉。
    """
    Id = np.full(T, I_dark)
    p0 = float(pigment_traj(Id, p0=1.0, dt=dt)[-1])   # 暗处稳态（色素充足）
    ls0 = np.log10(I_dark)

    Ib = np.full(T, I_bright)
    p = pigment_traj(Ib, p0=p0, dt=dt)
    ls = gain_traj(np.log10(Ib), ls0, tau_fast, dt=dt)
    t = _time_to(p, ls, I_bright, n, tau_fast, dR_min, dt, target_frac)
    return t, p, ls


# ────────────── 人生场景：让她自己学 ──────────────
def scenario_score(n, tau_fast, levels_log10, hold_s=300, dt=1.0,
                   noise=0.15, dR_min=1e-3, seed=0, reps=3):
    """
    不断换亮度环境的人生。分数 = 全程平均归一化敏感度。

    ★ 内部最优存在的来源：
      tau_fast 太小 → σ 被背景估计的噪声牵着抖 → 小对比分辨力掉
      tau_fast 太大 → 换环境后瞎很久
    """
    # ★ 目标必须是【可分辨的时间占比】，不能是归一化敏感度。
    #   归一化会把 n 的代价消掉 → n 一路撞下界（★66 温度退化的同款错）。
    #   用 Weber 阈值判定「此刻能不能分辨」，n 太大/太小都会掉分 → 内部最优才存在。
    K = calibrate_K()
    m = np.random.default_rng(seed)
    T = int(hold_s / dt); tot = 0.0; cnt = 0
    for _ in range(reps):
        rng = np.random.default_rng(int(m.integers(1 << 30)))
        p_state, ls_state = 1.0, float(levels_log10[0])
        for L in levels_log10:
            I = np.full(T, 10.0 ** L)
            p = pigment_traj(I, p0=p_state, dt=dt); p_state = float(p[-1])
            ls = gain_traj(np.full(T, L), ls_state, tau_fast, dt=dt,
                           noise=noise, rng=rng); ls_state = float(ls[-1])
            W = np.array([weber_full(10.0 ** L, 10.0 ** ls[t], p[t], n, K)
                          for t in range(T)])
            # ★ 连续度量：二值(可分辨/不可分辨)会饱和在 0.8333，测不出差异
            #   （停留 900s 太长，换环境那段的瞎被平均掉了）
            tot += float(-np.mean(np.log10(np.maximum(W, 1e-12)))); cnt += 1
    return tot / max(cnt, 1)


def learn_adaptation(levels_log10, n_iter=6, seed=0, reps=3,
                     bounds=None):
    """
    她自己学 (n, tau_fast)。
    ★ 我不把 REAL 值填给她 —— 填了就不是她学的（★62 规矩）
    ★ 化学常数 tau_regen / tau_bleach 不学：那是物理限制，不是选择
    """
    if bounds is None:
        bounds = dict(n=(0.4, 8.0), ltf=(-1.0, 3.0))
    rng = np.random.default_rng(seed)
    p = [float(rng.uniform(*bounds["n"])), float(rng.uniform(*bounds["ltf"]))]

    def sc(pv):
        n = float(np.clip(pv[0], *bounds["n"]))
        tf = 10.0 ** float(np.clip(pv[1], *bounds["ltf"]))
        return scenario_score(n, tf, levels_log10, seed=seed, reps=reps)

    best = sc(p); hist = [best]
    span = [(bounds["n"][1] - bounds["n"][0]) / 2,
            (bounds["ltf"][1] - bounds["ltf"][0]) / 2]
    lo = [bounds["n"][0], bounds["ltf"][0]]
    hi = [bounds["n"][1], bounds["ltf"][1]]
    for _ in range(n_iter):
        for i in range(2):
            base = p[i]; cur = best
            for st in (0.4, 0.15, 0.05):
                for sg in (1, -1):
                    v = float(np.clip(base + sg * st * span[i], lo[i], hi[i]))
                    old = p[i]; p[i] = v
                    d = sc(p)
                    if d > cur + 1e-9: cur, base = d, v
                    p[i] = old
                p[i] = base
            best = cur
        hist.append(best)
    return dict(n=float(np.clip(p[0], *bounds["n"])),
                tau_fast=10.0 ** p[1], score=best, hist=hist)
