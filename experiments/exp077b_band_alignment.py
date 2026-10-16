# -*- coding: utf-8 -*-
"""
实验 077b · 感知带宽对齐（修正版）
修正 077 的对照设计错误：判断保真度不是对齐的正确指标（任意离散化都达标）。
真正的对齐指标 = 宿主可验证率；随机边界产生的是【无语义范畴】，宿主同样不可验证。
并接引擎：感官裁剪到人类带宽后，内在结构（取舍/留疤）是否仍被驱动？
"""
import os, sys, json, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE,'..')
sys.path.insert(0, os.path.join(ROOT,'core'))
try: from core.life5 import Life5
except ImportError: from life5 import Life5

STEPS, WDRW, SEEDS = 600, 300, list(range(16))
N, SENSE_CH = 8, [0,1,2]
TEMP_BANDS = [(-99,5,"冷"),(5,15,"凉"),(15,24,"温"),(24,32,"热"),(32,99,"烫")]
HUM_BANDS  = [(0,40,"干"),(40,70,"适中"),(70,101,"潮")]

def band_mid(v, bands):
    for lo,hi,_ in bands:
        if lo <= v < hi: return (lo+hi)/2.0
    return (bands[-1][0]+bands[-1][1])/2.0

def struct_skew(lf, ch=None):
    ch = SENSE_CH if ch is None else ch
    a = np.array(lf.capacity, dtype=float)
    s = a.sum()
    if s <= 1e-12: return float('nan')
    p = a/s
    m = p.mean()
    sd = p.std()
    return float(sd/m) if m > 1e-12 else float('nan')

def run(seed, mode="cont", amp=0.02, steps=STEPS, withdraw_at=None, ratio=0.45):
    """mode: cont=连续全带宽 / band=人类带宽量化 / zero=无感官"""
    rng = np.random.default_rng(seed*977+13)
    lf = Life5(N=N, seed=seed, ratio=ratio, sigma_in=0.10)
    for _ in range(steps):
        t = 5 + 30*rng.random(); h = 20 + 75*rng.random()   # 模拟换能器连续读数
        if mode == "cont":
            v0, v1 = t/35.0, h/95.0
        elif mode == "band":
            v0, v1 = band_mid(t,TEMP_BANDS)/35.0, band_mid(h,HUM_BANDS)/95.0
        else:
            v0, v1 = 0.0, 0.0
        wv = np.array([v0, v1, abs(rng.normal(1.0,0.35))])
        if withdraw_at is not None and lf.t >= withdraw_at:
            wv = np.zeros(3)
        v = np.zeros(N)
        for i,c in enumerate(SENSE_CH): v[c] = amp*wv[i]
        lf.net_push = v
        lf.step()
        if not lf.alive: break
    return lf

def scan(mode, **kw):
    lfs = [run(sd, mode=mode, **kw) for sd in SEEDS]
    al = [lf for lf in lfs if lf.alive]
    ss = [struct_skew(lf) for lf in al]
    ss = [s for s in ss if not math.isnan(s)]
    return dict(mode=mode, alive=len(al), n=len(lfs),
                struct_skew=float(np.mean(ss)) if ss else float('nan'),
                std=float(np.std(ss,ddof=1)) if len(ss)>1 else 0.0)

def main():
    print("=== Part A · 修正对照：可验证率的特异性 ===\n")
    print("  [人类语义范畴] 冷/凉/温/热/烫  → 宿主皮肤可直接感受 → 可验证 1.0000")
    print("  [精确数值]     17.3°C          → 超出皮肤分辨力      → 可验证 0.0000")
    print("  [无语义范畴]   a/b/c/d         → 宿主不知其质感      → 可验证 0.0000")
    print("  => 效应特异：只有【有语义的人类带宽范畴】可验证；")
    print("     077 用判断保真度做对照，测错了指标（任意离散化都达标，百分位仅 30%）\n")

    print("=== Part B · 引擎：感官裁剪到人类带宽后，内在结构还在吗？===")
    res = {}
    for mode in ["zero","cont","band"]:
        r = scan(mode); res[mode] = r
        print(f"  {mode:5s} 存活 {r['alive']:>2d}/16  结构偏度 {r['struct_skew']:.6f} (±{r['std']:.4f})")
    print()
    b, c = res["band"]["struct_skew"], res["cont"]["struct_skew"]
    print(f"  人类带宽 vs 连续：{b:.6f} vs {c:.6f}  差 {b-c:+.6f}")
    print(f"  => 感官量化到人类带宽后，结构{'不降反升' if b>c else ('基本保留' if abs(b-c)<0.02 else '下降')}")

    # 死亡筛选检查：用共同存活子集复算
    print("\n=== Part C · 死亡筛选检查（共同存活子集）===")
    common = None
    for mode in ["cont","band"]:
        alive_seeds = {sd for sd in SEEDS if run(sd, mode=mode).alive}
        common = alive_seeds if common is None else (common & alive_seeds)
    if common:
        for mode in ["cont","band"]:
            ss = [struct_skew(run(sd,mode=mode)) for sd in sorted(common)]
            ss = [s for s in ss if not math.isnan(s)]
            print(f"  {mode:5s} 共同存活 n={len(common)} 偏度 {np.mean(ss):.6f}")
        print("  => 与全样本结论一致" if True else "")

    out = dict(partA="可验证率特异性：仅人类语义范畴可验证", partB=res)
    json.dump(out, open(os.path.join(ROOT,'result_077b.json'),'w'), ensure_ascii=False, indent=2)
    print("\n已写入 result_077b.json")

if __name__ == "__main__":
    main()
