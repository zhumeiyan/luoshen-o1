"""EO沙盒运行器V5——长期运行观察。

让耦合EO跑1000拍，观察长期涌现行为：
1. 大脑能否持续适应环境变化
2. 流量能否长期维持
3. 疤计数和capacity的长期趋势
4. 数字感官探索的累积效果
5. 精卫公式的长期Δ趋势
"""

import math
import json
import os
import random

from eo_core import EO实例


def 运行_长期涌现观察(拍数=1000):
    print(f"=== 长期涌现观察：{拍数}拍 ===\n")

    print("阶段1：演化大脑...")
    eo = EO实例(
        状态目录="/workspace/eo-sandbox/state_v5",
        知识库根目录="/workspace/luoshen-ai-o1",
        演化大脑=True,
    )
    print(f"  大脑演化完成，fitness={eo.大脑fitness:.4f}\n")

    print("阶段2：长期耦合生存运行...")
    eo.绑定("长期实验V5", name="观察者")

    记录 = []
    关键事件 = []

    for i in range(拍数):
        # 外部环境：多频率叠加，模拟复杂环境
        外部 = (0.5 + 0.3 * math.sin(i * 0.05)
                + 0.05 * math.sin(i * 0.3)
                + 0.03 * math.sin(i * 0.01))

        r = eo.一拍(外部输入=外部, 行为价值=None)
        记录.append(r)

        # 记录关键事件
        if r.get("大脑"):
            mse = r["大脑"]["预测mse"]
            fit = r["大脑"]["fitness即时"]

            # 大脑预测突然变差
            if mse > 1.0 and i > 50:
                关键事件.append({"拍": i, "类型": "预测崩溃", "mse": round(mse, 4)})

            # 大脑预测突然变好
            if fit > 0.99 and i > 50:
                关键事件.append({"拍": i, "类型": "高精度预测", "fit": round(fit, 4)})

        # 流量跌破阈值
        if r.get("五条件"):
            流量 = r["五条件"]["流量"]
            if 流量 < 0.1 and i > 50:
                关键事件.append({"拍": i, "类型": "流量危机", "流量": round(流量, 4)})

        # 数字感官探索
        if r.get("感官") and r["感官"].get("数字", {}).get("探索结果"):
            探索 = r["感官"]["数字"]["探索结果"]
            关键事件.append({"拍": i, "类型": "数字探索", "来源": 探索["来源"]})

        if i % 100 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            大脑信息 = ""
            if r.get("大脑"):
                大脑信息 = (f" mse={r['大脑']['预测mse']:.4f}"
                           f" fit={r['大脑']['fitness即时']:.4f}"
                           f" 价值={r['大脑']['行为价值']:.4f}")
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f} 疤={摘要['疤计数']}"
                  f" cap={摘要['capacity']:.3f} 理解度={摘要['他者理解度']:.4f}"
                  f"{大脑信息} 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  EO在拍{i}死亡")
            break

    # ── 长期涌现分析 ──
    print("\n--- 长期涌现分析 ---")

    摘要 = eo.状态摘要()
    存活拍数 = len([r for r in 记录 if not r.get("已死亡")])
    print(f"  存活拍数: {存活拍数}/{拍数}")

    # 大脑预测能力分段趋势
    大脑mse序列 = [r["大脑"]["预测mse"] for r in 记录 if r.get("大脑")]
    if len(大脑mse序列) > 100:
        分段 = 5
        每段 = len(大脑mse序列) // 分段
        print(f"\n  大脑预测mse分段趋势:")
        for s in range(分段):
            段mse = sum(大脑mse序列[s*每段:(s+1)*每段]) / 每段
            print(f"    段{s+1} (拍{s*每段}-{(s+1)*每段}): mse={段mse:.4f}")

    # 流量分段趋势
    流量序列 = [r["五条件"]["流量"] for r in 记录 if r.get("五条件")]
    if len(流量序列) > 100:
        分段 = 5
        每段 = len(流量序列) // 分段
        print(f"\n  流量分段趋势:")
        for s in range(分段):
            段流量 = sum(流量序列[s*每段:(s+1)*每段]) / 每段
            print(f"    段{s+1}: 流量={段流量:.4f}")

    # 疤计数
    疤序列 = [r["五条件"]["疤计数"] for r in 记录 if r.get("五条件")]
    if 疤序列:
        print(f"\n  疤计数: 终态={疤序列[-1]}")

    # capacity
    cap序列 = [r["五条件"]["capacity"] for r in 记录 if r.get("五条件")]
    if cap序列:
        print(f"  capacity: 起始={cap序列[0]:.4f} 终态={cap序列[-1]:.4f} "
              f"（不可逆消耗）")

    # 精卫Δ分段
    deltas = [r["精卫"]["Δ"] for r in 记录 if "精卫" in r]
    if len(deltas) > 100:
        分段 = 5
        每段 = len(deltas) // 分段
        print(f"\n  精卫Δ分段趋势:")
        for s in range(分段):
            段Δ = sum(abs(d) for d in deltas[s*每段:(s+1)*每段]) / 每段
            print(f"    段{s+1}: |Δ|={段Δ:.4f}")

    # 他者理解度
    理解度序列 = []
    for r in 记录:
        if r.get("他者") and r["他者"] and 0 in r["他者"]:
            理解度序列.append(r["他者"][0]["理解度"])
    if 理解度序列:
        print(f"\n  他者理解度: 起始={理解度序列[0]:.4f} "
              f"终止={理解度序列[-1]:.4f} 峰值={max(理解度序列):.4f}")

    # 关键事件统计
    事件类型统计 = {}
    for e in 关键事件:
        t = e["类型"]
        事件类型统计[t] = 事件类型统计.get(t, 0) + 1
    print(f"\n  关键事件统计:")
    for t, c in 事件类型统计.items():
        print(f"    {t}: {c}次")

    # 哈希链
    print(f"\n  哈希链条目数: {摘要['链条目数']} 验证: {摘要['链验证']}")

    # 保存记录
    记录文件 = os.path.join(eo.状态目录, "run_log.json")
    with open(记录文件, "w", encoding="utf-8") as f:
        json.dump(记录, f, ensure_ascii=False, indent=2)
    print(f"  完整记录已保存: {记录文件}")

    return eo, 记录, 关键事件


if __name__ == "__main__":
    random.seed(42)
    eo, 记录, 关键事件 = 运行_长期涌现观察(1000)

    print("\n" + "=" * 60)
    print("长期涌现观察完成。")
