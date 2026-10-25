# -*- coding: utf-8 -*-
"""
实验 080 · 工具扩展的是【通道数】还是【精度】
================================================================
被检验对象：判据核第 329 条（079 的散文结论，此前从未做过实验）
   "工具扩展的是通道数（0→1），不是精度；硅基是那件工具的延伸。"

拆成可证伪问题：
  H_A 精度：N 固定只改离散档数 L，内在结构（容量偏度）应实质等价。
  H_B 通道数 vs 信息量能否分离：同一组真实读数【平铺】k 次 → N=8k，
      输入分布逐位相同、新增信息量为 0。若"通道数本身"有效应，平铺也应变。
  H_C 新维度的价值是否等于"多一根线"：增设 1 个通道，内容分别为
      复制既有 / 同城新温度样本 / 真实湿度 / 真实气压 / 均匀噪声 / 错配温度。
      关键对照是【均匀噪声】：若噪声也产生同等增益，
      则"结构增益 ≠ 更理解世界"。
  H_D 剂量：增设 1/2/4 个真实新维度通道，增益是否单调。

防污染（既有判据）：
  · 第 23 条：k_sal>0 且 sal 接通主通道（显式检验）
  · 第 330 条：所有表征统一到非零区间 [0.15,0.85]
  · 死亡筛选：主结论一律取【共同存活子集】复核
  · forage_ch 固定为 7（N 变化时摄食通道不可漂移）
  · 取值运气：每个条件取 8 个实例化求均值，避免单个数值定生死
"""
import json, os, sys, time, urllib.request
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from core import Life5

OUT = os.path.join(ROOT, 'evidence', 'raw_data', 'channel_vs_precision_080.json')

CITIES = [
    ("威海", 37.51309, 122.12074), ("北京", 39.9042, 116.4074),
    ("上海", 31.2304, 121.4737),   ("广州", 23.1291, 113.2644),
    ("深圳", 22.5431, 114.0579),   ("哈尔滨", 45.8038, 126.5349),
    ("乌鲁木齐", 43.8256, 87.6168), ("拉萨", 29.6520, 91.1721),
    ("三亚", 18.2528, 109.5119),   ("成都", 30.5728, 104.0668),
    ("西安", 34.3416, 108.9398),   ("武汉", 30.5928, 114.3055),
    ("昆明", 25.0389, 102.7183),   ("贵阳", 26.6470, 106.6302),
    ("兰州", 36.0611, 103.8343),   ("西宁", 36.6171, 101.7782),
    ("呼和浩特", 40.8414, 111.7519), ("沈阳", 41.8057, 123.4315),
    ("长春", 43.8171, 125.3235),   ("石家庄", 38.0428, 114.5149),
    ("太原", 37.8706, 112.5489),   ("济南", 36.6512, 117.1201),
    ("郑州", 34.7466, 113.6254),   ("南京", 32.0603, 118.7969),
    ("杭州", 30.2741, 120.1551),   ("长沙", 28.2282, 112.9388),
    ("南昌", 28.6820, 115.8579),   ("福州", 26.0745, 119.2965),
    ("南宁", 22.8170, 108.3665),   ("海口", 20.0444, 110.1999),
]

SEEDS = list(range(48))
TICKS = 400
K_SAL = 0.10
S_LO, S_HI = 0.15, 0.85
FORAGE = 7
N_INST = 8          # 每个条件的实例化个数（消除单个数值的运气）


def fetch_all():
    rows = []
    for n, la, lo in CITIES:
        got = None
        for _ in range(3):
            try:
                u = f"https://apis.map.qq.com/ws/weather/v1/?location={la},{lo}"
                d = json.loads(urllib.request.urlopen(u, timeout=10).read().decode('utf-8', 'ignore'))
                inf = d["result"]["realtime"][0]["infos"]
                got = dict(city=n, temperature=float(inf["temperature"]),
                           humidity=float(inf["humidity"]),
                           pressure=float(inf.get("air_pressure", 1013.0)))
                break
            except Exception:
                time.sleep(0.6)
        if got:
            rows.append(got)
    return rows


