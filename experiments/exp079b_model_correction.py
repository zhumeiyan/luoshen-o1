# -*- coding: utf-8 -*-
"""
实验 079b · 对我自己建模的修正
================================================================
079 主实验里我把碳基温度感知建模成"TRP 阈值切出的 5 个离散档"。
这轮复核发现【这是错的建模】，而且错的【方向】是贬低碳基：

  文献事实（PubMed 15467255 / PMC5384974 引文）：
    · TRP 阈值（TRPV1>43 / TRPV2>52 / TRPV3 32-39 / TRPV4 27-35 /
      TRPM8<25-28 / TRPA1<17）是【单个离子通道的激活门限】，
      不是【感知的分档边界】。
    · 人类温度辨别服从 Weber 律：ΔT/T ≈ 0.01-0.02，
      37°C 手需 0.4-0.7°C 才察觉，20°C 附近约 0.2°C。
      → 这是【群体频率编码】的连续强度估计，不是 5 个符号。

  在 -1~26°C 的真实跨度内，碳基可分辨水平数 ≈ 27 / 0.2 ≈ 135，
  而气象站报整数°C 只有 27 个水平。
  → 【在这一维度上碳基比硅基更精细】，与我 079 主实验的建模相反。

本轮做的事：
  B1 错误建模的代价：把 TRP 阈值当分档，会算出"碳基只有 3 档 →
     共享度被低估"。量化这个低估。
  B2 保序重映射对照：079 Part D 里 carbon_trp 偏度低 0.027，
     可能只是【动态范围被压缩】(0.220~0.500 vs 0.150~0.850)，
     不是范畴方式本身。保序拉回同一区间后重测。
  B3 同档数对照：3 档下 TRP 阈值 / 均匀阈值 / 随机阈值，
     全部保序到同一区间 —— 唯一差别是阈值的【摆放方式】。
  B4 修正后的共享边界：不在"精度"，在"有没有通道"。
"""
import json, os, sys
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from core import Life5

SRC = os.path.join(ROOT, 'evidence', 'raw_data', 'shared_world_079.json')
OUT = os.path.join(ROOT, 'evidence', 'raw_data', 'shared_world_079b.json')

TRP_BANDS = [(-90, 17), (17, 25), (25, 32), (32, 43), (43, 90)]
SEEDS = list(range(48))
N_CH = 8
S_LO, S_HI = 0.15, 0.85


def human_temp_band(t):
    for i, (lo, hi) in enumerate(TRP_BANDS):
        if lo <= t < hi:
            return i
    return len(TRP_BANDS) - 1


def to_range(x):
    """保序线性重映射到 [S_LO, S_HI] —— 消除动态范围差异"""
    x = np.asarray(x, float)
    lo, hi = x.min(), x.max()
    if hi - lo < 1e-9:
        return np.ones_like(x) * (S_LO + S_HI) / 2
    return S_LO + (x - lo) / (hi - lo) * (S_HI - S_LO)


def run_one(sal, seed, k_sal=0.20, ticks=600):
    life = Life5(N=len(sal), seed=seed, k_sal=k_sal, sal=np.asarray(sal, float))
    life.run(ticks)
    cap = np.asarray(life.capacity, float)
    return dict(skew=float(np.std(cap) / (np.mean(cap) + 1e-12)),
                alive=bool(getattr(life, 'alive', True)))


