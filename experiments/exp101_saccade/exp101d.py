# -*- coding: utf-8 -*-
"""
101d · 把 101 的扫视序列接进本体引擎：是"看得多"还是"看不准"在塑造结构？

101b/c 证明了：识别靠的是跳对地方，不是看得多。
    GUIDED T=1  89 个特征 → acc 1.000
    FIXED  T=12 96 个特征 → acc 0.125（=随机）

那对**内在结构**呢？是"累积了多少感官"起作用，
还是"感官是否可预测"起作用？（091 曾发现：翻转率才是关键）

正交 2x2 —— 均值严格匹配，只变可预测性：
    A 量少·可预测   input≡0.3        → arrival 恒 0
    B 量少·不可预测 0.0/0.6 随机      → arrival 随机翻转
    C 量多·可预测   input≡0.7        → arrival 恒 1
    D 量多·不可预测 0.4/1.0 随机      → arrival 随机翻转
  均值：A=B=0.3，C=D=0.7（严格匹配）

另加生态效度组：直接把 101b 真实扫视序列（GUIDED/BLIND/FIXED）循环注入。

预注册：
  H1 可预测性主效应显著（不可预测 > 可预测）
  H2 量主效应不显著（均值匹配下）
"""
import os, sys, json
import numpy as np
sys.path.insert(0, '/data/workspace/luoshen-o1/core')
from life5 import Life5

OUT = os.path.dirname(os.path.abspath(__file__))
BASE = dict(N=8, ratio=0.6, k_seek=0.6, k_sal=0.6, sigma_in=0.15)
STEPS = 600
SEEDS = list(range(16))


def skew(lf):
    c = np.asarray(lf.capacity, float)
    if c.std() < 1e-12:
        return 0.0
    z = (c - c.mean()) / c.std()
    return float((z ** 3).mean())


def run(seq_fn, seed, mode='sense'):
    lf = Life5(seed=seed, **BASE) if mode == 'sense' else \
         Life5(seed=seed, **{**BASE, 'k_seek': 0.0, 'k_sal': 0.0})
    rng = np.random.default_rng(seed * 977 + 13)
    lf.rng = rng
    for t in range(STEPS):
        if mode == 'sense':
            v = seq_fn(t, rng)
            lf.input_val = float(v)
            lf.sal = np.full(lf.N, float(np.clip(v, 0, 1)))
        lf.step()
        if not lf.alive:
            break
    return lf


# ---- 四格序列（均值严格匹配）----
def mk_det(v):
    return lambda t, rng: v


def mk_stoch(lo, hi):
    def f(t, rng):
        return lo if rng.random() < 0.5 else hi
    return f


CELLS = {
    'A_少_可预测': mk_det(0.3),
    'B_少_不可预测': mk_stoch(0.0, 0.6),
    'C_多_可预测': mk_det(0.7),
    'D_多_不可预测': mk_stoch(0.4, 1.0),
}

# ---- 保活阳性对照 ----
print("=== 保活对照 ===")
for name, fn in CELLS.items():
    a = sum(1 for sd in SEEDS if run(fn, sd).alive)
    print(f"  {name:<14} 存活 {a}/16")
a = sum(1 for sd in SEEDS if run(mk_det(0.3), sd, 'none').alive)
print(f"  {'无感官':<14} 存活 {a}/16")

print("\n=== 2x2 主结果 ===")
SK = {}
res = {}
for name, fn in CELLS.items():
    sk = []
    al = 0
    for sd in SEEDS:
        lf = run(fn, sd)
        if lf.alive:
            al += 1
            sk.append(skew(lf))
    sk = np.array(sk)
    SK[name] = sk
    res[name] = dict(alive=al, skew_mean=float(sk.mean()) if len(sk) else None,
                     skew_sd=float(sk.std()) if len(sk) > 1 else 0.0, n=len(sk))
    print(f"  {name:<14} 存活={al:2d}/16 偏度={sk.mean():.6f}±{sk.std():.6f} (n={len(sk)})")


def paired(a, b, n_boot=4000):
    A, B = np.array(SK[a]), np.array(SK[b])
    n = min(len(A), len(B))
    if n == 0:
        return dict(n=0)
    D = B[:n] - A[:n]
    boot = np.array([np.random.default_rng(k).choice(D, n, replace=True).mean()
                     for k in range(n_boot)])
    return dict(n=int(n), diff=float(D.mean()),
                ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))])


print("\n=== 主效应（配对，共同存活子集）===")
eff = {}
eff['可预测性_在少(A->B)'] = paired('A_少_可预测', 'B_少_不可预测')
eff['可预测性_在多(C->D)'] = paired('C_多_可预测', 'D_多_不可预测')
eff['量_可预测下(A->C)'] = paired('A_少_可预测', 'C_多_可预测')
eff['量_不可预测下(B->D)'] = paired('B_少_不可预测', 'D_多_不可预测')
for k, v in eff.items():
    print(f"  {k:<20} diff={v['diff']:+.6f} CI=[{v['ci'][0]:+.6f},{v['ci'][1]:+.6f}] n={v['n']}")

