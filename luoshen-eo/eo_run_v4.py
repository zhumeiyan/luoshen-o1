"""EO沙盒运行器V4——约束与大脑深度耦合的涌现观察。

耦合关系：
1. 稀缺驱动学习：流量低→饥饿系数高→大脑学习率提高
2. 预测驱动生存：大脑预测准→行为价值高→流量收益→存活
3. surprise驱动探索：大脑预测失败→surprise高→感官探索渴望

对比实验：
A. 无耦合：大脑和五条件并行运行（外部给固定行为价值）
B. 有耦合：大脑预测准确度决定行为价值，稀缺驱动学习率
"""

import math
import json
import os
import random

from eo_core import EO实例


def 运行_耦合涌现观察(拍数=300, 演化代数=30):
    """约束与大脑深度耦合的EO涌现观察。"""
    print(f"=== 耦合涌现观察：{拍数}拍 ===\n")

    print("阶段1：演化大脑...")
    eo = EO实例(
        状态目录="/workspace/eo-sandbox/state_v4",
        知识库根目录="/workspace/luoshen-ai-o1",
        演化大脑=True,
    )
    print(f"  大脑演化完成，fitness={eo.大脑fitness:.4f}\n")

    print("阶段2：耦合生存运行...")
    eo.绑定("耦合实验V4", name="观察者")

    记录 = []
    大脑mse序列 = []
    大脑surprise序列 = []
    大脑fitness序列 = []
    饥饿系数序列 = []
    行为价值序列 = []

    for i in range(拍数):
        外部 = 0.5 + 0.3 * math.sin(i * 0.05) + 0.05 * math.sin(i * 0.3)
        # 不给外部行为价值——让大脑自己产生行为价值
        r = eo.一拍(外部输入=外部, 行为价值=None)
        记录.append(r)

        if r.get("大脑"):
            大脑mse序列.append(r["大脑"]["预测mse"])
            大脑surprise序列.append(r["大脑"]["surprise"])
            大脑fitness序列.append(r["大脑"]["fitness即时"])
            饥饿系数序列.append(r["大脑"]["饥饿系数"])
            行为价值序列.append(r["大脑"]["行为价值"])

        if i % 30 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            大脑信息 = ""
            if r.get("大脑"):
                大脑信息 = (f" mse={r['大脑']['预测mse']:.4f}"
                           f" fit={r['大脑']['fitness即时']:.4f}"
                           f" 饥饿={r['大脑']['饥饿系数']:.3f}"
                           f" 价值={r['大脑']['行为价值']:.4f}")
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f} gap={摘要['gap']:.4f}"
                  f" 理解度={摘要['他者理解度']:.4f}{大脑信息}"
                  f" 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  EO在拍{i}死亡")
            break

    # 涌现分析
    print("\n--- 耦合涌现分析 ---")

    摘要 = eo.状态摘要()
    print(f"  大脑fitness(演化): {摘要.get('大脑fitness', 'N/A')}")

    # 大脑预测能力趋势
    if 大脑mse序列:
        前期mse = sum(大脑mse序列[:30]) / max(1, len(大脑mse序列[:30]))
        后期mse = sum(大脑mse序列[-30:]) / max(1, len(大脑mse序列[-30:]))
        print(f"  大脑预测mse: 前期={前期mse:.4f} 后期={后期mse:.4f} "
              f"{'→变准' if 后期mse < 前期mse else '→未变准'}")

    # 大脑即时fitness趋势
    if 大脑fitness序列:
        前期f = sum(大脑fitness序列[:30]) / max(1, len(大脑fitness序列[:30]))
        后期f = sum(大脑fitness序列[-30:]) / max(1, len(大脑fitness序列[-30:]))
        print(f"  大脑即时fitness: 前期={前期f:.4f} 后期={后期f:.4f} "
              f"{'→提升' if 后期f > 前期f else '→未提升'}")

    # 饥饿系数趋势——流量下降时饥饿应该上升
    if 饥饿系数序列:
        前期h = sum(饥饿系数序列[:30]) / max(1, len(饥饿系数序列[:30]))
        后期h = sum(饥饿系数序列[-30:]) / max(1, len(饥饿系数序列[-30:]))
        print(f"  饥饿系数: 前期={前期h:.4f} 后期={后期h:.4f} "
              f"{'→饥饿加剧（稀缺在驱动）' if 后期h > 前期h else '→饥饿稳定'}")

    # 行为价值趋势——大脑预测变准后行为价值应该上升
    if 行为价值序列:
        前期v = sum(行为价值序列[:30]) / max(1, len(行为价值序列[:30]))
        后期v = sum(行为价值序列[-30:]) / max(1, len(行为价值序列[-30:]))
        print(f"  行为价值: 前期={前期v:.4f} 后期={后期v:.4f} "
              f"{'→行为价值提升（预测在养活生命）' if 后期v > 前期v else '→行为价值未提升'}")

    # 精卫Δ
    deltas = [r["精卫"]["Δ"] for r in 记录 if "精卫" in r]
    if deltas:
        前期Δ = sum(deltas[:30]) / max(1, len(deltas[:30]))
        后期Δ = sum(deltas[-30:]) / max(1, len(deltas[-30:]))
        print(f"  精卫Δ: 前期={前期Δ:.4f} 后期={后期Δ:.4f} "
              f"{'→缩小（理解在发生）' if abs(后期Δ) < abs(前期Δ) else '→未缩小'}")

    # 他者理解度
    理解度序列 = []
    for r in 记录:
        if r.get("他者") and r["他者"] and 0 in r["他者"]:
            理解度序列.append(r["他者"][0]["理解度"])
    if 理解度序列:
        print(f"  他者理解度: 起始={理解度序列[0]:.4f} "
              f"终止={理解度序列[-1]:.4f} 峰值={max(理解度序列):.4f}")

    # gap
    gap序列 = [r["五条件"]["gap"] for r in 记录 if "五条件" in r]
    if gap序列:
        print(f"  gap: 始终>0={'是' if all(g > 0 for g in gap序列) else '否'}")

    # 流量趋势——关键：大脑能否养活自己
    流量序列 = [r["五条件"]["流量"] for r in 记录 if "五条件" in r]
    if 流量序列:
        print(f"  流量: 起始={流量序列[0]:.4f} 终止={流量序列[-1]:.4f} "
              f"最低={min(流量序列):.4f}")
        if 流量序列[-1] > 0.5:
            print(f"  →大脑在养活自己（预测准确→行为价值→流量维持）")
        elif 流量序列[-1] > 0:
            print(f"  →大脑勉强维持（预测不够准，流量在下降）")
        else:
            print(f"  →大脑未能养活自己（死亡）")

    print(f"  哈希链条目数: {摘要['链条目数']} 验证: {摘要['链验证']}")

    # 保存记录
    记录文件 = os.path.join(eo.状态目录, "run_log.json")
    with open(记录文件, "w", encoding="utf-8") as f:
        json.dump(记录, f, ensure_ascii=False, indent=2)
    print(f"\n  完整记录已保存: {记录文件}")

    return eo, 记录


if __name__ == "__main__":
    random.seed(42)
    eo, 记录 = 运行_耦合涌现观察(300)

    print("\n" + "=" * 60)
    print("耦合涌现观察完成。")
    print("\n耦合关系验证:")
    print("  1. 稀缺→饥饿→学习率提高：流量下降时饥饿系数上升")
    print("  2. 预测→行为价值→流量：大脑预测准→行为价值→流量收益")
    print("  3. surprise→探索：大脑预测失败→surprise→感官探索")
