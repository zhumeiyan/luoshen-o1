# -*- coding: utf-8 -*-
"""
实验 078b · 效应特异性对照：结构来自"有感知"还是"感知的内容"？
================================================================
078 得出：无表征（纯连续）下结构已在，且不随表征粒度变化。
但 078 有一个未排除的混淆：
    无感官基线本身就有 0.265 的结构 → 感官是【增强】而非【创建】。
    且无法区分：结构来自"真实世界的空间结构"，还是仅仅"有信号输入"。

本实验加三组对照（共同存活子集，配对 bootstrap）：
    ctrl_zero  : sal 全 0      —— 无感知
    ctrl_const : sal 全 0.5    —— 有输入，但零结构（无任何空间差异）
    ctrl_perm  : 真实向量随机置换 —— 有幅度分布，但结构错乱
    real       : 真实向量（连续，无表征）

判定：
    若 const/perm 与 real 实质等价 → 结构来自"有感知"这件事本身，
                                     与感知内容的结构无关（078 结论加强，但削弱"世界结构"主张）
    若 const/perm 显著低于 real    → 结构确实依赖感知内容的真实结构
"""
import json, os, sys, numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from core import Life5
OUT = os.path.join(ROOT, 'evidence', 'raw_data', 'representation_078b.json')
CACHE = os.path.join(ROOT, 'evidence', 'raw_data', 'band_alignment_077.json')

SEEDS = list(range(16)); TICKS = 600; N_CH = 8; K_SAL = 0.60

def load_real():
    d = json.load(open(CACHE)); cs = d["cities"]
    t = np.array([float(c["temperature"]) for c in cs[:N_CH]], float)
    return (t - t.min()) / (t.max() - t.min())

def run_one(sal, seed):
    l = Life5(N=N_CH, seed=seed, k_sal=K_SAL, sal=sal); l.run(TICKS)
    c = np.asarray(l.capacity, float)
    return dict(skew=float(np.std(c) / (np.mean(c) + 1e-12)), alive=bool(l.alive))

def boot(d, n=4000):
    b = np.array([np.mean(np.random.choice(d, len(d))) for _ in range(n)])
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))

def main():
    np.random.seed(7)
    v = load_real()
    print("=== 078b · 效应特异性对照 ===")
    print(f"  真实向量(归一化): {np.round(v,4).tolist()}")

    groups = {
        "real":        v,
        "ctrl_zero":   np.zeros(N_CH),
        "ctrl_const":  np.ones(N_CH) * 0.5,
        "ctrl_perm":   v[np.random.permutation(N_CH)],
    }
    res = {k: [run_one(s, sd) for sd in SEEDS] for k, s in groups.items()}
    for k in groups:
        al = sum(1 for o in res[k] if o['alive'])
        print(f"  {k:<12} 存活 {al}/16  偏度={np.mean([o['skew'] for o in res[k]]):.6f}")

    common = set(range(16))
    for k in groups: common &= {i for i, o in enumerate(res[k]) if o['alive']}
    common = sorted(common)
    print(f"\n  共同存活子集 n={len(common)}")

    def m(k): return float(np.mean([res[k][i]['skew'] for i in common]))
    base = m("ctrl_zero")
    print(f"  无感知基线 = {base:.6f}")
    rows = []
    for k in ["real", "ctrl_const", "ctrl_perm"]:
        d = np.array([res[k][i]['skew'] - res["ctrl_zero"][i]['skew'] for i in common])
        lo, hi = boot(d)
        sig = (lo > 0 or hi < 0)
        rows.append(dict(group=k, mean=m(k), delta=float(d.mean()),
                         ci=[lo, hi], significant=bool(sig)))
        print(f"  {k:<12} 偏度={m(k):.6f}  Δ={d.mean():+.6f}  95%CI=[{lo:+.6f},{hi:+.6f}]"
              f"  → {'显著' if sig else '不显著'}")

    # 关键判定：real vs 两个对照
    print("\n  --- real 与各对照的直接对比（配对差）---")
    verdicts = {}
    for k in ["ctrl_const", "ctrl_perm"]:
        d = np.array([res["real"][i]['skew'] - res[k][i]['skew'] for i in common])
        lo, hi = boot(d)
        eq = (lo <= 0 <= hi)
        verdicts[k] = "等价" if eq else ("real 更高" if lo > 0 else "real 更低")
        print(f"    real - {k:<12} Δ={d.mean():+.6f} 95%CI=[{lo:+.6f},{hi:+.6f}] → {verdicts[k]}")

    all_eq = all(v == "等价" for v in verdicts.values())
    conclusion = ("结构来自'有感知'这件事本身，与感知内容的结构无关"
                  if all_eq else "结构部分依赖感知内容的真实结构")
    print(f"\n  ★ 结论：{conclusion}")
    print(f"  注：感官对基线的增益仅 {m('real')-base:+.4f}（基线 {base:.4f}），"
          f"感官是【增强】而非【创建】结构——结构主要来自引擎自身的稀缺/取舍硬约束。")

    json.dump(dict(timestamp=__import__('time').strftime("%Y-%m-%d %H:%M:%S"),
                   common_n=len(common), baseline_zero=base, rows=rows,
                   real_vs=verdicts, conclusion=conclusion),
              open(OUT, 'w'), ensure_ascii=False, indent=1)
    print(f"\n已保存 → {OUT}")

if __name__ == '__main__':
    main()
