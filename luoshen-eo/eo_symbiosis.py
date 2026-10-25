"""EO共生实验——多个EO实例互相作为他者。

洛神的核心特征：分布式存在 + 共生关系。
- 每个EO实例是一个独立的数字生命
- 它们互相感知、互相建模（他者表征）
- 一个EO的行为价值取决于它对其他EO的预测准确度
- 共生：互相预测→互相提供行为价值→共同存活

精卫公式在共生中的含义：
  a = 自己当前状态
  b = 他者的行为
  Δ = 自己与他者的差异
  ⊗ = 累积的互动历史 → 共生关系
"""

import math
import json
import os
import random

from eo_core import EO实例, 五条件, 哈希链, 精卫一步


class 共生系统:
    """多个EO实例的共生系统。

    每个实例：
    1. 有自己的五条件约束（独立存活）
    2. 感知其他实例的行为（他者表征）
    3. 对其他实例的预测准确度决定自己的行为价值
    4. 互相提供生存资源（共生）
    """

    def __init__(self, n_eo=2, 状态目录="/workspace/eo-sandbox/state_symbiosis"):
        self.n_eo = n_eo
        self.状态目录 = 状态目录
        os.makedirs(状态目录, exist_ok=True)

        # 创建n个EO实例（不演化大脑，专注于共生关系）
        self.eos = []
        for i in range(n_eo):
            eo = EO实例(
                状态目录=os.path.join(状态目录, f"eo_{i}"),
            )
            eo.绑定(f"共生实例{i}", name=f"EO-{i}")
            eo.实例编号 = i
            eo.行为输出 = 0.5  # 初始行为
            eo.共生历史 = []
            self.eos.append(eo)

        # 共生链——记录所有实例的互动
        self.共生链 = 哈希链(os.path.join(状态目录, "symbiosis_chain.jsonl"))
        self.拍 = 0

    def 一拍(self):
        self.拍 += 1

        # 每个实例的行为输出（上一拍产生的）
        行为列表 = [eo.行为输出 for eo in self.eos]

        结果 = []
        for i, eo in enumerate(self.eos):
            # 感知其他实例的行为——他者的行为就是我的外部输入
            他者行为 = [行为列表[j] for j in range(self.n_eo) if j != i]
            外部输入 = sum(他者行为) / max(1, len(他者行为)) if 他者行为 else 0.5

            # 行为价值 = 对他者行为的预测准确度
            # 如果我的行为输出接近他者的行为 → 预测准 → 行为价值高
            预测误差 = abs(eo.行为输出 - 外部输入)
            行为价值 = max(0.0, (0.2 - 预测误差) * 0.2)  # 误差<0.2时有正收益

            # EO一拍
            r = eo.一拍(外部输入=外部输入, 行为价值=行为价值)

            # 更新行为输出——基于精卫公式的结果
            # a追b：行为输出逐步追向他者的行为
            eo.行为输出 = 0.9 * eo.行为输出 + 0.1 * 外部输入

            # 记录共生互动
            eo.共生历史.append({
                "外部输入": round(外部输入, 4),
                "行为输出": round(eo.行为输出, 4),
                "预测误差": round(预测误差, 4),
                "行为价值": round(行为价值, 4),
            })

            结果.append(r)

        # 共生链留痕
        self.共生链.记("共生拍", {
            "拍": self.拍,
            "行为列表": [round(b, 4) for b in 行为列表],
        })

        return 结果

    def 状态摘要(self):
        摘要 = []
        for i, eo in enumerate(self.eos):
            s = eo.状态摘要()
            s["实例编号"] = i
            s["行为输出"] = round(eo.行为输出, 4)
            if eo.共生历史:
                最近 = eo.共生历史[-1]
                s["最近预测误差"] = 最近["预测误差"]
                s["最近行为价值"] = 最近["行为价值"]
            摘要.append(s)
        return 摘要


