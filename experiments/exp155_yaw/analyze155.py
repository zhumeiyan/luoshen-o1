import json, numpy as np
r = json.load(open("result155.json"))
P = r["reps"]["0.004"]["P"]; P2 = P/2
rng = np.random.default_rng(155)

def slope_ci(curves, n_boot=4000):
    """对步数做线性回归，返回斜率与 bootstrap CI"""
    A = np.array(curves)                     # (R, L)
    L = A.shape[1]
    x = np.arange(1, L+1, dtype=float)
    xc = x - x.mean()
    def sl(M):
        y = M.mean(axis=0)
        return float((xc @ (y - y.mean())) / (xc @ xc))
    bs = []
    for _ in range(n_boot):
        idx = rng.integers(0, A.shape[0], A.shape[0])
        bs.append(sl(A[idx]))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return sl(A), float(lo), float(hi)

def mean_ci(v):
    v = np.asarray(v, float)
    bs = [rng.choice(v, len(v), replace=True).mean() for _ in range(4000)]
    return float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

print("周期 P = %.4f rad (%.1f°)，模糊半宽 = %.4f rad" % (P, np.degrees(P), P2))
print("\n%-8s %-28s %-28s" % ("sigma", "dead 斜率/步 (95%CI)", "comb 斜率/步 (95%CI)"))
out = {}
for s in ("0.004", "0.012", "0.036"):
    d = np.array(r["reps"][s]["dead_all"]); c = np.array(r["reps"][s]["comb_all"])
    sd = slope_ci(d); sc = slope_ci(c)
    print("%-8s %+.6f [%+.6f,%+.6f]  %+.6f [%+.6f,%+.6f]" % (s, sd[0],sd[1],sd[2], sc[0],sc[1],sc[2]))
    # 末点差 (comb - dead)，负值=磁场更优
    diff = c[:, -1] - d[:, -1]
    m, lo, hi = mean_ci(diff)
    # 解模糊失败率：误差超过半个周期即判错分支
    fail = float((c > P2).mean())
    dead_fail = float((d > P2).mean())
    out[s] = {"dead_slope": sd, "comb_slope": sc,
              "end_diff_mean": m, "end_diff_CI": [lo, hi],
              "comb_fail_rate": fail, "dead_exceed_halfP": dead_fail,
              "dead_end": float(d[:,-1].mean()), "comb_end": float(c[:,-1].mean())}
    print("         末点差 comb-dead = %+.4f CI[%+.4f,%+.4f]  解模糊失败率 %.3f  积分超半周期率 %.3f"
          % (m, lo, hi, fail, dead_fail))

json.dump(out, open("analysis155.json","w"), indent=2, ensure_ascii=False)

print("\n--- 逐检查点均值 ---")
for s in ("0.004","0.012","0.036"):
    sc = r["sigma_scan"][s]
    print("sigma=%s" % s)
    print("  步数  ", sc["checkpoints"])
    print("  dead  ", [round(x,4) for x in sc["dead"]])
    print("  comb  ", [round(x,4) for x in sc["comb"]])
