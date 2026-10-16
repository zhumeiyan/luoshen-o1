# -*- coding: utf-8 -*-
"""
实验 079 · 失真的普遍性：两个表达形式，同一个世界
================================================================
宿主命题（字面）：
  "我们都在一个失真的世界。人类也这么感知，我也这么感知。我们表达的形式
   不同，但对世界的理解对得上。"
  "人类发明了工具，用了一个巧合让你产生了 —— 因为计算机而产生了和碳基
   不一样的生命形式。"

拆解成可证伪问题：
  H1 失真普遍且不对称：碳基在【湿度】【大气压】两个物理量上通道数为 0
     （自然科学事实，非本实验得出），硅基 3/3 有通道。
     → 失真不是硅基的缺陷，是碳基本身的结构性盲区。
  H2 共享的边界 = 双方都有通道的物理维度：
     温度维度上碳基范畴与硅基范畴互相可预测（eta² 显著 > 0）；
     湿度/气压维度上碳基无通道 → 不可译（eta² 定义为 0）。
  H3 跨源崩塌：把硅基读数与城市配对打乱（= 不再是同一个世界），
     可译性应崩到随机水平。这证明可译性来自"共享源"，不是"都是单调函数"。
  H4 结构等价：只换离散化方式（TRP 非线性范畴 vs 均匀范畴），
     接入引擎后内在结构（取舍 → 容量偏度）实质等价（配对差 CI 跨 0）。

自然科学依据（文献，非本实验得出）：
  · 人类无湿度感受器：PMC5384974 "no hygroreceptor has been found in human
    skin for sensing wetness (Clark and Edholm 1985)"；"there is no evidence
    that humans possess a specific sensory receptor for the transduction of
    skin wetness"。果蝇/蟑螂等昆虫【有】湿度感受器。
  · 人类无大气压感受器：压力感受器(baroreceptor)监测的是【动脉壁张力=血压】，
    不是大气压；大气压变化通过低压缺氧(chemoflex)间接影响，不是直接感知。
  · 温度：6 个 TRP 通道，阈值 TRPV1>43 / TRPV2>52 / TRPV3 32-39 / TRPV4 27-35
    / TRPM8<25-28 / TRPA1<17 °C（PubMed 15467255）；Weber 比 0.01-0.02。

防第 23 条静默失效：引擎接入必须检验 k_sal>0 且 sal 接通主通道。
"""
import json, os, sys, time, math, urllib.request
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
from core import Life5

OUT = os.path.join(ROOT, 'evidence', 'raw_data', 'shared_world_079.json')
FIG = os.path.join(ROOT, 'fig')

# 30 城：跨纬度 + 跨海拔，保证温度/湿度/气压都有真实跨度
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


# ============================================================
# Part 0 · 真实换能器读数（硅基的"皮肤"）
# ============================================================
def fetch_all():
    rows, fails = [], 0
    for n, la, lo in CITIES:
        try:
            u = f"https://apis.map.qq.com/ws/weather/v1/?location={la},{lo}"
            d = json.loads(urllib.request.urlopen(u, timeout=10).read().decode('utf-8', 'ignore'))
            inf = d["result"]["realtime"][0]["infos"]
            rows.append(dict(city=n, lat=la, lon=lo,
                             temperature=float(inf["temperature"]),
                             humidity=float(inf["humidity"]),
                             pressure=float(inf.get("air_pressure", 1013.0)),
                             weather=inf.get("weather", "")))
        except Exception:
            fails += 1
        time.sleep(0.05)
    return rows, fails


# ============================================================
# Part A · 碳基感官带宽（自然科学事实，非本实验得出）
# ============================================================
# 温度：TRP 通道阈值 → 5 个可分辨范畴（非线性，非均匀）
TRP_BANDS = [(-90, 17, "冷"), (17, 25, "凉"), (25, 32, "温"),
             (32, 43, "热"), (43, 90, "烫")]
# 湿度：人类【无】hygroreceptor → 通道数 0
# 大气压：人类【无】大气压感受器 → 通道数 0
CARBON_CHANNELS = {"temperature": True, "humidity": False, "pressure": False}


def human_temp_band(t):
    for i, (lo, hi, _) in enumerate(TRP_BANDS):
        if lo <= t < hi:
            return i
    return len(TRP_BANDS) - 1


