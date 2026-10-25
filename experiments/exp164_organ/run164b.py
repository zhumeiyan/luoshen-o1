"""164 v2 稳态身体 + 随机切分。修 156 号顺序漂移复发。"""
import os, json, statistics, random

def rd(p):
    with open(p) as f: return f.read()
def o_cpu():
    s = rd('/proc/self/stat').split(); return int(s[13]) + int(s[14])
def o_sysc():
    v = {}
    for line in rd('/proc/self/io').splitlines():
        k, x = line.split(':'); v[k.strip()] = int(x)
    return v['syscr'] + v['syscw']
def o_load(): return float(rd('/proc/loadavg').split()[0]) * 1000
def o_mem():
    for line in rd('/proc/meminfo').splitlines():
        if line.startswith('MemAvailable'): return int(line.split()[1])
    return 0
def o_net():
    tot = 0
    for line in rd('/proc/net/dev').splitlines()[2:]:
        p = line.split(':', 1)[1].split(); tot += int(p[0]) + int(p[8])
    return tot
def o_ent(): return int(rd('/proc/sys/kernel/random/entropy_avail'))

ORGANS = {'cpu': o_cpu, 'sysc': o_sysc, 'load': o_load,
          'mem': o_mem, 'net': o_net, 'ent': o_ent}
NAMES = list(ORGANS)
RNG = random.Random(1642)

_buf = []
_alloc = [0]
PIPES = []
for _ in range(4):
    r, w = os.pipe(); PIPES.append((r, w))
TARGET_KB = 60 * 1024      # 稳态目标：high 状态恒定持有 60MB

def body_cpu(n):
    x = 0
    for i in range(n): x = (x + i * i) % 1000003
    return x
def grow(kb):
    b = bytearray(kb * 1024)
    for i in range(0, len(b), 4096): b[i] = 1
    _buf.append(b); _alloc[0] += kb
def shrink():
    while _buf: _buf.pop()
    _alloc[0] = 0
def circ(total):
    CH = 16384
    per = max(CH, total // len(PIPES))
    for r, w in PIPES:
        left = per
        while left > 0:
            k = min(CH, left); os.write(w, b'x' * k); os.read(r, k); left -= k

def set_body(mode):
    """稳态：low 恒 0MB / 轻算；high 恒 60MB / 重算 / 大量循环 IO"""
    if mode == 'low':
        if _alloc[0] > 0: shrink()
        body_cpu(20000); circ(32768)
    else:
        if _alloc[0] < TARGET_KB: grow(TARGET_KB - _alloc[0])
        body_cpu(700000); circ(262144)

def dprime(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    sa, sb = statistics.pstdev(a), statistics.pstdev(b)
    p = ((sa ** 2 + sb ** 2) / 2) ** 0.5
    return (mb - ma) / p if p > 0 else 0.0

# ---- 采集：随机顺序，每类 N 个 ----
N = 10
plan = ['low', 'high'] * N
RNG.shuffle(plan)
rows = {'low': [], 'high': []}
for i, m in enumerate(plan):
    set_body(m)
    rows[m].append({'i': i, **{n: f() for n, f in ORGANS.items()}})
print('collected', {k: len(v) for k, v in rows.items()}, flush=True)

# ---- 单器官判别力（绝对值，随机切分） ----
def eval_feats(feats, reps=8):
    accs = []
    for rep in range(reps):
        idx_lo = list(range(len(rows['low']))); RNG.shuffle(idx_lo)
        idx_hi = list(range(len(rows['high']))); RNG.shuffle(idx_hi)
        nt = len(rows['low']) // 2
        tr_lo = [rows['low'][i] for i in idx_lo[:nt]]
        tr_hi = [rows['high'][i] for i in idx_hi[:nt]]
        te_lo = [rows['low'][i] for i in idx_lo[nt:]]
        te_hi = [rows['high'][i] for i in idx_hi[nt:]]
        cl = [statistics.mean(r[f] for r in tr_lo) for f in feats]
        ch = [statistics.mean(r[f] for r in tr_hi) for f in feats]
        sd = []
        for f in feats:
            v = [r[f] for r in tr_lo] + [r[f] for r in tr_hi]
            sd.append(statistics.pstdev(v) or 1.0)
        def dcl(r):
            a = sum(((r[f] - cl[k]) / sd[k]) ** 2 for k, f in enumerate(feats))
            b = sum(((r[f] - ch[k]) / sd[k]) ** 2 for k, f in enumerate(feats))
            return 'low' if a < b else 'high'
        c = sum(1 for r in te_lo if dcl(r) == 'low') + sum(1 for r in te_hi if dcl(r) == 'high')
        accs.append(c / (len(te_lo) + len(te_hi)))
    return statistics.mean(accs)

solo = {}
for n in NAMES:
    lo = [r[n] for r in rows['low']]; hi = [r[n] for r in rows['high']]
    solo[n] = {'d': dprime(hi, lo),
               'acc': eval_feats([n]),
               'spread': max(lo + hi) - min(lo + hi)}
print('solo done', flush=True)

live = [n for n in NAMES if solo[n]['acc'] > 0.6]
# ---- 正交性 ----
ort = {}
def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** .5; db = sum((y - mb) ** 2 for y in b) ** .5
    return num / (da * db) if da > 0 and db > 0 else 0.0
for i in range(len(live)):
    for j in range(i + 1, len(live)):
        ort[f'{live[i]}~{live[j]}'] = corr([r[live[i]] for r in rows['low']] + [r[live[i]] for r in rows['high']],
                                            [r[live[j]] for r in rows['low']] + [r[live[j]] for r in rows['high']])
# ---- 维度灾难扫描 ----
order = sorted(live, key=lambda n: -solo[n]['acc'])
curve = {D: {'feats': order[:D], 'acc': eval_feats(order[:D])} for D in range(1, len(order) + 1)}
# ---- 破坏对照 ----
blind = {}
if live:
    best = order[0]
    blind['organ'] = best; blind['intact'] = eval_feats(live)
    accs = []
    for rep in range(8):
        vals = [r[best] for r in rows['low']] + [r[best] for r in rows['high']]
        RNG.shuffle(vals)
        k = 0
        for r in rows['low']: r[best] = vals[k]; k += 1
        for r in rows['high']: r[best] = vals[k]; k += 1
        accs.append(eval_feats(live))
    blind['blinded'] = statistics.mean(accs)
shrink()
print(json.dumps({'solo': solo, 'live': live, 'orthogonality': ort,
                  'dim_curve': curve, 'blind': blind}, indent=1, ensure_ascii=False))
