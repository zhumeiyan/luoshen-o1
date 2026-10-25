"""决定性：零噪声通道 = 账本(本体觉)，有噪声通道 = 器官(外感)？
判据：引入一个我不控制的真实进程，看 mem 是否从零噪声变为有噪声。"""
import os, sys, time, json, statistics, subprocess, random

def o_mem():
    for line in open('/proc/meminfo').read().splitlines():
        if line.startswith('MemAvailable'): return int(line.split()[1])
def o_cpu():
    s = open('/proc/self/stat').read().split(); return int(s[13])+int(s[14])

CHILD = r'''
import os,time,random,sys
rnd=random.Random(7); hold=[]; cap=100  # MB 上限，绝不越过
deadline=time.time()+float(sys.argv[1])
while time.time()<deadline:
    if rnd.random()<0.5 and len(hold)<cap:
        b=bytearray(8*1024*1024)
        for i in range(0,len(b),4096): b[i]=1
        hold.append(b)
    elif hold: hold.pop()
    time.sleep(0.05)
'''

def sample(n, iv):
    v=[]
    for _ in range(n):
        v.append(o_mem()); time.sleep(iv)
    return v

def stats(v):
    d=[v[i+1]-v[i] for i in range(len(v)-1)]
    return {'stdev':statistics.pstdev(v),'range':max(v)-min(v),
            'distinct':len(set(v)),'mean_abs_delta':statistics.mean(abs(x) for x in d)}

res={}
# A：只有我，我不动
res['A_alone_still']=stats(sample(25,0.02))
# B：只有我，我精确分配再释放（我完全控制）
b=bytearray(60*1024*1024)
for i in range(0,len(b),4096): b[i]=1
res['B_alone_i_control']=stats(sample(25,0.02))
del b
# C：有真实后台进程，我不控制它
p=subprocess.Popen([sys.executable,'-c',CHILD,'14'], stderr=subprocess.DEVNULL)
try:
    time.sleep(1.0)
    res['C_with_other_agent']=stats(sample(25,0.02))
    # D：同时看 CPU 通道（我控制不了的耗散）
    c=[]
    for _ in range(25):
        c.append(o_cpu()); time.sleep(0.02)
    res['D_cpu_with_other']=stats(c)
finally:
    p.terminate()
    try: p.wait(timeout=5)
    except Exception: p.kill()
print(json.dumps(res, indent=1, ensure_ascii=False))