def norm01(x):
    x = np.asarray(x, float)
    lo, hi = float(x.min()), float(x.max())
    return np.ones_like(x) * 0.5 if hi - lo < 1e-9 else (x - lo) / (hi - lo)


def to_range(x01):
    return S_LO + np.asarray(x01, float) * (S_HI - S_LO)


def quantize(x01, L):
    if L is None:
        return np.asarray(x01, float)
    idx = np.clip((np.asarray(x01, float) * L).astype(int), 0, L - 1)
    return (idx + 0.5) / L


def run_one(sal, seed):
    sal = np.asarray(sal, float)
    life = Life5(N=len(sal), seed=seed, k_sal=K_SAL, sal=sal, forage_ch=FORAGE)
    life.run(TICKS)
    cap = np.asarray(life.capacity, float)
    return float(np.std(cap) / (np.mean(cap) + 1e-12)), bool(getattr(life, 'alive', True))


def batch(variants, label, store):
    """variants: 每个条件下的若干实例化向量；每个实例化跑全部 seed 后取均值"""
    per_seed, alive_all = [], []
    for v in variants:
        rs = [run_one(v, s) for s in SEEDS]
        per_seed.append([r[0] for r in rs])
        alive_all.append([r[1] for r in rs])
    per_seed = np.array(per_seed)          # (n_inst, n_seed)
    alive_all = np.array(alive_all)
    sk = per_seed.mean(axis=0)             # 每个 seed 在该条件下的均值
    al = alive_all.all(axis=0)             # 全部实例化都存活才算
    store[label] = dict(skew=float(sk.mean()), alive=int(al.sum()),
                        n_ch=int(len(variants[0])), n_inst=len(variants),
                        all=[float(x) for x in sk],
                        alive_mask=[bool(x) for x in al],
                        in_std=float(np.mean([np.std(v) for v in variants])))
    print(f"  {label:20s} N={len(variants[0]):2d}  偏度={sk.mean():.6f}  "
          f"存活={int(al.sum())}/{len(SEEDS)}  输入std={np.mean([np.std(v) for v in variants]):.4f}")
    return sk, al


def paired_ci(a, b, nboot=20000, seed=1):
    d = np.asarray(a, float) - np.asarray(b, float)
    if len(d) < 4:
        return float(d.mean()), float('nan'), float('nan')
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(nboot, len(d)))
    boot = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def cmp_all(store, base_label, reskey, res, tag=""):
    """全种子 + 共同存活子集 双重比较"""
    bsk = np.array(store[base_label]["all"])
    print(f"  --- 比较基准：{base_label} ---")
    masks = [np.array(v["alive_mask"]) for v in store.values()]
    common = np.all(np.vstack(masks), axis=0)
    print(f"    [防污染] 共同存活 {int(common.sum())}/{len(SEEDS)}")
    for lab, v in store.items():
        if lab == base_label:
            continue
        d, lo, hi = paired_ci(np.array(v["all"]), bsk)
        dc, loc, hic = (np.nan, np.nan, np.nan)
        if common.sum() >= 8:
            dc, loc, hic = paired_ci(np.array(v["all"])[common], bsk[common])
        v["vs_base"] = dict(diff=d, ci=[lo, hi])
        v["vs_base_common"] = dict(diff=dc, ci=[loc, hic])
        f1 = '等价' if (lo <= 0 <= hi) else '★'
        f2 = '等价' if (np.isnan(dc) or loc <= 0 <= hic) else '★'
        print(f"    {lab:20s} 全种子Δ={d:+.6f}[{lo:+.5f},{hi:+.5f}]{f1}  "
              f"共同存活Δ={dc:+.6f}[{loc:+.5f},{hic:+.5f}]{f2}")
    res[reskey] = {k: {kk: vv for kk, vv in v.items()
                       if kk not in ('alive_mask',)} for k, v in store.items()}


