"""152: 等预算下 文化(多代+继承) vs 时间(单人长跑) vs 分代(不继承)"""
import sys, json, time, statistics as st
sys.path.insert(0, '/data/workspace/luoshen-o1/experiments/exp151_integration')
from world151 import World
from agent151 import run

T = 150
NREP = 8
CULT = {"L1": True, "L6c": True}
SOLO = {"L1": True}

def ci(vals):
    n = len(vals); m = sum(vals)/n
    s = st.stdev(vals) if n > 1 else 0.0
    se = s/(n**0.5)
    return round(m,3), round(m-1.96*se,3), round(m+1.96*se,3)

w = World(500)
out = {"meta": {"T":T, "nrep":NREP, "nodes":w.n, "targets":len(w.targets),
                "deg":w.deg_mean}, "culture":{}, "solo":{}, "solo_seg":{}}

# ---- 1. culture: G 代 × 150 步，代间继承 ----
print("== culture (inherit) ==")
for G in [1,2,4,8,16,32]:
    finals, knows = [], []
    t0=time.perf_counter()
    for rep in range(NREP):
        cs = {}
        last = 0
        for g in range(G):
            r = run(w, CULT, T, rep*1000+g, culture_store=cs)
            last = r["hits"]
        finals.append(last); knows.append(len(cs.get("found",[])))
    m,lo,hi = ci(finals)
    out["culture"][G] = {"steps": G*T, "mean":m, "lo":lo, "hi":hi,
                         "known": round(sum(knows)/len(knows),1), "vals":finals}
    print("  G=%-3d steps=%-6d final %6.2f CI[%6.2f,%6.2f] known %5.1f (%.1fs)"
          % (G, G*T, m, lo, hi, out["culture"][G]["known"], time.perf_counter()-t0), flush=True)

# ---- 2. solo: 1 代 × T_big 步，visited 连续累积 ----
print("== solo (single long run) ==")
for TB in [150,300,600,1200,2400,4800,9600,19200]:
    vals = []
    t0=time.perf_counter()
    for rep in range(NREP):
        r = run(w, SOLO, TB, rep)
        vals.append(r["hits"])
    m,lo,hi = ci(vals)
    out["solo"][TB] = {"steps":TB, "mean":m, "lo":lo, "hi":hi, "vals":vals}
    print("  T=%-6d          final %6.2f CI[%6.2f,%6.2f]           (%.1fs)"
          % (TB, m, lo, hi, time.perf_counter()-t0), flush=True)

# ---- 3. solo_seg: G 代 × 150 步，不继承（阴性对照：分代本身有无价值）----
print("== solo_seg (G generations, NO inherit) ==")
for G in [1,2,4,8,16,32]:
    finals = []
    t0=time.perf_counter()
    for rep in range(NREP):
        last = 0
        for g in range(G):
            r = run(w, SOLO, T, rep*1000+g)   # 无 culture_store -> 每代全新
            last = r["hits"]
        finals.append(last)
    m,lo,hi = ci(finals)
    out["solo_seg"][G] = {"steps":G*T, "mean":m, "lo":lo, "hi":hi, "vals":finals}
    print("  G=%-3d steps=%-6d final %6.2f CI[%6.2f,%6.2f]           (%.1fs)"
          % (G, G*T, m, lo, hi, time.perf_counter()-t0), flush=True)

json.dump(out, open("result152.json","w"), indent=1)
print("saved result152.json")
