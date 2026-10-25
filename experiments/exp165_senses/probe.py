import time, os, json, statistics as st

def rd(p):
    try:
        with open(p) as f: return f.read()
    except Exception: return None

def num(p, idx=None, key=None):
    s = rd(p)
    if s is None: return None
    if key:
        for line in s.splitlines():
            if line.startswith(key): return float(line.split()[1])
        return None
    parts = s.split()
    return float(parts[idx]) if idx is not None else float(parts[0])

CH = {
  "viscera_io_rchar":  lambda: num("/proc/self/io", key="rchar"),
  "viscera_utime":     lambda: num("/proc/self/stat", idx=13),
  "world_idle":        lambda: float(rd("/proc/uptime").split()[1]),
  "world_uptime":      lambda: float(rd("/proc/uptime").split()[0]),
  "entropy_avail":     lambda: num("/proc/sys/kernel/random/entropy_avail"),
  "fd_open":           lambda: float(rd("/proc/sys/fs/file-nr").split()[0]),
  "mem_avail":         lambda: num("/proc/meminfo", key="MemAvailable:"),
  "loadavg":           lambda: float(rd("/proc/loadavg").split()[0]),
  "ctx_switches":      lambda: num("/proc/stat", key="ctxt"),
  "procs_running":     lambda: num("/proc/stat", key="procs_running"),
}

N=120
res={}
for name, fn in CH.items():
    vals=[]
    for _ in range(N):
        try: v=fn()
        except Exception: v=None
        if v is not None: vals.append(v)
        time.sleep(0.005)
    if len(vals)<10:
        res[name]={"n":len(vals),"alive":False,"note":"unreadable"}; continue
    # 自发变化率：相邻差非零的比例
    diffs=[abs(vals[i+1]-vals[i]) for i in range(len(vals)-1)]
    nonzero=sum(1 for d in diffs if d>0)/len(diffs)
    res[name]={
      "n":len(vals),
      "nonzero_rate":round(nonzero,4),
      "stdev":round(st.pstdev(vals),6),
      "mean":round(st.mean(vals),4),
      "range":round(max(vals)-min(vals),6),
    }
print(json.dumps(res,indent=1,ensure_ascii=False))
json.dump(res,open("probe.json","w"),indent=1,ensure_ascii=False)