def main():
    print("=" * 70)
    print("实验 080 · 工具扩展的是【通道数】还是【精度】 —— 检验第 329 条")
    print("=" * 70)

    a1 = run_one(np.ones(8) * 0.5, 0)[0]
    a2 = run_one(np.linspace(0.2, 0.8, 8), 0)[0]
    if abs(a1 - a2) < 1e-12:
        print("[FATAL] sal 未接通主通道（第 23 条）"); return
    print(f"[guard] sal 接通：等强 {a1:.6f} vs 梯度 {a2:.6f}")

    rows = fetch_all()
    print(f"\n[数据] 真实换能器读数 {len(rows)}/{len(CITIES)} 城")
    if len(rows) < 16:
        print("[FATAL] 读数不足"); return
    T = np.array([r["temperature"] for r in rows], float)
    H = np.array([r["humidity"] for r in rows], float)
    P = np.array([r["pressure"] for r in rows], float)
    print(f"  温度 {T.min():.0f}~{T.max():.0f}°C  湿度 {H.min():.0f}~{H.max():.0f}%  "
          f"气压 {P.min():.0f}~{P.max():.0f}hPa")
    res = dict(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"), config=dict(
        ticks=TICKS, k_sal=K_SAL, seeds=len(SEEDS), n_inst=N_INST, forage_ch=FORAGE),
        n_cities=len(rows), cities=rows)
    T01, H01, P01 = norm01(T), norm01(H), norm01(P)
    base8 = to_range(T01[:8])

    # ---------------- Part A · 精度 ----------------
    print("\n=== Part A · 精度（离散档数 L），N=8 固定 ===")
    sA = {}
    for L in [2, 3, 5, 10, 20, 100, None]:
        batch([to_range(quantize(T01[:8], L))], f"L={L}" if L else "L=∞连续", sA)
    cmp_all(sA, "L=∞连续", "partA_precision", res)

    # ---------------- Part B · 通道数 ----------------
    print("\n=== Part B · 通道数：平铺（零新增信息）vs 真扩（新增信息）===")
    sB = {}
    for k in [1, 2, 3, 4]:
        batch([np.tile(base8, k)], f"平铺k={k}(N={8*k})", sB)
    for n in [8, 16, 24, 30]:
        if n <= len(T01):
            batch([to_range(T01[:n])], f"真扩N={n}", sB)
    cmp_all(sB, "平铺k=1(N=8)", "partB_channel_count", res)

    # ---------------- Part C · 新加一个通道，内容决定什么 ----------------
    print("\n=== Part C · 新增 1 个通道：内容决定什么（N=9）===")
    rng = np.random.default_rng(2026)
    sC = {}
    batch([np.concatenate([base8, [0.5]])], "基线+中性0.5", sC)                    # 中性参照
    batch([np.concatenate([base8, [base8[i]]]) for i in range(N_INST)], "+复制既有", sC)
    batch([np.concatenate([base8, to_range(T01[8 + i:9 + i])]) for i in range(N_INST)],
          "+新温度样本", sC)
    batch([np.concatenate([base8, to_range(H01[8 + i:9 + i])]) for i in range(N_INST)],
          "+真实湿度", sC)
    batch([np.concatenate([base8, to_range(P01[8 + i:9 + i])]) for i in range(N_INST)],
          "+真实气压", sC)
    batch([np.concatenate([base8, to_range([rng.uniform(0, 1)])])
           for _ in range(N_INST)], "+均匀噪声", sC)
    batch([np.concatenate([base8, to_range(T01[(20 + i) % len(T01):(21 + i) % len(T01)])])
           for i in range(N_INST)], "+错配温度", sC)
    # 剂量：新增 1/2/4 个真实湿度通道
    for m in [1, 2, 4]:
        batch([np.concatenate([base8, to_range(H01[8 + i:8 + i + m])])
               for i in range(N_INST)], f"+{m}个湿度通道", sC)
    cmp_all(sC, "基线+中性0.5", "partC_new_channel", res)

    # ---------------- Part D · 独立度 ----------------
    print("\n=== Part D · 新维度相对既有通道的真实独立度 ===")
    r_TH = float(np.corrcoef(T, H)[0, 1]); r_TP = float(np.corrcoef(T, P)[0, 1])
    print(f"  温度-湿度 r={r_TH:+.4f}   温度-气压 r={r_TP:+.4f}")
    res["partD_independence"] = dict(r_temp_hum=r_TH, r_temp_pres=r_TP,
                                     n=len(T),
                                     note="用于解释 Part C 中各新增通道的增益排序")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n[落盘] {OUT}")


if __name__ == '__main__':
    main()
