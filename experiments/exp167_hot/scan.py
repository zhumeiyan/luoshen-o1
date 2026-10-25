import os, time, json

def probe():
    t0 = time.perf_counter_ns()
    x = 0
    for i in range(200000):
        x += i * i
    return time.perf_counter_ns() - t0

def med(n=5):
    return sorted(probe() for _ in range(n))[n//2]

base = med(9)
print(f"baseline={base}ns\n")

res = {}

# --- 信源A：CPU 竞争（几个真实子进程跑忙循环）---
import subprocess, signal
for n in [1,2,3]:
    ps=[]
    for _ in range(n):
        ps.append(subprocess.Popen(["python3","-c","x=0\nwhile 1: x+=1"]))
    time.sleep(1.2)
    res[f"cpu{n}"] = med()/base
    for p in ps:
        p.send_signal(signal.SIGKILL); p.wait()
    time.sleep(0.8)
    print(f"cpu竞争 {n}进程  倍率 {res[f'cpu{n}']:.3f}")

# --- 信源B：内存压力（真实分配+触碰）---
for mb in [64,128,256]:
    buf = bytearray(mb*1024*1024)
    for i in range(0,len(buf),4096):
        buf[i]=1
    r = med()/base
    res[f"mem{mb}"]=r
    del buf
    time.sleep(0.8)
    print(f"内存 {mb}MB   倍率 {r:.3f}")

# --- 信源C：I/O 压力（真实文件反复读）---
open("big.bin","wb").write(os.urandom(8*1024*1024))
for k in [1,2,4]:
    t0=time.perf_counter_ns()
    for _ in range(k):
        with open("big.bin","rb") as f:
            while f.read(1<<20): pass
    io = time.perf_counter_ns()-t0
    res[f"io{k}"] = io/1e6
    print(f"IO {k}轮({k*8}MB)  自身耗时 {io/1e6:.1f}ms")

json.dump({"base":base,"res":res}, open("scan.json","w"))
