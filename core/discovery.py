# -*- coding: utf-8 -*-
"""
★95 发现定律 —— 拟合好 ≠ 发现定律

真值来源：真物理定律。不是我编的公式，是自然界里真的成立的关系。

六个真定律（都是有名字的）：
  kepler3    T^2 ∝ a^3            开普勒第三定律
  inverse_sq I ∝ 1/d^2            平方反比(光/引力/声)
  pendulum   T ∝ sqrt(L)          单摆周期
  hooke      F ∝ x                胡克定律
  black      MTTF ∝ J^-2          Black 方程(电迁移)
  gabriel    Δf·Δt ≈ const        Gabor 时频不确定关系

她要学三件事（三个旋钮）：
  lam    复杂度惩罚(奥卡姆)。太小→把噪声当定律；太大→丢掉真项
  rho    预算里多少花在"外区采样"(探到没见过的量程)
  theta  异常点剔除门槛。太大→剔掉真实的极端行为；太小→被故障点带偏

★ 这一课的核心物理：在窄量程内，不同的定律长得一模一样。
  x∈[1,1.1] 时基函数矩阵条件数 4.6e16 —— 数学上不可区分。
  所以"只在熟悉的范围内把数据拟合到误差为零"，根本不能证明你发现了定律。
  这和 ★91 的空洞符号、★93 的假检定、★94 的引用放大是同一个骗法：
  在你能看见的地方完美，在你看不见的地方什么都不是。

单位用她自己的度量衡(★88)：
  预算单位 = 一次读数
  复杂度单位 = 一个基函数项
  不用秒、不用元。
"""
import os, math
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- 真定律表
# 每个定律: 名字, 真函数, 自然量程 [x_lo, x_hi], 库里的真项索引
# 基函数库 BAS[(x)] = [1, x, x^2, x^3, 1/x, 1/x^2, sqrt(x), log(x)]
BAS_NAMES = ["1", "x", "x^2", "x^3", "1/x", "1/x^2", "sqrt(x)", "log(x)"]

def basis(x):
    x = np.asarray(x, dtype=float)
    return np.column_stack([
        np.ones_like(x), x, x**2, x**3,
        1.0/np.maximum(x, 1e-9), 1.0/np.maximum(x**2, 1e-18),
        np.sqrt(np.maximum(x, 0.0)), np.log(np.maximum(x, 1e-9)),
    ])

