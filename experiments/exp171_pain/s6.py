"""疼的正确信源不是'环境有多忙'，是'我被抢走了多少'。
通道候选：ru_nivcsw（非自愿上下文切换，真实内核计数器，累积、不可清零）
对照：load1 / ctxt（已证瞎）
后果：吞吐倍率
"""
import os, sys, json, time, random, resource
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import work, spawn_cpu_busy, killall

random.seed(1712)


def nivcsw():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_nivcsw, r.ru_nvcsw


def sched_stat():
    """/proc/self/schedstat: 累计运行时间ns, 累计等待(被抢)时间ns, 次数"""
    try:
        p = open("/proc/self/schedstat").read().split()
        return int(p[0]), int(p[1]), int(p[2])
    except Exception:
        return None, None, None


def load1():
    return float(open("/proc/loadavg").read().split()[0])


REPS = 6
CONDS = [("none", 0)] * 1 + [("cpu", n) for n in [1, 2, 3, 4, 6]]
CONDS = CONDS * REPS
random.shuffle(CONDS)

rows = []
for kind, lvl in CONDS:
    pids = spawn_cpu_busy(lvl) if kind == "cpu" else []
    time.sleep(0.3)
    n0, v0 = nivcsw()
    w0, wa0, c0 = sched_stat()
    t0 = time.perf_counter()
    work()
    lat = time.perf_counter() - t0
    n1, v1 = nivcsw()
    w1, wa1, c1 = sched_stat()
    killall(pids)
    time.sleep(0.3)
    rows.append({
        "kind": kind, "lvl": lvl, "lat": lat,
        "dnivcsw": n1 - n0, "dnvcsw": v1 - v0,
        "drun_ns": (w1 - w0) if w1 else None,
        "dwait_ns": (wa1 - wa0) if wa1 else None,
        "load1": load1(),
    })

json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s6.json"), "w"))

import statistics as st
print(f"{'cond':8s} {'lat_ms':>8s} {'n':>3s} {'dNIVCSW':>9s} {'dwait_ms':>9s} {'load1':>6s}")
for lvl in [0, 1, 2, 3, 4, 6]:
    sub = [r for r in rows if r["lvl"] == lvl]
    if not sub:
        continue
    lat = st.median([r["lat"] for r in sub]) * 1000
    dn = st.median([r["dnivcsw"] for r in sub])
    dw = st.median([r["dwait_ns"] for r in sub if r["dwait_ns"] is not None]) / 1e6
    ld = st.median([r["load1"] for r in sub])
    print(f"{'cpu'+str(lvl):8s} {lat:8.2f} {len(sub):3d} {dn:9.1f} {dw:9.3f} {ld:6.2f}")
