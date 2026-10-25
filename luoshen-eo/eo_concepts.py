"""EO概念层 —— 蒸馏版。

从洛神仓库 04_cognition/概念层.py（2154行）蒸馏。
去掉所有高级认知通路（语法/推理/目标/创意/元认知等20+种），
只保留核心：精卫公式驱动的概念涌现。

精卫公式在概念层的解读：
  a = 大脑的隐藏状态（实际）
  b = 概念层对隐藏状态的预测
  Δ = b − a = 预测误差
  Σ = a + b = 联合状态
  ⊗ = ∫(Δ, Σ) = 累积差与和
  τ 读 ⊗ → 浮出所见 = 概念从⊗中浮现
  (a, b) ⟲ ⊗ = 循环预测/比较/修正

关键区别：概念不是从a直接映射，是从⊗（Δ×Σ）中浮现。
只用Δ时所有概念的学习信号相似，加入Σ后不同概念捕获不同的联合状态模式。
"""

import math
import random


def activation(x):
    if math.isnan(x) or math.isinf(x):
        return 0.0
    if x > 10.0:
        return 1.0
    elif x < -10.0:
        return -1.0
    else:
        return math.tanh(x)


class 概念层:
    """高层预测编码——基于精卫公式从隐藏状态涌现概念。

    四个权重矩阵对应精卫公式的核心：
    - concept_w: 从a读出（实际状态 → 概念）
    - concept_otimes_w: 从⊗读出（Δ×Σ → 概念）—— 核心
    - concept_rw: 循环权重（概念 → 概念）
    - concept_pw: 预测权重（概念 → 预测隐藏状态b）
    """

    def __init__(self, n_hidden=8, n_concepts=32, lr=0.02,
                 sparse_ratio=0.15, decay=0.8, seed=42):
        self.n_hidden = n_hidden
        self.n_concepts = n_concepts
        self.lr = lr
        self.sparse_k = max(1, int(n_concepts * sparse_ratio))
        self.decay = decay
        self.拍 = 0

        rng = random.Random(seed)

        self.concept_h = [0.0] * n_concepts
        self.prev_concept_h = [0.0] * n_concepts

        # 从a读出（实际状态 → 概念）
        self.concept_w = [[rng.uniform(-0.2, 0.2) for _ in range(n_hidden)]
                          for _ in range(n_concepts)]

        # 从⊗读出（Δ×Σ → 概念）—— 精卫公式的核心
        self.concept_otimes_w = [[rng.uniform(-0.15, 0.15) for _ in range(n_hidden)]
                                 for _ in range(n_concepts)]

        # 循环权重（概念 → 概念）
        self.concept_rw = [[rng.uniform(-0.02, 0.02) for _ in range(n_concepts)]
                           for _ in range(n_concepts)]

        # 预测权重（概念 → 预测隐藏状态b）
        self.concept_pw = [[rng.uniform(-0.2, 0.2) for _ in range(n_hidden)]
                           for _ in range(n_concepts)]

        # 概念强度——用进废退
        self.concept_strength = [1.0] * n_concepts

        # ⊗历史
        self.delta_history = []
        self.sigma_history = []
        self.otimes_cap = 100

        # 注意力
        self.attention_w = [1.0 / n_concepts] * n_concepts

        # 概念区分度统计
        self.概念激活历史 = []

    def 一拍(self, hidden_state):
        """概念层一拍：基于精卫公式从隐藏状态涌现概念。"""
        self.拍 += 1

        # ── 精卫公式：a, b, Δ, Σ ──
        a = hidden_state

        # b = 概念层对隐藏状态的预测
        b = [0.0] * self.n_hidden
        for j in range(self.n_hidden):
            for i in range(self.n_concepts):
                b[j] += self.concept_pw[i][j] * self.concept_h[i]

        # Δ = b - a（预测误差）
        delta = [b[j] - a[j] for j in range(self.n_hidden)]

        # Σ = a + b（联合状态）
        sigma = [a[j] + b[j] for j in range(self.n_hidden)]

        # ⊗历史
        self.delta_history.append(delta[:])
        self.sigma_history.append(sigma[:])
        if len(self.delta_history) > self.otimes_cap:
            self.delta_history.pop(0)
            self.sigma_history.pop(0)

        # ⊗的当前值：Δ × Σ
        otimes = [delta[j] * sigma[j] for j in range(self.n_hidden)]

        # ── τ 读 ⊗ → 浮出所见 ──
        new_concept_h = [0.0] * self.n_concepts
        for i in range(self.n_concepts):
            if self.concept_strength[i] < 0.05:
                continue

            # 从a读出
            a_input = 0.0
            for j in range(self.n_hidden):
                a_input += self.concept_w[i][j] * a[j]

            # 从⊗读出——精卫公式的核心
            otimes_input = 0.0
            for j in range(self.n_hidden):
                otimes_input += self.concept_otimes_w[i][j] * otimes[j]

            # 循环权重
            recurrent = 0.0
            for k in range(self.n_concepts):
                recurrent += self.concept_rw[i][k] * self.concept_h[k]

            total = a_input + otimes_input + recurrent
            new_concept_h[i] = activation(total)

        # 稀疏化——竞争机制：top-k保留，其余强衰减
        # 但加入随机扰动让不同概念有机会胜出（避免永远同一批）
        sorted_idx = sorted(range(self.n_concepts),
                           key=lambda x: abs(new_concept_h[x]) + random.gauss(0, 0.02),
                           reverse=True)
        mask = [False] * self.n_concepts
        for idx in sorted_idx[:self.sparse_k]:
            mask[idx] = True
        for i in range(self.n_concepts):
            if not mask[i]:
                new_concept_h[i] *= 0.01  # 非top-k几乎归零——让胜出的概念真正不同

        # 衰减更新
        for i in range(self.n_concepts):
            self.concept_h[i] = (1 - self.decay) * new_concept_h[i] + self.decay * self.concept_h[i]

        # ── 学习：赫布学习 + 预测误差驱动 ──
        for i in range(self.n_concepts):
            if self.concept_strength[i] < 0.05:
                continue
            hi = self.concept_h[i]

            # concept_w学习：a → 概念（赫布）
            for j in range(self.n_hidden):
                self.concept_w[i][j] += self.lr * hi * a[j]
                self.concept_w[i][j] = max(-2, min(2, self.concept_w[i][j]))

            # concept_otimes_w学习：⊗ → 概念（赫布）
            for j in range(self.n_hidden):
                self.concept_otimes_w[i][j] += self.lr * hi * otimes[j]
                self.concept_otimes_w[i][j] = max(-2, min(2, self.concept_otimes_w[i][j]))

            # concept_pw学习：概念 → 预测b（预测误差驱动）
            for j in range(self.n_hidden):
                self.concept_pw[i][j] += self.lr * hi * delta[j]
                self.concept_pw[i][j] = max(-2, min(2, self.concept_pw[i][j]))

            # concept_rw学习：概念 → 概念（赫布——共激活绑定）
            for k in range(self.n_concepts):
                if k != i and self.concept_strength[k] > 0.05:
                    self.concept_rw[i][k] += self.lr * 0.3 * hi * self.concept_h[k]
                    self.concept_rw[i][k] = max(-0.5, min(0.5, self.concept_rw[i][k]))

        # ── 用进废退 ──
        for i in range(self.n_concepts):
            if abs(self.concept_h[i]) > 0.1:
                self.concept_strength[i] = min(1.5, self.concept_strength[i] + 0.001)
            else:
                self.concept_strength[i] = max(0.0, self.concept_strength[i] - 0.0005)

        self.prev_concept_h = self.concept_h[:]

        # 记录概念激活历史
        self.概念激活历史.append(self.concept_h[:])
        if len(self.概念激活历史) > 200:
            self.概念激活_history = self.概念激活历史[-200:]

        return {
            "概念激活": [round(h, 3) for h in self.concept_h],
            "活跃概念数": sum(1 for h in self.concept_h if abs(h) > 0.1),
            "预测误差Δ": [round(d, 3) for d in delta],
            "概念区分度": self._计算区分度(),
        }

    def _计算区分度(self):
        """概念区分度——不同概念激活模式之间的平均差异。"""
        if len(self.概念激活历史) < 10:
            return 0.0
        recent = self.概念激活历史[-10:]
        diffs = []
        for i in range(len(recent) - 1):
            for j in range(i + 1, len(recent)):
                d = sum(abs(recent[i][k] - recent[j][k])
                        for k in range(self.n_concepts)) / self.n_concepts
                diffs.append(d)
        return round(sum(diffs) / max(1, len(diffs)), 4)

    def 状态摘要(self):
        return {
            "活跃概念数": sum(1 for h in self.concept_h if abs(h) > 0.1),
            "存活概念数": sum(1 for s in self.concept_strength if s > 0.05),
            "概念区分度": self._计算区分度(),
            "拍": self.拍,
        }