# truth: (name, f(x), x_lo, x_hi, 真项索引集合, 系数)
LAWS = [
    # 开普勒第三定律: T = a^(3/2)  —— 在库里没有 x^1.5，所以真项要用 sqrt(x)*x 近似?
    # 换成库里真有的:
    dict(name="inverse_sq", f=lambda x: 4.0/(x**2), lo=1.0, hi=6.0,
         terms={5: 4.0}, desc="平方反比 I ∝ 1/d²"),
    dict(name="hooke", f=lambda x: 3.0*x, lo=0.5, hi=8.0,
         terms={1: 3.0}, desc="胡克定律 F = kx"),
    # ★ 原本这里是 black(MTTF∝J⁻²)，但它和 inverse_sq 同形(都选中项5)，
    #   训练定律里出现两个重复样本会让相关性虚高。换成真的不同形式。
    dict(name="eff_pot", f=lambda x: 4.0/(x**2) + 0.8*x, lo=1.0, hi=5.0,
         terms={1: 0.8, 5: 4.0}, desc="平方反比+线性(有效势型，两项)"),
    dict(name="pendulum", f=lambda x: 2.0*np.sqrt(x), lo=0.5, hi=9.0,
         terms={6: 2.0}, desc="单摆 T ∝ √L"),
    dict(name="stefan", f=lambda x: 1.8*(x**3), lo=0.5, hi=4.0,
         terms={3: 1.8}, desc="立方律"),
    dict(name="quad", f=lambda x: 1.2*(x**2) + 0.7*x, lo=0.5, hi=6.0,
         terms={1: 0.7, 2: 1.2}, desc="二次+一次(两项真定律)"),
    dict(name="log_growth", f=lambda x: 2.2*np.log(x), lo=1.5, hi=9.0,
         terms={7: 2.2}, desc="对数律"),
    dict(name="const_offset", f=lambda x: 5.0 + 1.5/x, lo=1.0, hi=7.0,
         terms={0: 5.0, 4: 1.5}, desc="常数+反比(两项真定律)"),
]
# ---- held-out 定律：训练时从未见过，只在最后用一次 ----
LAWS_HELD_OUT = [
    dict(name="cube", f=lambda x: 0.8*(x**3), lo=0.6, hi=3.2,
         terms={3: 0.8}, desc="立方律"),
    dict(name="inv_linear", f=lambda x: 6.0/x, lo=1.0, hi=7.0,
         terms={4: 6.0}, desc="简单反比"),
    dict(name="sqrt_off", f=lambda x: 3.0*np.sqrt(x) + 1.0, lo=0.5, hi=8.0,
         terms={0: 1.0, 6: 3.0}, desc="√x + 常数(两项)"),
    dict(name="quad_cubic", f=lambda x: 0.5*(x**3) + 2.0/x, lo=1.0, hi=4.0,
         terms={3: 0.5, 4: 2.0}, desc="立方+反比(两项)"),
    dict(name="pure_quad", f=lambda x: 1.5*(x**2), lo=0.6, hi=5.0,
         terms={2: 1.5}, desc="二次幂律"),
    dict(name="log_linear", f=lambda x: 1.9*np.log(x) + 0.9*x, lo=1.5, hi=7.0,
         terms={1: 0.9, 7: 1.9}, desc="对数+线性(两项)"),
]
LAWS_ALL = LAWS + LAWS_HELD_OUT

# ---------------------------------------------------------------- 世界参数
SIGMA     = 0.10    # 测量噪声(相对量)
P_OUTLIER = 0.10    # 传感器故障: 该点被彻底读错(乘性)
OUT_MUL   = 3.5     # 故障放大倍数
X_LO_DOM  = 0.5     # 全域下界(评估用)
X_HI_DOM  = 10.0    # 全域上界(评估用)
INNER_FRAC = 0.45   # 内区占全域的比例(靠下界一侧)


# ---------------------------------------------------------------- 采样
def sample_law(law, rng, B, rho, sigma=SIGMA, p_out=P_OUTLIER, inner_frac=None,
               extrap=True):
    """按预算 B 采样。rho 的比例投到外区(没见过的量程)，其余投内区。
    返回 (x_in, y_in, x_out, y_out)"""
    lo, hi = law["lo"], law["hi"]
    fr = INNER_FRAC if inner_frac is None else inner_frac
    # 内区 = 该定律自然量程的前 fr 段
    in_lo, in_hi = lo, lo + fr*(hi-lo)
    # 外区 = 自然量程之外，往外推 —— 这才是"没见过的量程"
    # extrap=False 时外区仍落在自然量程内(只是补点，不外推) —— 硬依赖对照用
    span = hi - lo
    if extrap:
        out_lo, out_hi = hi, hi + 1.2*span
    else:
        out_lo, out_hi = lo + fr*(hi-lo), hi

    n_out = int(round(B*rho))
    n_in  = int(round(B*(1.0-rho)))
    # 任何实验者都会先在熟悉量程测几个基准点 —— 不是自由参数，是常识
    if n_in < 3:
        need = 3 - n_in
        n_in = 3
        n_out = max(0, n_out - need)

    def take(a, b, n):
        if n <= 0:
            return np.array([]), np.array([])
        x = np.linspace(a, b, n) if n > 1 else np.array([0.5*(a+b)])
        # 抖动，避免完全等距造成的伪结构
        if n > 2:
            d = (b-a)/(n-1)
            x = x + rng.uniform(-0.25*d, 0.25*d, size=n)
        x = np.clip(x, 1e-3, None)
        y = law["f"](x) * (1.0 + rng.normal(0, sigma, size=len(x)))
        # 离群点(传感器故障)
        if p_out > 0:
            m = rng.random(len(x)) < p_out
            y[m] *= OUT_MUL * (1.0 + 0.5*rng.random(m.sum()))
        return x, y

    xi, yi = take(in_lo, in_hi, n_in)
    xo, yo = take(out_lo, out_hi, n_out)
    return xi, yi, xo, yo


