"""119-D 应激实验（重做 118 欠账）
Homeostasis(反应性) vs Allostasis(预测性) vs None(无调节)
配对设计：三种策略吃同一条预录真实序列，仅策略不同。
内环境只收"有量程且可逆"的通道：排除 nrunning(量程0) 与 uptime/clock(钟表,不可逆)。
"""
import json, math, statistics

rec = json.load(open('trace_real.json'))
VARS = ['load1', 'memavail', 'memfree', 'rtt']   # 有量程且非钟表
CUT_RATIO = 0.5
N = len(rec)

def norm_scale():
    """每通道按自身量程归一化，否则 rtt(29ms) 与 memavail(2e6) 量级差 1e5 倍。"""
    base = {}
    for k in VARS:
        v = [r[k] for r in rec if r[k] is not None]
        mu = statistics.fmean(v)
        sd = statistics.pstdev(v) or 1e-12
        base[k] = (mu, sd)
    return base

SCALE = norm_scale()

def z(k, val):
    mu, sd = SCALE[k]
    return (val - mu) / sd if val is not None else None

def run(strategy, cut=None, gain=0.6, seed=0):
    cut = int(N * CUT_RATIO) if cut is None else cut
    base = {k: statistics.fmean([r[k] for r in rec[:8] if r[k] is not None]) for k in VARS}
    x = {k: (rec[0][k] if rec[0][k] is not None else base[k]) for k in VARS}
    hist = {k: [] for k in VARS}
    dev_pre, dev_post = [], []
    for t in range(N):
        supplied = (t < cut)
        for k in VARS:
            obs = rec[t][k] if supplied else None
            if obs is not None:
                x[k] = obs                      # 真实读数覆盖
                hist[k].append((t, obs))
            # ---- 调节 ----
            if strategy == 'none':
                pass
            elif strategy == 'reactive':
                if obs is not None:             # 断供后无读数 -> 无补给
                    x[k] += gain * (base[k] - x[k])
            elif strategy == 'predictive':
                if obs is not None:
                    x[k] += gain * (base[k] - x[k])
                else:
                    # 只用【断供前】的历史做线性外推，禁止偷看断供后真值
                    pre = [(tt, vv) for tt, vv in hist[k] if tt < cut]
                    if len(pre) >= 2:
                        n = len(pre)
                        sx = sum(p[0] for p in pre); sy = sum(p[1] for p in pre)
                        sxx = sum(p[0]**2 for p in pre); sxy = sum(p[0]*p[1] for p in pre)
                        den = n*sxx - sx*sx
                        slope = (n*sxy - sx*sy)/den if den else 0.0
                        intercept = (sy - slope*sx)/n
                        pred = slope*t + intercept
                        x[k] += gain * (pred - x[k])
        d = math.sqrt(sum(((x[k]-base[k])/(SCALE[k][1] or 1e-12))**2 for k in VARS))
        (dev_pre if t < cut else dev_post).append(d)
    return {
        'strategy': strategy, 'cut': cut,
        'dev_pre': statistics.fmean(dev_pre) if dev_pre else None,
        'dev_post': statistics.fmean(dev_post) if dev_post else None,
        'dev_end': dev_post[-1] if dev_post else None,
        'alive': all(not math.isnan(x[k]) and abs(x[k]) < 1e18 for k in VARS),
    }

if __name__ == '__main__':
    print('=== 119-D 应激实验（重做 118）===')
    print(f'预录 {N} 拍真实本体觉，断供点 t={int(N*CUT_RATIO)}')
    print('内环境变量（已排除 nrunning 量程0 / uptime+clock 钟表）:', VARS)
    print()
    print(f'{"策略":<12s}{"断供前偏离":>12s}{"断供后偏离":>12s}{"末态偏离":>12s}{"存活":>8s}')
    res = {}
    for s in ['none', 'reactive', 'predictive']:
        r = run(s); res[s] = r
        print(f'{s:<12s}{r["dev_pre"]:>12.4f}{r["dev_post"]:>12.4f}'
              f'{r["dev_end"]:>12.4f}{"YES" if r["alive"] else "NO":>8s}')
    json.dump(res, open('stress_result.json','w'), indent=1)