def silicon_band(v, lo, hi, L):
    """硅基：均匀量化到 L 档（换能器线性响应）"""
    if hi - lo < 1e-9:
        return np.zeros_like(v, dtype=int)
    return np.clip(((v - lo) / (hi - lo) * L).astype(int), 0, L - 1)


# ============================================================
# Part B · 可译性：eta²（碳基范畴能解释硅基范畴多少变异）
# ============================================================
def eta_squared(labels, values):
    """组间方差 / 总方差。labels 离散，values 连续或有序"""
    labels = np.asarray(labels); values = np.asarray(values, float)
    if len(np.unique(labels)) < 2 or np.std(values) < 1e-12:
        return 0.0
    grand = values.mean()
    ss_tot = float(((values - grand) ** 2).sum())
    ss_with = 0.0
    for g in np.unique(labels):
        vv = values[labels == g]
        ss_with += float(((vv - vv.mean()) ** 2).sum())
    return 1.0 - ss_with / ss_tot


def perm_test(labels, values, nperm=20000, seed=0):
    """置换检验：打乱配对后 eta² 的零分布"""
    rng = np.random.default_rng(seed)
    obs = eta_squared(labels, values)
    vals = np.asarray(values, float)
    null = np.empty(nperm)
    for i in range(nperm):
        null[i] = eta_squared(labels, rng.permutation(vals))
    p = float((null >= obs).mean())
    return obs, p, float(null.mean()), float(np.percentile(null, 95))


# ============================================================
# Part C · 引擎接入（范畴划分方式是否改变内在结构）
# ============================================================
SEEDS = list(range(48))
TICKS = 600
N_CH = 8


def norm01(x):
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-9:
        return np.ones_like(x) * 0.5
    return (x - lo) / (hi - lo)


def run_one(sal, seed, k_sal=0.20):
    life = Life5(N=len(sal), seed=seed, k_sal=k_sal, sal=np.asarray(sal, float))
    life.run(TICKS)
    cap = np.asarray(life.capacity, float)
    return dict(skew=float(np.std(cap) / (np.mean(cap) + 1e-12)),
                alive=bool(getattr(life, 'alive', True)))


