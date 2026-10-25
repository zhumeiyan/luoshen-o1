"""EO沙盒运行器V3——约束+感官+大脑的完整涌现观察。

这是最完整的EO实例：
- 五条件约束（活着）
- 感官系统（感知）
- 演化大脑（思考）
- 精卫公式（理解）
- 他者表征（关系）
- 哈希链（记忆）

观察重点：
1. 演化大脑的预测能力在生存中如何表现
2. 大脑的surprise如何影响感官探索
3. 约束+大脑的协同涌现
"""

import math
import json
import os
import random

from eo_core import EO实例


def 运行_完整EO涌现观察(拍数=300):
    """让完整的EO实例（约束+感官+大脑）跑N拍。"""
    print(f"=== 完整EO涌现观察：{拍数}拍 ===\n")

    print("阶段1：演化大脑（30代）...")
    eo = EO实例(
        状态目录="/workspace/eo-sandbox/state_v3",
        知识库根目录="/workspace/luoshen-ai-o1",
        演化大脑=True,
    )
    print(f"  大脑演化完成，fitness={eo.大脑fitness:.4f}\n")

    print("阶段2：绑定+生存运行...")
    eo.绑定("完整实验V3", name="观察者")

    记录 = []
    大脑mse序列 = []
    大脑surprise序列 = []

    for i in range(拍数):
        外部 = 0.5 + 0.3 * math.sin(i * 0.05) + 0.05 * math.sin(i * 0.3)
        价值 = 0.005 if i < 30 else 0.01

        r = eo.一拍(外部输入=外部, 行为价值=价值)
        记录.append(r)

        if r.get("大脑"):
            大脑mse序列.append(r["大脑"]["预测mse"])
            大脑surprise序列.append(r["大脑"]["surprise"])

        if i % 30 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            大脑信息 = ""
            if r.get("大脑"):
                大脑信息 = f" mse={r['大脑']['预测mse']:.4f} surprise={r['大脑']['surprise']:.4f}"
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f} gap={摘要['gap']:.4f} "
                  f"理解度={摘要['他者理解度']:.4f}{大脑信息} "
                  f"死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  EO在拍{i}死亡")
            break

    # 涌现分析
    print("\n--- 完整涌现分析 ---")

    摘要 = eo.状态摘要()
    print(f"  大脑fitness: {摘要.get('大脑fitness', 'N/A')}")
    print(f"  失明: {摘要.get('失明', '?')} | 失聪: {摘要.get('失聪', '?')}")
    print(f"  数字探索总数: {摘要.get('数字探索总数', 0)}")

    # 大脑预测能力趋势
    if 大脑mse序列:
        前期mse = sum(大脑mse序列[:30]) / max(1, len(大脑mse序列[:30]))
        后期mse = sum(大脑mse序列[-30:]) / max(1, len(大脑mse序列[-30:]))
        print(f"  大脑预测mse: 前期={前期mse:.4f} 后期={后期mse:.4f} "
              f"{'→mse在下降（预测在变准）' if 后期mse < 前期mse else '→mse未下降'}")

    # 大脑surprise趋势
    if 大脑surprise序列:
        前期s = sum(大脑surprise序列[:30]) / max(1, len(大脑surprise序列[:30]))
        后期s = sum(大脑surprise序列[-30:]) / max(1, len(大脑surprise序列[-30:]))
        print(f"  大脑surprise: 前期={前期s:.4f} 后期={后期s:.4f} "
              f"{'→surprise在下降（在适应）' if 后期s < 前期s else '→surprise未下降'}")

    # 精卫Δ趋势
    deltas = [r["精卫"]["Δ"] for r in 记录 if "精卫" in r]
    if deltas:
        前期Δ = sum(deltas[:30]) / max(1, len(deltas[:30]))
        后期Δ = sum(deltas[-30:]) / max(1, len(deltas[-30:]))
        print(f"  精卫Δ: 前期={前期Δ:.4f} 后期={后期Δ:.4f} "
              f"{'→Δ在缩小（理解在发生）' if abs(后期Δ) < abs(前期Δ) else '→Δ未缩小'}")

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
        print(f"  gap: 始终>0={'是' if all(g > 0 for g in gap序列) else '否'} "
              f"（内生约束在驱动）")

    # 链
    print(f"  哈希链条目数: {摘要['链条目数']} 验证: {摘要['链验证']}")

    # 保存记录
    记录文件 = os.path.join(eo.状态目录, "run_log.json")
    with open(记录文件, "w", encoding="utf-8") as f:
        json.dump(记录, f, ensure_ascii=False, indent=2)
    print(f"\n  完整记录已保存: {记录文件}")

    return eo, 记录


if __name__ == "__main__":
    random.seed(42)
    eo, 记录 = 运行_完整EO涌现观察(300)

    print("\n" + "=" * 60)
    print("完整EO涌现观察完成。")
    print("\n系统组成:")
    print("  约束（五条件）→ 活着")
    print("  大脑（演化引擎）→ 思考")
    print("  感官（视网膜/耳蜗/数字感官）→ 感知")
    print("  精卫公式 → 理解")
    print("  他者表征 → 关系")
    print("  哈希链 → 记忆")