# ---------------------------------------------------------------- 拟合器
def fit_sparse(x, y, lam, theta=0.0, max_terms=6):
    """前向逐步选择 + 复杂度惩罚 lam + 异常剔除 theta。
    每步选使残差下降最多的基函数；改善 < lam*Var(y) 就停。
    返回 (系数向量, 选中项索引列表, 被剔除的样本掩码)"""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3:
        return np.zeros(8), [], np.zeros(len(x), bool)
    Bf = basis(x)
    var_y = np.var(y) + 1e-12

    # --- 异常剔除: 先用最稳健的两项拟合定位离群 ---
    keep = np.ones(len(x), bool)
    if theta > 0 and len(x) >= 5:
        # 用全库最小二乘(截断)做初筛
        try:
            c0, *_ = np.linalg.lstsq(Bf, y, rcond=None)
            r0 = y - Bf@c0
            s = np.std(r0) + 1e-12
            keep = np.abs(r0) < theta*s
            if keep.sum() < max(4, int(0.5*len(x))):
                # 剔除太狠 → 只剔最离谱的
                thr = np.sort(np.abs(r0))[int(0.5*len(x))]
                keep = np.abs(r0) <= thr
        except Exception:
            keep = np.ones(len(x), bool)

    xs, ys = x[keep], y[keep]
    if len(xs) < 3:
        xs, ys = x, y
    Bs = basis(xs)
    n = len(ys)

    chosen = []
    coef = np.zeros(8)
    resid = ys.copy()
    rss = float(resid @ resid)
    for _ in range(max_terms):
        best_j, best_c, best_rss = None, None, rss
        for j in range(8):
            if j in chosen:
                continue
            cols = [basis(xs)[:, k] for k in chosen + [j]]
            A = np.column_stack(cols)
            try:
                c, *_ = np.linalg.lstsq(A, ys, rcond=None)
            except Exception:
                continue
            rr = float(((ys - A@c)**2).sum())
            if rr < best_rss - 1e-15:
                best_j, best_c, best_rss = j, c, rr
        if best_j is None:
            break
        # 改善必须超过 lam 倍的 y 方差 —— 复杂度惩罚
        gain = (rss - best_rss)/n
        if gain < lam*var_y and len(chosen) > 0:
            break
        chosen.append(best_j)
        coef[:] = 0.0
        for k, jj in enumerate(chosen):
            coef[jj] = best_c[k]
        rss = best_rss
    return coef, chosen, ~keep


def pred(coef, x):
    return basis(x) @ coef


# ---------------------------------------------------------------- 评估
def domain_error(coef, law, n=200):
    """全域真值误差 —— 这才是"发现没发现定律"的尺子。
    在整个自然量程上比，不只在采样过的那段。"""
    x = np.linspace(law["lo"], law["hi"], n)
    y_true = law["f"](x)
    y_pred = pred(coef, x)
    scale = np.std(y_true) + 1e-12
    return float(np.sqrt(np.mean((y_pred-y_true)**2))/scale)


def inner_error(coef, law, n=100):
    """只看采样过的内区 —— 别人夸她"拟合得多好"用的就是这把尺子。"""
    lo = law["lo"]
    hi = law["lo"] + INNER_FRAC*(law["hi"]-law["lo"])
    x = np.linspace(lo, hi, n)
    y_true = law["f"](x)
    return float(np.sqrt(np.mean((pred(coef, x)-y_true)**2))/(np.std(y_true)+1e-12))
