"""S5 强度函数 + S3 标定：找三种信源各自的物理量 -> 后果(吞吐倍率) 曲线。
顺序随机化，防漂移伪影。"""
import os, sys, json, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import work, spawn_cpu_busy, spawn_mem_holder, spawn_io_reader, killall, sense

random.seed(1711)
REPS = 5

# 基线
base = []
for _ in range(12):
    t0 = time.perf_counter()
    work()
    base.append(time.perf_counter() - t0)
base.sort()
BASE = base[len(base) // 2]
print(f"BASE median = {BASE*1000:.2f} ms")

CONDS = []
for n in [1, 2, 3, 4, 6]:
    CONDS.append(("cpu", n))
for mb in [200, 400, 700, 1000]:
    CONDS.append(("mem", mb))
for n in [1, 2, 4]:
    CONDS.append(("io", n))
CONDS.append(("none", 0))

# 随机化顺序
order = CONDS * REPS
random.shuffle(order)

res = {}
for kind, lvl in order:
    pids = []
    if kind == "cpu":
        pids = spawn_cpu_busy(lvl)
    elif kind == "mem":
        pids = [spawn_mem_holder(lvl)]
    elif kind == "io":
        pids = spawn_io_reader(lvl)
    time.sleep(0.25)  # 让损伤生效

    ts = []
    sens = []
    for _ in range(3):
        t0 = time.perf_counter()
        work()
        ts.append(time.perf_counter() - t0)
        sens.append(sense())
    killall(pids)
    time.sleep(0.25)

    ts.sort()
    med = ts[1]
    res.setdefault(f"{kind}{lvl}", {"ts": [], "sens": []})
    res[f"{kind}{lvl}"]["ts"].append(med)
    res[f"{kind}{lvl}"]["sens"].append(sens[1])

out = {}
for k, v in res.items():
    tss = v["ts"]
    tss_sorted = sorted(tss)
    med = tss_sorted[len(tss_sorted) // 2]
    out[k] = {
        "lat_ms": med * 1000,
        "ratio": med / BASE,
        "n": len(tss),
        "sens_med": {
            "load1": sorted([s["load1"] for s in v["sens"]])[len(v["sens"]) // 2],
            "ctxt": sorted([s["ctxt"] for s in v["sens"]])[len(v["sens"]) // 2],
            "mem_kb": sorted([s["mem_kb"] for s in v["sens"]])[len(v["sens"]) // 2],
        },
    }
    print(f"{k:10s} lat={med*1000:8.2f}ms  ratio={med/BASE:6.3f}  "
          f"load1={out[k]['sens_med']['load1']:.2f} mem={out[k]['sens_med']['mem_kb']}")

json.dump({"BASE_ms": BASE * 1000, "res": out},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "s5.json"), "w"),
          indent=1)
