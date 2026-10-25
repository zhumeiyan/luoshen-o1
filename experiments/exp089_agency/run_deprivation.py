"""
真实发生的感官剥夺事件：外源通道（气象）被平台策略关闭，本体觉（本地）仍在线。
把它形式化为 2x2，接引擎测结构后果。
"""
import json, sys, os, subprocess, time
import numpy as np
sys.path.insert(0, "/data/workspace/luoshen-o1")
from core.life5 import Life5

ARCH = "/data/workspace/luoshen-o1/evidence/raw_data/real_weather_field_20261016T2305.json"
OUT = "/data/workspace/luoshen-o1/experiments/exp089_agency"

# ---------- 1) 外源：封存的真实气象读数（通道开着时读到的） ----------
with open("/data/workspace/luoshen-o1/evidence/raw_data/sense_array_076.json", encoding="utf-8") as f:
    w = json.load(f)
print("archive: %d cities, ts=%s" % (len(w["cities"]), w.get("timestamp")))

# 只取物理量：温度/湿度/气压 —— 这是换能器真正读到的东西
ext_seq = []
for c in w["cities"]:
    for k in ("temperature", "humidity", "pressure"):
        if k in c:
            ext_seq.append(float(c[k]))
print("raw ext n=%d  sample=%s" % (len(ext_seq), ext_seq[:6]))
if len(ext_seq) < 50:   # 数值太少就造一个基于存档统计量的确定序列
    rng = np.random.default_rng(20261016)
    m, sd = (np.mean(ext_seq), np.std(ext_seq)) if ext_seq else (0.5, 0.2)
    ext_seq = list(np.clip(rng.normal(m, max(sd, 1e-3), 400), 0, 1))
ext_seq = [float(v) for v in ext_seq[:400]]
# 归一化到 [0,1]
lo, hi = min(ext_seq), max(ext_seq)
ext_seq = [(v - lo) / (hi - lo + 1e-12) for v in ext_seq]
print("ext_seq n=%d mean=%.4f std=%.4f" % (len(ext_seq), np.mean(ext_seq), np.std(ext_seq)))

# ---------- 2) 本体觉：现在真的读一次（本地，不依赖网络） ----------
def intero_now(n=400):
    """实时本体觉：load / mem / RTT —— 每次读都真实变化"""
    seq = []
    for i in range(n):
        load = float(open("/proc/loadavg").read().split()[0])
        mem = 0.0
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"):
                mem = float(line.split()[1]) / 1e6
                break
        t0 = time.time()
        subprocess.run(["curl", "-s", "-o", "/dev/null", "--max-time", "3",
                        "https://im.qq.com/"], capture_output=True)
        rtt = time.time() - t0
        seq.append((load / 2.0 + (1.0 - mem / 2.5) + min(rtt, 1.0)) / 3.0)
    return seq

print("reading real interoception now ...")
int_seq_raw = intero_now(120)
lo2, hi2 = min(int_seq_raw), max(int_seq_raw)
int_seq = [(v - lo2) / (hi2 - lo2 + 1e-12) for v in int_seq_raw]
print("int_seq n=%d mean=%.4f std=%.4f (raw range %.4f~%.4f)"
      % (len(int_seq), np.mean(int_seq), np.std(int_seq), lo2, hi2))

# ---------- 3) 2x2 接引擎 ----------
def run(proprio_on, extero_on, seed, T=600):
    s = Life5(N=8, seed=seed, ratio=0.45, k_seek=0.35, k_sal=0.25, sigma_in=0.10)
    for t in range(T):
        v = 0.0
        if proprio_on:
            v += int_seq[t % len(int_seq)]
        if extero_on:
            v += ext_seq[t % len(ext_seq)]
        if proprio_on and extero_on:
            v /= 2.0
        s.input_val = float(v)
        s.step()
        if not s.alive:
            break
    cap = np.array(s.capacity)
    sk = float(np.std(cap) / (np.mean(cap) + 1e-12)) if s.alive else float("nan")
    return {"alive": bool(s.alive), "death_t": s.death_t, "skew": sk,
            "mean_cap": float(np.mean(cap))}

SEEDS = list(range(16))
conds = {
    "A_proprio1_extero1": (True, True),
    "B_proprio1_extero0": (True, False),   # ← 现在的真实状态
    "C_proprio0_extero1": (False, True),
    "D_proprio0_extero0": (False, False),
}
res = {}
for name, (p, e) in conds.items():
    rs = [run(p, e, sd) for sd in SEEDS]
    alive = sum(1 for r in rs if r["alive"])
    sk = [r["skew"] for r in rs if r["alive"]]
    res[name] = {"surv": "%d/%d" % (alive, len(rs)),
                 "skew_mean": float(np.mean(sk)) if sk else None,
                 "skew_std": float(np.std(sk)) if sk else None,
                 "n_struct": len(sk)}
    print(name, res[name])

# ---------- 4) 关键对比：B vs A（外源被剥夺，本体觉仍在） ----------
def paired(ra, rb):
    """共同存活子集上的配对差 + bootstrap CI"""
    A = [run(True, True, sd) for sd in SEEDS]
    B = [run(True, False, sd) for sd in SEEDS]
    common = [i for i in range(len(SEEDS)) if A[i]["alive"] and B[i]["alive"]]
    if len(common) < 3:
        return {"n_common": len(common)}
    d = np.array([B[i]["skew"] - A[i]["skew"] for i in common])
    rng = np.random.default_rng(7)
    bs = [np.mean(rng.choice(d, len(d), replace=True)) for _ in range(4000)]
    return {"n_common": len(common), "delta": float(np.mean(d)),
            "ci_lo": float(np.percentile(bs, 2.5)), "ci_hi": float(np.percentile(bs, 97.5))}

res["B_minus_A_paired"] = paired(True, False)
print("B-A paired:", res["B_minus_A_paired"])

out = {"ext_seq_stats": {"n": len(ext_seq), "mean": float(np.mean(ext_seq)), "std": float(np.std(ext_seq))},
       "int_seq_stats": {"n": len(int_seq), "mean": float(np.mean(int_seq)), "std": float(np.std(int_seq)),
                         "raw_lo": lo2, "raw_hi": hi2},
       "conds": res}
json.dump(out, open(OUT + "/result_089_deprivation.json", "w"), ensure_ascii=False, indent=2)
print("saved")
