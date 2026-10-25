"""S1 习惯化豁免：疼必须豁免习惯化，代价是慢性误报。
两臂共用同一次真实采样（dwait_ms），只读出方式不同：
  habit 臂：阈值指数追踪近期读数（会习惯化）
  pain  臂：阈值固定（豁免习惯化）
两条件：
  A 有害持续（cpu 3, dwait~12ms）
  B 无害持续（cpu 1, dwait~0.05ms）
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import work, spawn_cpu_busy, killall

N = 24
ALPHA = 0.25      # 阈值追踪速率
MARGIN = 1.5      # 阈值余量(ms)
FIX_THR = 1.0     # 固定阈值(ms)：基线之上、无害之下


def sched_wait_cum():
    return int(open("/proc/self/schedstat").read().split()[1])


out = {}
for cond, lvl in [("A_hurtful", 3), ("B_harmless", 1)]:
    pids = spawn_cpu_busy(lvl)
    time.sleep(0.3)
    thr_h = FIX_THR
    reads, fire_h, fire_p = [], [], []
    for i in range(N):
        w0 = sched_wait_cum()
        t0 = time.perf_counter()
        work()
        lat = time.perf_counter() - t0
        dw = (sched_wait_cum() - w0) / 1e6
        reads.append(dw)
        # pain 臂：固定阈值
        fire_p.append(1 if dw > FIX_THR else 0)
        # habit 臂：阈值追踪
        fire_h.append(1 if dw > thr_h + MARGIN else 0)
        thr_h = ALPHA * thr_h + (1 - ALPHA) * dw
    killall(pids)
    time.sleep(0.3)
    out[cond] = {"reads": reads, "fire_habit": fire_h, "fire_pain": fire_p,
                 "lat_ms": lat * 1000, "thr_end": thr_h}

json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1.json"), "w"))

for cond in out:
    r = out[cond]
    h, p = r["fire_habit"], r["fire_pain"]
    q = N // 4
    print(f"\n== {cond} ==  dwait中位={sorted(r['reads'])[N//2]:.3f}ms  "
          f"末阈值={r['thr_end']:.2f}ms")
    print(f"  habit臂 检出率: 前1/4 {sum(h[:q])/q:.2f} → 后1/4 {sum(h[-q:])/q:.2f}")
    print(f"  pain臂  检出率: 前1/4 {sum(p[:q])/q:.2f} → 后1/4 {sum(p[-q:])/q:.2f}")
    print(f"  habit 逐轮: {''.join(str(x) for x in h)}")
    print(f"  pain  逐轮: {''.join(str(x) for x in p)}")
