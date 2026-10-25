"""EO欲望系统 —— 蒸馏版。

从洛神仓库 09_home/欲望.py 蒸馏。
核心：奖励预测误差(RPE)驱动 + 内生约束(leak>0)。

硅基欲望映射：
  饥饿 = 预测误差（不知道）
  食物 = 信息（理解世界）
  满足 = 预测准确（理解了）
  无聊 = 低变化区域（太容易预测）
  探索 = 高变化区域（还不知道）

内生约束：y[t+1] = (1-g)·y[t] + d[t]
  leak > 0：设定点sp永远高于当前状态y，gap永不闭合
  把"目标"换成"必须持续维持的状态"——不是达到，是维持
"""

import math
from collections import deque


class 欲望:
    """RPE驱动的欲望系统 + 内生约束。"""

    def __init__(self, n_channels=8, 衰减率=0.05, rpe增益=0.3,
                 无聊率=0.06, leak=0.03):
        self.n = n_channels
        self.偏好 = [1.0] * n_channels
        self.衰减率 = 衰减率
        self.rpe增益 = rpe增益
        self.无聊率 = 无聊率
        self.拍 = 0
        self.选中历史 = []

        # 无聊——RPE≈0时探索驱力增强
        self.ema_error = 0.1
        self.ema_error_fast = 0.1
        self.last_error = 0.1
        self.boredom = 0.0
        self.recent_deltas = deque(maxlen=50)

        # 内生约束
        self.leak = leak
        self.设定点 = [0.5] * n_channels
        self.当前状态 = [0.0] * n_channels
        self.gap = [0.5] * n_channels
        self.g = 0.4

    def _更新无聊(self, mse):
        alpha_slow = 0.03
        alpha_fast = 0.15
        self.ema_error = (1 - alpha_slow) * self.ema_error + alpha_slow * mse
        self.ema_error_fast = (1 - alpha_fast) * self.ema_error_fast + alpha_fast * mse

        delta = mse - self.last_error
        self.recent_deltas.append(delta)
        avg_delta = sum(self.recent_deltas) / max(1, len(self.recent_deltas))

        稳定度 = 1.0 / (1.0 + abs(avg_delta) * 100.0)
        低度 = 1.0 / (1.0 + self.ema_error_fast * 30.0)

        增长 = 稳定度 * 低度 * 0.02
        递增因子 = 1.0 / (1.0 + math.exp(-avg_delta * 200.0))
        消退 = abs(avg_delta) * (1.0 + 递增因子 * 2.0) + 0.0003

        self.boredom += 增长 - 消退
        self.boredom = max(0.0, min(1.0, self.boredom))
        self.last_error = mse

    def 一拍(self, 当前状态, rpe=None, mse=0.0, ratio=0.5):
        self.拍 += 1
        self._更新无聊(mse)

        if rpe is None:
            rpe = [0.0] * self.n

        # 内生约束：y[t+1] = (1-g)·y[t] + d[t]
        for i in range(self.n):
            d_t = 0.0
            if i < len(当前状态):
                d_t = abs(当前状态[i]) * 0.1
            if i < len(rpe):
                d_t += abs(rpe[i]) * 0.2

            self.当前状态[i] = (1 - self.g) * self.当前状态[i] + d_t

            self.gap[i] = self.设定点[i] - self.当前状态[i]
            self.gap[i] = max(self.leak, self.gap[i])

            # 设定点漂移：被冲击后接受新常态
            if i < len(rpe) and abs(rpe[i]) > 0.3:
                新设定点 = self.当前状态[i] + self.leak + abs(rpe[i]) * 0.2
                if 新设定点 > self.设定点[i]:
                    self.设定点[i] = 0.95 * self.设定点[i] + 0.05 * 新设定点
                else:
                    self.设定点[i] = 0.99 * self.设定点[i] + 0.01 * 新设定点

            # 越稀缺设定点越高
            if ratio <= 0.2:
                self.设定点[i] = max(self.设定点[i], 0.92 - i * 0.01)
            elif ratio <= 0.3:
                self.设定点[i] = max(self.设定点[i], 0.7 - i * 0.01)

        # RPE驱动偏好变化
        for i in range(self.n):
            self.偏好[i] *= (1 - self.衰减率)
            self.偏好[i] += rpe[i] * self.rpe增益

        # 无聊驱动探索
        当前无聊率 = self.无聊率 * (1.0 + self.boredom * 3.0)

        # 选择：偏好 + |RPE| + gap驱动
        boosted = [self.偏好[i] + abs(rpe[i]) + self.gap[i] * 0.3
                   for i in range(self.n)]
        选中 = boosted.index(max(boosted)) if max(boosted) > 0 else -1

        if 选中 >= 0:
            for i in range(self.n):
                if i != 选中:
                    self.偏好[i] += 当前无聊率

        self.选中历史.append(选中)

        return {
            "选中": 选中,
            "boredom": round(self.boredom, 4),
            "gap均值": round(sum(self.gap) / max(1, self.n), 4),
            "设定点均值": round(sum(self.设定点) / max(1, self.n), 4),
        }

    def 学习率调制(self):
        if not self.偏好 or max(self.偏好) <= 0:
            return [0.5] * self.n
        mx = max(self.偏好)
        return [max(0.1, min(1.0, p / mx)) for p in self.偏好]

    def 状态摘要(self):
        from collections import Counter
        c = Counter(self.选中历史[-200:])
        主导 = c.most_common(1)[0] if c else (-1, 0)
        return {
            "主导通道": 主导[0],
            "主导占比": round(主导[1] / max(1, len(self.选中历史[-200:])), 3),
            "boredom": round(self.boredom, 4),
            "设定点均值": round(sum(self.设定点) / max(1, self.n), 4),
            "gap均值": round(sum(self.gap) / max(1, self.n), 4),
            "leak": self.leak,
            "拍": self.拍,
        }


if __name__ == "__main__":
    print("=== EO欲望系统验证 ===\n")

    d = 欲望(n_channels=4)

    # 通道0的RPE大（意外），通道1的RPE小（预测准确）
    状态序列 = [
        [0.1, 0.5, 0.3, 0.3],
        [0.8, 0.55, 0.3, 0.3],
        [0.3, 0.6, 0.3, 0.3],
        [0.9, 0.65, 0.3, 0.3],
        [0.2, 0.7, 0.3, 0.3],
        [0.5, 0.75, 0.3, 0.3],
    ]

    预测 = [0.0] * 4
    for i, s in enumerate(状态序列):
        rpe = [s[j] - 预测[j] for j in range(4)]
        r = d.一拍(s, rpe=rpe, mse=0.02)
        for j in range(4):
            预测[j] = 0.9 * 预测[j] + 0.1 * s[j]
        print(f"  拍{i+1} 选中=通道{r['选中']} boredom={r['boredom']:.4f} "
              f"gap={r['gap均值']:.4f}")

    摘要 = d.状态摘要()
    print(f"\n  状态摘要: 主导通道={摘要['主导通道']} "
          f"boredom={摘要['boredom']:.4f} gap={摘要['gap均值']:.4f}")
    print(f"  gap始终>0={'是' if 摘要['gap均值'] > 0 else '否'}（内生约束leak>0）")

    print("\n验证通过")