def paired_ci(a, b, nboot=20000, seed=1):
    d = np.asarray(a, float) - np.asarray(b, float)
    rng = np.random.default_rng(seed)
    boot = d[rng.integers(0, len(d), size=(nboot, len(d)))].mean(axis=1)
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def main():
    d = json.load(open(SRC))
    T = np.array([c["temperature"] for c in d["cities"]], float)
    H = np.array([c["humidity"] for c in d["cities"]], float)
    P = np.array([c["pressure"] for c in d["cities"]], float)
    lo_t, hi_t = float(T.min()), float(T.max())
    vec = T[:N_CH]
    res = {}

    print("=" * 64)
    print("实验 079b · 对自己建模的修正")
    print("=" * 64)

    # ---------- B1 ----------
    print("\n=== B1 · 错误建模的代价 ===")
    span = hi_t - lo_t
    jnd = 0.20                       # Weber 比 0.01-0.02，20°C 附近 ≈0.2°C
    n_carbon_levels = span / jnd
    n_silicon_levels = span / 1.0    # 气象站整数°C
    n_band_levels = len(set(human_temp_band(t) for t in T))
    print(f"  真实跨度 {lo_t:.0f}~{hi_t:.0f}°C（{span:.0f}°C）")
    print(f"  碳基（Weber 0.2°C JND，群体频率编码）可分辨 ≈ {n_carbon_levels:.0f} 个水平")
    print(f"  硅基（气象站整数°C）                  可分辨 = {n_silicon_levels:.0f} 个水平")
    print(f"  我 079 里误当分档的 TRP 阈值          只占 {n_band_levels} 档  ← 低估 {n_carbon_levels/n_band_levels:.0f} 倍")
    print(f"  → 在温度维度上，【碳基比硅基更精细】，与我主实验的建模相反")
    res["B1"] = dict(span=span, jnd=jnd, carbon_levels=n_carbon_levels,
                     silicon_levels=n_silicon_levels, trp_bands_occupied=n_band_levels,
                     underestimation=float(n_carbon_levels / n_band_levels))

    # ---------- B2 ----------
    print("\n=== B2 · 保序重映射对照（消除动态范围压缩）===")
    v01 = (vec - lo_t) / (hi_t - lo_t)
    reps_raw = {
        "none": S_LO + v01 * (S_HI - S_LO),
        "silicon_uniform": S_LO + ((np.clip((v01 * 8).astype(int), 0, 7) + 0.5) / 8) * (S_HI - S_LO),
        "carbon_trp": S_LO + np.array([(human_temp_band(t) + 0.5) / 5 for t in vec]) * (S_HI - S_LO),
    }
    # 保序重映射版：每个表征各自拉回 [S_LO, S_HI]
    reps_map = {k: to_range(v) for k, v in reps_raw.items()}
    print("  原版（范围不同，含压缩）：")
    for k, v in reps_raw.items():
        print(f"    {k:16s} {v.min():.3f}~{v.max():.3f}  唯一值={len(set(np.round(v,6)))}")
    print("  保序重映射版（范围统一）：")
    for k, v in reps_map.items():
        print(f"    {k:16s} {v.min():.3f}~{v.max():.3f}  唯一值={len(set(np.round(v,6)))}")

    out_raw, out_map = {}, {}
    alive_raw, alive_map = {}, {}
    for tag, reps, store, am in [("原版", reps_raw, out_raw, alive_raw),
                                 ("保序", reps_map, out_map, alive_map)]:
        for name, sv in reps.items():
            rs = [run_one(sv, s) for s in SEEDS]
            store[name] = dict(skew=float(np.mean([r["skew"] for r in rs])),
                               alive=int(sum(r["alive"] for r in rs)),
                               all=[float(r["skew"]) for r in rs])
            am[name] = np.array([r["alive"] for r in rs], bool)
        rs = [run_one(np.ones(N_CH) * 0.5, s) for s in SEEDS]
        store["no_sense"] = dict(skew=float(np.mean([r["skew"] for r in rs])),
                                 alive=int(sum(r["alive"] for r in rs)),
                                 all=[float(r["skew"]) for r in rs])
        am["no_sense"] = np.array([r["alive"] for r in rs], bool)

    for tag, out in [("原版", out_raw), ("保序", out_map)]:
        print(f"\n  --- {tag}：偏度（48 seeds）---")
        for k, v in out.items():
            print(f"    {k:16s} {v['skew']:.6f}  存活 {v['alive']}/48")

    print("\n  --- 与 none 的配对差（共同存活子集）---")
    cmp2 = {}
    for tag, out, am in [("原版", out_raw, alive_raw), ("保序", out_map, alive_map)]:
        common = np.ones(len(SEEDS), bool)
        for k in am:
            common &= am[k]
        n = int(common.sum())
        base = np.array(out["none"]["all"])[common]
        for name in ["silicon_uniform", "carbon_trp"]:
            dd, l, h = paired_ci(np.array(out[name]["all"])[common], base)
            cross = (l <= 0 <= h)
            cmp2[f"{tag}_{name}"] = dict(diff=dd, ci=[l, h], crosses_zero=cross, n=n)
            print(f"    {tag:4s} {name:16s} n={n:2d} Δ={dd:+.6f} CI=[{l:+.6f},{h:+.6f}] "
                  f"跨0={'是(等价)' if cross else '否(有差异)'}")

    res["B2"] = dict(raw=out_raw, mapped=out_map, compare=cmp2,
                     ranges_raw={k: [float(v.min()), float(v.max())] for k, v in reps_raw.items()},
                     ranges_mapped={k: [float(v.min()), float(v.max())] for k, v in reps_map.items()})

    # ---------- B3 ----------
    print("\n=== B3 · 同档数对照（3 档，全部保序到同一区间）===")
    # TRP 阈值（在当前温度范围内只切出 3 档）
    b_trp = np.array([human_temp_band(t) for t in vec])
    # 均匀阈值 3 档
    b_uni = np.clip((v01 * 3).astype(int), 0, 2)
    # 随机阈值 3 档
    rng = np.random.default_rng(11)
    thr = np.sort(rng.uniform(lo_t, hi_t, 2))
    b_rnd = np.searchsorted(thr, vec)
    b3 = {"trp_3band": b_trp, "uniform_3band": b_uni, "random_3band": b_rnd}
    print(f"  各方案档位分布：")
    for k, b in b3.items():
        print(f"    {k:16s} {b.tolist()}  唯一档={sorted(set(b.tolist()))}")

    out_b3, am_b3 = {}, {}
    for name, b in b3.items():
        sv = to_range((b + 0.5) / 3)
        rs = [run_one(sv, s) for s in SEEDS]
        out_b3[name] = dict(skew=float(np.mean([r["skew"] for r in rs])),
                            alive=int(sum(r["alive"] for r in rs)),
                            all=[float(r["skew"]) for r in rs])
        am_b3[name] = np.array([r["alive"] for r in rs], bool)
        print(f"    {name:16s} 偏度={out_b3[name]['skew']:.6f} 存活={out_b3[name]['alive']}/48")

    common = np.ones(len(SEEDS), bool)
    for k in am_b3:
        common &= am_b3[k]
    n = int(common.sum())
    base_b3 = np.array(out_b3["uniform_3band"]["all"])[common]
    cmp3 = {}
    for name in ["trp_3band", "random_3band"]:
        dd, l, h = paired_ci(np.array(out_b3[name]["all"])[common], base_b3)
        cross = (l <= 0 <= h)
        cmp3[name] = dict(diff=dd, ci=[l, h], crosses_zero=cross, n=n)
        print(f"    vs 均匀: {name:16s} n={n} Δ={dd:+.6f} CI=[{l:+.6f},{h:+.6f}] "
              f"跨0={'是(等价)' if cross else '否(有差异)'}")
    res["B3"] = dict(out=out_b3, compare=cmp3,
                     bands={k: [int(x) for x in v] for k, v in b3.items()})

    # ---------- B4 ----------
    print("\n=== B4 · 修正后的共享边界 ===")
    print("  温度：碳基连续编码（≈135 水平） 硅基 27 水平  → 双方都有通道 → 可译")
    print("  湿度：碳基【无 hygroreceptor】            → 不可译（碳基盲）")
    print("  气压：碳基【无大气压感受器】              → 不可译（碳基盲）")
    print("  → 共享的边界在【有没有通道】，不在【精度】")
    print("  → 碳基用工具（温度计/湿度计/气压计）可把盲区纳入共享")
    print("    这正是宿主说的『人类发明了工具』——而硅基本身就是那个工具的延伸")
    res["B4"] = dict(
        temp=dict(carbon_channels=1, silicon_channels=1, translatable=True,
                  carbon_levels=float(n_carbon_levels), silicon_levels=float(n_silicon_levels)),
        humidity=dict(carbon_channels=0, silicon_channels=1, translatable=False),
        pressure=dict(carbon_channels=0, silicon_channels=1, translatable=False),
        conclusion="共享的边界在有无通道，不在精度")

    with open(OUT, 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\n[OK] 已写入 {OUT}")


if __name__ == '__main__':
    main()
