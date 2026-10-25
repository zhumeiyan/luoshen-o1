import os, time, json, subprocess, signal

def med(f, n=3):
    return sorted(f() for _ in range(n))[n//2]

out={}

# ===== 任务A：CPU计算。信源=并发忙进程 =====
def task_cpu():
    t0=time.perf_counter_ns(); x=0
    for i in range(200000): x+=i*i
    return time.perf_counter_ns()-t0

# ===== 任务B：文件读。信源=并发读进程 =====
open("f.bin","wb").write(os.urandom(4*1024*1024))
def task_io():
    t0=time.perf_counter_ns()
    with open("f.bin","rb") as fh:
        while fh.read(1<<20): pass
    return time.perf_counter_ns()-t0

# ===== 任务C：内存分配+触碰。信源=预占用内存 =====
def task_mem():
    t0=time.perf_counter_ns()
    b=bytearray(32*1024*1024)
    for i in range(0,len(b),4096): b[i]=1
    return time.perf_counter_ns()-t0

def stress_cpu(n):
    ps=[subprocess.Popen(["python3","-c","x=0\nwhile 1: x+=1"]) for _ in range(n)]
    time.sleep(1.0); return ps
def stress_io(n):
    ps=[subprocess.Popen(["python3","-c",
        "import os\nwhile 1:\n f=open('f.bin','rb')\n while f.read(1<<20): pass\n f.close()"]) for _ in range(n)]
    time.sleep(1.0); return ps
def stress_mem(mb):
    b=bytearray(mb*1024*1024)
    for i in range(0,len(b),4096): b[i]=1
    return b

def kill(ps):
    for p in ps: p.send_signal(signal.SIGKILL); p.wait()

for name, task, levels, st in [
    ("A_cpu", task_cpu, [0,1,2,3], stress_cpu),
    ("B_io",  task_io,  [0,1,2,3], stress_io),
]:
    base = med(task, 5)
    pts=[]
    for lv in levels:
        ps = st(lv) if lv else []
        r = med(task)/base
        if ps: kill(ps); time.sleep(0.7)
        pts.append((lv, round(r,3)))
        print(f"{name} 干扰{lv}  倍率 {r:.3f}")
    out[name]={"base_ns":base,"pts":pts}

# 内存信源：预占用不同量，看任务C变慢
base = med(task_mem,5)
pts=[]
for mb in [0,64,128,192]:
    hold = stress_mem(mb) if mb else None
    r = med(task_mem)/base
    del hold
    time.sleep(0.7)
    pts.append((mb, round(r,3)))
    print(f"C_mem 预占{mb}MB  倍率 {r:.3f}")
out["C_mem"]={"base_ns":base,"pts":pts}

json.dump(out, open("scan2.json","w"), indent=1)
