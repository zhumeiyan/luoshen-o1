"""164 升维加器官：器官 = 感受器 + 它对应的身体。先造身体，再装器官。"""
import os, time, json, statistics, math, random

def rd(p):
    with open(p) as f: return f.read()

def o_cpu():
    s = rd('/proc/self/stat').split(); return int(s[13]) + int(s[14])
def o_sysc():
    v = {}
    for line in rd('/proc/self/io').splitlines():
        k, x = line.split(':'); v[k.strip()] = int(x)
    return v['syscr'] + v['syscw']
def o_load():  return float(rd('/proc/loadavg').split()[0]) * 1000
def o_mem():
    for line in rd('/proc/meminfo').splitlines():
        if line.startswith('MemAvailable'): return int(line.split()[1])
    return 0
def o_net():
    tot = 0
    for line in rd('/proc/net/dev').splitlines()[2:]:
        p = line.split(':', 1)[1].split(); tot += int(p[0]) + int(p[8])
    return tot
def o_ent():   return int(rd('/proc/sys/kernel/random/entropy_avail'))

ORGANS = {'cpu': o_cpu, 'sysc': o_sysc, 'load': o_load,
          'mem': o_mem, 'net': o_net, 'ent': o_ent}
NAMES = list(ORGANS)

# ---------- 身体：真实器官被感受的对象 ----------
_buf_holder = []
def body_cpu(n):
    x = 0
    for i in range(n): x = (x + i * i) % 1000003
    return x
def body_mem_alloc(kb):          # 真分配并触碰 -> 真改变 MemAvailable
    b = bytearray(kb * 1024)
    for i in range(0, len(b), 4096): b[i] = 1
    _buf_holder.append(b)
def body_mem_free():             # 真释放
    while _buf_holder: _buf_holder.pop()
def body_circ(bytes_n, pipes):   # 真管道 IO；分块，绝不阻塞管道缓冲
    CH = 16384
    per = max(CH, bytes_n // len(pipes))
    for r, w in pipes:
        left = per
        while left > 0:
            k = min(CH, left)
            os.write(w, b'x' * k); os.read(r, k); left -= k

# 准备真实管道（循环系统）
PIPES = []
for _ in range(4):
    r, w = os.pipe(); PIPES.append((r, w))

MEM_CAP_KB = 120 * 1024   # 安全上限，绝不越过
_allocated = [0]

def set_body(mode):
    """把身体摆到某个真实代谢状态"""
    if mode == 'low':
        body_cpu(5000); body_mem_free(); _allocated[0] = 0
    elif mode == 'high':
        body_cpu(60000)
        want = 120 * 1024
        if _allocated[0] < want and _allocated[0] + 20000 <= MEM_CAP_KB:
            body_mem_alloc(20000); _allocated[0] += 20000
        body_circ(131072, PIPES)

def readout():
    return {n: f() for n, f in ORGANS.items()}

def dprime(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    sa, sb = statistics.pstdev(a), statistics.pstdev(b)
    p = ((sa ** 2 + sb ** 2) / 2) ** 0.5
    return (mb - ma) / p if p > 0 else 0.0

RNG = random.Random(20261019)
res = {}

# ---------- S1 器官激活：身体动起来之后，谁活了 ----------
# 用梯度读出（相邻差），绝对值含共模漂移
seq, labels = [], []
for i in range(16):
    m = 'low' if i % 2 == 0 else 'high'
    set_body(m)
    seq.append(readout()); labels.append(m)

act = {}
for n in NAMES:
    d_lo = [seq[i + 2][n] - seq[i][n] for i in range(0, len(seq) - 2, 2)]
    d_hi = [seq[i + 2][n] - seq[i][n] for i in range(1, len(seq) - 2, 2)]
    act[n] = {'d': dprime(d_hi, d_lo),
              'spread': max(s[n] for s in seq) - min(s[n] for s in seq)}
res['S1_activation'] = act

# ---------- S2 正交性：器官之间是不是在说同一件事 ----------
live = [n for n in NAMES if abs(act[n]['d']) > 0.3 and act[n]['spread'] > 0]
cols = {n: [s[n] for s in seq] for n in live}
def corr(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0
ort = {}
for i in range(len(live)):
    for j in range(i + 1, len(live)):
        ort[f'{live[i]}~{live[j]}'] = corr(cols[live[i]], cols[live[j]])
res['S2_orthogonality'] = {'live_organs': live, 'pairwise_corr': ort}

# ---------- S3 维度灾难：加器官是否一直有收益 ----------
# 采独立样本，D 从 1 加到 len(live)，看 held-out 判别力
def collect(n_per):
    rows = {'low': [], 'high': []}
    for i in range(n_per * 2):
        m = 'low' if i % 2 == 0 else 'high'
        set_body(m); rows[m].append(readout())
    return rows

# 用最近质心 + 留出，特征为梯度形式
def eval_D(rows, feats, n_train):
    tr_lo = rows['low'][:n_train]; tr_hi = rows['high'][:n_train]
    te_lo = rows['low'][n_train:]; te_hi = rows['high'][n_train:]
    if not te_lo or not te_hi: return None
    cl = [statistics.mean(r[f] for r in tr_lo) for f in feats]
    ch = [statistics.mean(r[f] for r in tr_hi) for f in feats]
    sd = []
    for k, f in enumerate(feats):
        v = [r[f] for r in tr_lo] + [r[f] for r in tr_hi]
        sd.append(statistics.pstdev(v) or 1.0)
    def dcl(r):
        a = sum(((r[f] - cl[k]) / sd[k]) ** 2 for k, f in enumerate(feats))
        b = sum(((r[f] - ch[k]) / sd[k]) ** 2 for k, f in enumerate(feats))
        return 'low' if a < b else 'high'
    correct = sum(1 for r in te_lo if dcl(r) == 'low')
    correct += sum(1 for r in te_hi if dcl(r) == 'high')
    return correct / (len(te_lo) + len(te_hi))

N_PER = 10
rows = collect(N_PER)
curve = {}
if live:
    order = sorted(live, key=lambda n: -abs(act[n]['d']))   # 按单器官强度排序加入
    for D in range(1, len(order) + 1):
        curve[D] = {'feats': order[:D], 'acc': eval_D(rows, order[:D], N_PER // 2)}
res['S3_dimensionality'] = {'order': sorted(live, key=lambda n: -abs(act[n]['d'])) if live else [],
                            'curve': curve, 'n_per_class': N_PER}

# ---------- S4 破坏对照：弄瞎最强的那个器官，判别力该掉 ----------
blind = {}
if live:
    best = sorted(live, key=lambda n: -abs(act[n]['d']))[0]
    base = eval_D(rows, live, N_PER // 2)
    for rep in range(6):
        rows2 = {'low': [dict(r) for r in rows['low']], 'high': [dict(r) for r in rows['high']]}
        allv = [r[best] for r in rows2['low']] + [r[best] for r in rows2['high']]
        RNG.shuffle(allv)
        for i, r in enumerate(rows2['low']): r[best] = allv[i]
        for i, r in enumerate(rows2['high']): r[best] = allv[len(rows2['low']) + i]
        blind.setdefault('blinded', []).append(eval_D(rows2, live, N_PER // 2))
    blind['intact'] = base
    blind['organ'] = best
res['S4_blind'] = blind

body_mem_free()
print(json.dumps(res, indent=1, ensure_ascii=False))
