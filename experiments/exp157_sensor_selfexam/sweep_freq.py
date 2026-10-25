"""157A 扫频听力图：等能量扰动下，短窗口传感器的判别力 vs 频率"""
import time, statistics, json, math

def load(k):
    x=0
    for i in range(k): x+=i*i
    return x

def observe(W, dt):
    """传感器：在时长W内以间隔dt稀疏采样抖动(点采样，非连续)"""
    s=[]; t=time.perf_counter_ns(); end=t+W*1e9
    while True:
        now=time.perf_counter_ns()
        if now>=end: break
        s.append(now-t); t=now
        # 稀疏：睡到下一个采样点
        nxt=t+dt*1e9
        while time.perf_counter_ns()<nxt: pass
    return s

def trial(T, W, dt, k, npulse, tag):
    """施加npulse个周期T的脉冲；返回(传感器读数, 真实脉冲数, 总墙钟ns)"""
    hits=0; t0=time.perf_counter_ns()
    # 扰动阶段
    for i in range(npulse):
        load(k); hits+=1
        if T>0:
            nxt=time.perf_counter_ns()+T*1e9
            while time.perf_counter_ns()<nxt: pass
    t1=time.perf_counter_ns()
    s=observe(W, dt)          # 观测窗口在扰动之后
    return (max(s) if s else 0.0), hits, (t1-t0)

def d_prime(a, b):
    """判别力：a=有扰动读数, b=无扰动读数"""
    ma, mb = statistics.mean(a), statistics.mean(b)
    sa, sb = statistics.pstdev(a), statistics.pstdev(b)
    sp = math.sqrt((sa*sa+sb*sb)/2) if (sa+sb)>0 else 1e-9
    return (ma-mb)/sp if sp>0 else 0.0

R=12; W=0.15; dt=0.0005; K=3000
# 等能量：总脉冲数*强度恒定 -> 固定总脉冲数, 变周期
NPULSE=6
print("=== 157A 扫频 (观测窗口W=%.2fs 采样间隔dt=%.4fs 脉冲数=%d 强度k=%d) ==="%(W,dt,NPULSE,K))
rows=[]
for T in (0.0, 0.005, 0.05, 0.2, 0.8):
    sig=[]; base=[]; wall=[]
    for r in range(R):
        m,h,w = trial(T, W, dt, K, NPULSE, "sig"); sig.append(m); wall.append(w)
        m0,h0,w0 = trial(T, W, dt, 0,  0,     "base"); base.append(m0)
    d = d_prime(sig, base)
    wm = statistics.mean(wall); w0m = statistics.mean([0]*1)
    rows.append(dict(T=T, d_prime=round(d,4),
                     sig_med=round(statistics.median(sig),1),
                     base_med=round(statistics.median(base),1),
                     wall_s=round(wm/1e9,4)))
    print("T=%-6s d'=%8.4f  sig中位=%9.1f  base中位=%9.1f  扰动墙钟=%.4fs" % (
        T, d, statistics.median(sig), statistics.median(base), wm/1e9))
json.dump(rows, open("freq_rows.json","w"), ensure_ascii=False, indent=1)
