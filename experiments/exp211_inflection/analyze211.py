# -*- coding: utf-8 -*-
import json, math, collections
import numpy as np

d = json.load(open("result211b.json"))
R = d["results"]; BETAS = d["BETAS"]; SEEDS = d["SEEDS"]

by = collections.defaultdict(dict)
for r in R:
    by[r["beta"]][r["seed"]] = r

print(f"{'beta':>6} {'Hfin':>7} {'±sd':>6} {'Hlast5':>7} {'崩塌':>6} {'层数':>5} {'acc':>7}")
print("-"*52)
rows = []
for b in BETAS:
    rs = [by[b][s] for s in SEEDS]
    Hf  = np.array([r["entropy_final"] for r in rs])
    Hl  = np.array([r["entropy_last5"] for r in rs])
    acc = np.array([r["acc"] for r in rs])
    L   = np.array([r["n_layers"] for r in rs])
    collapse = int((Hf < 0.5).sum())
    rows.append(dict(beta=b, Hfin=float(Hf.mean()), Hsd=float(Hf.std(ddof=1)),
                     Hlast5=float(Hl.mean()), collapse=collapse,
                     layers=float(L.mean()), acc=float(acc.mean()),
                     Hfin_list=[float(x) for x in Hf], acc_list=[float(x) for x in acc]))
    print(f"{b:>6} {Hf.mean():>7.3f} {Hf.std(ddof=1):>6.3f} {Hl.mean():>7.3f} "
          f"{collapse:>4}/8 {L.mean():>5.2f} {acc.mean():>7.4f}")

# 配对检验: beta=0 vs 各 beta, Hfinal 与 acc
def sign_test(a, bvec):
    diffs = np.array(bvec) - np.array(a)
    pos = int((diffs > 0).sum()); neg = int((diffs < 0).sum())
    n = pos + neg
    if n == 0: return pos, neg, 1.0
    # 双侧二项精确
    p = sum(math.comb(n, i) for i in range(0, min(pos, neg)+1)) / (2**n) * 2
    return pos, neg, min(1.0, p)

base_H  = by[0.0][SEEDS[0]]["entropy_final"]
H0 = [by[0.0][s]["entropy_final"] for s in SEEDS]
A0 = [by[0.0][s]["acc"] for s in SEEDS]
print("\n配对符号检验 (vs beta=0), 8 seeds:")
print(f"{'beta':>6} {'H: +/−':>9} {'p':>7} | {'acc: +/−':>9} {'p':>7}")
for b in BETAS[1:]:
    Hb = [by[b][s]["entropy_final"] for s in SEEDS]
    Ab = [by[b][s]["acc"] for s in SEEDS]
    ph, nh, pv_h = sign_test(H0, Hb)
    pa, na, pv_a = sign_test(A0, Ab)
    print(f"{b:>6} {ph:>4}/{nh:<4} {pv_h:>7.4f} | {pa:>4}/{na:<4} {pv_a:>7.4f}")

# 崩塌率
print("\n崩塌 (Hfinal<0.5) 计数:")
for b in BETAS:
    c = sum(1 for s in SEEDS if by[b][s]["entropy_final"] < 0.5)
    print(f"  beta={b:<5} {c}/8")

json.dump(rows, open("agg211.json","w"), ensure_ascii=False, indent=1)
print("\nsaved agg211.json")
