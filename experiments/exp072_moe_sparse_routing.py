# -*- coding: utf-8 -*-
"""
====================================================================
实验 072：富足条件下，强制取舍能否挽救结构？
        —— 把顶级开源模型的 MoE 稀疏路由映射进引擎
====================================================================

【灵感来源：顶级开源大模型的架构实践（不是抄代码，是验证主张）】

2026 年顶级开源模型的默认底盘是 MoE 稀疏激活：
  · DeepSeek-V3    671B 总 / 37B 激活
  · DeepSeek-V4 Pro 1.6T 总 / 49B 激活
  · Kimi K3        2.8T 总 / 104B 激活
  · Qwen3.5-397B-A17B  397B 总 / 17B 激活（约 4%）

关键事实：**即使算力充足，这些模型仍然强制 top-K 路由。**
MoE 的意义在于解耦「容量」与「推理成本」：总参数可以极大，
但每个 token 只激活其中一小部分。

这跟本项目核心主张同构：
    稀缺（强制取舍）驱动结构；富足（不取舍）杀死结构。
    —— 已实测：ratio ≥ 1.0 时结构偏度精确归零 0.0000。

【本实验要问的机制性问题（升级，不只是重复）】

    "富足杀死结构" 里的致死因子，到底是【资源多】还是【不取舍】？

    如果致死因子是资源多 → 那么即使强制 top-K 取舍，富足下结构仍应归零。
    如果致死因子是不取舍 → 那么富足下只要强制取舍，结构就应当保住。

这是可证伪的二分，且两种结果都有意义。

【映射方式】
  · Dense（全激活，类比 Dense 模型）：等比缩放，所有通道按比例分到，不取舍
  · TopK（稀疏路由，类比 MoE）：只激活 want 最大的 K 个通道，其余强制为 0

【预注册预测】
  1. 稀缺（ratio=0.45）下：Dense 与 TopK 偏度都 > 0（预算不足必然取舍）
  2. 富足（ratio=1.20）下：Dense 偏度 ≈ 0.0000（复现已发表结论）
  3. 富足（ratio=1.20）下：TopK 偏度显著 > 0（强制取舍保住结构）
  4. 剂量反应：富足下 K 从 8（全激活）递减到 2，偏度应单调上升

====================================================================
"""
import numpy as np
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.life5 import Life5

STEPS = 600
WARM = 300
N = 8
SEEDS = range(16)


# ---------- 分配规则 ----------
def make_dense():
    """Dense（全激活）：等比缩放，所有通道按比例分到，不发生取舍。"""
    def alloc(want, B, self):
        tot = want.sum()
        if tot <= 1e-12:
            return np.zeros_like(want)
        return want * (B / tot)          # 同比例扩张 → 结构比例不变
    return alloc


def make_topk(K):
    """TopK（稀疏路由）：只激活 want 最大的 K 个通道，其余强制为 0。
    即使在富足下也强制取舍 —— 这正是 MoE 的做法。"""
    def alloc(want, B, self):
        a = np.zeros_like(want)
        if want.sum() <= 1e-12:
            return a
        idx = np.argsort(-want)[:K]
        left = B
        for i in idx:
            take = min(want[i], left)
            a[i] = take
            left -= take
            if left <= 1e-12:
                break
        return a
    return alloc


def struct_skew(lf):
    """终态结构偏度：capacity 相对均匀的差异（std/mean）。"""
    c = np.asarray(lf.log[-1]['capv'], float)
    return float(c.std(ddof=1) / max(c.mean(), 1e-12))


def mean_active(lf):
    """后段平均激活通道数（验证稀疏路由真的稀疏）。"""
    recs = [r for r in lf.log if r['t'] > WARM]
    if not recs:
        return float('nan')
    return float(np.mean([np.sum(np.asarray(r['avec'], float) > 1e-9) for r in recs]))


def run_one(ratio, alloc_fn, sd):
    lf = Life5(N=N, seed=sd, ratio=ratio)
    lf.alloc_fn = alloc_fn
    lf.run(STEPS)
    return dict(
        seed=int(sd),
        survived=bool(lf.alive),
        skew=struct_skew(lf),
        active=mean_active(lf),
        final_E=float(lf.E),
    )


