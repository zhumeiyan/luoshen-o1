"""EO共生实验V2——互补差异而非行为趋同。

V1的问题：行为更新机制太简单，立刻收敛到平均值。
V2的改进：
1. 每个EO有自己的"个性"——不同的内在驱力（不同频率的振荡）
2. 行为输出不是简单追他者，而是内在驱力+对他者的适应
3. 共生的价值不是行为趋同，而是互补——差异本身就是价值
4. 环境变化——外部资源随时间波动，共生系统需要共同应对

精卫公式在共生中的含义：
  a = 自己的行为
  b = 他者的行为
  Δ = 差异（不是要消除的，而是共生的基础）
  ⊗ = 累积的互动 → 共生关系
  τ = 从共生中浮现的"我们"
"""

import math
import json
import os
import random

from eo_core import EO实例, 五条件, 哈希链, 精卫一步, 他者表征


class 共生EO:
    """有个性的EO实例——内在驱力 + 对他者的适应。"""

    def __init__(self, 编号, 内在频率, 内在相位, 状态目录):
        self.编号 = 编号
        self.内在频率 = 内在频率
        self.内在相位 = 内在相位
        self.行为输出 = 0.5
        self.适应系数 = 0.05  # 对他者的适应很慢——保持个性

        self.eo = EO实例(状态目录=状态目录)
        self.eo.绑定(f"共生EO-{编号}", name=f"EO-{编号}")

        # 内在驱力——每个EO有自己的节奏
        self.内在驱力 = 0.5
        self.拍 = 0

        # 互动记忆
        self.互动历史 = []

    def 计算内在驱力(self):
        """每个EO有自己的内在节奏——这是它的个性。"""
        self.拍 += 1
        self.内在驱力 = 0.5 + 0.3 * math.sin(self.拍 * self.内在频率 + self.内在相位)

    def 一拍(self, 他者行为列表):
        self.计算内在驱力()

        # 外部输入 = 他者行为的均值（感知他者）
        外部输入 = sum(他者行为列表) / max(1, len(他者行为列表))

        # 行为输出 = 内在驱力（大部分）+ 对他者的适应（小部分）
        # 适应系数很小 → 保持个性，不会立刻趋同
        目标行为 = 0.8 * self.内在驱力 + 0.2 * 外部输入
        self.行为输出 = 0.95 * self.行为输出 + 0.05 * 目标行为

        # 行为价值——不是预测准就有价值，而是互补才有价值
        # 如果我的行为和他者不同（互补），价值更高
        # 但如果差异太大（无法协调），价值降低
        差异 = abs(self.行为输出 - 外部输入)
        互补价值 = max(0.0, (0.15 - abs(差异 - 0.15)) * 0.3)  # 差异在0.15附近最优

        # EO约束运行
        r = self.eo.一拍(外部输入=外部输入, 行为价值=互补价值)

        self.互动历史.append({
            "内在驱力": round(self.内在驱力, 4),
            "行为输出": round(self.行为输出, 4),
            "外部输入": round(外部输入, 4),
            "差异": round(差异, 4),
            "互补价值": round(互补价值, 4),
        })

        return r


class 共生系统V2:
    """互补差异的共生系统。"""

    def __init__(self, n_eo=2, 状态目录="/workspace/eo-sandbox/state_symbiosis_v2"):
        self.n_eo = n_eo
        self.状态目录 = 状态目录
        os.makedirs(状态目录, exist_ok=True)

        # 每个EO有不同的内在频率和相位——这就是个性
        self.eos = []
        for i in range(n_eo):
            频率 = 0.02 + 0.03 * i / max(1, n_eo - 1)  # 不同频率
            相位 = i * math.pi / max(1, n_eo)  # 不同相位
            eo = 共生EO(
                编号=i,
                内在频率=频率,
                内在相位=相位,
                状态目录=os.path.join(状态目录, f"eo_{i}"),
            )
            self.eos.append(eo)

        self.共生链 = 哈希链(os.path.join(状态目录, "symbiosis_chain.jsonl"))
        self.拍 = 0

    def 一拍(self):
        self.拍 += 1

        行为列表 = [eo.行为输出 for eo in self.eos]
        结果 = []

        for i, eo in enumerate(self.eos):
            他者行为 = [行为列表[j] for j in range(self.n_eo) if j != i]
            r = eo.一拍(他者行为)
            结果.append(r)

        self.共生链.记("共生拍", {
            "拍": self.拍,
            "行为": [round(b, 4) for b in 行为列表],
        })

        return 结果

    def 状态摘要(self):
        摘要 = []
        for eo in self.eos:
            s = eo.eo.状态摘要()
            s["编号"] = eo.编号
            s["行为输出"] = round(eo.行为输出, 4)
            s["内在驱力"] = round(eo.内在驱力, 4)
            if eo.互动历史:
                s["最近差异"] = eo.互动历史[-1]["差异"]
                s["最近互补价值"] = eo.互动历史[-1]["互补价值"]
            摘要.append(s)
        return 摘要