# ---- 生态效度：真实扫视序列 ----
print("\n=== 生态效度：101b 真实扫视序列循环注入 ===")
import cv2
from exp101b import (base_texture, make_object, peripheral, salience,
                     fovea, N_OBJ, S, FOV)
orb = cv2.ORB_create(nfeatures=500)
if True:
    base = base_texture()
    objs = [make_object(base, i)[0] for i in range(N_OBJ)]

    def saccade_signal(obj, mode, seed):
        """返回每次扫视的局部信息量（0~1 归一）"""
        rng = np.random.default_rng(seed)
        per = peripheral(obj); sal = salience(per)
        inh = np.zeros((32, 32))
        cx, cy = S // 2, S // 2
        visited = []
        sig = []
        for t in range(6):
            if mode == 'GUIDED':
                s = sal - inh * (sal.max() + 1e-9)
                py, px = divmod(int(np.argmax(s)), 32)
                cx = int(np.clip(px / 32 * S, FOV // 2, S - FOV // 2))
                cy = int(np.clip(py / 32 * S, FOV // 2, S - FOV // 2))
            elif mode == 'BLIND':
                for _ in range(30):
                    nx = int(rng.integers(FOV // 2, S - FOV // 2))
                    ny = int(rng.integers(FOV // 2, S - FOV // 2))
                    if all(abs(nx - vx) > FOV // 2 or abs(ny - vy) > FOV // 2
                           for vx, vy in visited):
                        cx, cy = nx, ny
                        break
            visited.append((cx, cy))
            d = orb.detectAndCompute(fovea(obj, cx, cy), None)[1]
            sig.append(0 if d is None else min(1.0, len(d) / 120.0))
            py = int(np.clip(cy / S * 32, 0, 31)); px = int(np.clip(cx / S * 32, 0, 31))
            cv2.circle(inh, (px, py), 3, 1.0, -1)
        return sig

    eco = {}
    for mode in ['GUIDED', 'BLIND', 'FIXED']:
        seqs = [saccade_signal(objs[ti % N_OBJ], mode, 52000 + ti) for ti in range(8)]
        flat = [v for s in seqs for v in s]
        mean_v = float(np.mean(flat))

        def fn(t, rng, flat=flat):
            return flat[t % len(flat)]

        sk = []; al = 0
        for sd in SEEDS:
            lf = run(fn, sd)
            if lf.alive:
                al += 1; sk.append(skew(lf))
        sk = np.array(sk)
        eco[mode] = dict(mean_signal=mean_v, alive=al,
                         skew_mean=float(sk.mean()) if len(sk) else None,
                         skew_sd=float(sk.std()) if len(sk) > 1 else 0.0, n=len(sk),
                         seq_mean=mean_v)
        print(f"  {mode:<7} 平均信号={mean_v:.3f} 存活={al:2d}/16 "
              f"偏度={sk.mean():.6f}±{sk.std():.6f} (n={len(sk)})")
    res['eco'] = eco
    # 生态组配对（共同存活子集 + bootstrap）
    ECO_SK = {m: None for m in ['GUIDED', 'BLIND', 'FIXED']}
    for m in ['GUIDED', 'BLIND', 'FIXED']:
        seqs = [saccade_signal(objs[ti % N_OBJ], m, 52000 + ti) for ti in range(8)]
        flat = [v for s in seqs for v in s]
        sk = []
        for sd in SEEDS:
            lf = run(lambda t, r, f=flat: f[t % len(f)], sd)
            if lf.alive:
                sk.append(skew(lf))
        ECO_SK[m] = np.array(sk)

    def ecopair(a, b, n_boot=4000):
        A, B = ECO_SK[a], ECO_SK[b]
        n = min(len(A), len(B))
        if n == 0:
            return dict(n=0)
        D = B[:n] - A[:n]
        boot = np.array([np.random.default_rng(k).choice(D, n, replace=True).mean()
                         for k in range(n_boot)])
        return dict(n=int(n), diff=float(D.mean()),
                    ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))])

    res['eco_paired'] = {
        'FIXED->GUIDED': ecopair('FIXED', 'GUIDED'),
        'FIXED->BLIND': ecopair('FIXED', 'BLIND'),
        'BLIND->GUIDED': ecopair('BLIND', 'GUIDED'),
    }
    for k, v in res['eco_paired'].items():
        print(f"  配对 {k:<14} diff={v['diff']:+.6f} "
              f"CI=[{v['ci'][0]:+.6f},{v['ci'][1]:+.6f}] n={v['n']}")

res['effects'] = eff
res['_meta'] = dict(STEPS=STEPS, SEEDS=len(SEEDS), BASE={k: v for k, v in BASE.items()})
json.dump(res, open(os.path.join(OUT, 'result_101d.json'), 'w'), ensure_ascii=False, indent=1)
print("\nsaved result_101d.json")
