import sys, json, time, statistics as st
sys.path.insert(0, '.')
from world151 import World
from agent151 import run, Peer

T = 150
NREP = 16          # 文化条件用前 6 轮预热，报告后 10 轮
HALF = 6

def wilson(hits, n, z=1.96):
    p = hits/n
    d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    h = z*((p*(1-p)/n + z*z/(4*n*n))**0.5)/d
    return round(c-h, 3), round(c+h, 3)

def ci(vals):
    m = sum(vals)/len(vals)
    s = st.stdev(vals) if len(vals) > 1 else 0.0
    se = s/(len(vals)**0.5)
    return round(m, 3), round(m-1.96*se, 3), round(m+1.96*se, 3)

ALL = {"L1":True,"L2":True,"L3":True,"L4g":True,"L4d":True,"L4p":True,
       "L6m":True,"L6a":True,"L6d":True,"L6c":True}

CONDS = {
 "OFF":        {},
 "L1":         {"L1":True},
 "L1+L2":      {"L1":True,"L2":True},
 "L1+L3":      {"L1":True,"L3":True},
 "L1+L4g":     {"L1":True,"L4g":True},
 "L1+L4d":     {"L1":True,"L4d":True},
 "L1+L4p":     {"L1":True,"L4p":True},
 "L1+L6m":     {"L1":True,"L6m":True},
 "L1+L6a":     {"L1":True,"L6a":True},
 "L1+L6d":     {"L1":True,"L6d":True},
 "L1+L6c":     {"L1":True,"L6c":True},
 "BEST_noL5":  {"L1":True,"L3":True,"L4g":True,"L6d":True,"L6c":True},
 "FULL_noL5":  dict(ALL),
}
# 消融：从 FULL_noL5 敲掉一格
for k in ["L1","L2","L3","L4g","L4d","L4p","L6m","L6a","L6d","L6c"]:
    d = dict(ALL); d[k] = False
    CONDS["ABL_-"+k] = d

def main():
    w = World(500)
    out = {"meta": {"T": T, "nrep": NREP, "half": HALF, "nodes": w.n,
                    "targets": len(w.targets), "deg": w.deg_mean}, "cond": {}}
    for name, fl in CONDS.items():
        cs = {}
        vals = []
        t0 = time.perf_counter()
        for s in range(NREP):
            r = run(w, fl, T, s, culture_store=cs)
            vals.append(r["hits"])
        late = vals[HALF:]
        m, lo, hi = ci(late)
        out["cond"][name] = {"mean": m, "lo": lo, "hi": hi,
                             "first": round(sum(vals[:HALF])/HALF, 2),
                             "all": round(sum(vals)/len(vals), 2),
                             "vals": late}
        print("%-14s late %6.2f CI[%6.2f,%6.2f]  first %6.2f  (%.1fs)"
              % (name, m, lo, hi, out["cond"][name]["first"], time.perf_counter()-t0), flush=True)
    json.dump(out, open("result151.json", "w"), indent=1)
    print("saved")

if __name__ == "__main__":
    main()
