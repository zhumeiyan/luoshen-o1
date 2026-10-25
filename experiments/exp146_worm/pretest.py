# -*- coding: utf-8 -*-
"""前置检验：real 地形上 path_feat 是否真能预测 content_feat？
若不能，整个"选点有价值"的实验前提就不成立。"""
import os, sys, math, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from worm import discover_nodes, path_feat, content_feat, BASE, PF, CF

nodes = discover_nodes(os.path.join(BASE, "experiments"), max_nodes=60)
X, Y = [], []
for p in nodes:
    c = content_feat(p)
    if c is None: continue
    X.append(path_feat(p)); Y.append(c)
X = np.array(X); Y = np.array(Y)
n = len(X)
print(f"nodes={n} X={X.shape} Y={Y.shape}")
print("X col std:", np.round(X.std(0), 4))
print("Y col std:", np.round(Y.std(0), 4))

# 标准化
Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
Ys = (Y - Y.mean(0)) / (Y.std(0) + 1e-9)

def ridge_loo(Xs, Ys, lam=1.0):
    n = len(Xs); errs = []
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        Xt = Xs[idx]; Yt = Ys[idx]
        A = Xt.T @ Xt + lam*np.eye(Xt.shape[1])
        W = np.linalg.solve(A, Xt.T @ Yt)
        pred = Xs[i] @ W
        errs.append(np.linalg.norm(pred - Ys[i]))
    return float(np.mean(errs))

def mean_loo(Ys):
    n = len(Ys); errs = []
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        m = Ys[idx].mean(0)
        errs.append(np.linalg.norm(m - Ys[i]))
    return float(np.mean(errs))

for terrain_name, Yt in [("real", Ys),
                          ("noise", np.random.RandomState(7).randn(*Ys.shape))]:
    r = ridge_loo(Xs, Yt, lam=1.0)
    m = mean_loo(Yt)
    print(f"[{terrain_name:6s}] ridge_LOO={r:.4f}  mean_LOO={m:.4f}  "
          f"learnable={'YES' if r < m*0.95 else 'NO'}")
