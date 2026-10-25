#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
电子鼻 —— 嗅觉是【高维且没有坐标轴】的
================================================================
用户：「鼻子按电子鼻也行。」

★ 嗅觉与视觉/听觉的根本不同（这是本层要证明的）：
    视觉  3 个感受器（三色）  → 3 维，有明确坐标轴
    听觉  基底膜 tonotopy     → 1 维频率轴，位置=频率
    ★ 嗅觉 ~400 种受体         → 400 维，且【没有自然的"相邻"关系】
                                 受体 i 与 i+1 并不相似
    ★ 所以嗅觉不能画成一条线或一块色域，只能靠【组合编码】

----------------------------------------------------------------
一、生物鼻（REAL）
----------------------------------------------------------------
    功能性嗅觉受体基因  约 400（人类；总数约 800，一半是假基因）
    嗅神经元            约 1000~2000 万
    ★ 一个神经元只表达【一种】受体（one neuron–one receptor）
    嗅球肾小球          约 2000（同种受体的轴突汇聚到同一个球）
    嗅上皮面积          约 2.5~5 cm²
    ★ 再生周期          约 30~60 天 —— 这是生物鼻【抗漂移】的机制
    组合编码            一个气味激活多个受体；一个受体响应多个气味

----------------------------------------------------------------
二、电子鼻（REAL）
----------------------------------------------------------------
    传感器类型  MOS(SnO2)、电化学、PID、NDIR 红外、QCM、SAW
    ★ 交叉敏感  一个传感器对多种气体响应 → 【单个传感器没有选择性】
    ★ 阵列      8~32 个传感器 + 模式识别 = 电子鼻（Persaud & Dodd 1982）
    漂移        基线漂移：几%/天 ~ 几十%/月 ← 电子鼻【最致命】的问题
    温湿度依赖  MOS 强依赖，必须补偿
    响应/恢复   t90 数秒~数十秒；恢复数十秒~数分钟
    检出限      ppb~ppm
    MOS 模型    S = R_air / R_gas   或   R = R0·(1 + a·C^b)

----------------------------------------------------------------
三、本层要证明的三件事（★ 每件都有对照）
----------------------------------------------------------------
    ① 交叉敏感不是缺陷，是【设计】：单个不选择，阵列才选择
    ② 阵列维数决定可分性：维数↑ → 可分性↑（有饱和）
    ③ ★ 漂移 vs 再生：电子鼻会漂，生物鼻靠受体再生重置基线
    ④ 混合物抑制：A+B ≠ A+B（非线性）—— 真实现象，必须出现