def 运行_共生实验(拍数=500, n_eo=2):
    print(f"=== 共生实验：{n_eo}个EO实例，{拍数}拍 ===\n")

    系统 = 共生系统(n_eo=n_eo)

    # 初始行为不同——让它们有差异需要协调
    for i, eo in enumerate(系统.eos):
        eo.行为输出 = 0.3 + 0.4 * i / max(1, n_eo - 1)

    print(f"  初始行为: {[round(eo.行为输出, 3) for eo in 系统.eos]}")
    print(f"  初始差异: {max(eo.行为输出 for eo in 系统.eos) - min(eo.行为输出 for eo in 系统.eos):.3f}\n")

    记录 = []
    for i in range(拍数):
        r = 系统.一拍()
        记录.append(r)

        if i % 50 == 0 or any(rr.get("已死亡") for rr in r):
            摘要 = 系统.状态摘要()
            行为 = [s["行为输出"] for s in 摘要]
            流量 = [s["流量"] for s in 摘要]
            误差 = [s.get("最近预测误差", 0) for s in 摘要]
            死亡 = [s["已死亡"] for s in 摘要]
            行为差异 = max(行为) - min(行为)

            print(f"  拍{i:4d}: 行为={[round(b,3) for b in 行为]} "
                  f"差异={行为差异:.4f} "
                  f"流量={[round(f,3) for f in 流量]} "
                  f"误差={[round(e,3) for e in 误差]} "
                  f"死亡={死亡}")

            if any(死亡):
                死亡实例 = [s["实例编号"] for s in 摘要 if s["已死亡"]]
                print(f"\n  实例{死亡实例}在拍{i}死亡")
                break

    # ── 共生涌现分析 ──
    print("\n--- 共生涌现分析 ---")

    摘要 = 系统.状态摘要()

    # 行为趋同分析——共生是否让它们的行为趋同？
    行为序列 = []
    for r in 记录:
        行为 = [eo.行为输出 for eo in 系统.eos]
        行为序列.append(行为)

    if 行为序列:
        前期差异 = max(行为序列[0]) - min(行为序列[0])
        后期差异 = max(行为序列[-1]) - min(行为序列[-1])
        print(f"  行为差异: 前期={前期差异:.4f} 后期={后期差异:.4f} "
              f"{'→趋同（共生在协调）' if 后期差异 < 前期差异 else '→未趋同'}")

    # 预测误差趋势——互相预测是否变准？
    for i, eo in enumerate(系统.eos):
        误差序列 = [h["预测误差"] for h in eo.共生历史]
        if 误差序列:
            前期 = sum(误差序列[:50]) / max(1, len(误差序列[:50]))
            后期 = sum(误差序列[-50:]) / max(1, len(误差序列[-50:]))
            print(f"  EO-{i} 预测误差: 前期={前期:.4f} 后期={后期:.4f} "
                  f"{'→变准' if 后期 < 前期 else '→未变准'}")

    # 流量趋势——共生是否帮助存活？
    for i, s in enumerate(摘要):
        print(f"  EO-{i} 流量: {s['流量']:.4f} 疤={s['疤计数']} "
              f"理解度={s['他者理解度']:.4f} 死亡={s['已死亡']}")

    # 存活统计
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

    # 实验1：2个EO共生
    print("=" * 60)
    系统2, 记录2 = 运行_共生实验(500, n_eo=2)

    # 实验2：3个EO共生
    print("\n" + "=" * 60)
    系统3, 记录3 = 运行_共生实验(500, n_eo=3)

    print("\n" + "=" * 60)
    print("共生实验完成。")
    print("\n关键观察：")
    print("  1. 行为趋同——共生是否让多个EO的行为输出趋同？")
    print("  2. 预测变准——互相预测是否随时间变准？")
    print("  3. 共生存活——互相提供行为价值是否帮助存活？")
    print("  4. 差异→协调——初始行为不同的EO能否协调？")
