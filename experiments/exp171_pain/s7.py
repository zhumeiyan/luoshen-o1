"""S7 慢性痛的机制：通道与后果脱钩时，固定阈值会一直误报。
对照两组，各 24 轮持续刺激：
  A  cpu3  通道=dwait(被夺走的时间)   后果=延迟真的涨 3 倍  → 通道与后果绑定
  B  mem1000 通道=MemAvailable下降     后果=吞吐无变化       → 通道与后果脱钩
两臂：固定阈值 vs 自适应阈值。
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import work, spawn_cpu_busy, spawn_mem_holder, killall

N = 24
ALPHA, MARGIN = 0.25, 0.15


def sched_wait():
    return int(open("/proc/self/schedstat").read().split()[1])


def mem_avail():
    return int([l for l in open("/proc/meminfo")
                if l.startswith("MemAvailable")][0].split()[1])


out = {}
for cond, kind, lvl in [("A_cpu3", "cpu", 3), ("B_mem1000", "mem", 1000)]:
    # 基线
    blat, bmem = [], []
    for _ in range(5):
        t0 = time.perf_counter(); work(); blat.append(time.perf_counter() - t0)
        bmem.append(mem_avail())
    blat.sort(); BASE = blat[2]
    BMEM = sorted(bmem)[2]

    pids = spawn_cpu_busy(lvl) if kind == "cpu" else [spawn_mem_holder(lvl)]
    time.sleep(0.4)

    # 校准固定阈值：取前 3 轮读数中位 * 2（基线之上）
    warm = []
    for _ in range(3):
        if kind == "cpu":
            w0 = sched_wait(); work(); warm.append((sched_wait() - w0) / 1e6)
        else:
            work(); warm.append((BMEM - mem_avail()) / 1024.0)
    FIX_THR = sorted(warm)[1] * 2 + 0.5

    thr_h = FIX_THR
    reads, fire_h, fire_p, lats = [], [], [], []
    for i in range(N):
        if kind == "cpu":
            w0 = sched_wait()
            t0 = time.perf_counter(); work(); lat = time.perf_counter() - t0
            r = (sched_wait() - w0) / 1e6
        else:
            t0 = time.perf_counter(); work(); lat = time.perf_counter() - t0
            r = (BMEM - mem_avail()) / 1024.0
        reads.append(r); lats.append(lat)
        fire_p.append(1 if r > FIX_THR else 0)
        fire_h.append(1 if r > thr_h * (1 + MARGIN) else 0)
        thr_h = ALPHA * thr_h + (1 - ALPHA) * r
    killall(pids); time.sleep(0.4)

    lats.sort()
    out[cond] = {
        "reads": reads, "fire_habit": fire_h, "fire_pain": fire_p,
        "FIX_THR": FIX_THR, "thr_end": thr_h,
        "lat_ratio": lats[N // 2] / BASE, "BASE_ms": BASE * 1000,
    }

json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s7.json"), "w"))

for c in out:
    r = out[c]
    h, p = r["fire_habit"], r["fire_pain"]
    q = N // 4
    print(f"\n== {c} ==  固定阈值={r['FIX_THR']:.3f}  末阈值={r['thr_end']:.3f}  "
          f"读数中位={sorted(r['reads'])[N//2]:.3f}")
    print(f"  【真实后果】延迟倍率 = {r['lat_ratio']:.3f}  "
          f"({'有害' if r['lat_ratio'] > 1.3 else '无害'})")
    print(f"  pain臂(FIX)  前1/4 {sum(p[:q])/q:.2f} → 后1/4 {sum(p[-q:])/q:.2f}   {''.join(map(str,p))}")
    print(f"  habit臂(ADAPT) 前1/4 {sum(h[:q])/q:.2f} → 后1/4 {sum(h[-q:])/q:.2f}   {''.join(map(str,h))}")
