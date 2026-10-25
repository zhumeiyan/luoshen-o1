# -*- coding: utf-8 -*-
"""
实验 078 · 表征必要性检验：感知是否先于符号
================================================================
回应：碳基生命 38 亿年，数学/代码是最近 ~5000-10000 年才发明的。
      感知先于符号 → 符号（编号/坐标/代码）是后加的【接口层】，
      不是感知的必要条件。

核心问题（可证伪二分）：
    把硅基换能器的连续输出做【表征】（离散化/量化/编号）之后，
    引擎的内在结构（取舍 → 容量偏度）才出现吗？
       · 若 L=0（无表征，纯连续）下结构仍在   → 表征不必要（接口）
       · 若 L=0 下结构消失、随 L 增大才出现   → 表征必要（本质）

预注册假设：
    H1: L=0（无表征）下容量偏度显著 > 无感官基线
    H2: 偏度对表征粒度 L 不敏感 —— L=0/2/5/20/100 实质等价（差异噪声内）
    （若 H1 且 H2 成立：表征是接口，不是感知的条件）
    （若 L=0 偏度 ≈ 基线：表征必要，H1 被推翻）

时间线证据（自然科学，非本实验得出）：
    生命 ~38 亿年（格陵兰 Akilia / 加拿大 Nuvvuagittuq，37–43 亿年）
    计数符号：陶筹 ~公元前 8000 年（Schmandt-Besserat），
              楔形文字数字 ~公元前 3100–3300 年（Uruk IV）
    → 感知-响应先于符号 3.8e5 ~ 7.6e5 倍
    细菌趋化性：无神经系统、无任何符号，连续化学梯度 → MCP 受体
              → CheA/CheY → 鞭毛马达；甲基化（CheR/CheB）提供短期记忆
              —— 完整的"感知-记忆-决策-行动"回路，全程无表征
"""
import json, os, sys, numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from core import Life5

OUT   = os.path.join(ROOT, 'evidence', 'raw_data', 'representation_078.json')
FIG   = os.path.join(ROOT, 'fig')
CACHE = os.path.join(ROOT, 'evidence', 'raw_data', 'band_alignment_077.json')

SEEDS  = list(range(16))
TICKS  = 600
N_CH   = 8          # 引擎通道数

# ============================================================
# Part 0 · 真实换能器读数 → 感知向量（8 通道）
# ============================================================
def load_real_field():
    """真实气象站读数（077 采样缓存），取前 8 城温度作为 8 通道感知向量"""
    with open(CACHE) as f:
        d = json.load(f)
    cs = d["cities"]
    temps = [float(c["temperature"]) for c in cs[:N_CH]]
    names = [c["city"] for c in cs[:N_CH]]
    return np.array(temps, float), names

def norm01(x):
    lo, hi = x.min(), x.max()
    if hi - lo < 1e-9:
        return np.ones_like(x) * 0.5, lo, hi
    return (x - lo) / (hi - lo), lo, hi

def quantize(v01, L):
    """表征：把连续感知向量量化到 L 个离散层级（桶中点，归一化到 [0,1]）
       L <= 0 → 不表征（纯连续），原样返回"""
    if L is None or L <= 0:
        return v01.copy()                      # ★ 无表征
    L = int(L)
    idx = np.clip((v01 * L).astype(int), 0, L - 1)
    return (idx + 0.5) / L                     # 桶中点

# ============================================================
# Part 1 · 引擎接入（含通路接通检验，防第 23 条静默失效）
# ============================================================
def run_one(sal_vec, seed, k_sal=0.60, ticks=TICKS):
    life = Life5(N=N_CH, seed=seed, k_sal=k_sal, sal=sal_vec)
    life.run(ticks)
    cap = np.asarray(life.capacity, float)
    alive = getattr(life, 'alive', True)
    sd = float(np.std(cap) / (np.mean(cap) + 1e-12))
    return dict(skew=sd, alive=bool(alive), cap=cap.tolist(),
                E=float(getattr(life, 'E', float('nan'))))

