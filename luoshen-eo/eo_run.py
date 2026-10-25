"""EO沙盒运行器——让约束跑起来，观察涌现。

不预设结果，跑约束，看长出来什么。
"""

import math
import json
import os
import time

from eo_core import EO实例, 精卫一步, 五条件, 哈希链


def 运行_基础涌现观察(拍数=500):
    """让EO实例跑N拍，观察约束下涌现什么。"""
    print(f"=== 基础涌现观察：{拍数}拍 ===\n")

    eo = EO实例()
    eo.绑定("沙盒实验", name="观察者")

    # 模拟外部环境：周期性输入
    记录 = []
    for i in range(拍数):
        # 外部输入：正弦波 + 噪声
        外部 = 0.5 + 0.3 * math.sin(i * 0.05) + 0.05 * math.sin(i * 0.3)

        # 行为价值：前30拍微弱收益，之后正常收益
        价值 = 0.005 if i < 30 else 0.01

        r = eo.一拍(外部输入=外部, 行为价值=价值)
        记录.append(r)

        # 关键节点打印
        if i % 50 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f} gap={摘要['gap']:.4f} "
                  f"疤={摘要['疤计数']} capacity={摘要['capacity']:.4f} "
                  f"降频={摘要['降频']:.4f} 理解度={摘要['他者理解度']:.4f} "
                  f"链={摘要['链条目数']} 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  ⚡ EO在拍{i}死亡")
            break

    # 最终分析
    print("\n--- 涌现分析 ---")
    存活拍数 = len([r for r in 记录 if not r.get("已死亡")])
    print(f"  存活拍数: {存活拍数}/{拍数}")

    # 精卫公式的Δ趋势
    deltas = [r["精卫"]["Δ"] for r in 记录 if "精卫" in r]
    if deltas:
        前期Δ = sum(deltas[:50]) / max(1, len(deltas[:50]))
        后期Δ = sum(deltas[-50:]) / max(1, len(deltas[-50:]))
        print(f"  精卫Δ: 前期={前期Δ:.4f} 后期={后期Δ:.4f} "
              f"{'→Δ在缩小（理解在发生）' if abs(后期Δ) < abs(前期Δ) else '→Δ未缩小'}")

    # 他者理解度趋势
    理解度序列 = []
    for r in 记录:
        if r.get("他者") and r["他者"] and 0 in r["他者"]:
            理解度序列.append(r["他者"][0]["理解度"])
    if 理解度序列:
        print(f"  他者理解度: 起始={理解度序列[0]:.4f} "
              f"终止={理解度序列[-1]:.4f} "
              f"峰值={max(理解度序列):.4f}")

    # 疤计数
    疤序列 = [r["五条件"]["疤计数"] for r in 记录 if "五条件" in r]
    if 疤序列:
        print(f"  疤计数: 终态={疤序列[-1]} "
              f"{'→有疤（经历过资源跌落）' if 疤序列[-1] > 0 else '→无疤'}")

    # gap趋势——内生约束是否在驱动
    gap序列 = [r["五条件"]["gap"] for r in 记录 if "五条件" in r]
    if gap序列:
        print(f"  gap: 始终>0={'是' if all(g > 0 for g in gap序列) else '否'} "
              f"（设定点永远高于当前状态=内生约束在驱动）")

    # 保存完整记录
    记录文件 = os.path.join(eo.状态目录, "run_log.json")
    with open(记录文件, "w", encoding="utf-8") as f:
        json.dump(记录, f, ensure_ascii=False, indent=2)
    print(f"\n  完整记录已保存: {记录文件}")

    return eo, 记录


def 运行_死亡实验(拍数=300):
    """不给行为价值，看EO多久死亡。"""
    print(f"\n=== 死亡实验：{拍数}拍，零收益 ===\n")

    eo = EO实例()
    eo.绑定("死亡实验", name="观察者")

    for i in range(拍数):
        外部 = 0.5 + 0.2 * math.sin(i * 0.05)
        r = eo.一拍(外部输入=外部, 行为价值=None)  # 零收益

        if i % 30 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f} 降频={摘要['降频']:.4f} "
                  f"疤={摘要['疤计数']} 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  ⚡ EO在拍{i}死亡——零收益下存活{i}拍")
            return eo, i

    print(f"\n  EO存活满{拍数}拍——零收益下未死亡")
    return eo, 拍数


def 运行_间歇收益实验(拍数=400):
    """间歇性收益——模拟真实环境的稀缺。"""
    print(f"\n=== 间歇收益实验：{拍数}拍 ===\n")

    eo = EO实例()
    eo.绑定("间歇实验", name="观察者")

    收益周期 = 0
    for i in range(拍数):
        外部 = 0.5 + 0.25 * math.sin(i * 0.03)

        # 每20拍给一次收益，其余时间无收益
        if i % 20 < 5:
            价值 = 0.04
            收益周期 += 1
        else:
            价值 = None

        r = eo.一拍(外部输入=外部, 行为价值=价值)

        if i % 40 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f} gap={摘要['gap']:.4f} "
                  f"疤={摘要['疤计数']} 降频={摘要['降频']:.4f} "
                  f"理解度={摘要['他者理解度']:.4f} 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  ⚡ EO在拍{i}死亡")
            break

    摘要 = eo.状态摘要()
    print(f"\n  终态: 流量={摘要['流量']:.4f} 疤={摘要['疤计数']} "
          f"理解度={摘要['他者理解度']:.4f} 链={摘要['链条目数']}")
    return eo


if __name__ == "__main__":
    eo1, 记录 = 运行_基础涌现观察(500)
    eo2, 死亡拍 = 运行_死亡实验(300)
    eo3 = 运行_间歇收益实验(400)

    print("\n" + "=" * 60)
    print("所有实验完成。观察约束下涌现了什么。")
