"""S4 不可逆债务：schedstat 的累计等待时间是进程级累加、不可清零的。
损伤撤除后，增速归零但累计值不回落 —— 这就是'疼留下的东西'。
同时对照：nivcsw（次数）在持续期是否饱和。"""
import os, sys, json, time, resource
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import work, spawn_cpu_busy, killall

N_HURT = 10     # 前 10 轮施加损伤
N_HEAL = 10     # 后 10 轮撤除


def sched_wait_cum():
    p = open("/proc/self/schedstat").read().split()
    return int(p[1])          # 累计等待(被抢)时间 ns


def nivcsw_cum():
    return resource.getrusage(resource.RUSAGE_SELF).ru_nivcsw


w0 = sched_wait_cum()
n0 = nivcsw_cum()

rows = []
for i in range(N_HURT + N_HEAL):
    hurt = i < N_HURT
    pids = spawn_cpu_busy(3) if hurt else []
    time.sleep(0.25)
    wa_before = sched_wait_cum()
    nv_before = nivcsw_cum()
    t0 = time.perf_counter()
    work()
    lat = time.perf_counter() - t0
    wa_after = sched_wait_cum()
    nv_after = nivcsw_cum()
    killall(pids)
    time.sleep(0.2)
    rows.append({
        "i": i, "hurt": hurt,
        "lat_ms": lat * 1000,
        "dwait_ms": (wa_after - wa_before) / 1e6,
        "wait_cum_ms": (wa_after - w0) / 1e6,
        "dnivcsw": nv_after - nv_before,
        "nivcsw_cum": nv_after - n0,
    })

json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s4.json"), "w"), indent=1)

print(f"{'i':>3s} {'hurt':>5s} {'lat_ms':>8s} {'dwait_ms':>9s} {'waitCUM_ms':>11s} {'dniv':>5s} {'nivCUM':>7s}")
for r in rows:
    print(f"{r['i']:3d} {str(r['hurt']):>5s} {r['lat_ms']:8.2f} {r['dwait_ms']:9.3f} "
          f"{r['wait_cum_ms']:11.2f} {r['dnivcsw']:5d} {r['nivcsw_cum']:7d}")

hurt = [r for r in rows if r["hurt"]]
heal = [r for r in rows if not r["hurt"]]
import statistics as st
print()
print(f"损伤期  wait累计增量 = {hurt[-1]['wait_cum_ms'] - rows[0]['wait_cum_ms'] + rows[0]['dwait_ms']:.2f} ms")
print(f"撤除期  wait累计增量 = {heal[-1]['wait_cum_ms'] - hurt[-1]['wait_cum_ms']:.2f} ms")
print(f"撤除后 wait累计是否回落: {heal[-1]['wait_cum_ms'] < hurt[-1]['wait_cum_ms']}")
print(f"损伤期 dnivcsw 中位 = {st.median([r['dnivcsw'] for r in hurt]):.1f}, "
      f"撤除期 = {st.median([r['dnivcsw'] for r in heal]):.1f}")
