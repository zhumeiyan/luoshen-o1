import numpy as np, json, os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "/data/workspace/luoshen-o1/experiments/exp203_offline"
os.makedirs(OUT, exist_ok=True)


def clip_params(a1, a2, c):
    return (float(np.clip(a1, -0.85, 0.85)),
            float(np.clip(a2, -0.45, 0.45)),
            float(np.clip(c, -2.0, 2.0)))


def run(seed, rho, T_off, drift, sigma_d=1.0, T_on=10, n_cyc=60,
        lr=0.005, decay=0.03, recov=0.04, H=20, bufsize=300):
    """rho: 离线期用于做梦的比例；1-rho 用于休眠(恢复感知敏感性)"""
    rng = np.random.default_rng(seed)
    a1, a2, c = 0.55, -0.2, 0.3
    W = np.zeros(2); b = 0.0; s = 1.0
    buf = []; errs = []; perr = 0.0
    for cyc in range(n_cyc):
        # 世界漂移
        a1 += drift * rng.normal(); a2 += drift * rng.normal(); c += drift * rng.normal()
        a1, a2, c = clip_params(a1, a2, c)
        d = rng.normal(0, sigma_d)           # 本次被按时的局部偏差
        x = np.array([0.0, 0.0])
        # ---- 在线期：被按了 ----
        for t in range(T_on):
            xn = a1*x[-1] + a2*x[-2] + c + d + rng.normal(0, 0.2)
            obs = xn + rng.normal(0, 0.4/max(s, 1e-2))
            f = x[-2:].copy()
            p = float(W@f + b)
            W += lr*(obs-p)*f; b += lr*(obs-p)
            buf.append((f, obs))
            if len(buf) > bufsize: buf.pop(0)
            x = np.append(x[1:], xn)
            s *= math.exp(-decay)            # 感知敏感性衰减
        # ---- 离线期：没被按 ----
        B = int(round(rho*T_off)); S = T_off - B
        s = min(1.0, s + S*recov)            # 休眠：恢复敏感性
        for _ in range(B):                    # 做梦：重放旧样本
            if not buf: break
            i = int(rng.integers(0, len(buf)))
            f, tg = buf[i]
            p = float(W@f + b)
            W += lr*(tg-p)*f; b += lr*(tg-p)
        # ---- 评估：下次被按时，模型有多好 ----
        if cyc >= n_cyc//2:
            g = [0.0, 0.0]; ref = [0.0, 0.0]; ok = True
            for _ in range(H):
                gn = float(W@np.array(g[-2:]) + b)
                rn = a1*ref[-1] + a2*ref[-2] + c
                g.append(gn); ref.append(rn)
                if abs(gn) > 1e6: ok = False; break
            e = 100.0 if not ok else min(math.sqrt(np.mean((np.array(g)-np.array(ref))**2)), 100.0)
            errs.append(e)
        if cyc == n_cyc-1:
            perr = float(abs(W[0]-a1) + abs(W[1]-a2) + abs(b-c))
    return (float(np.mean(errs)) if errs else 100.0), perr


rhos = [0, 0.25, 0.5, 0.75, 1.0]
Toffs = [0, 5, 20, 60]
drifts = [0.0, 0.02]
seeds = [1, 2, 3]

res = {}
for dr in drifts:
    for Tf in Toffs:
        for r in rhos:
            es = []; ps = []
            for sd in seeds:
                e, p = run(sd, r, Tf, dr)
                es.append(e); ps.append(p)
            res[f"drift{dr}|T{Tf}|rho{r}"] = {
                "err_mean": float(np.mean(es)),
                "err_all": [round(float(x), 4) for x in es],
                "param_err": float(np.mean(ps)),
            }

json.dump(res, open(os.path.join(OUT, "result203.json"), "w"), ensure_ascii=False, indent=1)


def get(dr, Tf, r, key="err_mean"):
    return res[f"drift{dr}|T{Tf}|rho{r}"][key]


# 最优 rho*
best = {}
for dr in drifts:
    for Tf in Toffs:
        b = min(rhos, key=lambda r: get(dr, Tf, r))
        best[f"drift{dr}|T{Tf}"] = b
json.dump(best, open(os.path.join(OUT, "best203.json"), "w"), ensure_ascii=False, indent=1)

plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

ax = axes[0, 0]
for dr, mk, lb in [(0.0, 'o', '世界不变 drift=0'), (0.02, 's', '世界漂移 drift=0.02')]:
    ax.plot(Toffs, [get(dr, T, 0.5) for T in Toffs], marker=mk, label=lb)
ax.set_xlabel("被按的间隔 T_off（做梦占比 rho=0.5）")
ax.set_ylabel("预测误差")
ax.set_title("A. 按得太密会瞎，按得太疏会过时")
ax.legend(fontsize=8)

for idx, Tf in enumerate([20, 60]):
    ax = axes[0, 1] if idx == 0 else axes[1, 0]
    for dr, mk, lb in [(0.0, 'o', 'drift=0'), (0.02, 's', 'drift=0.02')]:
        ax.plot(rhos, [get(dr, Tf, r) for r in rhos], marker=mk, label=lb)
    b0 = best[f"drift0.0|T{Tf}"]; b2 = best[f"drift0.02|T{Tf}"]
    ax.set_xlabel("离线期用于做梦的比例 rho")
    ax.set_ylabel("预测误差")
    ax.set_title(f"{'B' if idx==0 else 'C'}. T_off={Tf}  最优做梦占比\n"
                 f"(不变世界 rho*={b0}, 漂移世界 rho*={b2})")
    ax.legend(fontsize=8)

ax = axes[1, 1]
w = 0.35
xs = np.arange(len(rhos))
for i, (dr, lb) in enumerate([(0.0, 'drift=0'), (0.02, 'drift=0.02')]):
    ax.bar(xs + i*w, [get(dr, 20, r, "param_err") for r in rhos], w, label=lb)
ax.set_xticks(xs + w/2); ax.set_xticklabels([str(r) for r in rhos])
ax.set_xlabel("做梦占比 rho")
ax.set_ylabel("模型与真实世界的参数距离（进化指标）")
ax.set_title("D. 进化：参数追上了多少（越低越好）")
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(OUT, "render203.png"), dpi=110)
print("OK", json.dumps(best, ensure_ascii=False))