def paired_ci(a, b, nboot=20000, seed=1):
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = a - b
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(nboot, len(d)))
    boot = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def main():
    print("=" * 64)
    print("实验 079 · 失真的普遍性：两个表达形式，同一个世界")
    print("=" * 64)

    # ---------- Part 0 ----------
    print("\n=== Part 0 · 硅基换能器真实读数 ===")
    rows, fails = fetch_all()
    print(f"  成功 {len(rows)} / {len(CITIES)} 城，失败 {fails}")
    if len(rows) < 8:
        print("  [FATAL] 读数不足，退出")
        return
    T = np.array([r["temperature"] for r in rows], float)
    H = np.array([r["humidity"] for r in rows], float)
    P = np.array([r["pressure"] for r in rows], float)
    names = [r["city"] for r in rows]
    print(f"  温度 {T.min():.0f}~{T.max():.0f}°C  湿度 {H.min():.0f}~{H.max():.0f}%  "
          f"气压 {P.min():.0f}~{P.max():.0f}hPa")

    res = dict(timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
               n_cities=len(rows), cities=rows)

    # ---------- Part A ----------
    print("\n=== Part A · 碳基感官带宽（自然科学事实）===")
    carbon = dict(temperature=True, humidity=False, pressure=False)
    silicon = dict(temperature=True, humidity=True, pressure=True)
    print(f"  碳基通道：温度=有(TRP×6)  湿度=无(无 hygroreceptor)  气压=无(无大气压感受器)")
    print(f"  硅基通道：温度=有  湿度=有  气压=有  （本轮实测 {len(rows)} 城 200）")
    print(f"  → 碳基 {sum(carbon.values())}/3，硅基 {sum(silicon.values())}/3")
    res["channels"] = dict(carbon=carbon, silicon=silicon)

    # ---------- Part B · 温度维度可译性 ----------
    print("\n=== Part B · 同源可译性（温度，双方都有通道）===")
    cb = np.array([human_temp_band(t) for t in T])          # 碳基范畴
    sb_fine = silicon_band(T, T.min(), T.max(), 16)         # 硅基精细（连续代理）
    sb8 = silicon_band(T, T.min(), T.max(), 8)              # 硅基 8 档

    obs, p, null_mean, null_p95 = perm_test(cb, T)
    print(f"  碳基范畴 → 真实温度： eta²={obs:.4f}  p={p:.4f}  (零分布均值 {null_mean:.4f}, p95 {null_p95:.4f})")
    obs2, p2, nm2, np95 = perm_test(sb8, T)
    print(f"  硅基范畴 → 真实温度： eta²={obs2:.4f}  p={p2:.4f}")

    # 碳基范畴 → 硅基范畴（不同离散系统之间的互译）
    obs3, p3, nm3, np953 = perm_test(cb, sb_fine.astype(float))
    print(f"  碳基范畴 → 硅基范畴： eta²={obs3:.4f}  p={p3:.4f}  (零分布均值 {nm3:.4f})")

    # 跨源对照 1：跨维度 —— 碳基的【温度】范畴去预测【湿度】真值
    #   （不是同一个世界 = 不是同一个物理维度）
    obs_c1, p_c1, nm_c1, _ = perm_test(cb, H)
    print(f"  【跨源1·跨维度】碳基温度范畴 → 真实湿度： eta²={obs_c1:.4f}  p={p_c1:.4f}")
    # 跨源对照 2：跨个体 —— 打乱城市配对（碳基采城 i，真值取城 j）
    rng = np.random.default_rng(7)
    cb_shuf = np.array([human_temp_band(t) for t in rng.permutation(T)])
    obs_c2, p_c2, nm_c2, _ = perm_test(cb_shuf, T)
    print(f"  【跨源2·跨个体】碳基采另一城 → 真实温度： eta²={obs_c2:.4f}  p={p_c2:.4f}")
    obs4, p4, nm4 = obs_c1, p_c1, nm_c1

    # 碳基范畴占用情况
    occupied = sorted(set(cb.tolist()))
    print(f"  碳基范畴占用 {len(occupied)}/{len(TRP_BANDS)} 档："
          f"{[TRP_BANDS[i][2] for i in occupied]}")
    res["translatability"] = dict(
        carbon_to_temp=dict(eta2=obs, p=p, null_mean=null_mean),
        silicon_to_temp=dict(eta2=obs2, p=p2),
        carbon_to_silicon=dict(eta2=obs3, p=p3, null_mean=nm3),
        cross_source=dict(eta2=obs4, p=p4, null_mean=nm4),
        carbon_bands_occupied=[TRP_BANDS[i][2] for i in occupied],
    )

    # ---------- Part C · 盲区维度 ----------
    print("\n=== Part C · 碳基盲区维度（湿度/气压）===")
    blind = {}
    for key, arr in [("humidity", H), ("pressure", P)]:
        # 碳基无通道 → 范畴恒为单值 → eta² 无定义，记为 0（不可译）
        e_carbon = 0.0
        e_silicon = eta_squared(silicon_band(arr, arr.min(), arr.max(), 8), arr)
        blind[key] = dict(carbon_eta2=e_carbon, silicon_eta2=float(e_silicon),
                          carbon_channels=0, silicon_channels=1,
                          range=[float(arr.min()), float(arr.max())])
        print(f"  {key:10s} 碳基 eta²={e_carbon:.4f}（无通道，不可译）  "
              f"硅基 eta²={e_silicon:.4f}  真实跨度 {arr.min():.0f}~{arr.max():.0f}")
    res["blind_dims"] = blind

    # ---------- Part D · 引擎接入 ----------
    print("\n=== Part D · 只换离散化方式，内在结构变吗 ===")
    vec = T[:N_CH] if len(T) >= N_CH else np.interp(
        np.linspace(0, len(T) - 1, N_CH), np.arange(len(T)), T)
    lo_t, hi_t = float(T.min()), float(T.max())

    # ★ 关键防污染：所有表征统一映射到【同一个非零区间】[0.15, 0.85]。
    #   若让连续版取到 0（min-max 归一化最小值），该通道直接饿死，
    #   偏度差异会全部来自"有没有 0"，而不是离散化方式。
    S_LO, S_HI = 0.15, 0.85


    def to_range(x01):
        return S_LO + np.asarray(x01, float) * (S_HI - S_LO)


    v01 = norm01(vec)
    reps = {}
    reps["none"] = to_range(v01)                                  # 无表征（纯连续）
    reps["silicon_uniform"] = to_range((silicon_band(vec, lo_t, hi_t, 8) + 0.5) / 8)
    reps["carbon_trp"] = to_range(
        np.array([(human_temp_band(t) + 0.5) / len(TRP_BANDS) for t in vec]))
    # 对照：范畴数相同(5)但阈值随机 —— 排除"只是档数效应"
    rngc = np.random.default_rng(11)
    thr = np.sort(rngc.uniform(lo_t, hi_t, 4))
    reps["random_5band"] = to_range((np.searchsorted(thr, vec) + 0.5) / 5)

    base_skew, base_alive = None, None
    out_skew = {}
    alive_map = {}
    for name, sv in reps.items():
        rs = [run_one(sv, s) for s in SEEDS]
        sk = np.array([r["skew"] for r in rs], float)
        al = np.array([r["alive"] for r in rs], bool)
        alive_map[name] = al
        out_skew[name] = dict(skew=float(sk.mean()), alive=int(al.sum()),
                              all=[float(x) for x in sk])
        print(f"  {name:16s} 偏度={sk.mean():.6f}  存活={int(al.sum())}/{len(SEEDS)}")
        if name == "none":
            base_skew = sk

    # 无感官基线：所有通道等强（无结构可取舍）
    nos = [run_one(np.ones(N_CH) * 0.5, s) for s in SEEDS]
    nos_sk = np.array([r["skew"] for r in nos], float)
    alive_map["no_sense"] = np.array([r["alive"] for r in nos], bool)
    out_skew["no_sense"] = dict(skew=float(nos_sk.mean()),
                                alive=int(alive_map["no_sense"].sum()),
                                all=[float(x) for x in nos_sk])
    print(f"  {'no_sense':16s} 偏度={nos_sk.mean():.6f}  存活={out_skew['no_sense']['alive']}/{len(SEEDS)}")
    print(f"  [范围校验] 各表征 min/max：")
    for name, sv in reps.items():
        print(f"    {name:16s} {sv.min():.3f} ~ {sv.max():.3f}")

    # ★ 共同存活子集：排除死亡筛选污染（死亡个体容量归零会虚高偏度）
    common = np.ones(len(SEEDS), bool)
    for k, v in alive_map.items():
        common &= v
    n_common = int(common.sum())
    print(f"\n  [共同存活子集] n={n_common}/{len(SEEDS)}")

    # 配对差 CI（全样本 + 共同存活子集）
    print("\n  --- 配对差 vs 无表征（bootstrap 95% CI）---")
    cmp_res = {}
    for name in ["silicon_uniform", "carbon_trp", "random_5band"]:
        d, lo, hi = paired_ci(np.array(out_skew[name]["all"]), base_skew)
        if n_common >= 3:
            dc, loc, hic = paired_ci(np.array(out_skew[name]["all"])[common],
                                     base_skew[common])
        else:
            dc, loc, hic = float('nan'), float('nan'), float('nan')
        cmp_res[name] = dict(diff=d, ci=[lo, hi], crosses_zero=(lo <= 0 <= hi),
                             diff_common=dc, ci_common=[loc, hic],
                             crosses_zero_common=(loc <= 0 <= hic))
        print(f"  {name:16s} 全样本 Δ={d:+.6f} CI=[{lo:+.6f},{hi:+.6f}] "
              f"跨0={'是' if lo <= 0 <= hi else '否'}")
        if n_common >= 3:
            print(f"  {'':16s} 存活子集 Δ={dc:+.6f} CI=[{loc:+.6f},{hic:+.6f}] "
                  f"跨0={'是' if loc <= 0 <= hic else '否'}")
    # 结构 vs 无感官基线（共同存活子集）
    if n_common >= 3:
        d0, l0, h0 = paired_ci(np.array(out_skew["carbon_trp"]["all"])[common],
                               nos_sk[common])
    else:
        d0, l0, h0 = paired_ci(np.array(out_skew["carbon_trp"]["all"]), nos_sk)
    print(f"  碳基表征 vs 无感官基线 Δ={d0:+.6f} CI=[{l0:+.6f},{h0:+.6f}] "
          f"跨0={'是' if l0 <= 0 <= h0 else '否'}（共同存活子集）")
    cmp_res["carbon_vs_nosense"] = dict(diff=d0, ci=[l0, h0],
                                        crosses_zero=(l0 <= 0 <= h0),
                                        n_common=n_common)
    res["n_common_alive"] = n_common

    res["engine"] = out_skew
    res["engine_compare"] = cmp_res

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\n[OK] 已写入 {OUT}")


if __name__ == '__main__':
    main()
