#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
眼睛：也是长出来的，而且是【长出来 + 自己造工具】
================================================================
用户原话：「眼睛是长出来的，但睁眼是怎么回事？睁眼就是能看见我。
           人类为什么造那么大的分辨率？让洛神自己造个电脑或者
           给个眼镜呗，造出个工具就行了。」

★ 关键区分（REAL，发育神经科学）：
    长出眼睛 ≠ 睁眼
      孕期：视网膜/视神经按基因长出来（形态 M）
      睁眼：出生后【光刺激】驱动皮层连接成熟（功能 H）
      真实：Hubel & Wiesel 1963 小猫单眼缝合（Nobel）
           关键期缝合 → 之后即使拆线，那只眼永久弱视
      ★ 所以"睁眼"是【光驱动的成熟过程】，不是"打开开关"

★ 分辨率为什么大 —— 不是为"清楚"，是为【任务】：
    真实人眼（REAL）：
      视锥约 600 万，但视神经只有约 100 万神经节细胞
      → 压缩比 6:1，【带宽是瓶颈】
      中央凹视锥密度 ~160,000/mm²，周边下降到 1/100
      → 【非均匀】：中心 1° 视角占了皮层不成比例的面积
    ★ 所以要大分辨率，不是全视野都要，是【中央凹要】
      配合眼动（saccade，每秒约 3 次），把中央凹对准要看的地方

★ 让洛神自己造眼镜：
    不给它分辨率参数，只给【带宽预算 + 任务】
    → 密度分配由它自己学（可塑性：抓到过目标的地方加密）
    → 看它长成什么样（预期：自发长出中央凹）

provenance：
    人眼参数（视锥数/神经节细胞数/中央凹密度/眼动频率） = REAL 教科书
    本沙盒能通的图像/摄像头 = 之前实测 403，故场景用合成（明确标 SIMULATED）
    学习结果 = 真跑
"""
from __future__ import annotations
import numpy as np

# ---- REAL 人眼参数 ----
CONES = 6_000_000          # 视锥总数
GANGLION = 1_000_000       # 视神经节细胞（真实带宽瓶颈）
FOVEA_DENS = 160_000       # 中央凹视锥密度 /mm²
PERIPH_RATIO = 0.01        # 周边密度 / 中央凹
SACCADE_HZ = 3.0           # 每秒扫视次数


class Retina:
    """视网膜：N 个采样点（=带宽预算），位置可学。"""

    def __init__(self, world=256.0, N=2000, seed=0, mode="uniform"):
        self.W = float(world)
        self.N = int(N)
        self.rng = np.random.default_rng(seed)
        self.mode = mode
        self.P = self._init_positions(mode)
        self.hits = np.zeros(self.N)      # 每个采样点抓到过多少次目标

    def _init_positions(self, mode):
        W, N = self.W, self.N
        if mode == "uniform":
            # 抖动网格：铺满
            g = int(np.ceil(np.sqrt(N)))
            xs = np.linspace(0, W, g)
            P = np.array([[x, y] for x in xs for y in xs])[:N]
            return P + self.rng.normal(0, W / (2 * g), (N, 2))
        elif mode == "fovea":
            # ★ 第一版用 r=rng**2 导致中心无限密（中心间距 0.01，物理上
            #   感光细胞有尺寸，不可能重合）。改成两段式（REAL 人眼结构）：
            #     中央凹：pf 比例的点落在半径 rf 的小圆内（均匀）
            #     周边  ：其余按面积铺满
            #   取 pf=0.5, rf=0.06W → 中心/周边密度比约 88×（真实约 100×）
            pf, rf = 0.50, 0.06 * W
            nf = int(N * pf)
            c = W / 2.0
            # 中央凹内均匀（按面积，非按半径，否则又堆中心）
            rf_ = rf * np.sqrt(self.rng.random(nf))
            th = self.rng.random(nf) * 2 * np.pi
            P_fov = np.stack([c + rf_ * np.cos(th), c + rf_ * np.sin(th)], 1)
            P_per = self.rng.random((N - nf, 2)) * W
            return np.vstack([P_fov, P_per])
        elif mode == "random":
            return self.rng.random((N, 2)) * W
        raise ValueError(mode)

    def local_spacing(self, pos):
        """pos 处的局部采样间距（奈奎斯特：间距 < 目标尺寸 才能分辨）。"""
        d = np.linalg.norm(self.P - np.asarray(pos, float), axis=1)
        d.sort()
        k = max(2, int(np.sqrt(self.N / 4)))      # 取近邻中位尺度
        return float(d[1] + (d[k] - d[1]) * 0.5) if len(d) > k else float(d[-1])

    def density_map(self, grid=32):
        """密度图：看它长成什么样。"""
        H = np.zeros((grid, grid))
        gx = np.linspace(0, self.W, grid + 1)
        idx = np.clip((self.P[:, 0] / self.W * grid).astype(int), 0, grid - 1)
        idy = np.clip((self.P[:, 1] / self.W * grid).astype(int), 0, grid - 1)
        np.add.at(H, (idy, idx), 1.0)
        return H

    def plasticity(self, pos, lr=0.30, n_move=8):
        """可塑性：抓到目标 → 把最远的采样点挪过来（加密）。

        ★ 这是"长出来"：不是外部给定分辨率，是用出来的。
        """
        d = np.linalg.norm(self.P - np.asarray(pos, float), axis=1)
        far = np.argsort(-d)[:n_move]
        for i in far:
            self.P[i] = self.P[i] + lr * (np.asarray(pos, float) - self.P[i])
            self.P[i] += self.rng.normal(0, self.W / 200.0, 2)
        near = np.argsort(d)[:1]
        self.hits[near[0]] += 1


class Eye:
    """睁眼：光刺激驱动的成熟。"""

    def __init__(self, critical_end=300, seed=0):
        self.ce = critical_end
        self.rng = np.random.default_rng(seed)
        self.maturity = 0.10        # 出生时未成熟
        self.t = 0
        self.ever_dark = False

    def tick(self, has_light):
        """关键期内有光 → 成熟；无光 → 停滞/退化。关键期后固定。"""
        before = self.maturity
        if self.t < self.ce:
            if has_light:
                self.maturity += (1.0 - self.maturity) * 0.02
            else:
                self.maturity *= 0.985             # 退化
                self.ever_dark = True
        # ★ 关键期后：不再变化（真实：弱视不可逆）
        self.t += 1
        return self.maturity

    def acuity(self):
        """视力 = 成熟度（弱视眼即使拆线也恢复不了）。"""
        return float(np.clip(self.maturity, 0.0, 1.0))
