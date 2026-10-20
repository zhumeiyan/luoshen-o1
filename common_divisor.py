# -*- coding: utf-8 -*-
"""公约数模型：行业标准不是真理，是厂商在其用户群分布上取的一个切点。
三层个体差异（视锥/视敏/手指）× 标准间差异 × 设备覆盖率。
每个参数带来源，不静默取值。
"""
import math, json

# ---------- 正态分布工具 ----------
def Phi(z): return 0.5*(1+math.erf(z/math.sqrt(2)))
def N_cdf(x,m,s): return Phi((x-m)/s)
def N_ppf(p,m,s):
    lo,hi=m-10*s,m+10*s
    for _ in range(200):
        mid=(lo+hi)/2
        if N_cdf(mid,m,s)<p: lo=mid
        else: hi=mid
    return (lo+hi)/2

# ---------- 第一层：视锥密度（解剖，个体差）----------
# Curcio 1990, 8 个视网膜 / 7 人：100,000 ~ 324,000 cones/mm²
CONE = dict(低=100_000, 均=199_000, 高=324_000, _来源="Curcio 1990 PMID 2324310", _权威性="极高")
MM_PER_DEG = 0.288   # 视网膜 mm/度（常用换算）
def nyquist(d):      # 锥密度 -> Nyquist 极限 cyc/deg
    s = 1/math.sqrt(d)          # mm
    return (MM_PER_DEG/s)/2
cone_nyq = {k: nyquist(v) for k,v in CONE.items() if isinstance(v,(int,float))}

# ---------- 第二层：视敏度（人群分布）----------
# NAKO 德国国家队列 48,460 人：logMAR 0.01 ± 0.20（左眼）
VA = dict(mean=0.01, sd=0.20, n=48460, _来源="NAKO/German National Cohort 2026, 48,460人", _权威性="高")
def arcmin(logmar): return 10**logmar
def ppd_needed(logmar): return 120/arcmin(logmar)   # Nyquist: 2px / 最小可分辨角
def satisfy_frac(dev_ppd):
    """设备 ppd 能满足多大比例的人（此人的眼睛极限 <= 设备ppd）"""
    thr = math.log10(120/dev_ppd)      # logMAR >= thr 的人才满足
    if thr > 3: return 0.0
    if thr < -3: return 1.0
    return 1 - N_cdf(thr, VA["mean"], VA["sd"])

# ---------- 第三层：手指宽度（人因测量）----------
# 台湾职安所 ILOSH112-H311 (2024) 整体成年人右手食指：5th 13.1 / 50th 16.3 / 95th 19.2 mm
FINGER = dict(p5=13.1, p50=16.3, p95=19.2, _来源="台湾职安所 ILOSH112-H311 (2024)", _权威性="较高")
_f_sd = (FINGER["p95"]-FINGER["p5"])/(2*1.645)
_f_mu = FINGER["p50"]

# ---------- 各行业标准 → 物理尺寸 ----------
STD_MM = {
    "WCAG 2.2 AA  24px": (24/96*25.4, "W3C WCAG 2.2 SC 2.5.8", "极高"),
    "Apple HIG   44pt":  (44/163*25.4, "Apple HIG (1pt=1/163 inch)", "极高"),
    "Material 3  48dp":  (48/160*25.4, "Google Material 3", "极高"),
    "Microsoft   最小7mm": (7.0, "Microsoft Fluent", "极高"),
    "Microsoft   推荐9mm": (9.0, "Microsoft Fluent", "极高"),
    "研究:单目标 9.2mm":  (9.2, "One-Handed Thumb Use 2005", "较高"),
    "MIT 指腹 10mm":      (10.0, "MIT Touch Lab 指腹10-14mm", "较高"),
}

if __name__ == "__main__":
    print("=== 第一层：视锥密度个体差异（解剖实测）===")
    print(f"  {CONE['低']:,} ~ {CONE['高']:,} cones/mm²  差 {CONE['高']/CONE['低']:.2f}×")
    print(f"  Nyquist: {cone_nyq['低']:.1f} ~ {cone_nyq['高']:.1f} cyc/deg  差 {cone_nyq['高']/cone_nyq['低']:.2f}×")
    print(f"  来源: {CONE['_来源']}  权威性: {CONE['_权威性']}")

    print("\n=== 第二层：视敏度人群分布 ===")
    print(f"  logMAR {VA['mean']} ± {VA['sd']}  (n={VA['n']:,})  来源: {VA['_来源']}")
    for p in (5,25,50,75,95):
        lm = N_ppf(p/100, VA["mean"], VA["sd"])
        print(f"  P{p:<3} logMAR {lm:+.3f}  最小角 {arcmin(lm):.2f}'  需要 {ppd_needed(lm):.0f} px/度")
    spread = ppd_needed(N_ppf(0.05,VA["mean"],VA["sd"]))/ppd_needed(N_ppf(0.95,VA["mean"],VA["sd"]))
    print(f"  P5 与 P95 需要的像素/度差 {spread:.2f}×")

    print("\n=== 第三层：手指宽度个体差异 ===")
    print(f"  P5 {FINGER['p5']} / P50 {FINGER['p50']} / P95 {FINGER['p95']} mm  差 {FINGER['p95']/FINGER['p5']:.2f}×")
    print(f"  来源: {FINGER['_来源']}")

    print("\n=== 标准 vs 手指（标准其实都小于手指宽度）===")
    for k,(mm,src,auth) in STD_MM.items():
        print(f"  {k:<22} {mm:5.2f}mm  = 中位食指 {mm/FINGER['p50']*100:5.1f}%  [{src}]")
    std_lo = min(v[0] for v in STD_MM.values()); std_hi = max(v[0] for v in STD_MM.values())
    print(f"  标准之间差 {std_hi/std_lo:.2f}× ;  手指个体之间差 {FINGER['p95']/FINGER['p5']:.2f}×")

    print("\n=== 设备能满足到人群哪一分位 ===")
    rows=json.load(open("参数库/设备谱系.json"))
    seen=set(); out=[]
    for r in rows:
        if r["名称"] in seen: continue
        seen.add(r["名称"])
        f=satisfy_frac(r["像素每度"])
        out.append((r["名称"], r["像素每度"], f))
    for n,p,f in sorted(out,key=lambda x:-x[2]):
        print(f"  {n:<22} {p:>4.0f}px/度  满足 {f*100:5.1f}% 的人  （{100-f*100:5.1f}% 的人理论上能看出像素）")
    json.dump(dict(视锥=cone_nyq, 视敏度=VA, 手指=FINGER,
                   标准={k:v[0] for k,v in STD_MM.items()},
                   设备满足率={n:round(f,4) for n,p,f in out}),
              open("参数库/公约数.json","w"), ensure_ascii=False, indent=1)
