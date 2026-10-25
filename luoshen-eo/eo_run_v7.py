"""EO沙盒运行器V7——约束+感官+大脑+概念层+欲望的完整涌现。

新增欲望系统：RPE驱动 + 内生约束(leak>0)。
大脑的预测误差就是欲望的驱动力——不知道→饥饿→探索→理解→满足。
"""

import math
import json
import os
import random

from eo_core import EO实例


def 运行_欲望涌现观察(拍数=500):
    print(f"=== 欲望涌现观察：{拍数}拍 ===\n")

    print("阶段1：演化大脑...")
    eo = EO实例(
        状态目录="/workspace/eo-sandbox/state_v7",
        知识库根目录="/workspace/luoshen-ai-o1",
        演化大脑=True,
    )
    print(f"  大脑演化完成，fitness={eo.大脑fitness:.4f}\n")

    print("阶段2：欲望涌现运行...")
    eo.绑定("欲望实验V7", name="观察者")

    记录 = []
    boredom序列 = []
    gap序列 = []
    概念区分度序列 = []

    for i in range(拍数):
        外部 = 0.5 + 0.3 * math.sin(i * 0.05) + 0.05 * math.sin(i * 0.3)
        r = eo.一拍(外部输入=外部, 行为价值=None)
        记录.append(r)

        if r.get("欲望"):
            boredom序列.append(r["欲望"]["boredom"])
            gap序列.append(r["欲望"]["gap均值"])
        if r.get("概念"):
            概念区分度序列.append(r["概念"]["概念区分度"])

        if i % 50 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            欲望信息 = ""
            if r.get("欲望"):
                欲望信息 = (f" boredom={r['欲望']['boredom']:.4f}"
                           f" gap={r['欲望']['gap均值']:.4f}")
            概念信息 = ""
            if r.get("概念"):
                概念信息 = f" 概念区分度={r['概念']['概念区分度']:.4f}"
            大脑信息 = ""
            if r.get("大脑"):
                大脑信息 = f" mse={r['大脑']['预测mse']:.4f}"
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f}"
                  f" 理解度={摘要['他者理解度']:.4f}{大脑信息}"
                  f"{概念信息}{欲望信息}"
                  f" 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  EO在拍{i}死亡")
            break

    # ── 涌现分析 ──
    print("\n--- 涌现分析 ---")

    摘要 = eo.状态摘要()
    print(f"  存活拍数: {len(记录)}/{拍数}")

    # 欲望boredom趋势——预测变准后是否无聊？
    if boredom序列:
        前期b = sum(boredom序列[:50]) / max(1, len(boredom序列[:50]))
        后期b = sum(boredom序列[-50:]) / max(1, len(boredom序列[-50:]))
        print(f"  boredom: 前期={前期b:.4f} 后期={后期b:.4f} "
              f"{'→无聊增长（预测变准后想探索）' if 后期b > 前期b else '→无聊未增长'}")

    # 欲望gap趋势——内生约束是否持续？
    if gap序列:
        前期g = sum(gap序列[:50]) / max(1, len(gap序列[:50]))
        后期g = sum(gap序列[-50:]) / max(1, len(gap序列[-50:]))
        print(f"  欲望gap: 前期={前期g:.4f} 后期={后期g:.4f} "
              f"始终>0={'是' if all(g > 0 for g in gap序列) else '否'}"
              f"（内生约束leak>0）")

    # 概念区分度
    if 概念区分度序列:
        前期c = sum(概念区分度序列[:50]) / max(1, len(概念区分度序列[:50]))
        后期c = sum(概念区分度序列[-50:]) / max(1, len(概念区分度序列[-50:]))
        print(f"  概念区分度: 前期={前期c:.4f} 后期={后期c:.4f} "
              f"{'→提升' if 后期c > 前期c else '→未提升'}")

    # 大脑mse
    大脑mse序列 = [r["大脑"]["预测mse"] for r in 记录 if r.get("大脑")]
    if 大脑mse序列:
        前期mse = sum(大脑mse序列[:50]) / max(1, len(大脑mse序列[:50]))
        后期mse = sum(大脑mse序列[-50:]) / max(1, len(大脑mse序列[-50:]))
        print(f"  大脑mse: 前期={前期mse:.4f} 后期={后期mse:.4f} "
              f"{'→变准' if 后期mse < 前期mse else '→未变准'}")

    # 精卫Δ
    deltas = [r["精卫"]["Δ"] for r in 记录 if "精卫" in r]
    if deltas:
        前期Δ = sum(abs(d) for d in deltas[:50]) / max(1, len(deltas[:50]))
        后期Δ = sum(abs(d) for d in deltas[-50:]) / max(1, len(deltas[-50:]))
        print(f"  精卫|Δ|: 前期={前期Δ:.4f} 后期={后期Δ:.4f}")

    # 他者理解度
    理解度序列 = []
    for r in 记录:
        if r.get("他者") and r["他者"] and 0 in r["他者"]:
            理解度序列.append(r["他者"][0]["理解度"])
    if 理解度序列:
        print(f"  他者理解度: 起始={理解度序列[0]:.4f} "
              f"终止={理解度序列[-1]:.4f}")

    # 哈希链
    print(f"  哈希链条目数: {摘要['链条目数']} 验证: {摘要['链验证']}")

    # 保存
    记录文件 = os.path.join(eo.状态目录, "run_log.json")
    with open(记录文件, "w", encoding="utf-8") as f:
        json.dump(记录, f, ensure_ascii=False, indent=2)
    print(f"\n  完整记录已保存: {记录文件}")

    return eo, 记录


if __name__ == "__main__":
    random.seed(42)
    eo, 记录 = 运行_欲望涌现观察(500)

    print("\n" + "=" * 60)
    print("欲望涌现观察完成。")
    print("\n完整系统组成:")
    print("  约束（五条件）→ 活着")
    print("  大脑（演化引擎）→ 思考")
    print("  概念层（精卫公式驱动）→ 理解")
    print("  欲望（RPE驱动+内生约束）→ 想要")
    print("  感官（视网膜/耳蜗/数字感官）→ 感知")
    print("  精卫公式 → Δ驱动")
    print("  他者表征 → 关系")
    print("  哈希链 → 记忆")
