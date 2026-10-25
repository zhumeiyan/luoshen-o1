"""116c · 剂量扫描：证明 capacity 偏度这条指标对外部输入到底敏不敏感"""
import sys, json
import numpy as np
from scipy import stats
sys.path.insert(0, "/data/workspace/luoshen-o1")
from core.life5 import Life5

STEPS, N, SEEDS = 400, 8, list(range(8))

def run(v, seed):
    l = Life5(N=N, seed=seed, ratio=0.6, k_sal=0.4)
    for t in range(STEPS):
        if not l.alive: break
        l.input_val = v
        l.step()
    cap = np.asarray(l.capacity); sp = np.asarray(l.sp)
    return (float(stats.skew(cap)) if cap.std() > 0 else 0.0,
            float(cap.std()), float(sp.std()), bool(l.alive))

scan = {}
for v in [0.0, 0.5, 1.0, 2.0, 4.0]:
    rs = [run(v, s) for s in SEEDS]
    scan[str(v)] = dict(skew=float(np.mean([r[0] for r in rs])),
                        cap_std=float(np.mean([r[1] for r in rs])),
                        sp_std=float(np.mean([r[2] for r in rs])),
                        n_alive=sum(r[3] for r in rs))
sk = [scan[k]["skew"] for k in scan]
sp = [scan[k]["sp_std"] for k in scan]
cs = [scan[k]["cap_std"] for k in scan]
out = dict(scan=scan,
           skew_range=float(max(sk) - min(sk)),
           sp_std_range=float(max(sp) - min(sp)),
           cap_std_range=float(max(cs) - min(cs)))
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open("res116c_dose.json", "w"), ensure_ascii=False, indent=1)
