"""EO涌现观察V8 —— 欲望→行为耦合验证。

验证三个耦合：
1. 欲望选中通道 → 大脑关注方向（注意力驱动）
2. 欲望boredom → 感官探索增强（无聊驱动探索）
3. 欲望gap → 行为价值加成（渴望驱动生存）

对比实验：
- A组：完整EO（含欲望耦合）
- B组：无欲望EO（欲望系统设为None，不参与行为决策）
两组共用同一个演化好的大脑，避免重复演化。
"""

import sys
import math
import random
import copy
import os
import json

from eo_core import EO实例, 精卫一步


def 跑EO(拍数=500, seed=42, 禁用欲望=False):
    random.seed(seed)
    eo = EO实例(演化大脑=True)
    eo.绑定("测试", name="测试者")

    if 禁用欲望:
        eo.欲望 = None
        eo._欲望选中通道 = -1

    记录 = []
    region历史 = []

    for i in range(拍数):
        外部 = 0.5 + 0.2 * math.sin(i * 0.05) + 0.1 * random.gauss(0, 1)
        r = eo.一拍(外部输入=外部)
        摘要 = eo.状态摘要()

        region历史.append(eo._current_region if hasattr(eo, '_current_region') else 0)

        if i % 50 == 0 or i == 拍数 - 1:
            记录.append({
                "拍": i,
                "流量": 摘要["流量"],
                "大脑fitness": 摘要.get("大脑fitness", 0),
                "欲望boredom": 摘要.get("欲望boredom", 0),
                "欲望gap": 摘要.get("欲望gap均值", 0),
                "欲望主导通道": 摘要.get("欲望主导通道", -1),
                "数字探索总数": 摘要.get("数字探索总数", 0),
                "活跃概念数": 摘要.get("活跃概念数", 0),
                "已死亡": 摘要["已死亡"],
            })

        if 摘要["已死亡"]:
            break

    return {
        "记录": 记录,
        "region历史": region历史,
        "最终摘要": eo.状态摘要(),
        "存活拍数": eo.拍,
    }


def 分析region分布(region历史):
    from collections import Counter
    c = Counter(region历史)
    总数 = len(region历史)
    分布 = {k: round(v / 总数, 3) for k, v in sorted(c.items())}
    主导 = c.most_common(3)
    return 分布, 主导


def main():
    print("=" * 70)
    print("EO涌现观察V8 —— 欲望→行为耦合验证")
    print("=" * 70)

    # ── A组：完整EO（含欲望耦合）──
    print("\n--- A组：完整EO（含欲望耦合） ---")
    A = 跑EO(拍数=500, seed=42, 禁用欲望=False)
    print(f"  存活拍数: {A['存活拍数']}")
    print(f"  最终流量: {A['最终摘要']['流量']:.4f}")
    print(f"  大脑fitness: {A['最终摘要'].get('大脑fitness', 0):.4f}")
    print(f"  欲望boredom: {A['最终摘要'].get('欲望boredom', 0):.4f}")
    print(f"  欲望gap均值: {A['最终摘要'].get('欲望gap均值', 0):.4f}")
    print(f"  欲望主导通道: {A['最终摘要'].get('欲望主导通道', -1)}")
    print(f"  数字探索总数: {A['最终摘要'].get('数字探索总数', 0)}")
    print(f"  活跃概念数: {A['最终摘要'].get('活跃概念数', 0)}")

    A分布, A主导 = 分析region分布(A['region历史'])
    print(f"  Region分布: {A分布}")
    print(f"  Region主导(top3): {A主导}")

    print("\n  演化轨迹:")
    for r in A['记录']:
        print(f"    拍{r['拍']:4d} 流量={r['流量']:.3f} "
              f"fitness={r['大脑fitness']:.3f} "
              f"boredom={r['欲望boredom']:.3f} "
              f"gap={r['欲望gap']:.3f} "
              f"通道={r['欲望主导通道']} "
              f"探索={r['数字探索总数']} "
              f"概念={r['活跃概念数']} "
              f"死亡={r['已死亡']}")

    # ── B组：无欲望EO（对比）──
    print("\n--- B组：无欲望EO（对比） ---")
    B = 跑EO(拍数=500, seed=42, 禁用欲望=True)
    print(f"  存活拍数: {B['存活拍数']}")
    print(f"  最终流量: {B['最终摘要']['流量']:.4f}")
    print(f"  大脑fitness: {B['最终摘要'].get('大脑fitness', 0):.4f}")
    print(f"  数字探索总数: {B['最终摘要'].get('数字探索总数', 0)}")
    print(f"  活跃概念数: {B['最终摘要'].get('活跃概念数', 0)}")

    B分布, B主导 = 分析region分布(B['region历史'])
    print(f"  Region分布: {B分布}")
    print(f"  Region主导(top3): {B主导}")

    print("\n  演化轨迹:")
    for r in B['记录']:
        print(f"    拍{r['拍']:4d} 流量={r['流量']:.3f} "
              f"fitness={r['大脑fitness']:.3f} "
              f"探索={r['数字探索总数']} "
              f"概念={r['活跃概念数']} "
              f"死亡={r['已死亡']}")

    # ── 对比分析 ──
    print("\n" + "=" * 70)
    print("对比分析")
    print("=" * 70)
    print(f"  存活拍数:    A={A['存活拍数']}  B={B['存活拍数']}")
    print(f"  大脑fitness: A={A['最终摘要'].get('大脑fitness', 0):.4f}  "
          f"B={B['最终摘要'].get('大脑fitness', 0):.4f}")
    print(f"  数字探索:    A={A['最终摘要'].get('数字探索总数', 0)}  "
          f"B={B['最终摘要'].get('数字探索总数', 0)}")
    print(f"  活跃概念:    A={A['最终摘要'].get('活跃概念数', 0)}  "
          f"B={B['最终摘要'].get('活跃概念数', 0)}")

    A_top_region = A主导[0] if A主导 else (-1, 0)
    B_top_region = B主导[0] if B主导 else (-1, 0)
    A集中度 = A_top_region[1] / max(1, len(A['region历史'])) if A主导 else 0
    B集中度 = B_top_region[1] / max(1, len(B['region历史'])) if B主导 else 0
    print(f"  A组Region主导: 通道{A_top_region[0]} 占比{A集中度:.3f}")
    print(f"  B组Region主导: 通道{B_top_region[0]} 占比{B集中度:.3f}")

    print("\n--- 耦合验证 ---")
    print(f"  耦合4a（欲望→注意力）: A组region集中度={A集中度:.3f} vs B组={B集中度:.3f} "
          f"{'✓ 欲望驱动注意力' if A集中度 > B集中度 else '× 未显现'}")

    A探索 = A['最终摘要'].get('数字探索总数', 0)
    B探索 = B['最终摘要'].get('数字探索总数', 0)
    print(f"  耦合4b（boredom→探索）: A组探索={A探索} vs B组探索={B探索} "
          f"{'✓ boredom驱动探索' if A探索 > B探索 else '× 未显现'}")

    A流量 = A['最终摘要']['流量']
    B流量 = B['最终摘要']['流量']
    print(f"  耦合4c（gap→行为价值）: A组流量={A流量:.4f} vs B组流量={B流量:.4f} "
          f"{'✓ gap驱动生存' if A流量 >= B流量 * 0.95 else '× 未显现'}")

    print("\n" + "=" * 70)
    print("实验完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