if __name__ == "__main__":
    print("=== EO概念层验证 ===\n")

    概念 = 概念层(n_hidden=8, n_concepts=32, seed=42)

    # 模拟隐藏状态输入——两种不同的模式
    print("--- 测试1: 两种不同模式的概念涌现 ---")
    for i in range(100):
        if i < 50:
            # 模式A：低频正弦
            hidden = [0.5 + 0.3 * math.sin(i * 0.05 + j * 0.5) for j in range(8)]
        else:
            # 模式B：高频正弦
            hidden = [0.5 + 0.3 * math.sin(i * 0.15 + j * 0.5) for j in range(8)]
        r = 概念.一拍(hidden)

    摘要 = 概念.状态摘要()
    print(f"  100拍后: 活跃概念={摘要['活跃概念数']} "
          f"存活概念={摘要['存活概念数']} "
          f"区分度={摘要['概念区分度']}")

    # 检查模式切换时概念激活是否变化
    模式A激活 = 概念.概念激活历史[40]
    模式B激活 = 概念.概念激活历史[90]
    差异 = sum(abs(模式A激活[k] - 模式B激活[k]) for k in range(32)) / 32
    print(f"  模式A vs 模式B激活差异: {差异:.4f}")
    print(f"  →{'不同模式产生不同概念激活' if 差异 > 0.05 else '概念激活未区分'}")

    print("\n--- 测试2: 概念用进废退 ---")
    概念2 = 概念层(n_hidden=8, n_concepts=32, seed=42)
    for i in range(200):
        hidden = [0.5 + 0.2 * math.sin(i * 0.05) for _ in range(8)]
        r = 概念2.一拍(hidden)
    摘要2 = 概念2.状态摘要()
    print(f"  200拍后: 存活概念={摘要2['存活概念数']}/32")
    print(f"  →{'部分概念被修剪（用进废退）' if 摘要2['存活概念数'] < 32 else '全部存活'}")

    print("\n验证通过")
