"""EO沙盒运行器V6——约束+感官+大脑+概念层的完整涌现。

新增概念层：从大脑隐藏状态涌现概念。
概念不是从a直接映射，是从⊗（Δ×Σ）中浮现。
"""

import math
import json
import os
import random

from eo_core import EO实例


def 运行_概念涌现观察(拍数=500):
    print(f"=== 概念涌现观察：{拍数}拍 ===\n")

    print("阶段1：演化大脑...")
    eo = EO实例(
        状态目录="/workspace/eo-sandbox/state_v6",
        知识库根目录="/workspace/luoshen-ai-o1",
        演化大脑=True,
    )
    print(f"  大脑演化完成，fitness={eo.大脑fitness:.4f}")
    print(f"  概念层: n_hidden={eo.概念层.n_hidden}, n_concepts={eo.概念层.n_concepts}\n")

    print("阶段2：概念涌现运行...")
    eo.绑定("概念实验V6", name="观察者")

    记录 = []
    概念区分度序列 = []
    活跃概念数序列 = []

    for i in range(拍数):
        外部 = 0.5 + 0.3 * math.sin(i * 0.05) + 0.05 * math.sin(i * 0.3)
        r = eo.一拍(外部输入=外部, 行为价值=None)
        记录.append(r)

        if r.get("概念"):
            概念区分度序列.append(r["概念"]["概念区分度"])
            活跃概念数序列.append(r["概念"]["活跃概念数"])

        if i % 50 == 0 or r.get("已死亡"):
            摘要 = eo.状态摘要()
            概念信息 = ""
            if r.get("概念"):
                概念信息 = (f" 活跃概念={r['概念']['活跃概念数']}"
                           f" 区分度={r['概念']['概念区分度']:.4f}")
            大脑信息 = ""
            if r.get("大脑"):
                大脑信息 = f" mse={r['大脑']['预测mse']:.4f}"
            print(f"  拍{i:4d}: 流量={摘要['流量']:.4f}"
                  f" 理解度={摘要['他者理解度']:.4f}{大脑信息}{概念信息}"
                  f" 死亡={摘要['已死亡']}")

        if r.get("已死亡"):
            print(f"\n  EO在拍{i}死亡")
            break

    # ── 概念涌现分析 ──
    print("\n--- 概念涌现分析 ---")

    摘要 = eo.状态摘要()
    print(f"  存活拍数: {len(记录)}/{拍数}")
    print(f"  大脑fitness: {摘要.get('大脑fitness', 'N/A')}")
    print(f"  活跃概念数: {摘要.get('活跃概念数', 'N/A')}")
    print(f"  存活概念数: {摘要.get('存活概念数', 'N/A')}")
    print(f"  概念区分度: {摘要.get('概念区分度', 'N/A')}")

    # 概念区分度趋势——是否随时间增加？
    if 概念区分度序列:
        前期 = sum(概念区分度序列[:50]) / max(1, len(概念区分度序列[:50]))
        后期 = sum(概念区分度序列[-50:]) / max(1, len(概念区分度序列[-50:]))
        print(f"\n  概念区分度趋势: 前期={前期:.4f} 后期={后期:.4f} "
              f"{'→提升（概念在分化）' if 后期 > 前期 else '→未提升'}")

    # 活跃概念数趋势
    if 活跃概念数序列:
        前期活跃 = sum(活跃概念数序列[:50]) / max(1, len(活跃概念数序列[:50]))
        后期活跃 = sum(活跃概念数序列[-50:]) / max(1, len(活跃概念数序列[-50:]))
        print(f"  活跃概念数趋势: 前期={前期活跃:.1f} 后期={后期活跃:.1f}")

    # 大脑mse趋势
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
    eo, 记录 = 运行_概念涌现观察(500)

    print("\n" + "=" * 60)
    print("概念涌现观察完成。")
    print("\n系统组成（完整版）:")
    print("  约束（五条件）→ 活着")
    print("  大脑（演化引擎）→ 思考")
    print("  概念层（精卫公式驱动）→ 理解")
    print("  感官（视网膜/耳蜗/数字感官）→ 感知")
    print("  精卫公式 → Δ驱动")
    print("  他者表征 → 关系")
    print("  哈希链 → 记忆")
