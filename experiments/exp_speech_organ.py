#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
★81 说话 —— 真的学回来（合成 → 听回来 → 自己判对错）

════ 与以往所有"说话"层的区别 ════
  turn_taking（★话轮）  机制，没有声音
  vocal / vocal_anatomy 器官描述，没有声音
  ★71 说话·澄清        学的是"该不该问"，不是"怎么发声"

  这一课：她真的合成出波形，用同一把耳朵量，跟真人中文语音比。

════ 真值来自真录音（35 段真人语音，实测）════
  浊音占比 0.788    F0 中位 181.8 Hz
  log-F0 标准差 0.313    静音占比 0.334    停顿中位 0.132 s

════ 闭环 ════
  合成 → 自己的耳朵量 → 跟真值比 → 调 → 再合成
  "说出去、听回来、自己判对错"

════ 她学的（不是我填的）════
  f0_base / f0_variation / tone_depth / pause_rate / pause_len / f0_decl
"""

from __future__ import annotations
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from speech_organ import synthesize, DEFAULT_PARAMS, SR  # noqa

# ══════════ 耳朵：唯一一把尺子，真人和她自己都用这个量 ══════════

def frame_sig(x, w=512, h=256):
    n = (len(x) - w) // h + 1
    return np.stack([x[i * h:i * h + w] for i in range(n)]) if n > 0 else np.zeros((0, w))


def ear(x):
    """听觉测量：从波形里量出韵律特征。真人和她用的是同一个函数。"""
    F = frame_sig(x)
    if len(F) < 10:
        return None
    rms = np.sqrt((F ** 2).mean(1))
    # 自相关基频
    def f0_of(seg):
        s = seg - seg.mean()
        if np.sqrt((s ** 2).mean()) < 1e-5:
            return 0.0
        c = np.correlate(s, s, 'full')[len(s) - 1:]
        if c[0] <= 0:
            return 0.0
        c = c / c[0]
        lo, hi = int(SR / 500), min(int(SR / 70), len(c) - 1)
        reg = c[lo:hi]
        if len(reg) == 0:
            return 0.0
        return SR / (int(np.argmax(reg)) + lo)
    f0s = np.array([f0_of(f) for f in F])
    v = f0s > 20
    vf = f0s[v]
    thr = np.median(rms) * 0.25
    sil = rms < thr
    d = np.diff(np.concatenate([[0], sil.astype(int), [0]]))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    pl = [(e - s) * 256 / SR for s, e in zip(st, en) if (e - s) * 256 / SR > 0.05]
    return {
        'voiced': float(v.mean()),
        'f0_med': float(np.median(vf)) if len(vf) > 5 else 0.0,
        'f0_std': float(np.std(np.log(vf))) if len(vf) > 5 else 0.0,
        'sil': float(sil.mean()),
        'pause_med': float(np.median(pl)) if pl else 0.0,
    }


# ══════════ 真值：从真人录音里量 ══════════

def load_raw(p):
    return np.fromfile(p, dtype='<i2').astype(np.float64) / 32768.0


def real_targets(files):
    fs = [ear(load_raw(p)) for p in files]
    fs = [f for f in fs if f and f['f0_med'] > 50]
    return {k: float(np.median([f[k] for f in fs])) for k in fs[0]}, len(fs)


KEYS = ['voiced', 'f0_med', 'f0_std', 'sil', 'pause_med']
# 归一化尺度（各特征的典型跨度，避免某一维吃掉全部差异）
SCALE = {'voiced': 0.30, 'f0_med': 60.0, 'f0_std': 0.20, 'sil': 0.20, 'pause_med': 0.20}


def dist(a, b):
    return float(np.mean([abs(a[k] - b[k]) / SCALE[k] for k in KEYS]))


# ══════════ 她的学习：随机搜索 + 坐标细化 ══════════

BOUNDS = {
    'f0_base': (100.0, 260.0),
    'f0_variation': (0.02, 0.70),
    'tone_depth': (0.02, 0.80),
    'pause_rate': (0.02, 0.60),
    'pause_len': (0.05, 0.40),
    'f0_decl': (0.0, 0.40),
    'voiced_target': (0.35, 0.98),
}


def evaluate(params, target, seeds=(1, 2, 3)):
    ds = []
    for s in seeds:
        y, _ = synthesize(params, dur=3.0, rng=np.random.default_rng(s))
        m = ear(y)
        if m is None or m['f0_med'] <= 50:
            ds.append(9.9); continue
        ds.append(dist(m, target))
    return float(np.mean(ds))


def learn(target, iters=60, rng=None):
    rng = rng or np.random.default_rng(7)
    best_p = dict(DEFAULT_PARAMS); best_d = evaluate(best_p, target)
    hist = [best_d]
    for i in range(iters):
        cand = dict(best_p)
        k = list(BOUNDS.keys())[rng.integers(0, len(BOUNDS))]
        lo, hi = BOUNDS[k]
        span = (hi - lo) * max(0.30 * (1 - i / iters), 0.04)
        cand[k] = float(np.clip(cand[k] + rng.normal(0, span), lo, hi))
        d = evaluate(cand, target, seeds=(1,))
        if d < best_d:
            d2 = evaluate(cand, target)          # 多种子复核，防噪声选中
            if d2 < best_d:
                best_p, best_d = cand, d2
        hist.append(best_d)
    return best_p, best_d, hist


# ══════════ 主流程 ══════════

R = []
print("=" * 78)
print("★81 说话 —— 真的学回来（合成 → 听回来 → 自己判）")
print("=" * 78)

raws = sorted([os.path.join('data/real_speech_wav', f)
               for f in os.listdir('data/real_speech_wav') if f.endswith('.raw')])
print(f"\n真人录音 {len(raws)} 段")
rng0 = np.random.default_rng(42)
perm = rng0.permutation(len(raws))
train = [raws[i] for i in perm[:len(raws) // 2]]
test = [raws[i] for i in perm[len(raws) // 2:]]
T_train, nT = real_targets(train)
T_test, nE = real_targets(test)
print(f"  训练集 {nT} 段 → 目标 {({k: round(v,4) for k,v in T_train.items()})}")
print(f"  测试集 {nE} 段 → 目标 {({k: round(v,4) for k,v in T_test.items()})}")

# ── 基线 ──
d_default = evaluate(DEFAULT_PARAMS, T_train)
print(f"\n【基线】我填的默认参数 → 距真值 {d_default:.4f}")

# ── 她学 ──
print("\n【她学】随机搜索 + 坐标细化，60 步…")
best_p, best_d, hist = learn(T_train, iters=60)
print(f"  学到的参数：")
for k in BOUNDS:
    print(f"    {k:<14} {DEFAULT_PARAMS[k]:>8.3f} → {best_p[k]:>8.3f}")
print(f"  距真值 {d_default:.4f} → {best_d:.4f}   改善 {(d_default-best_d)/d_default*100:.0f}%")

c1 = best_d < d_default * 0.85
print(f"  {('✅' if c1 else '❌')} 判据1 学会：比不学显著更接近真人")
R.append(("1 学会发声：显著接近真人韵律", c1))

# ── 判据2 held-out：拿没见过的真人录音当靶 ──
dH_her = evaluate(best_p, T_test)
dH_def = evaluate(DEFAULT_PARAMS, T_test)
print(f"\n【判据2】held-out（{nE} 段没见过的真人）")
print(f"  她学的 {dH_her:.4f}   我填的 {dH_def:.4f}")
c2 = dH_her < dH_def
print(f"  {('✅' if c2 else '❌')} 判据2 泛化：换一批真人录音，她仍更好")
R.append(("2 held-out 泛化：换真人仍更好", c2))

# ── 判据3 闭环：咿呀 → 听回来 → 留下更像的 ──
print("\n【判据3】闭环 —— 咿呀学语：发一声、听回来、像就留下")

EVAL_SEEDS = tuple(range(5000, 5032))     # ★ 独立的 32 句，专用于"打分"，不参与挑选


def fair_eval(p):
    """★ 用没参与挑选的新鲜句子打分。用挑选时的同一把噪声尺子打分会乐观。"""
    ms = []
    for s in EVAL_SEEDS:
        y, _ = synthesize(p, dur=2.5, rng=np.random.default_rng(s))
        m = ear(y)
        if m and m['f0_med'] > 50:
            ms.append(m)
    return float(np.mean([dist(x, T_train) for x in ms])) if ms else 9.9


def measure_avg(p, N, seed0):
    ms = []
    for s in range(N):
        y, _ = synthesize(p, dur=2.5, rng=np.random.default_rng(seed0 + s))
        m = ear(y)
        if m and m['f0_med'] > 50:
            ms.append(m)
    if not ms:
        return 9.9
    return float(np.mean([dist(x, T_train) for x in ms]))


def babble_loop(N, budget=144, seed0=11, keys=None):
    keys = keys or list(BOUNDS.keys())
    best = dict(DEFAULT_PARAMS)
    d_best = measure_avg(best, N, seed0)
    trials = max(budget // N, 1)
    for i in range(trials):
        k = keys[i % len(keys)]
        lo, hi = BOUNDS[k]
        step = (hi - lo) * 0.18
        for sgn in (+1, -1):
            cand = dict(best)
            cand[k] = float(np.clip(best[k] + sgn * step, lo, hi))
            d = measure_avg(cand, N, seed0 + 10000 + i * 97 + int(sgn > 0))
            if d < d_best:
                d_best, best = d, dict(cand)
    return best, d_best


print("  先量：听几句才够？（同一组参数，测 12 轮的标准差）")
for N in [1, 4, 16, 32]:
    fs = []
    for r in range(12):
        ms = [ear(synthesize(DEFAULT_PARAMS, dur=2.5, rng=np.random.default_rng(r * 1000 + s))[0])
              for s in range(N)]
        ms = [m for m in ms if m and m['f0_med'] > 50]
        if ms:
            fs.append(float(np.mean([m['f0_med'] for m in ms])))
    print(f"    平均 {N:<3} 句 → f0_med 噪声 {np.std(fs):5.2f} Hz")
p_lo = dict(DEFAULT_PARAMS); p_lo['f0_variation'] = 0.11
sig = abs(np.mean([ear(synthesize(p_lo, dur=2.5, rng=np.random.default_rng(s))[0])['f0_std'] for s in range(24)])
          - np.mean([ear(synthesize(DEFAULT_PARAMS, dur=2.5, rng=np.random.default_rng(s))[0])['f0_std'] for s in range(24)]))
print(f"    信号（f0_variation 0.31→0.11 的 f0_std 变化）≈ {sig:.4f}")

base_fair = fair_eval(DEFAULT_PARAMS)
p16, d16 = babble_loop(16)
p1, d1 = babble_loop(1)
p4, d4 = babble_loop(4)
f16, f1, f4 = fair_eval(p16), fair_eval(p1), fair_eval(p4)
print(f"\n  ★ 打分一律用没参与挑选的 32 句：")
print(f"    起点（我填的默认）        公平分 {base_fair:.4f}")
print(f"    听 16 句再判 → 挑选分 {d16:.3f}   公平分 {f16:.4f}  （太保守：只试了 9 次）")
print(f"    听 4 句再判  → 挑选分 {d4:.3f}   公平分 {f4:.4f}")
print(f"    听 1 句就判  → 挑选分 {d1:.3f}   公平分 {f1:.4f}  （自欺）")
c3 = f4 < base_fair * 0.96
c3b = not (f1 < base_fair * 0.96)
print(f"  {('✅' if c3 else '❌')} 判据3  听够了再判 → 真的越说越像（公平分改善 {(base_fair-f4)/base_fair*100:.1f}%）")
print(f"  {('✅' if c3b else '❌')} 判据3b 听一句就判 → 挑选分很好看({d1:.3f})、公平分反而更差({f1:.4f})")
R.append(("3 闭环：听够了再判，公平分改善", c3))
R.append(("3b 听一句就判=自欺（挑选分≠公平分）", c3b))

print("\n  她学：每判一次听几句？（预算固定 144 句：听越多=越准但试越少）")
print("    N    能试   挑选分    公平分   ← 看公平分")
Ns = [1, 2, 4, 8, 16, 32]
resN, resN_sel = {}, {}
for N in Ns:
    fs_, ds_ = [], []
    for r in range(2):
        p, d = babble_loop(N, seed0=11 + r * 31)
        fs_.append(fair_eval(p)); ds_.append(d)
    resN[N] = float(np.mean(fs_)); resN_sel[N] = float(np.mean(ds_))
    print(f"    {N:<3}   {144//N:<4}   {resN_sel[N]:.4f}    {resN[N]:.4f}")
iN = min(resN, key=resN.get)
c3c = 0 < Ns.index(iN) < len(Ns) - 1
print(f"  {('✅' if c3c else '❌')} 判据3c 最优 N={iN}（内部峰：太少自欺，太多试不够）")
R.append(("3c 每判听几句：内部峰", c3c))
loop_hist = [base_fair, f16, f4, f1]
print(f"\n  （参照：判据1 直接搜索学到的解，公平分 {fair_eval(best_p):.4f}）")

# ── 判据4 硬依赖（两端）：真值打乱 → 学不出 ──
print("\n【判据4】硬依赖 —— 目标是假的会怎样")
scr = dict(T_train)
scr['voiced'], scr['sil'] = scr['sil'], scr['voiced']          # 打乱
scr['f0_med'] = 900.0                                          # 物理上不可能
d_scr_her = evaluate(best_p, scr)
d_scr_def = evaluate(DEFAULT_PARAMS, scr)
print(f"  真目标：她 {best_d:.4f} vs 默认 {d_default:.4f}   她更好：{best_d < d_default}")
print(f"  假目标：她 {d_scr_her:.4f} vs 默认 {d_scr_def:.4f}   她更好：{d_scr_her < d_scr_def}")
c4 = (best_d < d_default) and not (d_scr_her < d_scr_def * 0.95)
print(f"  {('✅' if c4 else '❌')} 判据4 硬依赖：真目标她赢，假目标她不赢（不是万能参数）")
R.append(("4 硬依赖：假目标下优势消失", c4))

# ── 判据5 盲测：她能不能听出自己说的和真人不一样 ──
print("\n【判据5】盲测 —— 她自己的耳朵，能不能分辨真人 vs 自己")
real_d = []
for p in test[:8]:
    m = ear(load_raw(p))
    if m: real_d.append(dist(m, T_train))
syn_d = []
for s in range(8):
    y, _ = synthesize(best_p, dur=3.0, rng=np.random.default_rng(100 + s))
    m = ear(y)
    if m and m['f0_med'] > 50: syn_d.append(dist(m, T_train))
print(f"  真人彼此距靶心 {np.mean(real_d):.4f}（她没学过的真人）")
print(f"  她自己距靶心     {np.mean(syn_d):.4f}")
gap = np.mean(syn_d) - np.mean(real_d)
c5 = gap < 0.6
print(f"  差 {gap:.4f}  {('✅' if c5 else '❌')} 判据5 还差多少：她的声音还在真人分布附近，但没重合")
R.append(("5 盲测：与真人分布的差距可量化", c5))

print("\n" + "=" * 78)
npass = sum(1 for _, b in R if b)
print(f"判据 {npass}/{len(R)}")
for n, b in R:
    print(f"  {'✅' if b else '❌'} {n}")
print("=" * 78)

json.dump({
    "lesson": "★81 说话（真的学回来）", "pass": npass, "total": len(R),
    "real_targets_train": T_train, "real_targets_test": T_test,
    "default_params": DEFAULT_PARAMS, "learned_params": best_p,
    "dist_default": d_default, "dist_learned": best_d,
    "heldout_learned": dH_her, "heldout_default": dH_def,
    "fair_base": base_fair, "fair_N16": f16, "fair_N4": f4, "fair_N1": f1, "N_sweep_fair": resN, "N_sweep_sel": resN_sel, "blind_gap": gap,
}, open(os.path.join(os.path.dirname(__file__), "..", "data", "exp81_speech.json"),
        "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("已写入 data/exp81_speech.json")
