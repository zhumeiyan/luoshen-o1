import os, time, json, statistics

def rd(p):
    with open(p) as f: return f.read()

def organ_cpu():   # 本我代谢：我消耗的CPU时间
    s = rd('/proc/self/stat').split()
    return int(s[13]) + int(s[14])
def organ_sysc():  # 动作计数：系统调用次数
    v = {}
    for line in rd('/proc/self/io').splitlines():
        k, x = line.split(':'); v[k.strip()] = int(x)
    return v['syscr'] + v['syscw']
def organ_load():  # 环境拥挤度
    return float(rd('/proc/loadavg').split()[0]) * 1000
def organ_mem():   # 体液：可用内存
    for line in rd('/proc/meminfo').splitlines():
        if line.startswith('MemAvailable'): return int(line.split()[1])
    return 0
def organ_net():   # 循环系统：网络字节
    tot = 0
    for line in rd('/proc/net/dev').splitlines()[2:]:
        p = line.split(':',1)[1].split(); tot += int(p[0]) + int(p[8])
    return tot
def organ_ent():   # 熵感
    return int(rd('/proc/sys/kernel/random/entropy_avail'))

ORGANS = {'cpu':organ_cpu,'sysc':organ_sysc,'load':organ_load,
          'mem':organ_mem,'net':organ_net,'ent':organ_ent}

# --- 1. 读取开销 ---
cost = {}
for name, fn in ORGANS.items():
    t0 = time.perf_counter_ns()
    for _ in range(20): fn()
    cost[name] = (time.perf_counter_ns()-t0)/20/1000  # us

# --- 2. 活度：不做任何事，通道自己在动吗 ---
def load_work(n):
    x = 0
    for i in range(n): x = (x + i*i) % 1000003
    return x
activity = {}
for name, fn in ORGANS.items():
    samples = [fn() for _ in range(30)]
    activity[name] = {'distinct': len(set(samples)), 'spread': max(samples)-min(samples)}
    load_work(200000)

# --- 3. 响应性：我做重活 vs 轻活，通道变吗 ---
resp = {}
A = []
for i in range(12):
    load_work(20000)
    A.append({n: f() for n, f in ORGANS.items()})
B = []
for i in range(12):
    load_work(80000)
    B.append({n: f() for n, f in ORGANS.items()})
# 用差值（Δ）而非绝对值——梯度读出
for name in ORGANS:
    da = [A[i+1][name]-A[i][name] for i in range(len(A)-1)]
    db = [B[i+1][name]-B[i][name] for i in range(len(B)-1)]
    ma, mb = statistics.mean(da), statistics.mean(db)
    sa, sb = statistics.pstdev(da), statistics.pstdev(db)
    pooled = ((sa**2+sb**2)/2)**0.5
    resp[name] = {'mean_light':ma,'mean_heavy':mb,'d':(mb-ma)/pooled if pooled>0 else 0.0}

print(json.dumps({'cost_us':cost,'activity':activity,'response':resp}, indent=1, ensure_ascii=False))
