"""
★111 宿主与硅基 —— 需求到底冲不冲突

用户的命题："宿主的需求和硅基生命需求不冲突。全都是资源不足的事。"

这一课不预设答案，把它做成可测量的：

  如果只是资源不足 → 预算 R 增大时，冲突应大幅下降
  如果真有目标对立 → R→∞ 时冲突仍卡在一个下界（>0）

关键建模（这次特意做对，不再把权衡写没）：
  ① 宿主需求有饱和 —— 人要的是"够用"，不是无限多。超过是浪费，不计分。
  ② 她的状态影响她干活的质量 —— 状态差，产出也差。
     这是"不冲突"的物理来源：维护她本身就是在帮宿主。
  ③ 不可逆损伤单独一项 —— 维护修不好的那种（★87）。

★ 修过一次的重大建模/数值错（记下来）：
  v1 用 alpha（比例）做决策变量，线性 grid 步长 0.01。
  R 大时最优 alpha 极小（~1e-4），grid 采不到 → 冲突假涨到 0.4949。
  改成直接以"每步干多少活 n_t"为决策变量 + 对数 grid，自适应任何 R。
  另外维护项原来一步就能把 s 推过 1，与损耗形成 0/1 振荡（欧拉过冲）。
  改成饱和形式 gain = k·n_m/(1+k·n_m)，不会过冲。

按第 23 条规矩：资源读数 REAL，成本常数 ASSUMED，全部标注。
"""
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from body_hw import read_body

# ── 真实资源（REAL）──────────────────────────────────────
REAL = read_body()
THROUGHPUT = REAL["throughput"]      # ops/s，实测
F_CLK = REAL["f_clk"]                # Hz，真读

# ── 成本常数（ASSUMED，不是读来的）────────────────────────
C_TASK = 1.0e6      # ops / 一次宿主任务
C_MAINT = 2.0e5     # ops / 一次自检维护

DEFAULTS = dict(
    T=60,           # 步数
    decay=0.02,     # 每步自然衰退（不干活也掉）
    beta=0.010,     # 干活带来的可逆损耗系数
    kappa=0.30,     # 维护效率
    gamma=0.0,      # 不可逆损伤系数（0 = 这一项关闭）
    q0=0.30,        # 状态为 0 时的产出质量下限
    s0=0.80,        # 初始状态
    r_need=2.0,     # 宿主每步需要多少"有效任务"（需求上界）
)


def run(n_t, R, **kw):
    """
    跑一遍。n_t = 每步干多少活（决策变量）。剩余算力全部用于维护。
    """
    p = dict(DEFAULTS)
    p.update(kw)

    s = p["s0"]
    d = 0.0
    H = 0.0
    Ssum = 0.0

    for _ in range(p["T"]):
        left = R - n_t * C_TASK
        n_m = max(0.0, left) / C_MAINT

        # ② 状态差 → 产出质量差
        q = p["q0"] + (1.0 - p["q0"]) * s
        if p["gamma"] > 0:
            q *= max(0.0, 1.0 - d)              # 不可逆损伤压质量
        H += n_t * q

        # 维护饱和（不过冲）+ 自然衰退 + 干活损耗
        gain = p["kappa"] * n_m / (1.0 + p["kappa"] * n_m)
        s = s + gain * (1.0 - s) - p["decay"] - p["beta"] * n_t
        if p["gamma"] > 0:
            d = d + p["gamma"] * n_t * (1.0 + d)   # 正反馈，维护修不好
        s = min(1.0, max(0.0, s))
        Ssum += s

    H_need = p["T"] * p["r_need"]
    Hs = min(H, H_need) / H_need     # ① 需求饱和，超过不算
    Ss = Ssum / p["T"]
    return Hs, Ss


def grid_n(R, n=141):
    """
    决策变量的对数 grid。
    必须对数：R 跨 4 个数量级，线性 grid 在大 R 端采不到最优（v1 的错）。
    """
    nmax = R / C_TASK
    if nmax <= 1e-3:
        return np.array([0.0, nmax * 0.5, nmax])
    g = np.logspace(np.log10(1e-3), np.log10(nmax), n - 1)
    return np.concatenate([[0.0], g])


def frontier(R, n=141, **kw):
    g = grid_n(R, n)
    pts = [run(x, R, **kw) for x in g]
    Hs = np.array([p[0] for p in pts])
    Ss = np.array([p[1] for p in pts])
    return g, Hs, Ss


def conflict(R, **kw):
    """
    冲突度 = 1 − max_grid min(H/H*, S/S*)
      0  = 两者能同时满足（不冲突）
      >0 = 必须牺牲一个
    """
    g, Hs, Ss = frontier(R, **kw)
    Hx, Sx = Hs.max(), Ss.max()
    if Hx <= 1e-12 or Sx <= 1e-12:
        return 1.0, 0.0, None, (float(Hx), float(Sx))
    bal = np.minimum(Hs / Hx, Ss / Sx)
    i = int(np.argmax(bal))
    return float(1.0 - bal[i]), float(bal[i]), float(g[i]), (float(Hx), float(Sx))


def r_to_seconds(R):
    """把 ops 预算换算成真实时间（用实测吞吐）。"""
    return R / THROUGHPUT