"""
from __future__ import annotations
import numpy as np

# ---------------- 生物鼻 REAL ----------------
OR_GENES_FUNC   = 400        # 功能性受体基因（人类）
OR_TOTAL        = 800        # 总基因座（约一半假基因）
OSN_COUNT       = 12e6       # 嗅神经元（1000~2000 万）
GLOMERULI       = 2000       # 嗅球肾小球
EPITHELIUM_CM2  = 3.5        # 嗅上皮面积
REGENERATE_DAYS = 45.0       # 再生周期（30~60 天）

# ---------------- 电子鼻 REAL ----------------
MOS_TEMP_C      = 300.0      # MOS 工作温度（200~400）
T90_RESP_S      = 8.0        # 响应 t90（数秒~数十秒）
T90_RECOV_S     = 60.0       # 恢复（数十秒~数分钟）
DRIFT_PCT_DAY   = 1.5        # 基线漂移 %/天
DRIFT_PCT_MONTH = 30.0       # 长期漂移 数十%/月
LOD_PPB         = 50.0       # 检出限（ppb 级）
RH_SENS         = 0.35       # 湿度敏感度（归一化）
TEMP_SENS       = 0.25       # 温度敏感度


# ================================================================
# 一、受体/传感器响应模型
# ================================================================
def make_receptor_matrix(n_odor: int, n_recep: int,
                         sparsity: float = 0.45,
                         rng: np.random.Generator = None) -> np.ndarray:
    """★ 组合编码矩阵 M[odor, recep]。

    ★ 稀疏：每个气味只激活约 15% 的受体（REAL：气味是稀疏编码）
    ★ 每个受体响应多种气味（交叉敏感）
    """
    rng = rng or np.random.default_rng(0)
    # ★ 第一版用 random()**3 再乘 15% 稀疏 mask：
    #   响应值太小且不重叠 → 类间距离≈类内噪声 → 识别率全是随机水平(0.03)
    #   混合物抑制也测不出来（两个气味的非零位不重叠 → max+min=sum，比值1.000）
    # ★ 修：值域放宽，稀疏度提到 45%（真实受体确实响应多种气味，必须重叠）
    M = 0.3 + 0.7 * rng.random((n_odor, n_recep))
    mask = (rng.random((n_odor, n_recep)) < sparsity)
    return M * mask


def normalize_response(R: np.ndarray, mode: str = "vector") -> np.ndarray:
    """★ 浓度归一化 —— 电子鼻的必备预处理。

    ★ 不做归一化，最近邻测到的是【浓度差】不是【种类差】
      REAL：电子鼻信号预处理必做这一步
    """
    if mode == "vector":
        n = np.linalg.norm(R, axis=1, keepdims=True)
        return R / np.maximum(n, 1e-9)
    if mode == "max":
        return R / np.maximum(np.abs(R).max(axis=1, keepdims=True), 1e-9)
    return R


def make_dataset(M: np.ndarray, n_repeats: int, rng: np.random.Generator,
                 conc_spread: float = 0.4, snr_db: float = 10.0):
    """★ 生成 [label, response] 对齐的数据集。

    ★ 第一版用 np.tile(M,(n_repeats,1)) 配 np.repeat(labels)
      → 行顺序与标签【错位】，分类全是随机水平
    """
    n_odor = M.shape[0]
    labels = np.repeat(np.arange(n_odor), n_repeats)      # 000..111..222
    Mrep = np.repeat(M, n_repeats, axis=0)                # ★ 与 labels 对齐
    conc = 1.0 + conc_spread * rng.random(len(labels))
    K = receptor_K(M.shape[1], rng)
    R = receptor_response(Mrep, conc, K=K)
    # ★ 传感器噪声（REAL：电子鼻信噪比有限，约 10~20 dB）
    #   第一版 noise=0、第二版 20 dB → 识别率仍饱和在 1.000
    #   ★ 根因：类内距离≈0，加性漂移对所有样本相同，不改变最近邻结果
    #     → 必须有【每样本独立】的噪声，类内距离才真实存在
    #   改 10 dB（约 32%）后漂移/维数/温湿度才显出差异
    if snr_db < 200:
        sig = float(np.sqrt(np.mean(R ** 2)))
        R = R + rng.normal(0.0, sig * 10 ** (-snr_db / 20.0), R.shape)
    return R, labels, conc


def receptor_K(n_recep: int, rng: np.random.Generator = None,
               spread: float = 1.2) -> np.ndarray:
    """★ 每个受体有【自己的】亲和度 K（EC50）。

    ★ 第一版所有受体 K=1 → 浓度变化是纯乘性 → 归一化完全消除
      → 类内距离恒为 0 → 分类永远 1.000 → 漂移也测不出效果
    ★ 真实：不同受体对同一分子的亲和度差异很大（对数正态跨越数个量级）
    """
    rng = rng or np.random.default_rng(0)
    return np.exp(rng.normal(0.0, spread, n_recep) * 0.5)


def receptor_response(M: np.ndarray, conc: np.ndarray,
                      hill_n: float = 1.6, K: np.ndarray = None
                      ) -> np.ndarray:
    """★ Hill 饱和响应（不是线性）。Hill 系数 REAL 约 1~3。

    r = conc^n / (K^n + conc^n)   ★ K 逐受体不同
    """
    C = np.asarray(conc, float)[:, None]
    if K is None:
        K = np.ones(M.shape[1])
    K = np.asarray(K, float)[None, :]
    return (C ** hill_n) / (K ** hill_n + C ** hill_n) * M


def competitive_binding(M_A: np.ndarray, M_B: np.ndarray,
                        cA: float = 1.0, cB: float = 1.0,
                        K: np.ndarray = None,
                        rng: np.random.Generator = None) -> tuple:
    """★ 竞争结合（REAL 的混合物抑制机制）。

    ★ 两种分子【竞争同一受体的结合位点】→ 响应不是相加而是饱和竞争
      r_AB = (cA·M_A + cB·M_B) / (1 + cA·M_A + cB·M_B)
    ★ 这比"加权取大"更真实：受体总 occupancy 有上限
    返回 (r_A, r_B, r_AB_linear, r_AB_competitive)
    """
    if K is None:
        K = np.ones(M_A.shape[0])
    K = np.asarray(K, float)
    rA = (cA * M_A) / (K + cA * M_A)
    rB = (cB * M_B) / (K + cB * M_B)
    lin = rA + rB
    comp = (cA * M_A + cB * M_B) / (K + cA * M_A + cB * M_B)
    return rA, rB, lin, comp


def mixture_suppression(r_A: np.ndarray, r_B: np.ndarray,
                        beta: float = 0.35) -> np.ndarray:
    """★ 混合物抑制（REAL）：A+B 的响应【小于】A 与 B 单独响应之和。

    ★ 真实现象：mixture suppression / hypoadditivity
      r_AB = max(r_A, r_B) + (1−β)·min(r_A, r_B)   ← 折中模型
      β=0 → 完全线性相加；β=1 → 完全取最大（完全抑制）
    """
    hi = np.maximum(r_A, r_B)
    lo = np.minimum(r_A, r_B)
    return hi + (1.0 - beta) * lo


# ================================================================
# 二、可分性（★ 核心判据）
# ================================================================
def separability(feats: np.ndarray, labels: np.ndarray,
                 rng: np.random.Generator = None,
                 noise: float = 0.0) -> float:
    """最近邻分类正确率（留出一份做测试）。

    ★ feats: [n_sample, n_dim]；labels: [n_sample]
    ★ 返回正确率 0~1
    """
    rng = rng or np.random.default_rng(0)
    F = feats + noise * rng.standard_normal(feats.shape) if noise > 0 else feats
    n = len(F)
    idx = rng.permutation(n)
    k = max(1, n // 3)
    test, train = idx[:k], idx[k:]
    correct = 0
    for i in test:
        d = np.linalg.norm(F[train] - F[i], axis=1)
        correct += (labels[train[int(np.argmin(d))]] == labels[i])
    return correct / k


def single_vs_array(M: np.ndarray, n_repeats: int = 60,
                    seed: int = 0, norm: bool = True
                    ) -> tuple[float, float]:
    """★ 单个传感器 vs 整列阵列 的识别率（核心对照）。"""
    rng = np.random.default_rng(seed)
    R, labels, _ = make_dataset(M, n_repeats, rng)
    if norm:
        R = normalize_response(R)
    acc_arr = separability(R, labels, rng)
    accs = [separability(normalize_response(R[:, [j]]) if norm else R[:, [j]],
                         labels, rng) for j in range(M.shape[1])]
    return float(np.mean(accs)), float(acc_arr)


def dim_sweep(n_odor: int = 20, dims=(1, 2, 4, 8, 16, 32, 64, 128, 400),
              n_repeats: int = 40, seed: int = 0):
    """★ 维数扫描：可分性随受体数增加（应有饱和）。"""
    rng = np.random.default_rng(seed)
    out = []
    for d in dims:
        M = make_receptor_matrix(n_odor, d, rng=rng)
        R, labels, _ = make_dataset(M, n_repeats, rng)
        R = normalize_response(R)
        out.append((d, separability(R, labels, rng)))
    return out


# ================================================================
# 三、漂移 vs 再生
# ================================================================
def apply_drift(R: np.ndarray, days: float, rng: np.random.Generator = None,
                pct_per_day: float = DRIFT_PCT_DAY) -> np.ndarray:
    """★ 电子鼻基线漂移：每个传感器独立随机游走 + 增益漂移。"""
    rng = rng or np.random.default_rng(0)
    n_dim = R.shape[1]
    base = rng.normal(0.0, pct_per_day / 100.0 * np.sqrt(days), n_dim)
    gain = 1.0 + rng.normal(0.0, pct_per_day / 100.0 * np.sqrt(days), n_dim)
    return R * gain + base


def biological_renewal(R0: np.ndarray, R_drifted: np.ndarray, days: float,
                       renew_days: float = REGENERATE_DAYS,
                       rng: np.random.Generator = None) -> tuple:
    """★ 生物鼻：受体持续再生 → 已更新受体的漂移被【撤销】。

    ★ 机制：嗅神经元约 45 天换一批，新神经元带来全新的受体表达
      → 已更新通道回到【出厂基线】，漂移不累积
      → ★ 代价：气味记忆在这些通道上要重新校准
    ★ 第一版只传 R0（无漂移），等于没施加漂移 → 生物鼻永远 1.000，对照失效
    """
    rng = rng or np.random.default_rng(0)
    frac = min(1.0, days / renew_days)
    renewed = rng.random(R0.shape[1]) < frac
    R2 = R_drifted.copy()
    R2[:, renewed] = R0[:, renewed]      # ★ 已再生的通道：漂移归零
    return R2, float(renewed.mean())


def drift_curve(M: np.ndarray, days_list=(0, 7, 30, 90, 180, 365),
                n_repeats: int = 40, seed: int = 0, snr_db: float = 10.0):
    """★ 漂移曲线：★ 训练集是【第0天的库】，测试集是【第d天采的样】。

    ★ 前两版全部失败（识别率恒 1.000），根因：
      train/test 从【同一批、同一天】的数据里划分
      → 加性漂移对所有样本【相同】→ 不改变最近邻结果 → 漂移"测不出来"
    ★ 真实场景：电子鼻出厂时建好气味库，用了 N 天后再测
      → 库是旧的，样是新的，漂移【只在样本侧】→ 才致命
    """
    rng = np.random.default_rng(seed)
    R0, labels, _ = make_dataset(M, n_repeats, rng, snr_db=snr_db)
    Rn0 = normalize_response(R0)
    # ★ 建库：每个气味的类均值作为模板（REAL：电子鼻出厂标定）
    uniq = np.unique(labels)
    tmpl = np.array([Rn0[labels == u].mean(axis=0) for u in uniq])
    out = []
    for d in days_list:
        # 第 d 天重采一遍（新噪声 + 漂移）
        Rd, labels_d, _ = make_dataset(M, n_repeats, rng, snr_db=snr_db)
        R_e = apply_drift(Rd, float(d), rng)
        acc_e = _match_templates(normalize_response(R_e), labels_d, tmpl, uniq)
        R_b, frac = biological_renewal(Rd, apply_drift(Rd, float(d), rng),
                                       float(d), rng=rng)
        acc_b = _match_templates(normalize_response(R_b), labels_d, tmpl, uniq)
        out.append((d, acc_e, acc_b, frac))
    return out


def _match_templates(F: np.ndarray, labels: np.ndarray,
                     tmpl: np.ndarray, uniq: np.ndarray) -> float:
    """用【第0天建的模板库】匹配当前样本，返回正确率。"""
    correct = 0
    for i in range(len(F)):
        d = np.linalg.norm(tmpl - F[i], axis=1)
        correct += (uniq[int(np.argmin(d))] == labels[i])
    return correct / len(F)


# ================================================================
# 四、温湿度
# ================================================================
def env_effect(R: np.ndarray, rh: float = 0.5, temp_c: float = 25.0,
               rh_ref: float = 0.5, temp_ref: float = 25.0) -> np.ndarray:
    """★ MOS 对温湿度强依赖（未补偿时）。"""
    f = 1.0 + RH_SENS * (rh - rh_ref) + TEMP_SENS * (temp_c - temp_ref) / 10.0
    return R * f


def env_compensate(R: np.ndarray, rh: float, temp_c: float,
                   rh_ref: float = 0.5, temp_ref: float = 25.0) -> np.ndarray:
    """★ 补偿：除以已知的环境因子（前提是你【测了】温湿度）。"""
    f = 1.0 + RH_SENS * (rh - rh_ref) + TEMP_SENS * (temp_c - temp_ref) / 10.0
    return R / f


# ================================================================
# 五、适应（生物）
# ================================================================
def olfactory_adaptation(t_s: np.ndarray, tau: float = 20.0,
                         floor: float = 0.15) -> np.ndarray:
    """★ 嗅觉适应：持续暴露响应指数衰减到 floor。

    ★ REAL：时间常数数秒~数分钟，且【不会完全归零】
    """
    return floor + (1.0 - floor) * np.exp(-np.asarray(t_s, float) / tau)


def sensor_saturation(t_s: np.ndarray, tau: float = T90_RESP_S) -> np.ndarray:
    """★ 电子鼻：上升到饱和，【不衰减】（这是与生物适应的关键区别）。"""
    return 1.0 - np.exp(-np.asarray(t_s, float) / tau)


def recovery(t_s: np.ndarray, tau: float = T90_RECOV_S) -> np.ndarray:
    return np.exp(-np.asarray(t_s, float) / tau)