def summarize(rows):
    sk = np.array([r['skew'] for r in rows], float)
    ac = np.array([r['active'] for r in rows], float)
    return dict(
        n=len(rows),
        mean_skew=float(sk.mean()),
        se_skew=float(sk.std(ddof=1) / np.sqrt(len(sk))),
        mean_active=float(np.nanmean(ac)),
        survived=int(sum(r['survived'] for r in rows)),
        rows=rows,
    )


def main():
    out = {}

    # ---------- 主实验 2x2：稀缺/富足 × Dense/TopK ----------
    print("=" * 66)
    print("主实验：富足条件下，强制取舍能否挽救结构？")
    print("=" * 66)
    main_res = {}
    for ratio_name, ratio in (("scarce_045", 0.45), ("abundant_120", 1.20)):
        for rule_name, fn in (("dense", make_dense()),
                              ("topk_K3", make_topk(3))):
            rows = [run_one(ratio, fn, sd) for sd in SEEDS]
            s = summarize(rows)
            main_res[f"{ratio_name}_{rule_name}"] = s
            print(f"{ratio_name:14s} {rule_name:9s} "
                  f"skew={s['mean_skew']:.4f}±{s['se_skew']:.4f}  "
                  f"active={s['mean_active']:.2f}/{N}  "
                  f"alive={s['survived']}/{s['n']}")
    out['main_2x2'] = main_res

    # ---------- 剂量反应：富足下扫 K ----------
    print()
    print("=" * 66)
    print("剂量反应：富足（ratio=1.20）下，K 从 8（全激活）递减到 2")
    print("=" * 66)
    dose = {}
    for K in (8, 6, 4, 3, 2):
        rows = [run_one(1.20, make_topk(K), sd) for sd in SEEDS]
        s = summarize(rows)
        dose[f"K{K}"] = s
        print(f"K={K}  skew={s['mean_skew']:.4f}±{s['se_skew']:.4f}  "
              f"active={s['mean_active']:.2f}/{N}  alive={s['survived']}/{s['n']}")
    out['dose_response_abundant'] = dose

    # ---------- 稀缺带内也扫一遍（确认 TopK 不是普遍抬偏度） ----------
    print()
    print("=" * 66)
    print("稀缺带内扫描（ratio 0.30→0.60），确认两规则在稀缺下收敛")
    print("=" * 66)
    scar = {}
    for ratio in (0.30, 0.45, 0.60):
        for rule_name, fn in (("dense", make_dense()), ("topk_K3", make_topk(3))):
            rows = [run_one(ratio, fn, sd) for sd in SEEDS]
            s = summarize(rows)
            scar[f"r{ratio}_{rule_name}"] = s
            print(f"ratio={ratio}  {rule_name:9s} "
                  f"skew={s['mean_skew']:.4f}±{s['se_skew']:.4f}  "
                  f"alive={s['survived']}/{s['n']}")
    out['scarce_band'] = scar

    with open('result_072.json', 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n已写入 result_072.json")

    # ---------- 判定 ----------
    print()
    print("=" * 66)
    a_dense = main_res['abundant_120_dense']['mean_skew']
    a_topk = main_res['abundant_120_topk_K3']['mean_skew']
    s_dense = main_res['scarce_045_dense']['mean_skew']
    s_topk = main_res['scarce_045_topk_K3']['mean_skew']
    print(f"富足 Dense 偏度 = {a_dense:.4f}（预期≈0，复现『富足杀死结构』）")
    print(f"富足 TopK  偏度 = {a_topk:.4f}")
    print(f"→ 强制取舍在富足下把偏度从 {a_dense:.4f} 抬到 {a_topk:.4f}")
    print(f"稀缺 Dense 偏度 = {s_dense:.4f} / 稀缺 TopK = {s_topk:.4f}")
    print("=" * 66)


if __name__ == '__main__':
    main()
