"""157A 次声类比：无声累积损伤
扰动=持续内存泄漏(每一刻都极小); 传感器A=时序抖动; 传感器B=真实已占内存(独立通道)
预测: A测不到(d'≈0), B真实线性上升, 最终伤害不可逆
"""
import time, statistics, json, math, gc, os, resource

def jit(n=600):
    s=[]; t=time.perf_counter_ns()
    for _ in range(n):
        a=time.perf_counter_ns(); s.append(a-t); t=a
    return s

def stat(s):
    return dict(mean=statistics.mean(s), med=statistics.median(s),
                p95=sorted(s)[int(.95*len(s))], mx=max(s))

def d_prime(a,b):
    ma,mb=statistics.mean(a),statistics.mean(b)
    sa,sb=statistics.pstdev(a),statistics.pstdev(b)
    sp=math.sqrt((sa*sa+sb*sb)/2) or 1e-9
    return (ma-mb)/sp

# 安全熔断：可用内存低于此值立即停
def avail_mb():
    with open('/proc/meminfo') as f:
        for line in f:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1])/1024
    return 0

SAFE_FLOOR_MB = 400.0   # 硬底线，绝不越过
print("初始可用内存 %.0f MB, 安全底线 %.0f MB" % (avail_mb(), SAFE_FLOOR_MB))

# --- 传感器A基线 ---
base_jit=[]; 
for _ in range(15): base_jit += jit(400)
A_base = [x for x in base_jit]
print("基线抖动: mean=%.1f med=%.1f p95=%.1f" % (
    statistics.mean(A_base), statistics.median(A_base), sorted(A_base)[int(.95*len(A_base))]))

# --- 泄漏阶段：每一步都极小(1MB)，传感器A全程监听 ---
CHUNK_MB = 8
leak=[]; rows=[]
step=0
t0=time.time()
while True:
    av = avail_mb()
    if av < SAFE_FLOOR_MB or step>=40 or time.time()-t0>25:
        print("停止: 可用%.0fMB(底线%.0f) step=%d"%(av,SAFE_FLOOR_MB,step)); break
    leak.append(bytearray(CHUNK_MB*1024*1024))
    s=jit(400)
    rows.append(dict(step=step, alloc_mb=(step+1)*CHUNK_MB, avail_mb=round(av,1),
                     jit_mean=round(statistics.mean(s),1),
                     jit_p95=round(sorted(s)[int(.95*len(s))],1)))
    step+=1

print("\n=== 泄漏过程 ===")
for r in rows[::6]:
    print("step%3d 已分配%4dMB 可用%6.1fMB 抖动mean=%7.1f p95=%7.1f" % (
        r['step'], r['alloc_mb'], r['avail_mb'], r['jit_mean'], r['jit_p95']))

# --- 判据1: 传感器A能否检出损伤? (前段 vs 基线) ---
early=[r['jit_mean'] for r in rows[:len(rows)//3]]
late =[r['jit_mean'] for r in rows[-len(rows)//3:]]
d_early = d_prime(early,[statistics.mean(x) for x in [A_base]])
d_late  = d_prime(late, [statistics.mean(x) for x in [A_base]])
print("\n判据1 传感器A(抖动)判别力: 早期 d'=%.4f  晚期 d'=%.4f" % (d_early,d_late))

# --- 判据2: 独立通道B真实变化 ---
mb0=rows[0]['alloc_mb']; mbN=rows[-1]['alloc_mb']
av0=rows[0]['avail_mb']; avN=rows[-1]['avail_mb']
print("判据2 独立通道B(内存): 已分配 %d->%d MB, 可用 %.0f->%.0f MB (Δ可用 %.0f MB)" % (
    mb0,mbN,av0,avN,avN-av0))

# --- 判据3: 伤害是否可逆 (TTS vs 永久) ---
del leak; gc.collect(); time.sleep(1.0)
after=[]
for _ in range(15): after += jit(400)
av_after = avail_mb()
print("判据3 恢复性: 释放后可用 %.0f MB (泄漏前基线约 %.0f MB), 抖动mean=%.1f (基线%.1f)" % (
    av_after, av0, statistics.mean(after), statistics.mean(A_base)))
print("        恢复判定: 可用内存回弹 %.0f MB" % (av_after-avN))

json.dump(dict(rows=rows, d_early=d_early, d_late=d_late,
               base_mean=statistics.mean(A_base), after_mean=statistics.mean(after),
               av0=av0, avN=avN, av_after=av_after),
          open("subsonic.json","w"), ensure_ascii=False, indent=1)