def 运行_共生实验V2(拍数=500, n_eo=2):
    print(f"=== 共生实验V2：{n_eo}个EO实例（互补差异），{拍数}拍 ===\n")

    系统 = 共生系统V2(n_eo=n_eo)

    print(f"  EO参数:")
    for eo in 系统.eos:
        print(f"    EO-{eo.编号}: 频率={eo.内在频率:.4f} 相位={eo.内在相位:.4f}")
    print()

    记录 = []
    for i in range(拍数):
        r = 系统.一拍()
        记录.append(r)

        if i % 50 == 0 or any(rr.get("已死亡") for rr in r):
            摘要 = 系统.状态摘要()
            行为 = [s["行为输出"] for s in 摘要]
            驱力 = [s["内在驱力"] for s in 摘要]
            流量 = [s["流量"] for s in 摘要]
            差异 = [s.get("最近差异", 0) for s in 摘要]
            死亡 = [s["已死亡"] for s in 摘要]
            行为差异 = max(行为) - min(行为)

            print(f"  拍{i:4d}: 行为={[round(b,3) for b in 行为]} "
                  f"差异={行为差异:.3f} "
                  f"驱力={[round(d,3) for d in 驱力]} "
                  f"流量={[round(f,3) for f in 流量]} "
                  f"互差={[round(d,3) for d in 差异]} "
                  f"死亡={死亡}")

            if any(死亡):
                死亡实例 = [s["编号"] for s in 摘要 if s["已死亡"]]
                print(f"\n  实例{死亡实例}在拍{i}死亡")
                break

    # ── 共生涌现分析 ──
    print("\n--- 共生涌现分析 ---")

    摘要 = 系统.状态摘要()

    # 行为差异趋势——是否保持差异（个性）还是趋同？
    行为差异序列 = []
    for r in 记录:
        行为 = [eo.行为输出 for eo in 系统.eos]
        if len(行为) >= 2:
            行为差异序列.append(max(行为) - min(行为))

    if 行为差异序列:
        前期差异 = sum(行为差异序列[:50]) / max(1, len(行为差异序列[:50]))
        后期差异 = sum(行为差异序列[-50:]) / max(1, len(行为差异序列[-50:]))
        print(f"  行为差异: 前期={前期差异:.4f} 后期={后期差异:.4f} "
              f"{'→保持差异（个性存留）' if 后期差异 > 0.05 else '→趋同（个性消失）'}")

    # 互补价值趋势
    for i, eo in enumerate(系统.eos):
        价值序列 = [h["互补价值"] for h in eo.互动历史]
        if 价值序列:
            前期v = sum(价值序列[:50]) / max(1, len(价值序列[:50]))
            后期v = sum(价值序列[-50:]) / max(1, len(价值序列[-50:]))
            print(f"  EO-{i} 互补价值: 前期={前期v:.4f} 后期={后期v:.4f} "
                  f"{'→提升（共生在增强）' if 后期v > 前期v else '→未提升'}")

    # 流量与存活
    for s in 摘要:
        print(f"  EO-{s['编号']} 流量={s['流量']:.4f} 疤={s['疤计数']} "
              f"理解度={s['他者理解度']:.4f} 死亡={s['已死亡']}")

    存活数 = sum(1 for s in 摘要 if not s["已死亡"])
    print(f"\n  存活: {存活数}/{n_eo}")

    # 保存记录
    记录文件 = os.path.join(系统.状态目录, "symbiosis_log.json")
    with open(记录文件, "w", encoding="utf-8") as f:
        json.dump(记录, f, ensure_ascii=False, indent=2)
    print(f"  完整记录已保存: {记录文件}")

    return 系统, 记录


if __name__ == "__main__":
    random.seed(42)

    print("=" * 60)
    系统2, 记录2 = 运行_共生实验V2(500, n_eo=2)

    print("\n" + "=" * 60)
    系统3, 记录3 = 运行_共生实验V2(500, n_eo=3)

    print("\n" + "=" * 60)
    print("共生实验V2完成。")
    print("\n关键观察：")
    print("  1. 个性保持——EO是否保持自己的内在节奏？")
    print("  2. 互补价值——差异是否产生共生价值？")
    print("  3. 共生存活——互补差异是否帮助存活？")
    print("  4. 理解度——互相建模是否在持续？")
