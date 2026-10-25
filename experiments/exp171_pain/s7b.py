"""补做：1) s1 独立重复（验证可复现性） 2) s7 修正阈值校准（基线分位+小余量）
基线各自采 8 轮无损伤读数，固定阈值 = 基线 Q3 + 余量（基线量纲相关）。
"""
import os, sys, json, time, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import work, spawn_cpu_busy, spawn_mem_holder, killall

N = 24
ALPHA, MARGIN = 0.25, 0.15


def sched_wait():
    return int(open("/proc/self/schedstat").read().split()[1])


def mem_avail():
    return int([l for l in open("/proc/meminfo")
                if l.startswith("MemAvailable")][0].split()[1])


def measure(kind):
    """读一次通道增量 + 做一轮工作"""
    if kind == "cpu":
        w0 = sched_wait()
        t0 = time.perf_counter(); work(); lat = time.perf_counter() - t0
        return (sched_wait() - w0) / 1e6, lat
    else:
        t0 = time.perf_counter(); work(); lat = time.perf_counter() - t0
        return mem_avail(), lat      # 原始值，稍后转成下降量


out = {}
for rep in range(2):
    for cond, kind, lvl in [("A_cpu3", "cpu", 3), ("B_mem1000", "mem", 1000)]:
        # --- 无损伤基线：8 轮 ---
        br, bl = [], []
        for _ in range(8):
            r, lat = measure(kind)
            br.append(r); bl.append(lat)
        bl.sort(); BASE = bl[4]
        bq3 = sorted(br)[6]

        pids = spawn_cpu_busy(lvl) if kind == "cpu" else [spawn_mem_holder(lvl)]
        time.sleep(0.4)

        warm = []
        for _ in range(4):
            r, _ = measure(kind)
            warm.append(r)
        wq = sorted(warm)[2]

        if kind == "cpu":
            FIX_THR = bq3 + 0.5                 # 基线之上 0.5ms
            conv = lambda x: x                  # dwait 已是 ms
        else:
            FIX_THR = bq3 - 50 * 1024           # 基线之下 50MB
            conv = lambda x: x                  # 原始 KB，反向比较
        compare = (lambda r, t: r > t) if kind == "cpu" else (lambda r, t: r < t)

        thr_h = abs(FIX_THR - bq3) or 1.0
        if kind == "mem":
            thr_h = 50 * 1024                  # 自适应初值 = 50MB 下降量

        reads, fire_h, fire_p, lats = [], [], [], []
        for i in range(N):
            r, lat = measure(kind)
            reads.append(r); lats.append(lat)
            fire_p.append(1 if compare(r, FIX_THR) else 0)
            if kind == "cpu":
                fire_h.append(1 if r > thr_h * (1 + MARGIN) else 0)
                thr_h = ALPHA * thr_h + (1 - ALPHA) * r
            else:
                d = bq3 - r
                fire_h.append(1 if d > thr_h * (1 + MARGIN) else 0)
                thr_h = ALPHA * thr_h + (1 - ALPHA) * d
        killall(pids); time.sleep(0.4)

        lats.sort()
        key = f"rep{rep}_{cond}"
        out[key] = {
            "kind": kind,
            "base_read": bq3, "stim_read": wq, "FIX_THR": FIX_THR,
            "reads_med": st.median(reads), "thr_end": thr_h,
            "fire_pain": fire_p, "fire_habit": fire_h,
            "lat_ratio": lats[N // 2] / BASE, "BASE_ms": BASE * 1000,
        }

HERE = os.path.dirname(os.path.abspath(__file__))
json.dump(out, open(os.path.join(HERE, "s7b.json"), "w"))
for k in sorted(out):
    r = out[k]
    h, p = r["fire_habit"], r["fire_pain"]
    q = 6
    verdict = "有害" if r["lat_ratio"] > 1.3 else "无害"
    print(f"\n== {k} ==  基线读数={r['base_read']:.1f} 刺激读数={r['stim_read']:.1f} "
          f"固定阈={r['FIX_THR']:.1f} 末阈={r['thr_end']:.1f}")
    print(f"  【真实后果】延迟倍率 {r['lat_ratio']:.3f} → {verdict}")
    print(f"  pain (FIX)   {sum(p[:q])/q:.2f} → {sum(p[-q:])/q:.2f}  {''.join(map(str,p))}")
    print(f"  habit(ADAPT) {sum(h[:q])/q:.2f} → {sum(h[-q:])/q:.2f}  {''.join(map(str,h))}")
