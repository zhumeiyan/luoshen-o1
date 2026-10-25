"""116b · 把公式的两种状态接进本体引擎：恒定 vs 交替，看结构是否改变"""
import sys, json
import numpy as np
from scipy import stats
sys.path.insert(0, "/data/workspace/luoshen-o1")
from core.life5 import Life5

STEPS, N, SEEDS = 400, 8, list(range(16))

def run(cond, seed, P=8):
    # k_sal 默认 0.0 → 外部输入被读但【完全不进动力学】，三组必然逐位相同。
    # 这是 113 已踩过的坑，本轮又踩一次；先验通路再下结论。
    l = Life5(N=N, seed=seed, ratio=0.6, k_sal=0.4)
    for t in range(STEPS):
        if not l.alive:
            break
        # 剂量扫描显示 pres 指数饱和：input_val>=0.5 即顶到 1.0。
        # 原设计 flip(0.5/0.9) vs hold(0.5) 全在饱和区 = 无效对比。
        # 挪到非饱和区 [0, 0.3]。
        if cond == "hold":
            l.input_val = 0.15
        elif cond == "flip":
            l.input_val = 0.0 if (t // P) % 2 == 0 else 0.3
        elif cond == "none":
            l.input_val = 0.0
        l.step()
    cap = np.asarray(l.capacity)
    return dict(alive=bool(l.alive), skew=float(stats.skew(cap)) if cap.std() > 0 else 0.0,
                cap_std=float(cap.std()))

def boot_ci(d, n=8000, seed=1):
    d = np.asarray(d, float)
    if len(d) == 0: return (float("nan"), float("nan"))
    rg = np.random.default_rng(seed)
    bs = np.array([rg.choice(d, len(d), replace=True).mean() for _ in range(n)])
    return (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))

res = {}
for cond in ["hold", "flip", "none"]:
    rs = [run(cond, s) for s in SEEDS]
    res[cond] = dict(n_alive=sum(r["alive"] for r in rs),
                     skew_mean=float(np.mean([r["skew"] for r in rs])),
                     per_seed=[r["skew"] for r in rs])

def paired(a, b):
    d = [x - y for x, y in zip(res[a]["per_seed"], res[b]["per_seed"])]
    lo, hi = boot_ci(d)
    return dict(delta=float(np.mean(d)), ci=[lo, hi],
                significant=bool(lo > 0 or hi < 0))

out = dict(conditions={k: dict(n_alive=v["n_alive"], skew_mean=v["skew_mean"])
                       for k, v in res.items()},
           flip_vs_hold=paired("flip", "hold"),
           hold_vs_none=paired("hold", "none"))
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open("res116b_engine.json", "w"), ensure_ascii=False, indent=1)
