# -*- coding: utf-8 -*-
"""
120b · 繁衍 / 多样性 接本体引擎
------------------------------------------------------------
必须先做阳性对照: k_sal=0 时 input_val 被读但不进 want,
四组会逐位相同(113b 踩过 #443)。本轮先把通路打开再取样。
分离两个变量: "是否在繁衍" vs "后代是否彼此不同"(克隆 vs 真变异)。
"""
import os, sys, json, time, random
import numpy as np

sys.path.insert(0, "/data/workspace/luoshen-o1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.life5 import Life5
from v2 import Individual, Environment, ReproductionSystemV2, _h
from run_exp2 import evolve, stats, MULTI, SINGLE

OUT = os.path.dirname(os.path.abspath(__file__))
K_SAL = 0.60
R = {}


def run_stream(seq, seeds=16, steps=240, ratio=0.60, k_sal=K_SAL):
    ys, alive = [], 0
    for sd in range(seeds):
        L = Life5(N=8, seed=sd, ratio=ratio, k_sal=k_sal)
        L.sal = np.ones(8) * 0.1
        for t in range(steps):
            L.input_val = float(seq[t % len(seq)])
            L.step()
            if not L.alive:
                break
        if L.alive:
            alive += 1
            ys.append(float(np.std(L.y)))
    return dict(alive=alive, n=seeds,
                skew=float(np.mean(ys)) if ys else None,
                sd=float(np.std(ys)) if len(ys) > 1 else None)


print("=" * 62)
print("STEP 1 · 阳性对照：input_val 真的进动力学吗")
print("=" * 62)
pos = {}
for tag, val in [("zero", 0.0), ("lo", 0.1), ("hi", 0.9)]:
    pos[tag] = run_stream(np.array([val]))
    print(f"  {tag:5s} alive={pos[tag]['alive']}/16 skew={pos[tag]['skew']}")
# 判据: 相对差异 > 1% 才算通路有效。绝对差 1e-5 级属"名义通过、实质不敏感"
# (116 踩过: delta=-9.8e-09 却 CI 不跨 0 的伪显著)
d_abs = abs(pos["hi"]["skew"] - pos["zero"]["skew"])
d_rel = d_abs / abs(pos["zero"]["skew"]) if pos["zero"]["skew"] else 0.0
sens = bool(d_rel > 0.01)
R["pos_zero"] = pos["zero"]["skew"]; R["pos_hi"] = pos["hi"]["skew"]
R["pos_abs_diff"] = float(d_abs); R["pos_rel_diff"] = round(float(d_rel), 6)
R["pos_sensitive"] = sens
print(f"  绝对差={d_abs:.3e}  相对差={d_rel*100:.4f}%  → 通路有效(>1%) = {sens}")

print()
print("=" * 62)
print("STEP 2 · 三组真实序列（同种子，只换繁衍方式）")
print("=" * 62)


def seq_from(centers, mu, K=20, gens=25, seed=7, key="simpson_niche"):
    pop, env, traj, sys_ = evolve(centers, K=K, mu=mu, gens=gens, seed=seed)
    # 需要逐代序列, 重新跑一遍拿全轨迹
    import random
    rng = random.Random(seed)
    adam = Individual("ADAM", [0.5, 0.5, 0.5], [_h("genesis")], 100.0)
    env = Environment(centers, rng=rng)
    sy = ReproductionSystemV2(env, rng, mu=mu)
    p = [adam]
    out = []
    for g in range(gens):
        p = sy.step(p, carrying_capacity=K)
        s = stats(p, env)
        out.append(s[key] if key != "spread" else min(s["spread"], 1.0))
    return np.asarray(out, float), sy


groups = {}
# G1 无繁衍：单个体, 序列=自身适应度(恒定的世界读数)
e_single = Environment(MULTI, rng=random.Random(7))
ind = Individual("SOLO", [0.5, 0.5, 0.5], [_h("g")], 100.0)
groups["G1_no_repro"] = np.asarray([e_single.evaluate(ind)] * 25, float)

# G2 繁衍但克隆(mu=0)
s2, sy2 = seq_from(MULTI, 0.0)
groups["G2_repro_clone"] = s2

# G3 繁衍 + 真变异(mu=0.1)
s3, sy3 = seq_from(MULTI, 0.1)
groups["G3_repro_varied"] = s3

# G4 单峰世界 + 真变异(世界没有多样性可给)
s4, sy4 = seq_from(SINGLE, 0.1)
groups["G4_singlepeak_varied"] = s4

for k, v in groups.items():
    print(f"  {k:22s} len={len(v)} mean={v.mean():.4f} sd={v.std():.4f} uniq={len(set(np.round(v,4)))}")
    R[f"seq_{k}"] = [round(float(x), 4) for x in v]

print()
print("=" * 62)
print("STEP 3 · 接引擎")
print("=" * 62)
eng = {}
for k, v in groups.items():
    eng[k] = run_stream(v)
    sk = eng[k]["skew"]
    print(f"  {k:22s} alive={eng[k]['alive']:2d}/16  skew={sk if sk is None else round(sk,6)}")
    R[f"eng_{k}"] = dict(alive=eng[k]["alive"], skew=eng[k]["skew"])

print()
print("=" * 62)
print("STEP 4 · 配对比较（同种子）")
print("=" * 62)
def paired(a, b, seeds=16, steps=240):
    da = []
    for sd in range(seeds):
        o = []
        for seq in (a, b):
            L = Life5(N=8, seed=sd, ratio=0.60, k_sal=K_SAL)
            L.sal = np.ones(8) * 0.1
            for t in range(steps):
                L.input_val = float(seq[t % len(seq)])
                L.step()
                if not L.alive:
                    break
            o.append(float(np.std(L.y)) if L.alive else None)
        if o[0] is not None and o[1] is not None:
            da.append(o[1] - o[0])
    if len(da) < 3:
        return dict(n=len(da), mean=None, ci=None, note="样本不足/死亡筛选")
    m = float(np.mean(da))
    se = float(np.std(da, ddof=1) / np.sqrt(len(da)))
    return dict(n=len(da), mean=round(m, 6), ci=[round(m - 1.96 * se, 6), round(m + 1.96 * se, 6)])

pairs = [
    ("clone - no_repro", "G1_no_repro", "G2_repro_clone"),
    ("varied - clone", "G2_repro_clone", "G3_repro_varied"),
    ("singlepeak - varied", "G3_repro_varied", "G4_singlepeak_varied"),
]
for label, a, b in pairs:
    pr = paired(groups[a], groups[b])
    R[f"pair_{label}"] = pr
    print(f"  {label:24s} n={pr['n']} Δ={pr['mean']} CI={pr['ci']}")

with open(os.path.join(OUT, "result120b.json"), "w") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
print("\n[saved] result120b.json")