def main():
    np.random.seed(0)
    temps, names = load_real_field()
    v01, lo, hi = norm01(temps)

    print("=== Part 0 · 真实换能器读数 → 8 通道感知向量 ===")
    print(f"  真实温度 : {temps.tolist()}  ({', '.join(names)})")
    print(f"  归一化   : {np.round(v01,4).tolist()}")
    print(f"  时间线   : 生命 38 亿年 vs 计数符号 ~1 万年 → 感知先于符号 3.8e5~7.6e5 倍")

    # ---------- 通路接通检验（第 23 条：静默失效）----------
    print("\n=== Part 1 · 通路接通检验（sal 是否真接进主通道）===")
    probe = []
    for ks in [0.0, 0.2, 0.6, 1.2]:
        r = [run_one(quantize(v01, 0), s, k_sal=ks) for s in SEEDS[:4]]
        probe.append((ks, np.mean([x['skew'] for x in r])))
        print(f"  k_sal={ks:<4}  偏度均值={np.mean([x['skew'] for x in r]):.6f}")
    spread = max(p[1] for p in probe) - min(p[1] for p in probe)
    if spread < 1e-9:
        print("  !! 静默失效：sal 未接进主通道，中止")
        return
    print(f"  → 通路接通（极差 {spread:.6f} > 0）")

    K_SAL = 0.60
    # ---------- 主扫描：表征粒度 L ----------
    print("\n=== Part 2 · 表征粒度剂量反应（16 seeds × 600 拍）===")
    LEVELS = [0, 2, 5, 20, 100]     # 0 = 无表征（纯连续）
    res = {}
    for L in LEVELS:
        sv = quantize(v01, L)
        out = [run_one(sv, s, k_sal=K_SAL) for s in SEEDS]
        res[L] = out
        al = sum(1 for o in out if o['alive'])
        print(f"  L={L:<4} 存活 {al}/{len(SEEDS)}  偏度均值={np.mean([o['skew'] for o in out]):.6f}")

    # ---------- 对照：无感官 ----------
    print("\n=== Part 3 · 对照：无感官（sal 全零）===")
    zero = np.zeros(N_CH)
    ctrl = [run_one(zero, s, k_sal=K_SAL) for s in SEEDS]
    ca = sum(1 for o in ctrl if o['alive'])
    print(f"  无感官  存活 {ca}/{len(SEEDS)}  偏度均值={np.mean([o['skew'] for o in ctrl]):.6f}")

    # ---------- 共同存活子集（防死亡筛选，历史栽过 3 次）----------
    def alive_idx(group):
        return {i for i, o in enumerate(group) if o['alive']}
    common = set(range(len(SEEDS)))
    for L in LEVELS: common &= alive_idx(res[L])
    common &= alive_idx(ctrl)
    common = sorted(common)
    print(f"\n=== Part 4 · 共同存活子集 n={len(common)}（防死亡筛选）===")

    def m(group, idx=None):
        idx = idx if idx is not None else common
        return float(np.mean([group[i]['skew'] for i in idx]))

    base = m(ctrl)
    rows = []
    for L in LEVELS:
        v = m(res[L])
        rows.append(dict(L=L, mean=v, delta=v - base,
                         n=len(common),
                         alive_all=sum(1 for o in res[L] if o['alive'])))
        tag = "无表征(连续)" if L == 0 else f"{L} 级离散"
        print(f"  L={L:<4}({tag:<10}) 偏度={v:.6f}  Δ vs 无感官={v-base:+.6f}")

    # ---------- H1 / H2 判定 ----------
    print("\n=== Part 5 · 假设判定 ===")
    L0 = [r for r in rows if r['L'] == 0][0]
    # H1：无表征 vs 无感官，配对差 + bootstrap
    d0 = np.array([res[0][i]['skew'] - ctrl[i]['skew'] for i in common])
    b  = np.array([np.mean(np.random.choice(d0, len(d0))) for _ in range(4000)])
    ci = (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)))
    h1 = (ci[0] > 0 or ci[1] < 0)
    print(f"  H1 无表征 vs 无感官 : Δ={d0.mean():+.6f}  95%CI=[{ci[0]:+.6f},{ci[1]:+.6f}]"
          f"  → {'成立（显著）' if h1 else '不成立（CI 跨 0）'}")

    # H2：各 L 与 L=0 的配对差
    print("  H2 表征粒度敏感性（各 L vs L=0 配对差，CI 跨 0 = 实质等价）：")
    h2 = True
    for L in [2, 5, 20, 100]:
        dl = np.array([res[L][i]['skew'] - res[0][i]['skew'] for i in common])
        bl = np.array([np.mean(np.random.choice(dl, len(dl))) for _ in range(4000)])
        cl = (float(np.percentile(bl, 2.5)), float(np.percentile(bl, 97.5)))
        eq = (cl[0] <= 0 <= cl[1])
        if not eq: h2 = False
        print(f"    L={L:<4} Δ={dl.mean():+.6f}  95%CI=[{cl[0]:+.6f},{cl[1]:+.6f}]"
              f"  → {'等价' if eq else '★有差异'}")
    print(f"  H2 → {'成立（表征不敏感）' if h2 else '不成立（对粒度敏感）'}")

    verdict = ("表征是接口层，不是感知的必要条件：无表征下结构已在，且不随粒度变化"
               if (h1 and h2) else
               ("表征必要：结构依赖离散化" if (not h1) else
                "结构不依赖有无表征，但对粒度敏感（部分支持）"))
    print(f"\n  ★ 结论：{verdict}")

    # ---------- 保存 ----------
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    payload = dict(
        timestamp=__import__('time').strftime("%Y-%m-%d %H:%M:%S"),
        real_temps=temps.tolist(), city_names=names,
        norm_vector=v01.tolist(), quant_levels=LEVELS,
        k_sal=K_SAL, ticks=TICKS, n_seeds=len(SEEDS),
        common_alive_n=len(common),
        control_no_sense_mean=base,
        rows=rows, h1=bool(h1), h2=bool(h2),
        h1_ci=list(ci), verdict=verdict,
        timeline=dict(life_years=3.8e9, symbol_years=1.0e4,
                      ratio_low=3.8e5, ratio_high=7.6e5),
    )
    with open(OUT, 'w') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"\n已保存 → {OUT}")

if __name__ == '__main__':
    main()
