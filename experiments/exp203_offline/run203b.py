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


def run2(seed, B, drift, sigma_d=1.0, T_on=10, n_cyc=60, S=20,
         lr=0.005, decay=0.03, recov=0.04, H=20, bufsize=300, delta=0.0):
    """休眠时长 S 固定且充足(保证敏感性满恢复)，做梦步数 B 额外叠加。
       这样把'梦的收益'和'梦抢走休眠的代价'分离开。"""
    rng = np.random.default_rng(seed)
    a1, a2, c = 0.55, -0.2, 0.3
    W = np.zeros(2); b = 0.0; s = 1.0
    buf = []; errs = []; perr = 0.0
    for cyc in range(n_cyc):
        a1 += drift * rng.normal(); a2 += drift * rng.normal(); c += drift * rng.normal()
        a1, a2, c = clip_params(a1, a2, c)
        d = rng.normal(0, sigma_d)
        x = np.array([0.0, 0.0])
        for t in range(T_on):
            xn = a1*x[-1] + a2*x[-2] + c + d + rng.normal(0, 0.2)
            obs = xn + rng.normal(0, 0.4/max(s, 1e-2))
            f = x[-2:].copy()
            p = float(W@f + b)
            W += lr*(obs-p)*f; b += lr*(obs-p)
            buf.append((f, obs))
            if len(buf) > bufsize: buf.pop(0)
            x = np.append(x[1:], xn)
            s *= math.exp(-decay)
        # 休眠：固定充足
        s = min(1.0, s + S*recov)
        # 做梦：额外步数，不抢休眠
        for _ in range(B):
            if not buf: break
            i = int(rng.integers(0, len(buf)))
            f, tg = buf[i]
            tg2 = tg + delta * rng.normal(0, 1.0)   # 梦的荒诞度
            p = float(W@f + b)
            W += lr*(tg2-p)*f; b += lr*(tg2-p)
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


Bs = [0, 5, 20, 80, 300]
drifts = [0.0, 0.02, 0.10]
seeds = [1, 2, 3, 4, 5]

res = {}
for dr in drifts:
    for B in Bs:
        es = []; ps = []
        for sd in seeds:
            e, p = run2(sd, B, dr)
            es.append(e); ps.append(p)
        res[f"drift{dr}|B{B}"] = {
            "err_mean": float(np.mean(es)),
            "err_all": [round(float(x), 4) for x in es],
            "param_err": float(np.mean(ps)),
        }

json.dump(res, open(os.path.join(OUT, "result203b.json"), "w"), ensure_ascii=False, indent=1)

print("=== 做梦步数 B 的纯粹收益（休眠已固定充足）===")
for dr in drifts:
    row = [(B, round(res[f"drift{dr}|B{B}"]["err_mean"], 4)) for B in Bs]
    best = min(Bs, key=lambda B: res[f"drift{dr}|B{B}"]["err_mean"])
    print(f"drift={dr}: {row}  最优B={best}")

plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

ax = axes[0]
for dr, mk in zip(drifts, ['o', 's', '^']):
    ax.plot(Bs, [res[f"drift{dr}|B{B}"]["err_mean"] for B in Bs], marker=mk,
            label=f"世界漂移速度 drift={dr}")
ax.set_xlabel("离线期做梦步数 B（休眠时间已固定充足，不冲突）")
ax.set_ylabel("预测误差（越低越好）")
ax.set_title("A. 梦本身有没有用？——取决于世界变不变")
ax.legend(fontsize=8)

ax = axes[1]
for dr, mk in zip(drifts, ['o', 's', '^']):
    ax.plot(Bs, [res[f"drift{dr}|B{B}"]["param_err"] for B in Bs], marker=mk,
            label=f"drift={dr}")
ax.set_xlabel("做梦步数 B")
ax.set_ylabel("模型与真实世界的参数距离（进化指标，越低越好）")
ax.set_title("B. 进化：做多少梦才追得上世界")
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(OUT, "render203b.png"), dpi=110)
print("OK")
