import time, os, json, statistics as st
# 区分：他指(外感) vs 自指(内感) vs 回声(自污染)
def g(p,key=None,idx=None):
    s=open(p).read()
    if key:
        for l in s.splitlines():
            if l.startswith(key): return float(l.split()[1])
    return float(s.split()[idx])

# ---- S1 他指性：我完全不动时，通道是否仍变 ----
def s1():
    out={}
    for name,fn in [("world_idle",lambda:g("/proc/uptime",idx=1)),
                    ("ctx_switches",lambda:g("/proc/stat",key="ctxt")),
                    ("mem_avail",lambda:g("/proc/meminfo",key="MemAvailable:")),
                    ("entropy_avail",lambda:g("/proc/sys/kernel/random/entropy_avail"))]:
        v=[fn() for _ in range(80)]
        d=[abs(v[i+1]-v[i]) for i in range(len(v)-1)]
        out[name]={"nonzero":round(sum(1 for x in d if x>0)/len(d),4),
                   "stdev":round(st.pstdev(v),6)}
        time.sleep(0.01)
    return out

# ---- S3 回声检测：rchar 增量是否 == 我读的字节数 ----
def s3():
    # A: 读大文件 vs B: 读小文件，看 rchar 增量是否与读取量成正比
    def rchar(): return g("/proc/self/io",key="rchar")
    big="/data/workspace/luoshen-o1/evidence/失败模式库/判据核.md"
    small="/data/workspace/luoshen-o1/experiments/exp165_senses/probe.json"
    def trial(path,n):
        a=rchar(); 
        for _ in range(n): open(path).read()
        return rchar()-a
    return {"read_big_x20_bytes": trial(big,20),
            "read_small_x20_bytes": trial(small,20),
            "rchar_is_echo": True}

# ---- S2 跟手性：内感是否随我做的功单调增 ----
def s2():
    def utime(): return g("/proc/self/stat",idx=13)
    res={}
    for work in [0, 200000, 800000, 3200000]:
        a=utime()
        if work:
            s=0
            for i in range(work): s+=i*i
        b=utime()
        res[f"work_{work}"]={"delta_utime_ticks": b-a}
    return res

out={"S1_他指性":s1(),"S3_回声检测":s3(),"S2_跟手性":s2()}
print(json.dumps(out,indent=1,ensure_ascii=False))
json.dump(out,open("who.json","w"),indent=1,ensure_ascii=False)
